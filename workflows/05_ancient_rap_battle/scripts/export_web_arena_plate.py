#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Export a 9:16 (768x1344) optical-bokeh stage reference plate for makeitrap.com (0 CCU, local CPU).

Why not raw-crop the center of `refs/venue.png`?
  1. `venue.png` (1344x768) has a bare circular stage floor in the lower-center (`x in [0.25, 0.75], y in [0.61, 0.78]`)
     and a DJ figure in the upper-center (`x in [0.43, 0.58]`). Feeding bare stage floor into a 9:16 reference makes
     video models shrink performers into tiny full-body figures or hallucinate extra background performers.
  2. Sharp `f/11` crowd faces create uncanny 10px frozen puppet faces behind close-up singers.

Default `--mode split-wings` isotropically crops the left and right signature arena wings (`sx == sy`, zero stretching,
excluding the central bare stage floor and DJ), cosine-blends the center seam, runs `film_optics.make_bokeh_plate`
(`radius=16, arena_crowd=True`, preserving both warm 2700K practicals and high-chroma electric/neon practicals), and
writes a compact JPEG (`quality=82`, target <= 105 KB) to `makeitrap/apps/tanstack-app/public/template-assets/`.

Usage:
  python3 workflows/05_ancient_rap_battle/scripts/export_web_arena_plate.py \
    workflows/05_ancient_rap_battle/episodes/edison-vs-tesla-redo \
    --slug dynamo-arena

  python3 workflows/05_ancient_rap_battle/scripts/export_web_arena_plate.py \
    workflows/05_ancient_rap_battle/episodes/mozart-vs-salieri \
    --slug vienna-opera-arena
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
import numpy as np
from PIL import Image

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from film_optics import make_bokeh_plate  # noqa: E402

OUT_W, OUT_H = 768, 1344
DEFAULT_WEB_DIR = os.path.abspath(
    os.path.join(SCRIPT_DIR, "../../../../makeitrap/apps/tanstack-app/public/template-assets")
)


def build_isotropic_split_wings(
    im: Image.Image,
    y_range: tuple[float, float] = (0.02, 0.72),
    left_center_x: float = 0.145,
    right_center_x: float = 0.855,
    seam_px: int = 112,
) -> Image.Image:
    """Isotropically crop left & right arena wings (excluding central floor & DJ) into 768x1344."""
    w, h = im.size
    y0 = max(0, int(round(h * y_range[0])))
    y1 = min(h, int(round(h * y_range[1])))
    bh = y1 - y0
    if bh < 64:
        raise ValueError(f"Invalid y_range {y_range} for image height {h}")

    # Scale isotropically so crop height == OUT_H (1344) with zero aspect distortion
    scale = OUT_H / float(bh)
    scaled_w = int(round(w * scale))
    band = im.crop((0, y0, w, y1)).resize((scaled_w, OUT_H), Image.LANCZOS)

    wing_w = (OUT_W + seam_px) // 2  # e.g. (768 + 112) // 2 = 440 px per wing
    lx0 = int(round(scaled_w * left_center_x)) - wing_w // 2
    lx0 = max(0, min(scaled_w - wing_w, lx0))
    rx0 = int(round(scaled_w * right_center_x)) - wing_w // 2
    rx0 = max(0, min(scaled_w - wing_w, rx0))

    left_arr = np.asarray(band.crop((lx0, 0, lx0 + wing_w, OUT_H)), dtype=np.float32)
    right_arr = np.asarray(band.crop((rx0, 0, rx0 + wing_w, OUT_H)), dtype=np.float32)

    out = np.zeros((OUT_H, OUT_W, 3), dtype=np.float32)
    pure_left = wing_w - seam_px  # 328 px
    out[:, :pure_left, :] = left_arr[:, :pure_left, :]
    out[:, pure_left + seam_px :, :] = right_arr[:, seam_px:, :]

    # Cosine cross-fade across the center seam (`[pure_left, pure_left + seam_px)`)
    t = np.linspace(0.0, 1.0, seam_px, dtype=np.float32)[None, :, None]
    alpha = 0.5 - 0.5 * np.cos(np.pi * t)
    seam_left = left_arr[:, pure_left : pure_left + seam_px, :]
    seam_right = right_arr[:, :seam_px, :]
    out[:, pure_left : pure_left + seam_px, :] = seam_left * (1.0 - alpha) + seam_right * alpha

    return Image.fromarray(np.clip(out + 0.5, 0.0, 255.0).astype(np.uint8))


def build_isotropic_center(
    im: Image.Image,
    y_range: tuple[float, float] = (0.16, 0.74),
) -> Image.Image:
    """Isotropic 9:16 eye-level band crop (`y in [0.16, 0.74]`) for single-zone / floorless plates."""
    w, h = im.size
    y0 = max(0, int(round(h * y_range[0])))
    y1 = min(h, int(round(h * y_range[1])))
    bh = y1 - y0
    bw = min(w, int(round(bh * float(OUT_W) / float(OUT_H))))
    x0 = (w - bw) // 2
    return im.crop((x0, y0, x0 + bw, y1)).resize((OUT_W, OUT_H), Image.LANCZOS)


def apply_arena_bokeh_with_practicals(raw_plate: Image.Image, radius: int = 16) -> Image.Image:
    """Run `make_bokeh_plate(radius=16, arena_crowd=True)` while preserving luminous cool electric arcs
    (e.g. Tesla coils) that `cool_window_suppress` would otherwise mistake for daytime windows."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f_in, tempfile.NamedTemporaryFile(
        suffix=".png", delete=False
    ) as f_out:
        in_path, out_path = f_in.name, f_out.name

    try:
        raw_plate.save(in_path)
        make_bokeh_plate(in_path, out_path, radius=radius, arena_crowd=True)
        bokeh_im = Image.open(out_path).convert("RGB")

        # Recover high-intensity electric/violet arc bokeh where B/R chroma & peak luminance indicate
        # self-luminous arcs rather than dull grey-blue daylight windows
        raw_arr = np.asarray(raw_plate, dtype=np.float32) / 255.0
        bokeh_arr = np.asarray(bokeh_im, dtype=np.float32) / 255.0

        # Smooth raw_plate with the same aperture scale for luminous cool-arc glow
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f_arc:
            arc_path = f_arc.name
        try:
            make_bokeh_plate(
                in_path,
                arc_path,
                radius=radius,
                arena_crowd=False,
                exposure=0.55,
                specular_thresh=0.62,
                specular_gain=2.2,
                sat_scale=0.92,
                contrast_scale=0.90,
            )
            arc_bokeh = np.asarray(Image.open(arc_path).convert("RGB"), dtype=np.float32) / 255.0
        finally:
            if os.path.exists(arc_path):
                os.remove(arc_path)

        # Mask: vivid blue/violet arcs (`B > 0.55` and `B - G > 0.10`) blurred via arc_bokeh itself
        arc_strength = np.clip((arc_bokeh[:, :, 2] - 0.36) * 2.4, 0.0, 1.0) * np.clip(
            (arc_bokeh[:, :, 2] - arc_bokeh[:, :, 1] - 0.04) * 3.5, 0.0, 1.0
        )
        yy = np.linspace(0.0, 1.0, OUT_H, dtype=np.float32)[:, None]
        arc_mask = (arc_strength * np.clip(1.15 - 0.8 * yy, 0.0, 1.0))[:, :, None]
        merged = np.clip(bokeh_arr * (1.0 - 0.65 * arc_mask) + np.maximum(bokeh_arr, arc_bokeh) * (0.65 * arc_mask), 0.0, 1.0)
        _ = raw_arr
        return Image.fromarray((merged * 255.0 + 0.5).astype(np.uint8))
    finally:
        for p in (in_path, out_path):
            if os.path.exists(p):
                os.remove(p)


def save_compact_jpeg(im: Image.Image, dst_jpg: str, quality: int = 82, max_bytes: int = 110 * 1024) -> tuple[int, int]:
    """Save progressive optimized JPEG, stepping quality down slightly only if needed to stay <= max_bytes."""
    os.makedirs(os.path.dirname(os.path.abspath(dst_jpg)), exist_ok=True)
    q = quality
    while q >= 68:
        im.save(dst_jpg, format="JPEG", quality=q, optimize=True, progressive=True)
        size = os.path.getsize(dst_jpg)
        if size <= max_bytes:
            return q, size
        q -= 3
    return q, os.path.getsize(dst_jpg)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export 768x1344 optical-bokeh web arena reference plate.")
    parser.add_argument("episode_or_image", help="Episode directory (`episodes/<ep>`) or path to `venue.png`.")
    parser.add_argument("--slug", required=True, help="Output stage id (writes `<slug>-reference.jpg`).")
    parser.add_argument("--out-dir", default=DEFAULT_WEB_DIR, help="Destination `template-assets` directory.")
    parser.add_argument(
        "--mode",
        choices=("split-wings", "center"),
        default="split-wings",
        help="`split-wings` (default): left+right wings without central stage floor/DJ; `center`: y in [0.16, 0.74].",
    )
    parser.add_argument("--radius", type=int, default=16, help="Circular aperture bokeh radius (default: 16).")
    parser.add_argument("--quality", type=int, default=82, help="Initial JPEG quality (default: 82).")
    args = parser.parse_args()

    src = args.episode_or_image
    if os.path.isdir(src):
        src = os.path.join(src, "refs", "venue.png")
    if not os.path.isfile(src):
        raise SystemExit(f"Source venue image not found: {src}")

    im = Image.open(src).convert("RGB")
    raw_plate = build_isotropic_split_wings(im) if args.mode == "split-wings" else build_isotropic_center(im)
    bokeh_plate = apply_arena_bokeh_with_practicals(raw_plate, radius=args.radius)

    file_name = args.slug if args.slug.endswith("-reference") else f"{args.slug}-reference"
    dst_jpg = os.path.join(args.out_dir, f"{file_name}.jpg")
    used_q, size_bytes = save_compact_jpeg(bokeh_plate, dst_jpg, quality=args.quality)
    print(
        f"Exported {dst_jpg} ({OUT_W}x{OUT_H}, quality={used_q}, {size_bytes / 1024:.1f} KB, mode={args.mode})"
    )


if __name__ == "__main__":
    main()
