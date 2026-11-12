# -*- coding: utf-8 -*-
"""Arthur Morgan vs Geralt of Rivia 分镜构建脚本（Realism V3 暖调电影实拍 + 动态运镜拍法）：
  * 右手贴下唇下方 45° 斜握复古镀铬网头手持麦，左手随歌词自由做手势（不拿易漂移的小道具）
  * 一个口型镜头可跨 1～2 句、带真实运镜（ENTER 穿过人群、PUSH 前推、ARC 绕肩、FACE 鼻尖对峙、REVEAL 横摇、ECU、CRASH 急推、LONG）
  * 句中切到对手 / 观众的反应镜头（L-cut），声音不断，切回来还是同一条口型镜头
  * 四段越往后切得越快、贴得越近（前两段进场 + 长镜头，后两段以贴脸对峙为主）
  * 站位固定：Arthur Morgan 在左（黑皮赌徒帽 + 棕皮猎装夹克 · 1899 西部酒馆橡木酒桶侧）、Geralt of Rivia 在右（雪白半束长发 + 凯尔莫罕铆钉皮甲与狼徽 · 1272 诺维格瑞石拱火把与魔药架侧）

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
MAX_FRAMES = 226    # 单条口型镜头上限（F = 17k + 5，226f = 9.42s）

# ---------------------------------------------------------------- 素材校验与现场运镜层配置
for sub in ("work", "refs", "clips"):
    os.makedirs(os.path.join(EP, sub), exist_ok=True)
for f in ("work/lines.json", "work/words_edit.json", "work/grid.json", "work/vocals_final.wav", "work/music_final.wav",
          "work/a_face_clean.png", "work/b_face_clean.png", "work/stage_a.png", "work/stage_b.png",
          "refs/crowd.png", "refs/dj.png", "refs/venue.png"):
    assert os.path.exists(os.path.join(EP, f)), "missing " + f

json.dump({"handheld_px": 10, "drift": 0.04, "margin": 0.06, "whip": True, "whip_secs": 0.06, "contrast": 1.03,
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
    raw = w["w"].strip("!?,.\"'—")
    if w["w"].startswith("["):
        return False
    if raw in ("OOOH", "LEGEND", "RESPECT", "ROUND", "TWO", "BRAVO", "YEAH", "UH", "YO"):
        return False
    return True


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
LR = {"a": ("left", "right"), "b": ("right", "left")}
READ = ", his face and lips large and clearly readable whenever he faces the camera"
HAND = ", shot on a handheld 35mm cinema camera with a subtle natural sway"


def cam(kind, who):
    me, them = LR[who]
    if kind == "ENTER":   # 观众背后穿过人群推到台上
        return ("The camera starts behind the audience at head height: the backs of weathered Stetson cowboy hats, leather vests, medieval hoods and raised wooden tankards of "
                "the packed underground tavern crowd fill the lower half of the frame with the spotlit round dark-wood stage small in the distance, then the "
                "camera pushes in with large amplitude at slow speed, gliding forward between the raised fists and over the "
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
                "between the two men while warm 2700K amber oil-lantern and torch bokeh glows behind them, <Subject 1>'s lips and jaw clearly readable in every frame"
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
                "slow speed, warm 2700K amber lantern and torch bokeh orbs flaring behind his head, his lips large and clearly readable in every frame")
    if kind == "CRASH":   # 从过肩中景急推到大特写
        return ("The camera starts on an over-the-shoulder medium shot: the blurred shoulder and head of "
                "<Subject 2> in the %s foreground, <Subject 1> chest-up on the %s facing the camera, then the camera pushes "
                "in with large amplitude at fast speed past the shoulder, a sudden crash push-in that lands on a tight "
                "close-up where his whole face from brow to chin fills the frame, never closer than that, and shakes "
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


ONSTAGE = (". He stands on top of the raised round dark-wood stage: the cheering tavern crowd silhouettes are on the plank floor below and behind him, lower "
           "than his chest, softly out of focus at T2.2, and nobody stands at his own level except his opponent")
NOSTAGE = ("From the very first frame to the last this is a close shot of the audience only: the camera stands with its back to the stage, so the stage and the two rappers are never in frame. ")
TWO = {"ARC", "FACE", "FACEWIDE", "REVEAL", "CRASH"}
LISTEN = {
    "ARC": " while <Subject 2> stands with his mouth firmly closed, arms relaxed at his side, amber eyes watching him in silence",
    "FACE": " while <Subject 2> keeps his mouth firmly closed and stares back at him without blinking",
    "FACEWIDE": " while <Subject 2> stands with his arms crossed and his mouth firmly closed",
    "REVEAL": " while <Subject 2> listens with his mouth firmly closed, a faint cold smirk",
    "CRASH": " while <Subject 2> stands with his back to the camera in the foreground, motionless",
}

# 每条口型镜头：(首句, 末句, 机位, 另一只手的动作)。麦在右手，动作只用左手。
SHOTS = [
    # ---- 第一段 Arthur Morgan：1899 死亡之眼开场 + 8900万销量 + 昆特牌 & 屋顶萝卜 & 草叉正史暴击
    ("A01", "A02", "ENTER", "aiming two left fingers forward in a sharp gunslinger draw onto Geralt's chest, then sweeping his free left arm wide across the roaring tavern hall"),
    ("A03", "A04", "PUSH", "pointing off into the frozen distance with furrowed brow, then fanning his free left fingers out like a hand of Gwent cards with a mocking cowboy grin"),
    ("A05", "A06", "ARC", "patting his buckskin chest proudly with his free left palm, then pointing his left index finger straight up toward the rafters laughing at a horse on a roof"),
    ("A07", "A07", "ECU", "dropping his free left palm sharply downward a few inches right into the lens to mock a tiny four-foot porch fall"),
    ("A08", "A08", "FACE", "thrusting three spread left fingers forward between their faces like a peasant's pitchfork with ruthless outlaw grit"),
    # ---- 第二段 Geralt of Rivia：Wind's howling 切黑肺 + 达奇画饼大溪地 + 酒馆喊 Lenny & 唐斯现世报 + GOTY 绝杀
    ("B01", "B02", "ENTER", "cupping his free left hand lightly in the air to feel the howling wind, then holding up two fingers and shaking his head with icy Witcher disdain"),
    ("B03", "B04", "LONG", "spreading his free left palm grandly to mock Dutch's Tahiti speeches, then tilting his head with a cold dry smirk of mock pity"),
    ("B05", "B06", "WHIP", None),
    ("B07", "B07", "CRASH", "lifting his free left hand high above his white hair like hoisting the Game of the Year crown"),
    ("B08", "B08", "FACE", "chopping his free left hand decisively downward right in Arthur's face with cold monster-hunter authority"),
    # ---- 第三段 Arthur Morgan：双女术士独角兽手铐 + 开箱点蜡烛名梗 + 剧版崩盘 + 巫师4希里接棒退居二线
    ("A09", "A09", "ECU", "tapping the left side of his buckskin chest over his heart with a skeptical frontier sneer right into the lens"),
    ("A10", "A10", "REVEAL", "turning his left wrist upward to mock iron handcuffs beside a unicorn with a wry outlaw grin as he steps toward Geralt"),
    ("A11", "A12", "FACE", "miming tossing back toxic potion vials with his left hand, then flicking his left fingers upward like an accidental candle spark"),
    ("A13", "A13", "TQ", "placing his free left hand firmly over his bandolier and heart with raw weathered outlaw conviction"),
    ("A14", "A14", "CRASH", "slicing his free left hand sideways across the air in a ruthless director's cut cancellation gesture"),
    ("A15", "A15", "FACEWIDE", "tipping the front brim of his black leather gambler's hat lightly with two left fingers across the spotlight"),
    ("A16", "A16", "LONG", "jerking his free left thumb sideways to usher the White Wolf off the stage, chin held high"),
    # ---- 第四段 Geralt of Rivia：白鸦葡萄园传承 + 双神级DLC暴打R星弃养 + 60帧vs锁30帧玩家葬礼 + 抛硬币落日绝杀
    ("B09", "B09", "TQ", "tapping the gleaming silver Wolf medallion on his chest with two left fingers, jaw set with fierce pride"),
    ("B10", "B10", "FACE", "raising his free left hand smoothly between them as if swirling a goblet of crimson Toussaint vineyard wine"),
    ("B11", "B12", "LONG", "holding up two steady left fingers for two expansion crowns, then sweeping his flat left palm sideways in a ruthless Rockstar axe slash"),
    ("B13", "B13", "ECU", "flicking his free left fingers rapidly forward into the lens to contrast silky sixty-frame motion with a frozen thirty"),
    ("B14", "B14", "FACE", "lowering his head briefly in mock mourning with his left hand over his chest while staring nose-to-nose into Arthur's eyes"),
    ("B15", "B15", "FACEWIDE", "drawing an imaginary silver sword diagonal across the air between them with lethal Witcher precision"),
    ("B16", "B16", "CRASH", "flipping an imaginary coin upward with his left thumb, then pointing his left index finger dead-center into the camera lens"),
]


def fit(dur):
    need = math.ceil((dur + 0.35) * FPS)
    k = max(4, math.ceil((need - 5) / 17))
    f = 17 * k + 5
    assert f <= MAX_FRAMES, "clip of %.2fs needs %d frames" % (dur, f)
    return f


def ts(t):
    return "00:%06.3f" % t


def whip_prompt(who, a0, a1, text, frames, L_pre=0.0):
    """一条里两个镜头，甩镜落到对手脸上，后半段唱的人不在画面里（Realism V3 双色温 + T2.2 浅景深协议）。"""
    me, them = (A, B) if who == "a" else (B, A)
    my, their = LR[who]
    v_end = min(frames / FPS - 0.05, L_pre + a1 - a0)
    cut = round(L_pre + word_t("B06", "Beat") - a0, 2)
    return (
        "subject_definitions:\n"
        "<Subject 1> is %s (%s) from <Picture 1>, real human skin with matte pores and zero plastic sheen.\n"
        "<Subject 2> is %s (%s) from <Picture 2>, real human skin with matte pores.\n"
        "<Picture 3> is the medieval Novigrad stone-and-torch side of the underground tavern arena behind <Subject 1> in [Shot 1]: glowing amber potion flasks, "
        "warm 2700K wall torches and softly blurred cheering tavern spectators below.\n"
        "<Audio 1> is the target rap vocal track for <Subject 1>, providing his exact vocal timbre (%s) and "
        "syllable-by-syllable rhythm during %s–%s, followed by silence.\n\n"
        "summary:\n[reference generation + audio reuse] Inside %s, <Subject 1> performs an energetic English battle-rap "
        "couplet synced syllable-by-syllable to <Audio 1>, holding the %s just below his lower lip angled upward at 45 degrees "
        "near the bottom edge of the frame, across 2 shots, with <Subject 2> listening in silence, while %s.\n\n"
        "retention_analysis:\n"
        "<Subject 1> (appears in [Shot 1]): fully_preserved - Strictly preserve exact facial bone structure, snow-white half-tied hair, amber cat eyes, left-brow scar, "
        "silver Wolf medallion and dark studded leather armor from <Picture 1> with authentic matte skin.\n"
        "<Subject 2> (appears in [Shot 2]): fully_preserved - Strictly preserve exact weathered facial structure, worn black leather gambler's hat tilted back, short sandy beard clear of lips, "
        "and tan buckskin leather gunslinger jacket from <Picture 2>, keeping his mouth closed in silent listening throughout this clip.\n"
        "Background (appears in [Shot 1]): reference - Keep the stage environment of <Picture 3> softly out of focus at Cooke Panchro T2.2 "
        "shallow depth of field behind <Subject 1> with warm 2700K torch bokeh orbs while the cheering crowd silhouettes bounce.\n"
        "<Audio 1>: fully_copy - Reused 1:1 as the target vocal track; while <Subject 1>'s face is on screen his lip "
        "movements, jaw openings and syllable articulation are synchronized directly to <Audio 1>; after the camera leaves "
        "him the same vocal continues uninterrupted from off screen.\n\n"
        "detailed_description:\n"
        "r34l1sm, Facial Realism, authentic live-action 35mm concert documentary film shot on ARRI Alexa Mini LF with Cooke Panchro T2.2 prime lens on Kodak Vision3 500T film, "
        "natural matte human skin texture with real pores, zero oily shine, %s. Both shots are in the same underground timber-and-stone tavern rap arena: warm 2700K lanterns and torches, "
        "light hearth smoke, cheering cowboy and tavern crowd silhouettes packed below the stage. "
        "[Shot 1] From the very first frame, during %s–%s, the camera holds a chest-up three-quarter medium close-up of "
        "<Subject 1> standing on the raised stage, on the %s half of the frame, his face and lips large and readable, "
        "never a wide shot of the stage, holding the %s in his right hand an inch below his lower lip angled upward at 45 degrees (never occluding his lips), "
        "with <Picture 3> blurred into T2.2 bokeh behind him, rapping with intense brow and cheek articulation synced syllable-by-syllable "
        "to <Audio 1>, raising his free left hand in a mocking drunken tavern toast toward screen-%s; at "
        "the end of this shot the camera pans %s with large amplitude at fast speed, a whip pan with heavy motion blur. "
        "[Shot 2] At %s, the whip pan lands on a new shot. During %s–%s, the camera holds a tight chest-up medium close-up "
        "of <Subject 2> standing on the %s side of the stage with warm 2700K amber saloon oil-lantern bokeh blurred behind him at T2.2, facing "
        "the camera beneath his black leather hat brim, mouth firmly closed, jaw clenching hard, his weathered blue-green eyes darkening in stung silence at the Thomas Downes karma line while <Subject 1>'s voice "
        "continues from off screen. The lyric sung across the whole clip: <d>[English]%s</d> No subtitles, no on-screen "
        "text.\n\n"
        "overall_soundscape:\nClear, punchy foreground rap vocal performance from <Subject 1> during %s–%s synced 1:1 to "
        "<Audio 1> in %s, continuous across the cut.\n\n"
        "non_diegetic_music:\nN/A — <Audio 1> is directly reused 1:1 as the target vocal track."
        % (me["name_en"], me["look"], them["name_en"], them["look"], me["voice"], ts(L_pre), ts(v_end),
           e["venue_en"], MIC, CROWD, e["light_en"],
           ts(L_pre), ts(cut), my, MIC, their, their, ts(cut + 0.2), ts(cut + 0.2), ts(v_end), their, text,
           ts(L_pre), ts(v_end), e["arena_sound_en"])).replace(
        "[Shot 1] From the very first frame, during",
        "[Shot 1] During %s–%s, before he starts rapping, his mouth stays closed while the camera pushes in from a wide "
        "view of the stage and settles on him. Then, during" % (ts(0), ts(L_pre)) if L_pre else "[Shot 1] During").replace(
        ", never a wide shot of the stage," if L_pre else "@@", ",")


clips, lip = [], {}
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
        if kind == "ENTER":
            clip.update(wide=True, image_keys=[me_k], closeup_lora=0.0)
        else:
            clip.update(bg=plate, image_keys=[me_k] + ([them_k] if two else []) + [plate])
        if two:
            clip.update(listener_side=SIDE["b" if who == "a" else "a"], listener=LISTEN[kind])
        if kind in ("ECU", "CRASH"):
            clip["lens"] = "28mm wide-angle"
        if kind in ("PUSH", "ARC", "CRASH"):
            clip["closeup_lora"] = 0.2
        if c0 == "A14":
            clip.update(closeup_lora=0.0, lens="35mm")
    clips.append(clip)
    lip[c0] = (a0, lw_end[c1], covered)

# ---------------------------------------------------------------- 非口型镜头
IMG = {
    "a_face_clean": "Arthur Morgan (keep his exact rugged 36-year-old sun-weathered face, piercing blue-green eyes, worn black leather gambler's hat with braided rope band tilted slightly back, "
                    "short sandy-brown beard clear of lips, tan buckskin leather gunslinger jacket over slate-blue shirt, black neckerchief and leather bandolier)",
    "b_face_clean": "Geralt of Rivia (keep his exact rugged chiseled warrior face, snow-white half-tied hair, amber-gold cat eyes, vertical left-brow scar, "
                    "short silver-white stubble clear of lips, dark studded Kaer Morhen leather armor with chainmail shoulders, silver Wolf medallion and twin sword hilts behind right shoulder)",
    "stage_a": "Arthur's left 1899 saloon side of the underground tavern arena as seen from the stage (softly blurred brass oil-lantern glow, "
               "whiskey barrels and cheering cowboy crowd silhouettes)",
    "stage_b": "Geralt's right 1272 Novigrad side of the underground tavern arena as seen from the stage (softly blurred flickering wall torchlight, "
               "amber potion flask glow and cheering medieval tavern crowd silhouettes)",
    "venue": "the packed underground timber-and-stone tavern rap battle arena at night with an empty spotlit central round stage, 1899 Wild West saloon side on the left, 1272 medieval Novigrad stone-and-torch side on the right",
    "crowd": "the roaring underground tavern crowd of " + e["commoners_en"],
    "dj": "the charismatic frontier-tavern hip-hop DJ in flat-brim gambler hat, dark leather vest and brass-and-leather headphones at his raised dual-turntable booth",
}
VENUE_PLAIN = e["venue_en"].split("; the two rappers")[0]
SEAMLESS = ("Authentic live-action 35mm cinema shot on ARRI Alexa Mini LF with Cooke Panchro T2.2 lens on Kodak Vision3 500T film, "
            "natural matte human skin with fine pores (zero plastic sheen). Setting: " + e["venue_en"] + ". The crowd are " + e["commoners_en"]
            + ". Lighting: " + e["light_en"] + ". Whenever the crowd is in frame, " + CROWD + ".")
SEAMLESS_SOLO = ("Authentic live-action 35mm cinema shot on ARRI Alexa Mini LF with Cooke Panchro T2.2 lens on Kodak Vision3 500T film, "
                 "natural matte human skin with fine pores (zero plastic sheen). Setting: "
                 + VENUE_PLAIN.split(", and a raised round dark-wood stage")[0] + ". The crowd are " + e["commoners_en"]
                 + ". Lighting: " + e["light_en"] + ". Whenever the crowd is in frame, " + CROWD + ".")
RULES_SOLO = ("Keep the face, hairstyle, facial hair, clothing and colors exactly as in the reference images. There is no stage, no "
              "spotlit platform and no performer anywhere in the background of this shot. No subtitles, no on-screen text, "
              "no logos, no watermark.")
RULES_BASE = ("Keep every character's face, hairstyle, facial hair, clothing and colors exactly as in their reference images. Arthur Morgan "
              "always stands on the left side of the stage in his black leather gambler's hat and tan buckskin jacket, Geralt of Rivia on the right in his "
              "snow-white half-tied hair, dark studded leather armor and silver Wolf medallion. Whenever Arthur or Geralt is in frame he stands on top of the raised round "
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


def react(sid, who, act, frames=STILL_FRAMES):
    name, keys = (("Arthur Morgan", ["a_face_clean", "stage_a"]) if who == "a" else ("Geralt of Rivia", ["b_face_clean", "stage_b"]))
    still(sid, keys, "From the very first frame to the last, the camera holds a tight head-and-shoulders "
                     "close-up of %s (Image 1) alone at Cooke Panchro 50mm T2.2 shallow depth of field, frontal, at eye level: his face fills the upper two thirds of the "
                     "frame, his hands and arms are out of frame, and %s (Image 2) glow softly blurred into warm 2700K bokeh orbs behind him, never "
                     "a sharp wall of tiny faces. He is listening to his opponent, not rapping: his "
                     "mouth stays firmly closed the whole time. %s" % (
                         name, "the warm brass oil-lantern bokeh of his saloon side of the tavern" if who == "a" else
                         "the warm flickering torch and amber potion bokeh of his medieval side of the tavern", act), frames=frames)


react("R_G_GWENT", "b", "One scarred pale eyebrow slowly rises and his amber cat eyes narrow with a dry deadpan Witcher half-smirk, nodding slightly on the beat.")
react("R_G_UNICORN", "b", "His deadpan expression flickers for half a beat, jaw tightening slightly as his amber eyes glint sharply under the silver spotlight.")
react("R_G_SHOW", "b", "He exhales slowly through his nose and shakes his white-haired head once in cold monster-hunter disdain, mouth firmly closed.")
react("R_A_TAHITI", "a", "His weathered outlaw smirk vanishes beneath his black leather hat brim and a muscle twitches in his bearded jaw, glaring straight ahead.", frames=90)
react("R_A_DLC", "a", "He glances sideways for half a beat and swallows hard, jaw clenching tight beneath his hat brim as his blue-green eyes turn ice-cold.", frames=90)
react("R_A_FURY", "a", "He grinds his teeth, nostrils flaring, staring straight back in stung, defiant frontier outlaw pride.", frames=107)

still("VENUE_OPEN", ["venue"],
      "Wide establishing crane shot inside the packed timber-and-stone underground tavern rap battle arena at night (Image 1): glowing 2700K wrought-iron candle chandeliers and brass oil lanterns overhead, "
      "a crisp 5600K silver spotlight beam illuminating the empty round dark-wood stage in the center, 1899 Wild West saloon whiskey barrels and pine walls on the left, "
      "1272 medieval Novigrad stone arches, wall torches and glowing potion flasks on the right, and hundreds of cowboys and tavern-goers packed around the stage; the camera pushes in smoothly at slow speed.",
      frames=124, lora=0.0)
still("STAGE_STANDOFF", ["a_face_clean", "b_face_clean"],
      "Waist-up medium profile two-shot at eye level on the spotlit underground tavern stage: Arthur Morgan (Image 1) on the left in his black leather gambler's hat and tan buckskin jacket "
      "steps forward facing right, and Geralt of Rivia (Image 2) on the right with his snow-white hair, silver Wolf medallion and studded leather armor steps forward facing left; "
      "neither is singing yet, mouths firmly closed, locking eyes nose-to-nose across the silver spotlight beam while warm 2700K lantern and torch bokeh and cheering crowd silhouettes "
      "bounce behind them; handheld 35mm camera slowly arcs a few degrees.",
      frames=141, mic=True)
still("OPEN", ["a_face_clean", "b_face_clean"],
      "Over-the-shoulder shot at eye level at T2.2 shallow depth of field, handheld: the blurred snow-white half-tied hair and chainmail-and-leather shoulder with twin sword hilts of Geralt of Rivia "
      "(Image 2) fill the right foreground, and beyond him Arthur Morgan (Image 1) stands chest-up on the left in his black leather hat and tan buckskin jacket, facing the "
      "camera, raising his chrome handheld microphone toward his chin with a stoic outlaw smirk, mouth closed, warm 2700K saloon lantern bokeh glowing behind "
      "him; the camera pushes in with small amplitude at slow speed.", frames=124, mic=True)
still("DJ_FRONT", ["dj"],
      "Frontal medium shot of exactly one person, the charismatic frontier-tavern hip-hop DJ (Image 1), alone behind his raised rustic timber-and-iron dual-turntable booth, scratching a vinyl record with one hand and "
      "pressing one brass-and-leather headphone cup to his ear with the other, warm amber VU meters glowing on the mixer, cheering crowd silhouettes "
      "bouncing in the lantern bokeh haze behind him.", frames=141)
still("DJ_HANDS", ["dj"],
      "Low-angle close shot across the direct-drive turntables of the rustic timber-and-iron DJ booth (Image 1): the DJ's hands scratch a spinning black 12-inch vinyl record and "
      "snap the battle mixer crossfader, his dark leather vest above, warm 2700K lantern bokeh glowing behind.", frames=158)
still("CROWD_OOH", ["crowd"],
      "" + NOSTAGE + "Close medium shot packed with four or five frontier cowboys in Stetsons and medieval tavern patrons from the front row (Image 1), their faces large and filling the "
      "16:9 frame at T2.2 shallow depth of field, handheld camera at their eye level, brass lanterns and torches blurred into warm golden orbs behind them. They react to a "
      "brutal punchline: one cowboy grabs the brim of his Stetson with wide eyes, a bearded tavern patron claps a hand over his mouth, another leans back "
      "laughing and raising a wooden tankard in the air. Energetic, joyful chaos.", frames=90)
still("CROWD_CHANT", ["crowd"],
      "" + NOSTAGE + "Close medium shot of the front rows of the underground tavern crowd (Image 1), handheld at their eye level, faces sculpted by warm "
      "3200K lantern and torch light: cowboys in leather vests and Stetsons alongside hooded townsfolk chant together with raised fists and wooden tankards pumping in rhythm on every boom-bap beat, mouths wide open, "
      "light hearth smoke. The camera trucks right with small amplitude at slow speed along the front row.", frames=141)
still("CROWD_STARE", ["crowd"],
      "" + NOSTAGE + "Medium close shot of three rugged cowboys and tavern-goers in the front row (Image 1), handheld at their eye level, warm golden lantern light: they "
      "look up past the camera in stunned appreciation, arms folded, one slowly nodding hard under his Stetson hat.", frames=141)
still("CROWD_LAUGH", ["crowd"],
      "" + NOSTAGE + "Close shot of one weathered cowboy and a tavern bard in the front row (Image 1) throwing their heads back and laughing with "
      "hype applause, fists and hats punching the air, spectators cheering and bouncing around them, warm amber lantern bokeh, handheld.", frames=107)
still("CURTAIN", ["a_face_clean", "b_face_clean"],
      "The shot starts as a waist-up medium two-shot of Arthur Morgan (Image 1) on the left in his black leather gambler's hat and buckskin jacket and Geralt of Rivia (Image 2) on "
      "the right with his snow-white hair and studded Wolf armor standing side by side on the stage, both facing the camera, both raising their arms to salute the roaring "
      "underground tavern hall, mouths closed, Arthur tipping a respectful outlaw nod and Geralt giving a rare faint warrior smirk. Then the camera pulls out "
      "and pedestals up with large amplitude at slow speed, rising steadily backward and upward over the heads of the "
      "audience until it holds a high wide shot of the whole timber-and-stone tavern arena: the two men small in the silver spotlight at the "
      "center of the circular wooden stage, hundreds of cheering cowboys and medieval townsfolk waving hats and tankards all around them, saloon whiskey barrels on the "
      "left, medieval stone torches and potion shelves on the right. During the last second the camera smoothly decelerates and settles into a "
      "stationary shot.", frames=192, lora=0.0, mic=True)
ids = {c["id"]: c for c in clips}

# ---------------------------------------------------------------- 时间线
CUTAWAYS = [
    ("A03", "A04", "another", None, "R_G_GWENT", 0.45),
    ("B03", "B04", "feel", None, "CROWD_OOH", 2.45),
    ("A11", "A12", "candlesticks", None, "CROWD_STARE", 3.10),
    ("A13", "A13", "pure", None, "R_G_SHOW", 0.40),
    ("B10", "B10", "I", None, "R_A_DLC", 0.05),
    ("B11", "B11", "crowns", 0.90, "CROWD_LAUGH", 2.95),
    ("B13", "B13", "they", None, "R_A_FURY", 1.60),
    ("B14", "B14", "studio", None, "CROWD_STARE", 4.50),
]
GAPS = {   # 换人空档：(镜头, 入点)，全部保证同素材多处使用入点区间零重叠且避开内部硬切與空舞台穿帮
    "A08": [("CROWD_OOH", 0.20), ("DJ_HANDS", 2.55)],
    "B08": [
        ("CROWD_CHANT", 0.15),
        ("DJ_FRONT", 0.15),
        ("OPEN", 1.75),
        ("CROWD_LAUGH", 0.15),
        ("STAGE_STANDOFF", 1.25),
        ("CROWD_STARE", 0.15),
    ],
    "A16": [("CROWD_OOH", 1.40), ("DJ_HANDS", 3.85)],
}
first = lip["A01"][0]
if first >= 8.0:
    # 4 小节 10.03s 西部滑棒吉他×鲁特琴开场分镜：全景推进 + 搓碟（4.9s标题卡淡出）→ 两人登台对峙 → 过肩举麦 + DJ 控台 + 搓碟落拍起唱
    t_b1 = round(first * 0.25, 3)
    t_b2 = round(min(4.90, first * 0.50), 3)
    spans = [
        (0.000, t_b1, "VENUE_OPEN", 0.05),
        (t_b1, t_b2, "DJ_HANDS", 0.10),
        (t_b2, 6.150, "STAGE_STANDOFF", 0.05),
        (6.150, 7.580, "OPEN", 0.10),
        (7.580, 8.780, "DJ_FRONT", 4.55),
        (8.780, first, "DJ_HANDS", 5.15),
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
    spans.append((o0, round(o0 + 2.30, 3), "CROWD_CHANT", 2.95))
    spans.append((round(o0 + 2.30, 3), round(o0 + 4.50, 3), "DJ_FRONT", 2.95))
    spans.append((round(o0 + 4.50, 3), END_T, "CURTAIN", 2.10))
elif END_T - o0 >= 1.6:
    spans.append((o0, round(o0 + 0.9, 3), "DJ_HANDS", 5.20))
    spans.append((round(o0 + 0.9, 3), END_T, "CURTAIN", 2.92))
else:
    spans.append((o0, END_T, "CURTAIN", 2.92))
edl = [{"t0": a, "t1": b, "clip": c, "in": i} for a, b, c, i in spans]

# R_G_UNICORN：第三段第一句（A09）后半句落在 Geralt 脸上
i9 = next(i for i, x in enumerate(edl) if x["clip"] == "A09")
tc = word_t("A09", "quit")
x9 = edl[i9]
assert tc - x9["t0"] >= MIN_ON, "A09 before quit: %.2fs" % (tc - x9["t0"])
edl[i9:i9 + 1] = [{"t0": x9["t0"], "t1": tc, "clip": "A09", "in": None},
                  {"t0": tc, "t1": x9["t1"], "clip": "R_G_UNICORN", "in": 0.40}]

# 避开 B03 首帧远景闪帧（@0.00s）：将 B01->B03 切点顺延 0.032s 至 38.046s（B03 入点 v=0.08s，仍在首词发音点）
ib3 = next(i for i, x in enumerate(edl) if x["clip"] == "B03")
assert edl[ib3 - 1]["clip"] == "B01"
edl[ib3 - 1]["t1"] = edl[ib3]["t0"] = 38.046

# 避开 B05 预滚切镜点（v=2.958s -> t=43.54s）：让前一条 CROWD_OOH 顺延至 43.62s（"Lenny!" 前 0.04s），B05 直接切入杰洛特近景
ib5 = next(i for i, x in enumerate(edl) if x["clip"] == "B05")
assert edl[ib5 - 1]["clip"] == "CROWD_OOH"
edl[ib5 - 1]["t1"] = edl[ib5]["t0"] = 43.620

# 避开 B11 预滚切镜点（v=2.667s -> t=96.84s）：让前一条 R_A_DLC 顺延 0.14s 至 96.88s（in=0.05..0.79s 全实脸），B11 直接切入近景特写
ib11 = next(i for i, x in enumerate(edl) if x["clip"] == "B11")
assert edl[ib11 - 1]["clip"] == "R_A_DLC"
edl[ib11 - 1]["t1"] = edl[ib11]["t0"] = 96.880

# L-cut 反应桥接：B07 句尾 "called the crown" 切 Arthur 咬牙实脸特写（R_A_FURY 无重叠前段），正切 B08 双人贴脸
ib7 = next(i for i, x in enumerate(edl) if x["clip"] == "B07")
assert edl[ib7 + 1]["clip"] == "B08"
xb7, xb8 = edl[ib7], edl[ib7 + 1]
t_b7_cut, t_b8_in = round(word_t("B07", "called"), 3), round(xb8["t0"] + 0.36, 3)
edl[ib7:ib7 + 2] = [
    {"t0": xb7["t0"], "t1": t_b7_cut, "clip": "B07", "in": None},
    {"t0": t_b7_cut, "t1": t_b8_in, "clip": "R_A_FURY", "in": 0.55},
    {"t0": t_b8_in, "t1": xb8["t1"], "clip": "B08", "in": None},
]

# 若某条非口型素材未被引用，自动从 clips 清单剔除以免白烧 CCU
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
        assert x["in"] + d <= c["frames"] / FPS - 0.05, "%s: in %.2f + %.2fs > clip (%.2fs)" % (x["clip"], x["in"], d, c["frames"] / FPS)
assert used == set(ids), "unused: %s; undefined: %s" % (set(ids) - used, used - set(ids))
cut_ids = {c[4] for c in CUTAWAYS} | {"R_G_UNICORN", "R_A_TAHITI", "R_A_DLC"}
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
for rid in ("R_G_GWENT", "R_G_UNICORN", "R_G_SHOW"):
    x = slot(rid)
    if x:
        fx.append({"type": "punch", "t0": x["t0"], "t1": x["t1"], "amount": 0.06})
for rid in ("R_G_UNICORN", "R_A_FURY"):
    x = slot(rid)
    if x:
        fx += [{"type": "flash", "t0": x["t0"], "t1": round(x["t0"] + 0.08, 3), "alpha": 0.85},
               {"type": "shake", "t0": x["t0"], "t1": round(x["t0"] + 0.5, 3), "px": 9}]
for sid in ("CROWD_OOH", "CROWD_CHANT", "CURTAIN"):
    x = slot(sid)
    if x:
        fx.append({"type": "flash", "t0": x["t0"], "t1": round(x["t0"] + 0.08, 3), "alpha": 0.8})
fx.append({"type": "punch", "t0": word_t("B16", "sun"), "t1": slot("B16")["t1"], "amount": 0.08})

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
    print("  %6.2f-%6.2f %5.2fs %-14s %s" % (x["t0"], x["t1"], x["t1"] - x["t0"], x["clip"], ids[x["clip"]]["move"]))
