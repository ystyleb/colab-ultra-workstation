#!/usr/bin/env python3
"""H3 片段筛片：硬切检测 + 联系表（0 CCU，本地跑）。

python3 workflows/08_site_channels/screen_takes.py out/samples/songifted_nora            # 全部片段
python3 workflows/08_site_channels/screen_takes.py out/samples/songifted_nora N01 N02    # 只看这些前缀

- 硬切：逐帧灰度差，某帧 > 95 分位 × 4 且 > 12 记为一次跳变（首尾各 6 帧是定格段跳入/跳出，单独标出不算）。
- 「首帧 = 尾帧」的镜头 H3 爱自己推成特写再硬切回来（README「H3 选片规律」），硬切数 ≥1 就要换 seed。
- 中位帧差 > 1.8 = 整段都在大幅运动（多半是推近；Nora N06 推近再拉回只有 2.09，稳的镜头 0.5–1.0），要看联系表确认；推近本身看不出帧差，只能看联系表：每 12 帧一格，写到 <clips>/sheets/<id>.jpg。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np

W, H = 96, 54


def frames(path: Path) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vf", f"scale={W}:{H},format=gray", "-f", "rawvideo", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, H, W).astype(np.float32)


def screen(path: Path) -> dict:
    f = frames(path)
    d = np.abs(np.diff(f, axis=0)).mean(axis=(1, 2))
    med = float(np.median(d)) or 0.01
    p95 = float(np.percentile(d, 95))
    edge = 6
    # 硬切是孤立尖峰：推近时中位差本身就高（N01 中位 4.4、硬切 32.8、次高 7.0），所以和 95 分位比，不和中位数比
    jumps = [(i + 1, round(float(v), 1)) for i, v in enumerate(d) if v > max(12, p95 * 4)]
    inner = [j for j in jumps if edge <= j[0] < len(f) - edge]
    # 和首帧的差：中段远大于两端 = 中途换了景别（推近/切特写）又回来
    to_first = np.abs(f - f[0]).mean(axis=(1, 2))
    return {"n": len(f), "median": round(med, 2), "cuts": inner, "edge_jumps": [j for j in jumps if j not in inner],
            "max_drift": round(float(to_first.max()), 1), "end_drift": round(float(to_first[-1]), 1)}


def sheet(path: Path, out: Path):
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(path), "-vf", "select='not(mod(n\\,12))',scale=336:-1,tile=5x4",
                    "-frames:v", "1", str(out)], check=True)


def main():
    clips = Path(sys.argv[1]).resolve()
    pref = sys.argv[2:]
    for p in sorted(clips.glob("*_Master.mp4")):
        jid = p.name.removesuffix("_Master.mp4")
        if pref and not any(jid.startswith(x) for x in pref):
            continue
        r = screen(p)
        sheet(p, clips / "sheets" / f"{jid}.jpg")
        flag = "❌ 硬切" if r["cuts"] else ("⚠️ 运镜大" if r["median"] > 1.8 else "✅")
        print(f"{flag:6} {jid:22} {r['n']:4}f  中位差 {r['median']:5}  中途最大偏离首帧 {r['max_drift']:5}  硬切 {r['cuts'] or '-'}")


if __name__ == "__main__":
    main()
