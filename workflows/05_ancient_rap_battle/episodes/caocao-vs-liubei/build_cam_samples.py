# -*- coding: utf-8 -*-
"""运镜能力小样：把原片里带运动的镜头各做一条，摸 H3 在「运镜 + 锁定音频对口型」下能做到什么程度。

生成迷你剧集 samples_cam/（episode.json + work/clips.json + 参考图 + 测试人声），然后：
  python3 run_rap_battle_remote.py episodes/caocao-vs-liubei/samples_cam \
      --runner-args "--lock-strength 1.0 --mic handheld --tag cam1" --no-post

测试人声借用第 2 集的 vocals_final.wav（本集歌词还没定稿，不为小样花 Kie 额度）：
曹操的镜头配拿破仑的句子，刘备的镜头配威灵顿的句子，只看运镜和口型，不看内容。
运镜句式用官方词表：动作 + with small/large amplitude + at slow/fast speed（白皮书 5.5 节）。
"""
import json
import os
import shutil

EP = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(EP, "samples_cam")
SRC = os.path.join(os.path.dirname(EP), "napoleon-vs-wellington", "work")
REFS_TMP = os.environ.get("CAOCAO_REFS_DIR", "/tmp/caocao_refs")

e = json.load(open(os.path.join(EP, "episode.json"), encoding="utf-8"))
L = json.load(open(os.path.join(SRC, "lines.json"), encoding="utf-8"))
L = L if isinstance(L, list) else L["lines"]
LINE = {(l["who"], l.get("n", l.get("line"))): l for l in L}

# 小样按原片走：手持麦、手里不拿道具
e["title"] = "CaoCao_vs_LiuBei_camtest"
e["a"]["look"] = e["a"]["look"].split(", holding ")[0]
e["b"]["look"] = e["b"]["look"].split(", holding ")[0]
e["a"]["prop"], e["b"]["prop"] = "tall black official's cap", "green silk hair cloth"
e["a"]["voice"] = "fiery intense male rapper, commanding tenor voice"   # 实际音轨是拿破仑的声线
e["b"]["voice"] = "cold dry male rapper, deep baritone voice"            # 实际音轨是威灵顿的声线

VENUE, LIGHT, CROWD = e["venue_en"], e["light_en"], e["crowd_motion_en"]
A, B = e["a"], e["b"]
FPS = 24


def span(who, n0, n1):
    """ep2 人声里 who 的第 n0..n1 句：(起, 止, 连起来的歌词)"""
    ls = [LINE[(who, n)] for n in range(n0, n1 + 1)]
    return round(ls[0]["start"] - 0.05, 3), round(ls[-1]["end"] + 0.02, 3), " ".join(l["text"] for l in ls)


def rap(cid, who, n0, n1, frames, cam, action, two=False, listener=None, listener_side=None, wide=False,
        lens=None, lora=None):
    a0, a1, text = span(who, n0, n1)
    assert a1 - a0 + 0.3 <= frames / FPS, (cid, a1 - a0, frames / FPS)
    c = {"id": cid, "kind": "rap", "who": who, "line": n0, "move": "CAM", "text": text, "audio": [a0, a1],
         "lead": 0.0, "frames": frames, "action": action, "two_shot": two, "static": False, "cam": cam,
         "image_keys": [who + "_face_clean"] + (["ba"[who == "b"] + "_face_clean"] if two else [])}
    if listener:
        c["listener"] = listener
    if listener_side:
        c["listener_side"] = listener_side
    if wide:
        c["wide"] = True
    if lens:
        c["lens"] = lens
    if lora is not None:
        c["closeup_lora"] = lora
    return c


def ts(t):
    return "00:0%05.3f" % t


def raw_rap(cid, who, n0, n1, frames, shots, two=True, lora=0.2):
    """多镜头小样：自己写完整的官方六段式提示词。shots = [(t0, t1, 镜头描述, 这一段 <Subject 1> 是否在画面里唱)]"""
    a0, a1, text = span(who, n0, n1)
    total = frames / FPS
    v_end = min(total - 0.05, a1 - a0)
    assert v_end + 0.3 <= total, (cid, v_end, total)
    me, them = (A, B) if who == "a" else (B, A)
    subj = ["<Subject 1> is %s (%s) from <Picture 1>, natural matte skin texture with fine pores." % (me["name_en"], me["look"])]
    ret = ["<Subject 1> (appears in every shot he is framed in): fully_preserved - Strictly preserve exact facial bone "
           "structure, hairstyle, facial hair and outfit from <Picture 1>."]
    if two:
        subj.append("<Subject 2> is %s (%s) from <Picture 2>, natural matte skin texture." % (them["name_en"], them["look"]))
        ret.append("<Subject 2>: fully_preserved - Strictly preserve exact facial structure and outfit from <Picture 2>, "
                   "keeping his mouth closed in silent listening throughout this clip.")
    subj.append("<Audio 1> is the target rap vocal track for <Subject 1>, providing his exact vocal timbre (%s) and "
                "syllable-by-syllable rhythm during %s–%s, followed by silence." % (me["voice"], ts(0), ts(v_end)))
    ret.append("<Audio 1>: fully_copy - Reused 1:1 as the target vocal track; whenever <Subject 1>'s face is on screen "
               "during %s–%s his lip movements, jaw openings and syllable articulation are synchronized directly to "
               "<Audio 1>; when he is off screen or seen from behind, the same vocal continues uninterrupted." % (ts(0), ts(v_end)))
    body = []
    for i, (t0, t1, desc, _sings) in enumerate(shots, 1):
        head = ("[Shot %d] During %s–%s, " % (i, ts(t0), ts(t1))) if i == 1 else \
               ("[Shot %d] At %s, %s During %s–%s, " % (i, ts(t0), desc[0], ts(t0), ts(t1)))
        body.append(head + (desc if i == 1 else desc[1]))
    style = ("r34l1sm, Facial Realism, realistic ARRI Alexa Mini LF 35mm lens cinematography, Kodak Vision3 500T film "
             "look, natural soft matte skin texture with fine pores, zero oily shine, %s. " % LIGHT)
    prompt = (
        "subject_definitions:\n" + "\n".join(subj)
        + "\n\nsummary:\n[reference generation + audio reuse] Inside %s, <Subject 1> performs an energetic English "
          "battle-rap verse synced syllable-by-syllable to <Audio 1>, holding a vintage microphone in his right hand "
          "below his chin, across %d shots%s, while %s.\n\n" % (
              VENUE, len(shots), " with <Subject 2> listening in silence" if two else "", CROWD)
        + "retention_analysis:\n" + "\n".join(ret)
        + "\n\ndetailed_description:\n" + style + " ".join(body)
        + " The lyric sung across the whole clip: <d>[English]%s</d> No subtitles, no on-screen text.\n\n" % text
        + "overall_soundscape:\nClear, punchy foreground rap vocal performance from <Subject 1> during %s–%s synced 1:1 "
          "to <Audio 1> in %s, continuous across every cut.\n\n" % (ts(0), ts(v_end), e["arena_sound_en"])
        + "non_diegetic_music:\nN/A — <Audio 1> is directly reused 1:1 as the target vocal track."
    )
    return {"id": cid, "kind": "rap", "raw": True, "who": who, "line": n0, "move": "CAM", "text": text,
            "audio": [a0, a1], "lead": 0.0, "frames": frames, "prompt": prompt, "closeup_lora": lora,
            "image_keys": [who + "_face_clean"] + (["ba"[who == "b"] + "_face_clean"] if two else [])}


def still(cid, frames, shot, lora=0.0):
    head = ("Image 1 is Cao Cao's face (keep his exact face, narrow eyes, long thin moustache and pointed beard, tall "
            "black official's cap, black robe with dark red borders). Image 2 is Liu Bei's face (keep his exact face, "
            "large earlobes, short moustache and small chin beard, green hair cloth, deep green robe with gold borders).")
    setting = ("Setting: %s, with a cold pale spotlight beam cutting through thick incense smoke onto the circular stone "
               "stage. The crowd are %s. Nobody else stands inside the circle. Lighting: %s, shallow haze, gritty 35mm "
               "film grain; not glossy, not brightly lit. Whenever the crowd is in frame, %s." % (
                   VENUE, e["commoners_en"], LIGHT, CROWD))
    rules = ("Keep every character's face, hairstyle, costume and colors exactly as in their reference images. Each man "
             "holds one vintage chrome microphone in his right hand and nothing else. No subtitles, no on-screen text, "
             "no watermark.")
    return {"id": cid, "kind": "still", "move": "CAM", "frames": frames, "closeup_lora": lora,
            "image_keys": ["a_face_clean", "b_face_clean"],
            "prompt": "\n\n".join([head, "Cinematic photoreal shot, 16:9. " + shot, setting, rules])}


MOUTH = ", his face and lips large and clearly readable whenever he faces the camera"
LISTEN_L = (" while <Subject 2> stands on screen-left with his mouth firmly closed, hands clasped in front of him, "
            "watching him in silence")

clips = [
    # 原片 A2：全身 → 中景的前推，结尾直指镜头
    rap("T01_PUSH", "a", 1, 2, 141,
        "The camera starts on a full-body wide shot of <Subject 1> standing alone in the cold spotlight beam on the "
        "circular stage with the crowd packed around its edge, then the camera pushes in with large amplitude at slow "
        "speed, travelling steadily toward him until it settles on a chest-up medium close-up" + MOUTH,
        "prowling forward one step, then thrusting his free left hand out and pointing straight into the lens",
        lora=0.2),
    # 原片 A1→A2：从观众背后穿过人群推到台上
    rap("T02_CROWDPUSH", "a", 3, 4, 141,
        "The camera starts behind the audience at head height: the backs of heads, topknots and raised fists of the "
        "packed crowd fill the lower half of the frame with the spotlit stage small in the distance, then the camera "
        "pushes in with large amplitude at slow speed, gliding forward between the raised arms and over the shoulders "
        "of the crowd until it reaches the edge of the stage and settles on a knee-up medium shot of <Subject 1>; "
        + CROWD,
        "rapping out toward the crowd with his free left hand chopping the air on the beat", wide=True, lora=0.0),
    # 原片 A3：绕到唱者身后，变成过肩拍听者（官方建议 orbit 拆成 truck + pan）
    rap("T03_ARC", "a", 5, 6, 141,
        "The camera starts on a chest-up medium shot of <Subject 1> from the front as he raps, then the camera trucks "
        "right and pans left with large amplitude at slow speed, moving in an arc shot around his right shoulder, "
        "until it ends as an over-the-shoulder shot from behind him: the back of <Subject 1>'s head and his right "
        "shoulder softly blurred in the right foreground, and <Subject 2> in sharp focus a few steps away on "
        "screen-left, facing the camera",
        "jabbing his free left hand toward his opponent, pointing at him", two=True, listener_side="screen-left",
        listener=LISTEN_L, lora=0.2),
    # 原片 A10 / B14：鼻尖相对的侧面双人，慢推（唱的人在右）
    rap("T04_FACEOFF", "a", 7, 8, 141,
        "The camera holds a tight eye-level profile two-shot of the two men standing face to face, almost nose to "
        "nose, a foot apart: <Subject 1> on screen-right in profile facing left, leaning in and rapping straight "
        "into <Subject 2>'s face, <Subject 2> on screen-left in profile facing right; both from the chest up, and "
        "the camera pushes in with small amplitude at slow speed until their two faces fill the frame, <Subject 1>'s "
        "lips and jaw clearly readable in profile in every frame, handheld camera with a subtle natural sway",
        "leaning into his opponent's face with a wolfish grin, his free left hand low", two=True,
        listener_side="screen-left",
        listener=" while <Subject 2> on screen-left keeps his mouth firmly closed and stares back at him without blinking"),
    # 原片 A10 开头：从单人横摇带出对手
    rap("T05_PANREVEAL", "a", 9, 10, 141,
        "The camera starts on a chest-up three-quarter medium close-up of <Subject 1> alone on the right half of the "
        "frame, facing screen-left as he raps, then the camera pans left with small amplitude at slow speed, revealing "
        "<Subject 2> standing in profile at the left edge of the frame facing right, and settles into a tight profile "
        "two-shot of the two men face to face, <Subject 1>'s lips and jaw clearly readable in every frame",
        "stepping in close and rapping into his opponent's face, chin raised", two=True, listener_side="screen-left",
        listener=" while <Subject 2> on screen-left listens with his mouth firmly closed, a faint calm smile"),
    # 原片 A8：仰拍广角大特写，麦克风压在画面底部
    rap("T06_ECU_LOW", "b", 1, 2, 141,
        "A handheld camera with a wide-angle lens is very close to his face and slightly below chin height, tilted a "
        "few degrees off level, looking up at him: an extreme close-up where his face fills most of the 16:9 frame "
        "and the head of the vintage microphone sits large and soft in the bottom foreground just below his chin; "
        "the camera pushes in with small amplitude at slow speed, the spotlight haze flaring behind his head, his "
        "lips large and clearly readable in every frame",
        "glaring down into the lens, his free left hand rising into the edge of the frame", lens="24mm wide-angle"),
    # 原片 B11：从过肩中景急推到大特写
    rap("T07_CRASH", "b", 3, 3, 90,
        "The camera starts on an over-the-shoulder medium shot: the blurred shoulder and back of the head of "
        "<Subject 2> in the left foreground, <Subject 1> chest-up on the right facing the camera, then the camera "
        "pushes in with large amplitude at fast speed past the shoulder, a sudden crash push-in that lands on an "
        "extreme close-up of <Subject 1>'s face, and shakes slightly as it lands, his lips large and clearly readable",
        "snarling the line, eyes wide, leaning into the lens", two=True, listener_side="screen-left",
        listener=" while <Subject 2> stands with his back to the camera in the left foreground, motionless",
        lens="24mm wide-angle"),
    # 原片 B14：对峙双人里下摇跟手再摇回脸
    rap("T08_TILT", "b", 13, 14, 141,
        "The camera holds a tight profile two-shot of the two men face to face: <Subject 2> on screen-left in profile "
        "facing right, <Subject 1> on screen-right in profile facing left; as <Subject 1> jabs his free left hand "
        "downward, the camera tilts down with small amplitude at fast speed to follow the pointing hand, then tilts "
        "up again and settles back on the two faces, <Subject 1>'s lips and jaw clearly readable in profile",
        "jabbing his free left index finger sharply down toward the ground between them, then raising it up to his "
        "opponent's chest", two=True, listener_side="screen-left",
        listener=" while <Subject 2> on screen-left stands with his arms crossed and his mouth firmly closed"),
    # 原片 A11：10 秒级的正面近景长镜头（这里 8 秒，3 句）
    rap("T09_LONGCU", "b", 9, 11, 192,
        "The camera holds a frontal head-and-shoulders close-up at eye level, shot on a handheld camera with a subtle "
        "natural sway, and pushes in with small amplitude at slow speed across the whole shot; his face fills the "
        "upper two thirds of the 16:9 frame, his lips large and clearly readable in every frame",
        "his free left hand sweeping across the frame twice, then pointing up beside his head on the last line"),
]

# 原片 B5→B6：一条里两个镜头，甩镜转场，后半段唱的人不在画面里
a0, a1, _ = span("b", 5, 6)
d = a1 - a0
clips.append(raw_rap("T10_WHIP", "b", 5, 6, 141, [
    (0.0, 2.4,
     "The camera holds a chest-up three-quarter medium shot of <Subject 1> on the right half of the frame, rapping "
     "with lively syllable-by-syllable lip-sync to <Audio 1>, his free left arm stretched out pointing toward "
     "screen-left at someone off screen; at the end of this shot the camera pans left with large amplitude at fast "
     "speed, a whip pan with heavy motion blur.", True),
    (2.6, min(d, 5.4),
     ("the whip pan lands on a new shot.",
      "the camera holds a static chest-up medium close-up of <Subject 2> standing at the front of the crowd, facing the "
      "camera, mouth firmly closed, a slow cold smirk spreading across his face while <Subject 1>'s voice continues "
      "from off screen."), False),
]))

# 原片 A1→A2→A3：原生多镜头，一条里三个机位，全程同一条人声
a0, a1, _ = span("a", 11, 13)
d = a1 - a0
clips.append(raw_rap("T11_MULTI", "a", 11, 13, 209, [
    (0.0, 1.6,
     "The camera holds a wide shot from behind the audience at head height: backs of heads and raised fists fill the "
     "lower third of the frame, and beyond them <Subject 1> stands full-body in the cold spotlight beam on the stage, "
     "rapping to <Audio 1>, with <Subject 2> standing at the left edge of the stage; the crowd bounces on the beat.",
     True),
    (1.6, 5.0,
     ("the camera cuts to a new angle.",
      "the camera holds a frontal chest-up medium close-up of <Subject 1> and pushes in with small amplitude at slow "
      "speed while he raps with lively, unmistakable syllable-by-syllable lip-sync to <Audio 1> and thrusts his free "
      "left hand toward the lens."), True),
    (5.0, min(d, 8.2),
     ("the camera cuts to a reverse angle.",
      "the camera holds an over-the-shoulder shot from behind <Subject 1>: the back of his head and right shoulder "
      "blurred in the right foreground, and <Subject 2> in sharp focus on screen-left facing the camera, hands clasped, "
      "mouth firmly closed, listening with a faint calm smile while <Subject 1>'s voice continues."), False),
], lora=0.2))

# 原片 E2：两人并肩谢幕，镜头后拉升高到俯瞰全场
clips.append(still("T12_CURTAIN", 192,
    "The shot starts as a waist-up medium two-shot of Liu Bei (Image 2) on the left and Cao Cao (Image 1) on the right "
    "standing side by side on the stage, both facing the camera, both spreading their arms wide and grinning at the "
    "roaring crowd. Then the camera pulls out and pedestals up with large amplitude at slow speed, rising steadily "
    "backward and upward over the heads of the audience until it holds a high wide shot of the whole lantern-lit "
    "courtyard: the two men small in the spotlight at the center of the circular stage, hundreds of cheering people "
    "with raised fists all around them, banners and lanterns along the walls. During the last second the camera "
    "smoothly decelerates and settles into a stationary shot."))

for sub in ("work", "refs", "clips"):
    os.makedirs(os.path.join(OUT, sub), exist_ok=True)
json.dump(e, open(os.path.join(OUT, "episode.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(clips, open(os.path.join(OUT, "work", "clips.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
shutil.copy2(os.path.join(SRC, "vocals_final.wav"), os.path.join(OUT, "work", "vocals_final.wav"))
missing = []
for who in "ab":
    src = os.path.join(REFS_TMP, who + "_face", who + "_face_clean.png")
    if os.path.exists(src):
        shutil.copy2(src, os.path.join(OUT, "work", who + "_face_clean.png"))
    elif not os.path.exists(os.path.join(OUT, "work", who + "_face_clean.png")):
        missing.append(src)
tot = sum(c["frames"] for c in clips)
print("clips: %d, frames: %d (%.1f s)" % (len(clips), tot, tot / FPS))
for c in clips:
    print("  %-14s %-5s %3d f  audio %s" % (c["id"], c["kind"], c["frames"], c.get("audio")))
print("missing refs:", missing or "none")
