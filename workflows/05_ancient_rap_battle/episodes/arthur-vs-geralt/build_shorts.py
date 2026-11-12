# -*- coding: utf-8 -*-
"""Build vertical (9:16) YouTube Shorts as mini-episodes under shorts/<sid>/.

usage: python3 build_shorts.py [sid ...]        (default: every short in SHORTS)

  python3 ../../run_rap_battle_remote.py shorts/s1_roach shorts/s2_tahiti shorts/s3_finale --steps 12 \
    --runner-args "--fit --lock-strength 1.0 --mic handheld --realism-v2" --no-post
  python3 ../../scripts/assemble.py shorts/<sid> --size 768x1344 --film --out preview/草稿_胶片母带.mp4
  python3 ../../scripts/package.py shorts/<sid> --src preview/草稿_胶片母带.mp4 --film --1080p
"""
import json
import os
import shutil
import subprocess
import sys
import wave
import numpy as np
from PIL import Image

EP = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(EP, "work")
PRE, HEAD, TAIL = 0.08, 0.35, 1.8

SHORTS = {
    "s1_roach": ["A05", "A06", "A07", "A08"],
    "s2_tahiti": ["B01", "B02", "B03", "B04"],
    "s3_finale": ["B13", "B14", "B15", "B16"],
}
HOOK_SUB = {
    "s1_roach": "AI RAP BATTLE  ·  ROACH ON THE ROOF",
    "s2_tahiti": "AI RAP BATTLE  ·  NEXT STOP TAHITI",
    "s3_finale": "AI RAP BATTLE  ·  LOCKED AT 30 FPS",
}
CREEP_LINE = {"s1_roach": "A08", "s2_tahiti": "B04", "s3_finale": "B16"}

ONSTAGE_BY_WHO = {
    "a": (
        ". Tight portrait framing from the very first frame (0.0s) to the final frame with zero wide shot or bare floor: "
        "warm 2700K saloon oil-lantern bokeh orbs and softly blurred crowd silhouettes glow out of focus behind his shoulders "
        "at Cooke Panchro T2.2 shallow depth of field, with no other performer in the background"
    ),
    "b": (
        ". Tight portrait framing from the very first frame (0.0s) to the final frame with zero wide shot or bare floor: "
        "warm 2700K medieval torch bokeh orbs and softly blurred crowd silhouettes glow out of focus behind his shoulders "
        "at Cooke Panchro T2.2 shallow depth of field, with no other performer in the background"
    ),
}


def v_cam(who, creep=False):
    onstage = ONSTAGE_BY_WHO[who]
    if creep:
        return (
            "A handheld 35mm cinema camera at eye level with a subtle natural sway holds a tight vertical head-and-shoulders "
            "close-up shot of him at T2.2 shallow depth of field and gently pushes even closer on the final bar, his face and "
            "lips large in the upper half of the tall 9:16 frame from frame zero" + onstage
        )
    return (
        "A handheld 35mm cinema camera at eye level with a subtle natural sway holds a tight vertical chest-up close-up shot "
        "of him at T2.2 shallow depth of field, slowly arcing a few degrees around him, his face and lips large in the upper "
        "half of the tall 9:16 frame from frame zero" + onstage
    )


def make_vertical_eyelevel_plate(src_png, dst_png):
    """Crop out the top ceiling/balcony and bottom bare stage floor from the 1024x1024 stage plate
    into a native 768x1344 (9:16) eye-level bokeh plate so H3 never starts wide on the stage floor."""
    im = Image.open(src_png).convert("RGB")
    w, h = im.size
    # Keep y in [0.16, 0.74] (pure eye-level bokeh lights + blurred crowd silhouettes, no bare floor or high balcony)
    y0, y1 = int(round(h * 0.16)), int(round(h * 0.74))
    bh = y1 - y0
    bw = min(w, int(round(bh * 768.0 / 1344.0)))
    x0 = (w - bw) // 2
    crop = im.crop((x0, y0, x0 + bw, y1)).resize((768, 1344), Image.LANCZOS)
    crop.save(dst_png)


def j(p):
    return json.load(open(p, encoding="utf-8"))


def dump(obj, p):
    json.dump(obj, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def read_wav(p):
    with wave.open(p, "rb") as w:
        sr = w.getframerate()
        ch = w.getnchannels()
        arr = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).reshape(-1, ch).astype(np.float32) / 32768.0
    return sr, arr


def write_wav(p, sr, arr):
    pcm = np.clip(np.round(arr * 32767.0), -32768, 32767).astype(np.int16)
    with wave.open(p, "wb") as w:
        w.setnchannels(arr.shape[1])
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def cut_audio_tracks(dst_work, t0, t1, sung_end, nxt, bpm=95.0, verse_a=10.11):
    """Slice music_final.wav and vocals_final.wav cleanly; if a Short ends mid-verse (nxt < t1),
    crossfade music_final right after sung_end into an integer-bar-shifted pure instrumental bar
    from the mastered intro (zero Demucs vocal bleed!) so the next bar's vocals never play over the end card."""
    sr, m = read_wav(os.path.join(WORK, "music_final.wav"))
    _, voc = read_wav(os.path.join(WORK, "vocals_final.wav"))
    i0, i1 = int(round(t0 * sr)), int(round(t1 * sr))
    m_seg = m[i0:i1].copy()
    v_seg = voc[i0:i1].copy()

    if nxt < t1:
        bar_sec = 4.0 * 60.0 / bpm
        xf_start = max(0, int(round((sung_end - t0 + 0.008) * sr)))
        xf_end = min(len(m_seg), max(xf_start + 1, int(round((nxt - t0 - 0.006) * sr))))
        tail_len = len(m_seg) - xf_start
        # Pick integer number of bars earlier so (t0 + xf_start/sr - k*bar_sec) lands in pure instrumental intro [4.5s, verse_a - 2.2s]
        abs_xf = t0 + xf_start / sr
        k_bars = int(round((abs_xf - 5.25) / bar_sec))
        intro_start = int(round((abs_xf - k_bars * bar_sec) * sr))
        if 0 <= intro_start and intro_start + tail_len <= int((verse_a - 0.15) * sr):
            inst_tail = m[intro_start:intro_start + tail_len].copy()
        else:
            _, inst = read_wav(os.path.join(WORK, "svc_stems", "demucs_no_vocals.wav"))
            r0, r1 = int(5.0 * sr), int(9.0 * sr)
            gain = float(np.sqrt(np.mean(m[r0:r1] ** 2)) / max(1e-6, np.sqrt(np.mean(inst[r0:r1] ** 2))))
            inst_tail = inst[i0 + xf_start:i1] * gain

        n_xf = xf_end - xf_start
        alpha = 0.5 * (1.0 - np.cos(np.linspace(0.0, np.pi, n_xf, dtype=np.float32)))[:, None]
        m_seg[xf_start:xf_end] = m_seg[xf_start:xf_end] * (1.0 - alpha) + inst_tail[:n_xf] * alpha
        m_seg[xf_end:] = inst_tail[n_xf:]
        v_seg[xf_start:xf_end] *= 1.0 - alpha
        v_seg[xf_end:] = 0.0

    # Gentle 0.25s tail fade-out on music so loop transitions never click
    fade_n = min(len(m_seg), int(0.25 * sr))
    if fade_n > 0:
        m_seg[-fade_n:] *= np.linspace(1.0, 0.15, fade_n, dtype=np.float32)[:, None]

    write_wav(os.path.join(dst_work, "music_final.wav"), sr, m_seg)
    write_wav(os.path.join(dst_work, "vocals_final.wav"), sr, v_seg)


def is_sung(w):
    return not w["w"].startswith("[") and not w["w"].strip("!?,.").isupper()


def build(sid, ids):
    e = j(os.path.join(EP, "episode.json"))
    L = j(os.path.join(WORK, "lines.json"))
    words = j(os.path.join(WORK, "words_edit.json"))
    grid = j(os.path.join(WORK, "grid.json"))
    fx = j(os.path.join(WORK, "fx.json"))
    act = j(os.path.join(EP, "line_actions.json"))
    lid = lambda l: ("A" if l["who"] == "a" else "B") + "%02d" % l["n"]  # noqa: E731
    lines = [l for l in L if lid(l) in ids]
    assert [lid(l) for l in lines] == ids, "short lines must be consecutive in the song: %s" % ids
    assert len({l["who"] for l in lines}) == 1, "one rapper per short"
    nxt = L[L.index(lines[-1]) + 1]["start"] if L.index(lines[-1]) + 1 < len(L) else grid["length"]
    sung = [w for w in words if lines[0]["start"] - 0.1 <= w["t0"] < nxt - 0.05 and is_sung(w)]
    sung_end = max(w["t1"] for w in sung)
    t0 = round(lines[0]["start"] - HEAD, 3)
    t1 = round(min(sung_end + TAIL, grid["length"]), 3)
    sh = lambda t: round(t - t0, 3)  # noqa: E731

    d = os.path.join(EP, "shorts", sid)
    for sub in ("work", "refs", "clips"):
        os.makedirs(os.path.join(d, sub), exist_ok=True)
    for f in ("a_face_clean.png", "b_face_clean.png"):
        shutil.copy2(os.path.join(WORK, f), os.path.join(d, "work", f))
    for f in ("stage_a.png", "stage_b.png"):
        make_vertical_eyelevel_plate(os.path.join(WORK, f), os.path.join(d, "work", f))
    cut_audio_tracks(os.path.join(d, "work"), t0, t1, sung_end, nxt, bpm=grid["bpm"], verse_a=grid.get("verse_a", 10.11))

    se = dict(
        e,
        title="%s_Short_%s" % (e["title"], sid),
        venue_en=e["venue_en"].replace("the two rappers always stand on top of this stage", "the solo rapper stands front and center"),
        title_card=False,
        name_cards=False,
        end_card_secs=1.2,
        end_question="FULL BATTLE|ON THE CHANNEL",
        show_notes=False,
        hook={"a": e["a"]["name_cn"], "b": e["b"]["name_cn"], "sub": HOOK_SUB[sid], "secs": 2.6},
    )
    se.pop("structure", None)
    dump(se, os.path.join(d, "episode.json"))
    dump([dict(l, start=sh(l["start"]), end=sh(l["end"])) for l in lines], os.path.join(d, "work", "lines.json"))
    dump([dict(w, t0=sh(w["t0"]), t1=sh(w["t1"])) for w in words if t0 <= w["t0"] < min(t1, nxt)], os.path.join(d, "work", "words_edit.json"))
    beat = 60.0 / grid["bpm"]
    dump(
        dict(grid, beat0=round((grid["beat0"] - t0) % beat, 4), length=round(t1 - t0, 3), keep=[[0.0, round(t1 - t0, 3)]]),
        os.path.join(d, "work", "grid.json"),
    )
    dump(
        [dict(x, t0=sh(x["t0"]), t1=sh(min(x["t1"], t1))) for x in fx if t0 <= x["t0"] < sung_end and x["type"] in ("dark",)],
        os.path.join(d, "work", "fx.json"),
    )
    shutil.copy2(os.path.join(WORK, "live.json"), os.path.join(d, "work", "live.json"))

    clips, edl, last_end = [], [], {}
    for i, l in enumerate(lines):
        who, cid = l["who"], lid(l)
        face, plate = ("a_face_clean", "stage_a") if who == "a" else ("b_face_clean", "stage_b")
        nstart = lines[i + 1]["start"] if i + 1 < len(lines) else nxt
        lw = max(w["t1"] for w in sung if l["start"] - 0.1 <= w["t0"] < nstart - 0.05)
        creep = cid == CREEP_LINE[sid]
        clips.append({
            "id": cid,
            "kind": "rap",
            "who": who,
            "line": l["n"],
            "move": "FULL",
            "text": l["text"],
            "audio": [sh(l["start"] - PRE), sh(max(l["end"], lw))],
            "lead": 0.0,
            "aspect": "9:16",
            "action": act[who][l["n"] - 1],
            "two_shot": False,
            "cam": v_cam(who, creep=creep),
            "static": False,
            "bg": plate,
            "image_keys": [face, plate],
            "sway": 0.5,
            "drift": 0.0 if creep else 0.02,
        })
        last_end[cid] = sh(lw)

    cut_skip = {"A08": 0.305, "B02": 0.090, "B14": 0.050, "B15": 0.090}
    for i, c in enumerate(clips):
        s0 = 0.0 if i == 0 else edl[-1]["t1"]
        if i + 1 < len(clips):
            nxt_in = clips[i + 1]["audio"][0] + cut_skip.get(clips[i + 1]["id"], 0.0)
            s1 = round(max(nxt_in, last_end[c["id"]] + 0.02), 3)
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
