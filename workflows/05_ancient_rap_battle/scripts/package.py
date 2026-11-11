# -*- coding: utf-8 -*-
"""Step 9 - packaging: grade, gold lyric subtitles (last two characters big on a red brush stroke), a source
note under every line, name cards, opening title, end question, watermark, crowd sound.

usage: python scripts/package.py <episode_dir> [--src preview/成片_拼接.mp4] [--watermark 账号名] [--test 0:15] [--phone]

Output size follows the source (2K stays 2K). Writes final/<title>_成片.mp4 (--phone: also a < 30 MB copy).
All text is drawn with Pillow into transparent PNGs and overlaid (ffmpeg's drawtext needs fontconfig, often missing).
Grade "B": softer highlights, a little less colour, adaptive sharpening and film grain - it takes the waxy,
plastic look off AI skin without darkening the film (a heavy grade made it ~30% darker once).
"""
import argparse
import os
import random
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import font, jload, load_episode  # noqa: E402
from cover import CREAM, GOLD as GOLD_GRAD, RED as RED_GRAD, fancy, row  # noqa: E402
from film_optics import film_grade_filter  # noqa: E402

GOLD = (255, 228, 92, 255)       # bright: the darker (255, 210, 64) read dull on phones
FILM_GOLD = (242, 214, 132, 246) # cinema DCP muted warm gold (less digital neon sticker glare)
INK = (40, 22, 0, 255)
GRADE = ("eq=contrast=1.04:saturation=0.92:brightness=0.01,colorbalance=rs=0.01:bs=-0.01,"
         "curves=all='0/0 0.25/0.24 0.6/0.6 0.85/0.8 1/0.92',cas=0.35,vignette=angle=PI/12,noise=alls=9:allf=t+u")


class Sheet:
    def __init__(self, w, h, film_mode=False):
        # landscape scales from a 1920 width; portrait (Shorts, 9:16) from a 1080 width so text stays readable
        self.W, self.H, self.S = w, h, (w / 1920 if w >= h else w / 1080)
        self.portrait = h > w
        self.film_mode = film_mode
        self.gold = FILM_GOLD if film_mode else GOLD

    def canvas(self):
        return Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))

    def f(self, size, weight="Black"):
        f = ImageFont.truetype(font("serif_sc"), int(size * self.S))
        try:
            f.set_variation_by_name(weight)
        except Exception:
            pass
        return f

    def shadowed(self, layer):
        sh = Image.new("RGBA", layer.size, (0, 0, 0, 0))
        sh.putalpha(layer.split()[3].point(lambda v: int(v * 0.7)))
        out = self.canvas()
        out.alpha_composite(sh.filter(ImageFilter.GaussianBlur(5 * self.S)), (int(3 * self.S), int(4 * self.S)))
        out.alpha_composite(layer)
        return out

    def brush(self, w, h, seed):
        rnd = random.Random(seed)
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        for i in range(int(h * 0.9)):
            x0 = int(rnd.uniform(0, 0.06) * w + (0.05 * w if i > h * 0.7 else 0))
            x1 = int(w - rnd.uniform(0, 0.12) * w - 0.18 * w * (i / h) ** 2)
            a = int(rnd.uniform(150, 235) * (0.55 if rnd.random() < 0.12 else 1))
            fill = (174, 28, 32, int(a * 0.88)) if self.film_mode else (190, 18, 24, a)
            d.line([(x0, int(h * 0.05) + i), (x1, int(h * 0.05) + i)], fill=fill)
        return im.filter(ImageFilter.GaussianBlur(1.2))

    def lyric(self, text, note, seed):
        if self.portrait:
            return self.lyric_portrait(text, seed)
        S, W, H = self.S, self.W, self.H
        img, layer = self.canvas(), self.canvas()
        d = ImageDraw.Draw(layer)
        han = [i for i, c in enumerate(text) if "一" <= c <= "鿿"]
        if len(han) >= 2:
            cut = han[-2]
            head, tail = text[:cut].replace(" ", "  "), text[cut:]
            fh_size, ft_size = 60, 84
        else:
            rstripped = text.rstrip()
            last_sp = rstripped.rfind(" ")
            if last_sp != -1:
                head, tail = rstripped[:last_sp + 1], rstripped[last_sp + 1:]
            else:
                head, tail = "", rstripped
            fh_size, ft_size = 48, 68
        fh, ft = self.f(fh_size), self.f(ft_size)
        wh, wt = d.textlength(head, font=fh), d.textlength(tail, font=ft)
        while (wh + wt > W - 120 * S) and fh_size > 26:
            fh_size -= 2
            ft_size = int(fh_size * 1.38)
            fh, ft = self.f(fh_size), self.f(ft_size)
            wh, wt = d.textlength(head, font=fh), d.textlength(tail, font=ft)
        base = int(H * (0.896 if note else 0.94))  # lyric-only episodes sit the line lower, where the note used to be
        x = (W - wh - wt) / 2
        img.alpha_composite(self.brush(int(wt + 46 * S), int(52 * S), seed), (int(x + wh - 20 * S), int(base - 34 * S)))
        d.text((x, base), head, font=fh, fill=self.gold, anchor="ls", stroke_width=int(3 * S), stroke_fill=INK)
        d.text((x + wh, base), tail, font=ft, fill=self.gold, anchor="ls", stroke_width=int(4 * S), stroke_fill=INK)
        if note:
            fn = self.f(36)
            while d.textlength(note, font=fn) > W - 120 * S:
                fn = ImageFont.truetype(font("serif_sc"), fn.size - 2)
                fn.set_variation_by_name("Black")
            y = int(H * 0.971)
            glow = self.canvas()               # a soft white halo makes the white read brighter
            ImageDraw.Draw(glow).text((W / 2, y), note, font=fn, fill=(255, 255, 255, 110), anchor="ms",
                                      stroke_width=int(5 * S), stroke_fill=(255, 255, 255, 70))
            layer.alpha_composite(glow.filter(ImageFilter.GaussianBlur(6 * S)))
            d.text((W / 2, y), note, font=fn, fill=(255, 255, 255, 255), anchor="ms",
                   stroke_width=int(2.5 * S), stroke_fill=(0, 0, 0, 235))
            bh = int(H * 0.18)
            band = Image.new("L", (1, bh))
            for yy in range(bh):
                band.putpixel((0, yy), int(165 * min(1, yy / (bh * 0.58))))
            img.alpha_composite(Image.merge("RGBA", [Image.new("L", (W, bh), 0)] * 3 + [band.resize((W, bh))]), (0, H - bh))
        img.alpha_composite(self.shadowed(layer))
        return img

    def lyric_portrait(self, text, seed):
        """Shorts: two centred rows above the bottom ~22% that YouTube's caption / button overlay covers;
        the last word is the big brushed punch word, as in landscape."""
        S, W, H = self.S, self.W, self.H
        img, layer = self.canvas(), self.canvas()
        d = ImageDraw.Draw(layer)
        words = text.rstrip().split(" ")
        tail = words.pop() if words else ""
        best = None   # split the remaining words so both rows are as even as possible
        for k in range(0, len(words) + 1):
            r1, r2 = " ".join(words[:k]), " ".join(words[k:])
            score = abs(len(r1) - len(r2 + " " + tail))
            if best is None or score < best[0]:
                best = (score, r1, r2)
        _, r1, r2 = best
        size = 64
        while True:
            fh, ft = self.f(size), self.f(int(size * 1.38))
            w1 = d.textlength(r1, font=fh)
            w2 = d.textlength(r2 + " ", font=fh) + d.textlength(tail, font=ft)
            if max(w1, w2) <= W - 90 * S or size <= 34:
                break
            size -= 2
        base2 = int(H * 0.775)
        base1 = base2 - int(size * 1.55 * S)
        if r1:
            d.text(((W - w1) / 2, base1), r1, font=fh, fill=self.gold, anchor="ls", stroke_width=int(3 * S), stroke_fill=INK)
        x = (W - w2) / 2
        wr2 = d.textlength(r2 + " ", font=fh)
        wt = d.textlength(tail, font=ft)
        img.alpha_composite(self.brush(int(wt + 46 * S), int(52 * S), seed), (int(x + wr2 - 20 * S), int(base2 - 34 * S)))
        d.text((x, base2), r2 + " ", font=fh, fill=self.gold, anchor="ls", stroke_width=int(3 * S), stroke_fill=INK)
        d.text((x + wr2, base2), tail, font=ft, fill=self.gold, anchor="ls", stroke_width=int(4 * S), stroke_fill=INK)
        img.alpha_composite(self.shadowed(layer))
        return img

    def name(self, name, aka, right):
        S, W, H = self.S, self.W, self.H
        img, layer = self.canvas(), self.canvas()
        d = ImageDraw.Draw(layer)
        x = W - int(150 * S) if right else int(150 * S)
        anc = "rs" if right else "ls"          # B's card sits on the right, where B stands
        y0, y1 = (0.8125, 0.849) if not self.portrait else (0.20, 0.228)   # portrait: top, clear of the lyrics
        d.text((x, int(H * y0)), "“%s”" % name, font=self.f(92), fill=self.gold, anchor=anc,
               stroke_width=int(3 * S), stroke_fill=INK)
        if aka:
            d.text((x, int(H * y1)), "aka %s" % aka, font=self.f(36, "Bold"), fill=(250, 232, 180, 255), anchor=anc,
                   stroke_width=int(2 * S), stroke_fill=INK)
        img.alpha_composite(self.shadowed(layer))
        return img

    def title(self, a, b, disclaimer="AI生成  仅供娱乐"):
        S, W, H = self.S, self.W, self.H
        img = self.canvas()
        br = ImageFont.truetype(font("brush"), int(172 * S))
        en = ImageFont.truetype(font("serif_en_bolditalic"), int(150 * S))
        row(img, W // 2, int(H * 0.44), [(a, br, GOLD_GRAD, 8), ("VS", en, RED_GRAD, 8), (b, br, GOLD_GRAD, 8)], gap=30)
        fancy(img, (W // 2, int(H * 0.58)), "FREESTYLE BATTLE", ImageFont.truetype(font("serif_en_bold"), int(64 * S)),
              GOLD_GRAD, stroke=4, shadow=8)
        fancy(img, (W // 2, int(H * 0.655)), disclaimer, self.f(40, "Bold"), CREAM, stroke=3, shadow=6)
        return img

    def hook(self, a, b, sub):
        """Shorts opener (episode.json "hook"): tells a cold viewer what this is in the first seconds -
        '<A> VS <B>' in the title-card brush style plus one short line, sized to fit the frame width."""
        S, W, H = self.S, self.W, self.H
        img = self.canvas()
        d = ImageDraw.Draw(img)
        size = 150
        while True:
            br = ImageFont.truetype(font("brush"), int(size * S))
            en = ImageFont.truetype(font("serif_en_bolditalic"), int(size * 0.87 * S))
            gap = int(22 * S)
            tw = d.textlength(a, font=br) + d.textlength("VS", font=en) + d.textlength(b, font=br) + 2 * gap
            if tw <= W - 60 * S or size <= 70:
                break
            size -= 6
        y = int(H * 0.115)
        row(img, W // 2, y, [(a, br, GOLD_GRAD, 6), ("VS", en, RED_GRAD, 6), (b, br, GOLD_GRAD, 6)], gap=gap)
        fs = 40
        while d.textlength(sub, font=self.f(fs, "Bold")) > W - 60 * S and fs > 20:
            fs -= 2
        fancy(img, (W // 2, y + int(size * 0.72 * S)), sub, self.f(fs, "Bold"), CREAM, stroke=3, shadow=6)
        return img

    def end(self, l1, l2, disclaimer="AI生成 仅供娱乐"):
        S, W, H = self.S, self.W, self.H
        img = self.canvas()
        br = ImageFont.truetype(font("brush"), int(150 * S))
        fancy(img, (W // 2, int(H * 0.40)), l1, br, GOLD_GRAD, stroke=8)
        fancy(img, (W // 2, int(H * 0.56)), l2, br, GOLD_GRAD, stroke=8)
        if self.portrait:   # the long landscape line does not fit a 9:16 width: disclaimer only, shrunk to fit
            size = 36
            while ImageDraw.Draw(img).textlength(disclaimer, font=self.f(size, "Bold")) > W - 60 * S and size > 18:
                size -= 2
            fancy(img, (W // 2, int(H * 0.68)), disclaimer, self.f(size, "Bold"), CREAM, stroke=3, shadow=6)
        else:
            fancy(img, (W // 2, int(H * 0.68)), "FREESTYLE BATTLE  ·  " + disclaimer, self.f(36, "Bold"), CREAM, stroke=3, shadow=6)
        return img

    def watermark(self, text):
        S, W = self.S, self.W
        img, layer = self.canvas(), self.canvas()
        wm_fill = (242, 214, 132, 145) if self.film_mode else (255, 228, 92, 215)
        ImageDraw.Draw(layer).text((W - int(56 * S), int(80 * S)), text, font=self.f(38, "Bold"), fill=wm_fill,
                                   anchor="rs", stroke_width=int(2 * S), stroke_fill=INK)
        img.alpha_composite(self.shadowed(layer))
        return img


def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate",
                        "-show_entries", "format=duration", "-of", "csv=p=0", path], capture_output=True, text=True).stdout.split()
    w, h, fr = r[0].split(",")
    num, den = fr.split("/")
    return int(w), int(h), round(int(num) / int(den)), float(r[1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ep")
    ap.add_argument("--src", default=None)
    ap.add_argument("--watermark", default=None)
    ap.add_argument("--test", default=None, help="from:to seconds, renders only that part")
    ap.add_argument("--phone", action="store_true")
    ap.add_argument("--film", action="store_true",
                    help="Kodak Vision3 500T + Pro-Mist 1/4 optical halation + luma-only silver grain")
    ap.add_argument("--1080p", dest="p1080", action="store_true",
                    help="Upscale cleanly to 1920x1080 (or 1080x1920) before optical bloom & grain")
    ap.add_argument("--out", default=None, help="Explicit output path (relative to episode_dir or absolute)")
    a = ap.parse_args()
    ep, e = a.ep, load_episode(a.ep)
    film_mode = bool(a.film or e.get("film_look"))
    work = os.path.join(ep, "work")
    tmp = os.path.join(work, "package_film" if film_mode else "package")
    os.makedirs(tmp, exist_ok=True)
    src = a.src or next(p for p in ("preview/成片_拼接.mp4", "preview/最终剪辑.mp4") if os.path.exists(os.path.join(ep, p)))
    W, H, fps, end = probe(os.path.join(ep, src))
    out_W, out_H = ((1080, 1920) if H > W else (1920, 1080)) if a.p1080 else (W, H)
    sh = Sheet(out_W, out_H, film_mode=film_mode)
    L = jload(os.path.join(work, "lines.json"))
    # episode.json "show_notes": false keeps only the lyric line (no Chinese history note under it)
    notes = e.get("notes", {}) if e.get("show_notes", True) else {}
    A, B = e["a"], e["b"]
    wm = a.watermark if a.watermark is not None else e.get("watermark", "")

    layers = []
    # episode.json "disclaimer": the AI / entertainment notice on the title and end cards (English channel: English)
    disc = e.get("disclaimer")
    if e.get("title_card", True):   # Shorts open straight on the first bar
        sh.title(A["name_cn"], B["name_cn"], *([disc] if disc else [])).save(os.path.join(tmp, "title.png"))
        t_title_end = min(L[0]["start"] - 0.1, float(e["title_card_secs"])) if "title_card_secs" in e else (L[0]["start"] - 0.1)
        layers.append(("title.png", 0.0, t_title_end, 0.3))
    hook = e.get("hook")   # Shorts: {"a": "EDISON", "b": "TESLA", "sub": "...", "secs": 2.6}
    if hook:
        sh.hook(hook["a"], hook["b"], hook["sub"]).save(os.path.join(tmp, "hook.png"))
        layers.append(("hook.png", 0.0, float(hook.get("secs", 2.6)), 0.3))
    for who, right in (("a", False), ("b", True)) if e.get("name_cards", True) else ():
        # a Short may hold only some lines of one rapper: the card goes on that rapper's first line in the clip
        first = next((l for l in L if l["who"] == who), None)
        if first is None:
            continue
        # episode.json "name_card_lines": how many lines the name card stays up (default 2). Use 1 when the
        # storyboard cuts to the opponent's reaction inside line 2, or the card labels the wrong face.
        n_card = int(e.get("name_card_lines", 2))
        second = next((l for l in L if l["who"] == who and l["n"] == first["n"] + n_card - 1), first)
        sh.name(e[who]["name_cn"], e[who].get("aka", ""), right).save(os.path.join(tmp, "name_%s.png" % who))
        layers.append(("name_%s.png" % who, first["start"] - 0.08, second["end"] - 0.1, 0.25))
    for i, l in enumerate(L):
        ns = notes.get(l["who"], [])
        note = ns[l["n"] - 1] if l["n"] - 1 < len(ns) else ""
        sh.lyric(l["text"], note, i).save(os.path.join(tmp, "line_%02d.png" % i))
        last = i + 1 == len(L) or L[i + 1]["who"] != l["who"]
        # the last line of a verse lingers 0.5 s, but never into the next rapper's first line when the verses abut
        nxt = L[i + 1]["start"] - 0.07 if i + 1 < len(L) else None
        hold = l["end"] + 0.5 if nxt is None else min(l["end"] + 0.5, nxt)
        layers.append(("line_%02d.png" % i, l["start"] - 0.05, hold if last else nxt, 0.0))
    q = e.get("end_question", "下一场|你想看谁的对决？").split("|")
    sh.end(q[0], q[-1], *([disc] if disc else [])).save(os.path.join(tmp, "end.png"))
    # episode.json "end_card_secs" (default 4.6): shorten it when the outro carries reaction shots of its own
    # never on top of the last lyric line (Shorts end only ~1.8 s after the last word)
    last_lyric = max(en for png, st, en, fd in layers if png.startswith("line_"))
    layers.append(("end.png", max(end - float(e.get("end_card_secs", 4.6)), last_lyric + 0.05), end, 0.5))
    if wm:
        sh.watermark(wm).save(os.path.join(tmp, "watermark.png"))
        layers.append(("watermark.png", 0.0, end, 0.0))

    t_from, t_to = (0.0, end)
    if a.test:
        t_from, t_to = [float(x) for x in a.test.split(":")]
    inputs = ["-ss", "%.3f" % t_from, "-t", "%.3f" % (t_to - t_from), "-i", os.path.join(ep, src),
              "-ss", "%.3f" % t_from, "-t", "%.3f" % (t_to - t_from), "-i", os.path.join(work, "music_final.wav")]
    # episode.json "grade": ffmpeg filter chain replacing the default GRADE ("null" = none). assemble.py already
    # grades once (work/live.json); the default second pass made the 2026-11-10 remake too dark and grey.
    if film_mode:
        fc = [film_grade_filter("0:v", "base", target_size=(out_W, out_H) if (out_W, out_H) != (W, H) else None)]
    else:
        scale_pre = (f"scale={out_W}:{out_H}:force_original_aspect_ratio=increase:flags=lanczos,crop={out_W}:{out_H},"
                     if (out_W, out_H) != (W, H) else "")
        fc = ["[0:v]%s%s,format=yuv420p,setpts=PTS-STARTPTS[base]" % (scale_pre, e.get("grade") or GRADE)]
    last, k = "base", 2
    for idx, (png, st, en, fade) in enumerate(layers):
        st, en = max(st, t_from) - t_from, min(en, t_to) - t_from
        if en - st < 0.05:
            continue
        dur = en - st
        inputs += ["-loop", "1", "-framerate", "30", "-t", "%.3f" % dur, "-i", os.path.join(tmp, png)]
        ch = "[%d:v]format=rgba" % k
        if fade:
            ch += ",fade=t=in:st=0:d=%.2f:alpha=1,fade=t=out:st=%.3f:d=%.2f:alpha=1" % (fade, max(0, dur - fade), fade)
        fc += [ch + ",setpts=PTS-STARTPTS+%.3f/TB[l%d]" % (st, idx), "[%s][l%d]overlay=0:0:eof_action=pass[o%d]" % (last, idx, idx)]
        last, k = "o%d" % idx, k + 1

    # crowd sound: from the Seedance opening / break / ending clips (assembly.json), quietly under the music
    labels = ["[1:a]"]
    asm = os.path.join(work, "assembly.json")
    vol = {"open": 0.35, "break": 0.45, "end": 0.55}
    for j, x in enumerate(jload(asm)["ambience"] if os.path.exists(asm) else []):
        s0, s1 = max(x["song"][0], t_from), min(x["song"][1], t_to)
        if s1 - s0 < 0.2:
            continue
        inputs += ["-ss", "%.3f" % (x["src"] + s0 - x["song"][0]), "-t", "%.3f" % (s1 - s0), "-i", os.path.join(ep, x["clip"])]
        fc.append("[%d:a]aresample=44100,aformat=channel_layouts=stereo,volume=%.2f,afade=t=in:d=0.25,afade=t=out:st=%.3f:d=0.4,"
                  "adelay=%d:all=1[c%d]" % (k, vol[x["kind"]], max(0, s1 - s0 - 0.4), int((s0 - t_from) * 1000), j))
        labels.append("[c%d]" % j)
        k += 1
    fc.append("%samix=inputs=%d:normalize=0:duration=first,alimiter=limit=0.95[aout]" % ("".join(labels), len(labels)))
    os.makedirs(os.path.join(ep, "final"), exist_ok=True)
    if a.out:
        out = a.out if os.path.isabs(a.out) else os.path.join(ep, a.out)
        os.makedirs(os.path.dirname(out), exist_ok=True)
    elif film_mode:
        tag = ("_1080p_胶片版" if a.p1080 else "_成片_胶片版") + ("_测试" if a.test else "")
        out = os.path.join(ep, "final", "%s%s.mp4" % (e["title"], tag))
    else:
        out = os.path.join(ep, "final", "%s_成片%s.mp4" % (e["title"], "_测试" if a.test else ""))
    subprocess.run(["ffmpeg", "-y", "-v", "error"] + inputs +
                   ["-filter_complex", ";".join(fc), "-map", "[%s]" % last, "-map", "[aout]",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(fps),
                    "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", out], check=True)
    print("wrote", out)
    if a.phone:
        phone = out.replace(".mp4", "_手机预览.mp4")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", out, "-vf", "scale=1280:-2", "-r", "30", "-c:v", "libx264",
                        "-preset", "slow", "-b:v", "2000k", "-maxrate", "2400k", "-bufsize", "4000k", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", phone], check=True)
        print("wrote", phone)


if __name__ == "__main__":
    main()
