#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build & render V2 YouTube Shorts (0 CCU Cinema-Master Multi-Cut) for Episode 8: Kratos vs Master Chief.

Features (all 3 Shorts @ 1080x1920, 24fps, H.264 CRF 18 + AAC 192k):
  1. 0.0s-1.15s Split-Screen Clash Opener:
     - Top (y=0..956): Master Chief live armored rap performance clip
     - Bottom (y=964..1920): Kratos live furious Spartan glare reaction clip
     - 8px Cinema Gold divider (#F5C518) + crimson/gold VS badge centered at (540, 960)
  2. Full-bleed 1080x1920 smart subject-centered Lanczos crops following work/edl.json & work/shifts.json
     with frame-exact 0.0ms lip-sync alignment and beat-matched smash bridge.
  3. Kodak Vision3 500T + Pro-Mist 1/8 optical grade (`film_grade_filter`) applied to the video stream
     BEFORE compositing crisp text/UI overlays (zero halation blur on captions or callouts).
  4. Word-by-word Kinetic Pop Captions (`work/words_edit.json`) using Impact.ttf:
     - Full-bleed safe zone x in [44, 900], y in [1160, 1390]; split-screen opener chest zone y in [1420, 1565]
     - 1.18x active word pop: Chief #FFFFFF / #5CE8FF (Mjolnir Shield Cyan-Gold #FFE45C); Kratos #FFF4E0 / #FF4B36 (or #FFD728 punch)
  5. Bottom-Left Related-Video Pointer Pill (last 3.0s):
     - Gold #F5C518 rounded callout + downward triangle pointer at x=150 inside x in [36, 860], y in [1470, 1555]
     - Text: TAP RELATED VIDEO BELOW FOR FULL BATTLE
  6. Seamless Replay Loop Audio:
     - Phase-locked instrumental stem crossfades (`inst_cut.wav`), 100ms raised-cosine bridge crossfade,
       and crisp loop cut ~0.14s after the final sung word (zero silent tail).

Usage:
  python3 build_shorts_v2.py [--dry-check] [sid ...]
"""
from __future__ import annotations

import json
import math
import subprocess
import sys
import wave
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

EP_DIR = Path(__file__).resolve().parent
WORK_DIR = EP_DIR / "work"
CLIPS_DIR = EP_DIR / "clips"
PREVIEW_DIR = EP_DIR / "preview"
SCRIPTS_DIR = EP_DIR.parent.parent / "scripts"

sys.path.insert(0, str(SCRIPTS_DIR))
from film_optics import film_grade_filter  # noqa: E402

W, H, FPS = 1080, 1920, 24
IMPACT_PATH = "/System/Library/Fonts/Supplemental/Impact.ttf"

# Colors (RGBA)
GOLD_DIVIDER = (245, 197, 24, 255)       # #F5C518
BLACK_STROKE = (10, 10, 10, 255)
CHIEF_BASE = (255, 255, 255, 255)        # #FFFFFF
CHIEF_ACTIVE = (255, 228, 92, 255)       # #FFE45C Visor Amber-Gold
KRATOS_BASE = (255, 244, 224, 255)       # #FFF4E0 Ash-Bone
KRATOS_ACTIVE = (255, 75, 54, 255)       # #FF4B36 Spartan Rage Red
KRATOS_PUNCH = (255, 215, 40, 255)       # #FFD728 Rhyme Punch Gold


# ---------------------------------------------------------------------------
# Per-Short Master Specifications (24fps frame-exact EDL & Lyric Chunks)
# ---------------------------------------------------------------------------
SHORTS_V2_CFG: dict[str, dict[str, Any]] = {
    "s1_boy_cortana": {
        "qa_name": "qa_shorts_v2_s1.jpg",
        "seg1_song_t0": 12.840,
        "seg1_frames": 140,  # 5.833s -> song 12.840..18.673s
        "seg1_voc_in": (12.840, 12.855),
        "seg1_voc_out": (18.640, 18.670),  # mute before A05 "Mjolnir" at 18.701s
        "bridge_frames": 16,  # 0.667s
        "bridge_song_t0": 33.740,
        "seg2_song_t0": 34.407,
        "seg2_frames": 309,  # 12.875s -> song 34.407..47.282s (+0.15s after "spare" 47.13s)
        "seg2_voc_in": (34.395, 34.420),
        "seg2_voc_out": (47.135, 47.175),  # mute before B05 "I" at 47.206s
        "opener": {
            "frames": 28,  # 0.000..1.167s
            "top_clip": "A03",
            "top_scale": (1674, 956),
            "top_x_frac": 0.95,
            "top_y0": 0,
            "bot_clip": "B_R_BOY",
            "bot_in": 0.250,
            "bot_scale": (1745, 996),
            "bot_x0": 0.48,
            "bot_x1": 0.50,
            "bot_y0": 24,
        },
        "shots_after_opener": [
            # Seg 1 full-bleed shots (must sum to 140 - 28 = 112)
            {"seg": 1, "clip": "B_R_BOY", "in": 0.650, "frames": 24, "x0": 0.50, "x1": 0.50},
            {"seg": 1, "clip": "A03", "frames": 88, "x0": 0.68, "x1": 0.63},
            # Smash Bridge (16 frames = 0.667s)
            {"seg": 0, "clip": "KRATOS_ERUPT", "in": 1.500, "speed": 1.35, "frames": 16, "x0": 0.50, "x1": 0.50, "flash_out": True},
            # Seg 2 full-bleed shots (must sum to 309)
            {"seg": 2, "clip": "B01", "frames": 118, "x0": 0.50, "x1": 0.50, "shake_in": True},
            {"seg": 2, "clip": "A_R_BUCKET", "in": 0.600, "frames": 26, "x0": 0.50, "x1": 0.50},
            {"seg": 2, "clip": "B01", "frames": 14, "x0": 0.50, "x1": 0.50},
            {"seg": 2, "clip": "B03", "frames": 151, "x0": 0.68, "x1": 0.69},
        ],
        "chunks": [
            (1, "a", 12.86, 14.10, [["GRAY", "BEARD"], ["YELLING", '"BOY!"']], {'"BOY!"'}),
            (1, "a", 14.11, 15.92, [["AGAIN", "-"], ["SAME", "TANTRUM,", "DIFFERENT", "MOLD"]], {"MOLD"}),
            (1, "a", 15.97, 17.40, [["ROWING", "BOATS"], ["WITH", "MIMIR'S", "HEAD"]], {"MIMIR'S", "HEAD"}),
            (1, "a", 17.42, 18.66, [["THAT", "DAD", "ACT'S"], ["GETTING", "OLD"]], {"OLD"}),
            (2, "b", 34.43, 36.60, [["STOLEN", "AT", "SIX"], ["BY", "A", "LAB", "COAT"]], {"SIX", "COAT"}),
            (2, "b", 36.62, 37.92, [["STRIPPED", "OF", "YOUR"], ["NAME", "AND", "SOUL!"]], {"SOUL!"}),
            (2, "b", 37.97, 39.66, [["LOCKED", "IN", "A"], ["GREEN", "METAL", "BUCKET"]], {"BUCKET"}),
            (2, "b", 39.68, 40.92, [["PUPPET", "ON"], ["FULL", "CONTROL!"]], {"PUPPET", "CONTROL!"}),
            (2, "b", 40.97, 42.60, [["YOU", "LOST", "A"], ["BLUE", "HOLOGRAM"]], {"HOLOGRAM"}),
            (2, "b", 42.65, 44.02, [["CORTANA", "VANISHED"], ["IN", "THIN", "AIR"]], {"CORTANA", "AIR"}),
            (2, "b", 44.08, 45.76, [["YOU", "CLONED"], ['"THE', 'WEAPON"', "FROM", "HER", "CODE"]], {'"THE', 'WEAPON"'}),
            (2, "b", 45.78, 47.14, [["LIKE", "GRIEF", "JUST"], ["NEEDS", "A", "SPARE!"]], {"GRIEF", "SPARE!"}),
        ],
    },
    "s2_console_war_goty": {
        "qa_name": "qa_shorts_v2_s2.jpg",
        "seg1_song_t0": 18.685,
        "seg1_frames": 147,  # 6.125s -> song 18.685..24.810s
        "seg1_voc_in": (18.685, 18.700),
        "seg1_voc_out": (24.785, 24.810),  # mute before A07 "Dropped" at 24.826s
        "bridge_frames": 16,  # 0.667s
        "bridge_song_t0": 46.518,
        "seg2_song_t0": 47.185,
        "seg2_frames": 309,  # 12.875s -> song 47.185..60.060s
        "seg2_voc_in": (47.185, 47.205),
        "seg2_voc_out": (59.980, 60.045),  # mute before "ROUND THREE!" at 60.111s
        "opener": {
            "frames": 28,
            "top_clip": "A05",
            "top_scale": (1674, 956),
            "top_x_frac": 0.50,
            "top_y0": 0,
            "bot_clip": "KRATOS_ERUPT",
            "bot_in": 1.700,
            "bot_scale": (1745, 996),
            "bot_x0": 0.48,
            "bot_x1": 0.50,
            "bot_y0": 24,
        },
        "shots_after_opener": [
            # Seg 1 full-bleed (147 - 28 = 119 frames)
            {"seg": 1, "clip": "A05", "frames": 119, "x0": 0.50, "x1": 0.50},
            # Smash Bridge (16 frames = 0.667s)
            {"seg": 0, "clip": "AXE_FROST_CU", "in": 1.500, "speed": 1.50, "frames": 16, "x0": 0.50, "x1": 0.50, "flash_out": True},
            # Seg 2 full-bleed (309 frames)
            {"seg": 2, "clip": "B05", "frames": 84, "x0": 0.50, "x1": 0.50, "shake_in": True},
            {"seg": 2, "clip": "AXE_FROST_CU", "in": 1.750, "frames": 24, "x0": 0.50, "x1": 0.50},
            {"seg": 2, "clip": "B05", "frames": 34, "x0": 0.50, "x1": 0.50},
            {"seg": 2, "clip": "B07", "frames": 167, "x0": 0.50, "x1": 0.50},
        ],
        "chunks": [
            (1, "a", 18.70, 20.24, [["MJOLNIR", "ARMOR"], ["EATS", "YOUR", "BLADES"]], {"BLADES"}),
            (1, "a", 20.28, 21.95, [["ENERGY", "SHIELDS"], ["BLOCK", "EVERY", "BLOW"]], {"SHIELDS", "BLOW"}),
            (1, "a", 22.01, 23.54, [["MY", "M-A-FIVE"], ["AND", "PLASMA", "BLADE"]], {"M-A-FIVE", "BLADE"}),
            (1, "a", 23.58, 24.80, [["LAY", "ANCIENT"], ["GODS", "BELOW"]], {"GODS", "BELOW"}),
            (2, "b", 47.21, 48.83, [["I", "BUTCHERED", "OLYMPUS"], ["AND", "BROKE", "THE", "NINE"]], {"OLYMPUS", "NINE"}),
            (2, "b", 48.86, 50.20, [["FROST", "ON", "THE"], ["AXE", "I", "SWING!"]], {"AXE", "SWING!"}),
            (2, "b", 50.25, 51.45, [["LEVIATHAN", "CRACKS"], ["YOUR", "SHIELD"]], {"LEVIATHAN", "CRACKS"}),
            (2, "b", 51.46, 53.02, [["TO", "SPLINTERS", "AND"], ["BROKEN", "RINGS!"]], {"SPLINTERS", "RINGS!"}),
            (2, "b", 53.11, 54.53, [["A", "BROKEN", "RING"], ["AND", "A", "TEN-YEAR", "WAIT"]], {"TEN-YEAR", "WAIT"}),
            (2, "b", 54.55, 56.22, [["YOUR", "MAKERS"], ["REBRANDED", "IN", "SHAME!"]], {"REBRANDED", "SHAME!"}),
            (2, "b", 56.31, 57.35, [["I", "SWEPT", "GAME"], ["OF", "THE", "YEAR"]], {"YEAR"}),
            (2, "b", 57.50, 60.02, [["WHILE", "XBOX", "GAVE", "UP"], ["THE", "CONSOLE", "GAME!"]], {"XBOX", "GAME!"}),
        ],
    },
    "s3_ashes_spartan_blood": {
        "qa_name": "qa_shorts_v2_s3.jpg",
        "seg1_song_t0": 74.770,
        "seg1_frames": 155,  # 6.458s -> song 74.770..81.228s
        "seg1_voc_in": (74.770, 74.788),
        "seg1_voc_out": (81.195, 81.225),  # mute before A11 "You" at 81.255s
        "bridge_frames": 16,  # 0.667s
        "bridge_song_t0": 86.773,
        "seg2_song_t0": 87.440,
        "seg2_frames": 299,  # 12.458s -> song 87.440..99.898s (+0.148s after "hire" 99.75s)
        "seg2_voc_in": (87.440, 87.454),
        "seg2_voc_out": (99.715, 99.748),  # mute cleanly before A13 "No" at 99.754s
        "opener": {
            "frames": 28,
            "top_clip": "A09",
            "top_scale": (1920, 1097),
            "top_x_frac": 0.02,
            "top_y0": 32,
            "bot_clip": "B_R_ASHES",
            "bot_in": 2.000,
            "bot_scale": (1745, 996),
            "bot_x0": 0.49,
            "bot_x1": 0.50,
            "bot_y0": 24,
        },
        "shots_after_opener": [
            # Seg 1 full-bleed (155 - 28 = 127 frames)
            {"seg": 1, "clip": "A09", "frames": 54, "x0": 0.36, "x1": 0.40},
            {"seg": 1, "clip": "B_R_ASHES", "in": 2.150, "frames": 26, "x0": 0.50, "x1": 0.50},
            {"seg": 1, "clip": "A09", "frames": 47, "x0": 0.40, "x1": 0.45},
            # Space-Time Rift Blades of Chaos Smash Bridge (16 frames = 0.667s)
            {"seg": 0, "clip": "KRATOS_CHAOS_ERUPT", "in": 1.800, "speed": 1.35, "frames": 16, "x0": 0.50, "x1": 0.50, "flash_out": True},
            # Seg 2 full-bleed (299 frames)
            {"seg": 2, "clip": "B09", "frames": 88, "x0": 0.66, "x1": 0.64, "shake_in": True},
            {"seg": 2, "clip": "A_R_UNSC", "in": 2.050, "frames": 25, "x0": 0.50, "x1": 0.50},
            {"seg": 2, "clip": "B09", "frames": 35, "x0": 0.64, "x1": 0.62},
            {"seg": 2, "clip": "B11", "frames": 151, "x0": 0.55, "x1": 0.50},
        ],
        "chunks": [
            (1, "a", 74.79, 76.04, [["TALK", "ABOUT"], ["PUPPETS?"]], {"PUPPETS?"}),
            (1, "a", 76.07, 78.02, [["ARES", "CHAINED", "THOSE", "BLADES"], ["RIGHT", "INTO", "YOUR", "SKIN"]], {"CHAINED", "SKIN"}),
            (1, "a", 78.11, 79.90, [["ASHES", "OF", "FAMILY"], ["BAKED", "ON", "YOUR", "CHEST"]], {"ASHES", "CHEST"}),
            (1, "a", 79.94, 81.21, [["LIVING", "PROOF"], ["OF", "YOUR", "SIN"]], {"PROOF", "SIN"}),
            (2, "b", 87.45, 89.38, [["I", "BROKE", "THE", "CHAINS"], ["OF", "THE", "GODS", "THEMSELVES"]], {"BROKE", "GODS"}),
            (2, "b", 89.46, 90.48, [["I", "OWN", "THE"], ["SCARS", "I", "BEAR!"]], {"SCARS", "BEAR!"}),
            (2, "b", 90.48, 92.11, [["YOU'RE", "OWNED", "BY"], ["THE", "U.N.S.C."]], {"OWNED", "U.N.S.C."}),
            (2, "b", 92.14, 93.54, [["JUST", "HARDWARE"], ["THEY", "REPAIR!"]], {"HARDWARE", "REPAIR!"}),
            (2, "b", 93.58, 95.23, [["REAL", "SPARTANS", "BLEED"], ["IN", "LACONIA'S", "DUST"]], {"SPARTANS", "BLEED"}),
            (2, "b", 95.28, 96.70, [["NOT", "ON", "A"], ["SCIENTIST'S", "WIRE!"]], {"WIRE!"}),
            (2, "b", 96.83, 98.33, [["I", "SHATTERED", "FATE"], ["AND", "THE", "SISTERS'", "LOOM"]], {"SHATTERED", "FATE"}),
            (2, "b", 98.36, 99.75, [["YOU", "FOLLOW"], ["ORDERS", "FOR", "HIRE!"]], {"ORDERS", "HIRE!"}),
        ],
    },
}


# ---------------------------------------------------------------------------
# Audio Helpers
# ---------------------------------------------------------------------------
def read_wav(path: Path) -> tuple[int, np.ndarray]:
    with wave.open(str(path), "rb") as w:
        sr = w.getframerate()
        ch = w.getnchannels()
        pcm = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
        arr = pcm.reshape(-1, ch).astype(np.float32) / 32768.0
    return sr, arr


def write_wav(path: Path, sr: int, arr: np.ndarray) -> None:
    pcm = np.clip(np.round(arr * 32767.0), -32768, 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(arr.shape[1])
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def build_gated_song_slice(
    music: np.ndarray,
    inst: np.ndarray,
    sr: int,
    t0: float,
    n_samples: int,
    voc_in: tuple[float, float],
    voc_out: tuple[float, float],
) -> np.ndarray:
    """Extract [t0, t0 + n_samples/sr] from phase-locked music_final & inst_cut,
    using inst outside [voc_in, voc_out] with smooth cosine ramps so adjacent lyric breaths never bleed."""
    i0 = int(round(t0 * sr))
    m_sl = music[i0 : i0 + n_samples].copy()
    inst_sl = inst[i0 : i0 + n_samples].copy()

    t_axis = t0 + np.arange(n_samples, dtype=np.float32) / sr
    vin0, vin1 = voc_in
    vout0, vout1 = voc_out

    w_in = np.clip((t_axis - vin0) / max(1e-4, vin1 - vin0), 0.0, 1.0)
    w_in = 0.5 * (1.0 - np.cos(np.pi * w_in))

    w_out = np.clip((vout1 - t_axis) / max(1e-4, vout1 - vout0), 0.0, 1.0)
    w_out = 0.5 * (1.0 - np.cos(np.pi * w_out))

    mask = (w_in * w_out)[:, None].astype(np.float32)
    return inst_sl * (1.0 - mask) + m_sl * mask


def build_master_audio(cfg: dict[str, Any], dst_wav: Path) -> float:
    """Assemble exact frame-locked stereo WAV with 100ms raised-cosine bridge crossfade & seamless loop declick."""
    sr, music = read_wav(WORK_DIR / "music_final.wav")
    inst_path = WORK_DIR / "svc_stems" / "demucs_no_vocals.wav"
    if not inst_path.exists():
        inst_path = WORK_DIR / "inst_cut.wav"
    _, inst = read_wav(inst_path)

    # Match RMS on clean intro [1.0s..6.0s]
    r0, r1 = int(1.0 * sr), int(6.0 * sr)
    gain = float(np.sqrt(np.mean(music[r0:r1] ** 2)) / max(1e-6, np.sqrt(np.mean(inst[r0:r1] ** 2))))
    inst_matched = inst * np.clip(gain, 0.92, 1.08)

    xf_sec = 0.100
    xf_n = int(round(xf_sec * sr))

    total_frames = cfg["seg1_frames"] + cfg["bridge_frames"] + cfg["seg2_frames"]
    total_n = int(math.ceil((total_frames / FPS) * sr))
    n_seg1 = int(round((cfg["seg1_frames"] / FPS) * sr))
    n_br = int(round((cfg["bridge_frames"] / FPS) * sr))
    n_seg2 = total_n - n_seg1 - n_br

    seg1_ext = build_gated_song_slice(
        music,
        inst_matched,
        sr,
        cfg["seg1_song_t0"],
        n_seg1 + xf_n,
        cfg["seg1_voc_in"],
        cfg["seg1_voc_out"],
    )

    br_t0 = cfg["seg2_song_t0"] - (cfg["bridge_frames"] / FPS)
    seg2_full = build_gated_song_slice(
        music,
        inst_matched,
        sr,
        br_t0,
        n_br + n_seg2,
        cfg["seg2_voc_in"],
        cfg["seg2_voc_out"],
    )

    out = np.zeros((total_n, 2), dtype=np.float32)
    out[:n_seg1] = seg1_ext[:n_seg1]
    out[n_seg1:] = seg2_full

    theta = np.linspace(0.0, 0.5 * np.pi, xf_n, dtype=np.float32)[:, None]
    fade_out = np.cos(theta)
    fade_in = np.sin(theta)
    out[n_seg1 : n_seg1 + xf_n] = seg1_ext[n_seg1 : n_seg1 + xf_n] * fade_out + seg2_full[:xf_n] * fade_in

    n_in = int(0.012 * sr)
    n_out = int(0.018 * sr)
    out[:n_in] *= (0.5 * (1.0 - np.cos(np.linspace(0.0, np.pi, n_in, dtype=np.float32))))[:, None]
    out[-n_out:] *= (0.5 * (1.0 + np.cos(np.linspace(0.0, np.pi, n_out, dtype=np.float32))))[:, None]

    peak = float(np.max(np.abs(out)))
    if peak > 0.96:
        out *= 0.96 / peak

    write_wav(dst_wav, sr, out)
    return total_n / sr


# ---------------------------------------------------------------------------
# Word-Timestamp Alignment from work/words_edit.json
# ---------------------------------------------------------------------------
def load_normalized_words() -> list[dict[str, Any]]:
    raw = json.loads((WORK_DIR / "words_edit.json").read_text(encoding="utf-8"))
    merged: list[dict[str, Any]] = []
    i = 0
    while i < len(raw):
        w = raw[i]
        txt = w["w"].strip()
        if txt in ("OOOH!", "ROUND", "THREE!", "FINAL", "CLASH!", "SPARTAN!", "SPARTAN"):
            i += 1
            continue
        # Merge U. + N. + S. + C. into single token U.N.S.C.
        if (
            txt == "U."
            and i + 3 < len(raw)
            and raw[i + 1]["w"].strip() == "N."
            and raw[i + 2]["w"].strip() == "S."
            and raw[i + 3]["w"].strip().startswith("C.")
        ):
            merged.append({"w": "U.N.S.C.", "t0": float(w["t0"]), "t1": float(raw[i + 3]["t1"])})
            i += 4
            continue
        merged.append({"w": txt, "t0": float(w["t0"]), "t1": float(w["t1"])})
        i += 1
    return merged


def norm_alpha(s: str) -> str:
    return "".join(ch for ch in s.upper() if ch.isalnum())


def build_caption_schedule(cfg: dict[str, Any], all_words: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Map each configured lyric chunk & display word to millisecond timestamps on the Short output timeline."""
    seg1_t0 = cfg["seg1_song_t0"]
    seg2_t0 = cfg["seg2_song_t0"]
    seg2_out_offset = (cfg["seg1_frames"] + cfg["bridge_frames"]) / FPS

    def song_to_out(seg: int, ts: float) -> float:
        if seg == 1:
            return ts - seg1_t0
        return seg2_out_offset + (ts - seg2_t0)

    schedule: list[dict[str, Any]] = []
    for seg, who, c_t0, c_t1, rows, punch_set in cfg["chunks"]:
        flat_disp = [tok for r in rows for tok in r]
        cands = [w for w in all_words if (c_t0 - 0.12) <= w["t0"] <= (c_t1 + 0.12)]
        matched_times: list[tuple[float, float]] = []
        cursor = 0
        for tok in flat_disp:
            want = norm_alpha(tok)
            found_idx = None
            if want:
                for j in range(cursor, min(len(cands), cursor + 4)):
                    if norm_alpha(cands[j]["w"]) == want:
                        found_idx = j
                        break
            if found_idx is not None:
                w_match = cands[found_idx]
                matched_times.append((w_match["t0"], max(w_match["t1"], w_match["t0"] + 0.06)))
                cursor = found_idx + 1
            else:
                frac0 = len(matched_times) / max(1, len(flat_disp))
                frac1 = (len(matched_times) + 1) / max(1, len(flat_disp))
                matched_times.append((c_t0 + frac0 * (c_t1 - c_t0), c_t0 + frac1 * (c_t1 - c_t0)))

        word_out_Windows: list[tuple[float, float]] = []
        for idx, (wt0, wt1) in enumerate(matched_times):
            ot0 = song_to_out(seg, wt0)
            ot1 = song_to_out(seg, wt1)
            if idx + 1 < len(matched_times):
                nxt_ot0 = song_to_out(seg, matched_times[idx + 1][0])
                ot1 = max(ot1, nxt_ot0)
            else:
                ot1 = max(ot1, song_to_out(seg, c_t1))
            word_out_Windows.append((ot0, ot1))

        for tok in flat_disp:
            assert all(32 <= ord(ch) < 127 for ch in tok), f"Non-ASCII token forbidden: {tok!r}"

        chunk_out_t0 = max(0.0, min(song_to_out(seg, c_t0) - 0.03, word_out_Windows[0][0] - 0.02))
        chunk_out_t1 = max(song_to_out(seg, c_t1) + 0.04, word_out_Windows[-1][1] + 0.03)
        schedule.append(
            {
                "who": who,
                "t0": chunk_out_t0,
                "t1": chunk_out_t1,
                "rows": rows,
                "punch": punch_set,
                "word_windows": word_out_Windows,
            }
        )

    for i in range(len(schedule) - 1):
        if schedule[i]["t1"] > schedule[i + 1]["t0"]:
            schedule[i]["t1"] = schedule[i + 1]["t0"]
    total_dur = (cfg["seg1_frames"] + cfg["bridge_frames"] + cfg["seg2_frames"]) / FPS
    if schedule:
        schedule[-1]["t1"] = max(schedule[-1]["t1"], total_dur + 0.05)
    return schedule


# ---------------------------------------------------------------------------
# Crisp UI & Kinetic Typography Renderer (Post-Film-Grade RGBA Overlays)
# ---------------------------------------------------------------------------
class OverlayRenderer:
    def __init__(self) -> None:
        self._fonts: dict[int, ImageFont.FreeTypeFont] = {}
        self._caption_cache: dict[tuple[Any, ...], Image.Image] = {}
        self._vs_layer = self._build_vs_opener_overlay()
        self._pointer_cache: dict[int, Image.Image] = {}

    def font(self, size: int) -> ImageFont.FreeTypeFont:
        if size not in self._fonts:
            self._fonts[size] = ImageFont.truetype(IMPACT_PATH, size)
        return self._fonts[size]

    def _build_vs_opener_overlay(self) -> Image.Image:
        """Build 8px #F5C518 divider (y=956..964) + Crimson/Gold VS clash badge centered at (540, 960)."""
        canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sd = ImageDraw.Draw(shadow)

        sd.rectangle([0, 953, W, 967], fill=(0, 0, 0, 190))
        bx0, by0, bx1, by1 = 464, 916, 616, 1004
        sd.rounded_rectangle([bx0, by0 + 4, bx1, by1 + 6], radius=16, fill=(0, 0, 0, 210))
        canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(5)))

        d = ImageDraw.Draw(canvas)
        d.rectangle([0, 954, W, 966], fill=BLACK_STROKE)
        d.rectangle([0, 956, W, 964], fill=GOLD_DIVIDER)

        badge_w, badge_h = bx1 - bx0, by1 - by0
        grad = Image.new("RGBA", (badge_w, badge_h), (0, 0, 0, 0))
        gd = ImageDraw.Draw(grad)
        for yy in range(badge_h):
            t = yy / max(1, badge_h - 1)
            r = int(214 * (1 - t) + 136 * t)
            g = int(30 * (1 - t) + 12 * t)
            b = int(38 * (1 - t) + 18 * t)
            gd.line([(0, yy), (badge_w, yy)], fill=(r, g, b, 255))
        mask = Image.new("L", (badge_w, badge_h), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, badge_w - 1, badge_h - 1], radius=16, fill=255)

        badge_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        badge_layer.paste(grad, (bx0, by0), mask)
        bd = ImageDraw.Draw(badge_layer)
        bd.rounded_rectangle([bx0, by0, bx1, by1], radius=16, outline=GOLD_DIVIDER, width=5)
        bd.rounded_rectangle([bx0 - 2, by0 - 2, bx1 + 2, by1 + 2], radius=18, outline=BLACK_STROKE, width=2)

        f_vs = self.font(54)
        bd.text((540, 960), "VS", font=f_vs, fill=(255, 255, 255, 255), anchor="mm", stroke_width=4, stroke_fill=BLACK_STROKE)
        canvas.alpha_composite(badge_layer)
        return canvas

    def render_caption(self, chunk: dict[str, Any], active_idx: int, opener_mode: bool = False) -> Image.Image:
        """Render word-by-word kinetic pop caption inside safe zone (full-bleed y in [1160, 1390]; opener chest y in [1420, 1565])."""
        key = (
            chunk["who"],
            tuple(tuple(r) for r in chunk["rows"]),
            tuple(sorted(chunk["punch"])),
            active_idx,
            opener_mode,
        )
        if key in self._caption_cache:
            return self._caption_cache[key]

        rows: list[list[str]] = chunk["rows"]
        who: str = chunk["who"]
        punch_set: set[str] = chunk["punch"]

        x_center = 472
        max_row_w = 812

        base_size = (56 if opener_mode else 72) if len(rows) == 2 else (64 if opener_mode else 78)
        dummy = ImageDraw.Draw(Image.new("RGBA", (16, 16)))

        while base_size > 38:
            act_size = int(round(base_size * 1.18))
            f_base = self.font(base_size)
            f_act = self.font(act_size)
            sp_w = dummy.textlength(" ", font=f_base) * 1.12
            fits = True
            w_cursor = 0
            for r in rows:
                rw = 0.0
                for j, tok in enumerate(r):
                    is_act = (w_cursor + j) == active_idx
                    fn = f_act if is_act else f_base
                    rw += dummy.textlength(tok, font=fn) + (8 if is_act else 0)
                    if j + 1 < len(r):
                        rw += sp_w
                w_cursor += len(r)
                if rw > max_row_w:
                    fits = False
                    break
            if fits:
                break
            base_size -= 2

        act_size = int(round(base_size * 1.18))
        f_base = self.font(base_size)
        f_act = self.font(act_size)
        sp_w = dummy.textlength(" ", font=f_base) * 1.12

        if opener_mode:
            if len(rows) == 1:
                row_ys = [1486]
            else:
                gap = 64
                mid_y = 1486
                row_ys = [mid_y - gap // 2, mid_y + gap // 2]
        else:
            if len(rows) == 1:
                row_ys = [1274]
            else:
                gap = max(84, int(round(base_size * 1.22)))
                gap = min(gap, 94)
                mid_y = 1274
                row_ys = [mid_y - gap // 2, mid_y + gap // 2]

        text_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        td = ImageDraw.Draw(text_layer)

        placements: list[tuple[bool, float, float, str, ImageFont.FreeTypeFont, tuple[int, int, int, int], int]] = []
        w_cursor = 0
        for r_idx, r in enumerate(rows):
            widths: list[float] = []
            for j, tok in enumerate(r):
                is_act = (w_cursor + j) == active_idx
                fn = f_act if is_act else f_base
                widths.append(dummy.textlength(tok, font=fn) + (6 if is_act else 0))
            total_w = sum(widths) + sp_w * max(0, len(r) - 1)
            x_start = x_center - total_w / 2.0
            x_start = max(54.0, min(x_start, 886.0 - total_w))
            cy = row_ys[r_idx]

            cur_x = x_start
            for j, tok in enumerate(r):
                g_idx = w_cursor + j
                is_act = g_idx == active_idx
                fn = f_act if is_act else f_base
                tw = widths[j]
                cx = cur_x + tw / 2.0
                if who == "a":
                    fill = CHIEF_ACTIVE if is_act else CHIEF_BASE
                else:
                    if is_act:
                        fill = KRATOS_PUNCH if tok in punch_set else KRATOS_ACTIVE
                    else:
                        fill = KRATOS_BASE
                sw = 8 if is_act else 7
                wy = cy - 3 if is_act else cy
                placements.append((is_act, cx, wy, tok, fn, fill, sw))
                cur_x += tw + sp_w
            w_cursor += len(r)

        for pass_active in (False, True):
            for is_act, cx, wy, tok, fn, fill, sw in placements:
                if is_act == pass_active:
                    td.text((cx, wy), tok, font=fn, fill=fill, anchor="mm", stroke_width=sw, stroke_fill=BLACK_STROKE)

        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sh.putalpha(text_layer.split()[3].point(lambda a: int(a * 0.82)))
        sh = sh.filter(ImageFilter.GaussianBlur(3.2))

        out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        out.alpha_composite(sh, (4, 5))
        out.alpha_composite(text_layer)

        bbox = out.getbbox()
        if bbox is not None:
            bx0, by0, bx1, by1 = bbox
            assert bx0 >= 44 and bx1 <= 900, f"Caption X out of safe zone [44, 900]: {bbox}"
            if opener_mode:
                assert 1410 <= by0 and by1 <= 1568, f"Opener caption Y out of chest zone [1410, 1568]: {bbox}"
            else:
                assert 1160 <= by0 and by1 <= 1390, f"Caption Y out of safe zone [1160, 1390]: {bbox}"

        self._caption_cache[key] = out
        return out

    def render_related_pointer(self, dy: int = 0) -> Image.Image:
        """Render gold callout pill + downward triangle pointer at x=150 strictly inside x in [36, 860], y in [1470, 1555]."""
        dy = int(np.clip(dy, -1, 1))
        if dy in self._pointer_cache:
            return self._pointer_cache[dy]

        px0, py0, px1, py1 = 42, 1477 + dy, 850, 1531 + dy
        tip_x, tip_y = 150, 1546 + dy

        out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sil = Image.new("L", (W, H), 0)
        sd = ImageDraw.Draw(sil)
        sd.rounded_rectangle([px0, py0, px1, py1], radius=14, fill=255)
        sd.polygon([(tip_x - 18, py1 - 2), (tip_x + 18, py1 - 2), (tip_x, tip_y)], fill=255)

        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sh.putalpha(sil.point(lambda a: int(a * 0.65)))
        sh = sh.filter(ImageFilter.GaussianBlur(2.0))
        out.alpha_composite(sh, (2, 2))

        border_mask = sil.filter(ImageFilter.MaxFilter(9))
        border_layer = Image.new("RGBA", (W, H), BLACK_STROKE)
        out.paste(border_layer, (0, 0), border_mask)

        gold_layer = Image.new("RGBA", (W, H), GOLD_DIVIDER)
        out.paste(gold_layer, (0, 0), sil)

        td = ImageDraw.Draw(out)
        f_cta = self.font(34)
        label = "TAP RELATED VIDEO BELOW FOR FULL BATTLE"
        td.text(((px0 + px1) / 2.0, (py0 + py1) / 2.0), label, font=f_cta, fill=BLACK_STROKE, anchor="mm")

        bbox = out.getbbox()
        assert bbox is not None
        bx0, by0, bx1, by1 = bbox
        assert bx0 >= 36 and bx1 <= 860, f"Pointer X out of safe zone [36, 860]: {bbox}"
        assert by0 >= 1470 and by1 <= 1555, f"Pointer Y out of safe zone [1470, 1555]: {bbox}"

        self._pointer_cache[dy] = out
        return out


# ---------------------------------------------------------------------------
# FFmpeg Graded Video Builder (Raw Multi-Cut -> Kodak Vision3 500T Grade)
# ---------------------------------------------------------------------------
def build_graded_video(cfg: dict[str, Any], clips_meta: dict[str, dict[str, Any]], shifts: dict[str, float], dst_mp4: Path) -> int:
    """Assemble 0.0s split-screen opener + full-bleed smart subject-tracked 9:16 cuts and apply film_grade_filter."""
    opener = cfg["opener"]
    op_frames = opener["frames"]

    inputs: list[str] = []
    fc_parts: list[str] = []
    concat_labels: list[str] = []

    def add_clip_input(cid: str) -> int:
        idx = len(inputs) // 2
        clip_path = CLIPS_DIR / f"{cid}_t1.mp4"
        assert clip_path.exists(), f"Missing clip: {clip_path}"
        inputs.extend(["-i", str(clip_path)])
        return idx

    top_cid = opener["top_clip"]
    top_c = clips_meta[top_cid]
    top_src_in = cfg["seg1_song_t0"] - (top_c["audio"][0] - top_c.get("lead", 0.0)) + shifts.get(top_cid, 0.0)
    top_src_in = max(0.0, top_src_in)

    top_idx = add_clip_input(top_cid)
    bot_idx = add_clip_input(opener["bot_clip"])

    tsw, tsh = opener["top_scale"]
    tx0 = int(np.clip(round(tsw * opener["top_x_frac"] - W / 2.0), 0, tsw - W))
    ty0 = int(np.clip(opener["top_y0"], 0, tsh - 956))

    bsw, bsh = opener["bot_scale"]
    by0 = int(np.clip(opener["bot_y0"], 0, bsh - 956))
    op_dur = op_frames / FPS
    if "bot_x0" in opener and "bot_x1" in opener:
        bx0_f, bx1_f = float(opener["bot_x0"]), float(opener["bot_x1"])
        bx_expr = f"clip({bsw}*({bx0_f:.4f}+{bx1_f - bx0_f:.4f}*min(1,t/{op_dur:.4f}))-540,0,{bsw - W})"
    else:
        bx0_px = int(np.clip(round(bsw * opener["bot_x_frac"] - W / 2.0), 0, bsw - W))
        bx_expr = str(bx0_px)

    fc_parts.append(
        f"[{top_idx}:v]trim=start={top_src_in:.6f},setpts=PTS-STARTPTS,fps={FPS},"
        f"trim=end_frame={op_frames},setpts=PTS-STARTPTS,"
        f"scale={tsw}:{tsh}:flags=lanczos,crop={W}:956:{tx0}:{ty0},setsar=1[op_top]"
    )
    fc_parts.append(
        f"[{bot_idx}:v]trim=start={opener['bot_in']:.6f},setpts=PTS-STARTPTS,fps={FPS},"
        f"trim=end_frame={op_frames},setpts=PTS-STARTPTS,"
        f"scale={bsw}:{bsh}:flags=lanczos,crop={W}:956:x='{bx_expr}':y={by0},setsar=1[op_bot]"
    )
    fc_parts.append(f"color=c=0x141414:s={W}x8:r={FPS},trim=end_frame={op_frames},setpts=PTS-STARTPTS[op_bar]")
    fc_parts.append("[op_top][op_bar][op_bot]vstack=inputs=3,setsar=1[vshot0]")
    concat_labels.append("[vshot0]")

    cur_frame = op_frames
    seg2_start_frame = cfg["seg1_frames"] + cfg["bridge_frames"]

    for s_idx, shot in enumerate(cfg["shots_after_opener"], start=1):
        cid = shot["clip"]
        n_f = shot["frames"]
        dur = n_f / FPS
        seg = shot["seg"]
        speed = float(shot.get("speed", 1.0))

        if "in" in shot and shot["in"] is not None:
            src_in = float(shot["in"])
        else:
            c_meta = clips_meta[cid]
            if seg == 1:
                t_song = cfg["seg1_song_t0"] + (cur_frame / FPS)
            else:
                t_song = cfg["seg2_song_t0"] + ((cur_frame - seg2_start_frame) / FPS)
            src_in = t_song - (c_meta["audio"][0] - c_meta.get("lead", 0.0)) + shifts.get(cid, 0.0)
            src_in = max(0.0, src_in)

        in_idx = add_clip_input(cid)
        pts_expr = f"{1.0 / speed:.6f}*(PTS-STARTPTS)" if abs(speed - 1.0) > 1e-3 else "PTS-STARTPTS"

        sw, sh = 3360, 1920
        x0_f, x1_f = float(shot["x0"]), float(shot["x1"])
        if shot.get("whip_pan"):
            x_expr = f"clip({sw}*({x0_f:.4f}+{x1_f - x0_f:.4f}*(0.5-0.5*cos(PI*min(1,t/{dur:.4f}))))-540,0,{sw - W})"
        elif abs(x1_f - x0_f) > 1e-4:
            x_expr = f"clip({sw}*({x0_f:.4f}+{x1_f - x0_f:.4f}*min(1,t/{dur:.4f}))-540,0,{sw - W})"
        else:
            fixed_x = int(np.clip(round(sw * x0_f - W / 2.0), 0, sw - W))
            x_expr = str(fixed_x)

        extra_fx = ""
        if shot.get("whip_pan"):
            extra_fx += f",avgblur=sizeX=20:sizeY=1:enable='between(t,{dur * 0.18:.3f},{dur * 0.82:.3f})'"
        if shot.get("flash_out"):
            extra_fx += f",eq=brightness=0.22:contrast=1.12:enable='gte(t,{max(0.0, dur - 2.0 / FPS):.3f})'"
        if shot.get("shake_in"):
            sw_sh, sh_sh = 3460, 1978
            sx_base = int(np.clip(round(sw_sh * x0_f - W / 2.0), 0, sw_sh - W))
            chain = (
                f"[{in_idx}:v]trim=start={src_in:.6f},setpts={pts_expr},fps={FPS},"
                f"tpad=stop_mode=clone:stop_duration=0.2,trim=end_frame={n_f},setpts=PTS-STARTPTS,"
                f"scale={sw_sh}:{sh_sh}:flags=lanczos,"
                f"crop={W}:{H}:x='clip({sx_base}+if(lt(t,0.38),12*sin(t*95)*(1-t/0.38),0),0,{sw_sh - W})':"
                f"y='29+if(lt(t,0.38),10*cos(t*83)*(1-t/0.38),0)',"
                f"eq=brightness='if(lt(t,0.08),0.18,0)':eval=frame,setsar=1[vshot{s_idx}]"
            )
            fc_parts.append(chain)
            concat_labels.append(f"[vshot{s_idx}]")
            cur_frame += n_f
            continue

        chain = (
            f"[{in_idx}:v]trim=start={src_in:.6f},setpts={pts_expr},fps={FPS},"
            f"tpad=stop_mode=clone:stop_duration=0.2,trim=end_frame={n_f},setpts=PTS-STARTPTS,"
            f"scale={sw}:{sh}:flags=lanczos,crop={W}:{H}:x='{x_expr}':y=0{extra_fx},setsar=1[vshot{s_idx}]"
        )
        fc_parts.append(chain)
        concat_labels.append(f"[vshot{s_idx}]")
        cur_frame += n_f

    expected_total = cfg["seg1_frames"] + cfg["bridge_frames"] + cfg["seg2_frames"]
    assert cur_frame == expected_total, f"Frame count mismatch: {cur_frame} vs {expected_total}"

    n_concat = len(concat_labels)
    fc_parts.append(f"{''.join(concat_labels)}concat=n={n_concat}:v=1:a=0[v_raw]")
    fc_parts.append(film_grade_filter("v_raw", "v_graded", target_size=(W, H), halation=0.08, sat=0.88, luma_grain=3))

    cmd = (
        ["ffmpeg", "-y", "-v", "error"]
        + inputs
        + [
            "-filter_complex",
            ";".join(fc_parts),
            "-map",
            "[v_graded]",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "11",
            "-pix_fmt",
            "yuv420p",
            "-r",
            str(FPS),
            str(dst_mp4),
        ]
    )
    subprocess.run(cmd, check=True)
    return expected_total


# ---------------------------------------------------------------------------
# Post-Grade Crisp Overlay Compositor & Final H.264 CRF 18 + AAC 192k Encode
# ---------------------------------------------------------------------------
def composite_overlays_and_encode(
    cfg: dict[str, Any],
    graded_mp4: Path,
    master_wav: Path,
    schedule: list[dict[str, Any]],
    total_frames: int,
    renderer: OverlayRenderer,
    final_mp4: Path,
) -> None:
    final_mp4.parent.mkdir(parents=True, exist_ok=True)
    duration = total_frames / FPS
    op_frames = cfg["opener"]["frames"]
    pointer_start_t = duration - 3.0

    dec = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-i", str(graded_mp4), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        stdout=subprocess.PIPE,
    )
    enc = subprocess.Popen(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-s",
            f"{W}x{H}",
            "-r",
            str(FPS),
            "-i",
            "-",
            "-i",
            str(master_wav),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-r",
            str(FPS),
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "44100",
            "-ac",
            "2",
            "-movflags",
            "+faststart",
            str(final_mp4),
        ],
        stdin=subprocess.PIPE,
    )

    frame_bytes = W * H * 3
    assert dec.stdout is not None and enc.stdin is not None

    for f_idx in range(total_frames):
        raw = dec.stdout.read(frame_bytes)
        if len(raw) < frame_bytes:
            break
        t = (f_idx + 0.5) / FPS
        base_im = Image.frombytes("RGB", (W, H), raw).convert("RGBA")

        if f_idx < op_frames:
            base_im.alpha_composite(renderer._vs_layer)

        for ch in schedule:
            if ch["t0"] <= t < ch["t1"]:
                act_idx = 0
                for w_i, (wt0, _wt1) in enumerate(ch["word_windows"]):
                    if t >= wt0:
                        act_idx = w_i
                cap_im = renderer.render_caption(ch, act_idx, opener_mode=(f_idx < op_frames))
                base_im.alpha_composite(cap_im)
                break

        if t >= pointer_start_t:
            dt = t - pointer_start_t
            dy = int(round(2.0 * math.sin(dt * 2.0 * math.pi * 1.5)))
            ptr_im = renderer.render_related_pointer(dy=dy)
            base_im.alpha_composite(ptr_im)

        enc.stdin.write(base_im.convert("RGB").tobytes())

    enc.stdin.close()
    dec.stdout.close()
    dec.wait()
    rc = enc.wait()
    if rc != 0:
        raise RuntimeError(f"FFmpeg encode failed with code {rc}")


# ---------------------------------------------------------------------------
# Multi-Frame QA Sheet Generator
# ---------------------------------------------------------------------------
def build_qa_sheet(sid: str, cfg: dict[str, Any], final_mp4: Path, duration: float) -> Path:
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    qa_path = PREVIEW_DIR / cfg["qa_name"]

    t_bridge = (cfg["seg1_frames"] + cfg["bridge_frames"] * 0.5) / FPS
    t_kratos = (cfg["seg1_frames"] + cfg["bridge_frames"]) / FPS + 1.35
    total_frames = cfg["seg1_frames"] + cfg["bridge_frames"] + cfg["seg2_frames"]
    t_loop_end = min(duration - 0.08, (total_frames - 1.5) / FPS)

    checkpoints = [
        (0.10, "t=0.10s | Split-Screen Clash Opener"),
        (2.50, "t=2.50s | Chief Kinetic Caption"),
        (t_bridge, f"t={t_bridge:.2f}s | Beat-Matched Bridge"),
        (t_kratos, f"t={t_kratos:.2f}s | Kratos Explosion Pop"),
        (duration - 1.50, f"t={duration - 1.50:.2f}s | Related Video Pointer"),
        (t_loop_end, f"t={t_loop_end:.2f}s | Seamless Loop Cut"),
    ]

    cw, ch = 540, 960
    hdr_h = 44
    cols, rows = 3, 2
    sheet = Image.new("RGB", (cols * cw, rows * (ch + hdr_h)), (18, 18, 20))
    draw = ImageDraw.Draw(sheet)
    f_hdr = ImageFont.truetype(IMPACT_PATH, 24)

    for idx, (ts, label) in enumerate(checkpoints):
        r, c = divmod(idx, cols)
        x0, y0 = c * cw, r * (ch + hdr_h)
        tmp_png = final_mp4.parent / f"_qa_tmp_{idx}.png"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-v",
                "error",
                "-ss",
                f"{max(0.0, ts):.3f}",
                "-i",
                str(final_mp4),
                "-frames:v",
                "1",
                "-vf",
                f"scale={cw}:{ch}:flags=lanczos",
                str(tmp_png),
            ],
            check=True,
        )
        im = Image.open(tmp_png).convert("RGB")
        tmp_png.unlink(missing_ok=True)

        draw.rectangle([x0, y0, x0 + cw, y0 + hdr_h], fill=(28, 28, 32))
        draw.text((x0 + 14, y0 + hdr_h // 2), f"{sid} · {label}", font=f_hdr, fill=(245, 197, 24), anchor="lm")
        sheet.paste(im, (x0, y0 + hdr_h))
        draw.rectangle([x0, y0, x0 + cw - 1, y0 + hdr_h + ch - 1], outline=(60, 60, 66), width=1)

    sheet.save(qa_path, quality=92)
    return qa_path


def probe_summary(mp4_path: Path) -> str:
    out = subprocess.check_output(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "stream=codec_type,codec_name,width,height,r_frame_rate,sample_rate,channels",
            "-show_entries",
            "format=duration,size",
            "-of",
            "json",
            str(mp4_path),
        ],
        text=True,
    )
    info = json.loads(out)
    v_s = next(s for s in info["streams"] if s["codec_type"] == "video")
    a_s = next(s for s in info["streams"] if s["codec_type"] == "audio")
    dur = float(info["format"]["duration"])
    mb = int(info["format"]["size"]) / (1024 * 1024)
    return (
        f"{v_s['width']}x{v_s['height']} @{v_s['r_frame_rate']} {v_s['codec_name']} + "
        f"{a_s['codec_name']} {a_s['sample_rate']}Hz {a_s['channels']}ch | {dur:.3f}s ({mb:.2f} MB)"
    )


def build_one(
    sid: str,
    all_words: list[dict[str, Any]],
    clips_meta: dict[str, Any],
    shifts: dict[str, float],
    renderer: OverlayRenderer,
    dry_check: bool = False,
) -> None:
    cfg = SHORTS_V2_CFG[sid]
    s_dir = EP_DIR / "shorts" / sid
    s_work = s_dir / "work"
    s_final = s_dir / "final"
    s_work.mkdir(parents=True, exist_ok=True)
    s_final.mkdir(parents=True, exist_ok=True)

    master_wav = s_work / "audio_master_v2.wav"
    graded_mp4 = s_work / "graded_video_v2.mp4"
    final_mp4 = s_final / f"Kratos_vs_Master_Chief_Short_{sid}_1080p_胶片版.mp4"

    print(f"\n=== {'Dry-checking' if dry_check else 'Building'} {sid} ===")
    aud_dur = build_master_audio(cfg, master_wav)
    schedule = build_caption_schedule(cfg, all_words)
    (s_work / "captions_v2.json").write_text(json.dumps(schedule, indent=2, default=list), encoding="utf-8")

    # Verify all overlay safe-zone assertions across all chunks & modes
    for ch in schedule:
        for w_i in range(len(ch["word_windows"])):
            renderer.render_caption(ch, w_i, opener_mode=False)
            if ch["t0"] < cfg["opener"]["frames"] / FPS:
                renderer.render_caption(ch, w_i, opener_mode=True)
    for dy in (-1, 0, 1):
        renderer.render_related_pointer(dy=dy)

    expected_total = cfg["seg1_frames"] + cfg["bridge_frames"] + cfg["seg2_frames"]
    sum_shots = cfg["opener"]["frames"] + sum(s["frames"] for s in cfg["shots_after_opener"])
    assert sum_shots == expected_total, f"{sid}: shot frames {sum_shots} != {expected_total}"
    print(f"   Audio + Caption + Safe-Zone Check OK ({expected_total} frames = {aud_dur:.3f}s, {len(schedule)} chunks)")
    if dry_check:
        return

    total_frames = build_graded_video(cfg, clips_meta, shifts, graded_mp4)
    composite_overlays_and_encode(cfg, graded_mp4, master_wav, schedule, total_frames, renderer, final_mp4)
    graded_mp4.unlink(missing_ok=True)

    qa_path = build_qa_sheet(sid, cfg, final_mp4, aud_dur)
    print(f"✅ Rendered: {final_mp4}")
    print(f"   Probe   : {probe_summary(final_mp4)}")
    print(f"   QA Sheet: {qa_path}")


def main() -> None:
    args = [a for a in sys.argv[1:] if a != "--dry-check"]
    dry_check = "--dry-check" in sys.argv[1:]
    wanted = args or list(SHORTS_V2_CFG.keys())
    all_words = load_normalized_words()
    clips_meta = {c["id"]: c for c in json.loads((WORK_DIR / "clips.json").read_text(encoding="utf-8"))}
    shifts_p = WORK_DIR / "shifts.json"
    shifts = json.loads(shifts_p.read_text(encoding="utf-8")) if shifts_p.exists() else {}
    renderer = OverlayRenderer()

    for sid in wanted:
        if sid not in SHORTS_V2_CFG:
            raise SystemExit(f"Unknown Short ID: {sid} (available: {list(SHORTS_V2_CFG)})")
        build_one(sid, all_words, clips_meta, shifts, renderer, dry_check=dry_check)


if __name__ == "__main__":
    main()
