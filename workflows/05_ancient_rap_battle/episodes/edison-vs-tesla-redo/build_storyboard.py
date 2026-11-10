# -*- coding: utf-8 -*-
"""Edison vs Tesla 重做版分镜：歌曲和时间轴沿用 edison-vs-tesla-full，拍法沿用 edison-vs-tesla-remake，
人物、场景、观众、DJ 的设定图全部重做（2026-11-10：重制版画面偏暗偏灰，原因是场景图里观众是剪影、
人物图只有脸没有服装、后期调色压了两遍）。本集的设定图在 refs/ 和 work/，提示词在 ref_prompts/。

拍法来自 2026-11-10 的运镜小样（caocao-vs-liubei/samples_cam）：
  * 手持麦，手里不拿道具（PROPS = True 可以改回灯泡 / 线圈）
  * 一个口型镜头可以跨 1～2 句、带真实运镜（前推、穿过人群、绕到身后、横摇带出对手、急推）
  * 句中切到对手 / 观众的反应镜头，声音不断，切回来还是同一条口型镜头
  * 四段越往后切得越快、贴得越近（前两段进场 + 长镜头，后两段以贴脸对峙为主）
  * 站位固定：Edison 在左、Tesla 在右（和两半场景图一致）

usage: python3 build_storyboard.py            # 复制素材 + 写 work/clips.json、edl.json、fx.json
"""
import json
import math
import os
import re
import shutil

EP = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.dirname(EP), "edison-vs-tesla-full")
WORK = os.path.join(EP, "work")
PROPS = False
FPS = 24
PRE = 0.08          # 在第一个词前 0.08 秒起音频
STILL_FRAMES = 73   # 非口型镜头 3.04 秒
MAX_FRAMES = 209    # 单条口型镜头上限（小样 T11 验证过 209 帧）

# ---------------------------------------------------------------- 素材
for sub in ("work", "refs", "clips"):
    os.makedirs(os.path.join(EP, sub), exist_ok=True)
for f in ("lines.json", "words_edit.json", "grid.json", "vocals_final.wav", "music_final.wav"):
    if not os.path.exists(os.path.join(WORK, f)):
        shutil.copy2(os.path.join(SRC, "work", f), os.path.join(WORK, f))
for f in ("work/a_face_clean.png", "work/b_face_clean.png", "work/stage_a.png", "work/stage_b.png",
          "refs/crowd.png", "refs/dj.png", "refs/venue.png"):   # 本集自己的设定图，不从旧剧集复制
    assert os.path.exists(os.path.join(EP, f)), "missing " + f
# 调色只做一遍、力度减轻：合成时不加暗角、不偏冷、少颗粒；打包时不再做第二遍
json.dump({"handheld_px": 10, "drift": 0.04, "margin": 0.06, "whip": True, "whip_secs": 0.12, "contrast": 1.03,
           "saturation": 1.0, "beat_pulse": 0.02, "grain": 4, "vignette": 0, "cool": False},
          open(os.path.join(WORK, "live.json"), "w", encoding="utf-8"), indent=1)
for f in ("song.mp3",):
    if not os.path.exists(os.path.join(EP, f)):
        shutil.copy2(os.path.join(SRC, f), os.path.join(EP, f))

e = json.load(open(os.path.join(SRC, "episode.json"), encoding="utf-8"))
e["title"] = "Edison_vs_Tesla_Redo"
e["grade"] = "cas=0.25"   # 打包时只做轻微锐化，不再二次调色
e["mic_en"] = "vintage chrome handheld microphone with a round mesh head"
e["venue_en"] = ("the huge dynamo hall of an 1890s New York red-brick electric power station turned into an underground rap "
                 "battle arena at night, riveted iron columns and girders, giant brass flywheels and dynamos, steam and "
                 "tall arched windows; on the left side a dense canopy of hundreds of warm amber carbon-filament light "
                 "bulbs, on the right side two tall brass Tesla coils throwing blue-violet electric arcs, a raised DJ "
                 "booth built on a brass dynamo in the center background, and a raised round iron stage in the middle; the two rappers always "
                 "stand on top of this stage, above the crowd, who stand on the hall floor below and look up at them")
e["light_en"] = ("rich warm cinematic lighting, well-exposed faces: golden light from hundreds of amber bulbs as the key "
                 "light, a vivid blue-violet rim light from the Tesla coils, one cold white spotlight beam from above "
                 "cutting through soft haze, glowing highlights, the crowd behind clearly lit by the warm lamps")
e["arena_sound_en"] = "a packed brick dynamo hall full of roaring workers"
e["a"]["look"] = ("stocky man of about 45 with thick dishevelled grey-brown hair, clean-shaven, rumpled charcoal three-piece "
                  "wool suit worn open, dark waistcoat with a gold pocket-watch chain, white shirt with a stand-up collar "
                  "and a loose black bow tie, holding nothing")
e["b"]["look"] = ("tall, very slim man of about 34 with centre-parted jet-black hair and a neat dark moustache, immaculate "
                  "black Victorian frock coat with satin lapels, high stiff white wing collar, dark patterned silk cravat "
                  "with a small pearl pin, white pocket square, holding nothing")
e["crowd_motion_en"] = ("the packed crowd moves with the music the whole time, heads nodding and fists pumping on every "
                        "beat, bodies bouncing and swaying, some workers jumping and waving their flat caps")
if not PROPS:
    for w in "ab":
        e[w]["look"] = e[w]["look"].split(", holding ")[0]
    e["a"]["prop"], e["b"]["prop"] = "gold pocket-watch chain", "high white wing collar"
json.dump(e, open(os.path.join(EP, "episode.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)

L = json.load(open(os.path.join(WORK, "lines.json"), encoding="utf-8"))
WORDS = json.load(open(os.path.join(WORK, "words_edit.json"), encoding="utf-8"))
grid = json.load(open(os.path.join(WORK, "grid.json"), encoding="utf-8"))
END_T = round(grid["length"], 3)
A, B = e["a"], e["b"]
CROWD = e["crowd_motion_en"]
MIC = e["mic_en"]


# ---------------------------------------------------------------- 词级时间
def norm(w):
    return re.sub(r"[^a-z0-9']", "", w.lower().replace("’", "'"))


def is_sung(w):
    return not w["w"].startswith("[") and not w["w"].strip("!?,.").isupper()


cid_of = lambda l: ("A" if l["who"] == "a" else "B") + "%02d" % l["n"]
line_by = {cid_of(l): l for l in L}
order = [cid_of(l) for l in L]
nxt_start = {c: (L[i + 1]["start"] if i + 1 < len(L) else END_T) for i, c in enumerate(order)}


def last_word_end(c):
    l = line_by[c]
    ws = [w for w in WORDS if l["start"] - 0.1 <= w["t0"] < nxt_start[c] - 0.05 and is_sung(w)]
    return max(w["t1"] for w in ws)


def word_t(c, word):
    l = line_by[c]
    hits = [w["t0"] for w in WORDS if l["start"] - 0.1 <= w["t0"] < nxt_start[c] - 0.05 and norm(w["w"]) == norm(word)]
    assert hits, "%s: word '%s' not found" % (c, word)
    return round(hits[0], 3)


lw_end = {c: last_word_end(c) for c in order}

# ---------------------------------------------------------------- 机位（官方运镜词表：动作 + 幅度 + 速度）
SIDE = {"a": "screen-left", "b": "screen-right"}
FACING = {"a": "facing right", "b": "facing left"}
LR = {"a": ("left", "right"), "b": ("right", "left")}   # (自己那侧, 对手那侧)
READ = ", his face and lips large and clearly readable whenever he faces the camera"
HAND = ", shot on a handheld camera with a subtle natural sway"


def cam(kind, who):
    me, them = LR[who]
    if kind == "ENTER":   # 原片 A1→A2：观众背后穿过人群推到台上（小样 T02）
        return ("The camera starts behind the audience at head height: the backs of heads, flat caps and raised fists of "
                "the packed crowd fill the lower half of the frame with the spotlit stage small in the distance, then the "
                "camera pushes in with large amplitude at slow speed, gliding forward between the raised arms and over the "
                "shoulders of the crowd until it reaches the edge of the stage and settles on a chest-up medium shot of "
                "<Subject 1>; " + CROWD)
    if kind == "PUSH":    # 中景推到近景（小样 T01）
        return ("The camera starts on a knee-up medium shot of <Subject 1> in the cold spotlight beam, then the camera "
                "pushes in with large amplitude at slow speed, travelling steadily toward him until it settles on a "
                "head-and-shoulders close-up" + READ)
    if kind == "ARC":     # 绕到唱者身后变成过肩拍听者（小样 T03）
        return ("The camera starts on a chest-up medium shot of <Subject 1> from the front as he raps, then the camera "
                "trucks %s and pans %s with large amplitude at slow speed, moving in an arc shot around his %s shoulder, "
                "until it ends as an over-the-shoulder shot from behind him: the back of <Subject 1>'s head and his %s "
                "shoulder softly blurred in the %s foreground, and <Subject 2> in sharp focus a few steps away on %s, "
                "facing the camera" % (me, them, me, me, me, SIDE["b" if who == "a" else "a"]))
    if kind == "FACE":    # 鼻尖相对的侧面双人，慢推（小样 T04）
        return ("The camera holds a tight eye-level profile two-shot of the two men standing face to face, almost nose to "
                "nose, a foot apart: <Subject 1> on %s in profile %s, leaning in and rapping straight into <Subject 2>'s "
                "face, <Subject 2> on %s in profile %s; both from the chest up, and the camera pushes in with small "
                "amplitude at slow speed until their two faces fill the frame, <Subject 1>'s lips and jaw clearly readable "
                "in profile in every frame" % (SIDE[who], FACING[who], SIDE["b" if who == "a" else "a"],
                                               FACING["b" if who == "a" else "a"]) + HAND)
    if kind == "FACEWIDE":  # 拉宽的双人：半身，顶光在两人之间
        return ("The camera holds a waist-up medium profile two-shot at eye level: <Subject 1> on %s %s, leaning toward "
                "<Subject 2> and rapping at him, <Subject 2> on %s %s standing his ground, the cold spotlight beam falling "
                "between the two men, <Subject 1>'s lips and jaw clearly readable in every frame"
                % (SIDE[who], FACING[who], SIDE["b" if who == "a" else "a"], FACING["b" if who == "a" else "a"]) + HAND)
    if kind == "REVEAL":  # 从单人横摇带出对手（小样 T05）
        return ("The camera starts on a chest-up three-quarter medium close-up of <Subject 1> alone on the %s half of the "
                "frame, %s as he raps, then the camera pans %s with small amplitude at slow speed, revealing <Subject 2> "
                "standing in profile at the %s edge of the frame, and settles into a profile two-shot of the two men face "
                "to face, <Subject 1>'s lips and jaw clearly readable in every frame" % (me, FACING[who], them, them))
    if kind == "ECU":     # 仰拍广角大特写（小样 T06：开头约 1 秒会是中景，再推进去）
        return ("A handheld camera with a wide-angle lens is very close to his face and slightly below chin height, looking "
                "up at him: an extreme close-up where his face fills most of the 16:9 frame, the head of the microphone "
                "large and soft in the bottom foreground just below his chin; the camera pushes in with small amplitude at "
                "slow speed, the spotlight haze flaring behind his head, his lips large and clearly readable in every frame")
    if kind == "CRASH":   # 从过肩中景急推到大特写（小样 T07）
        return ("The camera starts on an over-the-shoulder medium shot: the blurred shoulder and back of the head of "
                "<Subject 2> in the %s foreground, <Subject 1> chest-up on the %s facing the camera, then the camera pushes "
                "in with large amplitude at fast speed past the shoulder, a sudden crash push-in that lands on a tight "
                "close-up where his whole face from hairline to chin fills the frame, never closer than that, and shakes "
                "slightly as it lands, his lips large and clearly readable"
                % (them, me))
    if kind == "LONG":    # 正面近景长镜头，慢推（小样 T09）
        return ("From the very first frame to the last, the camera holds a frontal head-and-shoulders close-up at eye "
                "level" + HAND + ", never a full-body or wide shot, his legs and the stage floor never in frame, and "
                "pushes in with small amplitude at slow speed across the whole shot; his face fills the upper two thirds "
                "of the 16:9 frame, his lips large and clearly readable in every frame")
    if kind == "TQ":      # 四分之三侧中景，手往对手那边指
        return ("The camera holds a chest-up three-quarter medium shot of <Subject 1> on the %s half of the frame, %s"
                % (me, FACING[who]) + HAND + ", slowly arcing a few degrees around him, his face and lips large and "
                "clearly readable in every frame")
    raise KeyError(kind)


ONSTAGE = (". He stands on top of the raised round stage: the crowd is on the hall floor below and behind him, lower "
           "than his chest, and nobody stands at his own level except his opponent")
NOSTAGE = ("From the very first frame to the last this is a close shot of the audience only: the camera stands with its back to the stage, so the stage and the two rappers are never in frame. ")
TWO = {"ARC", "FACE", "FACEWIDE", "REVEAL", "CRASH"}
LISTEN = {
    "ARC": " while <Subject 2> stands with his mouth firmly closed, hands clasped in front of him, watching him in silence",
    "FACE": " while <Subject 2> keeps his mouth firmly closed and stares back at him without blinking",
    "FACEWIDE": " while <Subject 2> stands with his arms crossed and his mouth firmly closed",
    "REVEAL": " while <Subject 2> listens with his mouth firmly closed, a faint cold smile",
    "CRASH": " while <Subject 2> stands with his back to the camera in the foreground, motionless",
}

# 每条口型镜头：(首句, 末句, 机位, 另一只手的动作)。麦在右手，动作只用左手。
SHOTS = [
    # ---- 第一段 Edison：进场 + 长镜头，节奏最慢
    ("A01", "A02", "ENTER", "sweeping his free left hand across the room like a landlord showing his property"),
    ("A03", "A04", "PUSH", "counting off on the fingers of his free left hand, then jabbing a finger straight into the lens"),
    ("A05", "A06", "ARC", "flicking his free left hand toward his opponent as if tossing him a coin"),
    ("A07", "A07", "ECU", "smirking down into the lens, wagging one finger of his free left hand"),
    ("A08", "A08", "FACE", "leaning into his opponent's face with a slow winner's grin"),
    # ---- 第二段 Tesla：同样的进场，中段加快
    ("B01", "B02", "ENTER", "raising his free left hand high, then letting it drop in mock applause"),
    ("B03", "B04", "LONG", "his free left hand sweeping wide across the frame, then pointing up beside his head"),
    ("B05", "B06", "WHIP", None),
    ("B07", "B07", "CRASH", "pinching his thumb and finger together as if holding a needle, eyes wide"),
    ("B08", "B08", "FACE", "tapping his own temple with his free left hand, then holding up one finger between their faces"),
    # ---- 第三段 Edison：切得更快，开始贴脸
    ("A09", "A09", "ECU", "rubbing his thumb and fingers together like counting money, sneering"),
    ("A10", "A10", "REVEAL", "holding up three fingers, then two, then seven, stepping in close"),
    ("A11", "A12", "FACE", "snapping the fingers of his free left hand right beside his opponent's ear"),
    ("A13", "A13", "TQ", "tapping his own chest with his free left hand, then flicking the hand away"),
    ("A14", "A14", "CRASH", "wiping imaginary sweat off his brow with the back of his free left hand, glaring"),
    ("A15", "A15", "FACEWIDE", "walking two fingers of his free left hand in a little circle in the air, mocking"),
    ("A16", "A16", "LONG", "counting napkins in the air with his free left hand, one, two, three, then shrugging"),
    # ---- 第四段 Tesla：最快，几乎全在贴脸对峙里
    ("B09", "B09", "TQ", "slicing his free left hand through the air like striking out a name"),
    ("B10", "B10", "FACE", "pointing his free left index finger at his opponent's chest"),
    ("B11", "B12", "LONG", "spreading his free left arm wide like a waterfall pouring down, then snapping his fingers"),
    ("B13", "B13", "ECU", "bringing down his free left hand like a judge's gavel, cold smile"),
    ("B14", "B14", "FACE", "pointing a finger at the ground, then circling it slowly around the whole room"),
    ("B15", "B15", "FACEWIDE", "holding up one finger of his free left hand, then pointing up at the ceiling"),
    ("B16", "B16", "CRASH", "pointing straight into the lens, then turning the hand into a dismissive wave"),
]


def fit(dur):
    need = math.ceil((dur + 0.35) * FPS)
    k = max(4, math.ceil((need - 5) / 17))
    f = 17 * k + 5
    assert f <= MAX_FRAMES, "clip of %.2fs needs %d frames" % (dur, f)
    return f


def ts(t):
    return "00:0%05.3f" % t


def whip_prompt(who, a0, a1, text, frames, L=0.0):
    """原片 B5→B6（小样 T10）：一条里两个镜头，甩镜落到对手脸上，后半段唱的人不在画面里。"""
    me, them = (A, B) if who == "a" else (B, A)
    my, their = LR[who]
    total, v_end = frames / FPS, min(frames / FPS - 0.05, L + a1 - a0)
    cut = round(L + word_t("B06", "called") - a0, 2)   # 甩镜放在第二句开头（L = 开头无声预备段）
    return (
        "subject_definitions:\n"
        "<Subject 1> is %s (%s) from <Picture 1>, natural matte skin texture with fine pores.\n"
        "<Subject 2> is %s (%s) from <Picture 2>, natural matte skin texture.\n"
        "<Picture 3> is the hall directly behind <Subject 1> in [Shot 1], seen from the stage: the Tesla coils, the "
        "violet-lit arched windows and the crowd below.\n"
        "<Audio 1> is the target rap vocal track for <Subject 1>, providing his exact vocal timbre (%s) and "
        "syllable-by-syllable rhythm during %s–%s, followed by silence.\n\n"
        "summary:\n[reference generation + audio reuse] Inside %s, <Subject 1> performs an energetic English battle-rap "
        "couplet synced syllable-by-syllable to <Audio 1>, holding the %s in his right hand below his chin, across 2 "
        "shots, with <Subject 2> listening in silence, while %s.\n\n"
        "retention_analysis:\n"
        "<Subject 1> (appears in [Shot 1]): fully_preserved - Strictly preserve exact facial bone structure, hairstyle, "
        "facial hair and outfit from <Picture 1>.\n"
        "<Subject 2> (appears in [Shot 2]): fully_preserved - Strictly preserve exact facial structure, hairstyle and outfit "
        "from <Picture 2>, keeping his mouth closed in silent listening throughout this clip.\n"
        "Background (appears in [Shot 1]): fully_preserved - Keep the environment of <Picture 3> behind <Subject 1>, "
        "softly out of focus; the crowd keeps moving.\n"
        "<Audio 1>: fully_copy - Reused 1:1 as the target vocal track; while <Subject 1>'s face is on screen his lip "
        "movements, jaw openings and syllable articulation are synchronized directly to <Audio 1>; after the camera leaves "
        "him the same vocal continues uninterrupted from off screen.\n\n"
        "detailed_description:\n"
        "r34l1sm, Facial Realism, realistic ARRI Alexa Mini LF 35mm lens cinematography, Kodak Vision3 500T film look, "
        "natural soft matte skin texture with fine pores, zero oily shine, %s. Both shots are in the same room: red-brick "
        "walls, dark iron girders, haze, the crowd of workers in flat caps packed around the stage. "
        "[Shot 1] From the very first frame, during %s–%s, the camera holds a chest-up three-quarter medium shot of "
        "<Subject 1> standing on the raised stage, on the %s half of the frame, his face and lips large and readable, "
        "never a wide shot of the stage, with the hall of <Picture 3> blurred behind him, rapping with lively syllable-by-syllable "
        "lip-sync to <Audio 1>, his free left arm stretched out pointing toward screen-%s at his opponent off screen; at "
        "the end of this shot the camera pans %s with large amplitude at fast speed, a whip pan with heavy motion blur. "
        "[Shot 2] At %s, the whip pan lands on a new shot. During %s–%s, the camera holds a static chest-up medium close-up "
        "of <Subject 2> standing on the %s side of the stage with warm amber incandescent bulbs blurred behind him, facing "
        "the camera, mouth firmly closed, jaw tight, his face slowly darkening with anger while <Subject 1>'s voice "
        "continues from off screen. The lyric sung across the whole clip: <d>[English]%s</d> No subtitles, no on-screen "
        "text.\n\n"
        "overall_soundscape:\nClear, punchy foreground rap vocal performance from <Subject 1> during %s–%s synced 1:1 to "
        "<Audio 1> in %s, continuous across the cut.\n\n"
        "non_diegetic_music:\nN/A — <Audio 1> is directly reused 1:1 as the target vocal track."
        % (me["name_en"], me["look"], them["name_en"], them["look"], me["voice"], ts(L), ts(v_end),
           e["venue_en"], MIC, CROWD, e["light_en"],
           ts(L), ts(cut), my, their, their, ts(cut + 0.2), ts(cut + 0.2), ts(v_end), their, text,
           ts(L), ts(v_end), e["arena_sound_en"])).replace(
        "[Shot 1] From the very first frame, during",
        "[Shot 1] During %s–%s, before he starts rapping, his mouth stays closed while the camera pushes in from a wide "
        "view of the stage and settles on him. Then, during" % (ts(0), ts(L)) if L else "[Shot 1] During").replace(
        ", never a wide shot of the stage," if L else "@@", ",")


clips, lip = [], {}   # lip[id] = (音频起点, 最后一个词结束, 覆盖的句子)
# 2026-11-10 重抽两次都压不住：H3 口型镜头开头 1～3 秒总是先给远一点的景再推进来。
# 给这几条加一段无声的开场（音轨在镜头里晚 L 秒才开始），远景和推进落在这段里，剪辑只用开唱之后的部分。
# assemble.py 按 audio[0] - lead 对位，口型不受影响。
PREROLL = {"B05": 2.5, "B11": 3.0}
PRE_CAM = ("During 00:00.000–%s, before he starts rapping, his mouth stays closed while the camera pushes in with "
           "large amplitude at slow speed from a wide shot of him standing on the stage until it reaches the framing "
           "below; from %s to the end of the shot it holds that framing. ")
for c0, c1, kind, action in SHOTS:
    covered = order[order.index(c0):order.index(c1) + 1]
    who = line_by[c0]["who"]
    me_k, them_k = (("a_face_clean", "b_face_clean") if who == "a" else ("b_face_clean", "a_face_clean"))
    plate = "stage_a" if who == "a" else "stage_b"
    a0 = round(line_by[c0]["start"] - PRE, 3)
    a1 = round(max(line_by[c1]["end"], lw_end[c1]), 3)
    text = " / ".join(line_by[x]["text"] for x in covered)
    L = PREROLL.get(c0, 0.0)
    frames = fit(a1 - a0 + L)
    clip = {"id": c0, "kind": "rap", "who": who, "line": line_by[c0]["n"], "move": kind, "text": text,
            "audio": [a0, a1], "lead": L, "frames": frames, "static": False, "sway": 0.5, "drift": 0.0}
    if kind == "WHIP":
        clip.update(raw=True, image_keys=[me_k, them_k, plate], closeup_lora=0.2,
                    prompt=whip_prompt(who, a0, a1, text.replace(" / ", " "), frames, L))
    else:
        two = kind in TWO
        # 2026-11-10 小样：背景图里带着空圆台时，人会被放到台前。背景图已换成「站在台上往外看」的视角，这里再写死一遍
        clip.update(action=action, two_shot=two, cam=(PRE_CAM % (ts(L), ts(L)) + cam(kind, who).replace(
                        "From the very first frame to the last, the camera holds", "The framing is").replace(
                        ", never a full-body or wide shot, his legs and the stage floor never in frame,", ",")
                        if L else cam(kind, who))
                    + ("" if kind == "ENTER" else ONSTAGE))
        if kind == "ENTER":          # 远景起步：不给场景图（给了观众会被冻成静止画面），关掉特写 LoRA
            clip.update(wide=True, image_keys=[me_k], closeup_lora=0.0)
        else:
            clip.update(bg=plate, image_keys=[me_k] + ([them_k] if two else []) + [plate])
        if two:
            clip.update(listener_side=SIDE["b" if who == "a" else "a"], listener=LISTEN[kind])
        if kind in ("ECU", "CRASH"):
            clip["lens"] = "24mm wide-angle"
        if kind in ("PUSH", "ARC", "CRASH"):
            clip["closeup_lora"] = 0.2
        if c0 == "A14":   # 两次都推到只剩眉毛到下巴：特写 LoRA 往里拉 + 24mm 广角放大贴近感，两个都去掉
            clip.update(closeup_lora=0.0, lens="35mm")
    clips.append(clip)
    lip[c0] = (a0, lw_end[c1], covered)

# ---------------------------------------------------------------- 非口型镜头
IMG = {
    "a_face_clean": "Thomas Edison (keep his exact face, dishevelled grey-brown hair, rumpled charcoal three-piece suit, "
                    "gold watch chain, stand-up collar and loose black bow tie)",
    "b_face_clean": "Nikola Tesla (keep his exact face, centre-parted jet-black hair, dark moustache, black frock coat "
                    "with satin lapels, high white wing collar, dark cravat with a pearl pin)",
    "stage_a": "Edison's side of the hall as seen from the stage (a canopy of warm amber bulbs, a giant brass flywheel, brick, the "
               "warmly lit crowd)",
    "stage_b": "Tesla's side of the hall as seen from the stage (two tall brass Tesla coils throwing blue-violet arcs, arched "
               "windows washed in violet light, the crowd)",
    "crowd": "the crowd of " + e["commoners_en"],
    "dj": "the DJ at his raised booth built on a brass dynamo",
}
VENUE_PLAIN = e["venue_en"].split("; the two rappers")[0]
SEAMLESS = ("This shot must cut seamlessly with the rest of the film: same venue, same cold white spotlight beam from "
            "above as the key light, 35-50mm lens look. Setting: " + e["venue_en"] + ". The crowd are " + e["commoners_en"]
            + ". Nobody else stands inside the spotlit circle. Lighting: " + e["light_en"] + ", shallow depth of field, "
            "fine 35mm film grain; warm and well exposed, never dark, murky or blue-grey. Whenever the crowd is in frame, "
            + CROWD + ".")
# 2026-11-10 第二轮小样：只要文字里提到「两位说唱手站在台上」，反应特写和观众镜头的背景里就会多出一个舞台和
# 两个站着的人。不含两位主角同框的镜头，用下面这段不提舞台和说唱手的版本。
SEAMLESS_SOLO = ("This shot must cut seamlessly with the rest of the film: same hall, 35-50mm lens look. Setting: "
                 + VENUE_PLAIN.split(", and a raised round iron stage")[0] + ". The crowd are " + e["commoners_en"]
                 + ". Lighting: " + e["light_en"].replace(", one cold white spotlight beam from above cutting through soft haze", "")
                 + ", shallow depth of field, fine 35mm film grain; warm and well exposed, never dark, murky or blue-grey. "
                 "Whenever the crowd is in frame, " + CROWD + ".")
RULES_SOLO = ("Keep the face, hairstyle, costume and colors exactly as in the reference images. There is no stage, no "
              "spotlit platform and no performer anywhere in the background of this shot. No subtitles, no on-screen text, "
              "no logos, no watermark.")
RULES_BASE = ("Keep every character's face, hairstyle, costume and colors exactly as in their reference images. Edison "
              "always stands on the left side of the stage with the amber bulbs behind him, Tesla on the right with the "
              "Tesla coils behind him. Whenever Edison or Tesla is in frame he stands on top of the raised round "
              "stage, above the crowd. No subtitles, no on-screen text, no logos, no watermark.")
# 第一轮（2026-11-10）：把「两人各拿一支麦」写进所有非口型镜头后，观众和 DJ 手里也长出了麦克风
RULES_MIC = " Each of the two men holds one " + MIC + " in his right hand and nothing else."
RULES_NOMIC = " Nobody in this shot holds a microphone: there is no microphone anywhere in the frame."


def still(sid, keys, shot, frames=STILL_FRAMES, lora=None, mic=False):
    head = " ".join("Image %d is %s." % (i, IMG[k]) for i, k in enumerate(keys, 1))
    c = {"id": sid, "kind": "still", "move": "V2", "frames": frames, "image_keys": keys,
         "prompt": "\n\n".join([head, "Cinematic photoreal shot, 16:9. " + shot] + (
             [SEAMLESS, RULES_BASE + RULES_MIC] if mic else [SEAMLESS_SOLO, RULES_SOLO + RULES_NOMIC]))}
    if lora is not None:
        c["closeup_lora"] = lora
    clips.append(c)


def react(sid, who, act):
    name, keys = (("Thomas Edison", ["a_face_clean", "stage_a"]) if who == "a" else ("Nikola Tesla", ["b_face_clean", "stage_b"]))
    still(sid, keys, "From the very first frame to the last, the camera holds a static tight head-and-shoulders "
                     "close-up of %s (Image 1) alone, frontal, at eye level: his face fills the upper two thirds of the "
                     "frame, his hands and arms are out of frame, and %s (Image 2) glow softly blurred behind him, never "
                     "a plain studio backdrop or a dark wall of people. He is listening to his opponent, not rapping: his "
                     "mouth stays firmly closed the whole time. %s" % (
                         name, "the amber bulbs and brass flywheel of his side of the hall" if who == "a" else
                         "the violet-lit Tesla coils and arched windows of his side of the hall", act))


react("R_T_SHIP", "b", "One eyebrow slowly rises and the corner of his mouth lifts in a thin, amused smile.")
react("R_T_HOTEL", "b", "His eyes drop for a moment and his jaw tightens, then he looks back up, cold and proud.")
react("R_T_SWEAT", "b", "He tilts his head a few degrees and exhales through his nose, utterly unimpressed.")
react("R_E_FAIR", "a", "His confident smirk fades and his eyes narrow, a muscle twitching in his cheek.")
react("R_E_BANK", "a", "He glances away to one side and swallows, then glares back, face reddening.")
react("R_E_HUM", "a", "He grinds his teeth, nostrils flaring, staring straight back in fury.")
still("OPEN", ["a_face_clean", "b_face_clean"],
      "Over-the-shoulder shot at eye level, handheld: the blurred dark shoulder and back of the head of Nikola Tesla "
      "(Image 2) fill the right foreground, and beyond him Thomas Edison (Image 1) stands chest-up on the left, facing the "
      "camera, lifting his microphone toward his chin with a slow confident smirk, mouth closed, amber bulbs glowing behind "
      "him; the camera pulls out with small amplitude at slow speed.", mic=True)
still("DJ_FRONT", ["dj"],
      "Frontal medium shot of exactly one person, the DJ (Image 1), alone behind his raised booth of brass dynamos, scratching a record with one hand and "
      "pressing one headphone to his ear with the other, small electric sparks jumping from the dynamos, the crowd "
      "bouncing in the haze behind him.", frames=124)
still("DJ_HANDS", ["dj"],
      "Low-angle close shot across the turntables of the DJ booth (Image 1): the DJ's hands scratch a spinning record and "
      "ride a brass fader, his torso above, coloured indicator lamps glowing on the brass mixer, haze and stage light "
      "behind.", frames=124)
still("CROWD_OOH", ["crowd"],
      "" + NOSTAGE + "Close medium shot packed with four or five workers from the front row (Image 1), their faces large and filling the "
      "16:9 frame, handheld camera at their eye level, the hall lights only a blurred glow behind them. They react to a "
      "brutal punchline: one claps both hands over his mouth, one grabs his flat cap with wide eyes, one doubles over "
      "laughing and shoves his friend. Energetic, joyful chaos.")
still("CROWD_CHANT", ["crowd"],
      "" + NOSTAGE + "Close medium shot of the front rows of the crowd (Image 1), handheld at their eye level, faces large and lit by warm "
      "amber light: workers and engineers chant together with their fists pumping in rhythm, mouths wide open, sweat and "
      "haze. The camera trucks right with small amplitude at slow speed along the front row and stays on their faces.")
still("CROWD_STARE", ["crowd"],
      "" + NOSTAGE + "Medium close shot of three workers in the front row (Image 1), handheld at their eye level, warm amber light: they "
      "look up past the camera in tense silence, arms folded, one of them slowly letting out a low whistle and shaking his head.")
still("CROWD_LAUGH", ["crowd"],
      "" + NOSTAGE + "Close shot of one young worker in a flat cap in the front row (Image 1) throwing his head back and roaring with "
      "laughter, one fist punching the air, his friends cheering and clapping around him, warm amber light, handheld.")
still("CURTAIN", ["a_face_clean", "b_face_clean"],
      "The shot starts as a waist-up medium two-shot of Thomas Edison (Image 1) on the left and Nikola Tesla (Image 2) on "
      "the right standing side by side on the stage, both facing the camera, both spreading their arms wide to the roaring "
      "crowd, mouths closed, Tesla with a calm victorious smile and Edison with a grudging one. Then the camera pulls out "
      "and pedestals up with large amplitude at slow speed, rising steadily backward and upward over the heads of the "
      "audience until it holds a high wide shot of the whole dynamo hall: the two men small in the spotlight at the "
      "center of the circular stage, hundreds of cheering workers with raised fists all around them, amber bulbs on the "
      "left, Tesla coils arcing on the right. During the last second the camera smoothly decelerates and settles into a "
      "stationary shot.", frames=192, lora=0.0, mic=True)
ids = {c["id"]: c for c in clips}

# ---------------------------------------------------------------- 时间线
# 句中插入的反应 / 观众镜头：(所在口型镜头, 句子, 从哪个词切走, 时长, 镜头, 入点)。时长 None = 一直到这条口型镜头结束
CUTAWAYS = [
    ("A03", "A04", "ship", None, "R_T_SHIP", 1.2),
    ("B03", "B04", "sulked", None, "R_E_FAIR", 0.3),
    ("A11", "A12", "scrapped", 1.0, "CROWD_STARE", 0.6),
    ("A13", "A13", "that's", None, "R_T_SWEAT", 0.3),
    ("B10", "B10", "current", None, "R_E_BANK", 0.5),
    ("B11", "B12", "buffalo", 0.9, "CROWD_LAUGH", 0.6),
    ("B14", "B14", "hums", None, "R_E_HUM", 0.5),
]
GAPS = {   # 换人空档：(镜头, 入点)，按顺序平分空档
    "A08": [("CROWD_OOH", 0.05), ("DJ_HANDS", 0.3)],
    "B08": [("CROWD_CHANT", 0.2), ("DJ_FRONT", 2.5)],   # DJ_FRONT 只有开头 1.5 秒可用
}
first = lip["A01"][0]
spans = [(0.0, round(first * 0.52, 3), "OPEN", 0.9), (round(first * 0.52, 3), first, "DJ_FRONT", 0.2)]
lip_ids = [s[0] for s in SHOTS]
cut_by = {}
for head, line, word, d, sid, inn in CUTAWAYS:
    cut_by.setdefault(head, []).append((word_t(line, word), d, sid, inn))
MIN_ON = 0.8
for k, c in enumerate(lip_ids):
    a0, lwe, _ = lip[c]
    nxt = lip_ids[k + 1] if k + 1 < len(lip_ids) else None
    t0 = spans[-1][1]
    gap = c in GAPS
    t1 = round(lwe + 0.02, 3) if (nxt is None or gap) else round(max(lip[nxt][0], lwe + 0.02), 3)
    t = t0
    for tc, d, sid, inn in sorted(cut_by.get(c, [])):
        te = t1 if d is None else round(tc + d, 3)
        assert tc - t >= MIN_ON, "%s: only %.2fs on the singer before %s" % (c, tc - t, sid)
        assert te <= t1 + 1e-6
        spans.append((t, tc, c, None))
        spans.append((tc, te, sid, inn))
        t = te
    if t1 - t > 1e-6:
        assert t == t0 or t1 - t >= 0.5, "%s: %.2fs tail after a cutaway" % (c, t1 - t)
        spans.append((t, t1, c, None))
    if gap:
        g0, g1 = t1, lip[nxt][0]
        n = len(GAPS[c])
        for j, (sid, inn) in enumerate(GAPS[c]):
            spans.append((round(g0 + (g1 - g0) * j / n, 3), round(g0 + (g1 - g0) * (j + 1) / n, 3), sid, inn))
# A09 开头：上一段唱完的空档已经用掉，R_T_HOTEL 放在 A09 的后半句
o0 = spans[-1][1]
spans.append((o0, round(o0 + 0.9, 3), "DJ_HANDS", 3.0))
spans.append((round(o0 + 0.9, 3), END_T, "CURTAIN", 1.6))
edl = [{"t0": a, "t1": b, "clip": c, "in": i} for a, b, c, i in spans]

# R_T_HOTEL：第三段第一句（A09）后半句落在 Tesla 脸上
i9 = next(i for i, x in enumerate(edl) if x["clip"] == "A09")
tc = word_t("A09", "ask")
x9 = edl[i9]
assert tc - x9["t0"] >= MIN_ON
edl[i9:i9 + 1] = [{"t0": x9["t0"], "t1": tc, "clip": "A09", "in": None},
                  {"t0": tc, "t1": x9["t1"], "clip": "R_T_HOTEL", "in": 0.3}]

# ---------------------------------------------------------------- 断言
for prev, cur in zip(edl, edl[1:]):
    assert abs(prev["t1"] - cur["t0"]) < 1e-6, (prev, cur)
assert abs(edl[0]["t0"]) < 1e-6 and abs(edl[-1]["t1"] - END_T) < 1e-6
for x in edl:
    c = ids[x["clip"]]
    d = x["t1"] - x["t0"]
    assert d > 0.3, "%s only %.2fs" % (x["clip"], d)
    if c["kind"] == "rap":
        assert x["t0"] >= c["audio"][0] - 1e-6, x
        assert x["t1"] - c["audio"][0] + c["lead"] <= c["frames"] / FPS + 1e-6, "%s runs past its clip" % x["clip"]
    else:
        assert x["in"] + d <= c["frames"] / FPS - 0.05, "%s: in %.2f + %.2fs > clip" % (x["clip"], x["in"], d)
used = {x["clip"] for x in edl}
assert used == set(ids), "unused: %s; undefined: %s" % (set(ids) - used, used - set(ids))
# 每个词都要么落在唱的人身上，要么落在登记过的切走镜头上
cut_ids = {c[4] for c in CUTAWAYS} | {"R_T_HOTEL"}
for w in WORDS:
    if not is_sung(w) or w["t0"] < first or w["t0"] > lip[lip_ids[-1]][1]:
        continue
    x = next((x for x in edl if x["t0"] - 1e-6 <= w["t0"] < x["t1"]), None)
    assert x and (ids[x["clip"]]["kind"] == "rap" or x["clip"] in cut_ids), "word %r at %.2f lands on %s" % (
        w["w"], w["t0"], x and x["clip"])

# ---------------------------------------------------------------- 后期特效
def slot(cid):
    return next(x for x in edl if x["clip"] == cid)


fx = [{"type": "flash", "t0": round(grid["beat0"], 3), "t1": round(grid["beat0"] + 0.08, 3), "alpha": 0.7}]
for rid in ("R_T_HOTEL", "R_E_HUM"):   # 重拳句落在对手脸上：闪白 + 震屏
    x = slot(rid)
    fx += [{"type": "flash", "t0": x["t0"], "t1": round(x["t0"] + 0.08, 3), "alpha": 0.85},
           {"type": "shake", "t0": x["t0"], "t1": round(x["t0"] + 0.5, 3), "px": 9}]
for sid in ("CROWD_OOH", "CROWD_CHANT", "CURTAIN"):
    x = slot(sid)
    fx.append({"type": "flash", "t0": x["t0"], "t1": round(x["t0"] + 0.08, 3), "alpha": 0.8})
# 原来是 dark 压暗 0.12：叠在本来就偏冷的背景上整段发蓝发黑（2026-11-10 全片）。改成数码推近
fx.append({"type": "punch", "t0": word_t("B16", "footnote"), "t1": slot("B16")["t1"], "amount": 0.08})

json.dump(clips, open(os.path.join(WORK, "clips.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(edl, open(os.path.join(WORK, "edl.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(fx, open(os.path.join(WORK, "fx.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# ---------------------------------------------------------------- 汇报
raps = [c for c in clips if c["kind"] == "rap"]
tot = sum(c["frames"] for c in clips)
print("clips: %d (lip %d, non-lip %d), %d frames = %.1f s" % (len(clips), len(raps), len(clips) - len(raps), tot, tot / FPS))
bounds = [("V1", lip["A01"][0], lip["B01"][0]), ("V2", lip["B01"][0], lip["A09"][0]),
          ("V3", lip["A09"][0], lip["B09"][0]), ("V4", lip["B09"][0], lip["B16"][1])]
for name, s, t in bounds:
    ds = sorted(x["t1"] - x["t0"] for x in edl if s - 1e-6 <= x["t0"] < t)
    print("  %s: %2d shots, median %.2fs, min %.2f, max %.2f" % (name, len(ds), ds[len(ds) // 2], ds[0], ds[-1]))
for x in edl:
    print("  %6.2f-%6.2f %5.2fs %-12s %s" % (x["t0"], x["t1"], x["t1"] - x["t0"], x["clip"], ids[x["clip"]]["move"]))
