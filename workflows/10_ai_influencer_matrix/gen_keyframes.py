#!/usr/bin/env python3
"""10 AI Influencer Matrix: 0-CCU Local Codex Talking-Head Keyframe Generator.

Generates 6 standardized 768x1344 portrait reference anchors (3 personas x 2 scenes):
- Round 1: independent base portraits (ref_elias_porch, ref_vivian_jet, ref_sienna_podcast)
- Round 2: identity-locked secondary scene portraits via `identity_of`
- Outputs raw 1024x1536 images to `work/<name>_raw.png` (gitignored)
- Outputs cropped 768x1344 anchors to `sample_inputs/<name>_768x1344.png` (tracked)
- Outputs 3x2 inspection board to `out/personas_keyframes_preview.jpg` (gitignored)
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
WORK_DIR = HERE / "work"
SAMPLE_DIR = HERE / "sample_inputs"
OUT_DIR = HERE / "out"
W, H = 768, 1344

HEAD_PROMPT = (
    "Use your image generation tool to create ONE photorealistic live-action 35mm cinema portrait in vertical 2:3 orientation (1024x1536), "
    "then save it in the current directory as {name}.png (PNG). Never add borders, padding, frames, text, subtitles, or watermarks. "
    "Do not ask questions; just produce the file.\n"
    "MANDATORY TALKING-HEAD FRAMING RULES (CRITICAL FOR VIDEO LIP-SYNC):\n"
    "1. CHEST-UP MEDIUM CLOSE-UP (MCU): Center the subject comfortably within the middle 75% of the width so center-cropping to 9:16 never cuts off ears or shoulders.\n"
    "2. CLEAN HEADROOM: Leave 18-22% open background above the crown of the head so top hook banners never touch the forehead.\n"
    "3. DIRECT CAMERA EYE CONTACT: Eyes must look straight at eye-level into the camera lens.\n"
    "4. 100% UNOBSTRUCTED MOUTH & JAWLINE: Mouth gently closed in a calm, poised natural expression. Keep hands, cups, hair, and microphones completely BELOW collarbone height and NEVER crossing the chin, lips, or mouth corners.\n"
)

IDENTITY_PROMPT = (
    "The attached image {base}.png is the FACE, BONE STRUCTURE, EYE, HAIR & AGE IDENTITY REFERENCE ONLY. "
    "Create a brand-new photorealistic 35mm cinema chest-up medium close-up of this EXACT SAME person "
    "(preserve 100% of their exact facial bone structure, nose, lips, eye color, eyebrows, age lines, natural skin pores, and hair color/texture). "
    "COMPLETELY DISCARD the clothing, background location, and lighting from {base}.png and place them into the new outfit and scene below.\n"
)


def crop_9x16(src: Path, dst: Path, tight: dict | None = None) -> None:
    """Center-crop and resize raw portrait image to exact 768x1344 9:16 frame.

    `tight` = {"height_frac": 0.72, "cx": 0.56, "top": 0.10}：先按高度比例裁一个更紧的 9:16 框
    （cx 为框中心的横向位置，top 为框顶的纵向位置），再放大到 768x1344。原图 1024x1536 时 0.72 只放大约 1.2 倍。
    """
    dst.parent.mkdir(parents=True, exist_ok=True)
    im = Image.open(src).convert("RGB")
    w, h = im.size
    if tight:
        ch = int(h * tight["height_frac"])
        cw = int(ch * W / H)
        x0 = min(max(int(w * tight.get("cx", 0.5) - cw / 2), 0), w - cw)
        y0 = min(max(int(h * tight.get("top", 0.0)), 0), h - ch)
        im.crop((x0, y0, x0 + cw, y0 + ch)).resize((W, H), Image.LANCZOS).save(dst)
        return
    tw = round(h * W / H)
    if tw <= w:
        x0 = (w - tw) // 2
        im = im.crop((x0, 0, x0 + tw, h))
    else:
        th = round(w * H / W)
        y0 = (h - th) // 2
        im = im.crop((0, y0, w, y0 + th))
    im.resize((W, H), Image.LANCZOS).save(dst)


# ---- 分层参考图（铁律 H，2026-11-18）：人物三视图 + 空环境图 -> edit_of 合成中景关键帧 ----
TURNAROUND_PROMPT = (
    "Use your image generation tool to create ONE photorealistic character reference sheet in landscape 3:2 orientation "
    "(1536x1024), then save it in the current directory as {name}.png (PNG). Do not ask questions; just produce the file.\n"
    "Three full-body views of the SAME person side by side on a plain light-grey studio backdrop with even soft light: "
    "LEFT = front view, MIDDLE = exact 90-degree profile, RIGHT = back view. Neutral relaxed standing pose, arms hanging "
    "naturally, hands empty, head and body always facing the same direction as the feet, calm neutral closed-mouth face. "
    "No props, no gestures, no head turns, no text, no labels, no borders.\n"
    "The attached {ident}.png is the identity reference: preserve EXACTLY the face, bone structure, eye color, skin, age "
    "lines, hairstyle and hair color, makeup and jewelry. Ignore its background, framing and pose.\n"
)
PLATE_PROMPT = (
    "Use your image generation tool to create ONE photorealistic empty-location photograph in vertical 2:3 orientation "
    "(1024x1536), then save it in the current directory as {name}.png (PNG). Do not ask questions; just produce the file.\n"
    "ABSOLUTELY NO PEOPLE: no person, no body parts, no hands, no reflections of people, no mannequins.\n"
    "{ref_line}"
)
COMPOSE_PROMPT = (
    "Use your image generation tool to create ONE photorealistic live-action 35mm cinema frame in vertical 2:3 orientation "
    "(1024x1536), then save it in the current directory as {name}.png (PNG). Do not ask questions; just produce the file.\n"
    "EDIT the attached {plate}.png: keep the camera position, lens, framing, room, furniture, every prop and the lighting "
    "EXACTLY as they are; only add ONE person into the open space left for them.\n"
    "That person is the one shown in the attached character sheet {sheet}.png: preserve EXACTLY their face, bone structure, "
    "eye color, skin, age lines, hairstyle, hair color, makeup and jewelry. Clothing is specified below and replaces the "
    "sheet's clothing if different.\n"
    "TALKING-HEAD RULES: medium shot (waist-up) with the person centered and 15-20% headroom; eyes look straight into the "
    "lens at eye level; mouth gently closed, lips and jawline 100% unobstructed; hands stay low on the furniture, far "
    "below the chin.\n"
)


def _attach(work: Path, dep: str) -> Path | None:
    src = WORK_DIR / f"{dep}_raw.png"
    if not src.exists():
        return None
    dst = work / f"{dep}.png"
    shutil.copy2(src, dst)
    return dst


def frame_deps(fr: dict) -> list[str]:
    deps = [fr.get("identity_of"), fr.get("edit_of"), fr.get("sheet_of"), fr.get("plate_ref")]
    return [d for d in deps if d]


def run_one(fr: dict, style: str) -> tuple[str, bool, str]:
    """Invoke codex exec inside an isolated temp directory to produce one image.

    kind = "portrait"（默认，旧版胸像关键帧）| "turnaround"（三视图）| "plate"（空环境图）| "composite"（环境图 + 三视图合成）
    """
    name = fr["name"]
    kind = fr.get("kind", "portrait")
    work = Path(tempfile.mkdtemp(prefix=f"kf10_{name}_"))
    refs: list[Path] = []
    for dep in frame_deps(fr):
        a = _attach(work, dep)
        if a is None:
            return name, False, f"missing dependency raw image: {WORK_DIR / (dep + '_raw.png')}"
        refs.append(a)

    if kind == "turnaround":
        prompt = TURNAROUND_PROMPT.format(name=name, ident=fr["identity_of"])
    elif kind == "plate":
        ref_line = ""
        if fr.get("plate_ref"):
            ref_line = (f"The attached {fr['plate_ref']}.png shows this location with a person in it. Use it ONLY as a reference "
                        "for the room's look, materials, palette and light; re-shoot the room EMPTY from the camera described "
                        "below. Do not keep any part of the person.\n")
        prompt = PLATE_PROMPT.format(name=name, ref_line=ref_line)
    elif kind == "composite":
        prompt = COMPOSE_PROMPT.format(name=name, plate=fr["edit_of"], sheet=fr["sheet_of"])
    else:
        prompt = HEAD_PROMPT.format(name=name)
        if fr.get("identity_of"):
            prompt += IDENTITY_PROMPT.format(base=fr["identity_of"])

    prompt += fr["prompt"].strip() + "\n" + style.strip()
    prompt += "\nNo text, no captions, no watermarks, no brand logos, no split screen."
    (work / "prompt.txt").write_text(prompt, encoding="utf-8")

    cmd = ["codex", "exec", "--skip-git-repo-check", "-C", str(work), "-s", "workspace-write", "-o", str(work / "last.txt")]
    for r in refs:
        cmd += ["-i", str(r)]
    cmd += ["--", prompt]

    p = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=1200)
    out = work / f"{name}.png"
    if not out.exists():
        ref_names = {r.name for r in refs}
        cands = [c for c in sorted(work.glob("*.png"), key=lambda q: q.stat().st_mtime) if c.name not in ref_names]
        out = cands[-1] if cands else out
    if not out.exists():
        return name, False, f"rc={p.returncode} no png; tail: {(p.stdout + p.stderr)[-500:]}"

    WORK_DIR.mkdir(parents=True, exist_ok=True)
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    raw_dst = WORK_DIR / f"{name}_raw.png"
    shutil.copy2(out, raw_dst)
    if kind == "turnaround":  # 三视图不裁 9:16，原样留作参考
        final_dst = SAMPLE_DIR / f"{name}.png"
        shutil.copy2(out, final_dst)
        return name, True, f"sheet={Image.open(final_dst).size}"
    final_dst = SAMPLE_DIR / f"{name}_768x1344.png"
    crop_9x16(out, final_dst, fr.get("tight_crop"))
    return name, True, f"raw={Image.open(raw_dst).size} -> 9:16={Image.open(final_dst).size}"


def build_preview_grid(frames: list[dict]) -> Path | None:
    """Create a 3x2 visual inspection contact sheet (3 personas x 2 scenes)."""
    by_persona: dict[str, list[tuple[str, Path]]] = {}
    for fr in frames:
        p = SAMPLE_DIR / f"{fr['name']}_768x1344.png"
        if p.exists():
            by_persona.setdefault(fr["persona"], []).append((fr["scene"], p))
    rows = [(pk, items) for pk, items in by_persona.items() if items]
    if not rows:
        return None

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cw, ch = 384, 672
    pad = 24
    hdr = 44
    cols = max(len(items) for _, items in rows)
    canvas = Image.new("RGB", (pad * (cols + 1) + cw * cols, pad + len(rows) * (ch + hdr + pad)), (18, 19, 22))
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 22)
    except Exception:
        font = ImageFont.load_default()

    for r_idx, (pk, items) in enumerate(rows):
        y0 = pad + r_idx * (ch + hdr + pad)
        labels = "  vs  ".join(sc.upper() for sc, _ in items)
        draw.text((pad, y0 + 8), f"{pk.upper()}  |  {labels}", fill=(242, 232, 210), font=font)
        for c_idx, (sc, path) in enumerate(items):
            x0 = pad + c_idx * (cw + pad)
            im = Image.open(path).convert("RGB").resize((cw, ch), Image.LANCZOS)
            canvas.paste(im, (x0, y0 + hdr))
            draw.rectangle((x0 + 12, y0 + hdr + 12, x0 + 150, y0 + hdr + 44), fill=(15, 16, 20))
            draw.text((x0 + 20, y0 + hdr + 16), sc.upper(), fill=(255, 220, 120), font=font)

    out_path = OUT_DIR / "personas_keyframes_preview.jpg"
    canvas.save(out_path, quality=92)
    return out_path


def topo_rounds(frames: list[dict], only_set: set[str] | None, skip_existing: bool) -> list[list[dict]]:
    """Order frames by dependency rounds so `identity_of` waits for base portraits."""
    selected = [f for f in frames if (not only_set or f["name"] in only_set)]
    if skip_existing:
        selected = [
            f
            for f in selected
            if not ((WORK_DIR / f"{f['name']}_raw.png").exists() and (SAMPLE_DIR / f"{f['name']}_768x1344.png").exists())
        ]
    pending = list(selected)
    planned: set[str] = set()
    rounds: list[list[dict]] = []

    while pending:
        batch: list[dict] = []
        next_pending: list[dict] = []
        pending_names = {f["name"] for f in pending}
        for f in pending:
            if all(dep in planned or (dep not in pending_names and (WORK_DIR / f"{dep}_raw.png").exists()) for dep in frame_deps(f)):
                batch.append(f)
            else:
                next_pending.append(f)
        if not batch:
            missing = [(f["name"], frame_deps(f)) for f in pending]
            raise RuntimeError(f"❌ Unresolved keyframe dependency: {missing}")
        rounds.append(batch)
        planned.update(f["name"] for f in batch)
        pending = next_pending
    return rounds


def main() -> None:
    ap = argparse.ArgumentParser(description="10 AI Influencer Matrix: 0-CCU Codex Keyframe Generator")
    ap.add_argument("--spec", default=str(HERE / "keyframes.json"))
    ap.add_argument("--only", default=None, help="Comma-separated frame names to regenerate")
    ap.add_argument("-j", "--jobs", type=int, default=3, help="Max parallel codex executions per round")
    ap.add_argument("--skip-existing", action="store_true", help="Skip existing frames in work/ and sample_inputs/")
    ap.add_argument("--preview-only", action="store_true", help="Only rebuild out/personas_keyframes_preview.jpg")
    ap.add_argument("--crop-only", action="store_true", help="0 次出图：按规范从 work/*_raw.png 重新裁 sample_inputs（配合 --only）")
    args = ap.parse_args()

    spec = json.loads(Path(args.spec).resolve().read_text(encoding="utf-8"))
    frames = spec["frames"]

    if args.crop_only:
        only = {x.strip() for x in args.only.split(",") if x.strip()} if args.only else None
        for fr in frames:
            if (only and fr["name"] not in only) or fr.get("kind") == "turnaround":
                continue
            raw = WORK_DIR / f"{fr['name']}_raw.png"
            if raw.exists():
                crop_9x16(raw, SAMPLE_DIR / f"{fr['name']}_768x1344.png", fr.get("tight_crop"))
                print(f"✂️ {fr['name']}: {fr.get('tight_crop') or 'center'}")
        return

    if args.preview_only:
        grid = build_preview_grid(frames)
        print(f"🖼️ 预览图已更新: {grid}" if grid else "⚠️ 尚无完整关键帧可供拼图。")
        return

    only_set = {x.strip() for x in args.only.split(",") if x.strip()} if args.only else None
    rounds = topo_rounds(frames, only_set=only_set, skip_existing=args.skip_existing)

    ok = True
    for r_idx, rnd in enumerate(rounds, 1):
        print(f"\n🎨 [Round {r_idx}/{len(rounds)}] 并发生成 {len(rnd)} 张关键帧 (-j {args.jobs})...", flush=True)
        with ThreadPoolExecutor(max_workers=args.jobs) as ex:
            for name, good, msg in ex.map(lambda f: run_one(f, spec.get("style", "")), rnd):
                print(f"{'✅' if good else '❌'} {name}: {msg}", flush=True)
                ok &= good

    grid = build_preview_grid(frames)
    if grid:
        print(f"\n🖼️ 人设三组双场景对比总览图: {grid}", flush=True)
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
