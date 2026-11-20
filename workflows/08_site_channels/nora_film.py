#!/usr/bin/env python3
"""Songifted 横屏故事片《Nora》（1920x1080，约 196 秒）。

配乐是站上 /demos/for-wife.mp3（虚构 Nora，3:10）整首，成片时间 = 歌内时间：从前奏开始，190 s 歌唱完后接片尾。
丈夫送给妻子的结婚纪念歌：现在的厨房（他放歌、她听）和 12 年的平常日子（漏雨的第一间公寓、午夜烤焦的吐司、
最难的那一年、搬家、路边抛锚）交替，镜头切点卡在歌词换句上。

镜头：samples/songifted_nora/keyframes.json（Codex 关键帧）→ jobs.json（H3 FL2VA 1344x768）→ 本脚本。
H3 片段还没出的镜头自动用关键帧静帧（首帧→尾帧交叉淡化 + 慢推），所以开机前就能先看样片审节奏。

python3 workflows/08_site_channels/nora_film.py --animatic       # 全部用关键帧（0 CCU 样片）
python3 workflows/08_site_channels/nora_film.py --preview        # 960x540，H3 有的用 H3
python3 workflows/08_site_channels/nora_film.py                  # 成片
python3 workflows/08_site_channels/nora_film.py --take N18_Walk=2 # 指定某镜头用第几个 seed
"""
from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from songifted_longform import CORAL, WHITE, fade, font, put, text_img

HERE = Path(__file__).resolve().parent
NS = HERE / "samples" / "songifted_nora"
KF = NS / "kf"
CLIPS = HERE / "out" / "samples" / "songifted_nora"
SONG = HERE / "samples" / "songifted" / "demos" / "for-wife.mp3"
OUT = HERE / "out" / "promo" / "songifted" / "Songifted_Story_Nora_1920x1080.mp4"

W, H, FPS = 1920, 1080, 24
SONG_END = 190.0
T_CARD = 182.5     # 片尾字卡开始淡入（尾声「it always was you」之前）
T_TOTAL = 196.0
OFFER = "Free 45-second preview for eligible first-time creators. Full songs from $49."
CREDIT = "Song: example from songifted.com (fictional “Nora”) · Scenes: AI dramatization"


@dataclass
class Shot:
    t0: float               # 成片起点（秒）
    t1: float               # 成片终点
    job: str | None         # H3 job 前缀（N04_Leak）；None = 静帧镜头
    first: str              # 关键帧名（静帧/样片用）
    last: str | None = None
    src_in: float = 0.25    # H3 片段入点：跳过开头几帧定格
    zoom: tuple[float, float] = (1.0, 1.04)  # 静帧/样片的慢推
    speed: float = 1.0      # <1 = 慢放（H3 片段不够长时用，帧间混合补帧）
    loop: float = 0.0       # >0 = 片段循环播放，接缝处交叉淡化这么多秒（静态雨景尾声用：H3 长片会自己剪成多镜头）


# 切点卡在歌词换句上（逐词时间戳见 README）
SHOTS = [
    Shot(0.0, 6.0, "N01_Counter", "n01_counter"),
    Shot(6.0, 12.3, "N02_Play", "n02_play"),
    Shot(12.3, 18.9, "N03_Name", "n03_name"),            # 「Nora, it was nothing, just a Tuesday」
    Shot(18.9, 23.9, "N04_Leak", "n04_leak_a", "n04_leak_b"),   # 「Rain came through the window we never fixed」
    Shot(23.9, 28.6, "N05_Toast", "n05_toast_a", "n05_toast_b"),  # 「You made toast at midnight」
    Shot(28.6, 32.7, "N06_Floor", "n06_floor"),           # 「laughed at nothing」
    Shot(32.7, 38.6, "N07_Smile", "n07_smile"),           # 「Twelve years on, we still bring up that night」
    Shot(38.6, 44.8, None, "n08_wedding", zoom=(1.0, 1.10)),  # 「Everyone remembers wedding photographs」
    Shot(44.8, 53.5, "N09_Dawn", "n09_dawn"),             # 「Nobody remembers ordinary days, but that's the one I keep」
    Shot(53.5, 58.8, "N10_Him", "n10_him"),               # 副歌 1
    Shot(58.8, 64.0, "N11_Dishes", "n11_dishes"),         # 「Not the big nights, the ones that nobody knew」
    Shot(64.0, 69.7, "N12_Tape", "n12_tape", speed=0.94),  # 「Burnt toast, a broken window and the rain」T1 第 151 帧弹回远景（尾帧锁），0.94× 读到 148 帧
    Shot(69.7, 75.8, "N13_Tear", "n13_tear"),
    Shot(75.8, 80.4, "N14_HospEdge", "n14_hosp_edge"),    # 「Then the year came round when nothing worked」
    Shot(80.4, 88.4, "N15_Drive", "n15_drive", speed=0.95),  # T2 第 196 帧硬切回远景，慢放让取帧停在 194 前           # 「You drove through the dark and never made a sound」
    Shot(88.4, 96.7, "N16_HospChair", "n16_hosp_chair", speed=0.86),  # T1 第 193 帧硬切；含 0.6 s 长淡化，0.86× 读到 190 帧  # 「You carried what I couldn't carry then」
    Shot(96.7, 102.1, "N17_HimClose", "n17_him_close"),   # 「And I have never said it out loud」
    Shot(102.1, 108.0, "N18_Walk", "n18_walk_a", "n18_walk_b"),  # 副歌 2
    Shot(108.0, 116.0, "N19_Hug", "n19_hug"),
    Shot(116.0, 122.5, "N20_Window", "n20_window"),       # 「a broken window in the rain」
    Shot(122.5, 130.8, "N21_Roadside", "n21_roadside"),   # 「And you still say "well, that went well"」
    Shot(130.8, 135.7, "N22_Box", "n22_box_a", "n22_box_b"),  # 「when everything is falling through」
    Shot(135.7, 144.5, "N23_FloorLaugh", "n23_floorlaugh", speed=0.96),  # T1 第 231 帧硬切，同上   # 「Nobody else would know to laugh, that one is ours」
    Shot(144.5, 153.9, "N24_Forehead", "n24_forehead"),   # 「That one is you」
    Shot(153.9, 163.0, "N25_Dance", "n25_dance", speed=0.97),  # T1 第 227 帧硬切回远景，0.97× 读到 224 帧         # 副歌 3
    Shot(163.0, 169.0, "N26_Toast", "n26_toast_a", "n26_toast_b"),  # 「Burnt toast…」164.8
    Shot(169.0, 176.3, "N27_Laugh", "n27_laugh"),
    Shot(176.3, T_TOTAL, "N28_Exterior", "n28_exterior", zoom=(1.0, 0.94), src_in=2.0, loop=1.0),  # 尾声慢慢拉远。T6 192 帧，2 s 后焦点已柔化，从那里起循环（1 s 交叉淡化）；H3 362 帧长片会自己剪成多镜头
]
XFADE = 0.25  # 镜头之间的短交叉淡化（秒）；时代切换处更长
LONG_XFADE = {18.9, 32.7, 44.8, 53.5, 58.8, 69.7, 75.8, 96.7, 102.1, 116.0, 122.5, 144.5, 153.9}

# 歌词字幕（逐词时间戳；whisper 听不清的地方以首页/歌名为准，交付前请用户听一遍）
LYRICS = [
    (12.3, 18.4, "Nora, it was nothing, just a Tuesday"),
    (18.9, 23.6, "Rain came through the window we never fixed"),
    (23.9, 31.6, "You made toast at midnight, laughed at nothing"),
    (32.7, 38.2, "Twelve years on, we still bring up that night"),
    (38.6, 44.2, "Everyone remembers wedding photographs"),
    (44.8, 49.0, "Nobody remembers ordinary days"),
    (49.1, 52.8, "But that's the one I keep"),
    (53.5, 58.4, "Nora, it was always gonna be you"),
    (58.8, 63.6, "Not the big nights, the ones that nobody knew"),
    (64.1, 69.3, "Burnt toast, a broken window and the rain"),
    (69.7, 75.0, "Nora, it was always gonna be you"),
    (75.8, 80.0, "Then the year came round when nothing worked"),
    (80.4, 87.6, "You drove through the dark and never made a sound"),
    (88.4, 94.5, "You carried what I couldn't carry then"),
    (96.7, 101.6, "And I have never said it out loud"),
    (102.1, 106.8, "Nora, it was always gonna be you"),
    (107.3, 112.4, "Not the big nights, the ones that nobody knew"),
    (112.9, 118.0, "Burnt toast, a broken window in the rain"),
    (118.5, 122.3, "Nora, it was always gonna be you"),
    (124.7, 130.4, "And you still say, “Well, that went well”"),
    (131.7, 135.4, "when everything is falling through"),
    (135.7, 144.9, "Nobody else would know to laugh — that one is ours"),
    (149.2, 152.8, "That one is you"),
    (153.9, 158.8, "Nora, it was always gonna be you"),
    (159.3, 164.3, "Not the big nights, the ones that nobody knew"),
    (164.8, 169.8, "Burnt toast, a broken window in the rain"),
    (170.5, 175.6, "Nora, it was always gonna be you"),
    (176.3, 181.6, "Nora, it was always you"),
]
ERAS = [(18.9, 22.4, "Twelve years earlier"), (75.8, 79.4, "Five years ago"), (122.5, 126.0, "The years in between")]


# ---------------- 取帧 ----------------
LOOP_TRIM = 8  # 循环片段丢掉最后 8 帧（锁尾帧的弹回、片尾定格）
# 选片（screen_takes.py 联系表逐条看过，2026-11-20）。0 = 还没有合格的片段，用关键帧代替；--take 可覆盖
TAKES: dict[str, int] = {
    # 首尾同图（锁尾帧）合格的
    "N03_Name": 1, "N04_Leak": 2, "N05_Toast": 1, "N07_Smile": 1, "N11_Dishes": 1, "N12_Tape": 1, "N13_Tear": 1,
    "N15_Drive": 2, "N16_HospChair": 1, "N18_Walk": 1, "N22_Box": 2, "N23_FloorLaugh": 1, "N24_Forehead": 1,
    "N25_Dance": 1, "N27_Laugh": 1,
    # 第二轮只锁首帧（first_only）选中的
    "N01_Counter": 3, "N02_Play": 4, "N06_Floor": 3, "N10_Him": 3, "N14_HospEdge": 3, "N17_HimClose": 3,
    "N19_Hug": 3, "N20_Window": 3, "N21_Roadside": 3, "N26_Toast": 3,
    # 第三轮：N09 去掉拨头发的动作，N28 改 192 帧 + 合成循环
    "N09_Dawn": 6, "N28_Exterior": 6,
}


def clip_path(job: str) -> Path | None:
    t = TAKES.get(job)
    if t == 0:
        return None
    cands = [CLIPS / f"{job}_T{t}_Master.mp4"] if t else sorted(CLIPS.glob(f"{job}_T*_Master.mp4"))
    return next((c for c in cands if c.exists()), None)


@lru_cache(maxsize=4)
def clip_frames(path: Path, src_in: float, dur: float, speed: float = 1.0) -> list[Image.Image]:
    n = round(dur * FPS) + 2
    retime = f"setpts=PTS/{speed},framerate=fps={FPS}" if speed < 1 else f"fps={FPS}"
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{src_in:.3f}", "-i", str(path), "-frames:v", str(n),
                          "-vf", f"{retime},scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H}",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    out = []
    while True:
        b = p.stdout.read(W * H * 3)
        if len(b) < W * H * 3:
            break
        out.append(Image.frombytes("RGB", (W, H), b))
    p.wait()
    if not out:
        raise RuntimeError(f"读不到帧 {path}")
    return out


@lru_cache(maxsize=64)
def kf_img(name: str) -> Image.Image:
    return Image.open(KF / f"{name}_1344x768.png").convert("RGB").resize((W, H), Image.LANCZOS)


def zoomed(im: Image.Image, z: float) -> Image.Image:
    if abs(z - 1) < 1e-3:
        return im
    cw, ch = W / z, H / z
    x0, y0 = (W - cw) / 2, (H - ch) / 2
    return im.crop((round(x0), round(y0), round(x0 + cw), round(y0 + ch))).resize((W, H), Image.BILINEAR)


def shot_frame(s: Shot, t: float, animatic: bool) -> Image.Image:
    p = (t - s.t0) / (s.t1 - s.t0)
    path = None if (animatic or not s.job) else clip_path(s.job)
    if path:
        # 交叉淡化时上一镜要续播到 t1 + xf（长淡化 0.6 s），只读 +0.25 s 会在淡化后半段定格
        tail = 0.6 if any(abs(x - s.t1) < 0.05 for x in LONG_XFADE) else XFADE
        k = int((t - s.t0) * FPS)
        if s.loop > 0:
            fr = clip_frames(path, s.src_in, 3600, 1.0)[:-LOOP_TRIM]  # 读完整片段，去掉尾部定格/弹回帧
            d = round(s.loop * FPS)
            period = len(fr) - d
            cyc, pos = divmod(k, period)
            im = fr[pos]
            if cyc > 0 and pos < d:  # 新一轮开头与上一轮结尾交叉淡化
                im = Image.blend(fr[period + pos], im, (pos + 1) / (d + 1))
        else:
            fr = clip_frames(path, s.src_in, s.t1 - s.t0 + tail, s.speed)
            im = fr[min(len(fr) - 1, k)]
        if s.zoom[1] < 1:  # 尾声拉远照样做
            im = zoomed(im, 1 + (1 / s.zoom[1] - 1) * (1 - p))  # 拉远：从 1/z1 倍缩回 1 倍
        return im
    a = kf_img(s.first)
    if s.last:
        a = Image.blend(a, kf_img(s.last), max(0.0, min(1.0, (p - 0.15) / 0.7)))
    z0, z1 = s.zoom
    if z1 < 1:
        return zoomed(a, 1 + (1 / z1 - 1) * (1 - p))
    return zoomed(a, z0 + (z1 - z0) * p)


# ---------------- 叠加 ----------------
def lyric_overlay(img: Image.Image, t: float):
    for t0, t1, line in LYRICS:
        a = fade(t, t0, t1, 0.25)
        if a > 0:
            card = text_img(line, ("fraunces", 46, "Regular"), WHITE, 1600, align="center")
            sh = Image.new("RGBA", (card.width + 60, card.height + 40), (0, 0, 0, 0))
            sh.alpha_composite(card, (30, 20))
            blur = Image.new("RGBA", sh.size, (0, 0, 0, 0))
            blur.putalpha(sh.getchannel("A").filter(ImageFilter.GaussianBlur(8)).point(lambda v: int(v * 0.85)))
            put(img, blur, W // 2, H - 120, a, "mm")
            put(img, card, W // 2, H - 120, a, "mm")


def era_overlay(img: Image.Image, t: float):
    for t0, t1, txt in ERAS:
        a = fade(t, t0 + 0.2, t1, 0.4)
        if a > 0:
            put(img, text_img(txt, ("dmsans", 30, "Medium"), (240, 230, 220)), 80, 70, a * 0.9)


def title_overlay(img: Image.Image, t: float):
    a = fade(t, 1.2, 10.8, 0.8)
    if a > 0:
        put(img, text_img("Nora", ("fraunces", 120, "SemiBold"), WHITE), 120, 760, a)
        put(img, text_img("Twelve years of ordinary days, in one song", ("dmsans", 36, "Medium"), (245, 235, 225)), 128, 905, a)


@lru_cache(maxsize=1)
def logo_white() -> Image.Image:
    from promo_short import rounded
    return rounded(Image.open(HERE / "out" / "songifted" / "avatar_800.png").convert("RGB").resize((88, 88), Image.LANCZOS), 44)


def card_overlay(img: Image.Image, t: float):
    if t < T_CARD:
        return
    k = min(1.0, (t - T_CARD) / 1.5)
    img.alpha_composite(Image.new("RGBA", (W, H), (12, 8, 6, int(170 * k))))
    lt = t - T_CARD
    put(img, text_img("He made her a song with her name in it.", ("fraunces", 72, "SemiBold"), WHITE, 1600, align="center"),
        W // 2, 330, fade(lt, 0.6, 99, 0.6), "mt")
    a = fade(lt, 1.6, 99, 0.5)
    f = font("dmsans", 60, "Bold")
    w = int(ImageDraw.Draw(img).textlength("songifted.com", font=f)) + 110
    p = Image.new("RGBA", (w, 108), (0, 0, 0, 0))
    ImageDraw.Draw(p).rounded_rectangle((0, 0, w - 1, 107), radius=54, fill=CORAL + (255,))
    ImageDraw.Draw(p).text((w // 2, 54), "songifted.com", font=f, fill=WHITE + (255,), anchor="mm")
    put(img, p, W // 2, 500, a, "mt")
    put(img, text_img(OFFER, ("dmsans", 34, "Medium"), (240, 230, 220), 1500, align="center"), W // 2, 660, fade(lt, 2.2, 99, 0.5), "mt")
    put(img, text_img(CREDIT, ("dmsans", 26, "Medium"), (200, 190, 180), 1600, align="center"), W // 2, 960, fade(lt, 2.6, 99, 0.5), "mt")
    if t > T_TOTAL - 1.0:
        img.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * (t - (T_TOTAL - 1.0))))))


def frame_at(t: float, animatic: bool) -> Image.Image:
    i = max(k for k, s in enumerate(SHOTS) if s.t0 <= t + 1e-6)
    s = SHOTS[i]
    im = shot_frame(s, t, animatic)
    if i > 0:
        xf = 0.6 if s.t0 in LONG_XFADE else XFADE
        if t - s.t0 < xf:
            prev = shot_frame(SHOTS[i - 1], t, animatic)
            im = Image.blend(prev, im, (t - s.t0) / xf)
    img = im.convert("RGBA")
    if t < 1.0:
        img.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(255 * (1 - t)))))
    title_overlay(img, t)
    era_overlay(img, t)
    if t < T_CARD:
        lyric_overlay(img, t)
    card_overlay(img, t)
    return img.convert("RGB")


def mix_audio(video: Path, out: Path):
    fl = (f"[1:a]atrim=0:{SONG_END:.3f},asetpts=PTS-STARTPTS,aformat=sample_rates=48000:channel_layouts=stereo,"
          f"afade=t=out:st={SONG_END - 2.5:.3f}:d=2.5,apad=whole_dur={T_TOTAL:.3f},loudnorm=I=-14:TP=-1.5:LRA=11,"
          f"atrim=0:{T_TOTAL:.3f}[a]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-i", str(SONG), "-filter_complex", fl,
                    "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)],
                   check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--animatic", action="store_true", help="全部用关键帧静帧（开机前审节奏）")
    ap.add_argument("--preview", action="store_true", help="960x540")
    ap.add_argument("--still", type=float, nargs="*")
    ap.add_argument("--take", nargs="*", default=[], help="JOB=N，例如 N18_Walk=2")
    args = ap.parse_args()
    for kv in args.take:
        k, v = kv.split("=")
        TAKES[k] = int(v)
    missing = [s.job for s in SHOTS if s.job and not clip_path(s.job)]
    if missing and not args.animatic:
        print(f"⚠️  {len(missing)} 个镜头还没有 H3 片段，用关键帧代替：{missing}")
    if args.still:
        d = OUT.parent / "stills"
        d.mkdir(parents=True, exist_ok=True)
        for s in args.still:
            p = d / f"nora_{s:06.1f}.png"
            frame_at(s, args.animatic).save(p)
            print(p)
        return
    tag = "_animatic" if args.animatic else ("_preview" if args.preview else "")
    out = OUT.with_name(OUT.stem + tag + ".mp4")
    out.parent.mkdir(parents=True, exist_ok=True)
    silent = out.with_suffix(".silent.mp4")
    sw, sh = (960, 540) if (args.preview or args.animatic) else (W, H)
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{sw}x{sh}", "-r", str(FPS),
                            "-i", "-", "-c:v", "libx264", "-preset", "veryfast" if sw < W else "slow", "-crf", "23" if sw < W else "17",
                            "-pix_fmt", "yuv420p", str(silent)], stdin=subprocess.PIPE)
    for k in range(int(T_TOTAL * FPS)):
        fr = frame_at(k / FPS, args.animatic)
        if sw != W:
            fr = fr.resize((sw, sh), Image.BILINEAR)
        enc.stdin.write(fr.tobytes())
        if k % (FPS * 30) == 0:
            print(f"  {k / FPS:5.1f}s", flush=True)
    enc.stdin.close()
    enc.wait()
    mix_audio(silent, out)
    silent.unlink()
    print(out)


if __name__ == "__main__":
    main()
