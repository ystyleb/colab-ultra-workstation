# -*- coding: utf-8 -*-
"""Napoleon vs Wellington：生成 work/clips.json + work/edl.json + work/fx.json（2 回合 32 句，约 107.5 秒）。

usage: python3 build_storyboard.py

在第 1 集（edison-vs-tesla-full/build_storyboard_full.py）的基础上，按对标视频（对标分析_曹操VS刘备.md）改了 5 处：
1. 后半句切反应（L-cut）：LCUT 里的句子，口型镜头在指定词开头切走，接对手的反应特写，声音继续（音轨来自整首歌）。
   其余句子仍然「唱完才切」，断言兜底。
2. 面对面对峙（FACE）：侧脸、鼻尖相对的双人镜头。站位固定：拿破仑永远在左，威灵顿永远在右（listener_side）。
3. 广角贴脸大特写（ECU）：24mm、手伸向镜头，用在每回合收尾句。
4. 两句一镜的慢推长镜头（LONG）：一个口型片段覆盖两句，约 5 秒，节奏长短交替。
5. 每段首句用观众背影视角的远景（WIDE_POV），铭牌叠在这一句上。
Render with: --fit --lock-strength 1.0 --mic stand --static-cam
"""
import json
import os
import re

EP = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(EP, "work")
e = json.load(open(os.path.join(EP, "episode.json"), encoding="utf-8"))
L = json.load(open(os.path.join(WORK, "lines.json"), encoding="utf-8"))
WORDS = json.load(open(os.path.join(WORK, "words_edit.json"), encoding="utf-8"))
ACT = json.load(open(os.path.join(EP, "line_actions.json"), encoding="utf-8"))
grid = json.load(open(os.path.join(WORK, "grid.json"), encoding="utf-8"))
A, B = e["a"], e["b"]
CROWD = e["crowd_motion_en"]  # 用户反馈：台上唱的时候，台下的人要跟着音乐动
END_T = round(grid["length"], 3)
PRE = 0.08          # 在下一句第一个词前 0.08 秒切
STILL_FRAMES = 73   # 非口型镜头 73 帧 = 3.04 秒
MIN_ON_SINGER = 0.9  # L-cut 前至少在歌手脸上停留的秒数
REACT_IN = 1.15     # 反应镜头入点：H3 开头约 1 秒照着参考图摆拍远景（小样 R_N_CROWN 1.04 s 才切到特写）
# 出片后逐条看帧改的入点：SURVIVED 1.15 s 还在从人群里升起，FIGLEAF 1.4 s 后切成全景
# 重抽的 SEPOY 0-1.55 s 是特写、之后切全景
REACT_IN_BY = {"R_W_SURVIVED": 1.7, "R_N_FIGLEAF": 0.25, "R_W_SEPOY": 0.25}

# ---------------------------------------------------------------- 机位
HAND = (", shot on a handheld camera at shoulder height with a subtle natural sway, slowly arcing a few degrees around "
        "him, his face and lips large and clearly readable in every frame")
CU = ("The camera holds a tight head-and-shoulders close-up at eye level, frontal, his face filling the upper half of "
      "the 16:9 frame") + HAND
TQL = "The camera holds a chest-up medium close-up from a three-quarter angle at eye level from his left side" + HAND
TQR = "The camera holds a chest-up medium close-up from a three-quarter angle at eye level from his right side" + HAND
LOW = ("The camera holds a low-angle chest-up medium close-up looking slightly up at him, the cold spotlight beam "
       "glowing through the smoke at the top of the frame") + HAND
# 第 1 集经验：只写 push-in 会从远景开始；要写明起点「starts on a chest-up medium close-up」
LONG = ("A handheld camera with a subtle natural sway starts on a chest-up medium close-up at eye level and slowly, "
        "steadily creeps closer to a tight head-and-shoulders close-up over the whole shot, his face and lips large and "
        "clearly readable from the first frame")
ECU = ("From the very first frame to the last, a handheld camera with a wide-angle lens is very close to his face, "
       "slightly below eye level, with no wider opening and no zoom: an extreme close-up where his face fills most of the 16:9 frame, his free hand thrusting toward the lens looks huge from "
       "the wide-angle perspective, the spotlight haze flaring behind his head, his lips large and clearly readable in "
       "every frame")
# 拿破仑永远在左、威灵顿永远在右（第 1 集经验：不写死站位，同框镜头里两人会左右互换）
SIDE = {"a": ("screen-left", "facing right"), "b": ("screen-right", "facing left")}


def face_cam(who):
    me_side, me_face = SIDE[who]
    them_side, them_face = SIDE["b" if who == "a" else "a"]
    return ("The camera holds a tight eye-level profile two-shot of the two men standing face to face, almost nose to "
            f"nose, a foot apart: <Subject 1> on {me_side} in profile {me_face}, leaning in and rapping straight into "
            f"<Subject 2>'s face, <Subject 2> on {them_side} in profile {them_face}; both from the chest up, his lips "
            "and jaw clearly readable in every frame, handheld camera with a subtle natural sway")


def wide_pov(who):
    me_half = "left" if who == "a" else "right"
    them_half = "right" if who == "a" else "left"
    return ("A handheld camera with a subtle natural sway holds a wide shot from inside the crowd, behind the audience "
            "at head height: the backs of heads, bearskin hats, shakos and raised fists of the packed crowd fill the "
            f"lower third of the frame, and beyond them on the {me_half} half of the spotlit circular stage <Subject 1> "
            f"raps full-body into the floor-stand microphone while <Subject 2> stands full-body on the {them_half} half; "
            "the whole courtyard rises above them: stone farm walls, flaming torches, French tricolours and golden eagles "
            "on the left, British flags on the right, haze drifting through the spotlight beam; " + CROWD)


# 每句的机位（第 1 集是 8 句一轮的固定轮换；这一集逐句指定，长短交替）
SHOT = {
    "A01": "WIDE", "A02": "LOW", "A03": "LONG", "A05": "CU", "A06": "FACE", "A07": "TQL", "A08": "ECU",
    "B01": "WIDE", "B02": "CU", "B03": "TQR", "B04": "LOW", "B05": "LONG", "B07": "FACE", "B08": "ECU",
    "A09": "WIDE", "A10": "TQR", "A11": "FACE", "A12": "CU", "A13": "LONG", "A15": "LOW", "A16": "ECU",
    "B09": "WIDE", "B10": "TQL", "B11": "CU", "B12": "LOW", "B13": "LONG", "B15": "FACE", "B16": "ECU",
}
MERGED = {"A04": "A03", "B06": "B05", "A14": "A13", "B14": "B13"}  # 并入前一句的长镜头
CAMS = {"CU": CU, "TQL": TQL, "TQR": TQR, "LOW": LOW, "LONG": LONG, "ECU": ECU}

# 后半句切对手反应：句子 -> (从哪个词开始切, 反应镜头 id)
LCUT = {
    "A05": ("sepoy", "R_W_SEPOY"), "A07": ("europe", "R_W_PLATE"),
    "B02": ("by", "R_N_SUNSET"), "B04": ("winter", "R_N_WINTER"), "B08": ("so", "R_N_CROWN"),
    "A10": ("that's", "R_W_SURVIVED"), "A12": ("won", "R_W_FLUKE"),
    "B12": ("people", "R_N_STARE"), "B14": ("fig", "R_N_FIGLEAF"),
}
LCUT_RIDS = {rid for _, rid in LCUT.values()}

# ---------------------------------------------------------------- 词级时间
def norm(w):
    return re.sub(r"[^a-z0-9']", "", w.lower().replace("’", "'"))


def is_sung(w):
    return not w["w"].startswith("[") and not w["w"].strip("!?,.").isupper()


def last_word_end(l, nxt_start):
    ws = [w for w in WORDS if l["start"] - 0.1 <= w["t0"] < nxt_start - 0.05 and is_sung(w)]
    return max(w["t1"] for w in ws)


def word_t(l, word, nxt_start):
    hits = [w["t0"] for w in WORDS if l["start"] - 0.1 <= w["t0"] < nxt_start - 0.05 and norm(w["w"]) == norm(word)]
    assert hits, f"{l['who']}{l['n']}: word '{word}' not found"
    return hits[0]


# ---------------------------------------------------------------- 口型镜头
cid_of = lambda l: ("A" if l["who"] == "a" else "B") + "%02d" % l["n"]
line_by = {cid_of(l): l for l in L}
order = [cid_of(l) for l in L]
nxt_start = {c: (L[i + 1]["start"] if i + 1 < len(L) else END_T) for i, c in enumerate(order)}
lw_end = {c: last_word_end(line_by[c], nxt_start[c]) for c in order}

clips, lip = [], {}  # lip[clip id] = (audio start, last word end of the clip, lines it covers)
for c in order:
    if c in MERGED:
        continue
    l = line_by[c]
    who = l["who"]
    me, them = (A, B) if who == "a" else (B, A)
    covered = [c] + [m for m, head in MERGED.items() if head == c]
    last = covered[-1]
    kind = SHOT[c]
    text = " / ".join(line_by[x]["text"] for x in covered)
    action = ", then ".join(ACT[who][line_by[x]["n"] - 1] for x in covered)
    face_me, face_them = (("a_face_clean", "b_face_clean") if who == "a" else ("b_face_clean", "a_face_clean"))
    plate = "stage_a" if who == "a" else "stage_b"
    clip = {"id": c, "kind": "rap", "who": who, "line": l["n"], "move": "FULL", "text": text,
            "audio": [round(l["start"] - PRE, 3), round(max(line_by[last]["end"], lw_end[last]), 3)], "lead": 0.0,
            "action": action + f", the {me['prop']} stays in his left hand, clearly separate from the microphone stand",
            "two_shot": False, "static": False, "bg": plate, "image_keys": [face_me, plate], "sway": 0.5, "drift": 0.02}
    if kind in CAMS:
        clip["cam"] = CAMS[kind]
        if kind in ("LONG",):
            clip["drift"] = 0.0
        if kind == "ECU":
            clip.update(lens="24mm wide-angle", drift=0.0)
    elif kind == "FACE":  # 两人同框：写清各自拿什么道具，站位固定
        clip.update(two_shot=True, cam=face_cam(who), image_keys=[face_me, face_them, plate],
                    listener_side=SIDE["b" if who == "a" else "a"][0],
                    action=action + f", holding only his own {me['prop']} low in his left hand",
                    listener=f" while <Subject 2> holds only his own {them['prop']} at his side, mouth firmly closed, "
                             "glaring back at him")
    elif kind == "WIDE":  # 整个院子 + 两人全身；用 venue.png 做环境参考，关掉特写 LoRA
        # 不给场景图：H3 会把参考图里的观众照抄成静止画面（小样 A01：观众帧间差 1.36～2.03，去掉场景图后 5.07）
        clip.pop("bg")
        clip.update(two_shot=True, wide=True, cam=wide_pov(who), image_keys=[face_me, face_them],
                    closeup_lora=0.0, action=action + f", holding his own {me['prop']} in his left hand",
                    listener=f" while <Subject 2> stands across the stage holding his own {them['prop']} at his side, "
                             "arms still and mouth closed, watching him")
    clips.append(clip)
    lip[c] = (clip["audio"][0], lw_end[last], covered)

# ---------------------------------------------------------------- 非口型镜头
IMG = {
    "a_face_clean": "Napoleon Bonaparte's face (keep his exact face, sideways black bicorne with tricolour cockade, grey "
                    "greatcoat over a dark green uniform with red collar, silver star on his chest)",
    "b_face_clean": "the Duke of Wellington's face (keep his exact face, hooked nose, curly greying hair and sideburns, "
                    "front-to-back black bicorne, scarlet field marshal's coat with gold epaulettes, white cravat)",
    "stage_a": "the French side of the arena behind Napoleon (tricolour banners, golden eagle standards, torches)",
    "stage_b": "the British side of the arena behind Wellington (Union flags, scarlet colours, stacked muskets, torches)",
    "venue": "the venue, " + e["venue_en"],
    "crowd": "the crowd of " + e["commoners_en"],
    "dj": "the DJ, a young man in a short blue drummer-boy military jacket with headphones, at his turntables built on "
          "a bronze field cannon and powder barrels",
}
SEAMLESS = (
    "This shot must cut seamlessly with the rest of the film: same venue, same cold spotlight beam from above as the key "
    "light, 35-50mm lens look. Setting: " + e["venue_en"] + ", with a cold white-blue spotlight beam cutting through "
    "thick cannon smoke onto the circular stage. The crowd are " + e["commoners_en"] + ". Nobody else stands inside the "
    "circle: the crowd is packed only beyond its edge, every person dressed differently. Low-key cinematic lighting with "
    "deep shadows, thick haze, high contrast, warm orange torchlight against the cold blue-white spotlight, shallow depth "
    "of field, gritty 35mm film grain; not glossy, not brightly lit. Whenever the crowd is in frame, " + CROWD + ".")
RULES = (
    "Keep every character's face, hairstyle, costume and colors exactly as in their reference images. Napoleon's "
    f"{A['prop']} is always {A['prop_desc']}. Wellington's {B['prop']} is always {B['prop_desc']}. The golden laurel wreath "
    "belongs only to Napoleon, the spyglass only to Wellington. Napoleon always stands on the left side of the stage with the "
    "French flags behind him, Wellington on the right with the British flags behind him. Nobody holds a microphone; the "
    "two vintage chrome microphones stand on floor stands at the edge of the circle. No subtitles, no on-screen text, no "
    "logos, no watermark.")


def still(sid, keys, shot, frames=STILL_FRAMES, lora=None):
    head = " ".join(f"Image {i} is {IMG[k]}." for i, k in enumerate(keys, 1))
    c = {"id": sid, "kind": "still", "move": "V2", "frames": frames, "image_keys": keys,
         "prompt": "\n\n".join([head, "Cinematic photoreal shot, 16:9. " + shot, SEAMLESS, RULES])}
    if lora is not None:
        c["closeup_lora"] = lora
    clips.append(c)


def react(sid, who, act):
    """对手的反应特写：L-cut 用，嘴一直闭着。"""
    name = "Napoleon Bonaparte" if who == "a" else "the Duke of Wellington"
    side = "French" if who == "a" else "British"
    keys = ["a_face_clean", "stage_a"] if who == "a" else ["b_face_clean", "stage_b"]
    still(sid, keys, f"Close-up of {name} (Image 1), frontal, eye level, handheld with a subtle natural sway, the {side} "
                     f"side of the arena (Image 2) blurred behind him. He is listening to his opponent, not rapping: his "
                     f"mouth stays firmly closed the whole time. {act}")


react("R_W_SEPOY", "b", "His head and shoulders fill the frame. One eyebrow slowly rises, utterly unimpressed, and he "
                       "gives a tiny dry exhale through his nose.")
react("R_W_PLATE", "b", "He slowly taps his closed brass spyglass against his palm, bored, eyes half-lidded.")
react("R_W_SURVIVED", "b", "His jaw tightens and he stares straight back, cold and unblinking.")
react("R_W_FLUKE", "b", "He scoffs silently, a thin cold smile at one corner of his pressed lips. His hands stay low, "
                       "out of frame.")
react("R_N_SUNSET", "a", "His nostrils flare and his jaw clenches, eyes narrowing in fury.")
react("R_N_WINTER", "a", "For a moment his face falls and his eyes drop, then he looks back up, hard and proud.")
react("R_N_CROWN", "a", "He grips his golden laurel wreath tighter against his chest, glaring furiously.")
react("R_N_STARE", "a", "He grimaces in disgust and looks away, shaking his head.")
react("R_N_FIGLEAF", "a", "His face flushes red with outrage, eyes wide, and he jabs a finger toward the lens while the "
                          "crowd behind him bursts out laughing.")
react("R_W_GAP", "b", "He calmly extends his brass spyglass, raises it to one eye toward the lens, then lowers it with a "
                      "dry smirk.")

still("WIDE_OPEN", ["a_face_clean", "b_face_clean"],
      "Extreme wide establishing shot from high above the courtyard: the camera cranes slowly down through drifting "
      "cannon smoke, revealing the whole torchlit farm courtyard packed with soldiers, the cold white spotlight on the "
      "circular stage where Napoleon Bonaparte (Image 1) on the left and the Duke of Wellington (Image 2) on the right "
      "face off as small full-body figures, French tricolours and golden eagles on the left, British flags on the right, "
      "hundreds of raised fists around the stage.", lora=0.0)
still("FACEOFF_OPEN", ["a_face_clean", "b_face_clean"],
      "Tight eye-level profile two-shot, handheld with a subtle sway: Napoleon Bonaparte (Image 1) on screen-left facing "
      "right and the Duke of Wellington (Image 2) on screen-right facing left stand face to face, almost nose to nose, "
      "staring each other down in silence, mouths closed, smoke drifting through the spotlight between them; Napoleon "
      "holds his golden laurel wreath low, Wellington his brass spyglass.")
still("FACEOFF_MID", ["a_face_clean", "b_face_clean"],
      "Medium two-shot at eye level, handheld, slowly circling: Napoleon Bonaparte (Image 1) on the left and the Duke of "
      "Wellington (Image 2) on the right pace slowly around each other in the spotlit circle like boxers between rounds, "
      "never breaking eye contact, mouths closed, the crowd roaring beyond the circle; Napoleon holds his golden laurel "
      "wreath, Wellington his brass spyglass.")
still("CROWD_OOH", ["crowd"],
      "Close medium shot packed with four or five soldiers and villagers from the front row (Image 1), their faces large "
      "and filling the 16:9 frame, handheld camera at their eye level, the spotlit stage only a blurred glow behind "
      "them. They react to a brutal punchline: one claps both hands over his mouth, a grenadier grabs his bearskin hat "
      "with wide eyes, a redcoat doubles over laughing and shoves his friend. Energetic, joyful chaos.")
still("CROWD_CHANT", ["crowd"],
      "Close medium shot of the front rows of the crowd (Image 1), handheld at their eye level, faces large and lit by "
      "torchlight: French grenadiers, British redcoats and villagers chant together with their fists pumping in rhythm, "
      "mouths wide open, sweat and smoke, the spotlight glowing behind them. The camera drifts sideways along this front "
      "row and stays on their faces from the first frame to the last; the stage is behind the camera.")
still("DJ", ["dj"],
      "Medium shot from a slightly low angle of the DJ (Image 1) at his raised booth built on a bronze field cannon and "
      "powder barrels, scratching a record with one hand and pointing at the crowd with the other, the crowd behind and "
      "below him punching the air in rhythm, torchlight and smoke.")
still("B_STEP", ["b_face_clean"],
      "The camera swings in from his side and settles into a frontal medium shot at eye level as the Duke of Wellington "
      "(Image 1) steps forward into the cold spotlight on the right side of the stage, calmly tugs his white cuffs "
      "straight and snaps his brass spyglass shut. Mouth closed, cold confident stare into the lens. He is alone on "
      "the stage: behind him only the British flags and the crowd beyond the edge of the circle.")
still("A_STEP", ["a_face_clean"],
      "The camera swings in from his side and settles into a frontal medium shot at eye level as Napoleon Bonaparte "
      "(Image 1) strides forward into the cold spotlight on the left side of the stage and raises his golden laurel wreath "
      "high above his head as the crowd roars. Mouth closed, fierce glare into the lens.")
still("WIDE_HIGH", ["a_face_clean", "b_face_clean"],
      "High wide shot from the top of the stone courtyard wall looking down over the whole arena, handheld: the entire "
      "crowd jumps and punches the air chanting, the spotlit circular stage in the middle with Napoleon Bonaparte "
      "(Image 1) on its left edge and the Duke of Wellington (Image 2) on its right edge, the DJ booth on its bronze "
      "cannon behind, haze drifting through the spotlight beam.", lora=0.0)
still("WIDE_OUTRO", ["b_face_clean", "a_face_clean"],
      "Wide shot from behind the Duke of Wellington (Image 1) on the right side of the stage, handheld at shoulder "
      "height: seen from behind, he raises his brass spyglass high in his right hand like a trophy as the whole packed "
      "courtyard chants and pumps their fists toward him, British flags waving; Napoleon Bonaparte (Image 2) is a small "
      "figure at the far left edge of the stage clutching his golden laurel wreath and turning away.", lora=0.0)
still("R_N_END", ["a_face_clean", "stage_a"],
      "Medium close-up of Napoleon Bonaparte (Image 1), handheld, the French side of the arena (Image 2) behind him: "
      "mouth closed, he lets his golden laurel wreath drop onto the straw at his feet and turns his back on the light.")
still("END", ["b_face_clean", "a_face_clean"],
      "Medium shot at eye level in the spotlit circle, slow push-in: the Duke of Wellington (Image 1) stands victorious on "
      "the right and spreads his arms wide, spyglass in one hand, the crowd roaring beyond the circle. In the dark "
      "background on the left, Napoleon Bonaparte (Image 2) walks out of the light. Mouths closed.", frames=90)
ids = {c["id"]: c for c in clips}

# ---------------------------------------------------------------- 时间线
spans = [(0.0, 1.26, "WIDE_OPEN", 1.0), (1.26, lip[order[0]][0], "FACEOFF_OPEN", 0.8)]
lip_ids = list(lip)
# 换人处的空档：(镜头, 入点, 最长可用秒数)；最后一个镜头吃掉剩余时间
GAPS = [
    [("CROWD_OOH", 0.05, 1.2), ("R_W_GAP", 0.3, 1.4), ("DJ", 0.2, 1.1), ("B_STEP", 0.4, 2.5)],
    [("CROWD_CHANT", 0.2, 2.2), ("DJ", 1.4, 1.5), ("WIDE_HIGH", 0.3, 2.6), ("FACEOFF_MID", 0.3, 2.3), ("A_STEP", 0.4, 2.5)],
]
gap_i, lcut_spans = 0, []
for k, c in enumerate(lip_ids):
    a0, lwe, covered = lip[c]
    # 接着上一句（或上一句的 L-cut 反应镜头）结束的地方；换人空档之后才从本句音频起点开始
    t0 = spans[-1][1] if (spans[-1][3] is None or spans[-1][2] in LCUT_RIDS) else a0
    nxt = lip_ids[k + 1] if k + 1 < len(lip_ids) else None
    if nxt is None:
        t1 = round(lwe + 0.02, 3)
    elif nxt[0] != c[0] and lip[nxt][0] - lwe > 0.5:
        t1 = round(lwe + 0.02, 3)  # 换人且有空档：最后一个词唱完就切
    else:
        t1 = round(max(lip[nxt][0], lwe + 0.02), 3)
    lc = next((x for x in covered if x in LCUT), None)
    if lc:  # 后半句切到对手反应，声音继续
        word, rid = LCUT[lc]
        tc = round(word_t(line_by[lc], word, nxt_start[lc]), 3)
        assert tc - t0 >= MIN_ON_SINGER, f"{c}: only {tc - t0:.2f}s on the singer before the L-cut"
        spans.append((t0, tc, c, None))
        spans.append((tc, t1, rid, REACT_IN_BY.get(rid, REACT_IN)))
        lcut_spans.append((c, tc, t1))
    else:
        spans.append((t0, t1, c, None))
    if nxt and nxt[0] != c[0] and t1 < lip[nxt][0] - 1e-6:
        g0, g1 = t1, lip[nxt][0]
        shots = GAPS[gap_i]
        gap_i += 1
        t = g0
        for j, (sid, inn, mx) in enumerate(shots):
            d = (g1 - t) if j == len(shots) - 1 else min(mx, (g1 - g0) / len(shots) * 1.15)
            assert d <= mx + 1e-6, f"gap {g0:.2f}-{g1:.2f}: {sid} would need {d:.2f}s > {mx}s usable"
            spans.append((round(t, 3), round(t + d, 3), sid, inn))
            t += d
assert gap_i == len(GAPS), f"used {gap_i} gaps, defined {len(GAPS)}"
# 尾奏：IRON DUKE 齐喊 → 拿破仑丢下月桂冠 → 威灵顿张开双臂（片尾卡盖在最后 2.3 秒上）
o0 = spans[-1][1]
end_d = float(e.get("end_card_secs", 2.3))
outro = [("WIDE_OUTRO", 0.5, END_T - o0 - 0.9 - end_d), ("R_N_END", 1.2, 0.9), ("END", 0.2, None)]
t = o0
for sid, inn, d in outro:
    d = (END_T - t) if d is None else d
    spans.append((round(t, 3), round(t + d, 3), sid, inn))
    t += d
edl = [{"t0": a, "t1": b, "clip": c, "in": i} for a, b, c, i in spans]

# ---------------------------------------------------------------- 断言
for prev, cur in zip(edl, edl[1:]):
    assert abs(prev["t1"] - cur["t0"]) < 1e-6, (prev, cur)
assert abs(edl[-1]["t1"] - END_T) < 1e-6
lcut_heads = {c for c, _, _ in lcut_spans}
for x in edl:
    c = ids[x["clip"]]
    assert x["t1"] - x["t0"] > 0.3, f"{x['clip']} only {x['t1'] - x['t0']:.2f}s"
    if c["kind"] == "rap":
        _, lwe, _ = lip[x["clip"]]
        if x["clip"] not in lcut_heads:  # 「唱完才切」：只有 L-cut 句子例外
            assert x["t1"] >= lwe - 0.05, f"{x['clip']} cut at {x['t1']:.2f} before its last word ends {lwe:.2f}"
        assert x["t0"] >= c["audio"][0] - 1e-6
        assert c["audio"][1] - c["audio"][0] + 0.35 <= 158 / 24, f"{x['clip']} too long for one H3 clip"
    else:
        assert x["in"] + (x["t1"] - x["t0"]) <= c["frames"] / 24 - 0.05, x
used = {x["clip"] for x in edl}
assert used == set(ids), f"defined but unused: {set(ids) - used}; used but undefined: {used - set(ids)}"

# ---------------------------------------------------------------- 后期特效
def slot_end(cid):
    return next(x["t1"] for x in edl if x["clip"] == cid)


def wt(cid, word):
    return round(word_t(line_by[cid], word, nxt_start[cid]), 3)


fx = [{"type": "flash", "t0": round(grid["beat0"], 3), "t1": round(grid["beat0"] + 0.08, 3), "alpha": 0.7}]
for cid, w, amt in [("A02", "crowned", 0.08), ("B03", "moscow", 0.08), ("A15", "rubber", 0.08), ("B11", "marengo", 0.08)]:
    fx.append({"type": "punch", "t0": wt(cid, w), "t1": slot_end(cid), "amount": amt})
for rid in ("R_N_FIGLEAF", "R_N_CROWN"):  # 重拳句落在对手脸上：闪白 + 震屏
    x = next(x for x in edl if x["clip"] == rid)
    fx += [{"type": "flash", "t0": x["t0"], "t1": round(x["t0"] + 0.08, 3), "alpha": 0.85},
           {"type": "shake", "t0": x["t0"], "t1": round(x["t0"] + 0.5, 3), "px": 9}]
fx.append({"type": "dark", "t0": wt("B16", "waterloo"), "t1": slot_end("B16"), "amount": 0.12})
for x in edl:
    if x["clip"] in ("CROWD_OOH", "CROWD_CHANT", "A_STEP", "B_STEP", "WIDE_OUTRO"):
        fx.append({"type": "flash", "t0": x["t0"], "t1": round(x["t0"] + 0.08, 3), "alpha": 0.8})

json.dump(clips, open(os.path.join(WORK, "clips.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(edl, open(os.path.join(WORK, "edl.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(fx, open(os.path.join(WORK, "fx.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
live_src = os.path.join(EP, "..", "edison-vs-tesla-full", "work", "live.json")
if not os.path.exists(os.path.join(WORK, "live.json")):
    json.dump(json.load(open(live_src)), open(os.path.join(WORK, "live.json"), "w"), indent=1)

n_lip = sum(1 for c in clips if c["kind"] == "rap")
durs = [x["t1"] - x["t0"] for x in edl]
print(f"wrote {len(clips)} clips ({n_lip} lip, {len(clips) - n_lip} still), {len(edl)} edl entries, {len(fx)} fx, "
      f"timeline 0-{END_T:.2f}s; shot length min {min(durs):.2f} median {sorted(durs)[len(durs) // 2]:.2f} "
      f"max {max(durs):.2f}")
for c, tc, t1 in lcut_spans:
    print(f"  L-cut {c}: singer until {tc:.2f}, reaction {t1 - tc:.2f}s")
