# -*- coding: utf-8 -*-
"""Optical & Film-Science utilities for Workflow 05 (Ancient/Historical Rap Battle).

Eliminates synthetic/digital ("AI CG") artifacts at two stages (both 0 CCU on local Mac):
1. Pre-generation reference conditioning:
   - `make_bokeh_plate`: applies linear-light specular highlight expansion + circular aperture disk convolution
     + atmospheric perspective to `stage_a.png` / `stage_b.png`, preventing H3's attention from pasting
     razor-sharp miniature puppet crowds behind close-up singers while optionally preserving recognizable
     cheering crowd silhouettes (`arena_crowd=True`, `radius=16`, Cooke T2.2 shallow DOF).
   - `condition_char_ref`: balances portrait references (`a_face_clean.png`, `b_face_clean.png`) into a natural
     warm 3200K tungsten-key + 5600K silver-rim 35mm cinema gamut (with optional `warm_skin_boost`).
2. Post-generation Kodak Vision3 500T / Tiffen Black Pro-Mist 1/8 film emulation (V3 Crisp Warm):
   - `film_grade_filter`: single-pass Lanczos supersampled resize -> subtle pre-bloom acutance -> Pro-Mist 1/8
     thresholded highlight halation (`0.08`, threshold `0.76`) -> tight solid Vision3 S-curve (`0 -> 0.034`,
     zero milky veil) -> warm midtone skin recovery -> ultra-fine luma-only silver grain (`c0s=3:c1s=0:c2s=0`).
"""
from __future__ import annotations

import numpy as np
from numpy.fft import irfft2, rfft2
from PIL import Image, ImageFilter


def make_bokeh_plate(
    src_path: str,
    dst_path: str,
    radius: int = 10,
    specular_thresh: float = 0.56,
    specular_gain: float = 2.6,
    sat_scale: float = 0.80,
    contrast_scale: float = 0.88,
    exposure: float = 0.85,
    dark_concert: bool = False,
    arena_crowd: bool = False,
    haze_lift: tuple[float, float, float] = (0.015, 0.016, 0.020),
) -> str:
    """Convert an f/11 sharp stage background plate into an optical-bokeh cinema plate.

    Modes:
      - `arena_crowd=True` (V3 recommended): `radius=16` (Cooke T2.2 shallow DOF) melts 10px uncanny facial
        features while preserving recognizable cheering scholar silhouettes, raised arms, oak gallery tiers,
        and warm 2700K candle chandelier bokeh orbs; darkens only the bright upper ceiling so faces pop cleanly.
      - `dark_concert=True` (V2 legacy): heavier night-arena vignette for ultra-dark concert isolation.
    """
    im = Image.open(src_path).convert("RGB")
    h, w = im.height, im.width
    arr = np.asarray(im, dtype=np.float32) / 255.0

    # 1. Convert sRGB -> linear light, apply spatial exposure mask, and boost warm practical lamps/candles
    linear = np.power(np.clip(arr, 0.0, 1.0), 2.4)
    yy_norm, xx_norm = np.meshgrid(
        np.linspace(0.0, 1.0, h, dtype=np.float32),
        np.linspace(-1.0, 1.0, w, dtype=np.float32),
        indexing="ij",
    )
    if arena_crowd:
        # Suppress cool daylight window panes so night-time underground arena mood holds, while boosting warm 2700K candles
        warm_weight = np.clip((arr[:, :, 0] - arr[:, :, 2] * 0.88) * 3.5, 0.04, 1.0)[:, :, None]
        cool_window_suppress = np.where(
            (arr[:, :, 2] > arr[:, :, 0] * 1.02) & (yy_norm < 0.62), 0.28, 1.0
        )[:, :, None].astype(np.float32)
        specular = np.maximum(0.0, linear - specular_thresh) * specular_gain * warm_weight
        # Keep upper walls dark moody oak/smoke behind the singer's rim-lit head (yy=0 -> 0.13)
        # while keeping lower cheering scholar silhouettes & raised arms clearly readable (yy=1 -> 0.66)
        amb_mask = (0.13 + 0.53 * np.power(yy_norm, 1.15)) * np.clip(1.0 - 0.28 * (xx_norm * xx_norm), 0.58, 1.0)
        boosted = linear * (exposure * amb_mask[:, :, None] * cool_window_suppress) + specular
    elif dark_concert:
        warm_weight = np.clip((arr[:, :, 0] - arr[:, :, 2] * 0.92) * 3.5, 0.05, 1.0)[:, :, None]
        specular = np.maximum(0.0, linear - specular_thresh) * specular_gain * warm_weight
        amb_mask = (0.12 + 0.16 * yy_norm) * np.clip(1.0 - 0.35 * (xx_norm * xx_norm), 0.5, 1.0)
        boosted = linear * (exposure * amb_mask[:, :, None]) + specular
    else:
        specular = np.maximum(0.0, linear - specular_thresh) * specular_gain
        boosted = linear * exposure + specular

    # 2. Circular aperture disk kernel convolution via FFT with edge padding
    r = max(2, int(round(radius * min(w, h) / 1024.0)))
    yy, xx = np.ogrid[-r : r + 1, -r : r + 1]
    disk = ((xx * xx + yy * yy) <= r * r).astype(np.float32)
    disk /= disk.sum()

    pad_h, pad_w = h + 2 * r, w + 2 * r
    k_pad = np.zeros((pad_h, pad_w), dtype=np.float32)
    k_pad[: 2 * r + 1, : 2 * r + 1] = disk
    k_fft = rfft2(k_pad)

    bokeh_lin = np.zeros_like(boosted)
    for ch in range(3):
        padded = np.pad(boosted[:, :, ch], r, mode="edge")
        conv = irfft2(rfft2(padded) * k_fft, s=(pad_h, pad_w))[2 * r : 2 * r + h, 2 * r : 2 * r + w]
        bokeh_lin[:, :, ch] = np.clip(conv, 0.0, 1.0)

    srgb = np.power(np.clip(bokeh_lin, 0.0, 1.0), 1.0 / 2.4)

    # 3. Atmospheric perspective: controlled saturation & contrast, tight solid black floor (no milky grey sheet)
    lum = (0.2126 * srgb[:, :, 0] + 0.7152 * srgb[:, :, 1] + 0.0722 * srgb[:, :, 2])[:, :, None]
    desat = lum + (srgb - lum) * sat_scale
    hazy = desat * contrast_scale + np.asarray(haze_lift, dtype=np.float32)[None, None, :]
    if arena_crowd:
        # Subtle 5600K overhead back-spotlight beam at top-center + warm amber lower stage bounce
        cone_w = 0.22 + 0.42 * yy_norm
        cone = np.exp(-0.5 * (xx_norm / cone_w) ** 2) * (1.0 - 0.72 * yy_norm) ** 1.6
        hazy = hazy + cone[:, :, None] * np.asarray([0.08, 0.09, 0.11], dtype=np.float32)[None, None, :]
    elif dark_concert:
        cone_w = 0.20 + 0.38 * yy_norm
        cone = np.exp(-0.5 * (xx_norm / cone_w) ** 2) * (1.0 - 0.62 * yy_norm) ** 1.4
        hazy = hazy + cone[:, :, None] * np.asarray([0.15, 0.17, 0.19], dtype=np.float32)[None, None, :]
    hazy = np.clip(hazy, 0.0, 1.0)

    out_im = Image.fromarray((hazy * 255.0 + 0.5).astype(np.uint8))
    out_im.save(dst_path)
    return dst_path


def condition_char_ref(
    src_path: str,
    dst_path: str,
    max_sat_mean: float = 0.35,
    min_sat_mean: float = 0.0,
    warm_skin_boost: float = 0.0,
    toe_lift: float = 0.012,
    soften_px: float = 0.30,
) -> str:
    """Ensure a character portrait reference sits in a natural live-action 35mm gamut.

    When `warm_skin_boost > 0` (e.g. `0.15`), gently warms midtone skin/fabric toward 3200K tungsten blood-warmth
    while leaving deep blacks (`lum -> 0`) solid and 5600K silver hair rim highlights (`lum -> 1`) crisp cool-white.
    """
    im = Image.open(src_path).convert("RGB")
    if soften_px > 0:
        soft = im.filter(ImageFilter.GaussianBlur(soften_px))
        im = Image.blend(im, soft, 0.22)

    arr = np.asarray(im, dtype=np.float32) / 255.0
    lum = (0.2126 * arr[:, :, 0] + 0.7152 * arr[:, :, 1] + 0.0722 * arr[:, :, 2])[:, :, None]

    if warm_skin_boost > 0.0:
        # Bell-shaped midtone mask peaking at lum=0.45 so shadows stay solid dark and 5600K rim highlights stay silver-white
        mid_w = np.power(np.clip(4.0 * lum * (1.0 - lum), 0.0, 1.0), 1.15)
        warm_mul = np.concatenate(
            [
                1.0 + warm_skin_boost * 0.90 * mid_w,
                1.0 + warm_skin_boost * 0.16 * mid_w,
                1.0 - warm_skin_boost * 0.80 * mid_w,
            ],
            axis=2,
        )
        arr = np.clip(arr * warm_mul, 0.0, 1.0)
        lum = (0.2126 * arr[:, :, 0] + 0.7152 * arr[:, :, 1] + 0.0722 * arr[:, :, 2])[:, :, None]

    mx = np.max(arr, axis=2)
    mn = np.min(arr, axis=2)
    sat = np.where(mx > 1e-3, (mx - mn) / np.maximum(mx, 1e-3), 0.0)
    cur_sat = float(np.mean(sat))

    if cur_sat > max_sat_mean:
        scale = max(0.62, max_sat_mean / cur_sat)
        arr = lum + (arr - lum) * scale
    elif min_sat_mean > 0.0 and 1e-3 < cur_sat < min_sat_mean:
        scale = min(1.35, min_sat_mean / cur_sat)
        mid_mask = np.clip(4.0 * lum * (1.0 - lum), 0.25, 1.0)
        arr = lum + (arr - lum) * (1.0 + (scale - 1.0) * mid_mask)

    # Gentle highlight shoulder roll-off + tight cinema shadow toe (no grey haze)
    arr = arr / (1.0 + 0.08 * np.maximum(0.0, arr - 0.76))
    arr = np.clip(arr * (1.0 - toe_lift) + toe_lift, 0.0, 1.0)

    out_im = Image.fromarray((arr * 255.0 + 0.5).astype(np.uint8))
    out_im.save(dst_path)
    return dst_path


def film_grade_filter(
    in_label: str,
    out_label: str,
    target_size: tuple[int, int] | None = None,
    halation: float = 0.08,
    sat: float = 0.85,
    luma_grain: int = 3,
) -> str:
    """Build an FFmpeg filtergraph chain emulating Kodak Vision3 500T + Tiffen Black Pro-Mist 1/8 + fine 35mm luma grain.

    V3 Crisp Warm Cinema Calibration:
      1. Optional clean Lanczos supersampled resize to final delivery resolution FIRST (e.g. 2688x1536 -> 1920x1080).
      2. Gentle pre-bloom acutance (`cas=0.06`) before optical diffusion.
      3. High-threshold Pro-Mist 1/8 warm halation (`0.76` threshold, `halation=0.08`) so ONLY specular rim/mic highlights
         bloom softly — zero milky veil over midtones or shadows.
      4. Tight Vision3 S-curve (`0 -> 0.034`, `0.12 -> 0.128`, `P05 ~ 9-11`, `crush<10 ~ 0.5-3%`) for rich solid blacks
         with readable velvet shadow folds, paired with warm 3200K midtone skin balance (`SatMean ~ 0.32-0.34`).
      5. Ultra-fine temporal luma-only silver grain (`c0s=3:c1s=0:c2s=0`) preserving native 2K pore & fabric micro-detail.
    """
    pre = []
    if target_size:
        tw, th = target_size
        # Scale preserving aspect ratio and center-crop cleanly (e.g. 2688x1536 -> 1920x1097 -> crop 1920x1080)
        pre.append(f"scale={tw}:{th}:force_original_aspect_ratio=increase:flags=lanczos,crop={tw}:{th},setsar=1")
    pre.append("cas=0.06")
    pre.append("format=rgb24")
    pre_chain = ",".join(pre)

    bloom_sigma = 20 if (target_size and max(target_size) >= 1920) else 14
    parts = [
        f"[{in_label}]{pre_chain},split=2[_fg_base][_fg_hi]",
        (
            f"[_fg_hi]curves=all='0/0 0.76/0 0.90/0.35 1/1',"
            f"colorbalance=rm=0.14:gm=0.04:bm=-0.09:rh=0.16:gh=0.05:bh=-0.11,"
            f"gblur=sigma={bloom_sigma}[_fg_bloom]"
        ),
        (
            f"[_fg_base][_fg_bloom]blend=all_mode=screen:all_opacity={halation:.3f},"
            f"curves=all='0/0.034 0.12/0.128 0.50/0.512 0.86/0.855 1/0.968',"
            f"hue=s={sat:.3f},"
            f"colorbalance=rs=-0.004:gs=0.000:bs=0.008:rm=0.016:gm=0.004:bm=-0.012:rh=0.018:gh=0.007:bh=-0.016,"
            f"format=yuv420p"
            + (f",noise=c0s={int(luma_grain)}:c1s=0:c2s=0:c0f=t+u" if luma_grain > 0 else "")
            + f",setpts=PTS-STARTPTS[{out_label}]"
        ),
    ]
    return ";".join(parts)


def condition_episode_refs(ep_dir: str, warm_skin_boost: float = 0.18, radius: int = 16) -> None:
    """Idempotently condition portrait & stage plates of an episode for Realism V3 cinema generation (0 CCU)."""
    import shutil
    from pathlib import Path

    ep = Path(ep_dir)
    work = ep / "work"
    refs = ep / "refs"
    work.mkdir(parents=True, exist_ok=True)
    refs.mkdir(parents=True, exist_ok=True)

    for who, boost in (("a", warm_skin_boost), ("b", warm_skin_boost)):
        clean_p = work / f"{who}_face_clean.png"
        raw_bak = work / f"{who}_face_raw_orig.png"
        if not clean_p.exists() and (refs / f"{who}_face.png").exists():
            shutil.copy2(refs / f"{who}_face.png", clean_p)
        if clean_p.exists():
            if not raw_bak.exists():
                shutil.copy2(clean_p, raw_bak)
            condition_char_ref(
                str(raw_bak),
                str(clean_p),
                max_sat_mean=0.36,
                min_sat_mean=0.29,
                warm_skin_boost=boost,
                toe_lift=0.010,
                soften_px=0.25,
            )
            shutil.copy2(clean_p, refs / f"{who}_face.png")
            print(f"✅ Conditioned V3 warm portrait: {clean_p}")

    for stg in ("stage_a", "stage_b"):
        stg_p = work / f"{stg}.png"
        raw_bak = work / f"{stg}_raw_orig.png"
        if stg_p.exists():
            if not raw_bak.exists():
                shutil.copy2(stg_p, raw_bak)
            make_bokeh_plate(
                str(raw_bak),
                str(stg_p),
                radius=radius,
                specular_thresh=0.52,
                specular_gain=3.2,
                sat_scale=0.82,
                contrast_scale=0.90,
                exposure=0.78,
                arena_crowd=True,
                haze_lift=(0.012, 0.013, 0.016),
            )
            print(f"✅ Conditioned V3 T2.2 bokeh stage plate (r={radius}): {stg_p}")


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Condition episode reference plates for Realism V3 cinema mode (0 CCU)")
    ap.add_argument("ep", help="Episode directory")
    ap.add_argument("--warm-boost", type=float, default=0.18, help="Midtone 3200K warm skin boost (0.0 to disable)")
    ap.add_argument("--radius", type=int, default=16, help="Circular aperture bokeh radius in px at 1024p")
    args = ap.parse_args()
    condition_episode_refs(args.ep, warm_skin_boost=args.warm_boost, radius=args.radius)
