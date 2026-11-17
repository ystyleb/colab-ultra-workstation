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


def crop_9x16(src: Path, dst: Path) -> None:
    """Center-crop and resize raw portrait image to exact 768x1344 9:16 frame."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    im = Image.open(src).convert("RGB")
    w, h = im.size
    tw = round(h * W / H)
    if tw <= w:
        x0 = (w - tw) // 2
        im = im.crop((x0, 0, x0 + tw, h))
    else:
        th = round(w * H / W)
        y0 = (h - th) // 2
        im = im.crop((0, y0, w, y0 + th))
    im.resize((W, H), Image.LANCZOS).save(dst)


def run_one(fr: dict, style: str) -> tuple[str, bool, str]:
    """Invoke codex exec inside an isolated temp directory to produce one keyframe."""
    name = fr["name"]
    work = Path(tempfile.mkdtemp(prefix=f"kf10_{name}_"))
    refs: list[Path] = []
    prompt = HEAD_PROMPT.format(name=name)

    dep_name = fr.get("identity_of")
    if dep_name:
        dep_raw = WORK_DIR / f"{dep_name}_raw.png"
        if not dep_raw.exists():
            return name, False, f"missing dependency raw image: {dep_raw}"
        dep_copy = work / f"{dep_name}.png"
        shutil.copy2(dep_raw, dep_copy)
        refs.append(dep_copy)
        prompt += IDENTITY_PROMPT.format(base=dep_name)

    prompt += fr["prompt"].strip() + "\n" + style.strip()
    prompt += "\nNo text, no captions, no watermarks, no brand logos, no split screen."
    (work / "prompt.txt").write_text(prompt, encoding="utf-8")

    cmd = [
        "codex",
        "exec",
        "--skip-git-repo-check",
        "-C",
        str(work),
        "-s",
        "workspace-write",
        "-o",
        str(work / "last.txt"),
    ]
    for r in refs:
        cmd += ["-i", str(r)]
    cmd += ["--", prompt]

    p = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=1200)
    out = work / f"{name}.png"
    if not out.exists():
        cands = sorted(work.glob("*.png"), key=lambda q: q.stat().st_mtime)
        if dep_name:
            cands = [c for c in cands if c.name != f"{dep_name}.png"]
        out = cands[-1] if cands else out
    if not out.exists():
        return name, False, f"rc={p.returncode} no png; tail: {(p.stdout + p.stderr)[-500:]}"

    WORK_DIR.mkdir(parents=True, exist_ok=True)
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    raw_dst = WORK_DIR / f"{name}_raw.png"
    final_dst = SAMPLE_DIR / f"{name}_768x1344.png"
    shutil.copy2(out, raw_dst)
    crop_9x16(out, final_dst)
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
            dep = f.get("identity_of")
            if not dep or dep in planned or (dep not in pending_names and (WORK_DIR / f"{dep}_raw.png").exists()):
                batch.append(f)
            else:
                next_pending.append(f)
        if not batch:
            missing = [(f["name"], f.get("identity_of")) for f in pending]
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
    args = ap.parse_args()

    spec = json.loads(Path(args.spec).resolve().read_text(encoding="utf-8"))
    frames = spec["frames"]

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
