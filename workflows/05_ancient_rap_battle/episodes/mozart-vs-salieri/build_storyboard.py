# -*- coding: utf-8 -*-
"""Mozart vs Salieri 分镜构建脚本（Realism V3 暖调电影实拍 + 动态运镜拍法）：
  * 右手贴下唇下方 45° 斜握复古镀铬网头手持麦，左手随歌词自由做手势（不拿易漂移的小道具）
  * 一个口型镜头可跨 1～2 句、带真实运镜（ENTER 穿过人群、PUSH 前推、ARC 绕肩、FACE 鼻尖对峙、REVEAL 横摇、ECU、CRASH 急推、LONG）
  * 句中切到对手 / 观众的反应镜头（L-cut），声音不断，切回来还是同一条口型镜头
  * 四段越往后切得越快、贴得越近（前两段进场 + 长镜头，后两段以贴脸对峙为主）
  * 站位固定：Mozart 在左（白假发鲜红礼服 · 古钢琴与发光乐谱侧）、Salieri 在右（深栗色长发深藏青礼服 · 鎏金指挥台与管风琴侧）

usage: python3 build_storyboard.py
"""
import json
import math
import os
import re

EP = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(EP, "work")
FPS = 24
PRE = 0.08          # 在第一个词前 0.08 秒起音频
STILL_FRAMES = 73   # 非口型镜头 3.04 秒
MAX_FRAMES = 209    # 单条口型镜头上限（小样验证过 209 帧）

# ---------------------------------------------------------------- 素材校验与现场运镜层配置
for sub in ("work", "refs", "clips"):
    os.makedirs(os.path.join(EP, sub), exist_ok=True)
for f in ("work/lines.json", "work/words_edit.json", "work/grid.json", "work/vocals_final.wav", "work/music_final.wav",
          "work/a_face_clean.png", "work/b_face_clean.png", "work/stage_a.png", "work/stage_b.png",
          "refs/crowd.png", "refs/dj.png", "refs/venue.png"):
    assert os.path.exists(os.path.join(EP, f)), "missing " + f

json.dump({"handheld_px": 10, "drift": 0.04, "margin": 0.06, "whip": True, "whip_secs": 0.12, "contrast": 1.03,
           "saturation": 1.0, "beat_pulse": 0.02, "grain": 4, "vignette": 0, "cool": False},
          open(os.path.join(WORK, "live.json"), "w", encoding="utf-8"), indent=1)

e = json.load(open(os.path.join(EP, "episode.json"), encoding="utf-8"))
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
HAND = ", shot on a handheld 35mm cinema camera with a subtle natural sway"


def cam(kind, who):
    me, them = LR[who]
    if kind == "ENTER":   # 观众背后穿过人群推到台上
        return ("The camera starts behind the audience at head height: the backs of powdered wigs, velvet shoulders and raised hands of "
                "the packed Viennese opera crowd fill the lower half of the frame with the spotlit round stage small in the distance, then the "
                "camera pushes in with large amplitude at slow speed, gliding forward between the raised arms and over the "
                "shoulders of the spectators until it reaches the edge of the stage and settles on a chest-up medium shot of "
                "<Subject 1>; " + CROWD)
    if kind == "PUSH":    # 中景推到近景
        return ("The camera starts on a waist-up medium shot of <Subject 1> in the crisp spotlight beam, then the camera "
                "pushes in with large amplitude at slow speed, travelling steadily toward him until it settles on a "
                "head-and-shoulders close-up at Cooke Panchro T2.2 shallow depth of field" + READ)
    if kind == "ARC":     # 绕到唱者身后变成过肩拍听者
        return ("The camera starts on a chest-up medium shot of <Subject 1> from the front as he raps, then the camera "
                "trucks %s and pans %s with large amplitude at slow speed, moving in an arc shot around his %s shoulder, "
                "until it ends as an over-the-shoulder shot from behind him: the back of <Subject 1>'s head and his %s "
                "shoulder softly blurred in the %s foreground, and <Subject 2> in sharp focus a few steps away on %s, "
                "facing the camera" % (me, them, me, me, me, SIDE["b" if who == "a" else "a"]))
    if kind == "FACE":    # 鼻尖相对的侧面双人，慢推
        return ("The camera holds a tight eye-level profile two-shot of the two men standing face to face, almost nose to "
                "nose, a foot apart: <Subject 1> on %s in profile %s, leaning in and rapping straight into <Subject 2>'s "
                "face, <Subject 2> on %s in profile %s; both from the chest up, and the camera pushes in with small "
                "amplitude at slow speed until their two faces fill the frame at T2.2 shallow depth of field, <Subject 1>'s lips and jaw clearly readable "
                "in profile in every frame" % (SIDE[who], FACING[who], SIDE["b" if who == "a" else "a"],
                                               FACING["b" if who == "a" else "a"]) + HAND)
    if kind == "FACEWIDE":  # 拉宽的双人：半身，顶光在两人之间
        return ("The camera holds a waist-up medium profile two-shot at eye level: <Subject 1> on %s %s, leaning toward "
                "<Subject 2> and rapping at him, <Subject 2> on %s %s standing his ground, the crisp silver overhead spotlight beam falling "
                "between the two men while warm 2700K chandelier bokeh glows behind them, <Subject 1>'s lips and jaw clearly readable in every frame"
                % (SIDE[who], FACING[who], SIDE["b" if who == "a" else "a"], FACING["b" if who == "a" else "a"]) + HAND)
    if kind == "REVEAL":  # 从单人横摇带出对手
        return ("The camera starts on a chest-up three-quarter medium close-up of <Subject 1> alone on the %s half of the "
                "frame, %s as he raps, then the camera pans %s with small amplitude at slow speed, revealing <Subject 2> "
                "standing in profile at the %s edge of the frame, and settles into a profile two-shot of the two men face "
                "to face, <Subject 1>'s lips and jaw clearly readable in every frame" % (me, FACING[who], them, them))
    if kind == "ECU":     # 仰拍广角大特写
        return ("A handheld 28mm cinema lens is close to his face and slightly below chin height, looking "
                "up at him: a tight close-up where his face fills most of the 16:9 frame, the chrome mesh head of the microphone "
                "softly foreshortened at the bottom edge of the frame just below his lower lip (never crossing his lips); the camera pushes in with small amplitude at "
                "slow speed, warm 2700K candle chandelier bokeh orbs flaring behind his head, his lips large and clearly readable in every frame")
    if kind == "CRASH":   # 从过肩中景急推到大特写
        return ("The camera starts on an over-the-shoulder medium shot: the blurred shoulder and hair of "
                "<Subject 2> in the %s foreground, <Subject 1> chest-up on the %s facing the camera, then the camera pushes "
                "in with large amplitude at fast speed past the shoulder, a sudden crash push-in that lands on a tight "
                "close-up where his whole face from hairline to chin fills the frame, never closer than that, and shakes "
                "slightly as it lands, his lips large and clearly readable"
                % (them, me))
    if kind == "LONG":    # 正面近景长镜头，慢推
        return ("From the very first frame to the last, the camera holds a frontal head-and-shoulders close-up at eye "
                "level at Cooke Panchro 50mm T2.2" + HAND + ", never a full-body or wide shot, his legs and the stage floor never in frame, and "
                "pushes in with small amplitude at slow speed across the whole shot; his face fills the upper two thirds "
                "of the 16:9 frame, his lips large and clearly readable in every frame")
    if kind == "TQ":      # 四分之三侧中景
        return ("The camera holds a chest-up three-quarter medium close-up of <Subject 1> on the %s half of the frame, %s"
                % (me, FACING[who]) + HAND + ", slowly arcing a few degrees around him at T2.2 shallow depth of field, his face and lips large and "
                "clearly readable in every frame")
    raise KeyError(kind)


ONSTAGE = (". He stands on top of the raised round stage: the cheering crowd silhouettes are on the opera pit floor below and behind him, lower "
           "than his chest, softly out of focus at T2.2, and nobody stands at his own level except his opponent")
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
    # ---- 第一段 Mozart：神童登场，灵动张扬
    ("A01", "A02", "ENTER", "spreading all five fingers of his free left hand proudly, then sweeping his palm briefly across his eyes like a playful blindfold"),
    ("A03", "A04", "PUSH", "miming turning a heavy lock key with his free left hand, then tapping his temple sharply with one finger"),
    ("A05", "A06", "ARC", "tugging an imaginary collar away from his neck with his free left hand, then sweeping his arm outward in defiance"),
    ("A07", "A07", "ECU", "conducting a soaring grace note in the air with his free left hand, grinning straight into the lens"),
    ("A08", "A08", "FACE", "counting rapid invisible notes in the air between their faces with his left fingers, then pointing firmly at his own chest"),
    # ---- 第二段 Salieri：帝国宫廷乐长稳重压迫反击
    ("B01", "B02", "ENTER", "raising his free left palm calmly to silence the hall, then tapping the golden Imperial medallion on his chest"),
    ("B03", "B04", "LONG", "holding his free left hand level like a scale weighing two operas, then lifting one index finger high in triumph"),
    ("B05", "B06", "WHIP", None),
    ("B07", "B07", "CRASH", "miming scribbling a frantic whining letter on his left palm, eyes blazing with aristocratic disdain"),
    ("B08", "B08", "FACE", "flicking his free left fingers forward between their faces as if tossing away wasted gold coins"),
    # ---- 第三段 Mozart：节奏加快，贴脸嘲讽传闻与不朽地位
    ("A09", "A09", "ECU", "cupping his free left hand behind his ear mockingly as if listening for silence, smirking down into the lens"),
    ("A10", "A10", "REVEAL", "blowing imaginary dust off his open left palm toward his opponent, stepping in close"),
    ("A11", "A12", "FACE", "sweeping his free left arm wide to show a mountain of scores, then snapping his fingers cleanly on the beat"),
    ("A13", "A13", "TQ", "miming tipping a drop into an imaginary goblet with his free left fingers, eyeing his rival sideways"),
    ("A14", "A14", "CRASH", "pointing his free left index finger straight toward his rival's chest with a piercing glare"),
    ("A15", "A15", "FACEWIDE", "sweeping his free left arm in a wide arc across the entire candlelit opera house"),
    ("A16", "A16", "LONG", "framing an imaginary cinema screen in the air with his free left hand and winking cockily at the camera"),
    # ---- 第四段 Salieri：最快最狠，史实铁证正面粉碎谣言
    ("B09", "B09", "TQ", "slicing his free left hand sharply sideways to dismiss the poison fairy tale once and for all"),
    ("B10", "B10", "FACE", "pointing his free left hand accusingly up toward the gilded royal opera boxes while staring straight into Mozart's eyes"),
    ("B11", "B12", "LONG", "clapping his free left hand against his chest in proud applause, then lowering his hand slowly in solemn respect"),
    ("B13", "B13", "ECU", "ticking off three legendary names on the fingers of his free left hand right into the lens with commanding authority"),
    ("B14", "B14", "FACE", "opening his free left arm toward the orchestra pit while glaring nose-to-nose at his rival"),
    ("B15", "B15", "FACEWIDE", "freezing his free left hand mid-conduct in the air between them as if the Requiem suddenly stopped"),
    ("B16", "B16", "CRASH", "pointing his free left index finger straight down at the stage floor in front of him, then locking eyes dead-center into the lens"),
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
    """一条里两个镜头，甩镜落到对手脸上，后半段唱的人不在画面里（Realism V3 双色温 + T2.2 浅景深协议）。"""
    me, them = (A, B) if who == "a" else (B, A)
    my, their = LR[who]
    v_end = min(frames / FPS - 0.05, L + a1 - a0)
    cut = round(L + word_t("B06", "blew") - a0, 2)
    return (
        "subject_definitions:\n"
        "<Subject 1> is %s (%s) from <Picture 1>, real human skin with matte pores and zero plastic sheen.\n"
        "<Subject 2> is %s (%s) from <Picture 2>, real human skin with matte pores.\n"
        "<Picture 3> is the candlelit opera house stage backdrop behind <Subject 1> in [Shot 1]: gilded Imperial podium, "
        "brass organ pipes, warm 2700K chandeliers and softly blurred cheering Viennese spectators below.\n"
        "<Audio 1> is the target rap vocal track for <Subject 1>, providing his exact vocal timbre (%s) and "
        "syllable-by-syllable rhythm during %s–%s, followed by silence.\n\n"
        "summary:\n[reference generation + audio reuse] Inside %s, <Subject 1> performs an energetic English battle-rap "
        "couplet synced syllable-by-syllable to <Audio 1>, holding the %s just below his lower lip angled upward at 45 degrees "
        "near the bottom edge of the frame, across 2 shots, with <Subject 2> listening in silence, while %s.\n\n"
        "retention_analysis:\n"
        "<Subject 1> (appears in [Shot 1]): fully_preserved - Strictly preserve exact facial bone structure, hairstyle "
        "and court coat from <Picture 1> with authentic matte skin.\n"
        "<Subject 2> (appears in [Shot 2]): fully_preserved - Strictly preserve exact facial structure, white powdered wig and scarlet coat "
        "from <Picture 2>, keeping his mouth closed in silent listening throughout this clip.\n"
        "Background (appears in [Shot 1]): reference - Keep the stage environment of <Picture 3> softly out of focus at Cooke Panchro T2.2 "
        "shallow depth of field behind <Subject 1> with warm 2700K chandelier bokeh orbs while the cheering crowd silhouettes bounce.\n"
        "<Audio 1>: fully_copy - Reused 1:1 as the target vocal track; while <Subject 1>'s face is on screen his lip "
        "movements, jaw openings and syllable articulation are synchronized directly to <Audio 1>; after the camera leaves "
        "him the same vocal continues uninterrupted from off screen.\n\n"
        "detailed_description:\n"
        "r34l1sm, Facial Realism, authentic live-action 35mm concert documentary film shot on ARRI Alexa Mini LF with Cooke Panchro T2.2 prime lens on Kodak Vision3 500T film, "
        "natural matte human skin texture with real pores, zero oily shine, %s. Both shots are in the same candlelit Vienna opera house: gilded crimson boxes, "
        "crystal chandeliers, light smoke, cheering crowd silhouettes packed below the stage. "
        "[Shot 1] From the very first frame, during %s–%s, the camera holds a chest-up three-quarter medium close-up of "
        "<Subject 1> standing on the raised stage, on the %s half of the frame, his face and lips large and readable, "
        "never a wide shot of the stage, holding the %s in his right hand an inch below his lower lip angled upward at 45 degrees (never occluding his lips), "
        "with <Picture 3> blurred into T2.2 bokeh behind him, rapping with intense brow and cheek articulation synced syllable-by-syllable "
        "to <Audio 1>, his free left palm held out mockingly toward screen-%s; at "
        "the end of this shot the camera pans %s with large amplitude at fast speed, a whip pan with heavy motion blur. "
        "[Shot 2] At %s, the whip pan lands on a new shot. During %s–%s, the camera holds a tight chest-up medium close-up "
        "of <Subject 2> standing on the %s side of the stage with warm 2700K fortepiano candlelight bokeh blurred behind him at T2.2, facing "
        "the camera, mouth firmly closed, jaw tight, his cocky smile fading into stung irritation while <Subject 1>'s voice "
        "continues from off screen. The lyric sung across the whole clip: <d>[English]%s</d> No subtitles, no on-screen "
        "text.\n\n"
        "overall_soundscape:\nClear, punchy foreground rap vocal performance from <Subject 1> during %s–%s synced 1:1 to "
        "<Audio 1> in %s, continuous across the cut.\n\n"
        "non_diegetic_music:\nN/A — <Audio 1> is directly reused 1:1 as the target vocal track."
        % (me["name_en"], me["look"], them["name_en"], them["look"], me["voice"], ts(L), ts(v_end),
           e["venue_en"], MIC, CROWD, e["light_en"],
           ts(L), ts(cut), my, MIC, their, their, ts(cut + 0.2), ts(cut + 0.2), ts(v_end), their, text,
           ts(L), ts(v_end), e["arena_sound_en"])).replace(
        "[Shot 1] From the very first frame, during",
        "[Shot 1] During %s–%s, before he starts rapping, his mouth stays closed while the camera pushes in from a wide "
        "view of the stage and settles on him. Then, during" % (ts(0), ts(L)) if L else "[Shot 1] During").replace(
        ", never a wide shot of the stage," if L else "@@", ",")


clips, lip = [], {}   # lip[id] = (音频起点, 最后一个词结束, 覆盖的句子)
PREROLL = {"B05": 2.5, "B11": 2.5}
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
    L_pre = PREROLL.get(c0, 0.0)
    frames = fit(a1 - a0 + L_pre)
    clip = {"id": c0, "kind": "rap", "who": who, "line": line_by[c0]["n"], "move": kind, "text": text,
            "audio": [a0, a1], "lead": L_pre, "frames": frames, "static": False, "sway": 0.5, "drift": 0.0}
    if kind == "WHIP":
        clip.update(raw=True, image_keys=[me_k, them_k, plate], closeup_lora=0.2,
                    prompt=whip_prompt(who, a0, a1, text.replace(" / ", " "), frames, L_pre))
    else:
        two = kind in TWO
        clip.update(action=action, two_shot=two, cam=(PRE_CAM % (ts(L_pre), ts(L_pre)) + cam(kind, who).replace(
                        "From the very first frame to the last, the camera holds", "The framing is").replace(
                        ", never a full-body or wide shot, his legs and the stage floor never in frame,", ",")
                        if L_pre else cam(kind, who))
                    + ("" if kind == "ENTER" else ONSTAGE))
        if kind == "ENTER":          # 远景起步：不给场景图（给了观众会被冻成静止画面），关掉特写 LoRA
            clip.update(wide=True, image_keys=[me_k], closeup_lora=0.0)
        else:
            clip.update(bg=plate, image_keys=[me_k] + ([them_k] if two else []) + [plate])
        if two:
            clip.update(listener_side=SIDE["b" if who == "a" else "a"], listener=LISTEN[kind])
        if kind in ("ECU", "CRASH"):
            clip["lens"] = "28mm wide-angle"
        if kind in ("PUSH", "ARC", "CRASH"):
            clip["closeup_lora"] = 0.2
        if c0 == "A14":   # 防止 CRASH 推得过近，去掉特写 LoRA 和广角
            clip.update(closeup_lora=0.0, lens="35mm")
    clips.append(clip)
    lip[c0] = (a0, lw_end[c1], covered)

# ---------------------------------------------------------------- 非口型镜头
IMG = {
    "a_face_clean": "Wolfgang Amadeus Mozart (keep his exact youthful face, neat compact white powdered queue wig tied with a black silk ribbon, "
                    "vivid scarlet-red velvet Viennese frock coat with gold brocade trim, ivory waistcoat and white lace jabot)",
    "b_face_clean": "Antonio Salieri (keep his exact patrician face, sleek dark chestnut-brown hair swept back with silvering temples and no white powder, "
                    "deep midnight-navy velvet Imperial court coat with gold embroidery, golden court medallion and white cravat)",
    "stage_a": "Mozart's left side of the Vienna opera house as seen from the stage (softly blurred gilded crimson boxes, Viennese fortepiano, "
               "2700K crystal chandelier bokeh and cheering crowd silhouettes)",
    "stage_b": "Salieri's right side of the Vienna opera house as seen from the stage (softly blurred gilded Imperial podium, brass organ pipes, "
               "2700K crystal chandelier bokeh and cheering crowd silhouettes)",
    "venue": "the packed 1786 Vienna Imperial Court Opera House at night with an empty spotlit central round stage, fortepiano on the left and brass organ pipes on the right",
    "crowd": "the roaring Viennese crowd of " + e["commoners_en"],
    "dj": "the young 18th-century Viennese court musician DJ at his raised baroque harpsichord turntable booth",
}
VENUE_PLAIN = e["venue_en"].split("; the two rappers")[0]
SEAMLESS = ("Authentic live-action 35mm cinema shot on ARRI Alexa Mini LF with Cooke Panchro T2.2 lens on Kodak Vision3 500T film, "
            "natural matte human skin with fine pores (zero plastic sheen). Setting: " + e["venue_en"] + ". The crowd are " + e["commoners_en"]
            + ". Lighting: " + e["light_en"] + ". Whenever the crowd is in frame, " + CROWD + ".")
SEAMLESS_SOLO = ("Authentic live-action 35mm cinema shot on ARRI Alexa Mini LF with Cooke Panchro T2.2 lens on Kodak Vision3 500T film, "
                 "natural matte human skin with fine pores (zero plastic sheen). Setting: "
                 + VENUE_PLAIN.split(", and a raised round dark-wood stage")[0] + ". The crowd are " + e["commoners_en"]
                 + ". Lighting: " + e["light_en"] + ". Whenever the crowd is in frame, " + CROWD + ".")
RULES_SOLO = ("Keep the face, hairstyle, wig, costume and colors exactly as in the reference images. There is no stage, no "
              "spotlit platform and no performer anywhere in the background of this shot. No subtitles, no on-screen text, "
              "no logos, no watermark.")
RULES_BASE = ("Keep every character's face, hairstyle, wig, costume and colors exactly as in their reference images. Mozart "
              "always stands on the left side of the stage in his scarlet coat and white powdered wig, Salieri on the right in his "
              "midnight-navy gold-embroidered court coat and dark hair. Whenever Mozart or Salieri is in frame he stands on top of the raised round "
              "stage, above the crowd. No subtitles, no on-screen text, no logos, no watermark.")
RULES_MIC = " Each of the two men holds one " + MIC + " in his right hand and nothing else."
RULES_NOMIC = " Nobody in this shot holds a microphone: there is no microphone anywhere in the frame."


def still(sid, keys, shot, frames=STILL_FRAMES, lora=None, mic=False):
    head = " ".join("Image %d is %s." % (i, IMG[k]) for i, k in enumerate(keys, 1))
    c = {"id": sid, "kind": "still", "move": "V2", "frames": frames, "image_keys": keys,
         "prompt": "\n\n".join([head, "Cinematic photoreal 35mm film shot, 16:9. " + shot] + (
             [SEAMLESS, RULES_BASE + RULES_MIC] if mic else [SEAMLESS_SOLO, RULES_SOLO + RULES_NOMIC]))}
    if lora is not None:
        c["closeup_lora"] = lora
    clips.append(c)


def react(sid, who, act):
    name, keys = (("Wolfgang Amadeus Mozart", ["a_face_clean", "stage_a"]) if who == "a" else ("Antonio Salieri", ["b_face_clean", "stage_b"]))
    still(sid, keys, "From the very first frame to the last, the camera holds a tight head-and-shoulders "
                     "close-up of %s (Image 1) alone at Cooke Panchro 50mm T2.2 shallow depth of field, frontal, at eye level: his face fills the upper two thirds of the "
                     "frame, his hands and arms are out of frame, and %s (Image 2) glow softly blurred into warm 2700K bokeh orbs behind him, never "
                     "a sharp wall of tiny faces. He is listening to his opponent, not rapping: his "
                     "mouth stays firmly closed the whole time. %s" % (
                         name, "the warm chandelier bokeh and gilded crimson opera boxes of his side of the house" if who == "a" else
                         "the warm chandelier bokeh and brass organ pipes of his side of the house", act))


react("R_S_SCORE", "b", "One dark eyebrow slowly rises and the corner of his mouth lifts in a cold, sceptical courtier's smile.")
react("R_S_TUNE", "b", "His eyes narrow sharply and a muscle twitches in his jaw, then he lifts his chin with icy composure.")
react("R_S_CUP", "b", "He tilts his head slightly and exhales through his nose, shaking his head once in disdain at the slander.")
react("R_M_VOTE", "a", "His cocky smirk fades in an instant and his bright eyes narrow, leaning forward intensely.")
react("R_M_COUNT", "a", "He glances sideways for half a beat and swallows, jaw tightening as his expression turns serious.")
react("R_M_FURY", "a", "He grinds his teeth, nostrils flaring, staring straight back in stung, defiant pride.")
still("VENUE_OPEN", ["venue"],
      "Wide establishing crane shot inside the candlelit 1786 Vienna Imperial Court Opera House at night (Image 1): tiered gilded crimson-velvet opera boxes, "
      "glowing 2700K crystal chandeliers, a crisp 5600K silver spotlight beam illuminating the empty round wooden stage in the center, Viennese fortepiano on the left, "
      "brass organ pipes on the right, and hundreds of 18th-century Viennese aristocrats and musicians packed around the stage; the camera pushes in smoothly at slow speed.",
      frames=124, lora=0.0)
still("STAGE_STANDOFF", ["a_face_clean", "b_face_clean"],
      "Waist-up medium profile two-shot at eye level on the spotlit Vienna opera stage: Wolfgang Amadeus Mozart (Image 1) on the left in his scarlet coat and white powdered wig "
      "steps forward facing right, and Antonio Salieri (Image 2) on the right in his midnight-navy gold-embroidered court coat and dark hair steps forward facing left; "
      "neither is singing yet, mouths firmly closed, locking eyes nose-to-nose across the silver spotlight beam while warm 2700K chandelier bokeh and cheering crowd silhouettes "
      "bounce behind them; handheld 35mm camera slowly arcs a few degrees.",
      frames=124, mic=True)
still("SALIERI_READY", ["b_face_clean", "stage_b"],
      "Tight chest-up medium close-up of Antonio Salieri (Image 1) on the right side of the stage at Cooke Panchro 50mm T2.2 shallow depth of field, warm chandelier bokeh and "
      "brass organ pipes (Image 2) softly blurred behind him: his mouth stays closed in an icy aristocratic smirk as he nods slightly to the heavy boom-bap beat drop, "
      "touching the golden Imperial medallion on his chest with his left hand while holding the chrome microphone low in his right hand.",
      frames=124, mic=True)
still("OPEN", ["a_face_clean", "b_face_clean"],
      "Over-the-shoulder shot at eye level at T2.2 shallow depth of field, handheld: the blurred dark chestnut hair and midnight-navy gold-embroidered shoulder of Antonio Salieri "
      "(Image 2) fill the right foreground, and beyond him Wolfgang Amadeus Mozart (Image 1) stands chest-up on the left, facing the "
      "camera, raising his chrome handheld microphone toward his chin with a rebellious cocky grin, mouth closed, warm 2700K crystal chandelier bokeh glowing behind "
      "him; the camera pushes in with small amplitude at slow speed.", frames=124, mic=True)
still("DJ_FRONT", ["dj"],
      "Frontal medium shot of exactly one person, the young 18th-century Viennese court musician DJ (Image 1), alone behind his raised baroque harpsichord turntable booth, scratching a vinyl record with one hand and "
      "pressing one black headphone to his ear with the other, warm amber indicator lamps glowing on the brass mixer, the Viennese crowd silhouettes "
      "bouncing in the candlelit bokeh haze behind him.", frames=124)
still("DJ_HANDS", ["dj"],
      "Low-angle close shot across the turntables of the baroque harpsichord DJ booth (Image 1): the DJ's hands in white lace cuffs scratch a spinning black vinyl record and "
      "ride a brass rotary fader, his gold-embroidered burgundy waistcoat above, warm 2700K chandelier bokeh glowing behind.", frames=124)
still("CROWD_OOH", ["crowd"],
      "" + NOSTAGE + "Close medium shot packed with four or five 18th-century Viennese aristocrats and musicians from the front row (Image 1), their faces large and filling the "
      "16:9 frame at T2.2 shallow depth of field, handheld camera at their eye level, crystal chandeliers blurred into warm golden orbs behind them. They react to a "
      "brutal punchline: one claps both hands over his mouth, one grabs his powdered wig with wide eyes, one doubles over "
      "laughing and waves a rolled music score. Energetic, joyful chaos.")
still("CROWD_CHANT", ["crowd"],
      "" + NOSTAGE + "Close medium shot of the front rows of the Viennese opera crowd (Image 1), handheld at their eye level, faces sculpted by warm "
      "3200K chandelier light: aristocrats and court musicians chant together with raised fists and rolled sheet-music scores pumping in rhythm, mouths wide open, "
      "light stage haze. The camera trucks right with small amplitude at slow speed along the front row.", frames=124)
still("CROWD_STARE", ["crowd"],
      "" + NOSTAGE + "Medium close shot of three Viennese court gentlemen in the front row (Image 1), handheld at their eye level, warm chandelier light: they "
      "look up past the camera in stunned silence, arms folded, one slowly letting out a low whistle and shaking his head.")
still("CROWD_LAUGH", ["crowd"],
      "" + NOSTAGE + "Close shot of one Viennese musician in a velvet coat in the front row (Image 1) throwing his head back and cheering with "
      "wide applause, one fist punching the air, spectators clapping and shouting around him, warm amber chandelier bokeh, handheld.")
still("CURTAIN", ["a_face_clean", "b_face_clean"],
      "The shot starts as a waist-up medium two-shot of Wolfgang Amadeus Mozart (Image 1) on the left in his scarlet coat and Antonio Salieri (Image 2) on "
      "the right in his midnight-navy coat standing side by side on the stage, both facing the camera, both spreading their arms wide to the roaring "
      "opera house, mouths closed, Salieri with a composed triumphant nod and Mozart with a defiant smirk. Then the camera pulls out "
      "and pedestals up with large amplitude at slow speed, rising steadily backward and upward over the heads of the "
      "audience until it holds a high wide shot of the whole candlelit Vienna Imperial Opera House: the two men small in the silver spotlight at the "
      "center of the circular wooden stage, hundreds of cheering Viennese spectators waving scores and fists all around them, gilded fortepiano on the "
      "left, brass organ pipes and Imperial podium on the right. During the last second the camera smoothly decelerates and settles into a "
      "stationary shot.", frames=192, lora=0.0, mic=True)
ids = {c["id"]: c for c in clips}

# ---------------------------------------------------------------- 时间线
CUTAWAYS = [
    ("A03", "A04", "memorized", None, "R_S_SCORE", 0.5),
    ("B03", "B04", "over", None, "R_M_VOTE", 0.01),
    ("A11", "A12", "every", None, "CROWD_STARE", 0.3),
    ("A13", "A13", "poison", None, "R_S_CUP", 0.4),
    ("B10", "B10", "cheat", None, "R_M_COUNT", 0.5),
    ("B11", "B11", "shouted", 0.95, "CROWD_LAUGH", 0.05),
    ("B14", "B14", "legends", None, "R_M_FURY", 0.05),
]
GAPS = {   # 换人空档：(镜头, 入点)，按音乐段落对拍切分
    "A08": [("CROWD_OOH", 1.08), ("DJ_HANDS", 0.1)],
    "B08": [("CROWD_CHANT", 0.2), ("DJ_FRONT", 1.2), ("STAGE_STANDOFF", 2.1), ("CROWD_STARE", 0.2)],
    "A16": [("CROWD_OOH", 1.08), ("DJ_HANDS", 1.2)],
}
first = lip["A01"][0]
if first > 12.0:
    # Track v2 完整 35.27s 歌剧院史诗前奏分镜（严丝合缝卡住弦乐开场 → "Bravo!" 搓碟与合唱 → 独奏小提琴对峙 → Boom-Bap 鼓点进场）
    spans = [
        (0.000, 5.050, "VENUE_OPEN", 0.05),
        (5.050, 7.580, "DJ_HANDS", 0.10),
        (7.580, 11.370, "CROWD_CHANT", 0.10),
        (11.370, 12.635, "CROWD_LAUGH", 0.05),
        (12.635, 13.900, "CROWD_OOH", 1.10),
        (13.900, 17.680, "DJ_FRONT", 0.10),
        (17.680, 22.740, "STAGE_STANDOFF", 0.05),
        (22.740, 25.260, "DJ_HANDS", 2.20),
        (25.260, 30.320, "SALIERI_READY", 0.05),
        (30.320, first, "OPEN", 0.05),
    ]
else:
    spans = [(0.0, round(first * 0.52, 3), "OPEN", 0.05), (round(first * 0.52, 3), first, "DJ_FRONT", 0.05)]
lip_ids = [s[0] for s in SHOTS]
cut_by = {}
for head, line, word, d, sid, inn in CUTAWAYS:
    cut_by.setdefault(head, []).append((word_t(line, word), d, sid, inn))
MIN_ON = 0.8
for k, c in enumerate(lip_ids):
    a0, lwe, _ = lip[c]
    nxt = lip_ids[k + 1] if k + 1 < len(lip_ids) else None
    t0 = spans[-1][1]
    raw_gap = (lip[nxt][0] - (lwe + 0.02)) if (nxt is not None and c in GAPS) else 0.0
    gap_items = GAPS.get(c, []) if raw_gap >= 0.45 else []
    if len(gap_items) == 2 and raw_gap < 0.85:
        gap_items = gap_items[:1]
    gap = bool(gap_items)
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
        n = len(gap_items)
        for j, (sid, inn) in enumerate(gap_items):
            spans.append((round(g0 + (g1 - g0) * j / n, 3), round(g0 + (g1 - g0) * (j + 1) / n, 3), sid, inn))
o0 = spans[-1][1]
if END_T - o0 >= 5.5:
    spans.append((o0, round(o0 + 1.55, 3), "CROWD_CHANT", 1.2))
    spans.append((round(o0 + 1.55, 3), round(o0 + 2.95, 3), "DJ_HANDS", 3.4))
    spans.append((round(o0 + 2.95, 3), END_T, "CURTAIN", 0.2))
elif END_T - o0 >= 1.6:
    spans.append((o0, round(o0 + 0.9, 3), "DJ_HANDS", 1.1))
    spans.append((round(o0 + 0.9, 3), END_T, "CURTAIN", 0.2))
else:
    spans.append((o0, END_T, "CURTAIN", 0.2))
edl = [{"t0": a, "t1": b, "clip": c, "in": i} for a, b, c, i in spans]

# R_S_TUNE：第三段第一句（A09）后半句落在 Salieri 脸上
i9 = next(i for i, x in enumerate(edl) if x["clip"] == "A09")
tc = word_t("A09", "nobody")
x9 = edl[i9]
assert tc - x9["t0"] >= MIN_ON, "A09 before nobody: %.2fs" % (tc - x9["t0"])
edl[i9:i9 + 1] = [{"t0": x9["t0"], "t1": tc, "clip": "A09", "in": None},
                  {"t0": tc, "t1": x9["t1"], "clip": "R_S_TUNE", "in": 0.4}]

# 若某条非口型素材因 Suno 跳过间奏而未被引用，自动从 clips 清单剔除以免白烧 CCU
used = {x["clip"] for x in edl}
clips = [c for c in clips if c["id"] in used]
ids = {c["id"]: c for c in clips}

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
assert used == set(ids), "unused: %s; undefined: %s" % (set(ids) - used, used - set(ids))
cut_ids = {c[4] for c in CUTAWAYS} | {"R_S_TUNE"}
for w in WORDS:
    if not is_sung(w) or w["t0"] < first or w["t0"] > lip[lip_ids[-1]][1]:
        continue
    x = next((x for x in edl if x["t0"] - 1e-6 <= w["t0"] < x["t1"]), None)
    assert x and (ids[x["clip"]]["kind"] == "rap" or x["clip"] in cut_ids), "word %r at %.2f lands on %s" % (
        w["w"], w["t0"], x and x["clip"])

# ---------------------------------------------------------------- 后期特效
def slot(cid):
    return next((x for x in edl if x["clip"] == cid), None)


fx = [{"type": "flash", "t0": round(grid["beat0"], 3), "t1": round(grid["beat0"] + 0.08, 3), "alpha": 0.7}]
if first > 12.0:
    # 25.26s Boom-Bap 重鼓点落下的瞬间加一道闪白冲击
    fx.append({"type": "flash", "t0": 25.26, "t1": 25.34, "alpha": 0.85})
for rid in ("R_S_TUNE", "R_M_FURY"):
    x = slot(rid)
    if x:
        fx += [{"type": "flash", "t0": x["t0"], "t1": round(x["t0"] + 0.08, 3), "alpha": 0.85},
               {"type": "shake", "t0": x["t0"], "t1": round(x["t0"] + 0.5, 3), "px": 9}]
for sid in ("CROWD_OOH", "CROWD_CHANT", "CURTAIN"):
    x = slot(sid)
    if x:
        fx.append({"type": "flash", "t0": x["t0"], "t1": round(x["t0"] + 0.08, 3), "alpha": 0.8})
fx.append({"type": "punch", "t0": word_t("B16", "widow"), "t1": slot("B16")["t1"], "amount": 0.08})

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
