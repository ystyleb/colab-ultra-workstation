#!/usr/bin/env python3
"""10 AI Influencer Matrix: 0-CCU Storefront Cover & Social Profile Avatar Generator.

Generates using local PIL (0 CCU):
- `out/<persona>/avatar_800x800.png` + `_avatar_circle_check.png`
- `out/<persona>/gumroad_free_cover_1280x720.png`
- `out/<persona>/gumroad_paid_cover_1280x720.png`
- `out/matrix_launch_board.jpg` (combined visual inspection board)
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
CONFIG_PATH = HERE / "influencer_config.json"
SAMPLE_DIR = HERE / "sample_inputs"
OUT_DIR = HERE / "out"

PALETTES = {
    "vivian": {
        "bg1": (18, 39, 34),
        "bg2": (11, 22, 20),
        "card": (250, 248, 243),
        "accent": (190, 152, 90),
        "ink": (28, 31, 30),
        "badge_fg": (15, 22, 20),
    },
    "june": {
        "bg1": (92, 63, 43),
        "bg2": (46, 31, 22),
        "card": (251, 247, 242),
        "accent": (214, 170, 120),
        "ink": (42, 36, 32),
        "badge_fg": (40, 28, 20),
    },
    "wen": {
        "bg1": (40, 64, 50),
        "bg2": (20, 33, 26),
        "card": (246, 245, 238),
        "accent": (184, 150, 96),
        "ink": (31, 36, 32),
        "badge_fg": (24, 30, 26),
    },
}

# 封面文案按人设 × 档位写死，避免 V2 的「30 天打卡」话术套到 V3.1 产品上（Wen 明确不设天数和连续打卡）。
COVER_COPY = {
    ("vivian", "free"): ("FREE 72-HOUR AUDIT", "• 4-page printable audit · instant DM download", "• Find the approval taxes you'd rather not pay"),
    ("vivian", "paid"): ("THE COMPLETE GUIDE", "• 11 pages: 10 spending rules + worksheets", "• Scripts for raises, loans & splitting the bill"),
    ("june", "free"): ("FREE 3-DAY JOURNAL", "• 4-page printable journal · instant DM download", "• Three small moments worth writing down"),
    ("june", "paid"): ("DATING & PARTNERED EDITIONS", "• 11 pages: record, find patterns, prepare one talk", "• Separate chapters for dating and long-term partners"),
    ("wen", "free"): ("FREE · 20 PAUSE CARDS", "• Pick by situation · skip any · no streaks", "• Printable cards with stories from Zhuangzi"),
    ("wen", "paid"): ("LOOK IT UP WHEN YOU NEED IT", "• 16 everyday troubles, one story each", "• One small step + one thing to skip · no tracking"),
}


def load_font(size: int, bold: bool = False, serif: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = []
    if serif and bold:
        candidates += [
            "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
            "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",
        ]
    elif serif:
        candidates += [
            "/System/Library/Fonts/Supplemental/Georgia.ttf",
            "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
        ]
    elif bold:
        candidates += [
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
        ]
    else:
        candidates += [
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
        ]
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


def make_gradient(w: int, h: int, c1: tuple[int, int, int], c2: tuple[int, int, int]) -> Image.Image:
    im = Image.new("RGB", (w, h), c1)
    draw = ImageDraw.Draw(im)
    for y in range(h):
        t = y / max(1, h - 1)
        col = tuple(int(c1[i] * (1 - t) + c2[i] * t) for i in range(3))
        draw.line([(0, y), (w, y)], fill=col)
    return im


def make_avatar(src_portrait: Path, out_dir: Path) -> Path:
    im = Image.open(src_portrait).convert("RGB")
    w, h = im.size
    # Portrait is 768x1344 with 18-22% headroom; crop upper-torso square [y: 60..828]
    side = min(w, h)
    top = min(max(0, int(h * 0.05)), h - side)
    sq = im.crop((0, top, side, top + side)).resize((800, 800), Image.LANCZOS)
    av_path = out_dir / "avatar_800x800.png"
    sq.save(av_path)

    # Circle crop visual preview
    chk = Image.new("RGB", (800, 800), (16, 17, 20))
    mask = Image.new("L", (800, 800), 0)
    ImageDraw.Draw(mask).ellipse((20, 20, 780, 780), fill=255)
    chk.paste(sq, (0, 0), mask)
    chk.save(out_dir / "_avatar_circle_check.png")
    return av_path


def make_cover(
    pk: str,
    persona: dict,
    tier: str,
    src_portrait: Path,
    out_path: Path,
) -> Path:
    pal = PALETTES[pk]
    prod = persona["products"][tier]
    w, h = 1280, 720
    canvas = make_gradient(w, h, pal["bg1"], pal["bg2"])
    draw = ImageDraw.Draw(canvas)

    # Decorative right panel with portrait crop
    port = Image.open(src_portrait).convert("RGB")
    pw, ph = port.size
    crop_h = int(pw * 1.25)
    y0 = max(0, int(ph * 0.04))
    port_sq = port.crop((0, y0, pw, min(ph, y0 + crop_h))).resize((440, 560), Image.LANCZOS)

    # Rounded card frame on right
    px, py = 785, 80
    draw.rounded_rectangle((px - 10, py - 10, px + 450, py + 570), radius=24, fill=pal["accent"])
    mask = Image.new("L", (440, 560), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, 440, 560), radius=18, fill=255)
    canvas.paste(port_sq, (px, py), mask)

    # Subtle bottom gradient badge on portrait
    draw.rounded_rectangle((px + 14, py + 485, px + 426, py + 542), radius=12, fill=(16, 18, 20))
    f_badge_sm = load_font(17, bold=True)
    badge_txt = f"{persona['display_name']} | {persona['handle']}"
    tb = draw.textbbox((0, 0), badge_txt, font=f_badge_sm)
    draw.text((px + (440 - (tb[2] - tb[0])) // 2, py + 503), badge_txt, fill=(248, 244, 234), font=f_badge_sm)

    # Left typography block
    lx = 68
    f_kicker = load_font(22, bold=True)
    f_title = load_font(48, bold=True, serif=True)
    f_sub = load_font(25, bold=False)
    f_cta = load_font(25, bold=True)
    f_meta = load_font(19, bold=True)

    kicker_txt, b1, b2 = COVER_COPY[(pk, tier)]
    kb = draw.textbbox((0, 0), kicker_txt, font=f_kicker)
    draw.rounded_rectangle((lx, 76, lx + (kb[2] - kb[0]) + 48, 122), radius=23, fill=pal["accent"])
    draw.text((lx + 24, 87), kicker_txt, fill=pal["badge_fg"], font=f_kicker)

    title_lines = textwrap.wrap(prod["title"], width=22)
    ty = 152
    for line in title_lines[:3]:
        draw.text((lx, ty), line, fill=(252, 249, 242), font=f_title)
        ty += 58

    sub_lines = textwrap.wrap(prod["subtitle"], width=42)
    sy = ty + 18
    for line in sub_lines[:3]:
        draw.text((lx, sy), line, fill=(214, 218, 212), font=f_sub)
        sy += 34

    # Simulated mini workbook checklist card
    cy = 436
    draw.rounded_rectangle((lx, cy, lx + 650, cy + 124), radius=16, fill=pal["card"])
    # 只显示真实售价：anchor_price_usd 是从未实际售出过的「原价」，划线展示属于虚构原价（FTC 16 CFR 233）。
    price_lbl = "FREE ($0+)" if tier == "free" else f"${prod['price_usd']:.0f}"

    draw.text((lx + 24, cy + 20), b1, fill=pal["ink"], font=f_meta)
    draw.text((lx + 24, cy + 54), b2, fill=pal["ink"], font=f_meta)
    draw.text((lx + 24, cy + 88), f"FORMAT: A4 PDF DOWNLOAD   |   {price_lbl}", fill=pal["accent"], font=f_meta)

    # Bottom CTA pill
    draw.rounded_rectangle((lx, 590, lx + 420, 650), radius=14, fill=pal["accent"])
    draw.text((lx + 28, 606), prod["cta"], fill=pal["badge_fg"], font=f_cta)

    canvas.save(out_path)
    return out_path


def build_launch_board(cfg: dict, generated: dict[str, dict[str, Path]]) -> Path:
    """Assemble avatars + free/paid covers for all 3 personas into one visual inspection sheet."""
    row_h = 380
    pad = 26
    w = 1880
    h = pad + len(generated) * (row_h + pad) + 60
    board = Image.new("RGB", (w, h), (16, 17, 21))
    draw = ImageDraw.Draw(board)
    f_hdr = load_font(28, bold=True)
    f_lbl = load_font(20, bold=True)
    draw.text((pad, 18), "WORKFLOW 10: AI INFLUENCER MATRIX — AVATARS & GUMROAD STOREFRONT COVERS", fill=(246, 236, 214), font=f_hdr)

    for idx, (pk, paths) in enumerate(generated.items()):
        y0 = 68 + idx * (row_h + pad)
        p_info = cfg["personas"][pk]
        draw.text((pad, y0), f"{p_info['display_name']} ({p_info['handle']}) — {p_info['niche']} [Keyword: {p_info['manychat_keyword']}]", fill=(235, 224, 198), font=f_lbl)
        y_img = y0 + 34
        av = Image.open(paths["avatar"]).convert("RGB").resize((330, 330), Image.LANCZOS)
        fc = Image.open(paths["free"]).convert("RGB").resize((586, 330), Image.LANCZOS)
        pc = Image.open(paths["paid"]).convert("RGB").resize((586, 330), Image.LANCZOS)
        board.paste(av, (pad, y_img))
        board.paste(fc, (pad * 2 + 330, y_img))
        board.paste(pc, (pad * 3 + 330 + 586, y_img))

    out_board = OUT_DIR / "matrix_launch_board.jpg"
    board.save(out_board, quality=92)
    return out_board


def main() -> None:
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    generated: dict[str, dict[str, Path]] = {}

    for pk, persona in cfg["personas"].items():
        scene_keys = list(persona["scenes"].keys())
        primary_img = SAMPLE_DIR / persona["scenes"][scene_keys[0]]["image"]
        secondary_img = SAMPLE_DIR / persona["scenes"][scene_keys[-1]]["image"]
        if not primary_img.exists():
            raise FileNotFoundError(f"Missing portrait keyframe: {primary_img}. Run gen_keyframes.py first.")
        if not secondary_img.exists():
            secondary_img = primary_img

        p_out = OUT_DIR / pk
        p_out.mkdir(parents=True, exist_ok=True)
        av_p = make_avatar(primary_img, p_out)
        free_p = make_cover(pk, persona, "free", primary_img, p_out / "gumroad_free_cover_1280x720.png")
        paid_p = make_cover(pk, persona, "paid", secondary_img, p_out / "gumroad_paid_cover_1280x720.png")
        generated[pk] = {"avatar": av_p, "free": free_p, "paid": paid_p}
        print(f"✅ [{pk}] avatar={av_p.name}, covers={free_p.name}, {paid_p.name}", flush=True)

    board = build_launch_board(cfg, generated)
    print(f"🖼️ 店铺与头像总览看板: {board}", flush=True)


if __name__ == "__main__":
    main()
