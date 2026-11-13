# -*- coding: utf-8 -*-
"""Kratos vs Master Chief 分镜构建脚本（Realism V3 电影实拍 + 三场景时空交错 + 无麦克风纯武戏表演）：
  * Master Chief（A，左侧）：永不摘下 Mjolnir Mark VI 橄榄绿头盔与琥珀金反光护目镜，持 MA5 步枪 / 幽能光剑
  * Kratos（B，右侧）：灰白战纹光头、修剪清晰露唇的北欧络腮胡、皮甲护肩，持结霜利维坦之斧 / 炽热混沌双刃
  * 三幕场景递进：Round 1 Halo Installation 04 黄昏残骸 -> Beat Switch 1 冲入燃烧的奥林匹斯神庙雪夜废墟 -> Bridge 开启时空裂隙决战桥（左 Halo 右希腊废墟）
  * 注意：仅检查到当前工作流（不强制依赖未完成的文件），生成 work/clips.json, work/edl.json, work/fx.json, work/live.json

usage: python3 build_storyboard.py
"""
import json
import math
import os
import re

EP = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(EP, "work")
FPS = 24
PRE = 0.08          # 在首词前 0.08 秒起音频
STILL_FRAMES = 90   # 3.75s（17*5 + 5 = 90）
MAX_FRAMES = 226    # 单条口型镜头上限（F = 17k + 5，226f = 9.42s）

for sub in ("work", "refs", "clips"):
    os.makedirs(os.path.join(EP, sub), exist_ok=True)
for f in (
    "work/lines.json",
    "work/words_edit.json",
    "work/grid.json",
    "work/a_face_clean.png",
    "work/b_face_clean.png",
    "work/stage_halo.png",
    "work/stage_olympus.png",
    "work/stage_clash_a.png",
    "work/stage_clash_b.png",
    "refs/scene_halo.png",
    "refs/scene_olympus.png",
    "refs/scene_clash.png",
):
    assert os.path.exists(os.path.join(EP, f)), "missing " + f

json.dump(
    {
        "handheld_px": 10,
        "drift": 0.04,
        "margin": 0.06,
        "whip": True,
        "whip_secs": 0.06,
        "contrast": 1.03,
        "saturation": 1.0,
        "beat_pulse": 0.02,
        "grain": 4,
        "vignette": 0,
        "cool": False,
    },
    open(os.path.join(WORK, "live.json"), "w", encoding="utf-8"),
    indent=1,
)

e = json.load(open(os.path.join(EP, "episode.json"), encoding="utf-8"))
L = json.load(open(os.path.join(WORK, "lines.json"), encoding="utf-8"))
WORDS = json.load(open(os.path.join(WORK, "words_edit.json"), encoding="utf-8"))
grid = json.load(open(os.path.join(WORK, "grid.json"), encoding="utf-8"))
END_T = round(grid["length"], 3)
A, B = e["a"], e["b"]
ACT = json.load(open(os.path.join(EP, "line_actions.json"), encoding="utf-8"))


def fit(secs: float) -> int:
    """对齐 H3 采样网格 17k + 5（24fps），上限 226f。"""
    need = math.ceil((secs + 0.12) * FPS)
    k = max(2, math.ceil((need - 5) / 17))
    return min(MAX_FRAMES, 17 * k + 5)


def norm(w: str) -> str:
    return re.sub(r"[^a-z0-9']", "", w.lower().replace("’", "'"))


def is_sung(w: dict) -> bool:
    raw = w["w"].strip("!?,.\"'—")
    if w["w"].startswith("["):
        return False
    if raw.upper() in ("OOOH", "ROUND", "THREE", "FINAL", "CLASH", "SPARTAN", "OH", "YEAH", "UH", "YO"):
        return False
    return True


def cid_of(l: dict) -> str:
    return ("A" if l["who"] == "a" else "B") + f"{l['n']:02d}"


line_by = {cid_of(l): l for l in L}
order = [cid_of(l) for l in L]
nxt_start = {c: (L[i + 1]["start"] if i + 1 < len(L) else END_T) for i, c in enumerate(order)}


def last_word_end(c: str) -> float:
    l = line_by[c]
    cutoff = min(nxt_start[c] - 0.05, l["end"] + 0.15)
    ws = [w for w in WORDS if l["start"] - 0.1 <= w["t0"] < cutoff and is_sung(w)]
    return max((w["t1"] for w in ws), default=l["end"])


def word_t(c: str, word: str) -> float:
    l = line_by[c]
    hits = [w["t0"] for w in WORDS if l["start"] - 0.1 <= w["t0"] < nxt_start[c] - 0.05 and norm(w["w"]) == norm(word)]
    assert hits, f"{c}: word {word!r} not found"
    return round(hits[0], 3)


lw_end = {c: last_word_end(c) for c in order}


def action_for_lines(covered: list[str]) -> str:
    parts = [ACT[cid[0].lower()][int(cid[1:]) - 1] for cid in covered]
    if len(parts) == 1:
        return parts[0]
    return f"first {parts[0]}, then {parts[1]}"


# ---------------------------------------------------------------- 三大电影实景配置
SCENES = e["scenes"]
SCENE_CFG = {
    "halo": {
        "venue_en": SCENES["halo"]["venue_en"],
        "light_en": SCENES["halo"]["light_en"],
        "bg_desc_en": "the shattered Halo Installation 04 Forerunner ridge at bruised twilight with burning UNSC drop-pod wreckage and glowing Halo ring horizon",
        "bg_lights_en": "warm 3200K burning wreckage flames and cool 5600K Halo ring twilight glow",
        "bg_motion_en": "drifting dark smoke plumes, glowing orange embers, and faint purple plasma sparks across metallic Forerunner ground plates",
        "plate_a": "stage_halo",
        "plate_b": "stage_halo",
        "env_tail": "He stands outdoors on a shattered Halo Installation 04 Forerunner ridge at twilight beside smoldering UNSC wreckage fire, with the colossal glowing Halo ring curving behind in rich optical bokeh (no studio, no stage, no crowd).",
    },
    "olympus": {
        "venue_en": SCENES["olympus"]["venue_en"],
        "light_en": SCENES["olympus"]["light_en"],
        "bg_desc_en": "shattered ancient Greek Olympus marble temple ruins dusted with Midgard frost and volcanic ash, lit by roaring 2700K bronze fire braziers at night",
        "bg_lights_en": "warm 2700K roaring bronze fire braziers and cool 6500K icy moonlit mist",
        "bg_motion_en": "swirling glowing fire embers, flickering brazier flame light, and fine Midgard snow-ash drifting past broken marble columns",
        "plate_a": "stage_olympus",
        "plate_b": "stage_olympus",
        "env_tail": "He stands outdoors in shattered ancient Greek Olympus marble temple ruins at night beside roaring 2700K bronze fire braziers as volcanic ash and icy snow drift through smoky air (no studio, no stage, no crowd).",
    },
    "clash": {
        "venue_en": SCENES["clash"]["venue_en"],
        "light_en": SCENES["clash"]["light_en"],
        "bg_desc_en": "a fractured space-time rift bridge where Halo Forerunner metal monoliths and cyan Slipspace sparks collide directly with shattered Greek Doric marble columns and roaring 2700K fire braziers",
        "bg_lights_en": "warm 3200K bronze temple firelight and cool 5600K electric cyan Slipspace energy sparks",
        "bg_motion_en": "cracking blue-silver Slipspace energy arcs colliding with swirling volcanic embers and drifting temple ash under a storm-lit Halo ring sky",
        "plate_a": "stage_clash_a",
        "plate_b": "stage_clash_b",
        "env_tail": "They battle on a fractured space-time rift bridge uniting Halo Forerunner titanium monoliths on the left and burning Greek Olympus marble temple ruins on the right under a storm-lit Halo ring sky (no studio, no stage, no crowd).",
    },
}

SIDE = {"a": "screen-left", "b": "screen-right"}
FACING = {"a": "facing right", "b": "facing left"}
LR = {"a": ("left", "right"), "b": ("right", "left")}
HAND = ", shot on a handheld ARRI Alexa Mini LF 35mm cinema camera with subtle organic breathing motion"


def read_cue(who: str) -> str:
    if who == "a":
        return ", his battle-scarred olive-drab Mjolnir Mark VI helmet permanently worn and gleaming amber-gold visor sharp and expressive in every frame (helmet NEVER removed, NO bare human face, no microphone anywhere)"
    return ", his ash-pale weathered face, crimson war tattoo, dark beard, jaw, and lips large, unobstructed, and clearly readable in every frame (no microphone anywhere)"


def subj_read_cue(who: str) -> str:
    if who == "a":
        return ", <Subject 1>'s battle-scarred green helmet and gleaming gold visor clearly framed (helmet NEVER removed, no microphone anywhere)"
    return ", <Subject 1>'s face, beard, jaw, and lips large and clearly readable in every frame (no microphone anywhere)"


def cam_move(kind: str, who: str, sc_tag: str) -> str:
    me, them = LR[who]
    sc = SCENE_CFG[sc_tag]
    tail = " " + sc["env_tail"]
    rc = read_cue(who)
    src = subj_read_cue(who)
    if kind == "PUSH":
        return (
            "The camera starts on a waist-up medium shot of <Subject 1>, then pushes in with large amplitude at slow speed "
            "on a smooth 35mm cinema dolly until it settles on a tight chest-up close-up at Cooke Panchro 50mm T2.2 shallow depth of field"
            + rc + tail
        )
    if kind == "TQ":
        return (
            f"The camera holds a chest-up three-quarter medium close-up of <Subject 1> on the {me} half of the 16:9 frame, {FACING[who]}"
            + HAND + ", slowly arcing a few degrees around him at T2.2 shallow depth of field" + rc + tail
        )
    if kind == "LONG":
        return (
            "From the very first frame to the last, the camera holds a frontal chest-up hero close-up at eye level with Cooke Panchro 50mm T2.2"
            + HAND + ", never cutting to full body, pushing in with small amplitude at slow speed across the entire shot"
            + rc + tail
        )
    if kind == "ECU":
        return (
            "A handheld 28mm wide-angle cinema lens frames a tight heroic close-up slightly below eye level looking up at <Subject 1>: "
            "his upper chest, broad shoulders, and head/helmet dominate the 16:9 frame while warm fire embers flare behind him, "
            "pushing in with small amplitude at slow speed" + rc + tail
        )
    if kind == "ARC":
        return (
            f"The camera starts on a chest-up medium shot of <Subject 1> from the front, then trucks {me} and pans {them} with large amplitude at slow speed "
            f"in an arc around his {me} shoulder until it settles into an over-the-shoulder two-shot across the rift: "
            f"the blurred shoulder of <Subject 1> in the {me} foreground and <Subject 2> sharply focused on {SIDE['b' if who == 'a' else 'a']}"
            + tail
        )
    if kind == "REVEAL":
        return (
            f"The camera starts on a chest-up three-quarter close-up of <Subject 1> on the {me} half of the frame, {FACING[who]}, "
            f"then pans {them} with small amplitude at slow speed to reveal <Subject 2> standing across from him on the {them} edge of the frame"
            + src + tail
        )
    if kind == "FACE":
        return (
            f"The camera holds a tight eye-level profile two-shot across the rift bridge: <Subject 1> on {SIDE[who]} {FACING[who]} "
            f"confronting <Subject 2> on {SIDE['b' if who == 'a' else 'a']} {FACING['b' if who == 'a' else 'a']}, chest-up framing, "
            "and pushes in with small amplitude at slow speed until both warriors dominate the T2.2 cinema frame" + src + HAND + tail
        )
    if kind == "FACEWIDE":
        return (
            f"The camera holds a waist-up heroic profile two-shot across the fractured bridge: <Subject 1> on {SIDE[who]} {FACING[who]} "
            f"rapping hands-free at <Subject 2> on {SIDE['b' if who == 'a' else 'a']} {FACING['b' if who == 'a' else 'a']}, "
            "electric cyan rift arcs flashing in the center between them against roaring temple braziers" + src + HAND + tail
        )
    if kind == "CRASH":
        return (
            f"The camera starts on an over-the-shoulder medium shot with the blurred shoulder of <Subject 2> in the {them} foreground "
            f"and <Subject 1> chest-up on the {me}, then surges forward in a sudden crash push-in at fast speed past the foreground shoulder "
            "landing on a tight 28mm cinema close-up of <Subject 1> with palpable impact energy" + rc + tail
        )
    raise KeyError(kind)


TWO = {"ARC", "FACE", "FACEWIDE", "REVEAL", "CRASH"}
LISTEN = {
    "ARC": " while <Subject 2> stands rigid with hands free in tense silence",
    "FACE": " while <Subject 2> stares straight back across the rift in stone-cold silence",
    "FACEWIDE": " while <Subject 2> holds his combat stance across the fractured stone without flinching",
    "REVEAL": " while <Subject 2> watches calmly from across the battlefield",
    "CRASH": " while <Subject 2> looms motionless in the blurred foreground",
}

# 19 个精密口型表演镜头（涵盖三段递进 + 单行长句独立切片 + 对峙特写）
SHOTS = [
    # Round 1: Master Chief @ Halo Ring (6.50 -> 32.38)
    ("A01", "A02", "PUSH", "halo"),
    ("A03", "A04", "TQ", "halo"),
    ("A05", "A06", "LONG", "halo"),
    ("A07", "A08", "ECU", "halo"),
    # Round 2: Kratos @ Olympus & Midgard Ruins (34.43 -> 60.11)
    ("B01", "B02", "PUSH", "olympus"),
    ("B03", "B04", "TQ", "olympus"),
    ("B05", "B06", "LONG", "olympus"),
    ("B07", "B08", "ECU", "olympus"),
    # Round 3: Space-Time Rift Clash (74.79 -> 130.95)
    ("A09", "A10", "REVEAL", "clash"),
    ("A11", "A12", "FACEWIDE", "clash"),
    ("B09", "B10", "FACE", "clash"),
    ("B11", "B12", "CRASH", "clash"),
    ("A13", "A13", "LONG", "clash"),     # 6.61s 单句独奏（No backup left...）
    ("A14", "A14", "ECU", "clash"),      # 5.78s 单句独奏（Protector of humanity...）
    ("B13", "B14", "FACE", "clash"),
    ("A15", "A16", "FACEWIDE", "clash"),
    ("B15", "B16", "CRASH", "clash"),
]

clips = []
lip = {}
for c0, c1, kind, sc_tag in SHOTS:
    who = line_by[c0]["who"]
    n0, n1 = int(c0[1:]), int(c1[1:])
    covered = [f"{who.upper()}{n:02d}" for n in range(n0, n1 + 1)]
    assert line_by[c1]["who"] == who

    me_k, them_k = ("a_face_clean", "b_face_clean") if who == "a" else ("b_face_clean", "a_face_clean")
    sc = SCENE_CFG[sc_tag]
    plate = sc["plate_a"] if who == "a" else sc["plate_b"]
    look_me = A["look"] if who == "a" else B["look"]
    look_them = B["look"] if who == "a" else A["look"]

    a0 = round(line_by[c0]["start"] - PRE, 3)
    a1 = round(max(line_by[c1]["end"], lw_end[c1]), 3)
    text = " / ".join(line_by[x]["text"] for x in covered)
    frames = fit(a1 - a0)
    two = kind in TWO

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
    if who == "a" and not two:
        clip["closeup_lora"] = 0.0
    elif kind in ("PUSH", "ARC", "CRASH", "FACE", "FACEWIDE"):
        clip["closeup_lora"] = 0.22 if two else 0.42
    elif who == "b" and not two:
        clip["closeup_lora"] = 0.42
    clips.append(clip)
    lip[c0] = (a0, lw_end[c1], covered)

# ---------------------------------------------------------------- 过场、武器特写、反应镜头 (Non-lip-sync Cinema Shots)
IMG = {
    "a_face_clean": "Spartan-II Master Chief John-117 in his battle-scarred matte olive-drab green Mjolnir Mark VI powered armor and reflective metallic amber-gold visor (helmet NEVER removed, NO bare human face, subtle white '117' chest stencil)",
    "b_face_clean": "Norse-era Kratos in his fifties, towering heavily muscled bald Spartan demigod with matte ash-pale skin pores and scars, crimson Spartan war tattoo over left eye and chest, bushy dark-brown-and-silver beard clear of lips, and dark leather Norse shoulder strap",
    "scene_halo": "the shattered Halo Installation 04 Forerunner alloy battlefield ridge at twilight with smoldering UNSC drop-pod wreckage fire on the left and the colossal illuminated Halo ring curving overhead",
    "scene_olympus": "shattered ancient Greek Olympus marble temple ruins blanketed with swirling Midgard snow-ash and twin roaring 2700K bronze fire braziers at night",
    "scene_clash": "the fractured space-time rift battle bridge uniting Forerunner titanium monoliths and cyan Slipspace sparks on the left with ruined Greek Doric columns and roaring temple fire braziers on the right beneath the Halo ring sky",
    "stage_halo": "the out-of-focus Installation 04 Forerunner battlefield fire glow and colossal Halo ring twilight horizon behind Master Chief",
    "stage_olympus": "the out-of-focus roaring 2700K Olympus bronze brazier flames and drifting snowy temple ruins behind Kratos",
    "stage_clash_a": "the out-of-focus electric cyan Slipspace energy sparks and Forerunner monoliths on the Halo side of the space-time rift behind Master Chief",
    "stage_clash_b": "the out-of-focus roaring bronze temple braziers and shattered Greek marble columns on the Olympus side of the space-time rift behind Kratos",
}

NO_TEXT_NOMIC = (
    "Keep every character's exact armor, helmet/facial bone structure, skin pores, scars, and markings 100% faithful to the reference images. "
    "Master Chief NEVER removes his helmet. "
    "Authentic live-action 35mm epic sci-fi and mythological cinema shot on ARRI Alexa Mini LF with Cooke Panchro T2.2 prime lens on Kodak Vision3 500T film (zero plastic CGI sheen). "
    "Nobody holds a microphone anywhere in the frame. No subtitles, no HUD overlay, no on-screen text, no logos, no watermark."
)


def still(sid: str, keys: list[str], shot_desc: str, frames: int = STILL_FRAMES, lora: float | None = None):
    head = " ".join(f"Image {i} is {IMG[k]}." for i, k in enumerate(keys, 1))
    c = {
        "id": sid,
        "kind": "still",
        "move": "V2",
        "frames": frames,
        "image_keys": keys,
        "prompt": "\n\n".join([head, "Cinematic live-action 35mm epic cinema shot, 16:9. " + shot_desc, NO_TEXT_NOMIC]),
    }
    if lora is not None:
        c["closeup_lora"] = lora
    clips.append(c)


# Intro & Establish
still(
    "HALO_OPEN",
    ["scene_halo"],
    "Wide establishing cinema crane shot gliding smoothly forward across the shattered Halo Installation 04 Forerunner battlefield ridge at bruised twilight (Image 1): "
    "smoldering UNSC drop-pod flames flicker warmly on the left across scarred hexagonal alloy floor plates while faint purple Covenant plasma embers and the colossal illuminated Halo ring rise into a deep starry twilight sky.",
    frames=107,
    lora=0.0,
)
still(
    "CHIEF_ARMOR_INIT",
    ["a_face_clean", "stage_halo"],
    "Chest-up 35mm hero close-up of Master Chief John-117 (Image 1) standing firm on the Halo ridge with blurred twilight wreckage fire and Halo horizon behind him (Image 2): "
    "electric cyan-blue Mjolnir energy shield shimmer ripples softly upward across his scarred olive-drab chestplate and shoulders as warm 3200K flames reflect sharply in his amber-gold helmet visor; "
    "the camera pushes slowly inward as he locks his stance before firing the opening bar.",
    frames=107,
    lora=0.25,
)

# Round 1 & 2 Cutaway Reactions & Weapon Close-Ups
still(
    "B_R_BOY",
    ["b_face_clean", "stage_olympus"],
    "Tight frontal head-and-shoulders close-up of Kratos (Image 1) standing alone in burning Olympus marble ruins dusted with falling snow-ash at T2.2 shallow depth of field (Image 2): "
    "mouth firmly closed, weathered brow crushing downward over cold glowing eyes, neck veins straining beneath warm 3200K bronze brazier firelight and crisp icy moonlight rim as he listens in simmering Spartan fury.",
    frames=90,
)
still(
    "A_R_BUCKET",
    ["a_face_clean", "stage_halo"],
    "Tight chest-up close-up of Master Chief (Image 1) on the twilight Halo ridge with blurred purple plasma embers and wreckage glow behind him (Image 2): "
    "mouth/face permanently concealed behind his scarred olive-drab Mark VI helmet, he tilts his helmet two degrees in cold unbothered assessment as warm amber firelight glints across his reflective gold visor and subtle blue shield sparks crackle on his shoulder pauldron.",
    frames=90,
)
still(
    "AXE_FROST_CU",
    ["b_face_clean", "stage_olympus"],
    "Dramatic low-angle waist-up cinema weapon hero shot of Kratos (Image 1) in the snowy Olympus temple ruins (Image 2): "
    "mouth firmly closed, gripping the massive wooden haft of the frost-encrusted Leviathan Axe diagonally in front of his scarred torso as glowing cyan Norse runes flare bright along the heavy steel axe head and crystalline frost mist cascades off the blade amidst drifting warm brazier embers.",
    frames=90,
    lora=0.20,
)

# Beat Switch 1 (Halo -> Burning Olympus Ruins)
still(
    "OLYMPUS_CRASH_IN",
    ["scene_olympus"],
    "Dynamic fast cinema push-in sweeping through swirling icy snow, embers, and smoky night air into the shattered ancient Greek Olympus marble temple courtyard (Image 1): "
    "broken Corinthian stone columns and roaring 2700K twin bronze fire braziers burst toward the lens in dramatic chiaroscuro contrast.",
    frames=90,
    lora=0.0,
)
still(
    "KRATOS_ERUPT",
    ["b_face_clean", "stage_olympus"],
    "Handheld 35mm medium close-up of Kratos (Image 1) striding forward out of roaring bronze brazier smoke and falling ash in the shattered Olympus ruins (Image 2): "
    "mouth firmly closed in a menacing pre-bar scowl, jaw clenched hard inside his dark beard, warm 3200K firelight sculpting weathered skin pores and crimson war-paint as cold snow mist swirls past his bare scarred shoulder.",
    frames=90,
    lora=0.28,
)

# Round 3 Bridge: Space-Time Rift Opening + Hero Weapon Dual Charge + Rift Faceoff
still(
    "RIFT_BRIDGE_OPEN",
    ["scene_clash"],
    "Sweeping wide 35mm epic crane shot gliding forward across the fractured space-time rift bridge (Image 1): "
    "on the left half, scarred Forerunner alloy monoliths crackle with bright electric cyan Slipspace energy arcs and UNSC steel crates; "
    "on the right half, broken Greek Doric marble columns and roaring bronze fire braziers blast hot embers through swirling volcanic ash beneath the colossal Halo ring bisecting storm-lit night clouds.",
    frames=124,
    lora=0.0,
)
still(
    "CHIEF_SWORD_CHARGE",
    ["a_face_clean", "stage_clash_a"],
    "Heroic waist-up weapon-focus medium close-up of Master Chief (Image 1) standing on the Forerunner metal side of the space-time rift with cyan Slipspace bokeh behind him (Image 2): "
    "cradling his matte-black UNSC MA5 assault rifle in one armored hand while igniting a blazing glowing cyan-white Covenant Energy Sword in his other heavy gauntlet, blue Mjolnir shield energy crackling violently over his scarred olive-drab armor.",
    frames=124,
    lora=0.22,
)
still(
    "KRATOS_CHAOS_ERUPT",
    ["b_face_clean", "stage_clash_b"],
    "Heroic waist-up weapon-focus medium close-up of Kratos (Image 1) on the burning Olympus ruin side of the space-time rift with roaring fire-brazier bokeh behind him (Image 2): "
    "mouth firmly closed with fierce glaring eyes, heavy iron chains coiled tightly around his scarred forearms as twin Blades of Chaos blaze bright orange-gold with molten volcanic embers in his fists, frost mist swirling at his shoulders.",
    frames=124,
    lora=0.22,
)
still(
    "RIFT_FACEOFF",
    ["a_face_clean", "b_face_clean"],
    "Monumental waist-up profile standoff two-shot on the fractured space-time rift bridge at night: "
    "Master Chief (Image 1) on screen-left in scarred green Mjolnir armor facing right with blue shield static shimmering across his shoulders, confronting "
    "Kratos (Image 2) on screen-right in ash-pale skin and crimson tattoo facing left with frost-rimed shoulders and mouth firmly closed in stone-cold rage; "
    "electric cyan Slipspace lightning on the left collides with warm 3200K temple brazier embers on the right while the handheld 35mm cinema camera slowly pushes in between them.",
    frames=124,
    lora=0.20,
)

# Round 3 Reactions & Finale Aftermath
still(
    "B_R_ASHES",
    ["b_face_clean", "stage_clash_b"],
    "Tight chest-up close-up of Kratos (Image 1) on the Olympus side of the rift bridge at T2.2 shallow depth of field (Image 2): "
    "mouth firmly closed, eyes darkening with stung haunted grief and boiling rage as bright orange brazier sparks drift across his ash-pale crimson-striped chest.",
    frames=107,
)
still(
    "A_R_UNSC",
    ["a_face_clean", "stage_clash_a"],
    "Tight chest-up close-up of Master Chief (Image 1) on the Halo side of the rift bridge at T2.2 shallow depth of field (Image 2): "
    "standing immovable like a fortress of titanium, cyan Slipspace arcs glowing across his olive-drab pauldrons and reflecting cold blue against warm fire highlights on his amber visor.",
    frames=107,
)
still(
    "RIFT_END_AFTERMATH",
    ["a_face_clean", "b_face_clean"],
    "The shot begins on a tense waist-up profile two-shot across the fractured space-time rift bridge — Master Chief (Image 1) on screen-left facing right with his amber visor glowing amidst blue shield sparks, "
    "and Kratos (Image 2) on screen-right facing left with mouth closed and burning embers swirling around his scarred shoulders. "
    "Then the 35mm cinema crane pulls steadily backward and upward through drifting ash and sparks, revealing both unyielding Spartans framed between Forerunner steel and burning Greek marble pillars under the towering Halo ring sky.",
    frames=158,
    lora=0.0,
)

ids = {c["id"]: c for c in clips}

# ---------------------------------------------------------------- Edit Decision List (EDL)
# 词级 L-cut 反切（保证唱者至少露脸 >= 0.85s 再切给对方或武器特写，再接回本条口型镜头）
CUTAWAYS = [
    ("A03", "A03", "BOY", 1.20, "B_R_BOY", 0.20),
    ("B01", "B02", "bucket", 1.15, "A_R_BUCKET", 0.20),
    ("B05", "B06", "Leviathan", 1.15, "AXE_FROST_CU", 1.65),
    ("A09", "A10", "Ashes", 1.15, "B_R_ASHES", 2.10),
    ("B09", "B10", "owned", 1.15, "A_R_UNSC", 2.00),
]

GAPS = {
    # 1.95s Beat Switch 1 (32.40 -> 34.35): 从 Halo 切入奥林匹斯雪夜神庙 -> Kratos 杀出！
    "A07": [
        ("OLYMPUS_CRASH_IN", 1.60),
        ("KRATOS_ERUPT", 1.50),
    ],
    # 14.58s Bridge (60.13 -> 74.71): ROUND THREE! FINAL CLASH! 时空裂隙降临 + 双雄亮兵器对峙！
    "B07": [
        ("RIFT_BRIDGE_OPEN", 0.15),
        ("CHIEF_SWORD_CHARGE", 1.10),
        ("KRATOS_CHAOS_ERUPT", 0.35),
        ("RIFT_FACEOFF", 0.15),
    ],
}

first = lip["A01"][0]  # 6.42s
spans = [
    (0.000, round(first * 0.52, 3), "HALO_OPEN", 0.15),
    (round(first * 0.52, 3), first, "CHIEF_ARMOR_INIT", 0.15),
]

lip_ids = [s[0] for s in SHOTS]
cut_by = {}
for head, line, word, d, sid, inn in CUTAWAYS:
    cut_by.setdefault(head, []).append((word_t(line, word), d, sid, inn))

MIN_ON = 0.80
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
        assert te <= t1 + 1e-6, f"{c}: cutaway end {te} > t1 {t1}"
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
            spans.append((s_a, s_b, sid, inn))

# Outro (130.97 -> 142.947 = 11.98s): SPARTAN! SPARTAN! 史诗终结收尾
o0 = spans[-1][1]
out_len = END_T - o0
spans.extend(
    [
        (o0, round(o0 + out_len * 0.30, 3), "CHIEF_SWORD_CHARGE", 0.35),
        (round(o0 + out_len * 0.30, 3), round(o0 + out_len * 0.60, 3), "KRATOS_CHAOS_ERUPT", 0.35),
        (round(o0 + out_len * 0.60, 3), END_T, "RIFT_END_AFTERMATH", 0.15),
    ]
)

edl = [{"t0": a, "t1": b, "clip": c, "in": i} for a, b, c, i in spans]

used = {x["clip"] for x in edl}
clips = [c for c in clips if c["id"] in used]
ids = {c["id"]: c for c in clips}

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

# Post FX (Beat-switch flashes, shield/axe impact shakes, climax punch zoom)
fx = [
    {"type": "flash", "t0": round(grid["beat0"], 3), "t1": round(grid["beat0"] + 0.08, 3), "alpha": 0.55},
    # Beat Switch 1: Shield shatter -> Olympus drop -> Kratos erupt
    {"type": "flash", "t0": 32.39, "t1": 32.48, "alpha": 0.80},
    {"type": "flash", "t0": 34.42, "t1": 34.51, "alpha": 0.85},
    {"type": "shake", "t0": 34.43, "t1": 34.95, "px": 9},
    # Round 3 Bridge & Rift Arrival
    {"type": "flash", "t0": 60.12, "t1": 60.21, "alpha": 0.80},
    {"type": "flash", "t0": 74.78, "t1": 74.87, "alpha": 0.85},
    {"type": "shake", "t0": 74.79, "t1": 75.35, "px": 9},
    # Climax Knockout Push
    {"type": "flash", "t0": 124.67, "t1": 124.76, "alpha": 0.85},
    {"type": "punch", "t0": word_t("B16", "God"), "t1": 131.05, "amount": 0.08},
]

json.dump(clips, open(os.path.join(WORK, "clips.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(edl, open(os.path.join(WORK, "edl.json"), "w", encoding="utf-8"), indent=1)
json.dump(fx, open(os.path.join(WORK, "fx.json"), "w", encoding="utf-8"), indent=1)

n_rap = sum(1 for c in clips if c["kind"] == "rap")
n_still = sum(1 for c in clips if c["kind"] != "rap")
tot_f = sum(c["frames"] for c in clips)
print(
    f"✅ Built Kratos vs Master Chief Storyboard: {len(clips)} clips ({n_rap} rap + {n_still} cinema B-roll/weapons/reactions), "
    f"{len(edl)} EDL cuts, {tot_f} total frames ({tot_f/FPS:.1f}s)"
)
