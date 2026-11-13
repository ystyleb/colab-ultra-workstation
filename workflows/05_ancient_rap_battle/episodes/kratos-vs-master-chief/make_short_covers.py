#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate 1080x1920 MakeItRap brand covers for Episode 08 (Kratos vs Master Chief) vertical Shorts."""
import os
import shutil
import subprocess
import sys
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

EP = os.path.dirname(os.path.abspath(__file__))
CH_DIR = os.path.abspath(os.path.join(EP, "..", "..", "channel"))
BEBAS = os.path.join(CH_DIR, "fonts", "BebasNeue-Regular.ttf")

BG = (10, 10, 10)
GOLD = (245, 197, 24)
ORANGE = (242, 106, 27)
WHITE = (248, 248, 244)

# sid -> (short_idx, clip_id, t_sec, x_frac, line1, line2)
COVERS = {
    "s1_boy_cortana": (1, "A07", 0.55, 0.65, "GRAY BEARD", 'YELLING "BOY!"'),
    "s2_console_war_goty": (2, "AXE_FROST_CU", 2.25, 0.56, "XBOX GAVE UP", "THE CONSOLE GAME!"),
    "s3_ashes_spartan_blood": (3, "KRATOS_CHAOS_ERUPT", 2.50, 0.50, "REAL SPARTANS", "BLEED IN DUST!"),
}


def bebas(size):
    return ImageFont.truetype(BEBAS, size)


def cover_fit(im, w, h, x_frac=0.5):
    s = max(w / im.width, h / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    max_x = max(0, im.width - w)
    x = int(round(max_x * max(0.0, min(1.0, x_frac))))
    y = (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))


def text_shadow(img, xy, text, font, fill, anchor="mm", shadow=ORANGE, off=(0, 0), stroke=0, glow=0):
    if glow:
        g = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(g).text(
            xy, text, font=font, fill=(0, 0, 0, 230), anchor=anchor,
            stroke_width=glow, stroke_fill=(0, 0, 0, 230),
        )
        img.alpha_composite(g.filter(ImageFilter.GaussianBlur(glow)))
    d = ImageDraw.Draw(img)
    if off != (0, 0):
        d.text((xy[0] + off[0], xy[1] + off[1]), text, font=font, fill=shadow, anchor=anchor)
    d.text(xy, text, font=font, fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill=BG)


def build_one(sid, short_idx, clip_id, t_sec, x_frac, line1, line2):
    W, H = 1080, 1920
    sdir = os.path.join(EP, "shorts", sid)
    os.makedirs(sdir, exist_ok=True)
    cover_dir = os.path.join(EP, "cover")
    os.makedirs(cover_dir, exist_ok=True)

    mp4 = os.path.join(EP, "clips", f"{clip_id}_t1.mp4")
    raw_png = os.path.join(sdir, "_cover_frame.png")
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-ss", f"{t_sec:.2f}", "-i", mp4, "-frames:v", "1", raw_png],
        check=True,
    )

    frame = Image.open(raw_png).convert("RGB")
    img = ImageEnhance.Contrast(cover_fit(frame, W, H, x_frac=x_frac)).enhance(1.12).convert("RGBA")

    # Top and bottom cinema gradient bands for crisp readability
    grad = Image.new("L", (1, H), 0)
    for y in range(H):
        top_a = int(175 * max(0.0, (H * 0.24 - y) / (H * 0.24)) ** 1.4)
        bot_a = int(230 * max(0.0, (y - H * 0.56) / (H * 0.44)) ** 1.3)
        grad.putpixel((0, y), max(top_a, bot_a))
    shade = Image.new("RGBA", (W, H), BG + (0,))
    shade.putalpha(grad.resize((W, H)))
    img.alpha_composite(shade)

    d = ImageDraw.Draw(img)
    # AI RAP BATTLE badge
    tag = "AI RAP BATTLE"
    f_tag = bebas(46)
    tw = d.textlength(tag, font=f_tag)
    d.rounded_rectangle((56, 145, 56 + tw + 40, 145 + 64), radius=12, fill=GOLD)
    d.text((56 + 20, 145 + 32), tag, font=f_tag, fill=BG, anchor="lm")

    # MASTER CHIEF VS KRATOS header (auto-fit width within W - 80)
    left, right = "MASTER CHIEF", "KRATOS"
    gap = 22
    hdr_sz = 148
    while hdr_sz > 84:
        fl, fv = bebas(hdr_sz), bebas(round(hdr_sz * 0.82))
        wl, wv, wr = (d.textlength(t, font=f) for t, f in ((left, fl), ("VS", fv), (right, fl)))
        if wl + wv + wr + 2 * gap <= W - 80:
            break
        hdr_sz -= 2
    x = (W - (wl + wv + wr + 2 * gap)) / 2
    y_hdr = 336
    text_shadow(img, (x, y_hdr), left, fl, GOLD, anchor="ls", off=(5, 5), glow=12)
    text_shadow(img, (x + wl + gap, y_hdr - 6), "VS", fv, ORANGE, anchor="ls", off=(4, 4), shadow=BG, glow=12)
    text_shadow(img, (x + wl + wv + 2 * gap, y_hdr), right, fl, GOLD, anchor="ls", off=(5, 5), glow=12)

    # 2-line punchline above YouTube Shorts bottom UI safe zone
    for idx, line in enumerate((line1, line2)):
        fs = 124
        while d.textlength(line, font=bebas(fs)) > W - 88 and fs > 72:
            fs -= 4
        text_shadow(img, (W / 2, 1345 + idx * 132), line, bebas(fs), WHITE, stroke=5, glow=14, off=(0, 0))

    out_jpg = os.path.join(sdir, "cover.jpg")
    out_ep_cover = os.path.join(cover_dir, f"short_cover_s{short_idx}.jpg")
    rgb = img.convert("RGB")
    rgb.save(out_jpg, quality=94)
    shutil.copy2(out_jpg, out_ep_cover)
    os.remove(raw_png)
    print("wrote", out_jpg, "->", out_ep_cover)
    return out_ep_cover


if __name__ == "__main__":
    outs = [build_one(sid, *COVERS[sid]) for sid in (sys.argv[1:] or COVERS)]
    imgs = [Image.open(p) for p in outs]
    sheet = Image.new("RGB", (sum(im.width for im in imgs), imgs[0].height))
    x0 = 0
    for im in imgs:
        sheet.paste(im, (x0, 0))
        x0 += im.width
    qa_p = os.path.join(EP, "preview", "qa", "shorts_covers_3up.jpg")
    os.makedirs(os.path.dirname(qa_p), exist_ok=True)
    sheet.resize((1620, 960), Image.LANCZOS).save(qa_p, quality=92)
    print("wrote", qa_p)
