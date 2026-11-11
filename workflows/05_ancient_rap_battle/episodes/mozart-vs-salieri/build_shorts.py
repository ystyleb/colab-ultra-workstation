# -*- coding: utf-8 -*-
"""Build vertical (9:16) YouTube Shorts as mini-episodes under shorts/<sid>/.

usage: python3 build_shorts.py [sid ...]        (default: every short in SHORTS)

  python3 ../../run_rap_battle_remote.py shorts/s1_vatican shorts/s2_amadeus shorts/s3_finale --steps 12 \
    --runner-args "--fit --lock-strength 1.0 --mic handheld --realism-v2" --no-post
  python3 ../../scripts/assemble.py shorts/<sid> --size 768x1344 --film --out preview/草稿_胶片母带.mp4
  python3 ../../scripts/package.py shorts/<sid> --src preview/草稿_胶片母带.mp4 --film --1080p
"""
import json
import os
import shutil
import subprocess
import sys

EP = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(EP, "work")
PRE, HEAD, TAIL = 0.08, 0.35, 1.8

SHORTS = {
    "s1_vatican": ["A01", "A02", "A03", "A04"],
    "s2_amadeus": ["A13", "A14", "A15", "A16"],
    "s3_finale": ["B13", "B14", "B15", "B16"],
}
HOOK_SUB = {
    "s1_vatican": "AI RAP BATTLE  ·  MOZART'S OPENING VERSE",
    "s2_amadeus": "AI RAP BATTLE  ·  THE POISON MYTH ROAST",
    "s3_finale": "AI RAP BATTLE  ·  SALIERI'S REAL RECEIPTS",
}
CREEP_LINE = {"s1_vatican": "A04", "s2_amadeus": "A16", "s3_finale": "B16"}
ONSTAGE = (". He stands alone on top of the raised stage: the cheering crowd silhouettes are on the opera pit floor below and behind him, lower "
           "than his chest, softly out of focus at Cooke Panchro T2.2, and there is no other stage or performer in the background")
V_HAND = ("A handheld 35mm cinema camera at eye level with a subtle natural sway holds a vertical chest-up close-up shot of him at T2.2 shallow depth of field, slowly "
          "arcing a few degrees around him, his face and lips large in the upper half of the tall 9:16 frame" + ONSTAGE)
V_CREEP = ("A handheld 35mm cinema camera with a subtle natural sway starts on a vertical chest-up shot at eye level and gently "
           "creeps closer to a head-and-shoulders close-up at T2.2 shallow depth of field, his face and lips large in the upper half of the tall 9:16 "
           "frame from the first frame" + ONSTAGE)


def j(p):
    return json.load(open(p, encoding="utf-8"))


def dump(obj, p):
    json.dump(obj, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def cut(src, dst, t0, t1):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", "%.3f" % t0, "-t", "%.3f" % (t1 - t0), "-i", src,
                    "-c:a", "pcm_s16le", dst], check=True)


def is_sung(w):
    return not w["w"].startswith("[") and not w["w"].strip("!?,.").isupper()


def build(sid, ids):
    e = j(os.path.join(EP, "episode.json"))
    L = j(os.path.join(WORK, "lines.json"))
    words = j(os.path.join(WORK, "words_edit.json"))
    grid = j(os.path.join(WORK, "grid.json"))
    fx = j(os.path.join(WORK, "fx.json"))
    act = j(os.path.join(EP, "line_actions.json"))
    lid = lambda l: ("A" if l["who"] == "a" else "B") + "%02d" % l["n"]   # noqa: E731
    lines = [l for l in L if lid(l) in ids]
    assert [lid(l) for l in lines] == ids, "short lines must be consecutive in the song: %s" % ids
    assert len({l["who"] for l in lines}) == 1, "one rapper per short"
    nxt = L[L.index(lines[-1]) + 1]["start"] if L.index(lines[-1]) + 1 < len(L) else grid["length"]
    sung = [w for w in words if lines[0]["start"] - 0.1 <= w["t0"] < nxt - 0.05 and is_sung(w)]
    t0 = round(lines[0]["start"] - HEAD, 3)
    t1 = round(min(max(w["t1"] for w in sung) + TAIL, grid["length"]), 3)
    sh = lambda t: round(t - t0, 3)   # noqa: E731

    d = os.path.join(EP, "shorts", sid)
    for sub in ("work", "refs", "clips"):
        os.makedirs(os.path.join(d, sub), exist_ok=True)
    for f in ("a_face_clean.png", "b_face_clean.png", "stage_a.png", "stage_b.png"):
        shutil.copy2(os.path.join(WORK, f), os.path.join(d, "work", f))
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
    sung_end = max(w["t1"] for w in sung)
    dump([dict(x, t0=sh(x["t0"]), t1=sh(min(x["t1"], t1))) for x in fx if t0 <= x["t0"] < sung_end
          and x["type"] in ("dark",)], os.path.join(d, "work", "fx.json"))
    shutil.copy2(os.path.join(WORK, "live.json"), os.path.join(d, "work", "live.json"))

    clips, edl, last_end = [], [], {}
    for i, l in enumerate(lines):
        who, cid = l["who"], lid(l)
        face, plate = ("a_face_clean", "stage_a") if who == "a" else ("b_face_clean", "stage_b")
        nstart = lines[i + 1]["start"] if i + 1 < len(lines) else nxt
        lw = max(w["t1"] for w in sung if l["start"] - 0.1 <= w["t0"] < nstart - 0.05)
        creep = cid == CREEP_LINE[sid]
        clips.append({"id": cid, "kind": "rap", "who": who, "line": l["n"], "move": "FULL", "text": l["text"],
                      "audio": [sh(l["start"] - PRE), sh(max(l["end"], lw))], "lead": 0.0, "aspect": "9:16",
                      "action": act[who][l["n"] - 1],
                      "two_shot": False, "cam": V_CREEP if creep else V_HAND, "static": False, "bg": plate,
                      "image_keys": [face, plate], "sway": 0.5, "drift": 0.0 if creep else 0.02})
        last_end[cid] = sh(lw)
    for i, c in enumerate(clips):
        s0 = 0.0 if i == 0 else edl[-1]["t1"]
        if i + 1 < len(clips):
            nxt_min = clips[i + 1]["audio"][0] + (0.173 if clips[i + 1]["id"] == "B16" else 0.0)
            s1 = round(max(nxt_min, last_end[c["id"]] + 0.02), 3)
        else:
            s1 = round(t1 - t0, 3)
        edl.append({"t0": s0, "t1": s1, "clip": c["id"], "in": None})
        assert s1 >= last_end[c["id"]] - 0.05, (c["id"], s1, last_end[c["id"]])
        assert c["audio"][1] - c["audio"][0] + 0.35 <= 158 / 24, c["id"]
    dump(clips, os.path.join(d, "work", "clips.json"))
    dump(edl, os.path.join(d, "work", "edl.json"))
    picks_p = os.path.join(d, "work", "picks.json")
    if not os.path.exists(picks_p):
        dump({}, picks_p)
    print("%-14s %6.2f-%6.2f s (%.1f s)  %s" % (sid, t0, t1, t1 - t0, " ".join(ids)))


if __name__ == "__main__":
    for sid in (sys.argv[1:] or SHORTS):
        build(sid, SHORTS[sid])
