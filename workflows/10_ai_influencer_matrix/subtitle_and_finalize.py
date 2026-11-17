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
) -> None:
    """Upscale 768x1344 -> 1080x1920, align phrases to speech window, and burn PIL overlays."""
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
    sel = {x.strip() for x in args.ids.split(",") if x.strip()} if args.ids else None
    scripts = [s for s in manifest["scripts"] if (not sel or s["id"] in sel)]

    count = 0
    for s in scripts:
        cands = sorted(RAW_DIR.glob(f"AIInf_{s['id']}_*.mp4"), key=lambda p: p.stat().st_mtime)
        if not cands:
            continue
        raw_mp4 = cands[-1]
        ext_wav = WORK_DIR / "tts" / f"{s['id']}.wav"
        out_mp4 = FINAL_DIR / f"{s['id']}_final_1080x1920.mp4"
        finalize_clip(raw_mp4, out_mp4, s["spoken_en"], s["hook_banner"], ext_wav=ext_wav if ext_wav.exists() else None)
        print(f"✅ Finalized {out_mp4.name} ({out_mp4.stat().st_size / 1e6:.2f} MB)", flush=True)
        count += 1

    if count == 0:
        print(f"⚠️ No raw MP4 files found in {RAW_DIR}. Run run_influencer_video_remote.py first.")


if __name__ == "__main__":
    main()
