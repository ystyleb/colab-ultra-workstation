#!/usr/bin/env python3
"""08 号：用 Codex 生图（0 CCU）批量出 H3 关键帧。

每个 samples/<dir>/keyframes.json：
    {"style": "<公共风格尾句>",
     "frames": [{"name": "pm_a", "refs": ["../pawmotif/x.jpg"], "prompt": "...", "edit_of": null}, ...]}
- refs / edit_of 相对 keyframes.json 所在目录；edit_of 指向本批已生成的帧名（自动加进参考图，并加「只改动作」的约束）。
- 依赖（edit_of，以及 refs 里指向本批 kf/<name>_raw.png 的图）按层级排序：一层生成完再跑下一层，层数不限。
- "aspect": "9:16"（默认）或 "16:9"（横版长视频）。
- 产物：<dir>/kf/<name>_raw.png（Codex 原图）+ <name>_768x1344.png 或 <name>_1344x768.png（居中裁切再缩放，H3 直接用）。

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
SIZES = {"9:16": (768, 1344), "16:9": (1344, 768)}

HEADS = {
    "9:16": (
        "Use your image generation tool to create ONE image in portrait orientation (1024x1536), then save it in the "
        "current directory as {name}.png (PNG). Never add borders, padding or text. Do not ask questions; just produce the file.\n"
        "Keep every important subject inside the central 80% of the image width (it will be center-cropped to 9:16).\n"
    ),
    "16:9": (
        "Use your image generation tool to create ONE image in landscape orientation (1536x1024), then save it in the "
        "current directory as {name}.png (PNG). Never add borders, padding or text. Do not ask questions; just produce the file.\n"
        "Keep every important subject inside the central 85% of the image height (it will be center-cropped to 16:9).\n"
    ),
}
EDIT = (
    "The image named {base}.png attached here is the REFERENCE FRAME of the same shot. Produce the next frame of that shot: keep the "
    "exact same camera position, lens, framing, room/location, furniture, props, lighting, color grade, and the exact same "
    "people/animal identity, faces, hair, clothes. Change ONLY what is described below.\n"
)


def crop_to(src: Path, dst: Path, W: int, H: int) -> None:
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


def run_one(fr: dict, base: Path, kf: Path, style: str, aspect: str = "9:16") -> tuple[str, bool, str]:
    name = fr["name"]
    work = Path(tempfile.mkdtemp(prefix=f"kf_{name}_"))
    refs = [(base / r).resolve() for r in fr.get("refs", [])]
    prompt = HEADS[aspect].format(name=name)
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
    W, H = SIZES[aspect]
    crop_to(out, kf / f"{name}_{W}x{H}.png", W, H)
    return name, True, str(Image.open(out).size)


def deps_of(fr: dict) -> set[str]:
    """本帧依赖的本批帧名：edit_of + refs 里的 kf/<name>_raw.png。"""
    d = {fr["edit_of"]} if fr.get("edit_of") else set()
    for r in fr.get("refs", []):
        p = Path(r)
        if p.parent.name == "kf" and p.name.endswith("_raw.png"):
            d.add(p.name[: -len("_raw.png")])
    return d


def levels(frames: list[dict]) -> list[list[dict]]:
    """按依赖分层；依赖不在本次运行（--only）里的帧视为已生成。"""
    names = {f["name"] for f in frames}
    done: set[str] = set()
    todo = list(frames)
    out = []
    while todo:
        rnd = [f for f in todo if (deps_of(f) & names) <= done]
        if not rnd:
            raise SystemExit(f"关键帧依赖成环：{[f['name'] for f in todo]}")
        out.append(rnd)
        done |= {f["name"] for f in rnd}
        todo = [f for f in todo if f["name"] not in done]
    return out


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
    aspect = spec.get("aspect", "9:16")
    rounds = levels(frames)
    ok = True
    for rnd in rounds:
        if not rnd:
            continue
        with ThreadPoolExecutor(max_workers=args.j) as ex:
            for name, good, msg in ex.map(lambda f: run_one(f, base, kf, spec.get("style", ""), aspect), rnd):
                print(f"{'✅' if good else '❌'} {name}: {msg}", flush=True)
                ok &= good
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
