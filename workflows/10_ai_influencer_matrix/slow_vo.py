#!/usr/bin/env python3
"""配音放慢（0 CCU，本地）：句间停顿加长 + 整体变速。2026-11-18 用户试听后选的「B」。

原配音平均 Wen 191 / Vivian 171 / June 165 wpm，对 60–70 岁的人设太快。做法：
1. 停顿加长：静音段 >= 0.35s（句号）+0.35s，更短的（逗号）+0.15s，插在静音段中点
2. 整体变速 atempo：Wen 0.84、Vivian 0.92、June 0.94（目标 ~145–155 wpm）
原文件先备份到 work/tts/_fast/（已存在则从备份读，重复运行不会越放越慢）。
J09 当初为塞进 15.08s 加速过 1.06 倍，原始版在 work/tts/_orig/，从那里读。
放慢后要重跑 make_cta_cuts.py，并且 H3 口型素材必须全部重出（嘴型是按旧配音生成的）。
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import wave
from pathlib import Path

import numpy as np

from subtitle_and_finalize import detect_pauses

HERE = Path(__file__).resolve().parent
TTS_DIR = HERE / "work" / "tts"
FAST_DIR = TTS_DIR / "_fast"
ORIG_DIR = TTS_DIR / "_orig"
TEMPO = {"W": 0.84, "V": 0.92, "J": 0.94}
LONG_GAP, SHORT_GAP = 0.35, 0.15


def slow_one(clip_id: str) -> tuple[float, float]:
    dst = TTS_DIR / f"{clip_id}.wav"
    FAST_DIR.mkdir(parents=True, exist_ok=True)
    backup = FAST_DIR / f"{clip_id}.wav"
    if not backup.exists():
        shutil.copy2(dst, backup)
    src = ORIG_DIR / f"{clip_id}.wav" if (ORIG_DIR / f"{clip_id}.wav").exists() else backup
    with wave.open(str(src)) as w:
        sr, ch, sw = w.getframerate(), w.getnchannels(), w.getsampwidth()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    assert ch == 1 and sw == 2, f"{src} 不是 16-bit 单声道"
    total = len(x) / sr
    pieces, last = [], 0
    for s, e in detect_pauses(src, noise_db=-35, min_sil=0.15):
        if s < 0.5 or e > total - 0.05:  # 开头静音和结尾静音不动
            continue
        mid = int((s + e) / 2 * sr)
        pieces += [x[last:mid], np.zeros(int((LONG_GAP if e - s >= 0.35 else SHORT_GAP) * sr), dtype=np.int16)]
        last = mid
    pieces.append(x[last:])
    tmp = TTS_DIR / f"_{clip_id}_gap.wav"
    with wave.open(str(tmp), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(np.concatenate(pieces).tobytes())
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(tmp), "-af", f"atempo={TEMPO[clip_id[0]]}", "-ar", str(sr), str(dst)], check=True)
    tmp.unlink()
    out = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(dst)], text=True))
    return total, out


def main() -> None:
    ap = argparse.ArgumentParser(description="配音放慢：停顿加长 + 整体变速")
    ap.add_argument("--ids", default="")
    args = ap.parse_args()
    ids = [x.strip() for x in args.ids.split(",") if x.strip()] or sorted(
        p.stem for p in (FAST_DIR.glob("[VJW][0-9][0-9].wav") if FAST_DIR.exists() and any(FAST_DIR.iterdir()) else TTS_DIR.glob("[VJW][0-9][0-9].wav"))
    )
    for i in ids:
        a, b = slow_one(i)
        print(f"{i}: {a:5.2f}s -> {b:5.2f}s (x{TEMPO[i[0]]})", flush=True)


if __name__ == "__main__":
    main()
