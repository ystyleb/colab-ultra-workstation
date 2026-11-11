# -*- coding: utf-8 -*-
"""YouTube channel art for the three tool-site channels: Songifted, PawMotif, TryOnSwap.

usage: python3 make_channel_assets.py [--site songifted|pawmotif|tryonswap|all] [--out out/]

Every colour, font and picture comes from the live site (palette and fonts read from each site's CSS, 2026-11-10),
so the channel looks like the site it sends traffic to:
  songifted  coral #D25D40 on warm cream, Fraunces + DM Sans, gift-ribbon "S" mark (from /favicon.svg)
  pawmotif   ink #303c33 on paper #f8f6f0, olive #52634b, Georgia + DM Sans, framed dog-and-cat icon
  tryonswap  ivory #f2ede5 on near-black #0c0b0a, gold ring #c8a46b, Cormorant Garamond + Manrope, serif "TS" icon
Fonts (OFL, Google Fonts repo) and site pictures are downloaded once into fonts/ and .cache/ (both gitignored).

YouTube sizes: avatar 800x800 (shown as a circle), banner 2560x1440 where only the centre 2560x423 shows on desktop
and only the centre 1546x423 is safe on every device. _banner_check.png draws both crops for eyeballing.
"""
import argparse
import os
import re
import urllib.request

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, "fonts")
CACHE = os.path.join(HERE, ".cache")
GF = "https://raw.githubusercontent.com/google/fonts/main/ofl/"
FONTS = {
    "fraunces": GF + "fraunces/Fraunces%5BSOFT,WONK,opsz,wght%5D.ttf",
    "cormorant": GF + "cormorantgaramond/CormorantGaramond%5Bwght%5D.ttf",
    "dmsans": GF + "dmsans/DMSans%5Bopsz,wght%5D.ttf",
    "manrope": GF + "manrope/Manrope%5Bwght%5D.ttf",
}
GEORGIA = "/System/Library/Fonts/Supplemental/Georgia.ttf"            # pawmotif.com's --serif; macOS ships it
GEORGIA_I = "/System/Library/Fonts/Supplemental/Georgia Italic.ttf"

W, H = 2560, 1440
BAND_H = 423
BAND_TOP = (H - BAND_H) // 2
SAFE_W = 1546


def hexrgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


# ---------- downloads ----------

def fetch(url, path):
    if os.path.exists(path) and os.path.getsize(path) > 0:
        return path
    os.makedirs(os.path.dirname(path), exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (channel-art script)"})
    with urllib.request.urlopen(req, timeout=60) as r, open(path + ".part", "wb") as f:
        f.write(r.read())
    os.replace(path + ".part", path)
    return path


def font(name, size, weight=None):
    if name in ("georgia", "georgia_i"):
        path = GEORGIA if name == "georgia" else GEORGIA_I
        if not os.path.exists(path):                                    # not on a Mac: closest OFL serif
            return font("fraunces", size, weight or "Regular")
        return ImageFont.truetype(path, size)
    path = fetch(FONTS[name], os.path.join(FONT_DIR, name + ".ttf"))
    f = ImageFont.truetype(path, size)
    if weight:
        f.set_variation_by_name(weight)
    return f


def site_img(site, path):
    return Image.open(fetch(f"https://{site}.com{path}", os.path.join(CACHE, site, os.path.basename(path))))


# ---------- drawing helpers ----------

def cover_fit(im, w, h, y_bias=0.5):
    s = max(w / im.width, h / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x, y = (im.width - w) // 2, int((im.height - h) * y_bias)
    return im.crop((x, y, x + w, y + h))


def rounded(im, r):
    m = Image.new("L", im.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, im.width - 1, im.height - 1), radius=r, fill=255)
    im = im.convert("RGBA")
    im.putalpha(m)
    return im


def paste_card(canvas, card, xy, angle=0.0, shadow=(0, 0, 0, 90), blur=18, off=(0, 14)):
    """Paste an RGBA card with a soft drop shadow, optionally rotated around its centre."""
    if angle:
        card = card.rotate(angle, resample=Image.BICUBIC, expand=True)
    sh = Image.new("RGBA", card.size, shadow)
    sh.putalpha(card.getchannel("A").point(lambda a: a * shadow[3] // 255))
    pad = blur * 3
    layer = Image.new("RGBA", (card.width + 2 * pad, card.height + 2 * pad), (0, 0, 0, 0))
    layer.alpha_composite(sh, (pad, pad))
    layer = layer.filter(ImageFilter.GaussianBlur(blur))
    canvas.alpha_composite(layer, (xy[0] - pad + off[0], xy[1] - pad + off[1]))
    canvas.alpha_composite(card, xy)


def vgradient(size, top, bottom):
    w, h = size
    g = Image.new("RGB", (1, h))
    for y in range(h):
        t = y / max(1, h - 1)
        g.putpixel((0, y), tuple(round(a + (b - a) * t) for a, b in zip(top, bottom)))
    return g.resize((w, h)).convert("RGBA")


def text_w(font_, s):
    return ImageDraw.Draw(Image.new("RGB", (1, 1))).textlength(s, font=font_)


def fit_font(make, text, max_w, start):
    size = start
    while size > 20 and text_w(make(size), text) > max_w:
        size -= 4
    return make(size)


def save_banner(img, out):
    img.convert("RGB").save(os.path.join(out, "banner_2560x1440.png"), optimize=True)
    chk = img.convert("RGB").copy()
    d = ImageDraw.Draw(chk)
    d.rectangle((0, BAND_TOP, W - 1, BAND_TOP + BAND_H), outline=(0, 255, 255), width=6)
    d.rectangle(((W - SAFE_W) // 2, BAND_TOP, (W + SAFE_W) // 2, BAND_TOP + BAND_H), outline=(255, 0, 255), width=6)
    chk.resize((1280, 720)).save(os.path.join(out, "_banner_check.png"))


# ---------- SVG path (only what the Songifted mark uses: M/m L/l C/c Z) ----------

def svg_path_points(d, steps=24):
    toks = re.findall(r"[MmLlCcZz]|-?(?:\d+\.?\d*|\.\d+)(?:e-?\d+)?", d)
    pts, cur, start, cmd, i = [], (0.0, 0.0), (0.0, 0.0), None, 0
    while i < len(toks):
        if re.match(r"[A-Za-z]", toks[i]):
            cmd = toks[i]
            i += 1
            if cmd in "Zz":
                pts.append(start)
                cur = start
                continue
        rel = cmd.islower()
        c = cmd.upper()
        n = {"M": 2, "L": 2, "C": 6}[c]
        v = [float(x) for x in toks[i:i + n]]
        i += n
        if rel:
            v = [v[k] + cur[k % 2] for k in range(n)]
        if c == "M":
            cur = start = (v[0], v[1])
            pts.append(cur)
            cmd = "l" if rel else "L"                                     # implicit lineto after moveto
        elif c == "L":
            cur = (v[0], v[1])
            pts.append(cur)
        else:
            p0, p1, p2, p3 = cur, (v[0], v[1]), (v[2], v[3]), (v[4], v[5])
            for s in range(1, steps + 1):
                t = s / steps
                u = 1 - t
                pts.append(tuple(u ** 3 * a + 3 * u * u * t * b + 3 * u * t * t * c_ + t ** 3 * e
                                 for a, b, c_, e in zip(p0, p1, p2, p3)))
            cur = p3
    return pts


SONGIFTED_S = ("M18.6 2.6c-2.8-1-8.1-.9-11.5.4-3.4 1.3-4.6 4.3-3.5 7 1 2.4 3.4 3.5 6.7 4.9l4 1.8c1.2.6.9 1.9-.4 "
               "2.4-2.6 1-7 .4-10.3.9l-.1 2c4.5.6 10.5.3 13.7-1.5 3.3-1.8 3.3-5.4-.1-7.2L9.5 9.5c-1.3-.7-.9-2 0-2.4 "
               "2.5-.8 6.8-.1 10-1l-.9-3.5Z")


def songifted_mark(size, bg, fg, mark_frac=0.64, ss=4):
    """Coral disc + ribbon S, same geometry as songifted.com/favicon.svg (mark = 64% of the canvas, bbox-centred)."""
    S = size * ss
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if bg is not None:
        d.ellipse((0, 0, S - 1, S - 1), fill=bg)
    pts = svg_path_points(SONGIFTED_S)
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    bw, bh = max(xs) - min(xs), max(ys) - min(ys)
    k = S * mark_frac / max(bw, bh)
    ox = (S - bw * k) / 2 - min(xs) * k
    oy = (S - bh * k) / 2 - min(ys) * k
    d.polygon([(x * k + ox, y * k + oy) for x, y in pts], fill=fg)
    return im.resize((size, size), Image.LANCZOS)


# ---------- Songifted ----------

SG = dict(coral=hexrgb("#D25D40"), ink=hexrgb("#2b1d16"), cream_top=hexrgb("#fdf6ee"), cream_bot=hexrgb("#f3e2d1"),
          muted=hexrgb("#7a6152"))


def songifted(out):
    # avatar: full-bleed coral (YouTube crops to a circle) + white ribbon S
    av = Image.new("RGBA", (800, 800), SG["coral"] + (255,))
    av.alpha_composite(songifted_mark(800, None, (255, 255, 255, 255), mark_frac=0.56))
    av.convert("RGB").save(os.path.join(out, "avatar_800.png"))

    img = vgradient((W, H), SG["cream_top"], SG["cream_bot"])
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((W // 2 - 900, BAND_TOP - 250, W // 2 + 900, BAND_TOP + BAND_H + 250),
                                 fill=SG["coral"] + (34,))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(160)))
    # occasion photos fanned on both sides of the desktop band (outside the all-device safe area)
    cw, ch = 300, 225                                                     # inner card must end before x~600 (text starts ~680)
    cards = [("/imgs/generated/photo-birthday.jpg", 30, -5, 40), ("/imgs/generated/photo-mom.jpg", 236, 4, 120),
             ("/imgs/generated/photo-wedding.jpg", W - 30 - cw - 24, 5, 40),
             ("/imgs/generated/photo-anniversary.jpg", W - 236 - cw - 24, -4, 120)]
    for path, x, ang, dy in cards:
        photo = cover_fit(site_img("songifted", path).convert("RGB"), cw, ch)
        frame = Image.new("RGBA", (cw + 24, ch + 24), (255, 255, 255, 255))
        frame.alpha_composite(rounded(photo, 10), (12, 12))
        paste_card(img, rounded(frame, 16), (x, BAND_TOP + dy), angle=ang, shadow=(80, 40, 20, 80))
    cx = W // 2
    d = ImageDraw.Draw(img)
    title = font("fraunces", 160, "SemiBold")
    mark = songifted_mark(128, SG["coral"] + (255,), (255, 255, 255, 255))
    tw = text_w(title, "Songifted")
    x0 = cx - (mark.width + 32 + tw) / 2
    img.alpha_composite(mark, (int(x0), BAND_TOP + 40))
    d.text((x0 + mark.width + 32, BAND_TOP + 104), "Songifted", font=title, fill=SG["ink"], anchor="lm")
    # tagline with the site's coral emphasis on "their name"
    tag = font("fraunces", 64, "Regular")
    tag_em = font("fraunces", 64, "SemiBold")
    parts = [("A custom song with ", tag, SG["ink"]), ("their name", tag_em, SG["coral"]), (" in it", tag, SG["ink"])]
    total = sum(text_w(f, s) for s, f, _ in parts)
    x = cx - total / 2
    for s, f, col in parts:
        d.text((x, BAND_TOP + 252), s, font=f, fill=col, anchor="lm")
        x += text_w(f, s)
    d.text((cx, BAND_TOP + 345), "Birthday  ·  Anniversary  ·  Mom  ·  Wedding   —   songifted.com",
           font=font("dmsans", 34, "Medium"), fill=SG["muted"], anchor="mm")
    save_banner(img, out)


# ---------- PawMotif ----------

PM = dict(ink=hexrgb("#303c33"), paper=hexrgb("#f8f6f0"), cream=hexrgb("#eeebe0"), sage=hexrgb("#e7eadf"),
          olive=hexrgb("#52634b"), muted=hexrgb("#797e70"), line=hexrgb("#dedfd3"))


def ink_cutout(im, ink):
    """The site icon is dark ink on its own light paper; keep only the ink so it sits on any background."""
    lum = im.convert("L")
    lo, hi = 70, 235                                                      # ink ~#303c33 (L~55), paper ~#faf9f6 (L~249)
    alpha = lum.point(lambda v: 255 if v <= lo else 0 if v >= hi else round(255 * (hi - v) / (hi - lo)))
    out = Image.new("RGBA", im.size, ink + (255,))
    out.putalpha(alpha)
    return out


def pawmotif(out):
    icon = ink_cutout(site_img("pawmotif", "/brand/pawmotif-icon-512.png"), PM["ink"])
    av = Image.new("RGBA", (800, 800), PM["paper"] + (255,))
    s = 600                                                               # keep the square frame inside the circle crop
    av.alpha_composite(icon.resize((s, s), Image.LANCZOS), ((800 - s) // 2, (800 - s) // 2))
    av.convert("RGB").save(os.path.join(out, "avatar_800.png"))

    img = vgradient((W, H), PM["paper"], PM["cream"])
    # gallery wall: four botanical-series portraits in thin ink frames, two per side of the desktop band
    ph = 300
    pw = round(ph * 1000 / 1500)
    fw, gap, edge = pw + 36, 20, 40                                       # framed width; inner frame ends ~x532
    lineup = [("/art/golden-portrait.webp", edge), ("/art/corgi-portrait.webp", edge + fw + gap),
              ("/art/tuxedo-portrait.webp", W - edge - fw), ("/art/calico-portrait.webp", W - edge - 2 * fw - gap)]
    for path, x in lineup:
        art = cover_fit(site_img("pawmotif", path).convert("RGB"), pw, ph)
        frame = Image.new("RGBA", (pw + 36, ph + 36), PM["ink"] + (255,))
        mat = Image.new("RGBA", (pw + 24, ph + 24), PM["paper"] + (255,))
        frame.alpha_composite(mat, (6, 6))
        frame.alpha_composite(art.convert("RGBA"), (18, 18))
        paste_card(img, frame, (x, BAND_TOP + (BAND_H - ph - 36) // 2), shadow=(48, 60, 51, 70), blur=14, off=(0, 10))
    cx = W // 2
    d = ImageDraw.Draw(img)
    title = font("georgia", 176)
    mark = icon.resize((150, 150), Image.LANCZOS)
    tw = text_w(title, "PawMotif")
    x0 = cx - (mark.width + 34 + tw) / 2
    img.alpha_composite(mark, (int(x0), BAND_TOP + 42))
    d.text((x0 + mark.width + 34, BAND_TOP + 117), "PawMotif", font=title, fill=PM["ink"], anchor="lm")
    d.text((cx, BAND_TOP + 262), "Your companion, made into art.", font=font("georgia_i", 76), fill=PM["olive"],
           anchor="mm")
    d.line((cx - 120, BAND_TOP + 318, cx + 120, BAND_TOP + 318), fill=PM["line"], width=3)
    d.text((cx, BAND_TOP + 362), "Custom pet portraits from your photo   ·   pawmotif.com",
           font=font("dmsans", 38, "Medium"), fill=PM["muted"], anchor="mm")
    save_banner(img, out)


# ---------- TryOnSwap ----------

TS = dict(bg=hexrgb("#0c0b0a"), ivory=hexrgb("#f2ede5"), gold=hexrgb("#c8a46b"), muted=hexrgb("#8f877b"))


def tryonswap(out):
    icon = site_img("tryonswap", "/brand/android-chrome-512x512-v2.png").convert("RGBA")
    av = Image.new("RGBA", (800, 800), TS["bg"] + (255,))
    av.alpha_composite(icon.resize((800, 800), Image.LANCZOS))         # rounded corners fall on black = seamless
    av.convert("RGB").save(os.path.join(out, "avatar_800.png"))

    img = Image.new("RGBA", (W, H), TS["bg"] + (255,))
    # editorial film strip: the same idea the site sells, one model photo -> many looks
    sw = 250                                                              # 2*sw+8 = 508 = just outside the safe area
    strip = [("/samples/home/model-a-1200.webp", 0), ("/samples/home/r-coat-street-1200.webp", sw + 8),
             ("/samples/home/r-dress-cinematic-1200.webp", W - sw), ("/samples/home/r-blazer-pro-1200.webp", W - 2 * sw - 8)]
    # hard-edged frames exactly the desktop band's height: soft fades turned the light studio backdrops into grey fog
    for path, x in strip:
        ph = cover_fit(site_img("tryonswap", path).convert("RGB"), sw, BAND_H, y_bias=0.3).convert("RGBA")
        img.alpha_composite(ph, (x, BAND_TOP))
    cx = W // 2
    d = ImageDraw.Draw(img)
    d.text((cx, BAND_TOP + 125), "TryOnSwap", font=font("cormorant", 210, "SemiBold"), fill=TS["ivory"], anchor="mm")
    d.text((cx, BAND_TOP + 292), "Put any garment on any model.", font=font("cormorant", 78, "Medium"),
           fill=TS["ivory"], anchor="mm")
    d.text((cx, BAND_TOP + 372), "AI VIRTUAL TRY-ON FOR BRANDS, SELLERS & CREATORS   ·   TRYONSWAP.COM",
           font=font("manrope", 30, "SemiBold"), fill=TS["gold"], anchor="mm")
    save_banner(img, out)


SITES = {"songifted": songifted, "pawmotif": pawmotif, "tryonswap": tryonswap}

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default="all", choices=["all", *SITES])
    ap.add_argument("--out", default=os.path.join(HERE, "out"))
    a = ap.parse_args()
    for name in (SITES if a.site == "all" else [a.site]):
        o = os.path.join(a.out, name)
        os.makedirs(o, exist_ok=True)
        SITES[name](o)
        print("wrote", o, sorted(os.listdir(o)))
