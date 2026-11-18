#!/usr/bin/env python3
"""08 号：用 Codex 生图（0 CCU）批量出 H3 关键帧。

每个 samples/<dir>/keyframes.json：
    {"style": "<公共风格尾句>",
     "frames": [{"name": "pm_a", "refs": ["../pawmotif/x.jpg"], "prompt": "...", "edit_of": null}, ...]}
- refs / edit_of 相对 keyframes.json 所在目录；edit_of 指向本批已生成的帧名（自动加进参考图，并加「只改动作」的约束）。
- 有 edit_of 的帧会等依赖帧生成完再跑（简单两轮：先跑无依赖的，再跑有依赖的）。
- 产物：<dir>/kf/<name>_raw.png（Codex 原图）+ <name>_768x1344.png（居中裁 9:16 再缩放，H3 直接用）。

用法：
    python3 workflows/08_site_channels/gen_keyframes.py samples/pawmotif_intoframe [--only pm_a,pm_b] [-j 5]
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
W, H = 768, 1344

HEAD = (
    "Use your image generation tool to create ONE image in portrait orientation (1024x1536), then save it in the "
    "current directory as {name}.png (PNG). Never add borders, padding or text. Do not ask questions; just produce the file.\n"
    "Keep every important subject inside the central 80% of the image width (it will be center-cropped to 9:16).\n"
)
EDIT = (
    "The image named {base}.png attached here is the REFERENCE FRAME of the same shot. Produce the next frame of that shot: keep the "
    "exact same camera position, lens, framing, room/location, furniture, props, lighting, color grade, and the exact same "
    "people/animal identity, faces, hair, clothes. Change ONLY what is described below.\n"
)


def crop_9x16(src: Path, dst: Path) -> None:
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


def run_one(fr: dict, base: Path, kf: Path, style: str) -> tuple[str, bool, str]:
    name = fr["name"]
    work = Path(tempfile.mkdtemp(prefix=f"kf_{name}_"))
    refs = [(base / r).resolve() for r in fr.get("refs", [])]
    prompt = HEAD.format(name=name)
    if fr.get("edit_of"):
        b = kf / f"{fr['edit_of']}_raw.png"
        shutil.copy(b, work / f"{fr['edit_of']}.png")
        refs.insert(0, work / f"{fr['edit_of']}.png")
        prompt += EDIT.format(base=fr["edit_of"])
    prompt += fr["prompt"].strip() + "\n" + style.strip() + "\nNo text, no captions, no watermark, no logo."
    (work / "prompt.txt").write_text(prompt, encoding="utf-8")
    cmd = ["codex", "exec", "--skip-git-repo-check", "-C", str(work), "-s", "workspace-write", "-o", str(work / "last.txt")]
    for r in refs:
        cmd += ["-i", str(r)]
    cmd += ["--", prompt]
    p = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=1200)
    out = work / f"{name}.png"
    if not out.exists():
        cands = sorted(work.glob("*.png"), key=lambda q: q.stat().st_mtime)
        cands = [c for c in cands if c.name != f"{fr.get('edit_of')}.png"]
        out = cands[-1] if cands else out
    if not out.exists():
        return name, False, f"rc={p.returncode} no png; tail: {(p.stdout + p.stderr)[-400:]} (work={work})"
    shutil.copy(out, kf / f"{name}_raw.png")
    crop_9x16(out, kf / f"{name}_768x1344.png")
    return name, True, str(Image.open(out).size)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--only", default=None)
    ap.add_argument("-j", type=int, default=5)
    args = ap.parse_args()
    base = Path(args.dir)
    base = (base if base.is_absolute() else HERE / base).resolve()
    spec = json.loads((base / "keyframes.json").read_text(encoding="utf-8"))
    kf = base / "kf"
    kf.mkdir(exist_ok=True)
    frames = spec["frames"]
    if args.only:
        keep = {x.strip() for x in args.only.split(",")}
        frames = [f for f in frames if f["name"] in keep]
    rounds = [[f for f in frames if not f.get("edit_of")], [f for f in frames if f.get("edit_of")]]
    ok = True
    for rnd in rounds:
        if not rnd:
            continue
        with ThreadPoolExecutor(max_workers=args.j) as ex:
            for name, good, msg in ex.map(lambda f: run_one(f, base, kf, spec.get("style", "")), rnd):
                print(f"{'✅' if good else '❌'} {name}: {msg}", flush=True)
                ok &= good
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
