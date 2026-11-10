# -*- coding: utf-8 -*-
"""Build work/clips.json + work/edl.json + work/fx.json for the full 2-round song (32 lines, ~96 s).

usage: python3 build_storyboard_full.py [--link-v2-clips]

- One lip-sync clip per line (A01-A16, B01-B16), cut just before the next line's first word; a guard asserts no
  clip is cut before its last word ends (user rule 2026-11-08: never cut away while a line is being sung).
- Camera rotates per 8-line round: CU, 3/4 left, low angle, OTS two-shot, CU, 3/4 right, low angle, CU.
- Reactions only in the gaps Suno actually left (OOOH after round 1, ROUND TWO break, outro). Most non-lip
  shots reuse the v2 renders (--link-v2-clips copies them into clips/ and marks them in picks.json).
Render with: --fit --lock-strength 1.0 --mic stand --static-cam
"""
import json
import os
import shutil
import sys

EP = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(EP, "work")
V2 = os.path.join(EP, "..", "edison-vs-tesla-v2")
e = json.load(open(os.path.join(EP, "episode.json"), encoding="utf-8"))
L = json.load(open(os.path.join(WORK, "lines.json"), encoding="utf-8"))
WORDS = json.load(open(os.path.join(WORK, "words_edit.json"), encoding="utf-8"))
ACT = json.load(open(os.path.join(EP, "line_actions.json"), encoding="utf-8"))
grid = json.load(open(os.path.join(WORK, "grid.json"), encoding="utf-8"))
v2 = {c["id"]: c for c in json.load(open(os.path.join(V2, "work", "clips.json"), encoding="utf-8"))}
A, B = e["a"], e["b"]
END_T = round(grid["length"], 3)
PRE = 0.08  # cut just before the first word (same rule as make_clips.py)

CU = ("The camera holds a tight head-and-shoulders close-up at eye level, frontal, his face filling the upper half of "
      "the 16:9 frame")
TQ = "The camera holds a chest-up medium close-up from a three-quarter angle at eye level"
LOW = ("The camera holds a low-angle chest-up medium close-up looking slightly up at him, the overhead spotlight lamp "
       "glowing at the top of the frame")
OTS = ("The camera holds an over-the-shoulder two-shot from behind <Subject 2>'s shoulder: <Subject 2> is a dark, "
       "out-of-focus shoulder and back of the head in the left foreground, <Subject 1> is chest-up and in sharp focus "
       "on screen-right facing the lens")
ROT = [(CU, False), (TQ + " from his left side", False), (LOW, False), (OTS, True),
       (CU, False), (TQ + " from his right side", False), (LOW, False), (CU, False)]
LISTENER = " while <Subject 2> stays a silent, blurred foreground shoulder with his back to the camera"
# 2026-11-09 "live" pass (user: shots felt like isolated animated stills). Every lip shot gets its singer's stage plate
# (crops of refs/venue.png) and a handheld operator; punchlines get a real push-in instead of the edit-time punch zoom.
# Both camera phrasings were sampled on A05/B05 first (preview/bc_sample/) - keep the "starts on ... creeps closer"
# wording: a bare "push-in" made H3 open on a wide shot.
HAND = (", shot on a handheld camera at shoulder height with a subtle natural sway, slowly arcing a few degrees around "
        "him, his face and lips large and clearly readable in every frame")
CREEP = ("A handheld camera with a subtle natural sway starts on a chest-up medium close-up at eye level and gently creeps "
         "closer to a head-and-shoulders close-up over the shot, his face and lips large and clearly readable from the first frame")
PLATE = {"a": "stage_a", "b": "stage_b"}
# 2026-11-09 wide pass (user: almost everything is close/medium, no sense of the whole room). The singer stays on screen
# for the whole line (never cut away mid-line); only the camera pulls back. Verse openers = front wide (who is on the
# stage), one mid-verse reverse wide from behind the singer toward the crowd and his opponent.
WIDE_FRONT = ("A handheld camera with a subtle natural sway holds a wide shot from the front edge of the crowd at chest "
              "height: <Subject 1> is seen full-body on the spotlit circular stage rapping into the floor-stand microphone, "
              "<Subject 2> stands across the stage on the far side, the raised fists and flat caps of the packed crowd "
              "silhouetted in the foreground, the whole arena visible around them: iron girders, strings of amber bulbs on "
              "the left balcony and arcing Tesla coils on the right")
WIDE_REV = ("A handheld camera with a subtle natural sway holds a wide reverse shot from just behind <Subject 1> on the "
            "stage: <Subject 1> is a three-quarter back view in the near foreground rapping out toward the arena, beyond "
            "him <Subject 2> stands full-body across the stage, and behind <Subject 2> the packed crowd fills the hall "
            "under the iron girders and the hazy spotlight beam")
# the reverse wide was sampled (clips/B03_s2.mp4) and came back as a medium profile two-shot; a high balcony wide reads as
# "the whole room" far more reliably, like the front wide that worked (clips/A01_s2.mp4)
WIDE_HIGH = ("A handheld camera with a subtle natural sway holds a high wide shot from the side balcony rail looking down "
             "at the spotlit circular stage: <Subject 1> is a full-body figure rapping into the floor-stand microphone, "
             "<Subject 2> stands across the stage, the packed crowd surrounds the stage on every side, and the whole arena "
             "is visible: iron girders, strings of amber bulbs, Tesla coils arcing, haze drifting through the spotlight beam")
# second wide pass: the balcony / front-edge wording still came back as knee-up two-shots on 6 of 8 lines; the crowd's
# heads in the lower third force distance, and those shots drop the close-up face LoRA ("closeup_lora": 0)
WIDE_FAR = ("A handheld camera with a subtle natural sway holds a wide shot from the back rows of the crowd: the heads, "
            "flat caps and raised fists of the packed crowd fill the lower third of the frame, and beyond them on the "
            "spotlit circular stage <Subject 1> raps full-body into the floor-stand microphone while <Subject 2> stands "
            "full-body across the stage; the whole arena rises above them: iron girders, strings of amber bulbs, Tesla "
            "coils arcing blue-violet, haze drifting through the spotlight beam")
WIDE_LISTENER = (" while <Subject 2> stands across the stage holding his {prop} at his side, arms still and mouth closed, "
                 "watching him")
# A01 / B03 keep their accepted takes (front wide, pull-back to wide); the rest use WIDE_FAR
WIDE = {"A01": WIDE_FRONT, "B03": WIDE_HIGH, "B01": WIDE_FAR, "A09": WIDE_FAR, "B09": WIDE_FAR,
        "A06": WIDE_FAR, "A14": WIDE_FAR, "B13": WIDE_FAR}
WIDE_NO_LORA = {"B01", "A09", "B09", "A06", "A14", "B13"}
PUSH = {"A02", "A07", "A12", "A16", "B06", "B08", "B09", "B12", "B16"}


def last_word_end(l, nxt_start):
    ws = [w for w in WORDS if l["start"] - 0.1 <= w["t0"] < nxt_start - 0.05 and not w["w"].strip("!").isupper()]
    return max(w["t1"] for w in ws)


clips, edl = [], []
lip = {}
pushed = set()  # lines that really got the CREEP camera (an OTS two-shot keeps its framing)
for i, l in enumerate(L):
    who, n = l["who"], l["n"]
    cid = ("A" if who == "a" else "B") + "%02d" % n
    nxt = L[i + 1]["start"] if i + 1 < len(L) else END_T
    lw_end = last_word_end(l, nxt)
    cam, two = ROT[(n - 1) % 8]
    me, them = ("a_face_clean", "b_face_clean") if who == "a" else ("b_face_clean", "a_face_clean")
    prop = A if who == "a" else B
    c = {"id": cid, "kind": "rap", "who": who, "line": n, "move": "FULL", "text": l["text"],
         "audio": [round(l["start"] - PRE, 3), round(max(l["end"], lw_end), 3)], "lead": 0.0,
         "action": ACT[who][n - 1] + f", the {prop['prop']} stays in his left hand, clearly separate from the microphone stand",
         "two_shot": two, "cam": CREEP if cid in PUSH and not two else cam + HAND, "static": False,
         "bg": PLATE[who], "image_keys": ([me, them] if two else [me]) + [PLATE[who]],
         "sway": 0.5, "drift": 0.0 if cid in PUSH and not two else 0.02}
    if cid in PUSH and not two:
        pushed.add(cid)
    if two:
        c["listener"] = LISTENER
    if cid in WIDE:  # both rappers + whole arena; venue.png as the environment ref instead of the half plate
        other = B if who == "a" else A
        if cid in ("A01", "B03"):  # exactly as rendered (accepted takes)
            c.update(two_shot=True, wide=True, cam=WIDE[cid], bg="venue", image_keys=[me, them, "venue"], sway=0.5,
                     drift=0.02, action=ACT[who][n - 1],
                     listener=" while <Subject 2> stands across the stage with his arms folded and his mouth closed, watching him")
        else:  # each man holds only his own prop (with both on screen H3 hands props to the wrong man otherwise)
            c.update(two_shot=True, wide=True, cam=WIDE[cid], bg="venue", image_keys=[me, them, "venue"], sway=0.5,
                     drift=0.02, action=ACT[who][n - 1] + f", holding his own {prop['prop']} in his left hand",
                     listener=WIDE_LISTENER.format(prop=other["prop"]))
        if cid in WIDE_NO_LORA:
            c["closeup_lora"] = 0.0
        pushed.discard(cid)
    clips.append(c)
    lip[cid] = (round(l["start"] - PRE, 3), lw_end, nxt)

# sections between rap runs (where the singer changes)
order = list(lip)
spans = []  # (t0, t1, clip, in)
spans.append((0.0, 1.26, "WIDE_OPEN", 1.1))  # H3 put a posed close-up in the first second; the crane-down starts ~1.0 s
spans.append((1.26, lip[order[0]][0], "FACEOFF", 0.8))
REACT = {  # gap index -> shots (clip, in, max usable seconds); last one absorbs the remainder
    0: [("CROWD_OOH", 0.2, 0.8), ("R_T1", 0.0, 0.8), ("B_STEP", 0.4, 1.4)],
    1: [("DJ", 0.0, 0.85), ("WIDE_BALCONY", 0.2, 1.4)],
}
gap_i = 0
for k, cid in enumerate(order):
    # continue right where the previous lip clip ended (it may run past our pre-roll to finish its last word)
    t0 = spans[-1][1] if spans[-1][3] is None else lip[cid][0]
    nxt_cid = order[k + 1] if k + 1 < len(order) else None
    if nxt_cid is None:
        t1 = max(lip[cid][1] + 0.02, t0)  # last line: until its last word ends, then the outro
    elif nxt_cid[0] != cid[0] and lip[nxt_cid][0] - lip[cid][1] > 0.5:
        t1 = round(lip[cid][1] + 0.02, 3)  # singer change with a real gap: cut right after the last word
    else:
        # same run (or no gap): cut before the next first word, but never before this line's last word ends
        t1 = round(max(lip[nxt_cid][0], lip[cid][1] + 0.02), 3)
    spans.append((t0, t1, cid, None))
    if nxt_cid and nxt_cid[0] != cid[0] and t1 < lip[nxt_cid][0] - 1e-6:
        g0, g1 = t1, lip[nxt_cid][0]
        shots = REACT[gap_i]
        gap_i += 1
        t = g0
        for j, (sid, inn, mx) in enumerate(shots):
            d = (g1 - t) if j == len(shots) - 1 else min(mx, (g1 - g0) / len(shots))
            assert d <= mx + 1e-6, f"gap {g0:.2f}-{g1:.2f}: {sid} would need {d:.2f}s > {mx}s usable"
            spans.append((round(t, 3), round(t + d, 3), sid, inn))
            t += d
# outro: new crowd chant shot, Edison stung, bulb dies, Tesla triumphant
o0 = spans[-1][1]
outro = [("WIDE_OUTRO", 0.8, 1.0),  # first ~0.7 s is a different wide; Tesla-from-behind starts ~0.7 s
          ("R_E1", 0.4, 0.63), ("BLACKOUT", 0.55, 0.6), ("END", 0.2, None)]
t = o0
for sid, inn, d in outro:
    d = (END_T - t) if d is None else d
    spans.append((round(t, 3), round(t + d, 3), sid, inn))
    t += d
edl = [{"t0": a, "t1": b, "clip": c, "in": i} for a, b, c, i in spans]

# non-lip clip definitions: reuse v2 renders, plus one new crowd chant shot
for sid in ("OPEN", "FACEOFF", "CROWD_OOH", "R_T1", "B_STEP", "DJ", "CROWD_ERUPT", "R_E1", "BLACKOUT", "END"):
    clips.append(dict(v2[sid]))
ce = dict(v2["CROWD_ERUPT"])
ce["id"] = "CROWD_TESLA"
ce["prompt"] = ce["prompt"].replace(
    ce["prompt"].split("\n\n")[1],
    "Cinematic photoreal shot, 16:9. Close medium shot packed with workers from the front row (Image 1), faces large in "
    "frame, handheld camera at their eye level: they chant together with fists pumping in rhythm, mouths wide open, "
    "blue-violet light from the Tesla coils flickering over their sweaty faces.")
clips.append(ce)
# gap wides: whole-room establishing shots (same image refs as OPEN: venue, crowd, Edison, Tesla)
GAP_WIDE = {
    "WIDE_OPEN": "Extreme wide establishing shot from high up among the iron roof girders: the camera cranes slowly down "
                 "through the haze, revealing the whole packed hall below, the cold white spotlight on the circular stage "
                 "where Thomas Edison (Image 3) on the left and Nikola Tesla (Image 4) on the right face off as small "
                 "full-body figures, strings of amber bulbs along the left balcony, Tesla coils arcing blue-violet on the "
                 "right, hundreds of raised fists around the stage.",
    "WIDE_BALCONY": "High wide shot from the upper balcony rail looking down over the whole arena, handheld: the entire "
                    "crowd jumps and punches the air chanting, the empty spotlit circular stage in the middle with Thomas "
                    "Edison (Image 3) and Nikola Tesla (Image 4) at its opposite edges, the DJ booth glowing on its brass "
                    "dynamos behind, haze drifting through the spotlight beam.",
    "WIDE_OUTRO": "Wide shot from behind Nikola Tesla (Image 4) on the stage, handheld at shoulder height: seen from "
                  "behind, he raises his crackling brass Tesla coil high in his right hand, its blue-violet arcs lighting "
                  "the whole packed hall as the crowd chants and pumps their fists toward him, Tesla coils arcing on both "
                  "sides, Thomas Edison (Image 3) a small figure at the far edge of the stage clutching his own glowing "
                  "amber bulb and turning away.",
}
for gid, shot in GAP_WIDE.items():
    g = dict(v2["OPEN"])
    g["id"] = gid
    g["prompt"] = g["prompt"].replace(g["prompt"].split("\n\n")[1], "Cinematic photoreal shot, 16:9. " + shot)
    if gid != "WIDE_OPEN":
        g["closeup_lora"] = 0.0
    clips.append(g)

ids = {c["id"]: c for c in clips}
for prev, cur in zip(edl, edl[1:]):
    assert abs(prev["t1"] - cur["t0"]) < 1e-6, (prev, cur)
assert abs(edl[-1]["t1"] - END_T) < 1e-6
for x in edl:
    c = ids[x["clip"]]
    if c["kind"] == "rap":
        _, lw_end, _ = lip[x["clip"]]
        assert x["t1"] >= lw_end - 0.05, f"{x['clip']} cut at {x['t1']:.2f} before its last word ends {lw_end:.2f}"
        assert x["t0"] >= c["audio"][0] - 1e-6
    else:
        assert x["in"] + (x["t1"] - x["t0"]) <= c["frames"] / 24 - 0.05, x

# punch-ins on punchline words, flashes on section changes
def word_t(cid, word):
    a0, a1 = ids[cid]["audio"]
    return next(w["t0"] for w in WORDS if a0 - 0.05 <= w["t0"] < a1 + 0.3 and w["w"].strip(",.?!—\"'").lower().startswith(word))

def slot_end(cid):
    return next(x["t1"] for x in edl if x["clip"] == cid)

fx = [{"type": "flash", "t0": round(grid["beat0"], 3), "t1": round(grid["beat0"] + 0.08, 3), "alpha": 0.7}]
for cid, w, amt in [("A02", "crawl", 0.08), ("A07", "humor", 0.10), ("B06", "liar", 0.10), ("B08", "law", 0.10),
                    ("A12", "dreamers", 0.10), ("A16", "counting", 0.08), ("B09", "dropped", 0.10)]:
    if cid not in pushed:  # those lines now carry a real camera push-in
        fx.append({"type": "punch", "t0": round(word_t(cid, w), 3), "t1": slot_end(cid), "amount": amt})
for cid, w in [("B12", "spark")]:
    t = round(word_t(cid, w), 3)
    fx += [{"type": "flash", "t0": t, "t1": t + 0.08, "alpha": 0.85}, {"type": "shake", "t0": t, "t1": t + 0.55, "px": 9},
           ] + ([] if cid in pushed else [{"type": "punch", "t0": t, "t1": slot_end(cid), "amount": 0.08}])
t = round(word_t("B16", "dark"), 3)
fx.append({"type": "dark", "t0": t, "t1": slot_end("B16"), "amount": 0.12})
for x in edl:
    if x["clip"] in ("CROWD_OOH", "DJ", "WIDE_OUTRO"):
        fx.append({"type": "flash", "t0": x["t0"], "t1": round(x["t0"] + 0.08, 3), "alpha": 0.8})
fx.append({"type": "dark", "t0": next(x["t0"] for x in edl if x["clip"] == "BLACKOUT"),
           "t1": next(x["t1"] for x in edl if x["clip"] == "BLACKOUT"), "amount": 0.10})

json.dump(clips, open(os.path.join(WORK, "clips.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(edl, open(os.path.join(WORK, "edl.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(fx, open(os.path.join(WORK, "fx.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

if "--link-v2-clips" in sys.argv:  # reuse rendered non-lip takes from v2
    picks_p = os.path.join(WORK, "picks.json")
    picks = json.load(open(picks_p)) if os.path.exists(picks_p) else {}
    os.makedirs(os.path.join(EP, "clips"), exist_ok=True)
    for sid in ("OPEN", "FACEOFF", "CROWD_OOH", "R_T1", "B_STEP", "DJ", "CROWD_ERUPT", "R_E1", "BLACKOUT", "END"):
        src = os.path.join(V2, "clips", f"{sid}_t1.mp4")
        shutil.copy2(src, os.path.join(EP, "clips", f"{sid}_t1.mp4"))
        picks[sid] = 1
    json.dump(picks, open(picks_p, "w"), indent=1)
    print("linked", len(picks), "v2 non-lip takes into clips/ + picks.json")

n_lip = sum(1 for c in clips if c["kind"] == "rap")
print(f"wrote {len(clips)} clips ({n_lip} lip), {len(edl)} edl entries, {len(fx)} fx, timeline 0-{END_T:.2f}s")
