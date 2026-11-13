#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Michael De Santa vs Trevor Philips (GTA V) — 3-Scene No-Microphone Live-Action Cinema MV Storyboard.

Three Real Locations (Realism V3 + Cooke Panchro T2.2 + Kodak Vision3 500T, mic="none"):
  1. Scene 1 (Verse 1: A01–A08): Rockford Hills Luxury Mansion Pool Terrace at Night (Los Santos skyline bokeh)
  2. Beat Switch 1 Transition: Iconic GTA V 3-step Satellite Zoom (Los Santos -> Blaine County / Sandy Shores)
  3. Scene 2 (Verse 2: B01–B08): Sandy Shores Battered Trailer & Dusty Airfield at Fiery Dusk
  4. Bridge Transition -> Scene 3 (Round 2: A09–A16 & B09–B16): North Yankton Ludendorff Snowy Graveyard at Night
     (lit from the side by warm 3200K pickup-truck halogen headlights + 6500K blizzard rim light, zero cyan skin cast)
"""
import json
import math
import os
import re

EP = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(EP, "work")
FPS = 24
PRE = 0.08
STILL_FRAMES = 90
MAX_FRAMES = 226

for sub in ("work", "refs", "clips"):
    os.makedirs(os.path.join(EP, sub), exist_ok=True)
for req in (
    "work/lines.json",
    "work/words_edit.json",
    "work/grid.json",
    "work/vocals_final.wav",
    "work/music_final.wav",
    "work/a_face_clean.png",
    "work/b_face_clean.png",
    "work/a_face_winter.png",
    "work/b_face_winter.png",
    "work/stage_mansion.png",
    "work/stage_desert.png",
    "work/stage_yankton_a.png",
    "work/stage_yankton_b.png",
    "refs/scene_mansion.png",
    "refs/scene_desert.png",
    "refs/scene_yankton.png",
):
    assert os.path.exists(os.path.join(EP, req)), "missing " + req

json.dump(
    {
        "handheld_px": 9,
        "drift": 0.035,
        "margin": 0.055,
        "whip": True,
        "whip_secs": 0.06,
        "contrast": 1.03,
        "saturation": 1.0,
        "beat_pulse": 0.02,
        "grain": 3,
        "vignette": 0,
        "cool": False,
    },
    open(os.path.join(WORK, "live.json"), "w", encoding="utf-8"),
    indent=1,
)

e = json.load(open(os.path.join(EP, "episode.json"), encoding="utf-8"))
L = json.load(open(os.path.join(WORK, "lines.json"), encoding="utf-8"))
WORDS = json.load(open(os.path.join(WORK, "words_edit.json"), encoding="utf-8"))
ACTIONS = json.load(open(os.path.join(EP, "line_actions.json"), encoding="utf-8"))
grid = json.load(open(os.path.join(WORK, "grid.json"), encoding="utf-8"))
END_T = round(grid["length"], 3)
A, B = e["a"], e["b"]
SCENES = e["scenes"]


def norm(w: str) -> str:
    return re.sub(r"[^a-z0-9']", "", w.lower().replace("’", "'"))


def is_sung(w: dict) -> bool:
    raw = w["w"].strip("!?,.\"'—")
    if w["w"].startswith("["):
        return False
    if raw.upper() in ("OOOH", "LEGEND", "RESPECT", "ROUND", "TWO", "BRAVO", "WASTED"):
        return False
    return True


cid_of = lambda l: ("A" if l["who"] == "a" else "B") + "%02d" % l["n"]
line_by = {cid_of(l): l for l in L}
order = [cid_of(l) for l in L]
nxt_start = {c: (L[i + 1]["start"] if i + 1 < len(L) else END_T) for i, c in enumerate(order)}


def last_word_end(c: str) -> float:
    l = line_by[c]
    ws = [w for w in WORDS if l["start"] - 0.1 <= w["t0"] < nxt_start[c] - 0.05 and is_sung(w)]
    return max(w["t1"] for w in ws)


def word_t(c: str, word: str) -> float:
    l = line_by[c]
    hits = [
        w["t0"]
        for w in WORDS
        if l["start"] - 0.1 <= w["t0"] < nxt_start[c] - 0.05 and norm(w["w"]) == norm(word)
    ]
    assert hits, f"{c}: word '{word}' not found"
    return round(hits[0], 3)


lw_end = {c: last_word_end(c) for c in order}


def fit(dur: float) -> int:
    need = math.ceil((dur + 0.35) * FPS)
    k = max(4, math.ceil((need - 5) / 17))
    f = 17 * k + 5
    assert f <= MAX_FRAMES, f"clip of {dur:.2f}s needs {f} frames (> {MAX_FRAMES})"
    return f


SIDE = {"a": "screen-left", "b": "screen-right"}
FACING = {"a": "facing right", "b": "facing left"}
LR = {"a": ("left", "right"), "b": ("right", "left")}
HAND = ", shot on a handheld 35mm ARRI Alexa Mini LF cinema camera with subtle organic movement"
READ = ", his face, jaw, and lips large, unobstructed, and clearly readable in every frame (no microphone anywhere)"


def cam_move(kind: str, who: str, loc_tag: str) -> str:
    me, them = LR[who]
    loc_ground = {
        "mansion": "He stands out on his Rockford Hills luxury hillside mansion pool terrace at night beside the sleek glass balcony railing, the glittering Los Santos skyscraper skyline glowing far below in warm 2700K bokeh (no stage, no crowd)",
        "desert": "He stands outside his battered Sandy Shores corrugated-metal desert trailer beside the dusty airfield at fiery golden-amber dusk (no stage, no crowd)",
        "yankton": "He stands beside the freshly dug open snow grave in the snow-blanketed Ludendorff cemetery at midnight, illuminated from the side by warm 3200K amber pickup-truck halogen headlights cutting through falling snow and steaming breath (no stage, no crowd)",
    }[loc_tag]

    if kind == "PUSH":
        return (
            "The camera starts on a waist-up medium shot of <Subject 1>, then pushes in with large amplitude at slow "
            "speed on a smooth cinema dolly until it settles on a tight chest-up close-up at Cooke Panchro 50mm T2.2 shallow depth of field"
            + READ
            + ". "
            + loc_ground
        )
    if kind == "LONG":
        return (
            "From the very first frame to the last, the camera holds a frontal chest-up close-up at eye level on a Cooke Panchro 50mm T2.2 prime lens"
            + HAND
            + ", pushing in with small amplitude at slow speed across the shot; his face fills the upper two thirds of the 16:9 frame"
            + READ
            + ". "
            + loc_ground
        )
    if kind == "TQ":
        return (
            f"The camera holds a chest-up three-quarter medium close-up of <Subject 1> on the {me} half of the 16:9 frame, {FACING[who]}"
            + HAND
            + ", slowly arcing a few degrees around him at T2.2 shallow depth of field"
            + READ
            + ". "
            + loc_ground
        )
    if kind == "ECU":
        return (
            "A handheld 28mm wide-angle cinema lens is close to <Subject 1> slightly below chin height, looking slightly up at him: "
            "a tight, high-impact close-up where his head and upper shoulders fill the 16:9 frame (both hands free, zero microphone); "
            "the camera pushes in with small amplitude at slow speed"
            + READ
            + ". "
            + loc_ground
        )
    if kind == "FACE":
        return (
            "The camera holds a tense eye-level profile two-shot of the two men standing face to face across the freshly dug open snow grave, "
            f"barely two feet apart in the warm 3200K pickup-truck headlight beam: <Subject 1> on {SIDE[who]} in profile {FACING[who]}, leaning in and rapping "
            f"straight into <Subject 2>'s face with steaming breath in the cold night air, <Subject 2> on {SIDE['b' if who == 'a' else 'a']} in profile "
            f"{FACING['b' if who == 'a' else 'a']}; both framed chest-up as the camera pushes in with small amplitude at slow speed at T2.2 shallow depth of field"
            + HAND
            + ", <Subject 1>'s lips and jaw clearly readable in every frame (no microphone anywhere)"
        )
    if kind == "FACEWIDE":
        return (
            f"The camera holds a waist-up medium two-shot across the snow-covered grave at Ludendorff cemetery: <Subject 1> on {SIDE[who]} {FACING[who]}, "
            f"rapping fiercely across the open grave toward <Subject 2> on {SIDE['b' if who == 'a' else 'a']} {FACING['b' if who == 'a' else 'a']}, "
            "warm 3200K amber pickup-truck headlight beams slicing through falling snowflakes and steaming breath between the two men while warm 2700K church lantern bokeh glows far behind"
            + HAND
            + READ
        )
    if kind == "ARC":
        return (
            "The camera starts on a chest-up medium shot of <Subject 1> in the warm 3200K headlight beam as he raps, then trucks "
            f"{me} and pans {them} with medium amplitude at slow speed around his {me} shoulder until it frames an over-the-shoulder two-shot "
            f"across the snowy grave with <Subject 2> glaring silently on {SIDE['b' if who == 'a' else 'a']}"
            + READ
        )
    if kind == "CRASH":
        return (
            f"The camera starts on an over-the-shoulder medium shot past the blurred snow-dusted shoulder of <Subject 2> in the {them} foreground "
            f"onto <Subject 1> chest-up on the {me} facing the camera, then executes a sudden fast crash push-in past the shoulder that lands on a tight "
            "close-up of <Subject 1>'s face in the warm 3200K headlight glow"
            + READ
        )
    if kind == "REVEAL":
        return (
            f"The camera starts on a chest-up three-quarter medium close-up of <Subject 1> alone on the {me} side of the snowy grave, {FACING[who]}, "
            f"then pans {them} with small amplitude at slow speed to reveal <Subject 2> standing across the open grave on {SIDE['b' if who == 'a' else 'a']}"
            + READ
        )
    raise KeyError(kind)


SCENE_CFG = {
    "mansion": {
        "venue_en": SCENES["mansion"]["venue_en"],
        "light_en": SCENES["mansion"]["light_en"],
        "bg_desc_en": "the luxurious Rockford Hills hillside mansion infinity-pool terrace overlooking the glittering Los Santos night skyline",
        "bg_lights_en": "warm 2700K mansion wall-sconce and glittering Los Santos skyscraper bokeh",
        "bg_motion_en": "shimmering amber pool water reflections and gently swaying palm silhouettes in the night breeze",
    },
    "desert": {
        "venue_en": SCENES["desert"]["venue_en"],
        "light_en": SCENES["desert"]["light_en"],
        "bg_desc_en": "the gritty Sandy Shores battered trailer yard and dusty dirt airfield at fiery sunset",
        "bg_lights_en": "warm 2700K trailer porch bulb and distant airfield floodlight bokeh",
        "bg_motion_en": "golden-amber desert dust drifting slowly across the warm twilight glow",
    },
    "yankton": {
        "venue_en": SCENES["yankton"]["venue_en"],
        "light_en": SCENES["yankton"]["light_en"],
        "bg_desc_en": "the snow-blanketed Ludendorff cemetery at midnight with an open grave, upright shovel, and warm pickup-truck headlight beams",
        "bg_lights_en": "warm 3200K amber pickup-truck headlight beams and distant 2700K church lantern bokeh",
        "bg_motion_en": "wind-blown snowflakes swirling continuously through the warm amber headlight beams and faint steaming breath",
    },
}

TWO = {"FACE", "FACEWIDE", "ARC", "CRASH", "REVEAL"}
LISTEN = {
    "FACE": " while <Subject 2> keeps his mouth firmly closed, jaw clenched hard, staring straight back across the snowy grave without blinking",
    "FACEWIDE": " while <Subject 2> stands motionless in his winter coat on the opposite side of the open grave with his mouth firmly closed",
    "ARC": " while <Subject 2> watches him in cold, silent fury with his mouth firmly closed",
    "CRASH": " while <Subject 2> stands motionless in the foreground with his back to the camera",
    "REVEAL": " while <Subject 2> glares silently across the open grave with his mouth firmly closed",
}

# (c0, c1, scene_tag, cam_kind)
SHOTS = [
    # ---- Verse 1: Michael on Rockford Hills Mansion Pool Terrace (Night, solo cinema MV)
    ("A01", "A02", "mansion", "PUSH"),
    ("A03", "A04", "mansion", "TQ"),
    ("A05", "A06", "mansion", "LONG"),
    ("A07", "A07", "mansion", "ECU"),
    ("A08", "A08", "mansion", "TQ"),
    # ---- Verse 2: Trevor at Sandy Shores Trailer & Airfield (Dusk, solo cinema MV)
    ("B01", "B02", "desert", "ECU"),
    ("B03", "B04", "desert", "TQ"),
    ("B05", "B06", "desert", "LONG"),
    ("B07", "B07", "desert", "PUSH"),
    ("B08", "B08", "desert", "ECU"),
    # ---- Verse 3: Michael in North Yankton Snowy Graveyard (Night, winter coat, face-to-face confrontation)
    ("A09", "A10", "yankton", "REVEAL"),
    ("A11", "A12", "yankton", "FACE"),
    ("A13", "A13", "yankton", "TQ"),
    ("A14", "A14", "yankton", "ECU"),
    ("A15", "A15", "yankton", "FACEWIDE"),
    ("A16", "A16", "yankton", "LONG"),
    # ---- Verse 4: Trevor in North Yankton Snowy Graveyard (Night, winter parka, climax & cold execution)
    ("B09", "B10", "yankton", "CRASH"),
    ("B11", "B12", "yankton", "FACE"),
    ("B13", "B13", "yankton", "ARC"),
    ("B14", "B14", "yankton", "FACEWIDE"),
    ("B15", "B15", "yankton", "ECU"),
    ("B16", "B16", "yankton", "LONG"),
]


def action_for_lines(covered: list[str]) -> str:
    parts = []
    for cid in covered:
        who = line_by[cid]["who"]
        idx = line_by[cid]["n"] - 1
        act = ACTIONS[who][idx]
        # Avoid holding fragile glass props in hand so H3 hands stay 100% clean
        act = act.replace(" while swirling amber scotch in a crystal rocks glass with his right hand", ", gesturing smoothly over the glass balcony railing with his open right hand")
        act = act.replace(" while tilting his whiskey glass in his right hand", "")
        parts.append(act)
    if len(parts) == 1:
        return parts[0]
    return f"first {parts[0]}, then {parts[1]}"


clips, lip = [], {}
for c0, c1, sc_tag, kind in SHOTS:
    covered = order[order.index(c0) : order.index(c1) + 1]
    who = line_by[c0]["who"]
    is_winter = sc_tag == "yankton"
    if is_winter:
        me_k, them_k = ("a_face_winter", "b_face_winter") if who == "a" else ("b_face_winter", "a_face_winter")
        plate = "stage_yankton_a" if who == "a" else "stage_yankton_b"
        look_me = A["look_winter"] if who == "a" else B["look_winter"]
        look_them = B["look_winter"] if who == "a" else A["look_winter"]
    else:
        me_k, them_k = ("a_face_clean", "b_face_clean") if who == "a" else ("b_face_clean", "a_face_clean")
        plate = "stage_mansion" if sc_tag == "mansion" else "stage_desert"
        look_me = A["look"] if who == "a" else B["look"]
        look_them = B["look"] if who == "a" else A["look"]

    a0 = round(line_by[c0]["start"] - PRE, 3)
    a1 = round(max(line_by[c1]["end"], lw_end[c1]), 3)
    text = " / ".join(line_by[x]["text"] for x in covered)
    frames = fit(a1 - a0)
    two = kind in TWO
    sc = SCENE_CFG[sc_tag]

    clip = {
        "id": c0,
        "kind": "rap",
        "who": who,
        "scene": sc_tag,
        "line": line_by[c0]["n"],
        "move": kind,
        "mic": "none",
        "text": text,
        "audio": [a0, a1],
        "lead": 0.0,
        "frames": frames,
        "static": False,
        "sway": 0.5,
        "drift": 0.0,
        "action": action_for_lines(covered),
        "two_shot": two,
        "cam": cam_move(kind, who, sc_tag),
        "bg": plate,
        "bg_exterior": True,
        "venue_en": sc["venue_en"],
        "light_en": sc["light_en"],
        "bg_desc_en": sc["bg_desc_en"],
        "bg_lights_en": sc["bg_lights_en"],
        "bg_motion_en": sc["bg_motion_en"],
        "crowd_motion_en": "",
        "look_me": look_me,
        "look_them": look_them,
        "image_keys": [me_k] + ([them_k] if two else []) + [plate],
    }
    if two:
        clip.update(listener_side=SIDE["b" if who == "a" else "a"], listener=LISTEN[kind])
    if kind in ("ECU", "CRASH"):
        clip["lens"] = "28mm wide-angle"
    if kind in ("PUSH", "ARC", "CRASH", "FACE", "FACEWIDE"):
        clip["closeup_lora"] = 0.22
    clips.append(clip)
    lip[c0] = (a0, lw_end[c1], covered)


# ---------------------------------------------------------------- Non-lip-sync Cinema Shots (Establishing, GTA Satellite Switch, L-Cut Reactions)
IMG = {
    "a_face_clean": "Michael De Santa in his tailored charcoal suit and slate-blue open-collar dress shirt (keep his exact 45-year-old square-jawed face, silver-grey temples, hazel eyes, clean-shaven jaw clear of lips)",
    "b_face_clean": "Trevor Philips in his sweat-stained off-white crew-neck pocket T-shirt (keep his exact 46-year-old gaunt sinewy face, receding M-shaped hairline, deeply furrowed brow, short scraggly stubble clear of lips, dotted neck tattoo)",
    "a_face_winter": "Michael De Santa in winter North Yankton wearing a heavy dark navy-black wool overcoat with upturned collar over a charcoal sweater (keep his exact facial bone structure, silver-templed dark hair dusted with snowflakes)",
    "b_face_winter": "Trevor Philips in winter North Yankton wearing a rugged brown leather-and-sheepskin winter parka over his off-white T-shirt (keep his exact gaunt weathered face, receding hairline with snow, dotted neck tattoo)",
    "scene_mansion": "the luxurious Rockford Hills hillside mansion terrace and infinity pool deck at night overlooking the glittering Los Santos downtown skyline",
    "scene_desert": "the gritty sun-scorched Sandy Shores battered trailer yard and dusty dirt airfield at fiery golden-amber sunset",
    "scene_yankton": "the snow-blanketed Ludendorff cemetery in North Yankton during a midnight snowfall with a freshly dug open grave, upright snow shovel, distant wooden church, and a parked red pickup truck casting warm 3200K amber halogen headlights across the snow",
    "stage_mansion": "the out-of-focus glittering Los Santos night skyline and infinity pool glow behind Michael's Rockford Hills terrace",
    "stage_desert": "the out-of-focus Sandy Shores trailer porch bulb and dusty desert airfield sunset glow behind Trevor",
    "stage_yankton_a": "the out-of-focus warm 3200K pickup-truck headlight beam and snow-covered tombstones in North Yankton behind Michael",
    "stage_yankton_b": "the out-of-focus snow-blanketed Ludendorff cemetery, open grave, and warm church-lantern glow behind Trevor",
}

NO_TEXT_NOMIC = (
    "Keep every character's exact facial bone structure, skin pores, hair, and outfit faithful to the reference images. "
    "Authentic live-action 35mm crime cinema shot on ARRI Alexa Mini LF with Cooke Panchro T2.2 prime lens on Kodak Vision3 500T film, "
    "natural warm blood-toned matte human skin (zero CGI plastic sheen, zero cyan skin cast). "
    "Nobody holds a microphone anywhere in the frame. No subtitles, no on-screen text, no HUD, no logos, no watermark."
)


def still(sid: str, keys: list[str], shot_desc: str, frames: int = STILL_FRAMES, lora: float | None = None):
    head = " ".join(f"Image {i} is {IMG[k]}." for i, k in enumerate(keys, 1))
    c = {
        "id": sid,
        "kind": "still",
        "move": "V2",
        "frames": frames,
        "image_keys": keys,
        "prompt": "\n\n".join([head, "Cinematic live-action 35mm crime film shot, 16:9. " + shot_desc, NO_TEXT_NOMIC]),
    }
    if lora is not None:
        c["closeup_lora"] = lora
    clips.append(c)


# Intro & Establishing Plates
still(
    "MANSION_OPEN",
    ["scene_mansion"],
    "Wide establishing cinema crane shot gliding smoothly forward across the empty luxurious Rockford Hills hillside mansion infinity-pool terrace at night (Image 1): "
    "warm 2700K architectural wall sconces and shimmering amber pool water on the left, sleek glass balcony railing, tall palm tree silhouettes, and the vast glittering Los Santos skyscraper skyline glowing below under a deep midnight sky.",
    frames=124,
    lora=0.0,
)
still(
    "M_TERRACE_PREP",
    ["a_face_clean", "stage_mansion"],
    "Chest-up medium close-up at eye level on the Rockford Hills mansion terrace at night: Michael De Santa (Image 1) stands beside the glass balcony railing with the glittering warm 2700K Los Santos night skyline blurred at Cooke Panchro T2.2 behind him (Image 2); "
    "warm 3200K terrace wall-sconce side-key light sculpts natural warm skin tone while cool 5600K moonlight traces his silver-templed hair and charcoal suit shoulders; mouth firmly closed, he exhales slowly with a cynical world-weary mob-boss smirk as the camera pushes in slowly.",
    frames=141,
    lora=0.30,
)

# Beat Switch 1: Iconic GTA V 3-Step Satellite Character-Switch Transition (Rockford Hills -> Sandy Shores)
still(
    "SAT_ZOOM_UP",
    ["scene_mansion"],
    "Iconic high-speed top-down aerial helicopter-to-satellite pull-back shot starting above the glowing Rockford Hills hillside mansion pool terrace at night (Image 1) and rocketing straight upward into the night sky: "
    "the glittering golden grid of Los Santos freeways, skyscrapers, and palm-lined hills rapidly shrinks below through drifting night clouds in dramatic 35mm aerial cinematography.",
    frames=124,
    lora=0.0,
)
still(
    "SAT_DESERT_DROP",
    ["scene_desert"],
    "High-altitude top-down aerial dive plunging rapidly down through golden-amber desert dust clouds at fiery sunset and swooping low into the gritty Sandy Shores trailer yard and dirt airfield (Image 1): "
    "the battered corrugated-metal mobile home with its warm 2700K porch bulb, red steel jerrycan, Joshua trees, and glowing airfield control tower rush into crisp 35mm focus as the camera decelerates near ground level.",
    frames=124,
    lora=0.0,
)
still(
    "T_TRAILER_ERUPT",
    ["b_face_clean", "stage_desert"],
    "Handheld 35mm medium close-up outside the battered Sandy Shores trailer at fiery golden-amber dusk: Trevor Philips (Image 1) steps aggressively forward into the warm 3200K sunset glow with the blurred trailer porch light and dusty airfield behind him at T2.2 (Image 2); "
    "mouth firmly closed, veins tensing in his neck beneath his dotted tattoo, rolling his shoulders with a feral unhinged glare straight into the lens before snapping into his verse.",
    frames=124,
    lora=0.30,
)

# Round 1 Cross-Location L-Cut Reactions
still(
    "R_T_MOMMY",
    ["b_face_clean", "stage_desert"],
    "Tight frontal head-and-shoulders close-up of Trevor Philips (Image 1) alone at Sandy Shores dusk at Cooke Panchro 50mm T2.2 shallow depth of field with warm 2700K trailer light bokeh behind him (Image 2): "
    "he is listening in stung silence, mouth firmly closed, his left eye twitching violently under his deeply furrowed brow as his jaw clenches in explosive rage.",
    frames=90,
)
still(
    "R_M_WIFE",
    ["a_face_clean", "stage_mansion"],
    "Tight frontal head-and-shoulders close-up of Michael De Santa (Image 1) alone on his Rockford Hills night terrace at Cooke Panchro 50mm T2.2 shallow depth of field with glittering Los Santos skyline bokeh behind him (Image 2): "
    "mouth firmly closed, his smug Vinewood smirk vanishes instantly, jaw muscle twitching and hazel eyes narrowing in stung humiliation under warm 3200K terrace side-lighting.",
    frames=107,
)

# Bridge Transition & Round 2 North Yankton Snowy Graveyard Standoff
still(
    "YANKTON_OPEN",
    ["scene_yankton"],
    "Wide establishing 35mm winter night shot pushing slowly across the snow-blanketed Ludendorff cemetery in North Yankton during a heavy midnight snowfall (Image 1): "
    "from the left, the twin warm 3200K amber halogen headlights of a parked red pickup truck cut dramatically through swirling snowflakes across the freshly dug open snow grave, dark wooden coffin lid, and upright iron snow shovel, with a distant wooden church lantern glowing on the snowy hill.",
    frames=141,
    lora=0.0,
)
still(
    "GRAVE_STANDOFF",
    ["a_face_winter", "b_face_winter"],
    "Tense waist-up profile two-shot at eye level across the freshly dug open grave in the snow-covered Ludendorff cemetery at night: "
    "Michael De Santa (Image 1) on screen-left in his heavy dark navy wool overcoat facing right, and Trevor Philips (Image 2) on screen-right in his worn brown sheepskin winter parka facing left; "
    "both keep their mouths firmly closed, warm breath steaming in the freezing air as warm 3200K amber pickup-truck headlights sculpt natural warm skin tones on their faces and 6500K icy moonlight rims the falling snow; handheld 35mm camera slowly creeps closer.",
    frames=158,
    lora=0.22,
)
still(
    "R_T_SNOW",
    ["b_face_winter", "stage_yankton_b"],
    "Tight chest-up close-up of Trevor Philips (Image 1) in his brown sheepskin winter parka in the snowy North Yankton graveyard at T2.2 shallow depth of field (Image 2): "
    "mouth firmly closed, steaming breath rising in the warm 3200K amber truck headlight glow, his eyes glistening with raw nine-year betrayal and fury as snowflakes catch on his hair.",
    frames=124,
)
still(
    "R_M_JUDAS",
    ["a_face_winter", "stage_yankton_a"],
    "Tight chest-up close-up of Michael De Santa (Image 1) in his dark wool overcoat in the snowy North Yankton graveyard at T2.2 shallow depth of field (Image 2): "
    "mouth firmly closed, warm breath misting in the 3200K amber truck headlight beam, swallowing hard with cold cornered guilt in his tired eyes as snow falls around him.",
    frames=124,
)
still(
    "YANKTON_AFTERMATH",
    ["a_face_winter", "b_face_winter"],
    "The shot starts on a waist-up medium two-shot of Michael De Santa (Image 1) on screen-left in his dark navy wool overcoat and Trevor Philips (Image 2) on screen-right in his brown sheepskin winter parka standing motionless on opposite sides of the freshly dug open snow grave in North Yankton, mouths firmly closed, locking a final ice-cold stare through swirling snow and steaming breath in the warm 3200K pickup headlight beam. "
    "Then the cinema crane pulls backward and rises high into the snowy midnight air with large amplitude at slow speed, revealing the lone red pickup truck's twin amber headlight beams illuminating the open grave, wooden coffin lid, and upright iron shovel in the vast silent cemetery.",
    frames=192,
    lora=0.0,
)

ids = {c["id"]: c for c in clips}

# ---------------------------------------------------------------- Edit Decision List (EDL)
# Word-level L-cuts (keeping >= 0.9s on the singer before cutting to opponent reaction)
CUTAWAYS = [
    ("A05", "A06", "fetal", None, "R_T_MOMMY", 0.35),
    ("B03", "B04", "stretching", None, "R_M_WIFE", 0.30),
    ("B05", "B06", "prime-time", None, "R_M_WIFE", 2.10),
    ("A14", "A14", "nobody", None, "R_T_SNOW", 0.35),
    ("B13", "B13", "family", None, "R_M_JUDAS", 0.35),
]

GAPS = {
    # 14.81s Beat Switch 1 (31.92s -> 46.71s): GTA V 3-step satellite character switch from Mansion to Sandy Shores!
    "A08": [
        ("M_TERRACE_PREP", 2.20),
        ("SAT_ZOOM_UP", 0.10),
        ("SAT_DESERT_DROP", 0.10),
        ("T_TRAILER_ERUPT", 0.15),
    ],
    # 10.54s Bridge (67.85s -> 78.37s): Howling blizzard + shovel thud -> North Yankton Ludendorff Graveyard!
    "B08": [
        ("YANKTON_OPEN", 0.10),
        ("GRAVE_STANDOFF", 0.15),
        ("R_T_SNOW", 1.80),
    ],
    # 22.34s Final Drop (99.54s -> 121.86s): Gun cocking click + distorted hardcore climax build in the snow!
    "A16": [
        ("R_T_SNOW", 3.15),
        ("YANKTON_OPEN", 2.15),
        ("GRAVE_STANDOFF", 2.55),
        ("R_M_JUDAS", 1.85),
        ("YANKTON_AFTERMATH", 0.15),
    ],
}

first = lip["A01"][0]  # 9.920s
spans = [
    (0.000, 4.900, "MANSION_OPEN", 0.10),
    (4.900, 7.500, "SAT_DESERT_DROP", 1.20),
    (7.500, first, "M_TERRACE_PREP", 0.15),
]

lip_ids = [s[0] for s in SHOTS]
cut_by = {}
for head, line, word, d, sid, inn in CUTAWAYS:
    cut_by.setdefault(head, []).append((word_t(line, word), d, sid, inn))

MIN_ON = 0.85
for k, c in enumerate(lip_ids):
    a0, lwe, _ = lip[c]
    nxt = lip_ids[k + 1] if k + 1 < len(lip_ids) else None
    t0 = spans[-1][1]
    raw_gap = (lip[nxt][0] - (lwe + 0.02)) if (nxt is not None and c in GAPS) else 0.0
    gap_items = GAPS.get(c, []) if raw_gap >= 0.45 else []
    gap = bool(gap_items)
    t1 = round(lwe + 0.02, 3) if (nxt is None or gap) else round(max(lip[nxt][0], lwe + 0.02), 3)
    t = t0
    for tc, d, sid, inn in sorted(cut_by.get(c, [])):
        te = t1 if d is None else round(tc + d, 3)
        assert tc - t >= MIN_ON, f"{c}: only {tc - t:.2f}s on singer before {sid}"
        assert te <= t1 + 1e-6
        spans.append((t, tc, c, None))
        spans.append((tc, te, sid, inn))
        t = te
    if t1 - t > 1e-6:
        assert t == t0 or t1 - t >= 0.5, f"{c}: {t1 - t:.2f}s tail after cutaway"
        spans.append((t, t1, c, None))
    if gap:
        g0, g1 = t1, lip[nxt][0]
        n = len(gap_items)
        for j, (sid, inn) in enumerate(gap_items):
            s_a = round(g0 + (g1 - g0) * j / n, 3)
            s_b = round(g0 + (g1 - g0) * (j + 1) / n, 3)
            # Clamp segment duration to <= 4.5s by splitting long final-drop musical build cleanly
            spans.append((s_a, s_b, sid, inn))

# Outro (143.97s -> 162.275s = 18.305s): WASTED! WASTED! snowy graveyard aftermath
o0 = spans[-1][1]
rem = END_T - o0
spans.extend(
    [
        (o0, round(o0 + 3.40, 3), "R_M_JUDAS", 3.15),
        (round(o0 + 3.40, 3), round(o0 + 6.90, 3), "GRAVE_STANDOFF", 4.10),
        (round(o0 + 6.90, 3), round(o0 + 10.60, 3), "YANKTON_OPEN", 2.00),
        (round(o0 + 10.60, 3), END_T, "YANKTON_AFTERMATH", 0.20),
    ]
)

edl = [{"t0": a, "t1": b, "clip": c, "in": i} for a, b, c, i in spans]

used = {x["clip"] for x in edl}
clips = [c for c in clips if c["id"] in used]
ids = {c["id"]: c for c in clips}

# Ensure every non-rap clip has enough frames for its latest (in + duration) usage
for x in edl:
    c = ids[x["clip"]]
    if c["kind"] != "rap":
        need_s = float(x["in"] or 0.0) + (x["t1"] - x["t0"]) + 0.25
        req_f = fit(need_s)
        if req_f > c["frames"]:
            c["frames"] = req_f

# Strict Storyboard Assertions
for prev, cur in zip(edl, edl[1:]):
    assert abs(prev["t1"] - cur["t0"]) < 1e-6, (prev, cur)
assert abs(edl[0]["t0"]) < 1e-6 and abs(edl[-1]["t1"] - END_T) < 1e-6
for x in edl:
    c = ids[x["clip"]]
    d = x["t1"] - x["t0"]
    assert d > 0.3, f"{x['clip']} only {d:.2f}s"
    assert (c["frames"] - 5) % 17 == 0, f"{c['id']} frames={c['frames']} violates 17k+5"
    if c["kind"] == "rap":
        assert x["t0"] >= c["audio"][0] - 1e-6, x
        assert x["t1"] - c["audio"][0] + c["lead"] <= c["frames"] / FPS + 1e-6, f"{x['clip']} runs past its clip"
    else:
        assert x["in"] + d <= c["frames"] / FPS - 0.05, f"{x['clip']}: in {x['in']:.2f} + {d:.2f}s > {c['frames']/FPS:.2f}s"

cut_ids = {c[4] for c in CUTAWAYS}
for w in WORDS:
    if not is_sung(w) or w["t0"] < first or w["t0"] > lip[lip_ids[-1]][1]:
        continue
    x = next((x for x in edl if x["t0"] - 1e-6 <= w["t0"] < x["t1"]), None)
    assert x and (ids[x["clip"]]["kind"] == "rap" or x["clip"] in cut_ids), f"word {w['w']!r} at {w['t0']:.2f} lands on {x}"

# Post FX (Beat-switch flashes & punch zooms on lethal bars)
fx = [
    {"type": "flash", "t0": round(grid["beat0"], 3), "t1": round(grid["beat0"] + 0.08, 3), "alpha": 0.65},
    # GTA V Character-Switch camera flash pulses on Beat Switch 1
    {"type": "flash", "t0": 34.67, "t1": 34.76, "alpha": 0.85},
    {"type": "flash", "t0": 38.37, "t1": 38.46, "alpha": 0.85},
    {"type": "flash", "t0": 46.70, "t1": 46.79, "alpha": 0.90},
    {"type": "shake", "t0": 46.78, "t1": 47.45, "px": 10},
    # Round 2 Blizzard Grave flash & Judas execution punch
    {"type": "flash", "t0": 78.37, "t1": 78.46, "alpha": 0.75},
    {"type": "flash", "t0": 121.86, "t1": 121.95, "alpha": 0.90},
    {"type": "shake", "t0": 121.94, "t1": 122.55, "px": 10},
    {"type": "punch", "t0": word_t("B16", "Judas"), "t1": 143.95, "amount": 0.08},
]

json.dump(clips, open(os.path.join(WORK, "clips.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(edl, open(os.path.join(WORK, "edl.json"), "w", encoding="utf-8"), indent=1)
json.dump(fx, open(os.path.join(WORK, "fx.json"), "w", encoding="utf-8"), indent=1)

n_rap = sum(1 for c in clips if c["kind"] == "rap")
n_still = sum(1 for c in clips if c["kind"] != "rap")
tot_f = sum(c["frames"] for c in clips)
print(f"✅ Built Episode 7 Storyboard: {len(clips)} clips ({n_rap} rap + {n_still} cinema B-roll/reactions), {len(edl)} EDL cuts, {tot_f} total frames ({tot_f/FPS:.1f}s)")
