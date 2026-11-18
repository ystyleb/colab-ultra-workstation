#!/usr/bin/env python3
"""08 号第四批：多镜头「小故事」Shorts 合成器（本地 0 CCU）。

和 promo_short.py 的「四段式」不同，这里是一条时间线：
    镜头（H3 片段 / 本地生成的画面）依次排开，可选与上一段交叉淡化；
    叠加层（钩子字幕、旁白字幕、网址胶囊、AI 标注）按全片时间挂上去；
    音轨 = 配乐（可多段拼接、交叉淡化）+ 各镜头 H3 原声（按增益混进去），最后响度归一到 -14 LUFS。
产品真实性：画框里的画、商品页里的上身图、歌，都是站上真实产出；故事画面是 AI 生成的，片中标注。

    python3 workflows/08_site_channels/story_short.py pawmotif-intoframe
    python3 workflows/08_site_channels/story_short.py pawmotif-intoframe --preview   # 半分辨率快速预览
"""

from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Callable

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from promo_short import (FPS, H, HERE, STEP_Y, TS, TS_SCENES, SG, PM, W, contain, cover_fit, ease_out, ease_out_back, font,
                         paste_scaled, pill, rounded, wrap)

SAMPLES = HERE / "samples"
OUT = HERE / "out"


# ---------------- 时间线引擎 ----------------
@dataclass
class Seg:
    dur: float  # 本段在成片里的时长（秒，含与上一段重叠的淡化部分）
    clip: Path | None = None  # H3 片段；None 时用 gen
    t0: float = 0.0  # 片段入点（秒）
    gen: Callable[[int, int], Image.Image] | None = None  # (帧号, 总帧数) -> 1080x1920 RGB
    xfade: int = 0  # 与上一段交叉淡化的帧数
    native: float = 0.0  # H3 原声增益（0 = 静音）
    zoom: tuple[float, float] = (1.0, 1.0)  # 片段慢推：起止缩放
    y_bias: float = 0.5  # 768x1344 → 1080x1920 cover 裁切的纵向偏置


@dataclass
class Story:
    segs: list[Seg]
    overlays: list[Callable[[Image.Image, float], None]]  # (RGBA 画布, 全片秒数)
    music: list[tuple[Path, float, float]]  # [(文件, 入点, 出点)]，多段之间 0.4 s 交叉淡化
    music_gain: float = 1.0
    out: Path = OUT / "story" / "x.mp4"
    music_fade_in: float = 0.05


def clip_reader(clip: Path, t0: float, n: int, zoom=(1.0, 1.0), y_bias=0.5):
    """H3 768x1344 片段 → 1080x1920 cover（缩放到 1920 高再居中裁 1080 宽），可选慢推。"""
    sw = round(768 * 1920 / 1344)
    sw += sw % 2
    proc = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-ss", f"{t0:.3f}", "-i", str(clip), "-frames:v", str(n),
         "-vf", f"scale={sw}:1920:flags=lanczos", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        stdout=subprocess.PIPE,
    )
    last = None
    for i in range(n):
        buf = proc.stdout.read(sw * 1920 * 3)
        if len(buf) == sw * 1920 * 3:
            last = Image.frombytes("RGB", (sw, 1920), buf)
        if last is None:
            raise RuntimeError(f"读不到帧: {clip} @ {t0}")
        z = zoom[0] + (zoom[1] - zoom[0]) * (i / max(1, n - 1))
        cw, ch = W / z, H / z
        x0 = (sw - cw) / 2
        y0 = (1920 - ch) * y_bias
        yield last.crop((round(x0), round(y0), round(x0 + cw), round(y0 + ch))).resize((W, H), Image.LANCZOS)
    proc.stdout.close()
    proc.wait()


def render_frames(story: Story, scale: float = 1.0):
    """逐帧产出成片（RGB），并返回各段在成片里的起点（秒），给混音用。"""
    starts, t = [], 0.0
    for k, s in enumerate(story.segs):
        t -= (s.xfade / FPS) if k else 0
        starts.append(t)
        t += s.dur
    total = t

    def frames():
        gi = 0
        tail: list[Image.Image] = []
        for k, s in enumerate(story.segs):
            n = round(s.dur * FPS)
            nxt = story.segs[k + 1].xfade if k + 1 < len(story.segs) else 0
            src = clip_reader(s.clip, s.t0, n, s.zoom, s.y_bias) if s.clip else (s.gen(i, n) for i in range(n))
            new_tail: list[Image.Image] = []
            for i, fr in enumerate(src):
                if i < len(tail):  # 与上一段尾部交叉淡化
                    fr = Image.blend(tail[i], fr.convert("RGB"), (i + 1) / (len(tail) + 1))
                if i >= n - nxt:  # 本段最后 nxt 帧留给下一段淡化
                    new_tail.append(fr.convert("RGB"))
                    continue
                yield gi, fr
                gi += 1
            tail = new_tail

    def composed():
        for gi, fr in frames():
            img = fr.convert("RGBA")
            for ov in story.overlays:
                ov(img, gi / FPS)
            out = img.convert("RGB")
            if scale != 1.0:
                out = out.resize((round(W * scale) // 2 * 2, round(H * scale) // 2 * 2), Image.BILINEAR)
            yield out

    return composed(), starts, total


def mix_audio(story: Story, starts: list[float], total: float, video: Path, out: Path):
    ins, fl = [], []
    # 配乐：多段 atrim + acrossfade
    for j, (f, a, b) in enumerate(story.music):
        ins += ["-i", str(f)]
        fl.append(f"[{j + 1}:a]atrim={a:.3f}:{b:.3f},asetpts=PTS-STARTPTS,aformat=sample_rates=48000:channel_layouts=stereo[m{j}]")
    cur = "m0"
    for j in range(1, len(story.music)):
        fl.append(f"[{cur}][m{j}]acrossfade=d=0.4:c1=tri:c2=tri[mx{j}]")
        cur = f"mx{j}"
    fl.append(f"[{cur}]atrim=0:{total:.3f},volume={story.music_gain},afade=t=in:d={story.music_fade_in},"
              f"afade=t=out:st={total - 0.9:.3f}:d=0.9[music]")
    mixes = ["[music]"]
    idx = len(story.music) + 1
    for s, st in zip(story.segs, starts):
        if s.clip and s.native > 0:
            ins += ["-i", str(s.clip)]
            ms = int(st * 1000)
            fl.append(f"[{idx}:a]atrim={s.t0:.3f}:{s.t0 + s.dur:.3f},asetpts=PTS-STARTPTS,aformat=sample_rates=48000:channel_layouts=stereo,"
                      f"volume={s.native},afade=t=in:d=0.15,afade=t=out:st={max(0.0, s.dur - 0.25):.3f}:d=0.25,adelay={ms}|{ms}[n{idx}]")
            mixes.append(f"[n{idx}]")
            idx += 1
    fl.append(f"{''.join(mixes)}amix=inputs={len(mixes)}:normalize=0:duration=first,loudnorm=I=-14:TP=-1.5:LRA=11,"
              f"aresample=48000,atrim=0:{total:.3f}[a]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), *ins, "-filter_complex", ";".join(fl),
                    "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)],
                   check=True)


# ---------------- 叠加层小工具 ----------------
@lru_cache(maxsize=64)
def text_card(text: str, size: int, fam: str = "dmsans", weight: str = "Bold", color=(255, 255, 255), maxw: int = 900,
              shadow: int = 150, line_gap: float = 1.18) -> Image.Image:
    """居中多行字幕 + 柔和阴影（缓存），返回 RGBA。"""
    f = font(fam, size, weight)
    probe = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    lines = []
    for para in text.split("\n"):
        lines += wrap(probe, para, f, maxw)
    lh = int(size * line_gap)
    w = max(int(probe.textlength(l, font=f)) for l in lines) + 80
    h = lh * len(lines) + 60
    sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(sh)
    for k, l in enumerate(lines):
        d.text((w // 2, 30 + lh * k + lh // 2), l, font=f, fill=(0, 0, 0, shadow), anchor="mm")
    sh = sh.filter(ImageFilter.GaussianBlur(9))
    d = ImageDraw.Draw(sh)
    for k, l in enumerate(lines):
        d.text((w // 2, 30 + lh * k + lh // 2), l, font=f, fill=color + (255,), anchor="mm")
    return sh


def caption(text: str, t0: float, t1: float, cy: int, size: int = 64, fade: float = 0.18, **kw):
    def ov(img: Image.Image, t: float):
        if t0 <= t < t1:
            a = min(1.0, (t - t0) / fade, (t1 - t) / fade)
            card = text_card(text, size, **kw)
            if a < 1:
                card = card.copy()
                card.putalpha(card.getchannel("A").point(lambda v: int(v * a)))
            img.alpha_composite(card, ((W - card.width) // 2, cy - card.height // 2))
    return ov


def url_pill(text: str, t0: float, t1: float, fg, bg, fam: str = "dmsans"):
    def ov(img: Image.Image, t: float):
        if t0 <= t < t1:
            a = min(1.0, (t - t0) / 0.25)
            pill(ImageDraw.Draw(img), W // 2, 190, text, font(fam, 44, "Bold"), fg + (int(255 * a),), bg + (int(235 * a),), pad=(36, 18))
    return ov


def credit_pill(text: str, t0: float, t1: float, fg=(255, 255, 255), bg=(0, 0, 0), fam: str = "dmsans"):
    def ov(img: Image.Image, t: float):
        if t0 <= t < t1:
            pill(ImageDraw.Draw(img), W // 2, STEP_Y + 85, text, font(fam, 26, "Medium"), fg, bg + (190,), pad=(20, 8))
    return ov


def flash(t0: float, dur: float = 0.25, color=(255, 255, 255)):
    """白闪：魔法转场用。"""
    def ov(img: Image.Image, t: float):
        if t0 <= t < t0 + dur:
            a = 1 - abs((t - t0) / dur * 2 - 1)
            img.alpha_composite(Image.new("RGBA", img.size, color + (int(200 * a),)))
    return ov


# ---------------- PawMotif《Into the Frame》 ----------------
PMI = SAMPLES / "pawmotif_intoframe"
PM_PORTRAIT = SAMPLES / "pawmotif" / "pawmotif_doberman_fb_watercolor_full.jpg"  # 站上测试号用全身照真实生成的 Watercolor（红项圈和真狗一致）


def find_frame_opening(im: Image.Image) -> tuple[int, int, int, int]:
    """在 768x1344 关键帧里找画框内的留白（米色衬纸）区域：从中心向外扫，亮度掉下去的地方就是木框。"""
    g = im.convert("L")
    w, h = g.size
    cx, cy = w // 2 - 10, int(h * 0.30)
    ref = g.getpixel((cx, cy))

    def scan(x, y, dx, dy):
        while 0 < x < w - 1 and 0 < y < h - 1:
            if abs(g.getpixel((x, y)) - ref) > 28:
                return x, y
            x += dx
            y += dy
        return x, y

    left = scan(cx, cy, -1, 0)[0]
    right = scan(cx, cy, 1, 0)[0]
    top = scan(cx, cy, 0, -1)[1]
    bottom = scan(cx + 120, cy, 0, 1)[1]  # 偏右扫，避开狗头
    return left, top, right, bottom


def paste_portrait(kf: Path, dst: Path, opening=None, inset: int = 22):
    """把站上真实画像（衬纸留边）贴进关键帧的画框里。opening = 衬纸内区域 (l, t, r, b)，None 时自动找。"""
    im = Image.open(kf).convert("RGB")
    l, t, r, b = opening or find_frame_opening(im)
    l, t, r, b = l + inset, t + inset, r - inset, b - inset
    art = Image.open(PM_PORTRAIT).convert("RGB")
    s = min((r - l) / art.width, (b - t) / art.height)
    art = art.resize((round(art.width * s), round(art.height * s)), Image.LANCZOS)
    # 轻微压暗 + 跟随场景暖色，避免像贴纸
    art = Image.blend(art, Image.new("RGB", art.size, (236, 214, 180)), 0.06)
    x = l + (r - l - art.width) // 2
    y = t + (b - t - art.height) // 2
    sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rectangle((x + 3, y + 4, x + art.width + 3, y + art.height + 4), fill=(60, 40, 20, 70))
    im = Image.alpha_composite(im.convert("RGBA"), sh.filter(ImageFilter.GaussianBlur(3))).convert("RGB")
    im.paste(art, (x, y))
    im.save(dst)
    return (l, t, r, b)


def prep_pawmotif():
    kf = PMI / "kf"
    boxes = {}
    for n in ("pm_a", "pm_b", "pm_c"):
        boxes[n] = paste_portrait(kf / f"{n}_768x1344.png", kf / f"{n}_framed_768x1344.png")
        print(n, "opening", boxes[n])
    # 推镜尾帧：以画框为中心放大 ~1.7 倍
    im = Image.open(kf / "pm_c_framed_768x1344.png")
    l, t, r, b = boxes["pm_c"]
    cx, cy = (l + r) / 2, (t + b) / 2
    z = 1.7
    cw, ch = 768 / z, 1344 / z
    x0 = min(max(0, cx - cw / 2), 768 - cw)
    y0 = min(max(0, cy - ch / 2), 1344 - ch)
    im.crop((round(x0), round(y0), round(x0 + cw), round(y0 + ch))).resize((768, 1344), Image.LANCZOS).save(kf / "pm_c_zoom_768x1344.png")
    print("✅ pawmotif 关键帧已贴画")


def h3(sub: str, name: str) -> Path:
    return OUT / "samples" / sub / f"{name}_Master.mp4"


def pawmotif_endcard(photo_path: Path = SAMPLES / "pawmotif" / "pawmotif_doberman_fullbody_src.jpg", art_path: Path = PM_PORTRAIT,
                     art_label: str = "Watercolor", photo_x: int = 290, art_x: int = 790, art_box: tuple[int, int] = (400, 500),
                     photo_box: tuple[int, int] = (400, 500), arrow_x: int = 540,
                     photo_size: tuple[int, int] = (600, 760), photo_bias: float = 0.3):
    """落版：网址 + 「手机照片 → 站上画像」对照（说清楚产品是什么）+ 报价原文（brand.json offer.verbatim）。默认参数 = 第四批杜宾水彩。"""
    from promo_short import framed, pm_serif
    icon = rounded(Image.open(OUT / "pawmotif" / "avatar_800.png").convert("RGB").resize((190, 190), Image.LANCZOS), 95)
    photo = Image.open(photo_path).convert("RGB")  # 第四批杜宾原照车牌已打码
    ph = framed(cover_fit(photo, *photo_size, photo_bias), *photo_box)
    art = framed(Image.open(art_path).convert("RGB"), *art_box)
    sans = lambda n, w="SemiBold": font("dmsans", n, w)  # noqa: E731

    def gen(i: int, n: int) -> Image.Image:
        img = Image.new("RGBA", (W, H), PM["paper"] + (255,))
        d = ImageDraw.Draw(img)
        paste_scaled(img, icon, W // 2, 250, ease_out_back(i / 10))
        d.text((W // 2, 410), "PawMotif", font=pm_serif(118), fill=PM["ink"], anchor="mm")
        d.text((W // 2, 530), "pawmotif.com", font=sans(72, "Bold"), fill=PM["olive"], anchor="mm")
        paste_scaled(img, ph, photo_x, 860, ease_out((i - 4) / 8))
        paste_scaled(img, art, art_x, 860, ease_out((i - 9) / 8))
        d.text((arrow_x, 860), "→", font=sans(80, "Bold"), fill=PM["olive"], anchor="mm")
        d.text((photo_x, 1125), "Your photo", font=sans(34, "Medium"), fill=PM["muted"], anchor="mm")
        d.text((art_x, 1125), art_label, font=sans(34, "Medium"), fill=PM["muted"], anchor="mm")
        pill(d, W // 2, 1235, "Preview your portrait free", sans(44, "Bold"), PM["white"], PM["olive"], pad=(40, 20))
        d.text((W // 2, 1330), "No card needed until you decide to buy.", font=sans(34, "Medium"), fill=PM["ink"], anchor="mm")
        d.text((W // 2, 1385), "$29 USD · one-time digital artwork", font=sans(34, "Medium"), fill=PM["ink"], anchor="mm")
        return img.convert("RGB")
    return gen


def pawmotif_intoframe(take: dict[str, int] | None = None) -> Story:
    """《Into the Frame》：杜宾盯着墙上自己的画像 → 一跃钻进画里 → 画里的它冲你眨眼 → 客厅只剩狗绳。"""
    t = {"meet": 1, "leap": 2, "alive": 2, "empty": 2} | (take or {})  # 选片见 README 第四批
    sub = "pawmotif_story"
    segs = [
        Seg(5.2, h3(sub, f"PM_S1_Meet_T{t['meet']}"), t0=0.25, native=0.35),
        # T2 第 153 帧后是 38 帧定格（已成画），只用到 0.3+6.0 s；下一镜首帧就是同一幅画，直接硬切无缝
        Seg(6.0, h3(sub, f"PM_S2_Leap_T{t['leap']}"), t0=0.3, native=0.6),
        Seg(4.6, h3(sub, f"PM_S3_Alive_T{t['alive']}"), t0=0.25, native=0.4),
        Seg(4.4, h3(sub, f"PM_S4_Empty_T{t['empty']}"), t0=0.25, native=0.4),
        Seg(3.6, gen=pawmotif_endcard(), xfade=5),
    ]
    b = [0.0]
    for s in segs[:-1]:
        b.append(b[-1] + s.dur)
    b[-1] -= segs[-1].xfade / FPS
    s2, s3, s4, s5 = b[1], b[2], b[3], b[4]
    cy = 1400
    ov = [
        caption("We hung his portrait.", 0.25, 2.6, cy),
        caption("He had questions.", 2.6, 5.1, cy),
        flash(s4 - 0.12, 0.3),
        caption("He went in.", s2 + 4.2, s4 - 0.1, cy),  # 跃起后第 ~4.5 s 身体开始化成水彩
        caption("He's not coming out.", s4 + 0.4, s5, cy),
        url_pill("pawmotif.com", s3, s5, PM["white"], PM["olive"]),
        credit_pill("Portrait: PawMotif  ·  Scenes & motion: AI video", 0.0, s5),
    ]
    return Story(segs, ov, music=[(OUT / "bgm" / "pawmotif" / "bgm_v1.mp3", 0.0, 40.0)], music_gain=0.9,
                 out=OUT / "promo" / "pawmotif" / "PawMotif_Story_IntoTheFrame_1080x1920.mp4")


# ---------------- TryOnSwap《The Photoshoot That Never Happened》 ----------------
TSP = SAMPLES / "tryonswap_photoshoot"
COURIER = "/System/Library/Fonts/Supplemental/Courier New.ttf"
COURIER_B = "/System/Library/Fonts/Supplemental/Courier New Bold.ttf"


def ts_quote_insert():
    """报价单特写（本地画，字清楚）：逐行打出，最后红笔圈总价。数字是示意的典型报价，片中写 Example quote。"""
    from PIL import ImageFont
    rows = [("Model (half day)", "$800"), ("Studio rental", "$900"), ("Photographer", "$700")]
    fm, fb = ImageFont.truetype(COURIER, 40), ImageFont.truetype(COURIER_B, 46)
    paper = Image.new("RGBA", (800, 900), (250, 247, 240, 255))
    pd = ImageDraw.Draw(paper)
    pd.text((400, 110), "PHOTOSHOOT QUOTE", font=fb, fill=(30, 30, 30), anchor="mm")
    pd.text((400, 170), "1 product · on-model images", font=fm, fill=(90, 90, 90), anchor="mm")
    pd.line((60, 220, 740, 220), fill=(40, 40, 40), width=3)
    bg = Image.open(TSP / "kf" / "ts_a_768x1344.png").convert("RGB")
    bg = cover_fit(bg, W, H).filter(ImageFilter.GaussianBlur(18))
    bg = Image.blend(bg, Image.new("RGB", (W, H), (20, 14, 10)), 0.45).convert("RGBA")

    def gen(i: int, n: int) -> Image.Image:
        p = paper.copy()
        d = ImageDraw.Draw(p)
        shown = min(len(rows) + 1, int(i / 7))
        for k, (a, b) in enumerate(rows[: min(shown, len(rows))]):
            y = 300 + k * 110
            d.text((70, y), a, font=fm, fill=(30, 30, 30), anchor="lm")
            d.text((730, y), b, font=fm, fill=(30, 30, 30), anchor="rm")
        if shown > len(rows):
            d.line((60, 630, 740, 630), fill=(40, 40, 40), width=3)
            d.text((70, 720), "TOTAL", font=fb, fill=(20, 20, 20), anchor="lm")
            d.text((730, 720), "$2,400", font=fb, fill=(20, 20, 20), anchor="rm")
            prog = min(1.0, max(0.0, (i - 7 * (len(rows) + 1) - 3) / 8))
            if prog > 0:
                d.arc((480, 650, 770, 790), start=200, end=200 + 340 * prog, fill=(205, 40, 35), width=8)
        d.text((400, 860), "Example quote", font=ImageFont.truetype(COURIER, 28), fill=(140, 140, 140), anchor="mm")
        z = 1.0 + 0.06 * i / n
        pr = p.resize((round(800 * z), round(900 * z)), Image.LANCZOS).rotate(-3, expand=True, resample=Image.BICUBIC)
        img = bg.copy()
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rectangle(((W - pr.width) // 2 + 20, 900 - pr.height // 2 + 30, (W + pr.width) // 2 + 20, 900 + pr.height // 2 + 30),
                                     fill=(0, 0, 0, 120))
        img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(25)))
        img.alpha_composite(pr, ((W - pr.width) // 2, 900 - pr.height // 2))
        return img.convert("RGB")
    return gen


def ts_product():
    """产品动作：手机拍的平铺图 → TryOnSwap → 6 个 Scene 预设的上身图依次弹出（全部站长账号在站上真实生成，2026-11-12）。"""
    serif = lambda n: font("cormorant", n, "SemiBold")  # noqa: E731
    sans = lambda n, w="SemiBold": font("manrope", n, w)  # noqa: E731
    flat = rounded(contain(Image.open(SAMPLES / "tryonswap" / "tryonswap_g-knit.webp"), 420, 420, (246, 243, 237)), 26)
    cw, ch = 290, 516
    cards = []
    for key, label in TS_SCENES:
        c = cover_fit(Image.open(SAMPLES / "tryonswap" / "campaign" / f"tryonswap_knit_{key}_2k.jpg").convert("RGB"), cw, ch, 0.3).convert("RGBA")
        g = Image.new("RGBA", (cw, 90), (0, 0, 0, 0))
        for y in range(90):
            ImageDraw.Draw(g).line((0, y, cw, y), fill=(0, 0, 0, int(170 * y / 90)))
        c.alpha_composite(g, (0, ch - 90))
        ImageDraw.Draw(c).text((cw // 2, ch - 32), label, font=sans(26, "Bold"), fill=TS["ivory"], anchor="mm")
        cards.append(rounded(c, 20))
    pos = [(205 + (k % 3) * (cw + 20), 590 + (k // 3) * (ch + 20) + ch // 2 - 30) for k in range(6)]

    def gen(i: int, n: int) -> Image.Image:
        img = Image.new("RGBA", (W, H), TS["bg"] + (255,))
        d = ImageDraw.Draw(img)
        t = i / FPS
        if t < 1.3:
            d.text((W // 2, 360), "One flat photo", font=serif(104), fill=TS["ivory"], anchor="mm")
            paste_scaled(img, flat, W // 2, 820, ease_out_back(i / 9))
            if t > 0.6:
                a = int(255 * min(1.0, (t - 0.6) / 0.2))
                pill(d, W // 2, 1180, "Generate  →", sans(52, "Bold"), TS["bg"] + (a,), TS["gold"] + (a,), pad=(46, 22))
        else:
            d.text((W // 2, 360), "Six on-model shots", font=serif(104), fill=TS["gold"], anchor="mm")
            for k, (c, (cx, cy)) in enumerate(zip(cards, pos)):
                paste_scaled(img, c, cx, cy, ease_out_back((t - 1.3 - k * 0.22) / 0.35))
        return img.convert("RGB")
    return gen


def tryonswap_endcard():
    serif = lambda n: font("cormorant", n, "SemiBold")  # noqa: E731
    sans = lambda n, w="SemiBold": font("manrope", n, w)  # noqa: E731
    icn = Image.open(SAMPLES / "tryonswap" / "tryonswap_icon_512.png").convert("RGBA").resize((200, 200), Image.LANCZOS)

    def gen(i: int, n: int) -> Image.Image:
        img = Image.new("RGBA", (W, H), TS["bg"] + (255,))
        d = ImageDraw.Draw(img)
        paste_scaled(img, icn, W // 2, 470, ease_out_back(i / 10))
        d.text((W // 2, 700), "TryOnSwap", font=serif(150), fill=TS["ivory"], anchor="mm")
        d.text((W // 2, 850), "tryonswap.com", font=sans(78, "Bold"), fill=TS["gold"], anchor="mm")
        d.text((W // 2, 990), "On-model photos from one product photo.", font=sans(40, "Medium"), fill=TS["ivory"], anchor="mm")
        pill(d, W // 2, 1130, "12 FREE CREDITS ON SIGN-UP", sans(44, "Bold"), TS["bg"], TS["ivory"], pad=(40, 20))
        for k, line in enumerate(["New accounts receive 12 credits after email verification,", "enough for up to 3 basic images.",
                                  "Priced per image, no subscription."]):
            d.text((W // 2, 1240 + k * 50), line, font=sans(32, "Medium"), fill=TS["muted"], anchor="mm")
        return img.convert("RGB")
    return gen


def tryonswap_photoshoot(take: dict[str, int] | None = None) -> Story:
    """《The Photoshoot That Never Happened》：深夜卖家看到 $2,400 拍摄报价 → 揉掉 → 手机拍平铺图 → TryOnSwap 出 6 张上身图 → 举杯。"""
    t = {"quote": 1, "flat": 1, "street": 2, "cheers": 1} | (take or {})  # Street T2 第 130 帧硬切回远景，只用 0.3–3.3 s
    sub = "tryonswap_story"
    q = h3(sub, f"TS_S1_Quote_T{t['quote']}")
    segs = [
        Seg(2.8, q, t0=0.25, native=0.6),
        Seg(2.2, gen=ts_quote_insert()),
        Seg(2.6, q, t0=3.1, native=0.6),
        Seg(2.8, h3(sub, f"TS_S2_FlatLay_T{t['flat']}"), t0=0.3, native=0.6),
        Seg(4.2, gen=ts_product()),
        Seg(3.0, h3(sub, f"TS_S3_Street_T{t['street']}"), t0=0.3, native=0.3),
        Seg(4.4, h3(sub, f"TS_S4_Cheers_T{t['cheers']}"), t0=1.0, native=0.5),
        Seg(3.4, gen=tryonswap_endcard(), xfade=8),
    ]
    b = [0.0]
    for s in segs[:-1]:
        b.append(b[-1] + s.dur)
    b[-1] -= 8 / FPS
    cy = 1400
    ov = [
        caption("Photoshoot quote for ONE sweater:", 0.25, b[1], cy),
        caption("Nope.", b[2] + 1.2, b[3], cy, size=80),
        caption("One phone photo instead.", b[3] + 0.2, b[4], cy),
        caption("No model. No studio.", b[5] + 0.1, b[6], cy),
        caption("Still got the shot.", b[6] + 0.8, b[7], cy),
        url_pill("tryonswap.com", b[4], b[7], TS["bg"], TS["ivory"], fam="manrope"),
        credit_pill("Images: TryOnSwap  ·  Scenes & motion: AI video  ·  The model is AI-generated", 0.0, b[7], fam="manrope"),
    ]
    return Story(segs, ov, music=[(OUT / "bgm" / "tryonswap" / "bgm_v1.mp3", 12.8, 60.0)], music_gain=0.85,
                 out=OUT / "promo" / "tryonswap" / "TryOnSwap_Story_Photoshoot_1080x1920.mp4")


# ---------------- Songifted《It Was Not Nothing》（她写给他） ----------------
SGD = SAMPLES / "songifted_danny"
# /demos/for-husband.mp3（站上 /custom-song-for-husband 示例歌，虚构名字 Danny）。mlx_whisper small 时间戳（整首识别，不带上文条件）
SGH_A = (52.40, 72.95)  # 第一段：「So I put it in the song myself」→ 副歌 → 「It was not nothing」
SGH_B0 = 175.90  # 第二段：尾声「Danny … Go on, make the joke now」，0.4 s 交叉淡化接上
SGH_LYRICS = [  # (歌内秒, 歌内秒, 歌词)
    (52.70, 56.96, "So I put it in the song myself"),
    (58.64, 61.48, "Danny, don't make a joke yet"),
    (61.48, 63.84, "Four more lines and then it's yours"),
    (63.84, 66.88, "You went out in the dark that January"),
    (67.94, 70.14, "And you said it was nothing"),
    (70.84, 72.76, "It was not nothing"),
]
SGH_TAG = (178.28, 181.14, "Go on, make the joke now")


def sg_brief(title: tuple[str, str] = ("She told the story", "he never tells."),
             brief: str = "January. 2 a.m. My car was buried in snow. Danny went out and dug it out, and said it was nothing.",
             card_bottom: int = 1250, label: str = "Tell us about him"):
    """「Tell us about him」输入卡（还原 /create 的故事输入步骤，本地画）：标题两行 + 逐字打出用户写的故事。默认 = 第四批 Danny。"""
    serif = lambda n, w="SemiBold": font("fraunces", n, w)  # noqa: E731
    sans = lambda n, w="SemiBold": font("dmsans", n, w)  # noqa: E731
    bg = Image.new("RGBA", (W, H))
    for y in range(H):
        ImageDraw.Draw(bg).line((0, y, W, y), fill=tuple(int(a + (b - a) * y / H) for a, b in zip(SG["cream"], SG["cream2"])) + (255,))

    def gen(i: int, n: int) -> Image.Image:
        img = bg.copy()
        d = ImageDraw.Draw(img)
        a = int(255 * ease_out(i / 8))
        d.text((W // 2, 360), title[0], font=serif(88), fill=SG["ink"] + (a,), anchor="mm")
        d.text((W // 2, 470), title[1], font=serif(88), fill=SG["coral"] + (a,), anchor="mm")
        x0, y0, x1, y1 = 90, 600, W - 90, card_bottom
        d.rounded_rectangle((x0 + 6, y0 + 10, x1 + 6, y1 + 10), radius=34, fill=(120, 80, 60, 40))
        d.rounded_rectangle((x0, y0, x1, y1), radius=34, fill=SG["white"] + (255,))
        d.text((x0 + 56, y0 + 62), label, font=sans(34, "Bold"), fill=SG["muted"], anchor="lm")
        k = int(len(brief) * min(1.0, max(0.0, (i - 3) / (n - 26))))
        f = serif(54, "Regular")
        y, line = 720, ""
        for line in wrap(d, brief[:k], f, W - 300):
            d.text((150, y), line, font=f, fill=SG["ink"], anchor="la")
            y += 78
        if (i // 6) % 2 == 0 and k < len(brief):
            cx = 150 + d.textlength(line, font=f) + 6
            d.rectangle((cx, y - 72, cx + 4, y - 14), fill=SG["coral"])
        return img.convert("RGB")
    return gen


def songifted_endcard(tagline: str = "A song with his name in it."):
    serif = lambda n, w="SemiBold": font("fraunces", n, w)  # noqa: E731
    sans = lambda n, w="SemiBold": font("dmsans", n, w)  # noqa: E731
    icon = rounded(Image.open(OUT / "songifted" / "avatar_800.png").convert("RGB").resize((200, 200), Image.LANCZOS), 100)
    bg = Image.new("RGBA", (W, H))
    for y in range(H):
        ImageDraw.Draw(bg).line((0, y, W, y), fill=tuple(int(a + (b - a) * y / H) for a, b in zip(SG["cream"], SG["cream2"])) + (255,))

    def gen(i: int, n: int) -> Image.Image:
        img = bg.copy()
        d = ImageDraw.Draw(img)
        paste_scaled(img, icon, W // 2, 560, ease_out_back(i / 10))
        d.text((W // 2, 790), "Songifted", font=serif(150), fill=SG["ink"], anchor="mm")
        d.text((W // 2, 940), "songifted.com", font=sans(78, "Bold"), fill=SG["coral"], anchor="mm")
        d.text((W // 2, 1090), tagline, font=sans(46, "Medium"), fill=SG["ink"], anchor="mm")
        pill(d, W // 2, 1240, "Free 45-second preview", sans(46, "Bold"), SG["white"], SG["coral"], pad=(40, 20))
        d.text((W // 2, 1340), "for eligible first-time creators", font=sans(32, "Medium"), fill=SG["muted"], anchor="mm")
        return img.convert("RGB")
    return gen


def lyric(text: str, t0: float, t1: float, name: str = "Danny", cy: int = 1330):
    """歌词字幕：深色半透明底条 + 名字高亮。"""
    serif = lambda n, w="SemiBold": font("fraunces", n, w)  # noqa: E731

    @lru_cache(maxsize=1)
    def band():
        probe = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
        sz = 64  # 先缩字号争取一行放下（最小 50），放不下再折行
        while sz > 50 and probe.textlength(text, font=serif(sz, "Bold")) > W - 220:
            sz -= 2
        f, fb = serif(sz), serif(sz, "Bold")
        lines = wrap(probe, text, fb, W - 220)
        b = Image.new("RGBA", (W, 100 * len(lines) + 70), (0, 0, 0, 0))
        d = ImageDraw.Draw(b)
        d.rounded_rectangle((70, 0, W - 70, b.height - 1), radius=36, fill=(43, 29, 22, 150))
        for r, line in enumerate(lines):
            segs = []
            for wtok in line.split(" "):
                segs.append((wtok + " ", fb if name in wtok else f, (255, 168, 140) if name in wtok else (255, 255, 255)))
            x = (W - sum(d.textlength(s, font=ff) for s, ff, _ in segs)) / 2
            for s, ff, c in segs:
                d.text((x, 85 + r * 100), s, font=ff, fill=c, anchor="ls")
                x += d.textlength(s, font=ff)
        return b

    def ov(img: Image.Image, t: float):
        if t0 - 0.08 <= t < t1:
            a = min(1.0, (t - t0 + 0.08) / 0.15, (t1 - t) / 0.15)
            b = band()
            if a < 1:
                b = b.copy()
                b.putalpha(b.getchannel("A").point(lambda v: int(v * a)))
            img.alpha_composite(b, (0, cy - b.height // 2))
    return ov


def songifted_danny(take: dict[str, int] | None = None) -> Story:
    """《It Was Not Nothing》：她深夜写下他从不提的那件事 → 歌响起「Danny, don't make a joke yet」→ 雪夜闪回 → 他哭了 → 「Go on, make the joke now」。"""
    t = {"typing": 1, "notyet": 1, "snow": 1, "keys": 2, "tears": 1, "hug": 1} | (take or {})
    sub = "songifted_story"
    a0 = SGH_A[0]
    cut = [0.0, 3.0, 58.64 - a0, 63.84 - a0, 66.90 - a0, 70.14 - a0, SGH_A[1] - a0]  # 镜头切点卡在歌词换句处
    segs = [
        Seg(cut[1] - cut[0], h3(sub, f"SG_S1_Typing_T{t['typing']}"), t0=0.3, native=0.0),
        Seg(cut[2] - cut[1], gen=sg_brief()),
        Seg(cut[3] - cut[2], h3(sub, f"SG_S2_NotYet_T{t['notyet']}"), t0=0.3, native=0.0),
        Seg(cut[4] - cut[3], h3(sub, f"SG_S3_Snow_T{t['snow']}"), t0=0.5, native=0.35),
        Seg(cut[5] - cut[4], h3(sub, f"SG_S4_Keys_T{t['keys']}"), t0=0.4, native=0.15),
        Seg(cut[6] - cut[5], h3(sub, f"SG_S5_Tears_T{t['tears']}"), t0=0.4, native=0.0),
        Seg(5.4, h3(sub, f"SG_S6_Hug_T{t['hug']}"), t0=0.3, native=0.6),
        Seg(3.0, gen=songifted_endcard(), xfade=8),
    ]
    b_off = cut[6] - 0.4 - SGH_B0  # 第二段歌内秒 → 成片秒
    end = cut[6] + 5.4 - 8 / FPS
    ov = [caption("He always says\n“it was nothing.”", 0.2, cut[1], 360, size=76, fam="fraunces", weight="SemiBold")]
    ov += [lyric(txt, s0 - a0, s1 - a0) for s0, s1, txt in SGH_LYRICS]
    ov += [lyric(SGH_TAG[2], SGH_TAG[0] + b_off, SGH_TAG[1] + b_off),
           url_pill("songifted.com", cut[1], end, SG["white"], SG["coral"]),
           credit_pill("Example song from songifted.com (fictional \"Danny\")  ·  Scene: AI dramatization", 0.0, end)]
    music_end = SGH_B0 + (end + 3.0 - (cut[6] - 0.4)) + 0.5
    return Story(segs, ov, music=[(SAMPLES / "songifted" / "demos" / "for-husband.mp3", a0, SGH_A[1]),
                                  (SAMPLES / "songifted" / "demos" / "for-husband.mp3", SGH_B0, music_end)],
                 out=OUT / "promo" / "songifted" / "Songifted_Story_NotNothing_1080x1920.mp4")


# 第五批起画面里不放 AI 标注胶囊（2026-11-16 用户定）：AI 声明走 YouTube 上传的 Altered or synthetic content = Yes，
# 加上发布包各平台文案里原样写的 disclosure.credit_line（ops validate 会校验）。
# ---------------- 第五批（2026-11-16）：PawMotif《Under the Tree》/ TryOnSwap《Model Cancelled》/ Songifted《Porch Light》 ----------------
B5 = SAMPLES / "inputs_1116"  # 站上真实产出 + 喂给站的 AI 输入图（金毛照、圣诞毛衣平铺）
PT = SAMPLES / "pawmotif_tree"
PM_OIL = B5 / "golden_oil_full.jpg"  # 测试号用 golden_src.jpg 在 /portraits/old-world 真实生成（job 1867f515），5024x3360
# 画布种子点（768x1344 关键帧里空白米色画布内的一点），floodfill 从这里按颜色容差长出画布区域
PT_SEEDS = {"pt_b": (380, 520), "pt_c": (436, 600), "pt_d": (432, 590), "pt_e": (390, 330)}


def paste_into_canvas(kf: Path, dst: Path, art_path: Path, seed: tuple[int, int], tol: int = 120, focus_x: float = 0.45):
    """把站上真实画像贴进关键帧里的空白画布。

    和 paste_portrait 不同：画布区域用 floodfill 求出来（不是扫描矩形），前景遮挡物（比如压在画框下沿的狗头）
    颜色和米色画布差很多，自然不在区域里，贴画时保留。返回画布外接框 (l, t, r, b)。
    """
    im = Image.open(kf).convert("RGB")
    probe = im.copy()
    ImageDraw.floodfill(probe, seed, (255, 0, 255), thresh=tol)
    diff = ImageChops.difference(probe, Image.new("RGB", im.size, (255, 0, 255))).convert("L")
    mask = diff.point(lambda v: 255 if v == 0 else 0)
    # 闭运算补画布纹理里的小洞，不外扩
    mask = mask.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.MinFilter(5))
    l, t, r, b = mask.getbbox()
    art = Image.open(art_path).convert("RGB")
    bw, bh = r - l, b - t
    s = max(bw / art.width, bh / art.height)
    art = art.resize((round(art.width * s), round(art.height * s)), Image.LANCZOS)
    x0 = round((art.width - bw) * focus_x)
    y0 = (art.height - bh) // 2
    art = art.crop((x0, y0, x0 + bw, y0 + bh))
    art = Image.blend(art, Image.new("RGB", art.size, (236, 214, 180)), 0.06)  # 跟场景暖色，避免像贴纸
    layer = Image.new("RGB", im.size)
    layer.paste(art, (l, t))
    im.paste(layer, (0, 0), mask.filter(ImageFilter.GaussianBlur(0.8)))
    im.save(dst)
    return l, t, r, b


def zoom_on(src: Path, dst: Path, box, z: float):
    """推镜尾帧：以 box 为中心放大 z 倍（裁切后缩回 768x1344）。"""
    im = Image.open(src)
    l, t, r, b = box
    cx, cy = (l + r) / 2, (t + b) / 2
    cw, ch = 768 / z, 1344 / z
    x0 = min(max(0, cx - cw / 2), 768 - cw)
    y0 = min(max(0, cy - ch / 2), 1344 - ch)
    im.crop((round(x0), round(y0), round(x0 + cw), round(y0 + ch))).resize((768, 1344), Image.LANCZOS).save(dst)


def prep_batch5():
    kf = PT / "kf"
    boxes = {}
    for n, seed in PT_SEEDS.items():
        boxes[n] = paste_into_canvas(kf / f"{n}_768x1344.png", kf / f"{n}_framed_768x1344.png", PM_OIL, seed)
        print(n, "canvas", boxes[n])
    zoom_on(kf / "pt_e_framed_768x1344.png", kf / "pt_e_zoom_768x1344.png", boxes["pt_e"], 1.6)
    # TryOnSwap：站长账号真实生成的 Custom 雪夜街景（1536x2752）→ H3 输入尺寸
    tc = SAMPLES / "tryonswap_cancelled"
    cover_fit(Image.open(B5 / "ts_xmas_snow_2k.jpg").convert("RGB"), 768, 1344, 0.4).save(tc / "ts_xmas_snow_768x1344.png")
    print("✅ 第五批关键帧已贴画 / 已缩放")


def seg_starts(segs: list[Seg]) -> list[float]:
    """各段在成片里的起点（秒，已扣掉 xfade 重叠），末尾追加全片总长。"""
    b, t = [], 0.0
    for k, s in enumerate(segs):
        t -= (s.xfade / FPS) if k else 0
        b.append(t)
        t += s.dur
    return b + [t]


def pawmotif_tree(take: dict[str, int] | None = None) -> Story:
    """《Under the Tree》：圣诞早晨她递给他一个扁礼盒 → 是他家金毛的 Old World 油画 → 金毛跑来趴在画前摆出同样姿势 → 晚上画挂在壁炉上，画里的狗冲你眨眼。"""
    # 选片（帧差 + 抽帧目检，2026-11-16）：Reveal T1、Mirror T1 都自己推近景，选 T2；Gift 两条中段都平滑推到男主，T1 晃礼盒更好
    t = {"gift": 1, "reveal": 2, "mirror": 2, "mantel": 1} | (take or {})
    sub = "pawmotif_story5"
    segs = [
        Seg(5.2, h3(sub, f"PT_S1_Gift_T{t['gift']}"), t0=0.3, native=0.45),
        Seg(4.2, h3(sub, f"PT_S2_Reveal_T{t['reveal']}"), t0=0.3, native=0.4),
        Seg(5.6, h3(sub, f"PT_S3_Mirror_T{t['mirror']}"), t0=0.25, native=0.5),
        Seg(5.2, h3(sub, f"PT_S4_Mantel_T{t['mantel']}"), t0=0.25, native=0.35),
        Seg(3.8, gen=pawmotif_endcard(B5 / "golden_src.jpg", PM_OIL, "Old World oil", photo_x=215, art_x=725, arrow_x=432,
                                      photo_box=(380, 360), art_box=(560, 430), photo_size=(760, 600), photo_bias=0.55), xfade=6),
    ]
    b = seg_starts(segs)
    cy = 1400
    ov = [
        caption("Christmas morning.", 0.3, 2.3, cy),
        caption("She couldn't exactly\nwrap the dog…", 2.3, b[1], cy),
        caption("…so she wrapped his portrait.", b[1] + 0.3, b[2], cy),
        caption("Bear approves.", b[2] + 3.6, b[3], cy, size=80),
        caption("Painted from one phone photo.", b[3] + 0.4, b[4], cy),
        url_pill("pawmotif.com", b[2], b[4], PM["white"], PM["olive"]),
    ]
    return Story(segs, ov, music=[(OUT / "bgm" / "pawmotif_tree" / "bgm_v1.mp3", 0.0, 40.0)], music_gain=0.85,
                 out=OUT / "promo" / "pawmotif" / "PawMotif_Story_UnderTheTree_1080x1920.mp4")


# ---- TryOnSwap《Model Cancelled》 ----
TCD = SAMPLES / "tryonswap_cancelled"
TS_XMAS = [("snow", "Snowy street"), ("cozy", "Holiday home"), ("street", "Street style")]  # 站长账号 2026-11-16 真实生成（Custom×2 + Street style）


def ts_msg_insert():
    """模特取消拍摄的消息（本地画的示意聊天界面，片中写 Example message）：两条气泡依次弹出。"""
    sans = lambda n, w="Medium": font("manrope", n, w)  # noqa: E731
    bg = cover_fit(Image.open(TCD / "kf" / "tc_a_768x1344.png").convert("RGB"), W, H).filter(ImageFilter.GaussianBlur(20))
    bg = Image.blend(bg, Image.new("RGB", (W, H), (10, 10, 14)), 0.5).convert("RGBA")
    msgs = ["hey… I'm so sorry", "I can't make tomorrow's shoot. something came up"]  # 不用 emoji：字体里没有，会出豆腐块
    ph_w, ph_h = 760, 860
    phone = Image.new("RGBA", (ph_w, ph_h), (0, 0, 0, 0))
    pd = ImageDraw.Draw(phone)
    pd.rounded_rectangle((0, 0, ph_w - 1, ph_h - 1), radius=70, fill=(18, 18, 20, 255))
    pd.rounded_rectangle((14, 14, ph_w - 15, ph_h - 15), radius=58, fill=(250, 250, 252, 255))
    pd.rectangle((14, 90, ph_w - 15, 230), fill=(242, 242, 246, 255))
    pd.ellipse((ph_w // 2 - 42, 104, ph_w // 2 + 42, 188), fill=(196, 170, 150, 255))
    pd.text((ph_w // 2, 146), "J", font=sans(46, "Bold"), fill=(255, 255, 255), anchor="mm")
    pd.text((ph_w // 2, 212), "Jess · Model", font=sans(30, "SemiBold"), fill=(30, 30, 30), anchor="mm")
    pd.text((ph_w // 2, 290), "Wed 11:42 PM", font=sans(26), fill=(140, 140, 146), anchor="mm")

    def bubble(text: str) -> Image.Image:
        f = sans(40)
        probe = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
        lines = wrap(probe, text, f, 480)
        bw = max(int(probe.textlength(l, font=f)) for l in lines) + 64
        bh = 56 * len(lines) + 40
        im = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle((0, 0, bw - 1, bh - 1), radius=34, fill=(229, 229, 234, 255))
        for k, l in enumerate(lines):
            d.text((32, 20 + 56 * k), l, font=f, fill=(20, 20, 20), anchor="la")
        return im
    bubbles = [bubble(m) for m in msgs]

    def gen(i: int, n: int) -> Image.Image:
        img = bg.copy()
        p = phone.copy()
        y = 350
        for k, bb in enumerate(bubbles):
            s = ease_out_back((i - 4 - k * 14) / 6)
            if s > 0.01:
                sb = bb.resize((max(1, round(bb.width * s)), max(1, round(bb.height * s))), Image.LANCZOS)
                p.alpha_composite(sb, (44, y))
            y += bb.height + 22
        ImageDraw.Draw(p).text((ph_w // 2, ph_h - 60), "Example message", font=sans(24), fill=(160, 160, 166), anchor="mm")
        img.alpha_composite(p, ((W - ph_w) // 2, 420))
        return img.convert("RGB")
    return gen


def ts_product5(switch: float = 1.0, flat_path: Path | None = None, items: list[tuple[Path, str]] | None = None,
                after: str = "On-model. Any scene."):
    """产品动作：平铺照 → Generate → 站上真实生成的 3 张上身图依次弹出。switch = 结果弹出时刻（段内秒），对齐配乐 drop。
    默认参数 = 第五批圣诞毛衣；items = [(上身图, 标签)] × 3。"""
    serif = lambda n: font("cormorant", n, "SemiBold")  # noqa: E731
    sans = lambda n, w="SemiBold": font("manrope", n, w)  # noqa: E731
    flat = rounded(contain(Image.open(flat_path or B5 / "sweater_src.jpg"), 440, 600, (246, 243, 237)), 26)
    items = items or [(B5 / f"ts_xmas_{key}_2k.jpg", label) for key, label in TS_XMAS]
    cw, ch = 320, 572
    cards = []
    for path, label in items:
        c = cover_fit(Image.open(path).convert("RGB"), cw, ch, 0.3).convert("RGBA")
        g = Image.new("RGBA", (cw, 90), (0, 0, 0, 0))
        for y in range(90):
            ImageDraw.Draw(g).line((0, y, cw, y), fill=(0, 0, 0, int(170 * y / 90)))
        c.alpha_composite(g, (0, ch - 90))
        ImageDraw.Draw(c).text((cw // 2, ch - 32), label, font=sans(28, "Bold"), fill=TS["ivory"], anchor="mm")
        cards.append(rounded(c, 20))
    pos = [(W // 2 + (k - 1) * (cw + 18), 900) for k in range(3)]

    def gen(i: int, n: int) -> Image.Image:
        img = Image.new("RGBA", (W, H), TS["bg"] + (255,))
        d = ImageDraw.Draw(img)
        t = i / FPS
        if t < switch:
            d.text((W // 2, 380), "One flat photo", font=serif(104), fill=TS["ivory"], anchor="mm")
            paste_scaled(img, flat, W // 2, 860, ease_out_back(i / 8))
            if t > switch * 0.45:
                a = int(255 * min(1.0, (t - switch * 0.45) / 0.2))
                pill(d, W // 2, 1230, "Generate  →", sans(52, "Bold"), TS["bg"] + (a,), TS["gold"] + (a,), pad=(46, 22))
        else:
            d.text((W // 2, 380), after, font=serif(96), fill=TS["gold"], anchor="mm")
            for k, (c, (cx, cy)) in enumerate(zip(cards, pos)):
                paste_scaled(img, c, cx, cy, ease_out_back((t - switch - k * 0.25) / 0.35))
        return img.convert("RGB")
    return gen


def ts_orders(t0: float, t1: float = 1e9):
    """上线后订单通知依次滑入（示意，标 Example）。"""
    sans = lambda n, w="SemiBold": font("manrope", n, w)  # noqa: E731
    thumb = rounded(cover_fit(Image.open(B5 / "ts_xmas_snow_2k.jpg").convert("RGB"), 84, 84, 0.25), 16)
    cards = []
    for k, when in enumerate(["just now", "just now", "1 min ago"]):
        c = Image.new("RGBA", (880, 124), (0, 0, 0, 0))
        d = ImageDraw.Draw(c)
        d.rounded_rectangle((0, 0, 879, 123), radius=30, fill=(250, 248, 244, 236))
        c.alpha_composite(thumb, (20, 20))
        d.text((128, 42), "New order · Fair Isle Sweater", font=sans(34, "Bold"), fill=(25, 25, 25), anchor="lm")
        d.text((128, 86), f"Example · {when}", font=sans(26, "Medium"), fill=(120, 116, 110), anchor="lm")
        cards.append(c)

    def ov(img: Image.Image, t: float):
        if t >= t1:
            return
        for k, c in enumerate(cards):
            p = ease_out((t - t0 - k * 0.45) / 0.3)
            if p > 0:
                x = round(W + 20 - (W + 20 - 100) * p)
                img.alpha_composite(c, (x, 320 + k * 140))
    return ov


def tryonswap_cancelled(take: dict[str, int] | None = None) -> Story:
    """《Model Cancelled》：黑五上新前一晚模特取消 → 崩溃 → 手机拍平铺图 → TryOnSwap 出雪景/居家/街拍上身图（卡配乐 drop）→ 零点上线，订单进来。"""
    # 选片：Cancel T2 推脸部特写；Flat 两条都有硬切（T1@124、T2@32/123），T1 的在所用区间外；Snow T1 硬切@105 在区间外、T2 有重影溶解；Win T2 双臂全程高举
    t = {"cancel": 1, "flat": 1, "snow": 1, "win": 2} | (take or {})
    sub = "tryonswap_story5"
    c = h3(sub, f"TC_S1_Cancel_T{t['cancel']}")
    segs = [
        Seg(2.0, c, t0=0.3, native=0.5),
        Seg(2.0, gen=ts_msg_insert()),
        Seg(2.6, c, t0=2.8, native=0.5),
        Seg(2.4, h3(sub, f"TC_S2_Flat_T{t['flat']}"), t0=0.3, native=0.6),
        Seg(3.8, gen=ts_product5(switch=1.0)),  # 段起点 9.0 s，结果弹出 = 10.0 s = 配乐 drop
        Seg(3.4, h3(sub, f"TC_S3_Snow_T{t['snow']}"), t0=0.3, native=0.3),
        Seg(4.0, h3(sub, f"TC_S4_Win_T{t['win']}"), t0=0.4, native=0.5),
        Seg(3.4, gen=tryonswap_endcard(), xfade=8),
    ]
    b = seg_starts(segs)
    cy = 1400
    ov = [
        caption("Black Friday drop:\n24 hours away.", 0.25, b[1], cy),
        caption("Model cancelled. No backup.", b[2] + 0.5, b[3], cy),
        caption("So: one phone photo.", b[3] + 0.2, b[4], cy),
        caption("No model booked. No studio.", b[5] + 0.1, b[6], cy),
        caption("12:00 AM. The drop is live.", b[6] + 0.2, b[7], cy),
        ts_orders(b[6] + 0.9, b[7]),  # 落版开始前收掉，别盖 logo
        url_pill("tryonswap.com", b[4], b[7], TS["bg"], TS["ivory"], fam="manrope"),
    ]
    return Story(segs, ov, music=[(OUT / "bgm" / "tryonswap_cancelled" / "bgm_v1.mp3", 0.0, 60.0)], music_gain=0.85,
                 out=OUT / "promo" / "tryonswap" / "TryOnSwap_Story_ModelCancelled_1080x1920.mp4")


# ---- Songifted《Porch Light》 ----
# /demos/for-dad.mp3（站上 /birthday-song-for-dad 示例歌，虚构名字 Daniel）。mlx_whisper small 逐词时间戳（前 52 s，不带上文条件）
SGP_A = (1.6, 30.1)  # 第一段：「Daniel, the porch light…」→「Happy birthday, Dad! We came to sing it loud」
SGP_B = (36.5, 45.6)  # 第二段：「Daniel, lift your coffee cup / Let the whole room join in too / The best part of this birthday」
SGP_LYRICS_A = [
    (2.00, 6.60, "Daniel, the porch light finds us pulling in again", "Daniel"),
    (6.68, 12.95, "You ask about the drive before you ask how long we've been", "Daniel"),
    (13.06, 18.40, "The coffee's on, your favorite cup is waiting by your chair", "Daniel"),
    (18.70, 22.60, "Your birthday starts the way it should", "Daniel"),
    (23.00, 25.10, "All of us right there", "Daniel"),
    (25.28, 27.20, "Happy birthday, Dad!", "Dad"),
    (27.26, 30.00, "We came to sing it loud", "Daniel"),
]
SGP_LYRICS_B = [
    (36.70, 39.30, "Daniel, lift your coffee cup", "Daniel"),
    (39.40, 41.70, "Let the whole room join in too", "Daniel"),
]


def songifted_porch(take: dict[str, int] | None = None) -> Story:
    """《Porch Light》：门廊灯下车开进车道 → 爸爸抱着女儿问路上顺不顺 → （用户写的故事卡）→ 手机放歌 →「Happy birthday, Dad!」他捂嘴笑出眼泪 → 全家举咖啡杯合唱。"""
    # 选片：Porch T2 中途切到「爸爸在开车」作废，T1 第 122 帧硬切回远景 → 只用 0–5.0 s；Play T1 第 139 帧硬切 → 只用 0–5.75 s；Toast T2 全景稳
    t = {"porch": 1, "door": 1, "play": 1, "tears": 1, "toast": 2} | (take or {})
    sub = "songifted_story5"
    a0 = SGP_A[0]
    cut = [0.0, 6.60 - a0, 12.95 - a0, 19.35 - a0, 25.10 - a0, SGP_A[1] - a0]  # 切点卡歌词换句（故事卡多留 0.8 s，给 Play T1 的硬切让位）
    segs = [
        Seg(cut[1] - cut[0], h3(sub, f"SP_S1_Porch_T{t['porch']}"), t0=0.0, native=0.2),
        Seg(cut[2] - cut[1], h3(sub, f"SP_S2_Door_T{t['door']}"), t0=0.2, native=0.0),
        Seg(cut[3] - cut[2], gen=sg_brief(("They told us", "about Dad."),
                                          "He always asks about the drive before he asks how long we're staying. The coffee's on before we're through the door.",
                                          card_bottom=1130)),  # 两行歌词条顶边约 1195，卡片收短避让
        Seg(cut[4] - cut[3], h3(sub, f"SP_S3_Play_T{t['play']}"), t0=0.0, native=0.0),
        Seg(cut[5] - cut[4], h3(sub, f"SP_S4_Tears_T{t['tears']}"), t0=0.3, native=0.0),
        Seg(5.8, h3(sub, f"SP_S5_Toast_T{t['toast']}"), t0=0.3, native=0.35),
        Seg(3.0, gen=songifted_endcard(), xfade=8),
    ]
    b = seg_starts(segs)
    b_off = cut[5] - 0.4 - SGP_B[0]  # 第二段歌内秒 → 成片秒（与第一段 0.4 s 交叉淡化）
    end = b[-1]
    ov = [caption("Dad's birthday.\nFour hours of driving.", 0.2, cut[1] - 0.2, 360, size=76, fam="fraunces", weight="SemiBold")]
    ov += [lyric(txt, s0 - a0, s1 - a0, name=nm) for s0, s1, txt, nm in SGP_LYRICS_A]  # 故事卡那段也叠：用户写的故事 → 歌里唱出来
    ov += [lyric(txt, s0 + b_off, min(s1 + b_off, end - 0.2), name=nm) for s0, s1, txt, nm in SGP_LYRICS_B]
    ov += [url_pill("songifted.com", cut[2], end, SG["white"], SG["coral"])]
    music_end = SGP_B[0] + (end - (cut[5] - 0.4)) + 0.5
    song = SAMPLES / "songifted" / "demos" / "for-dad.mp3"
    return Story(segs, ov, music=[(song, a0, SGP_A[1]), (song, SGP_B[0], music_end)],
                 out=OUT / "promo" / "songifted" / "Songifted_Story_PorchLight_1080x1920.mp4")


# ---------------- 第六批（2026-11-17）：PawMotif《Back in His Spot》/ TryOnSwap《One Dress, Every Party》/ Songifted《Mia》 ----------------
B6 = SAMPLES / "inputs_1117"  # 站上真实产出 + 喂给站的 AI 输入图（老年边牧照、丝绒裙平铺）
PB = SAMPLES / "pawmotif_biscuit"
PM_WC6 = B6 / "collie_watercolor_full.jpg"  # 测试号用 collie_src.jpg 在 /portraits/watercolor 真实生成（job 943726cc），3360x5024
PB_SEEDS = {"pb_c": (540, 420), "pb_d": (540, 420)}  # 竖版空白画框内的一点
TPD = SAMPLES / "tryonswap_party"
TS_PARTY = [("office", "Office party", "#c44b"), ("nye", "New Year's Eve", "#3fa9"), ("family", "Family dinner", "#b6f5")]  # 站长账号 2026-11-17 Custom 场景


def prep_batch6():
    kf = PB / "kf"
    boxes = {}
    for n, seed in PB_SEEDS.items():
        boxes[n] = paste_into_canvas(kf / f"{n}_768x1344.png", kf / f"{n}_framed_768x1344.png", PM_WC6, seed, focus_x=0.5)
        print(n, "canvas", boxes[n])
    zoom_on(kf / "pb_d_framed_768x1344.png", kf / "pb_d_zoom_768x1344.png", boxes["pb_d"], 1.7)
    for key, _, _ in TS_PARTY:
        cover_fit(Image.open(B6 / f"ts_party_{key}_2k.jpg").convert("RGB"), 768, 1344, 0.4).save(TPD / f"ts_party_{key}_768x1344.png")
    print("✅ 第六批关键帧已贴画 / 已缩放")


def pm_product6(photo_path: Path = B6 / "collie_src.jpg", art_path: Path = PM_WC6, style: str = "Watercolor", switch: float = 1.5):
    """PawMotif 产品动作：一张旧手机照片 → 「Create my free preview →」（站上按钮原文）→ 站上真实生成的画像翻出来。"""
    from promo_short import framed, pm_serif
    sans = lambda n, w="SemiBold": font("dmsans", n, w)  # noqa: E731
    photo = rounded(cover_fit(Image.open(photo_path).convert("RGB"), 520, 700, 0.4), 22)
    art = framed(Image.open(art_path).convert("RGB"), 640, 900)

    def gen(i: int, n: int) -> Image.Image:
        img = Image.new("RGBA", (W, H), PM["paper"] + (255,))
        d = ImageDraw.Draw(img)
        t = i / FPS
        if t < switch:
            d.text((W // 2, 330), "One old phone photo", font=pm_serif(84), fill=PM["ink"], anchor="mm")
            paste_scaled(img, photo, W // 2, 860, ease_out_back(i / 8))
            if t > switch * 0.45:
                a = int(255 * min(1.0, (t - switch * 0.45) / 0.2))
                pill(d, W // 2, 1300, "Create my free preview →", sans(46, "Bold"), PM["white"] + (a,), PM["olive"] + (a,), pad=(40, 20))
        else:
            d.text((W // 2, 330), f"PawMotif · {style}", font=pm_serif(84), fill=PM["olive"], anchor="mm")
            paste_scaled(img, art, W // 2, 880, ease_out_back((t - switch) / 0.35))
        return img.convert("RGB")
    return gen


def pawmotif_biscuit(take: dict[str, int] | None = None) -> Story:
    """《Back in His Spot》（宠物纪念，第一人称）：后门边的空狗窝 → 翻手机里唯一一张好照片 → 站上画成水彩 → 挂回狗窝上方 → 画里的 Biscuit 转头看你。"""
    # 选条（帧差 + 接触印样）：Phone T1 从 f60（2.5 s）起 H3 自己切进一个手机屏特写，屏上是她本人照片，
    # T2 中段把屏幕转向镜头、同样是她本人照片 → 只用 T1 的 0.05–2.35 s，本段从 4.2 s 缩到 2.3 s
    t = {"bed": 2, "phone": 1, "wall": 2, "turn": 1} | (take or {})
    sub = "pawmotif_story6"
    segs = [
        Seg(5.0, h3(sub, f"PB_S1_Bed_T{t['bed']}"), t0=0.3, native=0.35),
        Seg(2.3, h3(sub, f"PB_S2_Phone_T{t['phone']}"), t0=0.05, native=0.25),
        Seg(3.6, gen=pm_product6(switch=1.5)),
        # 原声：Wall T2 里她在嘟囔一句听不清的话，Turn T1 是 H3 自带配乐（whisper 判为 Music，-14 LUFS）→ 都静音
        Seg(5.0, h3(sub, f"PB_S3_Wall_T{t['wall']}"), t0=0.3, native=0.0),
        Seg(5.4, h3(sub, f"PB_S4_Turn_T{t['turn']}"), t0=0.25, native=0.0),
        Seg(3.8, gen=pawmotif_endcard(B6 / "collie_src.jpg", PM_WC6, "Watercolor", photo_bias=0.35), xfade=6),
    ]
    b = seg_starts(segs)
    cy = 1400
    ov = [
        caption("His bed is still\nby the back door.", 0.4, b[1], cy),
        caption("I only had one good\nphoto of Biscuit.", b[1] + 0.2, b[2], cy),
        caption("So I gave him\nhis spot back.", b[3] + 0.3, b[4], cy),
        caption("Painted from one\nold phone photo.", b[4] + 0.6, b[5] - 1.4, cy),  # 推近末段画框下沿会到字幕位置，提前收
        url_pill("pawmotif.com", b[2], b[5], PM["white"], PM["olive"]),
    ]
    return Story(segs, ov, music=[(OUT / "bgm" / "pawmotif_biscuit" / "bgm_v1.mp3", 0.0, 40.0)], music_gain=0.8,
                 out=OUT / "promo" / "pawmotif" / "PawMotif_Story_BackInHisSpot_1080x1920.mp4")


TP_DROP = 13.60  # bgm_v2 的 drop（0.05 s 窗响度从 -19 跳到 -10，之后每 0.5 s 一个重拍）


def tryonswap_party(take: dict[str, int] | None = None) -> Story:
    """《One Dress, Every Party》：12 月店主拿着一条丝绒裙 → 手机拍平铺图 → 3 个派对场景上身图卡 drop 弹出 → 年会 / 跨年夜 / 家宴逐个动起来。"""
    # 选条：Office T2 从 1.2 s 起正好装下一整个转圈（背面 → 回正脸大笑）；NYE T1 是平滑推近举杯（无硬切）
    t = {"owner": 1, "flat": 1, "office": 2, "nye": 1, "family": 1} | (take or {})
    sub = "tryonswap_story6"
    items = [(B6 / f"ts_party_{k}_2k.jpg", label) for k, label, _ in TS_PARTY]
    segs = [
        Seg(3.6, h3(sub, f"TP_S1_Owner_T{t['owner']}"), t0=0.3, native=0.4),
        Seg(2.4, h3(sub, f"TP_S2_Flat_T{t['flat']}"), t0=0.3, native=0.6),
        Seg(3.6, gen=ts_product5(switch=1.2, flat_path=B6 / "dress_src.jpg", items=items, after="One dress. Every party.")),
        # 原声压到底噪：Office / Family 有听得出的重复人声（"I'm gonna do that"），NYE 是 H3 自带音乐
        Seg(2.5, h3(sub, f"TP_S3_Office_T{t['office']}"), t0=1.2, native=0.1),
        Seg(2.5, h3(sub, f"TP_S4_NYE_T{t['nye']}"), t0=0.3, native=0.1),
        Seg(2.5, h3(sub, f"TP_S5_Family_T{t['family']}"), t0=0.3, native=0.1),
        Seg(3.4, gen=tryonswap_endcard(), xfade=8),
    ]
    b = seg_starts(segs)
    reveal = b[2] + 1.2  # 产品段里 3 张图弹出的时刻 = 配乐 drop
    cy = 1400
    ov = [
        caption("December: every customer\nhas a party to dress for.", 0.25, b[1], cy),
        caption("No model. No studio.\nOne phone photo.", b[1] + 0.1, b[2], cy),
        caption("Office party.", b[3] + 0.1, b[4], cy, size=80),
        caption("New Year's Eve.", b[4] + 0.1, b[5], cy, size=80),
        caption("Family dinner.", b[5] + 0.1, b[6], cy, size=80),
        url_pill("tryonswap.com", b[2], b[6], TS["bg"], TS["ivory"], fam="manrope"),
    ]
    a0 = TP_DROP - reveal
    return Story(segs, ov, music=[(OUT / "bgm" / "tryonswap_party" / "bgm_v2.mp3", a0, a0 + 40.0)], music_gain=0.85,
                 out=OUT / "promo" / "tryonswap" / "TryOnSwap_Story_EveryParty_1080x1920.mp4")


# ---- Songifted《Mia》 ----
# /demos/for-daughter.mp3（站上示例歌，虚构名字 Mia，生日歌）。mlx_whisper small 逐词时间戳（前 30 s 单独识别，不带上文条件）
SGM_A = (21.5, 59.8)
SGM_LYRICS = [
    (22.86, 28.40, "I let go a little slower than you ever knew"),
    (28.84, 33.96, "Twenty years of practicing, I'm still no good at letting you"),
    (35.54, 40.70, "Happy birthday, Mia, look at how you turned out"),
    (40.82, 45.60, "Braver at your age than I have ever been about"),
    (46.82, 51.60, "Anything that scared me, so I put it in a song"),
    (51.78, 57.30, "Happy birthday, Mia, you've been something all along"),
]


def songifted_mia(take: dict[str, int] | None = None, dorm: str = "s1") -> Story:
    """《Mia》：感恩节饭桌上爸爸放歌 → 3 岁过马路甩开他的手（背影闪回）→ 他写给我们的故事 →「Happy birthday, Mia」她捂嘴 → 18 岁报到 → 拥抱 → 南瓜派上吹生日蜡烛。

    dorm（宿舍镜头，2026-11-18 两套方案对比，见 README「有走位、有转身的镜头怎么做」）：
      t3 = 旧版 sm_f → sm_f_end（尾帧扭头，用户否决）
      s1 = 【正式，用户 11-18 选定】方案一：sm_g0（侧面道别）→ sm_f3_end_b（回头挥手）141 帧一次生成
      s2 = 方案二：A 段 sm_g0 → sm_f3（73 帧）接 B 段 sm_f3 → sm_f3_end_b（90 帧），共用中间帧无缝接力
    """
    # 选条：Pie T2 在唱到「Mia」时吹蜡烛。Cross/Dorm 的 T1/T2 首尾帧是同一张图，走路镜头只能原地踏步或走出去再倒回来
    # （用户审片发现）→ T3/T4 改用单独的尾帧 sm_e_end / sm_f_end 重渲，T3 全程向前走
    # 段长按歌词切点定，最长 5.8 s，入点要让 t0 + 段长 ≤ 片长 5.875 s，否则末尾冻帧
    assert dorm in ("t3", "s1", "s2"), dorm
    # Pie T1/T2 首尾同图 → 蜡烛吹灭后复燃（用户发现）；T3 用尾帧 sm_d_end，2.54 s 熄灭且不复燃，t0=0 让熄灭落在歌里 53.94 s，紧挨「Mia」54.14 s
    # T4 自己推成脸部特写，弃用
    t = {"table": 1, "cross": 3, "name": 1, "dorm": 3, "hug": 1, "pie": 3} | (take or {})
    t0 = {"table": 0.3, "cross": 0.3, "name": 0.25, "dorm": 0.25, "hug": 0.05, "pie": 0.0}
    sub = "songifted_story6"
    a0 = SGM_A[0]
    cut = [a0, 25.0, 28.64, 34.4, 40.0, 45.6, 51.4, 57.0]  # 歌内秒：切点卡在歌词换句处
    if dorm == "s2":
        cut[4] = 39.4  # 接力两段（道别 + 转身走 + 回头挥手）至少要 6.2 s，从捂嘴镜头借 0.6 s
    clips = ["table", "cross", None, "name", "dorm", "hug", "pie"]
    ids = {"table": "SM_S1_Table", "cross": "SM_S2_Cross", "name": "SM_S3_Name", "dorm": "SM_S4_Dorm", "hug": "SM_S5_Hug", "pie": "SM_S6_Pie"}
    # Pie T2/T3 原声都是 H3 自带音乐（-15 LUFS），会盖住站上的真实示例歌 → 静音
    native = {"table": 0.0, "cross": 0.15, "name": 0.0, "dorm": 0.1, "hug": 0.0, "pie": 0.0}
    segs = []
    for k, key in enumerate(clips):
        dur = cut[k + 1] - cut[k]
        if key is None:
            segs.append(Seg(dur, gen=sg_brief(("He told us", "about Mia."),
                                              "When she was three, she wouldn't hold my hand to cross the street. "
                                              "Twenty years later I'm still practicing letting go.", card_bottom=1130, label="Tell us about her")))
        elif key == "dorm" and dorm == "s1":
            # S1_T1 冷启动超时没出片，只有 T2：0–1.3 s 侧面道别，4.5–5.0 s 从左肩转身挥手
            assert 0.25 + dur <= 141 / 24
            segs.append(Seg(dur, h3(sub, "SM_S4_DormS1_T2"), t0=0.25, native=0.1))
        elif key == "dorm" and dorm == "s2":
            # A_T2 末帧 → B_T1 首帧 帧差 1.80（片内正常运动 1～1.7，无关镜头约 64）→ 硬接即无缝；只能剪 A 的头和 B 的尾
            a_t0, a_len, b_len = 0.3, 73 / 24, 90 / 24
            a_dur = a_len - a_t0
            b_dur = dur - a_dur
            assert 0 < b_dur <= b_len, f"B 段需要 {b_dur:.2f} s，片长只有 {b_len:.2f} s"
            segs.append(Seg(a_dur, h3(sub, "SM_S4_DormA_T2"), t0=a_t0, native=0.1))
            segs.append(Seg(b_dur, h3(sub, "SM_S4_DormB_T1"), t0=0.0, native=0.1))
        else:
            assert t0[key] + dur <= 141 / 24, f"{key}: 入点 {t0[key]} + 段长 {dur:.2f} 超出片长"
            segs.append(Seg(dur, h3(sub, f"{ids[key]}_T{t[key]}"), t0=t0[key], native=native[key]))
    segs.append(Seg(3.0, gen=songifted_endcard("A song with her name in it."), xfade=8))
    b = seg_starts(segs)
    end = b[-1]
    ov = [caption("Mia's 23rd birthday\nfell on Thanksgiving.", 0.2, cut[2] - a0 - 0.2, 360, size=76, fam="fraunces", weight="SemiBold")]
    ov += [lyric(txt, s0 - a0, min(s1 - a0, b[-2] + 0.1), name="Mia") for s0, s1, txt in SGM_LYRICS]
    ov += [url_pill("songifted.com", cut[2] - a0, end, SG["white"], SG["coral"])]
    song = SAMPLES / "songifted" / "demos" / "for-daughter.mp3"
    suffix = {"s1": "", "t3": "_DormT3", "s2": "_DormS2"}[dorm]
    return Story(segs, ov, music=[(song, a0, a0 + end + 0.2)],
                 out=OUT / "promo" / "songifted" / f"Songifted_Story_Mia{suffix}_1080x1920.mp4")


def story_registry() -> dict[str, Callable[[], Story]]:
    return {"pawmotif-intoframe": pawmotif_intoframe, "tryonswap-photoshoot": tryonswap_photoshoot, "songifted-danny": songifted_danny,
            "pawmotif-tree": pawmotif_tree, "tryonswap-cancelled": tryonswap_cancelled, "songifted-porch": songifted_porch,
            "pawmotif-biscuit": pawmotif_biscuit, "tryonswap-party": tryonswap_party, "songifted-mia": songifted_mia,
            "songifted-mia-s2": lambda: songifted_mia(dorm="s2"), "songifted-mia-t3": lambda: songifted_mia(dorm="t3")}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("--preview", action="store_true", help="540x960 快速预览")
    args = ap.parse_args()
    if args.name == "prep-pawmotif":
        prep_pawmotif()
        return
    if args.name == "prep-batch5":
        prep_batch5()
        return
    if args.name == "prep-batch6":
        prep_batch6()
        return
    story = story_registry()[args.name]()
    out = story.out if not args.preview else story.out.with_name(story.out.stem + "_preview.mp4")
    out.parent.mkdir(parents=True, exist_ok=True)
    scale = 0.5 if args.preview else 1.0
    frames, starts, total = render_frames(story, scale)
    ow, oh = round(W * scale) // 2 * 2, round(H * scale) // 2 * 2
    tmp_v = out.with_suffix(".video.mp4")
    enc = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{ow}x{oh}", "-r", str(FPS), "-i", "-",
         "-c:v", "libx264", "-preset", "veryfast" if args.preview else "slow", "-crf", "17", "-pix_fmt", "yuv420p", str(tmp_v)],
        stdin=subprocess.PIPE,
    )
    n = 0
    for fr in frames:
        enc.stdin.write(fr.tobytes())
        n += 1
    enc.stdin.close()
    enc.wait()
    mix_audio(story, starts, n / FPS, tmp_v, out)
    tmp_v.unlink()
    print(f"✅ {out} ({n} 帧, {n / FPS:.2f}s；时间线 {total:.2f}s)")


if __name__ == "__main__":
    main()
