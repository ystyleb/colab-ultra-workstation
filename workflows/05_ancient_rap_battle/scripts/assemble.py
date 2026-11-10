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


def live_cam(live, seed, dur, push, whip_in, whip_out):
    """Per-shot virtual camera operator (work/live.json): handheld sway + slow push/pull + whip pans.
    Sway is a sum of low-frequency sines (breathing / weight shifts, ~0.2-1.7 Hz), not jitter; each shot gets its own
    phases so consecutive shots don't move identically. Returns a filter fragment working on a WxH stream."""
    import math
    import random
    r = random.Random(seed)
    px, drift, wd = live.get("handheld_px", 10), live.get("drift", 0.04), live.get("whip_secs", 0.12)
    m = 1.0 + live.get("margin", 0.06)

    def sway(amp):
        terms = []
        for f, a in ((0.23, 1.0), (0.61, 0.55), (1.7, 0.18)):
            terms.append("%.2f*sin(%.4f*t+%.3f)" % (amp * a, 2 * math.pi * f * r.uniform(0.8, 1.25), r.uniform(0, 6.283)))
        return "+".join(terms)

    z = ("%.4f+%.4f*(t/%.3f)" if push else "%.4f+%.4f*(1-t/%.3f)") % (m, drift, dur)  # push-in or pull-out
    dx, dy = sway(px), sway(px * 0.6)
    wz = []
    # whip pan: the camera swings away at the end of the outgoing shot and lands in from the other side
    if whip_out:
        p = "pow(max(0,(t-%.3f)/%.3f),2)" % (dur - wd, wd)
        dx += "+%d*%s" % (whip_out * int(W * 0.16), p)
        wz.append("0.34*%s" % p)
    if whip_in:
        p = "pow(max(0,1-t/%.3f),2)" % wd
        dx += "+%d*%s" % (-whip_in * int(W * 0.16), p)
        wz.append("0.34*%s" % p)
    if wz:
        z += "+" + "+".join(wz)
    s = ("scale=w='trunc(%d*(%s)/2)*2':h='trunc(%d*(%s)/2)*2':eval=frame,"
         "crop=%d:%d:x='(iw-%d)/2+(%s)':y='(ih-%d)/2+(%s)'" % (W, z, H, z, W, H, W, dx, H, dy))
    for on, win in ((whip_out, "gte(t,%.3f)" % (dur - wd)), (whip_in, "lte(t,%.3f)" % wd)):
        if on:
            s += ",avgblur=sizeX=48:sizeY=1:enable='%s'" % win
    return s


def live_grade(live, t_from, beat0, beat):
    """Whole-film look shared by every shot: one grade, stage lights pulsing on the beat, vignette, film grain."""
    g = ["eq=contrast=%.3f:saturation=%.3f:gamma=0.97" % (live.get("contrast", 1.07), live.get("saturation", 0.9)),
         "colorbalance=rs=-0.04:bs=0.05:rh=0.05:bh=-0.04",
         "eq=brightness='%.3f*exp(-9*mod(t+%.3f-%.3f,%.4f))':eval=frame" % (live.get("beat_pulse", 0.03), t_from, beat0, beat),
         "vignette=angle=%.3f" % live.get("vignette", 0.55),
         "noise=alls=%d:allf=t" % live.get("grain", 7)]
    if not live.get("vignette", 0.55):   # live.json "vignette": 0 = no vignette (bright, warm episodes)
        g.pop(3)
    if not live.get("cool", True):       # live.json "cool": false = skip the teal/orange colour balance
        g.pop(1)
    return ",".join(g)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ep")
    ap.add_argument("--from", dest="t0", type=float, default=0.0)
    ap.add_argument("--to", dest="t1", type=float, default=None)
    ap.add_argument("--out", default="preview/草稿.mp4")
    ap.add_argument("--size", default=None, help="WxH output, e.g. 768x1344 for 9:16 Shorts (default 1344x768)")
    a = ap.parse_args()
    global W, H
    if a.size:
        W, H = (int(v) for v in a.size.lower().split("x"))
    ep = a.ep
    work = os.path.join(ep, "work")
    edl = jload(os.path.join(work, "edl.json"))
    clips = {c["id"]: c for c in jload(os.path.join(work, "clips.json"))}
    picks = jload(os.path.join(work, "picks.json")) if os.path.exists(os.path.join(work, "picks.json")) else {}
    shifts = jload(os.path.join(work, "shifts.json")) if os.path.exists(os.path.join(work, "shifts.json")) else {}
    t_end = a.t1 if a.t1 is not None else edl[-1]["t1"]
    live_p = os.path.join(work, "live.json")
    live = jload(live_p) if os.path.exists(live_p) else None

    def subject(x):
        c = clips.get(x["clip"].split("@")[0], {})
        return c.get("who", "a") if c.get("kind") == "rap" else "react"

    subj = [subject(x) for x in edl]
    words_p = os.path.join(work, "words_edit.json")
    words, tag = [], False
    for w in (jload(words_p) if os.path.exists(words_p) else []):  # keep only the rapper's words:
        tag = tag or w["w"].startswith("[")                         # drop [Section: ...] tags
        if not tag and not w["w"].strip("!?,.").isupper():          # and shouted crowd words (OOOH!)
            words.append(w)
        tag = tag and not w["w"].endswith("]")
    swing = {"a": -1, "b": 1}

    def cam(i, x, st, en, dur):
        if not live:
            return ""
        # whip only on a real subject change, only where this render contains the cut, and never over a sung word
        # on a lip-sync shot (user rule: a line is never blurred/cut away while it is being sung)
        wd = live.get("whip_secs", 0.12)

        def free(a0, a1):
            return subj[i] == "react" or not any(w["t0"] < a1 and w["t1"] > a0 for w in words)
        w_in = (swing.get(subj[i], 1) if live.get("whip", True) and i > 0 and subj[i] != subj[i - 1]
                and st == x["t0"] and free(x["t0"], x["t0"] + wd) else 0)
        w_out = (swing.get(subj[i + 1], 1) if live.get("whip", True) and i + 1 < len(edl) and subj[i] != subj[i + 1]
                 and en == x["t1"] and free(x["t1"] - wd, x["t1"]) else 0)
        if w_in or w_out:
            report.append("        whip %s %s%s" % (x["clip"], "in " if w_in else "", "out" if w_out else ""))
        # clips that already carry a real camera move ask for less virtual sway / drift (clip keys "sway", "drift")
        c = clips.get(x["clip"].split("@")[0], {})
        lv = dict(live, handheld_px=live.get("handheld_px", 10) * c.get("sway", 1.0), drift=c.get("drift", live.get("drift", 0.04)))
        return "," + live_cam(lv, x["clip"] + str(i), dur, subj[i] != "react", w_in, w_out)
    inputs, filters, report, n = [], [], [], 0
    for i, x in enumerate(edl):
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
                           "scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d%s,setsar=1[v%d]"
                           % (n, head, pad + 0.1, dur, FPS, W, H, W, H, cam(i, x, st, en, dur), n))
            report.append("%6.2f-%6.2f %-8s t%s @%.2f" % (st, en, cid, take, src))
        else:
            inputs += ["-f", "lavfi", "-t", "%.3f" % dur, "-i", "color=c=0x202020:s=%dx%d:r=%d" % (W, H, FPS)]
            filters.append("[%d:v]setsar=1[v%d]" % (n, n))
            report.append("%6.2f-%6.2f %-8s (not generated yet)" % (st, en, cid))
        n += 1
    inputs += ["-ss", "%.3f" % a.t0, "-t", "%.3f" % (t_end - a.t0), "-i", os.path.join(work, "music_final.wav")]
    fc = ";".join(filters) + ";" + "".join("[v%d]" % i for i in range(n)) + "concat=n=%d:v=1:a=0[cat]" % n
    fx_p = os.path.join(work, "fx.json")
    fc += ";" + fx_chain(jload(fx_p) if os.path.exists(fx_p) else [], a.t0, "cat", "fxo" if live else "v")
    if live:
        grid = jload(os.path.join(work, "grid.json"))
        fc += ";[fxo]" + live_grade(live, a.t0, grid["beat0"], 60.0 / grid["bpm"]) + "[v]"
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
