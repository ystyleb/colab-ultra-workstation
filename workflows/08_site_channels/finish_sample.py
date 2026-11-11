#!/usr/bin/env python3
"""08 号样片后期（本地 0 CCU）：按帧截取 → 1080×1920 → 顶部署名 → 音频首尾短淡入淡出。

H3 FL2VA 的已知现象：首尾几帧是原图定格，接到生成内容时会跳一下（相邻帧差约 8，正常运动约 1.5）。
所以截取范围要按帧差选（见 README「样片」一节），不是固定值。

    python3 workflows/08_site_channels/finish_sample.py -i raw.mp4 -o final.mp4 --start 5 --end 186 \
        --credit "Portrait: PawMotif · Motion: AI video" --font workflows/08_site_channels/fonts/dmsans.ttf --color 303c33
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--input", required=True)
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--start", type=int, required=True, help="保留的第一帧（含）")
    ap.add_argument("--end", type=int, required=True, help="保留的最后一帧（含）")
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--credit", default="")
    ap.add_argument("--font", default=str(Path(__file__).resolve().parent / "fonts" / "dmsans.ttf"))
    ap.add_argument("--color", default="303c33", help="署名文字色（hex，不带 #）")
    ap.add_argument("--box", default="f8f6f0", help="署名底色（hex）")
    ap.add_argument("--fade", type=float, default=0.08, help="音频首尾淡入淡出秒数，防循环接缝爆音")
    ap.add_argument("--audio", default=None, help="替换音轨（如 Songifted 示例歌）；不给则用 H3 原生音轨")
    ap.add_argument("--audio-start", type=float, default=0.0, help="替换音轨从第几秒开始截")
    ap.add_argument("--audio-fade-out", type=float, default=0.4, help="替换音轨结尾淡出秒数")
    args = ap.parse_args()

    t0 = args.start / args.fps
    dur = (args.end - args.start + 1) / args.fps
    vf = [f"trim=start_frame={args.start}:end_frame={args.end + 1}", "setpts=PTS-STARTPTS", "scale=1080:1920:flags=lanczos"]
    if args.credit:
        txt = args.credit.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
        vf.append(
            f"drawtext=fontfile='{args.font}':text='{txt}':fontsize=34:fontcolor=0x{args.color}"
            f":x=(w-text_w)/2:y=96:box=1:boxcolor=0x{args.box}@0.82:boxborderw=14"
        )
    if args.audio:
        a0, fo = args.audio_start, args.audio_fade_out
        af = f"[1:a]atrim=start={a0:.4f}:duration={dur:.4f},asetpts=PTS-STARTPTS,afade=t=in:d=0.05,afade=t=out:st={dur - fo:.4f}:d={fo}[a]"
    else:
        af = f"[0:a]atrim=start={t0:.4f}:duration={dur:.4f},asetpts=PTS-STARTPTS,afade=t=in:d={args.fade},afade=t=out:st={dur - args.fade:.4f}:d={args.fade}[a]"
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    inputs = ["-i", args.input] + (["-i", args.audio] if args.audio else [])
    cmd = [
        "ffmpeg", "-v", "error", "-y", *inputs,
        "-filter_complex", "[0:v]" + ",".join(vf) + "[v];" + af, "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", args.output,
    ]
    subprocess.run(cmd, check=True)
    print(f"✅ {args.output} ({dur:.2f}s, 帧 {args.start}–{args.end})")


if __name__ == "__main__":
    main()
