# -*- coding: utf-8 -*-
"""Build vertical (9:16) YouTube Shorts as mini-episodes under shorts/<sid>/.

usage: python3 build_shorts.py [sid ...]        (default: every short in SHORTS)

Each short re-uses one rapper's 4-line run from the full song but renders its own lip-sync clips natively at 768x1344
(user decision 2026-11-09: render vertical, never crop the 16:9 master). Everything is re-timed so the short starts
at 0 s: music / vocals are cut, lines / words / grid / fx / edl shifted. After that the normal pipeline applies:

  python3 ../../run_rap_battle_remote.py shorts/<sid> --runner-args "--fit --lock-strength 1.0 --mic stand --static-cam" --no-post
  python3 ../../scripts/assemble.py shorts/<sid> --size 768x1344
  python3 ../../scripts/package.py shorts/<sid>
"""
import json
import os
import shutil
import subprocess
import sys

EP = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(EP, "work")
# cut-before-first-word, lead-in before the first line, hold after the last word (the song keeps playing; the last
# lyric stays up 0.5 s and the 1.2 s end card follows it, so TAIL must be >= 1.7 or the card covers the last line)
PRE, HEAD, TAIL = 0.08, 0.35, 1.8

SHORTS = {
    "s1_four_cents": ["A05", "A06", "A07", "A08"],
    "s2_liar": ["B05", "B06", "B07", "B08"],
    "s3_finale": ["B13", "B14", "B15", "B16"],
}
# opener shown over the first seconds so a cold viewer knows what this is (user 2026-11-09); replaces the name cards
HOOK_SUB = {
    "s1_four_cents": "AI RAP BATTLE  ·  EDISON ROASTS TESLA",
    "s2_liar": "AI RAP BATTLE  ·  TESLA FIRES BACK",
    "s3_finale": "AI RAP BATTLE  ·  TESLA'S FINAL VERSE",
}
V_HAND = ("A handheld camera at eye level with a subtle natural sway holds a vertical waist-up shot of him, slowly "
          "arcing a few degrees around him, his face and lips large in the upper half of the tall 9:16 frame")
V_CREEP = ("A handheld camera with a subtle natural sway starts on a vertical waist-up shot at eye level and gently "
           "creeps closer to a head-and-shoulders close-up, his face and lips large in the upper half of the tall 9:16 "
           "frame from the first frame")


def j(p):
    return json.load(open(p, encoding="utf-8"))


def dump(obj, p):
    json.dump(obj, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def cut(src, dst, t0, t1):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", "%.3f" % t0, "-t", "%.3f" % (t1 - t0), "-i", src,
                    "-c:a", "pcm_s16le", dst], check=True)


def build(sid, ids):
    e = j(os.path.join(EP, "episode.json"))
    L = j(os.path.join(WORK, "lines.json"))
    words = j(os.path.join(WORK, "words_edit.json"))
    grid = j(os.path.join(WORK, "grid.json"))
    fx = j(os.path.join(WORK, "fx.json"))
    main = {c["id"]: c for c in j(os.path.join(WORK, "clips.json"))}
    lid = lambda l: ("A" if l["who"] == "a" else "B") + "%02d" % l["n"]   # noqa: E731
    lines = [l for l in L if lid(l) in ids]
    assert [lid(l) for l in lines] == ids, "short lines must be consecutive in the song: %s" % ids
    nxt = L[L.index(lines[-1]) + 1]["start"] if L.index(lines[-1]) + 1 < len(L) else grid["length"]
    # the rapper's own words only (no [section] tags, no shouted crowd words)
    sung = [w for w in words if lines[0]["start"] - 0.1 <= w["t0"] < nxt - 0.05 and not w["w"].startswith("[")
            and not w["w"].strip("!?,.").isupper()]
    t0 = round(lines[0]["start"] - HEAD, 3)
    t1 = round(min(max(w["t1"] for w in sung) + TAIL, grid["length"]), 3)
    sh = lambda t: round(t - t0, 3)   # noqa: E731

    d = os.path.join(EP, "shorts", sid)
    for sub in ("work", "refs", "clips"):
        os.makedirs(os.path.join(d, sub), exist_ok=True)
    # refs the runner copies to ComfyUI: face crops + stage plates + venue
    for f in ("a_face_clean.png", "b_face_clean.png", "stage_a.png", "stage_b.png"):
        shutil.copy2(os.path.join(WORK, f), os.path.join(d, "work", f))
    shutil.copy2(os.path.join(EP, "refs", "venue.png"), os.path.join(d, "refs", "venue.png"))
    for f in ("music_final.wav", "vocals_final.wav"):
        cut(os.path.join(WORK, f), os.path.join(d, "work", f), t0, t1)

    se = dict(e, title="%s_Short_%s" % (e["title"], sid), title_card=False, name_cards=False, end_card_secs=1.2,
              end_question="FULL BATTLE|ON THE CHANNEL", show_notes=False,
              hook={"a": e["a"]["name_cn"], "b": e["b"]["name_cn"], "sub": HOOK_SUB[sid], "secs": 2.6})
    se.pop("structure", None)
    dump(se, os.path.join(d, "episode.json"))
    dump([dict(l, start=sh(l["start"]), end=sh(l["end"])) for l in lines], os.path.join(d, "work", "lines.json"))
    dump([dict(w, t0=sh(w["t0"]), t1=sh(w["t1"])) for w in words if t0 <= w["t0"] < t1], os.path.join(d, "work", "words_edit.json"))
    beat = 60.0 / grid["bpm"]
    dump(dict(grid, beat0=round((grid["beat0"] - t0) % beat, 4), length=round(t1 - t0, 3), keep=[[0.0, round(t1 - t0, 3)]]),
         os.path.join(d, "work", "grid.json"))
    # only effects that START inside these lines (a shake / flash spilling in from a neighbouring line or the outro cut
    # belongs to that cut); punch-ins are dropped because the vertical shots carry their own camera moves
    sung_end = max(w["t1"] for w in sung)
    dump([dict(x, t0=sh(x["t0"]), t1=sh(min(x["t1"], t1))) for x in fx if t0 <= x["t0"] < sung_end
          and x["type"] != "punch"], os.path.join(d, "work", "fx.json"))
    shutil.copy2(os.path.join(WORK, "live.json"), os.path.join(d, "work", "live.json"))

    clips, edl = [], []
    last_end = {}
    for i, l in enumerate(lines):
        c = dict(main[lid(l)])
        creep = c["cam"].startswith("A handheld camera with a subtle natural sway starts on")
        me = c["image_keys"][0]
        plate = "stage_a" if l["who"] == "a" else "stage_b"
        for k in ("wide", "listener", "closeup_lora"):
            c.pop(k, None)
        a0, a1 = c["audio"]
        c.update(aspect="9:16", two_shot=False, cam=V_CREEP if creep else V_HAND, static=False, bg=plate,
                 image_keys=[me, plate], audio=[sh(a0), sh(a1)], sway=0.5, drift=0.0 if creep else 0.02)
        clips.append(c)
        lw = max(w["t1"] for w in sung if l["start"] - 0.1 <= w["t0"] < (lines[i + 1]["start"] - 0.05 if i + 1 < len(lines) else nxt))
        last_end[c["id"]] = sh(lw)
    for i, c in enumerate(clips):
        s0 = 0.0 if i == 0 else edl[-1]["t1"]
        if i + 1 < len(clips):
            s1 = round(max(clips[i + 1]["audio"][0], last_end[c["id"]] + 0.02), 3)   # never cut a line mid-word
        else:
            s1 = round(t1 - t0, 3)
        edl.append({"t0": s0, "t1": s1, "clip": c["id"], "in": None})
        assert s1 >= last_end[c["id"]] - 0.05, (c["id"], s1, last_end[c["id"]])
    dump(clips, os.path.join(d, "work", "clips.json"))
    dump(edl, os.path.join(d, "work", "edl.json"))
    picks_p = os.path.join(d, "work", "picks.json")   # re-running keeps takes that were already rendered
    if not os.path.exists(picks_p):
        dump({}, picks_p)
    print("%-14s %5.2f-%5.2f s (%.1f s)  %s" % (sid, t0, t1, t1 - t0, " ".join(ids)))


if __name__ == "__main__":
    for sid in (sys.argv[1:] or SHORTS):
        build(sid, SHORTS[sid])
