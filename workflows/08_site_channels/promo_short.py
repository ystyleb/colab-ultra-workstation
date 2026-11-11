#!/usr/bin/env python3
"""08 号：把「结果样片」包装成能带货的 Shorts（本地 0 CCU）。

纯结果片的问题：观众只看到画面好看，不知道这是什么产品、自己能怎么用、去哪里用。
所以每条 Shorts 都按四段结构来剪：
  ① 钩子 + 输入（你给什么）→ ② 产品动作（在站上怎么操作）→ ③ 结果（H3 动起来的样片）→ ④ 落版（网址 + 免费额度）
网址从 ③ 开始常驻在右上角。Shorts 简介和评论里的链接点不开，所以网址必须直接出现在画面上。

    python3 workflows/08_site_channels/promo_short.py tryonswap
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
FONTS = HERE / "fonts"
W, H, FPS = 1080, 1920, 24
# Shorts 安全区：底部约 20% 被标题/频道名/音乐条盖住，右侧有点赞列，右上有搜索按钮。关键文字放在 STEP_Y 以上、居中
STEP_Y = 1450


def font(name: str, size: int, weight: str | None = None) -> ImageFont.FreeTypeFont:
    f = ImageFont.truetype(str(FONTS / f"{name}.ttf"), size)
    if weight:
        try:
            f.set_variation_by_name(weight)
        except Exception:
            pass
    return f


def cover_fit(im: Image.Image, w: int, h: int, y_bias: float = 0.5) -> Image.Image:
    s = max(w / im.width, h / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x, y = (im.width - w) // 2, int((im.height - h) * y_bias)
    return im.crop((x, y, x + w, y + h))


def contain(im: Image.Image, w: int, h: int, bg) -> Image.Image:
    s = min(w / im.width, h / im.height)
    im = im.convert("RGB").resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    c = Image.new("RGB", (w, h), bg)
    c.paste(im, ((w - im.width) // 2, (h - im.height) // 2))
    return c


def rounded(im: Image.Image, r: int) -> Image.Image:
    m = Image.new("L", im.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, im.width - 1, im.height - 1), radius=r, fill=255)
    im = im.convert("RGBA")
    im.putalpha(m)
    return im


def ease_out_back(t: float) -> float:
    t = max(0.0, min(1.0, t))
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def ease_out(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


def pill(d: ImageDraw.ImageDraw, cx: int, cy: int, text: str, f, fg, bg, pad=(30, 16)):
    l, t, r, b = d.textbbox((0, 0), text, font=f)
    w, h = r - l + pad[0] * 2, b - t + pad[1] * 2
    d.rounded_rectangle((cx - w // 2, cy - h // 2, cx + w // 2, cy + h // 2), radius=h // 2, fill=bg)
    d.text((cx, cy), text, font=f, fill=fg, anchor="mm")


def paste_scaled(canvas: Image.Image, card: Image.Image, cx: int, cy: int, s: float, alpha: float = 1.0):
    if s <= 0.01 or alpha <= 0.01:
        return
    im = card.resize((max(1, round(card.width * s)), max(1, round(card.height * s))), Image.LANCZOS)
    if alpha < 1:
        a = im.getchannel("A").point(lambda v: int(v * alpha))
        im.putalpha(a)
    canvas.alpha_composite(im, (cx - im.width // 2, cy - im.height // 2))


def clip_frames(clip: Path, start: int, end: int, src_w: int = 768, src_h: int = 1344):
    """把 768x1344 的 H3 样片按帧截取、放大到 1080 宽，逐帧产出 RGB Image（1080x1890，上下留 15px 底色）。"""
    ch = round(src_h * W / src_w)
    ch += ch % 2
    proc = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-i", str(clip), "-vf", f"trim=start_frame={start}:end_frame={end + 1},setpts=PTS-STARTPTS,"
         f"scale={W}:{ch}:flags=lanczos", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        stdout=subprocess.PIPE,
    )
    for _ in range(end - start + 1):
        buf = proc.stdout.read(W * ch * 3)
        if len(buf) < W * ch * 3:
            break
        yield Image.frombytes("RGB", (W, ch), buf)
    proc.stdout.close()
    proc.wait()


def wrap(d: ImageDraw.ImageDraw, text: str, f, maxw: int) -> list[str]:
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= maxw:
            cur = t
        else:
            lines.append(cur)
            cur = w
    return lines + ([cur] if cur else [])


# ---------------- TryOnSwap ----------------
TS = {"bg": (12, 11, 10), "ivory": (242, 237, 229), "gold": (200, 164, 107), "muted": (160, 152, 140)}


def tryonswap_frames(src: Path, clip: Path, clip_start: int, clip_end: int):
    """逐帧产出 RGB Image。src = samples/tryonswap 目录。"""
    model = Image.open(src / "tryonswap_model-a_768x1344.png").convert("RGB")
    garments = [Image.open(src / f"tryonswap_g-{g}.webp").convert("RGB") for g in ("coat", "knit", "trousers", "loafers")]
    icon = Image.open(src / "tryonswap_icon_512.png").convert("RGBA")
    serif = lambda n: font("cormorant", n, "SemiBold")  # noqa: E731
    sans = lambda n, w="SemiBold": font("manrope", n, w)  # noqa: E731

    def url_badge(img: Image.Image):
        d = ImageDraw.Draw(img)
        pill(d, W // 2, 190, "tryonswap.com", sans(44, "Bold"), TS["bg"], TS["ivory"] + (235,), pad=(36, 18))

    # ① 钩子 + 输入：0–2.0s，暗底大标题 + 本人照（照片从 y=PHOTO_Y 起，头部不被标题压住）慢推
    n1 = int(2.0 * FPS)
    PHOTO_Y = 470
    full = cover_fit(model, W, round(1344 * W / 768), 0.0)
    fade = Image.new("RGBA", (W, 180), (0, 0, 0, 0))
    for y in range(180):
        ImageDraw.Draw(fade).line((0, y, W, y), fill=TS["bg"] + (int(255 * (1 - y / 180)),))
    for i in range(n1):
        z = 1.0 + 0.05 * i / n1
        fw, fh = int(W / z), int((H - PHOTO_Y) / z)
        x0 = (W - fw) // 2
        ph = full.crop((x0, 0, x0 + fw, fh)).resize((W, H - PHOTO_Y), Image.LANCZOS).convert("RGBA")
        img = Image.new("RGBA", (W, H), TS["bg"] + (255,))
        img.alpha_composite(ph, (0, PHOTO_Y))
        img.alpha_composite(fade, (0, PHOTO_Y))
        d = ImageDraw.Draw(img)
        a = int(255 * ease_out(i / 8))
        d.text((W // 2, 230), "One photo.", font=serif(150), fill=TS["ivory"] + (a,), anchor="mm")
        d.text((W // 2, 380), "Any outfit.", font=serif(150), fill=TS["gold"] + (a,), anchor="mm")
        pill(d, W // 2, STEP_Y, "1  Upload a photo of the person", sans(42), TS["bg"], TS["ivory"] + (240,))
        yield img.convert("RGB")

    # ② 产品动作：2.0–4.6s，暗底「人 + 4 件单品」依次弹入，模拟站上 Model + Garment 两个上传框
    n2 = int(2.6 * FPS)
    mcard = rounded(cover_fit(model, 420, 735, 0.3), 28)
    gcards = [rounded(contain(g, 270, 330, (246, 243, 237)), 22) for g in garments]
    gpos = [(700, 640), (980 - 10, 640), (700, 1010), (980 - 10, 1010)]
    gpos = [(x - 30, y) for x, y in gpos]
    for i in range(n2):
        img = Image.new("RGBA", (W, H), TS["bg"] + (255,))
        d = ImageDraw.Draw(img)
        d.text((W // 2, 250), "Add the clothes", font=serif(104), fill=TS["ivory"], anchor="mm")
        d.text((W // 2, 360), "you want to try", font=serif(104), fill=TS["gold"], anchor="mm")
        paste_scaled(img, mcard, 270, 830, ease_out(i / 6))
        d.text((270, 1240), "Model", font=sans(36), fill=TS["muted"], anchor="mm")
        d.text((505, 830), "+", font=sans(96, "Bold"), fill=TS["gold"], anchor="mm")
        for k, (card, (cx, cy)) in enumerate(zip(gcards, gpos)):
            paste_scaled(img, card, cx, cy, ease_out_back((i - 6 - k * 5) / 9))
        d.text((830, 1240), "Garments", font=sans(36), fill=TS["muted"], anchor="mm")
        pill(d, W // 2, STEP_Y, "2  Pick the pieces you want", sans(42), TS["bg"], TS["ivory"])
        if i > n2 - 16:
            a = int(255 * (i - (n2 - 16)) / 16)
            pill(d, W // 2, 1335, "Swap outfit  →", sans(52, "Bold"), TS["bg"] + (a,), TS["gold"] + (a,), pad=(46, 22))
        yield img.convert("RGB")

    # ③ 结果：H3 动起来的上身效果，网址常驻顶部居中（右上角会被 Shorts 的搜索/菜单按钮挡住）
    for i, fr in enumerate(clip_frames(clip, clip_start, clip_end)):
        img = Image.new("RGBA", (W, H), TS["bg"] + (255,))
        img.paste(fr, (0, (H - fr.height) // 2))
        url_badge(img)
        d = ImageDraw.Draw(img)
        if i < int(3.5 * FPS):
            a = int(255 * min(1.0, i / 6))
            pill(d, W // 2, STEP_Y, "3  Get the new look in ~1 min", sans(42), TS["bg"] + (a,), TS["ivory"] + (min(a, 240),))
        d.text((W // 2, STEP_Y + 85), "Try-on image: TryOnSwap  ·  Motion: AI video", font=sans(26, "Medium"), fill=(242, 237, 229, 170), anchor="mm")
        yield img.convert("RGB")

    # ④ 落版：网址 + 免费额度
    n4 = int(2.8 * FPS)
    icn = icon.resize((220, 220), Image.LANCZOS)
    for i in range(n4):
        img = Image.new("RGBA", (W, H), TS["bg"] + (255,))
        d = ImageDraw.Draw(img)
        paste_scaled(img, icn, W // 2, 560, ease_out_back(i / 10))
        d.text((W // 2, 800), "TryOnSwap", font=serif(150), fill=TS["ivory"], anchor="mm")
        d.text((W // 2, 950), "tryonswap.com", font=sans(78, "Bold"), fill=TS["gold"], anchor="mm")
        d.text((W // 2, 1110), "Put any outfit on any photo.", font=sans(46, "Medium"), fill=TS["ivory"], anchor="mm")
        pill(d, W // 2, 1260, "12 free credits on sign-up", sans(46, "Bold"), TS["bg"], TS["ivory"], pad=(40, 20))
        d.text((W // 2, 1420), "Link on our channel page", font=sans(36, "Medium"), fill=TS["muted"], anchor="mm")
        yield img.convert("RGB")


# ---------------- Songifted ----------------
SG = {"coral": (210, 93, 64), "ink": (43, 29, 22), "cream": (253, 246, 238), "cream2": (243, 226, 209), "muted": (122, 97, 82), "white": (255, 255, 255)}
SG_LEAD = 4.6  # ①② 两段总时长；示例歌从 (副歌起点 - SG_LEAD) 开始放，结果段一开始正好唱到 "Happy birthday Sarah"
SG_CHORUS = 24.96
# 歌词时间（相对于示例歌 /demos/birthday.mp3，mlx_whisper small 词级时间戳）
SG_LYRICS = [(24.96, 28.30, "Happy birthday Sarah,", "this song belongs to you"), (28.30, 32.52, "Every single line of it", "is us saying thank you")]


def songifted_frames(src: Path, clip: Path, clip_start: int, clip_end: int):
    icon = Image.open(HERE / "out" / "songifted" / "avatar_800.png").convert("RGB").resize((200, 200), Image.LANCZOS)
    icon = rounded(icon, 100)
    serif = lambda n, w="SemiBold": font("fraunces", n, w)  # noqa: E731
    sans = lambda n, w="SemiBold": font("dmsans", n, w)  # noqa: E731
    bg = Image.new("RGBA", (W, H))
    for y in range(H):
        t = y / H
        ImageDraw.Draw(bg).line((0, y, W, y), fill=tuple(int(a + (b - a) * t) for a, b in zip(SG["cream"], SG["cream2"])) + (255,))

    def headline(d, a1: str, a2: str, alpha: int = 255):
        d.text((W // 2, 250), a1, font=serif(104), fill=SG["ink"] + (alpha,), anchor="mm")
        d.text((W // 2, 375), a2, font=serif(104), fill=SG["coral"] + (alpha,), anchor="mm")

    def card(d, box, label: str):
        x0, y0, x1, y1 = box
        d.rounded_rectangle((x0 + 6, y0 + 10, x1 + 6, y1 + 10), radius=34, fill=(120, 80, 60, 40))
        d.rounded_rectangle(box, radius=34, fill=SG["white"] + (255,))
        d.text((x0 + 56, y0 + 62), label, font=sans(34, "Bold"), fill=SG["muted"], anchor="lm")

    # ① 钩子 + 输入：一句话写下 Sarah（站上「How it works」示例原文），打字机效果
    brief = "A birthday song for our friend Sarah, to say thank you for the laughs and late-night calls."
    n1 = int(2.6 * FPS)
    for i in range(n1):
        img = bg.copy()
        d = ImageDraw.Draw(img)
        headline(d, "A birthday song", "with her name in it.", int(255 * ease_out(i / 8)))
        card(d, (90, 560, W - 90, 1200), "Tell us about them")
        k = int(len(brief) * min(1.0, max(0.0, (i - 6) / (n1 - 18))))
        f = serif(62, "Regular")
        y = 680
        for line in wrap(d, brief[:k], f, W - 300):
            d.text((150, y), line, font=f, fill=SG["ink"], anchor="la")
            y += 86
        if (i // 6) % 2 == 0 and k < len(brief):
            d.rectangle((150 + d.textlength(line if k else "", font=f) + 6, y - 80, 154 + d.textlength(line if k else "", font=f) + 6, y - 14), fill=SG["coral"])
        pill(d, W // 2, STEP_Y, "1  Share a few words about them", sans(42), SG["white"], SG["ink"])
        yield img.convert("RGB")

    # ② 产品动作：AI 把这句话写成带名字的歌词，你确认后再唱
    n2 = int(SG_LEAD * FPS) - n1
    lyr = ["Happy birthday Sarah,", "this song belongs to you.", "Every single line of it", "is us saying thank you."]
    for i in range(n2):
        img = bg.copy()
        d = ImageDraw.Draw(img)
        headline(d, "We write the lyrics.", "You approve them.")
        card(d, (90, 560, W - 90, 1270), "Your lyrics")
        f = serif(60, "Regular")
        for j, line in enumerate(lyr):
            a = int(255 * ease_out((i - j * 4) / 6))
            y = 690 + j * 96
            if line.startswith("Happy birthday Sarah"):
                pre = "Happy birthday "
                d.text((150, y), pre, font=f, fill=SG["ink"] + (a,), anchor="la")
                xs = 150 + d.textlength(pre, font=f)
                d.text((xs, y), "Sarah,", font=serif(60, "Bold"), fill=SG["coral"] + (a,), anchor="la")
            else:
                d.text((150, y), line, font=f, fill=SG["ink"] + (a,), anchor="la")
        if i > n2 - 20:
            s_ = ease_out_back((i - (n2 - 20)) / 10)
            btn = Image.new("RGBA", (460, 110), (0, 0, 0, 0))
            bd = ImageDraw.Draw(btn)
            bd.rounded_rectangle((0, 0, 459, 109), radius=55, fill=SG["coral"])
            bd.text((230, 55), "Approve lyrics", font=sans(44, "Bold"), fill=SG["white"], anchor="mm")
            paste_scaled(img, btn, W // 2, 1175, s_)
        pill(d, W // 2, STEP_Y, "2  Approve the lyrics", sans(42), SG["white"], SG["ink"])
        yield img.convert("RGB")

    # ③ 结果：反应片 + 歌词字幕（Sarah 高亮），网址常驻顶部
    for i, fr in enumerate(clip_frames(clip, clip_start, clip_end)):
        img = Image.new("RGBA", (W, H), SG["ink"] + (255,))
        img.paste(fr, (0, (H - fr.height) // 2))
        d = ImageDraw.Draw(img)
        pill(d, W // 2, 190, "songifted.com", sans(44, "Bold"), SG["white"], SG["coral"], pad=(36, 18))
        t_song = SG_CHORUS + i / FPS
        for a0, a1, l1, l2 in SG_LYRICS:
            if a0 <= t_song < a1:
                fa = int(255 * min(1.0, (t_song - a0) / 0.15, (a1 - t_song) / 0.15))
                band = Image.new("RGBA", (W, 300), (0, 0, 0, 0))
                bd = ImageDraw.Draw(band)
                bd.rounded_rectangle((70, 0, W - 70, 270), radius=36, fill=(43, 29, 22, int(fa * 0.62)))
                for row, line in enumerate((l1, l2)):
                    yy = 80 + row * 110
                    if "Sarah" in line:
                        pre, post = line.split("Sarah", 1)
                        tw = sum(bd.textlength(x, font=serif(68, w)) for x, w in ((pre, "SemiBold"), ("Sarah", "Bold"), (post, "SemiBold")))
                        x = (W - tw) / 2
                        for part, w, c in ((pre, "SemiBold", SG["white"]), ("Sarah", "Bold", (255, 168, 140)), (post, "SemiBold", SG["white"])):
                            bd.text((x, yy), part, font=serif(68, w), fill=c + (fa,), anchor="lm")
                            x += bd.textlength(part, font=serif(68, w))
                    else:
                        bd.text((W // 2, yy), line, font=serif(68), fill=SG["white"] + (fa,), anchor="mm")
                img.alpha_composite(band, (0, 1130))
        if i < int(2.5 * FPS):
            a = int(255 * min(1.0, i / 6))
            pill(d, W // 2, STEP_Y, "3  Play it. Watch their face.", sans(42), SG["white"] + (a,), SG["coral"] + (a,))
        d.text((W // 2, STEP_Y + 85), "Song: made with Songifted  ·  Scene: AI dramatization", font=sans(26, "Medium"), fill=(255, 255, 255, 190), anchor="mm")
        yield img.convert("RGB")

    # ④ 落版
    n4 = int(2.8 * FPS)
    for i in range(n4):
        img = bg.copy()
        d = ImageDraw.Draw(img)
        paste_scaled(img, icon, W // 2, 560, ease_out_back(i / 10))
        d.text((W // 2, 790), "Songifted", font=serif(150), fill=SG["ink"], anchor="mm")
        d.text((W // 2, 940), "songifted.com", font=sans(78, "Bold"), fill=SG["coral"], anchor="mm")
        d.text((W // 2, 1090), "A song with their name in it.", font=sans(46, "Medium"), fill=SG["ink"], anchor="mm")
        pill(d, W // 2, 1240, "Free 45-second preview", sans(46, "Bold"), SG["white"], SG["coral"], pad=(40, 20))
        d.text((W // 2, 1340), "for eligible first-time creators", font=sans(32, "Medium"), fill=SG["muted"], anchor="mm")
        d.text((W // 2, 1420), "Link on our channel page", font=sans(36, "Medium"), fill=SG["muted"], anchor="mm")
        yield img.convert("RGB")


# ---------------- PawMotif ----------------
PM = {"ink": (48, 60, 51), "paper": (248, 246, 240), "cream": (238, 235, 224), "olive": (82, 99, 75), "muted": (121, 126, 112), "white": (255, 255, 255)}
GEORGIA = Path("/System/Library/Fonts/Supplemental/Georgia.ttf")
GEORGIA_I = Path("/System/Library/Fonts/Supplemental/Georgia Italic.ttf")


def pm_serif(n: int, italic: bool = False):
    path = GEORGIA_I if italic else GEORGIA
    return ImageFont.truetype(str(path), n) if path.exists() else font("fraunces", n, "Regular")  # 非 Mac 退回 OFL 衬线体


def pawmotif_frames(src: Path, clip: Path, clip_start: int, clip_end: int):
    """原照 → 选风格 → 划屏变成水彩 → 落版。不用 H3（0 CCU）；clip 只借柯基样片的音乐盒原生音轨。"""
    photo = Image.open(src / "pawmotif_doberman_src.jpg").convert("RGB")
    art = Image.open(src / "pawmotif_doberman_watercolor_full.jpg").convert("RGB")
    cache = HERE / ".cache" / "pawmotif"
    styles = [("watercolor-portrait", "Watercolor"), ("old-world-portrait", "Old World Oil"), ("golden-portrait", "Botanical"), ("pencil-portrait", "Colored Pencil")]
    icon = rounded(Image.open(HERE / "out" / "pawmotif" / "avatar_800.png").convert("RGB").resize((210, 210), Image.LANCZOS), 105)
    sans = lambda n, w="SemiBold": font("dmsans", n, w)  # noqa: E731
    # 照片和画像都放在纸色底上、整体下移：顶部留给标题/网址，不压耳朵
    def on_paper(im: Image.Image, y: int) -> Image.Image:
        c = Image.new("RGB", (W, H), PM["paper"])
        ph = cover_fit(im, W, round(im.height * W / im.width))
        c.paste(ph, (0, y))
        fade = Image.new("RGBA", (W, 90), (0, 0, 0, 0))
        for yy in range(90):
            ImageDraw.Draw(fade).line((0, yy, W, yy), fill=PM["paper"] + (int(255 * (1 - yy / 90)),))
        c = c.convert("RGBA")
        c.alpha_composite(fade, (0, y))
        return c.convert("RGB")

    photo_full = on_paper(photo, 400)  # 1536x2048 → 1080x1440，占 400–1840
    art_full = on_paper(art, 290)  # 1664x2512 → 1080x1630，占 290–1920

    def url_badge(d):
        pill(d, W // 2, 190, "pawmotif.com", sans(44, "Bold"), PM["white"], PM["ink"] + (235,), pad=(36, 18))

    # ① 钩子 + 输入：手机随手拍的原照，满屏慢推
    n1 = int(2.2 * FPS)
    for i in range(n1):
        z = 1.0 + 0.05 * i / n1
        fw, fh = int(W / z), int(H / z)
        x0, y0 = (W - fw) // 2, (H - fh) // 2
        img = photo_full.crop((x0, y0, x0 + fw, y0 + fh)).resize((W, H), Image.LANCZOS).convert("RGBA")
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(ov)
        a = int(255 * ease_out(i / 8))
        od.text((W // 2, 200), "Just a phone photo", font=pm_serif(96), fill=PM["ink"] + (a,), anchor="mm")
        od.text((W // 2, 315), "of my dog…", font=pm_serif(96, True), fill=PM["olive"] + (a,), anchor="mm")
        pill(od, W // 2, STEP_Y, "1  Upload one photo of your pet", sans(42), PM["white"], PM["ink"] + (240,))
        img.alpha_composite(ov)
        yield img.convert("RGB")

    # ② 产品动作：选风格（站上真实的风格样图），Watercolor 被选中，再弹出站上原文按钮
    n2 = int(2.4 * FPS)
    cards = [(rounded(cover_fit(Image.open(cache / f"{k}.webp").convert("RGB"), 340, 360, 0.3), 24), name) for k, name in styles]
    pos = [(330, 600), (750, 600), (330, 1080), (750, 1080)]
    for i in range(n2):
        img = Image.new("RGBA", (W, H), PM["paper"] + (255,))
        d = ImageDraw.Draw(img)
        d.text((W // 2, 230), "Pick an art style", font=pm_serif(96), fill=PM["ink"], anchor="mm")
        d.text((W // 2, 345), "and preview it free", font=pm_serif(96, True), fill=PM["olive"], anchor="mm")
        sel = i > 22
        for k, ((card, name), (cx, cy)) in enumerate(zip(cards, pos)):
            sc = ease_out_back((i - k * 3) / 9)
            if k == 0 and sel:
                sc *= 1.0 + 0.04 * ease_out((i - 22) / 6)
                r = int(card.width * sc / 2) + 12
                rh = int(card.height * sc / 2) + 12
                d.rounded_rectangle((cx - r, cy - rh, cx + r, cy + rh), radius=32, outline=PM["olive"], width=10)
            paste_scaled(img, card, cx, cy, sc)
            if sc > 0.5:
                d.text((cx, cy + 218), name, font=sans(34, "Medium"), fill=PM["ink"] if (k == 0 and sel) else PM["muted"], anchor="mm")
        if i > n2 - 18:
            btn = Image.new("RGBA", (640, 110), (0, 0, 0, 0))
            bd = ImageDraw.Draw(btn)
            bd.rounded_rectangle((0, 0, 639, 109), radius=8, fill=PM["olive"])
            bd.text((320, 55), "Create my free preview  →", font=sans(42, "Bold"), fill=PM["white"], anchor="mm")
            paste_scaled(img, btn, W // 2, 1395, ease_out_back((i - (n2 - 18)) / 8))
        pill(d, W // 2, 1510, "2  Choose from 6 art styles", sans(40), PM["white"], PM["ink"])
        yield img.convert("RGB")

    # ③ 结果：原照 → 水彩 划屏，然后在画上慢推
    n3h, n3w, n3p = int(0.5 * FPS), int(1.5 * FPS), int(4.3 * FPS)
    for i in range(n3h + n3w + n3p):
        if i < n3h:
            img = photo_full.copy().convert("RGBA")
        elif i < n3h + n3w:
            t = ease_out((i - n3h) / n3w) * 1.12
            edge = int(t * (W + 240)) - 120
            mask = Image.new("L", (W, H), 0)
            md = ImageDraw.Draw(mask)
            md.rectangle((0, 0, max(0, edge - 120), H), fill=255)
            for x in range(max(0, edge - 120), min(W, edge + 120)):
                md.line((x, 0, x, H), fill=int(255 * (1 - (x - (edge - 120)) / 240)))
            img = Image.composite(art_full, photo_full, mask).convert("RGBA")
            if 0 < edge < W:
                glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                ImageDraw.Draw(glow).rectangle((edge - 3, 0, edge + 3, H), fill=(255, 255, 255, 170))
                img.alpha_composite(glow)
        else:
            k = (i - n3h - n3w) / n3p
            z = 1.0 + 0.07 * k
            fw, fh = int(W / z), int(H / z)
            x0, y0 = (W - fw) // 2, int((H - fh) * 0.3)
            img = art_full.crop((x0, y0, x0 + fw, y0 + fh)).resize((W, H), Image.LANCZOS).convert("RGBA")
        d = ImageDraw.Draw(img)
        url_badge(d)
        if i >= n3h + n3w // 2:
            a = int(255 * min(1.0, (i - n3h - n3w // 2) / 6))
            pill(d, W // 2, STEP_Y, "3  Your portrait in about a minute", sans(42), PM["white"] + (a,), PM["ink"] + (min(a, 240),))
        pill(d, W // 2, STEP_Y + 85, "Real photo → PawMotif watercolor portrait", sans(26, "Medium"), PM["ink"], PM["paper"] + (210,), pad=(20, 8))
        yield img.convert("RGB")

    # ④ 落版
    n4 = int(2.8 * FPS)
    for i in range(n4):
        img = Image.new("RGBA", (W, H), PM["paper"] + (255,))
        d = ImageDraw.Draw(img)
        paste_scaled(img, icon, W // 2, 560, ease_out_back(i / 10))
        d.text((W // 2, 800), "PawMotif", font=pm_serif(150), fill=PM["ink"], anchor="mm")
        d.text((W // 2, 950), "pawmotif.com", font=sans(78, "Bold"), fill=PM["olive"], anchor="mm")
        d.text((W // 2, 1095), "Custom pet portraits from your photo", font=sans(44, "Medium"), fill=PM["ink"], anchor="mm")
        pill(d, W // 2, 1240, "Free preview  ·  $29 only if you love it", sans(42, "Bold"), PM["white"], PM["olive"], pad=(40, 20))
        d.text((W // 2, 1380), "Link on our channel page", font=sans(36, "Medium"), fill=PM["muted"], anchor="mm")
        yield img.convert("RGB")


RECIPES = {
    "tryonswap": dict(
        src="samples/tryonswap", clip="out/samples/tryonswap/TryOnSwap_SpinSwap_Coat_Master.mp4", start=1, end=188,
        out="out/promo/tryonswap/TryOnSwap_Promo_Coat_1080x1920.mp4", frames=tryonswap_frames,
    ),
    "pawmotif": dict(
        src="samples/pawmotif", clip="out/samples/pawmotif/PawMotif_LivingCorgi_T1_Master.mp4", start=0, end=0,
        out="out/promo/pawmotif/PawMotif_Promo_Doberman_1080x1920.mp4", frames=pawmotif_frames,
    ),
    "songifted": dict(
        src="samples/songifted", clip="out/samples/songifted/Songifted_BirthdayReaction_T1_Master.mp4", start=0, end=181,
        out="out/promo/songifted/Songifted_Promo_Birthday_1080x1920.mp4", frames=songifted_frames,
        audio="samples/songifted/songifted_demo_birthday.mp3", audio_start=SG_CHORUS - SG_LEAD,
    ),
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("site", choices=sorted(RECIPES))
    args = ap.parse_args()
    r = RECIPES[args.site]
    clip = HERE / r["clip"]
    out = HERE / r["out"]
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp_v = out.with_suffix(".video.mp4")
    enc = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
         "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p", str(tmp_v)],
        stdin=subprocess.PIPE,
    )
    n = 0
    for fr in r["frames"](HERE / r["src"], clip, r["start"], r["end"]):
        enc.stdin.write(fr.tobytes())
        n += 1
    enc.stdin.close()
    enc.wait()
    dur = n / FPS
    # 音轨：有 audio 就从 audio_start 截（Songifted 示例歌）；否则 H3 原生音轨循环铺满全片。
    # 首尾淡入淡出，开头不留静音（Shorts 开头静音会掉留存）
    if r.get("audio"):
        a_in, a0 = ["-i", str(HERE / r["audio"])], float(r.get("audio_start", 0.0))
    else:
        a_in, a0 = ["-stream_loop", "-1", "-i", str(clip)], 0.0
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(tmp_v), *a_in,
         "-filter_complex", f"[1:a]atrim={a0:.3f}:{a0 + dur:.3f},asetpts=PTS-STARTPTS,afade=t=in:d=0.1,afade=t=out:st={dur - 0.8:.3f}:d=0.8[a]",
         "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)],
        check=True,
    )
    tmp_v.unlink()
    print(f"✅ {out} ({n} 帧, {dur:.2f}s)")


if __name__ == "__main__":
    main()
