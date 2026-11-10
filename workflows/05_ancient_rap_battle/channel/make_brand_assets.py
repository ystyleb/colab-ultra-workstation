# -*- coding: utf-8 -*-
"""MakeItRap YouTube channel art: avatar, banner and an English thumbnail for an episode.

usage: python3 make_brand_assets.py [--ep ../episodes/edison-vs-tesla-full] [--out out/]

Brand = makeitrap.com: background #0a0a0a, primary gold #f5c518, accent orange #f26a1b, Bebas Neue + Inter
(fonts/ holds the OFL font files so this is reproducible offline).
YouTube sizes: avatar 800x800 (shown as a circle), banner 2560x1440 where only the centre 2560x423 shows on desktop
and only the centre 1546x423 is safe on every device, thumbnail 1280x720.
"""
import argparse
import os

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
BG, GOLD, ORANGE, WHITE = (10, 10, 10), (245, 197, 24), (242, 106, 27), (245, 245, 240)
BEBAS = os.path.join(HERE, "fonts", "BebasNeue-Regular.ttf")
INTER = os.path.join(HERE, "fonts", "Inter.ttf")


def bebas(size):
    return ImageFont.truetype(BEBAS, size)


def inter(size, weight="Bold"):
    f = ImageFont.truetype(INTER, size)
    f.set_variation_by_name(weight)
    return f


def text_shadow(img, xy, text, font, fill, anchor="mm", shadow=ORANGE, off=(0, 0), stroke=0, glow=0):
    """Draw text with an optional offset 'sticker' shadow and a soft dark glow behind it."""
    if glow:
        g = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(g).text(xy, text, font=font, fill=(0, 0, 0, 220), anchor=anchor, stroke_width=glow, stroke_fill=(0, 0, 0, 220))
        img.alpha_composite(g.filter(ImageFilter.GaussianBlur(glow)))
    d = ImageDraw.Draw(img)
    if off != (0, 0):
        d.text((xy[0] + off[0], xy[1] + off[1]), text, font=font, fill=shadow, anchor=anchor)
    d.text(xy, text, font=font, fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill=BG)


def cover_fit(im, w, h):
    s = max(w / im.width, h / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x, y = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))


def fade_edges(im, left=0, right=0, top=0, bottom=0):
    """Alpha-fade the edges so a cut-out blends into the background (no visible rectangle)."""
    a = Image.new("L", im.size, 255)
    px = a.load()
    for x in range(im.width):
        vx = 255
        if left and x < left:
            vx = int(255 * x / left)
        if right and x > im.width - right:
            vx = min(vx, int(255 * (im.width - x) / right))
        for y in range(im.height):
            vy = 255
            if top and y < top:
                vy = int(255 * y / top)
            if bottom and y > im.height - bottom:
                vy = min(vy, int(255 * (im.height - y) / bottom))
            px[x, y] = vx * vy // 255
    im = im.convert("RGBA")
    im.putalpha(a)
    return im


def avatar(out):
    S = 800
    img = Image.new("RGBA", (S, S), BG + (255,))
    d = ImageDraw.Draw(img)
    d.ellipse((40, 40, S - 40, S - 40), outline=GOLD, width=14)       # reads as a ring inside YouTube's circle crop
    text_shadow(img, (S / 2, S / 2 - 10), "M", bebas(520), GOLD, off=(14, 14))
    d.text((S / 2, S - 158), "MAKE IT RAP", font=bebas(78), fill=WHITE, anchor="mm")
    img.convert("RGB").save(os.path.join(out, "avatar_800.png"))


def banner(out, ep):
    W, H = 2560, 1440
    venue = Image.open(os.path.join(ep, "refs", "venue.png")).convert("RGB")
    img = cover_fit(venue, W, H)
    img = ImageEnhance.Brightness(img).enhance(0.45).filter(ImageFilter.GaussianBlur(3)).convert("RGBA")
    # Edison / Tesla from the film's two-shot frame, placed in the desktop band but outside the all-device safe area
    frame = Image.open(os.path.join(ep, "cover", "frame.png")).convert("RGB")
    band_top, band_h = (H - 423) // 2, 423
    fw, fh = frame.size
    ed = frame.crop((int(fw * 0.20), int(fh * 0.08), int(fw * 0.55), int(fh * 0.62)))
    te = frame.crop((int(fw * 0.66), int(fh * 0.06), int(fw * 0.98), int(fh * 0.62)))
    for part, x, side in ((ed, 40, "l"), (te, None, "r")):
        s = (band_h + 120) / part.height
        part = part.resize((round(part.width * s), round(part.height * s)), Image.LANCZOS)
        part = fade_edges(part, left=120 if side == "l" else 200, right=200 if side == "l" else 120, top=90, bottom=110)
        px = x if side == "l" else W - part.width - 40
        img.alpha_composite(part, (px, band_top - 60))
    # dark centre plate so the type reads over the arena
    plate = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(plate).rectangle(((W - 1546) // 2, band_top, (W + 1546) // 2, band_top + band_h), fill=(0, 0, 0, 150))
    img.alpha_composite(plate.filter(ImageFilter.GaussianBlur(40)))
    cx = W // 2
    text_shadow(img, (cx, band_top + 150), "MAKE IT RAP", bebas(230), GOLD, off=(8, 8), glow=12)
    text_shadow(img, (cx, band_top + 285), "AI RAP BATTLES  ·  HISTORY'S BIGGEST RIVALS", bebas(78), WHITE, glow=8)
    text_shadow(img, (cx, band_top + 365), "Make your own rap video at makeitrap.com", inter(36, "SemiBold"), ORANGE, glow=6)
    img.convert("RGB").save(os.path.join(out, "banner_2560x1440.png"), optimize=True)
    # preview with the device crops drawn on, for checking only
    chk = img.convert("RGB").copy()
    dd = ImageDraw.Draw(chk)
    dd.rectangle((0, band_top, W - 1, band_top + band_h), outline=(0, 255, 255), width=6)
    dd.rectangle(((W - 1546) // 2, band_top, (W + 1546) // 2, band_top + band_h), outline=(255, 0, 255), width=6)
    chk.resize((1280, 720)).save(os.path.join(out, "_banner_check.png"))


def thumbnail(out, ep, name, left, right, tagline):
    W, H = 1280, 720
    frame = Image.open(os.path.join(ep, "cover", "frame.png")).convert("RGB")
    img = ImageEnhance.Contrast(cover_fit(frame, W, H)).enhance(1.12).convert("RGBA")
    grad = Image.new("L", (1, H))
    for y in range(H):
        grad.putpixel((0, y), int(235 * max(0, (y - H * 0.42) / (H * 0.58)) ** 1.3))
    shade = Image.new("RGBA", (W, H), BG + (0,))
    shade.putalpha(grad.resize((W, H)))
    img.alpha_composite(shade)
    y = int(H * 0.74)
    d = ImageDraw.Draw(img)
    gap = 26
    # long names (NAPOLEON / WELLINGTON) shrink to fit 92% of the width; short ones keep the full size
    full = sum(d.textlength(t, font=f) for t, f in ((left, bebas(176)), ("VS", bebas(150)), (right, bebas(176)))) + 2 * gap
    s = min(1.0, W * 0.92 / full)
    fl, fv = bebas(int(176 * s)), bebas(int(150 * s))
    wl, wv, wr = (d.textlength(t, font=f) for t, f in ((left, fl), ("VS", fv), (right, fl)))
    x = (W - (wl + wv + wr + 2 * gap)) / 2
    text_shadow(img, (x, y), left, fl, GOLD, anchor="ls", off=(6, 6), glow=10)
    text_shadow(img, (x + wl + gap, y - 8), "VS", fv, ORANGE, anchor="ls", off=(5, 5), shadow=BG, glow=10)
    text_shadow(img, (x + wl + wv + 2 * gap, y), right, fl, GOLD, anchor="ls", off=(6, 6), glow=10)
    text_shadow(img, (W / 2, int(H * 0.88)), tagline, bebas(66), WHITE, glow=8)
    tag = "AI RAP BATTLE"
    tw = d.textlength(tag, font=bebas(44))
    d.rounded_rectangle((28, 26, 28 + tw + 36, 26 + 60), radius=10, fill=GOLD)
    d.text((28 + 18, 26 + 30), tag, font=bebas(44), fill=BG, anchor="lm")
    img.convert("RGB").save(os.path.join(out, name), quality=92)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--ep", default=os.path.join(HERE, "..", "episodes", "edison-vs-tesla-full"))
    ap.add_argument("--out", default=os.path.join(HERE, "out"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    avatar(a.out)
    banner(a.out, a.ep)
    thumbnail(a.out, a.ep, "thumb_ep01_edison_vs_tesla.jpg", "EDISON", "TESLA", "WHO REALLY LIT UP THE WORLD?")
    print("wrote", sorted(os.listdir(a.out)))
