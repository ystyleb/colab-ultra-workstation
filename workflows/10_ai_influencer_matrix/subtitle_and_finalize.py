#!/usr/bin/env python3
"""Local 0-CCU Finalizer: 1080x1920 Upscale + Acoustic-Aligned PIL Phrase Subtitles + Hook Pill.

Takes raw 768x1344 MP4s produced by Cloud G4 (`outputs/raw/AIInf_<ID>_*.mp4`), upscales via Lanczos
to 1080x1920, aligns 3-5 word punchy English caption chunks to detected speech energy envelopes
(zero libass dependency via transparent RGBA PIL overlays), adds an opening hook pill (0.0s-2.4s),
and writes upload-ready MP4s into `outputs/final/<ID>_final_1080x1920.mp4`.

Includes `--self-test` (0 CCU) to verify end-to-end FFmpeg + PIL compositing locally.
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import struct
import subprocess
import tempfile
import wave
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
CONFIG_PATH = HERE / "influencer_config.json"
MANIFEST_PATH = HERE / "scripts_30_manifest.json"
SAMPLE_DIR = HERE / "sample_inputs"
RAW_DIR = HERE / "outputs" / "raw"
FINAL_DIR = HERE / "outputs" / "final"
WORK_DIR = HERE / "work"

W, H = 1080, 1920


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for p in (
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Impact.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ):
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def probe_duration(mp4_path: Path) -> float:
    out = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(mp4_path),
        ],
        text=True,
    ).strip()
    return float(out)


def probe_resolution(mp4_path: Path) -> str:
    out = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "csv=s=x:p=0",
            str(mp4_path),
        ],
        text=True,
    ).strip()
    return out


def detect_speech_window(media_path: Path, total_dur: float) -> tuple[float, float]:
    """Detect active speech start/end via 20ms RMS energy envelope from extracted mono 16k PCM."""
    tmp_wav = Path(tempfile.mkdtemp(prefix="wf10_env_", dir="/tmp")) / "mono.wav"
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-i", str(media_path), "-ac", "1", "-ar", "16000", "-vn", str(tmp_wav)],
            check=False,
        )
        if not tmp_wav.exists() or tmp_wav.stat().st_size < 1000:
            return 0.25, max(1.0, total_dur - 0.35)
        with wave.open(str(tmp_wav), "rb") as wf:
            sr = wf.getframerate()
            frames = wf.readframes(wf.getnframes())
        samples = struct.unpack(f"<{len(frames) // 2}h", frames)
        hop = int(sr * 0.02)
        rms_vals = []
        for i in range(0, len(samples) - hop, hop):
            seg = samples[i : i + hop]
            rms = math.sqrt(sum(s * s for s in seg) / len(seg))
            rms_vals.append(rms)
        if not rms_vals:
            return 0.25, max(1.0, total_dur - 0.35)
        peak = max(rms_vals)
        if peak < 180.0:
            return 0.25, max(1.0, total_dur - 0.35)
        thresh = max(180.0, peak * 0.14)
        active = [idx * 0.02 for idx, r in enumerate(rms_vals) if r >= thresh]
        if not active:
            return 0.25, max(1.0, total_dur - 0.35)
        return max(0.15, active[0] - 0.05), min(total_dur - 0.15, active[-1] + 0.12)
    finally:
        shutil.rmtree(tmp_wav.parent, ignore_errors=True)


def detect_pauses(wav: Path, noise_db: float = -35.0, min_sil: float = 0.25) -> list[tuple[float, float]]:
    """Silence spans in the voiceover (ffmpeg silencedetect) -> [(start, end), ...]."""
    r = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(wav), "-af", f"silencedetect=noise={noise_db}dB:d={min_sil}", "-f", "null", "-"],
        capture_output=True,
        text=True,
    )
    spans: list[tuple[float, float]] = []
    start = None
    for line in r.stderr.splitlines():
        if "silence_start:" in line:
            start = float(line.split("silence_start:")[1].split()[0])
        elif "silence_end:" in line and start is not None:
            spans.append((start, float(line.split("silence_end:")[1].split()[0])))
            start = None
    return spans


def plan_punch_cuts(pauses: list[tuple[float, float]], total_dur: float, min_seg: float = 3.0, min_tail: float = 1.0) -> list[float]:
    """Pick up to two cut points (pause midpoints) for hook / body / CTA framing.

    剪辑式推近：只在句间停顿的中点切，不会切断正在说的词。
    - 第 1 刀：第一个离开头 >= min_seg 秒的停顿（钩子句说完）
    - 第 2 刀：最后一个停顿，要求和第 1 刀间隔 >= min_seg、离结尾 >= min_tail（CTA 常常只有 1.5 秒）
    开头/结尾贴边的静音不算停顿。
    """
    mids = [(s + e) / 2 for s, e in pauses if s > 0.05 and e < total_dur - 0.05]
    c1 = next((m for m in mids if m >= min_seg), None)
    if c1 is None:
        return []
    c2 = next((m for m in reversed(mids) if m - c1 >= min_seg and total_dur - m >= min_tail), None)
    return [c1] if c2 is None else [c1, c2]


def punch_zoom_expr(cuts: list[float], total_dur: float, levels: list[float], drift: list[float]) -> str:
    """ffmpeg per-frame zoom factor z(t): each segment starts at levels[i] and drifts by drift[i] over its length."""
    bounds = [0.0, *cuts, total_dur]
    segs = []
    for i in range(len(bounds) - 1):
        a, b = bounds[i], bounds[i + 1]
        lv = levels[min(i, len(levels) - 1)]
        dr = drift[min(i, len(drift) - 1)]
        segs.append((b, f"({lv:.4f}+{dr:.4f}*(t-{a:.3f})/{max(0.1, b - a):.3f})"))
    expr = segs[-1][1]
    for b, e in reversed(segs[:-1]):
        expr = f"if(lt(t,{b:.3f}),{e},{expr})"
    return expr


def detect_hard_cuts(mp4: Path, ratio: float = 10.0, floor: float = 12.0) -> list[float]:
    """H3 有时会自己把一条口播拍成多个镜头（V02 第一版在 5.71s / 9.79s 硬切，换了背景和前景道具）。
    灰度小图逐帧差，超过中位数 ratio 倍且绝对值 > floor 的记为硬切；返回时间点（秒）。"""
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(mp4), "-vf", "scale=96:168,format=gray", "-f", "rawvideo", "-"],
        capture_output=True,
    ).stdout
    n = 96 * 168
    frames = [raw[i : i + n] for i in range(0, len(raw) - n + 1, n)]
    diffs = [sum(abs(a - b) for a, b in zip(f0[::7], f1[::7])) / len(f0[::7]) for f0, f1 in zip(frames, frames[1:])]
    if not diffs:
        return []
    med = sorted(diffs)[len(diffs) // 2]
    fps = 24.0
    return [round((i + 1) / fps, 2) for i, v in enumerate(diffs) if v > max(floor, med * ratio)]


def chunk_words(text: str, max_words: int = 4) -> list[str]:
    words = text.strip().split()
    chunks: list[str] = []
    cur: list[str] = []
    for w in words:
        cur.append(w)
        if len(cur) >= max_words or (len(cur) >= 3 and w.endswith((".", ",", "!", "?", ":"))):
            chunks.append(" ".join(cur))
            cur = []
    if cur:
        chunks.append(" ".join(cur))
    return chunks


def render_hook_overlay(hook_text: str, out_png: Path) -> None:
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    f = load_font(44)
    label = hook_text.upper()
    bbox = draw.textbbox((0, 0), label, font=f)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pad_x, pad_y = 38, 18
    bx0 = (W - tw) // 2 - pad_x
    by0 = 155
    bx1 = (W + tw) // 2 + pad_x
    by1 = by0 + th + pad_y * 2
    draw.rounded_rectangle((bx0, by0, bx1, by1), radius=24, fill=(18, 20, 24, 228), outline=(245, 200, 98, 255), width=4)
    draw.text(((W - tw) // 2, by0 + pad_y - 4), label, font=f, fill=(255, 248, 232, 255))
    im.save(out_png)


def render_caption_overlay(phrase: str, out_png: Path) -> None:
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)
    f = load_font(62)
    text = phrase.strip()
    bbox = draw.textbbox((0, 0), text, font=f, stroke_width=6)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    # Shrink slightly if phrase is very wide
    if tw > W - 120:
        f = load_font(52)
        bbox = draw.textbbox((0, 0), text, font=f, stroke_width=5)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = (W - tw) // 2
    ty = 1380
    # Subtle dark pill backdrop + bold outlined caption
    draw.rounded_rectangle((tx - 26, ty - 14, tx + tw + 26, ty + th + 22), radius=18, fill=(10, 12, 16, 138))
    draw.text((tx, ty), text, font=f, fill=(255, 255, 255, 255), stroke_width=5, stroke_fill=(0, 0, 0, 255))
    im.save(out_png)


def finalize_clip(
    raw_mp4: Path,
    out_mp4: Path,
    spoken_en: str,
    hook_banner: str,
    ext_wav: Path | None = None,
    punch: dict | None = None,
) -> None:
    """Upscale 768x1344 -> 1080x1920, align phrases to speech window, and burn PIL overlays.

    `punch`（influencer_config.json 的 finalize.punch_in）不为空时，按配音的句间停顿切景别：
    钩子句原景别慢推 -> 主体切近 -> CTA 回一点。缩放和放大到 1080x1920 在同一次 scale 里完成，只重采样一次。
    """
    total_dur = probe_duration(raw_mp4)
    t_start, t_end = detect_speech_window(ext_wav if (ext_wav and ext_wav.exists()) else raw_mp4, total_dur)
    chunks = chunk_words(spoken_en, max_words=4)
    total_words = sum(len(c.split()) for c in chunks)
    span = max(0.8, t_end - t_start)

    tmp_dir = Path(tempfile.mkdtemp(prefix="wf10_sub_", dir="/tmp"))
    try:
        overlays: list[tuple[Path, float, float]] = []
        if hook_banner.strip():
            hp = tmp_dir / "hook.png"
            render_hook_overlay(hook_banner, hp)
            overlays.append((hp, 0.0, min(2.45, total_dur)))

        cur_t = t_start
        for idx, ch in enumerate(chunks):
            frac = len(ch.split()) / max(1, total_words)
            dur = span * frac
            nxt_t = t_end if idx == len(chunks) - 1 else min(t_end, cur_t + dur)
            cp = tmp_dir / f"cap_{idx:02d}.png"
            render_caption_overlay(ch, cp)
            overlays.append((cp, cur_t, nxt_t))
            cur_t = nxt_t

        cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(raw_mp4)]
        has_ext_audio = ext_wav is not None and ext_wav.exists()
        if has_ext_audio:
            cmd += ["-i", str(ext_wav)]
        for ov_p, _, _ in overlays:
            cmd += ["-i", str(ov_p)]

        cuts: list[float] = []
        if punch and punch.get("enabled") and has_ext_audio:
            # 停顿和结尾都按配音时长算：H3 视频按 17k+5 帧补齐，比配音长，末尾静音不能当句间停顿
            cuts = plan_punch_cuts(detect_pauses(ext_wav), probe_duration(ext_wav), punch.get("min_seg_sec", 3.0), punch.get("min_tail_sec", 1.0))
        if cuts:
            z = punch_zoom_expr(cuts, total_dur, punch["levels"], punch["drift"])
            ay = punch.get("face_anchor_y", 0.32)
            fc_parts = [
                f"[0:v]scale=w='trunc({W}*({z})/2)*2':h='trunc({H}*({z})/2)*2':eval=frame:flags=lanczos,"
                f"crop={W}:{H}:(iw-{W})/2:(ih-{H})*{ay},setsar=1[v0]"
            ]
            print(f"   ✂️ punch-in cuts at {', '.join(f'{c:.2f}s' for c in cuts)}", flush=True)
        else:
            fc_parts = [f"[0:v]scale={W}:{H}:flags=lanczos,setsar=1[v0]"]
        prev = "v0"
        base_idx = 2 if has_ext_audio else 1
        for k, (_, s_t, e_t) in enumerate(overlays):
            in_lbl = f"[{base_idx + k}:v]"
            out_lbl = f"[v{k + 1}]"
            fc_parts.append(f"[{prev}]{in_lbl}overlay=0:0:enable='between(t,{s_t:.3f},{e_t:.3f})'{out_lbl}")
            prev = f"v{k + 1}"

        out_mp4.parent.mkdir(parents=True, exist_ok=True)
        cmd += [
            "-filter_complex",
            ";".join(fc_parts),
            "-map",
            f"[{prev}]",
            "-map",
            "1:a:0" if has_ext_audio else "0:a?",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "17",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            "-shortest",
            str(out_mp4),
        ]
        subprocess.run(cmd, check=True)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def run_self_test() -> None:
    """0-CCU local smoke test using ref_elias_porch_768x1344.png + synthesized 3.5s tone audio."""
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    # 自测只借用一条脚本的 hook_banner；V3.1 起 E01 已不存在，取第一条
    e01 = next((s for s in manifest["scripts"] if s["id"] == "E01"), manifest["scripts"][0])
    src_img = SAMPLE_DIR / "ref_elias_porch_768x1344.png"
    if not src_img.exists():
        raise FileNotFoundError(f"Self-test requires {src_img}")

    WORK_DIR.mkdir(parents=True, exist_ok=True)
    tmp_raw = WORK_DIR / "_selftest_raw_768x1344.mp4"
    out_mp4 = WORK_DIR / "selftest_elias_E01_1080x1920.mp4"

    # Build a synthetic 3.5s 768x1344 clip with mild audio tone (0.3s..3.2s) to exercise RMS speech-window alignment
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-loop",
            "1",
            "-i",
            str(src_img),
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=220:sample_rate=24000:duration=3.5",
            "-t",
            "3.5",
            "-vf",
            "scale=768:1344,format=yuv420p",
            "-af",
            "volume='if(between(t,0.3,3.2),0.25,0.0)':eval=frame",
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            str(tmp_raw),
        ],
        check=True,
    )

    sample_line = "Morning sun before screens and mineral salt water kept us sharp."
    finalize_clip(tmp_raw, out_mp4, sample_line, e01["hook_banner"])
    tmp_raw.unlink(missing_ok=True)

    res = probe_resolution(out_mp4)
    size_kb = out_mp4.stat().st_size / 1024.0
    assert res == "1080x1920", f"Unexpected output resolution: {res}"
    assert size_kb > 50.0, f"Self-test MP4 too small: {size_kb:.1f} KB"
    print(f"✅ [0-CCU SELF-TEST] {out_mp4.name}: {res} | {size_kb:.1f} KB", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser(description="Workflow 10 Local 0-CCU Subtitle & 1080x1920 Finalizer")
    ap.add_argument("--ids", default="", help="Comma-separated script IDs to finalize")
    ap.add_argument("--self-test", action="store_true", help="Run 0-CCU local FFmpeg + PIL self-test")
    args = ap.parse_args()

    if args.self_test:
        run_self_test()
        return

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    punch_cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8")).get("finalize", {}).get("punch_in")
    sel = {x.strip() for x in args.ids.split(",") if x.strip()} if args.ids else None
    scripts = [s for s in manifest["scripts"] if (not sel or s["id"] in sel)]

    count = 0
    for s in scripts:
        cands = sorted(RAW_DIR.glob(f"AIInf_{s['id']}_*.mp4"), key=lambda p: p.stat().st_mtime)
        if not cands:
            continue
        raw_mp4 = cands[-1]
        cuts_found = detect_hard_cuts(raw_mp4)
        vo_wav = WORK_DIR / "tts" / f"{s['id']}.wav"
        if vo_wav.exists():
            # 只算说话期间的硬切：配音前的开场摆拍、配音结束后的尾帧闪烁都会被 -shortest 截掉或不影响口型
            speech_end = probe_duration(vo_wav) - 0.3
            cuts_found = [c for c in cuts_found if 0.35 < c < speech_end]
        if cuts_found:
            print(f"⚠️ [{s['id']}] H3 素材里有硬切 {cuts_found}（{raw_mp4.name}），建议重跑这一条", flush=True)
        ext_wav = WORK_DIR / "tts" / f"{s['id']}.wav"
        out_mp4 = FINAL_DIR / f"{s['id']}_final_1080x1920.mp4"
        # 脚本级 "punch_in": false = 素材里 H3 自己已经有运镜（如 J01），不再叠加剪辑推近
        punch = punch_cfg if s.get("punch_in", True) else None
        finalize_clip(raw_mp4, out_mp4, s["spoken_en"], s["hook_banner"], ext_wav=ext_wav if ext_wav.exists() else None, punch=punch)
        print(f"✅ Finalized {out_mp4.name} ({out_mp4.stat().st_size / 1e6:.2f} MB)", flush=True)
        count += 1

    if count == 0:
        print(f"⚠️ No raw MP4 files found in {RAW_DIR}. Run run_influencer_video_remote.py first.")


if __name__ == "__main__":
    main()
