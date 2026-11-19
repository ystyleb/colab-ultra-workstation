#!/usr/bin/env python3
"""Songifted 横屏长视频「How it works」（1920x1080，约 88 秒，本地合成 0 CCU）。

素材全部来自网站本身：
- /create 桌面版逐状态截图：capture_songifted_create.mjs（ego-browser，视口 1280x720 @2x）→ samples/songifted_longform/create/
- 首页 AI 反应视频 /videos/reaction-*.mp4、场合配图 /imgs/generated/photo-*.jpg → samples/songifted_longform/site/
- 示例歌 /demos/*.mp3 → samples/songifted/demos/（不另外生成歌）

结构跟着首页「How it works」三步走：
  钩子（派对 + 「Happy birthday Sarah, make a wish…」）→ 标题 → ① 录屏 → ② 歌词 → ③ 反应镜头 → 场合串烧 → 片尾
配乐只用 Sarah 那首示例歌，并且基本按原顺序播放：钩子用第二段副歌，从标题开始从 0 秒放起，
第一段副歌（歌内 24.72 s）正好落在「② We write it」那一段。改时长先改 TIMELINE，再核对 song_t 换算。

python3 workflows/08_site_channels/songifted_longform.py            # 成片
python3 workflows/08_site_channels/songifted_longform.py --preview  # 960x540 快速预览
python3 workflows/08_site_channels/songifted_longform.py --still 35 # 只导出第 35 秒的单帧 PNG
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Callable

from PIL import Image, ImageDraw, ImageFilter

from promo_short import SG, ease_out, font, rounded, wrap

HERE = Path(__file__).resolve().parent
SL = HERE / "samples" / "songifted_longform"
CREATE = SL / "create"
SITE = SL / "site"
DEMOS = HERE / "samples" / "songifted" / "demos"
OUT = HERE / "out" / "promo" / "songifted" / "Songifted_HowItWorks_1920x1080.mp4"

W, H, FPS = 1920, 1080, 30
CORAL, INK, CREAM, CREAM2, MUTED, WHITE = SG["coral"], SG["ink"], SG["cream"], SG["cream2"], SG["muted"], SG["white"]

# ---------------- 时间线（成片秒） ----------------
T_HOOK = 0.0
T_TITLE = 7.2          # 歌曲从 0 秒开始播放的时刻：song_t = t - T_TITLE
T_WALK = 10.2
T_STEP2 = 31.4         # 第一段副歌 24.72 s → 成片 31.92 s
T_STEP3 = 43.0
T_MONTAGE = 60.0
T_END = 78.8
T_TOTAL = 87.8
SONG_HOOK = (35.8, 43.0)   # 「Happy birthday Sarah, make a wish and watch it come true」36.08–40.58


def song_t(t: float) -> float:
    return t - T_TITLE


# 歌词（Sarah 示例歌，mlx_whisper small 逐窗口识别 + 首页歌词摘录核对；前两句与首页原文一致）
# 每句手动断成两行；行内片段 (文字, 是否高亮)。高亮 = 名字 / 和 brief 对应的词
LYRICS = [
    (24.72, [[("Happy birthday ", 0), ("Sarah", 1), (",", 0)], [("this song belongs to you", 0)]]),
    (28.92, [[("Every single line of it", 0)], [("is us saying thank you", 0)]]),
    (32.82, [[("For the ", 0), ("laughs", 1), (",", 0)], [("the ", 0), ("late-night calls", 1)]]),
]
# 首页 “The idea” 原文（fictional example 的示意 brief）
BRIEF = "“A birthday song for our friend Sarah, to say thank you for the laughs and late-night calls.”"

# 场合串烧：(文件, 入点, 出点, 首页曲名原文, 首页标签原文, 配图)
MONTAGE = [
    ("memorial.mp3", 14.4, 19.0, "Remembering Joe", "In Memory · Piano Ballad", "photo-memorial.jpg"),
    ("for-mom.mp3", 39.9, 44.0, "Everything You Gave Me (for Linda)", "For Mom · Acoustic Pop", "photo-mom.jpg"),
    ("wedding.mp3", 15.0, 20.6, "Walking to You (for Chloe & Ben)", "Wedding · First Dance", "photo-wedding.jpg"),
    ("anniversary.mp3", 54.9, 59.4, "Ten Years of Us (for Emma)", "Anniversary · Piano Ballad", "photo-anniversary.jpg"),
]
END_SONG = (51.4, 60.0)  # 「You showed up for all of us … so tonight we're singing yours」

OFFER = "Eligible first-time creators can preview 45 seconds free. Full songs from $49. No card needed for an eligible preview."


# ---------------- 小工具 ----------------
def serif(size: int, weight: str = "SemiBold"):
    return font("fraunces", size, weight)


def sans(size: int, weight: str = "Medium"):
    return font("dmsans", size, weight)


def alpha_mul(im: Image.Image, a: float) -> Image.Image:
    if a >= 0.999:
        return im
    im = im.copy()
    im.putalpha(im.getchannel("A").point(lambda v: int(v * max(0.0, a))))
    return im


def fade(t: float, t0: float, t1: float, d: float = 0.3) -> float:
    if t < t0 or t >= t1:
        return 0.0
    return max(0.0, min(1.0, (t - t0) / d, (t1 - t) / d))


@lru_cache(maxsize=256)
def text_img(text: str, f_key: tuple, color: tuple, maxw: int = 1600, line_gap: float = 1.22, align: str = "left") -> Image.Image:
    fam, size, weight = f_key
    f = font(fam, size, weight)
    probe = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    lines = []
    for para in text.split("\n"):
        lines += wrap(probe, para, f, maxw)
    lh = int(size * line_gap)
    w = max(int(probe.textlength(l, font=f)) for l in lines) + 8
    im = Image.new("RGBA", (w, lh * len(lines) + int(size * 0.35)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for k, l in enumerate(lines):
        x = {"left": 0, "center": (w - probe.textlength(l, font=f)) / 2}[align]
        d.text((x, lh * k), l, font=f, fill=color + (255,))
    return im


def rich_line(canvas: Image.Image, x: int, y: int, segs, size: int, a: float):
    """一行富文本：高亮片段用珊瑚色 SemiBold，其余 INK Regular。"""
    if a <= 0.01:
        return
    probe = ImageDraw.Draw(canvas)
    for text, hl in segs:
        f_key = ("fraunces", size, "SemiBold" if hl else "Regular")
        put(canvas, text_img(text, f_key, CORAL if hl else INK), x, y, a)
        x += int(probe.textlength(text, font=font(*f_key)))


def put(canvas: Image.Image, im: Image.Image, x: int, y: int, a: float = 1.0, anchor: str = "lt"):
    if a <= 0.01:
        return
    if anchor[0] == "m":
        x -= im.width // 2
    elif anchor[0] == "r":
        x -= im.width
    if anchor[1] == "m":
        y -= im.height // 2
    canvas.alpha_composite(alpha_mul(im, a), (int(x), int(y)))


def chip(canvas: Image.Image, x: int, y: int, num: str | None, text: str, a: float = 1.0, dark: bool = False):
    """左上角步骤签：珊瑚色圆形序号 + 文字。dark=True 用在视频画面上（半透明黑底）。"""
    if a <= 0.01:
        return
    f = sans(34, "SemiBold")
    tw = int(ImageDraw.Draw(canvas).textlength(text, font=f))
    h = 64
    w = tw + (h + 22 if num else 0) + 44
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=h // 2, fill=((20, 14, 10, 175) if dark else WHITE + (255,)))
    x0 = 22
    if num:
        d.ellipse((8, 8, h - 8, h - 8), fill=CORAL + (255,))
        d.text((h // 2, h // 2), num, font=sans(30, "Bold"), fill=WHITE + (255,), anchor="mm")
        x0 = h + 14
    d.text((x0, h // 2), text, font=f, fill=(WHITE if dark else INK) + (255,), anchor="lm")
    put(canvas, layer, x, y, a)


@lru_cache(maxsize=1)
def logo() -> Image.Image:
    return rounded(Image.open(HERE / "out" / "songifted" / "avatar_800.png").convert("RGB").resize((96, 96), Image.LANCZOS), 48)


def video_frames(path: Path, t0: float, dur: float, w: int, h: int, mode: str = "cover"):
    """读视频片段为 w×h RGB 帧（cover 裁切或按高缩放），统一到 FPS。"""
    vf = f"fps={FPS},scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}" if mode == "cover" else f"fps={FPS},scale={w}:{h}"
    n = round(dur * FPS)
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{t0:.3f}", "-i", str(path), "-frames:v", str(n), "-vf", vf,
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    frames = []
    while True:
        b = p.stdout.read(w * h * 3)
        if len(b) < w * h * 3:
            break
        frames.append(Image.frombytes("RGB", (w, h), b))
    p.wait()
    if not frames:
        raise RuntimeError(f"读不到帧: {path}")
    while len(frames) < n:
        frames.append(frames[-1])
    return frames


# ---------------- A 钩子：派对（方形）+ 右侧歌词 ----------------
@lru_cache(maxsize=1)
def party_frames():
    return video_frames(SITE / "reaction-party-square.mp4", 0.0, T_TITLE + 0.6, 1080, 1080, mode="scale")


def scene_hook(t: float) -> Image.Image:
    c = Image.new("RGBA", (W, H), CREAM + (255,))
    fr = party_frames()[min(len(party_frames()) - 1, int(t * FPS))]
    c.paste(fr, (0, 0))
    st = SONG_HOOK[0] + t
    x = 1150
    put(c, text_img("Example song · songifted.com", ("dmsans", 28, "Medium"), MUTED), x, 300, fade(t, 0.2, 99, 0.4))
    a1 = fade(st, 36.0, 99, 0.35)
    put(c, text_img("Happy birthday", ("fraunces", 64, "Regular"), INK, 760), x, 360, a1)
    put(c, text_img("Sarah,", ("fraunces", 64, "SemiBold"), CORAL, 760), x, 440, a1)
    put(c, text_img("make a wish and\nwatch it come true", ("fraunces", 64, "Regular"), INK, 760), x, 520, fade(st, 37.4, 99, 0.35))
    a3 = fade(t, 4.9, 99, 0.4)
    d = ImageDraw.Draw(c)
    if a3 > 0:
        d.line((x, 712, x + 90, 712), fill=CORAL + (int(255 * a3),), width=4)
    put(c, text_img("A song with their name in it.", ("dmsans", 44, "SemiBold"), INK, 760), x, 740, a3)
    return c


# ---------------- B 标题 ----------------
STEPS = [("1", "Tell us about them"), ("2", "We write it — you approve it"), ("3", "Share it — and watch their face")]


def scene_title(t: float) -> Image.Image:
    lt = t - T_TITLE
    c = Image.new("RGBA", (W, H), CREAM + (255,))
    put(c, logo(), W // 2, 210, fade(lt, 0.0, 99, 0.3), "mm")
    put(c, text_img("How to make a custom song\nwith their name in it", ("fraunces", 84, "SemiBold"), INK, 1500, align="center"),
        W // 2, 300, fade(lt, 0.1, 99, 0.35), "mt")
    for k, (n, s) in enumerate(STEPS):
        a = fade(lt, 0.7 + 0.35 * k, 99, 0.3)
        chip(c, W // 2 - 330, 600 + k * 92, n, s, a)
    return c


# ---------------- C 录屏：/create 五步 ----------------
SUB = [  # (label 前缀, 顶栏右侧小字)
    ("s1_empty", "Their name — the one they'll hear sung"), ("s1_name", "Their name — the one they'll hear sung"),
    ("s1_friend", "Who they are to you"), ("s1_age", "Who they are to you"), ("s1_next", "The occasion"),
    ("s2", "The occasion"), ("s3_enter", "How it should sound"), ("s3", "How it should sound"),
    ("s4_msg", "Your words to them"), ("s4", "The details only you know"),
    ("s5_final", "Free 45-second preview for eligible first-time creators"), ("s5", "Who it's from"),
]


def sub_for(label: str) -> str:
    if label.startswith("s3_next"):
        return "The details only you know"
    if label.startswith("s4_next"):
        return "Who it's from"
    for p, s in SUB:
        if label.startswith(p):
            return s
    return ""


def shot_duration(label: str) -> float:
    """每张截图在成片里停留多久（缩放前的基准秒数）。决定录屏段的节奏。"""
    if "_scroll" in label:
        return 0.10
    if label.endswith("_hover"):
        return 0.42
    if label.startswith(("s1_name_", "s5_from_")):
        return 0.14
    if label.startswith("s4_msg_"):
        return 0.12
    if label.endswith("_next"):
        return 0.55
    return {"s1_empty": 0.9, "s3_enter": 0.6, "s5_enter": 0.9, "s5_final": 2.4}.get(label, 0.5)


# 窗口布局：模拟浏览器窗口，内容区 1600x900（16:9），顶上留 120 px 放步骤签
WIN_X, WIN_Y, WIN_W, WIN_H, CHROME = 160, 150, 1600, 900, 0


@dataclass
class Shot:
    file: str
    label: str
    targets: dict
    dur: float = 0.0
    start: float = 0.0


@lru_cache(maxsize=1)
def walk_shots() -> list[Shot]:
    man = json.loads((CREATE / "manifest.json").read_text())
    shots = [Shot(s["file"], s["label"], s["targets"]) for s in man["shots"]
             if not s["label"].startswith("s5_start_hover")]
    # 第 5 步页面上有账号邮箱：任何一帧缺邮箱坐标就拒绝出片（之前选错元素、邮箱明文漏进过预览）
    # 点完第 4 步 Next（s4_next）之后每一帧都是第 5 步，含滚动帧；采集脚本每帧按 "@" 查邮箱坐标
    i5 = next(k for k, s in enumerate(shots) if s.label == "s4_next")
    leak = [s.file for s in shots[i5:] if not s.targets.get("email")]
    assert not leak, f"这些第 5 步截图没有邮箱坐标，无法打码: {leak}"
    for s in shots:
        s.dur = shot_duration(s.label)
    total = sum(s.dur for s in shots)
    k = (T_STEP2 - T_WALK) / total
    t = T_WALK
    for s in shots:
        s.dur *= k
        s.start = t
        t += s.dur
    return shots


@lru_cache(maxsize=8)
def shot_img(file: str) -> Image.Image:
    im = Image.open(CREATE / file).convert("RGB")  # 2560x1440
    sh = next(s for s in walk_shots() if s.file == file)
    box = sh.targets.get("email")
    if box and box[1] + box[3] > 0:  # 第 5 步的账号邮箱打码
        x, y, w, h = [v * 2 for v in box]
        x0, y0, x1, y1 = int(x) - 6, max(0, int(y) - 6), int(x + w) + 6, int(y + h) + 6
        region = im.crop((x0, y0, x1, y1)).filter(ImageFilter.GaussianBlur(14))
        im.paste(region, (x0, y0))
    return im


def target_of(s: Shot):
    """光标/镜头目标（截图像素坐标，2x）。"""
    # 不把灰着的「Start … song」当目标：光标停在它上面像是要提交（我们不提交，也不碰 Turnstile）
    for key in ("target", "field", "offer" if s.label.startswith("s5_final") else "_"):
        b = s.targets.get(key)
        if b:
            x, y, w, h = b
            if key == "field":  # 打字时光标停在输入框右下，镜头看输入框
                return (x + w * 0.5) * 2, (y + h * 0.5) * 2, (x + w - 30) * 2, (y + h - 12) * 2
            return (x + w / 2) * 2, (y + h / 2) * 2, (x + w / 2) * 2, (y + h / 2) * 2
    return None


def zoom_for(s: Shot) -> float:
    if s.label.startswith("s4_msg_") or s.label.startswith("s1_name_") or s.label.startswith("s5_from_"):
        return 1.45
    if s.label.startswith("s5_final"):
        return 2.0  # 报价原文只有 13–14 CSS px，推到 2x 成片里约 33 px
    if "_scroll" in s.label or s.label.endswith(("_next", "_enter", "_empty")):
        return 1.0
    return 1.22


class WalkState:
    """逐帧推进的镜头与光标（指数平滑，像手持录屏软件的自动跟随）。"""

    def __init__(self):
        self.cx, self.cy, self.z = 1280.0, 720.0, 1.0
        self.mx, self.my = 1500.0, 900.0
        self.frame = -1
        self.click_t = -9.0
        self.last_label = ""


_walk = WalkState()


def cursor_img() -> Image.Image:
    pts = [(0, 0), (0, 34), (9, 26), (15, 40), (21, 37), (15, 24), (27, 24)]
    im = Image.new("RGBA", (44, 52), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.polygon([(x + 4, y + 4) for x, y in pts], fill=(0, 0, 0, 90))
    im = im.filter(ImageFilter.GaussianBlur(2))
    d = ImageDraw.Draw(im)
    d.polygon([(x + 2, y + 2) for x, y in pts], fill=WHITE + (255,), outline=(20, 20, 20, 255))
    return im


CURSOR = None


def scene_walk(t: float) -> Image.Image:
    global CURSOR
    if CURSOR is None:
        CURSOR = cursor_img()
    shots = walk_shots()
    i = max(k for k, s in enumerate(shots) if s.start <= t + 1e-6)
    s = shots[i]
    st = _walk
    # 镜头目标
    tg = target_of(s)
    z_goal = zoom_for(s)
    if tg:
        cx_goal, cy_goal, mx_goal, my_goal = tg
    else:
        cx_goal, cy_goal, mx_goal, my_goal = 1280, 720, st.mx, st.my
    if z_goal <= 1.0:
        cx_goal, cy_goal = 1280, 720
    if s.label != st.last_label:
        if st.last_label.endswith("_hover") or (st.last_label.endswith("_next_hover")):
            st.click_t = t
        st.last_label = s.label
    k_cam, k_mouse = 0.10, 0.22
    st.z += (z_goal - st.z) * k_cam
    st.cx += (cx_goal - st.cx) * k_cam
    st.cy += (cy_goal - st.cy) * k_cam
    st.mx += (mx_goal - st.mx) * k_mouse
    st.my += (my_goal - st.my) * k_mouse
    # 取景：源 2560x1440，视窗 2560/z × 1440/z
    vw, vh = 2560 / st.z, 1440 / st.z
    x0 = min(max(0, st.cx - vw / 2), 2560 - vw)
    y0 = min(max(0, st.cy - vh / 2), 1440 - vh)
    src = shot_img(s.file)
    # 滚动段与下一张交叉淡化，减少跳动
    if "_scroll" in s.label and i + 1 < len(shots):
        p = (t - s.start) / s.dur
        src = Image.blend(src, shot_img(shots[i + 1].file), max(0.0, min(1.0, p)) * 0.6)
    view = src.crop((round(x0), round(y0), round(x0 + vw), round(y0 + vh))).resize((WIN_W, WIN_H), Image.LANCZOS)

    c = Image.new("RGBA", (W, H), CREAM2 + (255,))
    # 窗口阴影 + 圆角
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle((WIN_X + 6, WIN_Y + 16, WIN_X + WIN_W + 6, WIN_Y + WIN_H + 22), radius=22, fill=(60, 30, 10, 70))
    c.alpha_composite(sh.filter(ImageFilter.GaussianBlur(18)))
    c.alpha_composite(rounded(view, 18), (WIN_X, WIN_Y))
    # 光标（源坐标 → 窗口坐标）
    sx = WIN_X + (st.mx - x0) / vw * WIN_W
    sy = WIN_Y + (st.my - y0) / vh * WIN_H
    ct = t - st.click_t
    if 0 <= ct < 0.35:
        r = 14 + 40 * ease_out(ct / 0.35)
        ring = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(ring).ellipse((sx - r, sy - r, sx + r, sy + r), outline=CORAL + (int(230 * (1 - ct / 0.35)),), width=6)
        c.alpha_composite(ring)
    if WIN_X - 10 < sx < WIN_X + WIN_W and WIN_Y - 10 < sy < WIN_Y + WIN_H:
        c.alpha_composite(CURSOR, (int(sx) - 2, int(sy) - 2))
    # 顶栏：步骤签 + 当前小节
    lt = t - T_WALK
    chip(c, WIN_X, 46, "1", "Tell us about them", fade(lt, 0.0, 99, 0.3))
    sub = sub_for(s.label)
    if sub:
        put(c, text_img(sub, ("dmsans", 36, "Medium"), MUTED), WIN_X + WIN_W, 78, 1.0, "rm")
    return c


# ---------------- D ② 歌词 ----------------
def scene_step2(t: float) -> Image.Image:
    lt, st = t - T_STEP2, song_t(t)
    c = Image.new("RGBA", (W, H), CREAM + (255,))
    chip(c, 160, 46, "2", "We write it — you approve it", fade(lt, 0.0, 99, 0.3))
    # 左：brief
    put(c, text_img("YOUR WORDS", ("dmsans", 28, "Bold"), MUTED), 160, 230, fade(lt, 0.2, 99, 0.3))
    card = Image.new("RGBA", (640, 360), (0, 0, 0, 0))
    ImageDraw.Draw(card).rounded_rectangle((0, 0, 639, 359), radius=26, fill=WHITE + (255,))
    put(c, card, 160, 280, fade(lt, 0.2, 99, 0.3))
    put(c, text_img(BRIEF, ("fraunces", 40, "Regular"), INK, 560), 200, 320, fade(lt, 0.3, 99, 0.3))
    hl = fade(st, LYRICS[2][0], 99, 0.3)
    if hl:  # 唱到「For the laughs, the late-night calls」时把 brief 里对应的词标出来
        put(c, text_img("laughs  ·  late-night calls", ("dmsans", 30, "Bold"), CORAL), 200, 580, hl)
    put(c, text_img("Illustrative brief for the fictional “Sarah” example on songifted.com",
                    ("dmsans", 24, "Medium"), MUTED, 640), 160, 690, fade(lt, 0.3, 99, 0.3))
    # 中间箭头
    a = fade(lt, 0.4, 99, 0.3)
    if a:
        d = ImageDraw.Draw(c)
        d.line((860, 460, 950, 460), fill=CORAL + (int(255 * a),), width=6)
        d.polygon([(950, 444), (976, 460), (950, 476)], fill=CORAL + (int(255 * a),))
    # 右：歌词逐句
    put(c, text_img("THEIR LYRICS", ("dmsans", 28, "Bold"), MUTED), 1030, 230, fade(lt, 0.2, 99, 0.3))
    for k, (ts, lines) in enumerate(LYRICS):
        a = fade(st, ts - 0.15, 99, 0.3)
        nxt = LYRICS[k + 1][0] if k + 1 < len(LYRICS) else 99
        dim = 0.5 if st >= nxt else 1.0
        for j, segs in enumerate(lines):
            rich_line(c, 1030, 282 + k * 128 + j * 54, segs, 42, a * dim)
    put(c, text_img("Lyric excerpt from the fictional “Sarah” sample song on songifted.com",
                    ("dmsans", 24, "Medium"), MUTED, 760), 1030, 690, fade(lt, 0.6, 99, 0.3))
    # 底部：审歌词的规则（首页 How it works 第 2 步）
    rules = ["Read every line", "Edit the title or lyrics", "Up to three AI rewrites", "Audio starts only after you confirm"]
    x = 160
    for k, r in enumerate(rules):
        a = fade(lt, 1.6 + 0.9 * k, 99, 0.3)
        f = sans(30, "SemiBold")
        w = int(ImageDraw.Draw(c).textlength(r, font=f)) + 56
        pill = Image.new("RGBA", (w, 62), (0, 0, 0, 0))
        dd = ImageDraw.Draw(pill)
        dd.rounded_rectangle((0, 0, w - 1, 61), radius=31, fill=(CORAL if k == 3 else CREAM2) + (255,))
        dd.text((w // 2, 31), r, font=f, fill=(WHITE if k == 3 else INK) + (255,), anchor="mm")
        put(c, pill, x, 860, a)
        x += w + 18
    return c


# ---------------- E ③ 反应镜头 ----------------
STEP3 = [  # (文件, 入点, 时长, 标题, 小字) 标题与小字都是首页原文
    ("reaction-remote.mp4", 0.0, 5.6, "Over text", "A gift page they can replay whenever they miss you"),
    ("reaction-quiet.mp4", 0.0, 5.6, "The quiet moment after", "When they realize you made this for them"),
    ("reaction-sequence.mp4", 13.9, 5.8, "Hear 45 seconds first", "Free preview for eligible first-time creators. Full songs from $49."),
]


@lru_cache(maxsize=3)
def step3_frames(k: int):
    f, t0, dur, *_ = STEP3[k]
    return video_frames(SITE / f, t0, dur + 0.5, W, H)


def scene_step3(t: float) -> Image.Image:
    lt = t - T_STEP3
    acc = 0.0
    for k, (_, _, dur, title, small) in enumerate(STEP3):
        if lt < acc + dur or k == len(STEP3) - 1:
            break
        acc += dur
    li = lt - acc
    fr = step3_frames(k)
    img = fr[min(len(fr) - 1, int(li * FPS))].convert("RGBA")
    if li < 0.3 and k > 0:  # 与上一段交叉淡化
        pf = step3_frames(k - 1)
        prev = pf[min(len(pf) - 1, int((STEP3[k - 1][2] + li) * FPS))].convert("RGBA")
        img = Image.blend(prev, img, li / 0.3)
    # 底部渐变 + 文案
    grad = Image.new("L", (1, 360))
    for y in range(360):
        grad.putpixel((0, y), int(200 * (y / 359) ** 1.6))
    shade = Image.new("RGBA", (W, 360), (15, 8, 4, 255))
    shade.putalpha(grad.resize((W, 360)))
    img.alpha_composite(shade, (0, H - 360))
    chip(img, 80, 50, "3", "Share it — and watch their face", 1.0, dark=True)
    a = fade(li, 0.25, dur + (0.5 if k == len(STEP3) - 1 else 0.0), 0.35)
    put(img, text_img(title, ("fraunces", 64, "SemiBold"), WHITE), 120, H - 230, a)
    put(img, text_img(small, ("dmsans", 36, "Medium"), (245, 232, 220), 1500), 120, H - 140, a)
    return img


# ---------------- F 场合串烧 ----------------
def montage_spans():
    t, out = T_MONTAGE, []
    for m in MONTAGE:
        d = m[2] - m[1]
        out.append((t, t + d, m))
        t += d
    assert abs(t - T_END) < 0.05, f"串烧总长 {t - T_MONTAGE:.2f} 与 T_END 不符"
    return out


@lru_cache(maxsize=8)
def occasion_card(photo: str) -> Image.Image:
    im = Image.open(SITE / photo).convert("RGB").resize((880, 660), Image.LANCZOS)
    return rounded(im, 28)


def scene_montage(t: float) -> Image.Image:
    c = Image.new("RGBA", (W, H), CREAM + (255,))
    chip(c, 160, 46, None, "One Gift That Works for Every Occasion", 1.0)
    for t0, t1, (_, _, _, title, tag, photo) in montage_spans():
        if t0 - 0.001 <= t < t1:
            li = t - t0
            a = fade(li, 0.0, t1 - t0, 0.25)
            card = occasion_card(photo)
            s = 1.0 + 0.03 * (li / (t1 - t0))
            cs = card.resize((int(card.width * s), int(card.height * s)), Image.BILINEAR)
            put(c, cs, 160 + 440, 230 + 330, a, "mm")
            put(c, text_img(tag, ("dmsans", 32, "SemiBold"), CORAL), 1120, 380, a)
            put(c, text_img(title, ("fraunces", 62, "SemiBold"), INK, 680), 1120, 430, a)
            put(c, text_img("Example song from songifted.com", ("dmsans", 26, "Medium"), MUTED), 1120, 650, a)
    return c


# ---------------- G 片尾 ----------------
def scene_end(t: float) -> Image.Image:
    lt = t - T_END
    c = Image.new("RGBA", (W, H), CREAM + (255,))
    put(c, logo(), W // 2, 200, fade(lt, 0.0, 99, 0.3), "mm")
    put(c, text_img("Make one with their name in it", ("fraunces", 78, "SemiBold"), INK, 1600, align="center"),
        W // 2, 290, fade(lt, 0.1, 99, 0.35), "mt")
    a = fade(lt, 0.5, 99, 0.35)
    f = sans(64, "Bold")
    w = int(ImageDraw.Draw(c).textlength("songifted.com", font=f)) + 120
    p = Image.new("RGBA", (w, 116), (0, 0, 0, 0))
    ImageDraw.Draw(p).rounded_rectangle((0, 0, w - 1, 115), radius=58, fill=CORAL + (255,))
    ImageDraw.Draw(p).text((w // 2, 58), "songifted.com", font=f, fill=WHITE + (255,), anchor="mm")
    put(c, p, W // 2, 470, a, "mt")
    put(c, text_img(OFFER, ("dmsans", 34, "Medium"), MUTED, 1300, align="center"), W // 2, 650, fade(lt, 0.8, 99, 0.35), "mt")
    put(c, text_img("Link in the description", ("dmsans", 34, "SemiBold"), CORAL), W // 2, 820, fade(lt, 1.4, 99, 0.35), "mt")
    if t > T_TOTAL - 0.6:
        c.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * (t - (T_TOTAL - 0.6)) / 0.6))))
    return c


# ---------------- 拼装 ----------------
SCENES: list[tuple[float, float, Callable[[float], Image.Image]]] = [
    (T_HOOK, T_TITLE, scene_hook), (T_TITLE, T_WALK, scene_title), (T_WALK, T_STEP2, scene_walk),
    (T_STEP2, T_STEP3, scene_step2), (T_STEP3, T_MONTAGE, scene_step3), (T_MONTAGE, T_END, scene_montage),
    (T_END, T_TOTAL, scene_end),
]
XFADE = {T_TITLE: 0.4, T_WALK: 0.35, T_STEP2: 0.35, T_STEP3: 0.3, T_MONTAGE: 0.3, T_END: 0.4}


def frame_at(t: float) -> Image.Image:
    for k, (a, b, fn) in enumerate(SCENES):
        if a <= t < b or k == len(SCENES) - 1:
            img = fn(t)
            xf = XFADE.get(a, 0)
            if k and t - a < xf:
                prev = SCENES[k - 1][2](t)
                img = Image.blend(prev, img, (t - a) / xf)
            return img.convert("RGB")
    raise ValueError(t)


def mix_audio(video: Path, out: Path):
    B = DEMOS / "birthday.mp3"
    segs = [(B, *SONG_HOOK, T_HOOK), (B, 0.0, T_MONTAGE - T_TITLE, T_TITLE)]
    for t0, _, (f, a, b, *_r) in montage_spans():
        segs.append((DEMOS / f, a, b, t0))
    segs.append((B, END_SONG[0], END_SONG[1], T_END))
    ins, fl, labels = [], [], []
    for j, (f, a, b, at) in enumerate(segs):
        ins += ["-i", str(f)]
        d = b - a
        ms = int(at * 1000)
        fl.append(f"[{j + 1}:a]atrim={a:.3f}:{b:.3f},asetpts=PTS-STARTPTS,aformat=sample_rates=48000:channel_layouts=stereo,"
                  f"afade=t=in:d={0.05 if j == 0 else 0.25},afade=t=out:st={d - 0.35:.3f}:d=0.35,adelay={ms}|{ms}[s{j}]")
        labels.append(f"[s{j}]")
    fl.append(f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0:duration=longest,"
              f"afade=t=out:st={T_TOTAL - 1.2:.3f}:d=1.2,atrim=0:{T_TOTAL:.3f},loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[a]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), *ins, "-filter_complex", ";".join(fl),
                    "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)],
                   check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true", help="960x540 快速预览")
    ap.add_argument("--still", type=float, nargs="*", help="只导出这些秒数的单帧")
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--end", type=float, default=T_TOTAL)
    args = ap.parse_args()

    if args.still:
        d = OUT.parent / "stills"
        d.mkdir(parents=True, exist_ok=True)
        for s in args.still:
            # 镜头是逐帧平滑的，单帧要从录屏段开头连续推进到该时刻
            if T_WALK <= s < T_STEP2:
                for k in range(int(T_WALK * FPS), int(s * FPS)):
                    scene_walk(k / FPS)
            p = d / f"longform_{s:05.1f}.png"
            frame_at(s).save(p)
            print(p)
        return

    out = OUT.with_name(OUT.stem + ("_preview" if args.preview else "") + ".mp4")
    out.parent.mkdir(parents=True, exist_ok=True)
    silent = out.with_suffix(".silent.mp4")
    sw, sh = (960, 540) if args.preview else (W, H)
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{sw}x{sh}", "-r", str(FPS),
                            "-i", "-", "-c:v", "libx264", "-preset", "veryfast" if args.preview else "slow", "-crf", "24" if args.preview else "17",
                            "-pix_fmt", "yuv420p", str(silent)], stdin=subprocess.PIPE)
    n0, n1 = int(args.start * FPS), int(args.end * FPS)
    for k in range(int(T_WALK * FPS) if args.start > T_WALK else n0, n0):  # 预热录屏镜头状态
        if T_WALK <= k / FPS < T_STEP2:
            scene_walk(k / FPS)
    for k in range(n0, n1):
        fr = frame_at(k / FPS)
        if (sw, sh) != (W, H):
            fr = fr.resize((sw, sh), Image.BILINEAR)
        enc.stdin.write(fr.tobytes())
        if k % (FPS * 10) == 0:
            print(f"  {k / FPS:5.1f}s", flush=True)
    enc.stdin.close()
    enc.wait()
    if args.start == 0 and args.end >= T_TOTAL:
        mix_audio(silent, out)
        silent.unlink()
    else:
        silent.rename(out)
    print(out)


if __name__ == "__main__":
    main()
