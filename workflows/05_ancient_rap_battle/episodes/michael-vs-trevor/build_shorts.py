#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build 3 vertical (9:16) YouTube Shorts as mini-episodes under shorts/<sid>/ for Michael vs Trevor.

Usage:
  python3 build_shorts.py [sid ...]        (default: every short in SHORTS)

Render on Colab G4 (no-mic 35mm cinema mode):
  python3 ../../run_rap_battle_remote.py shorts/s1_mansion shorts/s2_witness shorts/s3_judas --steps 12 \
    --runner-args "--fit --lock-strength 1.0 --mic none --realism-v2" --no-post
  python3 ../../scripts/assemble.py shorts/<sid> --size 768x1344 --film --out preview/草稿_胶片母带.mp4
  python3 ../../scripts/package.py shorts/<sid> --src preview/草稿_胶片母带.mp4 --film --1080p
"""
import json
import os
import shutil
import sys
import wave
import numpy as np
from PIL import Image

EP = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(EP, "work")
PRE, HEAD, TAIL = 0.08, 0.35, 1.8

SHORTS = {
    "s1_mansion": ["A01", "A02", "A03", "A04"],
    "s2_witness": ["B01", "B02", "B03", "B04"],
    "s3_judas": ["B13", "B14", "B15", "B16"],
}
HOOK_SUB = {
    "s1_mansion": "AI RAP BATTLE  ·  ROCKFORD HILLS THRONE",
    "s2_witness": "AI RAP BATTLE  ·  WITNESS PROTECTION?!",
    "s3_judas": "AI RAP BATTLE  ·  DIE ALONE, JUDAS",
}
CREEP_LINE = {
    "s1_mansion": "A04",
    "s2_witness": "B04",
    "s3_judas": "B16",
}

SHORT_SCENE_CFG = {
    "s1_mansion": {
        "who": "a",
        "face_src": "a_face_clean.png",
        "face_key": "a_face_clean",
        "plate_src": "stage_mansion.png",
        "plate_key": "stage_mansion_v",
        "venue_en": "a luxury Rockford Hills mansion pool terrace at night overlooking the glittering Los Santos city skyline",
        "light_en": "warm 3200K architectural tungsten terrace key light sculpting natural human skin tones with 5600K cool silver moonlight hair rim light and deep rich night shadows",
        "bg_desc_en": "the luxury Rockford Hills mansion pool terrace and glittering Los Santos night skyline",
        "bg_lights_en": "glittering golden-amber and cool sapphire Los Santos city skyline bokeh orbs",
        "bg_motion_en": "shimmering pool water reflections and distant freeway city lights glimmering softly out of focus",
        "look_me": "late-40s retired Los Santos bank-heist kingpin with neatly combed dark-brown hair graying at the temples, subtle crow's feet, wearing a tailored charcoal-grey luxury suit over an unbuttoned slate-blue dress shirt",
    },
    "s2_witness": {
        "who": "b",
        "face_src": "b_face_clean.png",
        "face_key": "b_face_clean",
        "plate_src": "stage_desert.png",
        "plate_key": "stage_desert_v",
        "venue_en": "a gritty sun-scorched Sandy Shores desert trailer park and dusty dirt airfield at fiery golden-amber dusk",
        "light_en": "fiery 3000K golden-hour sunset side-key light and warm 2700K porch-bulb glow sculpting gritty natural skin texture, sweat sheen, and stubble",
        "bg_desc_en": "the battered Sandy Shores mobile home, neon beer sign, and dusty desert airfield at sunset",
        "bg_lights_en": "warm 2700K trailer porch-bulb and fiery golden-amber desert sunset bokeh orbs",
        "bg_motion_en": "golden desert dust and dry heat-haze drifting across the airfield",
        "look_me": "late-40s unhinged Sandy Shores outlaw with receding thinning dark unkempt hair, wild intense hazel-brown eyes, coarse five-o'clock stubble, faint dotted neck tattoo, wearing a sweat-stained dirty off-white crew-neck pocket t-shirt",
    },
    "s3_judas": {
        "who": "b",
        "face_src": "b_face_winter.png",
        "face_key": "b_face_winter",
        "plate_src": "stage_yankton_b.png",
        "plate_key": "stage_yankton_v",
        "venue_en": "the snow-covered Ludendorff cemetery in North Yankton at night during a heavy snowfall beside an open grave",
        "light_en": "strong warm 3200K amber halogen pickup-truck headlights from the side sculpting healthy warm human skin tones (zero cyan cast on faces), paired with crisp 6500K icy silver rim light on falling snowflakes and steaming breath",
        "bg_desc_en": "the snow-blanketed Ludendorff graveyard at night with warm amber pickup-truck headlight beams and falling snow",
        "bg_lights_en": "warm 3200K amber pickup-truck headlight bokeh and distant church lantern glow through falling snow",
        "bg_motion_en": "wind-driven white snowflakes and steaming cold breath drifting continuously through the headlight beams",
        "look_me": "late-40s unhinged outlaw with receding unkempt hair dusted with snowflakes, wild intense eyes, coarse stubble, wearing a heavy worn brown leather winter parka with a thick beige sheepskin shearling collar",
    },
}


def v_cam(cfg: dict, creep: bool = False) -> str:
    tail = (
        f". Tight vertical 9:16 portrait framing from frame zero (0.0s) to the final frame with zero wide shot: "
        f"{cfg['bg_lights_en']} glow softly out of focus behind his shoulders at Cooke Panchro T2.2 shallow depth of field, "
        f"with no microphone and no other person in the frame"
    )
    if creep:
        return (
            "A handheld 35mm cinema camera at eye level with a subtle natural sway holds a tight vertical head-and-shoulders "
            "close-up shot of <Subject 1> at T2.2 shallow depth of field and pushes fiercely closer on the final punchline, "
            "his face and lips large and centered in the upper half of the tall 9:16 frame" + tail
        )
    return (
        "A handheld 35mm cinema camera at eye level with a subtle natural sway holds a tight vertical chest-up close-up shot "
        "of <Subject 1> at T2.2 shallow depth of field, slowly arcing a few degrees around him, his face and lips large in "
        "the upper half of the tall 9:16 frame" + tail
    )


def make_vertical_eyelevel_plate(src_png: str, dst_png: str) -> None:
    """Crop eye-level band from 768x768 bokeh stage plate into native 768x1344 (9:16) portrait bokeh plate."""
    im = Image.open(src_png).convert("RGB")
    w, h = im.size
    y0, y1 = int(round(h * 0.10)), int(round(h * 0.86))
    bh = y1 - y0
    bw = min(w, int(round(bh * 768.0 / 1344.0)))
    x0 = (w - bw) // 2
    crop = im.crop((x0, y0, x0 + bw, y1)).resize((768, 1344), Image.Resampling.LANCZOS)
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


def cut_audio_tracks(dst_work: str, t0: float, t1: float, sung_end: float, nxt: float) -> None:
    """Slice music_final.wav and vocals_final.wav; crossfade tail after sung_end into exact Beat-Switch-matched
    instrumental stem (`inst_cut.wav`) so the next lyric line never bleeds over the 1.2s end card."""
    sr, m = read_wav(os.path.join(WORK, "music_final.wav"))
    _, voc = read_wav(os.path.join(WORK, "vocals_final.wav"))
    i0, i1 = int(round(t0 * sr)), int(round(t1 * sr))
    m_seg = m[i0:i1].copy()
    v_seg = voc[i0:i1].copy()

    if nxt < t1:
        xf_start = max(0, int(round((sung_end - t0 + 0.010) * sr)))
        xf_end = min(len(m_seg), max(xf_start + 1, int(round((nxt - t0 - 0.008) * sr))))
        inst_path = os.path.join(WORK, "svc_stems", "demucs_no_vocals.wav")
        if not os.path.exists(inst_path):
            inst_path = os.path.join(WORK, "inst_cut.wav")
        _, inst = read_wav(inst_path)
        # Match RMS level on pure instrumental intro window [2.0s, 8.5s]
        r0, r1 = int(2.0 * sr), int(8.5 * sr)
        gain = float(np.sqrt(np.mean(m[r0:r1] ** 2)) / max(1e-6, np.sqrt(np.mean(inst[r0:r1] ** 2))))
        inst_tail = inst[i0 + xf_start : i1] * min(1.15, gain)

        n_xf = xf_end - xf_start
        alpha = 0.5 * (1.0 - np.cos(np.linspace(0.0, np.pi, n_xf, dtype=np.float32)))[:, None]
        m_seg[xf_start:xf_end] = m_seg[xf_start:xf_end] * (1.0 - alpha) + inst_tail[:n_xf] * alpha
        m_seg[xf_end:] = inst_tail[n_xf:]
        v_seg[xf_start:xf_end] *= 1.0 - alpha
        v_seg[xf_end:] = 0.0

    fade_n = min(len(m_seg), int(0.25 * sr))
    if fade_n > 0:
        m_seg[-fade_n:] *= np.linspace(1.0, 0.15, fade_n, dtype=np.float32)[:, None]

    write_wav(os.path.join(dst_work, "music_final.wav"), sr, m_seg)
    write_wav(os.path.join(dst_work, "vocals_final.wav"), sr, v_seg)


def is_sung(w):
    return not w["w"].startswith("[") and not w["w"].strip("!?,.").isupper()


def build(sid: str, ids: list[str]) -> None:
    cfg = SHORT_SCENE_CFG[sid]
    e = j(os.path.join(EP, "episode.json"))
    L = j(os.path.join(WORK, "lines.json"))
    words = j(os.path.join(WORK, "words_edit.json"))
    grid = j(os.path.join(WORK, "grid.json"))
    fx = j(os.path.join(WORK, "fx.json"))
    act = j(os.path.join(EP, "line_actions.json"))
    lid = lambda l: ("A" if l["who"] == "a" else "B") + "%02d" % l["n"]  # noqa: E731
    lines = [l for l in L if lid(l) in ids]
    assert [lid(l) for l in lines] == ids, f"short lines must be consecutive: {ids}"
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
    shutil.copy2(os.path.join(WORK, cfg["face_src"]), os.path.join(d, "work", f"{cfg['face_key']}.png"))
    make_vertical_eyelevel_plate(
        os.path.join(WORK, cfg["plate_src"]),
        os.path.join(d, "work", f"{cfg['plate_key']}.png"),
    )
    cut_audio_tracks(os.path.join(d, "work"), t0, t1, sung_end, nxt)

    se = dict(
        e,
        title="%s_Short_%s" % (e["title"], sid),
        venue_en=cfg["venue_en"],
        light_en=cfg["light_en"],
        mic_en="none",
        crowd_motion_en="",
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
    dump(
        [dict(w, t0=sh(w["t0"]), t1=sh(w["t1"])) for w in words if t0 <= w["t0"] < min(t1, nxt)],
        os.path.join(d, "work", "words_edit.json"),
    )
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
        nstart = lines[i + 1]["start"] if i + 1 < len(lines) else nxt
        lw = max(w["t1"] for w in sung if l["start"] - 0.1 <= w["t0"] < nstart - 0.05)
        creep = cid == CREEP_LINE[sid]
        clips.append(
            {
                "id": cid,
                "kind": "rap",
                "who": who,
                "line": l["n"],
                "move": "FULL",
                "text": l["text"],
                "audio": [sh(l["start"] - PRE), sh(max(l["end"], lw))],
                "lead": 0.0,
                "aspect": "9:16",
                "mic": "none",
                "look_me": cfg["look_me"],
                "venue_en": cfg["venue_en"],
                "light_en": cfg["light_en"],
                "crowd_motion_en": "",
                "bg_exterior": True,
                "bg_desc_en": cfg["bg_desc_en"],
                "bg_lights_en": cfg["bg_lights_en"],
                "bg_motion_en": cfg["bg_motion_en"],
                "action": act[who][str(l["n"])] if isinstance(act[who], dict) else act[who][l["n"] - 1],
                "two_shot": False,
                "cam": v_cam(cfg, creep=creep),
                "static": False,
                "bg": cfg["plate_key"],
                "image_keys": [cfg["face_key"], cfg["plate_key"]],
                "sway": 0.5,
                "drift": 0.0 if creep else 0.02,
            }
        )
        last_end[cid] = sh(lw)

    for i, c in enumerate(clips):
        s0 = 0.0 if i == 0 else edl[-1]["t1"]
        if i + 1 < len(clips):
            nxt_in = clips[i + 1]["audio"][0]
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
    want = sys.argv[1:] or list(SHORTS)
    for sid in want:
        build(sid, SHORTS[sid])
