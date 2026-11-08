# -*- coding: utf-8 -*-
"""Step 8 - assemble a draft from the accepted takes (work/edl.json + work/picks.json + work/shifts.json).

usage: python scripts/assemble.py <episode_dir> [--from 0] [--to END] [--out preview/草稿.mp4]
  * lip-sync clips are placed so their audio lines up with the song; if a clip is too short the LAST FRAME IS HELD -
    never slide it earlier, that breaks the lip sync
  * work/shifts.json: seconds to play a clip's picture earlier (H3 started the song late / the mouth trails)
  * a clip without an accepted take shows as dark grey, so the rhythm is visible before everything exists
  * picks.json may name any take: {"A07": 2}; edl.json may use "B_REACT@1" style ids to force a take as a cutaway
"""
import argparse
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import jload  # noqa: E402

W, H, FPS = 1344, 768, 24


def duration(f):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f]))


def fx_chain(fx, t_from, src, dst):
    """Edit-time effects from work/fx.json (times on the song timeline):
      {"type": "punch", "t0", "t1", "amount": 0.1}   fast digital push-in (0.08 s ease) held until t1
      {"type": "shake", "t0", "t1", "px": 10}         camera shake (needs a small zoom margin, added automatically)
      {"type": "flash", "t0", "t1", "alpha": 0.8}     white flash
      {"type": "dark",  "t0", "t1", "amount": 0.15}   pull brightness down
    An empty list is a pass-through, so episodes without fx.json render exactly as before."""
    if not fx:
        return "[%s]null[%s]" % (src, dst)

    def win(x):
        return "between(t,%.3f,%.3f)" % (x["t0"] - t_from, x["t1"] - t_from)

    zoom = ["1"]
    for x in fx:
        if x["type"] == "punch":
            zoom.append("if(%s,%.3f*min(1,(t-%.3f)/0.08),0)" % (win(x), x.get("amount", 0.1), x["t0"] - t_from))
        elif x["type"] == "shake":
            zoom.append("if(%s,0.03,0)" % win(x))
    z = "+".join(zoom)
    dx = "+".join(["0"] + ["if(%s,%d*sin(t*97),0)" % (win(x), x.get("px", 10)) for x in fx if x["type"] == "shake"])
    dy = "+".join(["0"] + ["if(%s,%d*cos(t*83),0)" % (win(x), x.get("px", 10)) for x in fx if x["type"] == "shake"])
    chain = ["[%s]scale=w='trunc(%d*(%s)/2)*2':h='trunc(%d*(%s)/2)*2':eval=frame,"
             "crop=%d:%d:x='(iw-%d)/2+(%s)':y='(ih-%d)/2+(%s)'" % (src, W, z, H, z, W, H, W, dx, H, dy)]
    for x in fx:
        if x["type"] == "dark":
            chain.append("eq=brightness=%.3f:enable='%s'" % (-x.get("amount", 0.15), win(x)))
    parts = [",".join(chain) + "[fx0]"]
    last = "fx0"
    for i, x in enumerate(f for f in fx if f["type"] == "flash"):
        parts.append("color=c=white:s=%dx%d:r=%d,format=rgba,colorchannelmixer=aa=%.2f[wf%d]" % (W, H, FPS, x.get("alpha", 0.8), i))
        parts.append("[%s][wf%d]overlay=shortest=1:enable='%s'[fl%d]" % (last, i, win(x), i))
        last = "fl%d" % i
    parts.append("[%s]setsar=1[%s]" % (last, dst))
    return ";".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ep")
    ap.add_argument("--from", dest="t0", type=float, default=0.0)
    ap.add_argument("--to", dest="t1", type=float, default=None)
    ap.add_argument("--out", default="preview/草稿.mp4")
    a = ap.parse_args()
    ep = a.ep
    work = os.path.join(ep, "work")
    edl = jload(os.path.join(work, "edl.json"))
    clips = {c["id"]: c for c in jload(os.path.join(work, "clips.json"))}
    picks = jload(os.path.join(work, "picks.json")) if os.path.exists(os.path.join(work, "picks.json")) else {}
    shifts = jload(os.path.join(work, "shifts.json")) if os.path.exists(os.path.join(work, "shifts.json")) else {}
    t_end = a.t1 if a.t1 is not None else edl[-1]["t1"]
    inputs, filters, report, n = [], [], [], 0
    for x in edl:
        st, en = max(x["t0"], a.t0), min(x["t1"], t_end)
        if en - st < 0.02:
            continue
        dur = en - st
        cid, take = x["clip"], None
        if "@" in cid:
            cid, take = cid.split("@")
        take = take or picks.get(cid)
        f = os.path.join(ep, "clips", "%s_t%s.mp4" % (cid, take)) if take else None
        if f and os.path.exists(f):
            c = clips[cid]
            if x["in"] is None:                       # lip-sync: clip time 0 = audio start (minus lead)
                src = x["t0"] - (c["audio"][0] - c.get("lead", 0.0)) + shifts.get(cid, 0.0) + (st - x["t0"])
            else:
                src = x["in"] + (st - x["t0"])
            # negative shift (picture later) can push src before the clip start: hold the first frame instead
            head = max(0.0, -src) if x["in"] is None else 0.0
            src = max(0.0, src)
            pad, clen = 0.0, duration(f)
            if src + dur - head > clen - 0.04:
                if x["in"] is None:
                    pad = src + dur - head - (clen - 0.04)
                else:
                    src = max(0.0, clen - 0.04 - dur)
            inputs += ["-ss", "%.3f" % src, "-t", "%.3f" % (dur + 0.2), "-i", f]
            filters.append("[%d:v]tpad=start_mode=clone:start_duration=%.3f:stop_mode=clone:stop_duration=%.3f,"
                           "trim=0:%.3f,setpts=PTS-STARTPTS,fps=%d,"
                           "scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d,setsar=1[v%d]"
                           % (n, head, pad + 0.1, dur, FPS, W, H, W, H, n))
            report.append("%6.2f-%6.2f %-8s t%s @%.2f" % (st, en, cid, take, src))
        else:
            inputs += ["-f", "lavfi", "-t", "%.3f" % dur, "-i", "color=c=0x202020:s=%dx%d:r=%d" % (W, H, FPS)]
            filters.append("[%d:v]setsar=1[v%d]" % (n, n))
            report.append("%6.2f-%6.2f %-8s (not generated yet)" % (st, en, cid))
        n += 1
    inputs += ["-ss", "%.3f" % a.t0, "-t", "%.3f" % (t_end - a.t0), "-i", os.path.join(work, "music_final.wav")]
    fc = ";".join(filters) + ";" + "".join("[v%d]" % i for i in range(n)) + "concat=n=%d:v=1:a=0[cat]" % n
    fx_p = os.path.join(work, "fx.json")
    fc += ";" + fx_chain(jload(fx_p) if os.path.exists(fx_p) else [], a.t0, "cat", "v")
    out = os.path.join(ep, a.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error"] + inputs + ["-filter_complex", fc, "-map", "[v]", "-map", "%d:a" % n,
                    "-c:v", "libx264", "-crf", "20", "-preset", "fast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                    "-shortest", out], check=True)
    if a.out == "preview/草稿.mp4":
        import shutil
        shutil.copy(out, os.path.join(ep, "preview/成片_拼接.mp4"))
    print("\n".join(report))
    print("wrote", out)


if __name__ == "__main__":
    main()
