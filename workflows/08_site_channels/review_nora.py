#!/usr/bin/env python3
"""《Nora》开机前审核页：人物三视图、环境图、逐镜头分镜（首尾帧 + 歌词 + H3 任务）、关键帧来源审计、样片。

数据全部从 keyframes.json / jobs.json / nora_film.py 读取，不手抄；改了分镜重跑本脚本即可。
python3 workflows/08_site_channels/review_nora.py
→ out/review/songifted_nora/index.html（浏览器直接打开；缩略图在 img/，点开看原图）
"""
from __future__ import annotations

import html
import json
import os
from pathlib import Path

from PIL import Image

import nora_film as nf

HERE = Path(__file__).resolve().parent
NS = HERE / "samples" / "songifted_nora"
OUT = HERE / "out" / "review" / "songifted_nora"
IMG = OUT / "img"
ANIMATIC = HERE / "out" / "promo" / "songifted" / "Songifted_Story_Nora_1920x1080_animatic.mp4"
H3_FPS = 24
CCU_PER_GPU_MIN = 10.05 / 60

KF = json.loads((NS / "keyframes.json").read_text())
JOBS = json.loads((NS / "jobs.json").read_text())
FRAMES = {f["name"]: f for f in KF["frames"]}

# 没有 edit_of 底图的帧，时代靠名字判断
ERA_OF_ROOT = {"env_kitchen": "现在 · 厨房", "env_kitchen_wide": "现在 · 厨房", "env_apt": "十二年前 · 第一间公寓",
               "env_hosp": "五年前 · 最难的那一年", "env_moving": "这些年 · 搬家"}
ERA_EXTRA = {"n08_wedding": "十二年前 · 婚礼", "n15_drive": "五年前 · 最难的那一年", "n21_roadside": "这些年 · 路边抛锚",
             "n28_exterior": "现在 · 屋外"}
ERA_COLOR = {"现在": "#d98b5f", "十二年前": "#7ea6c9", "五年前": "#9b8fc4", "这些年": "#88b07f"}


def e(s) -> str:
    return html.escape(str(s))


def rel(p: Path) -> str:
    return os.path.relpath(p, OUT)


def thumb(name: str) -> str:
    """960 宽 JPEG 缩略图，返回相对路径。"""
    src = NS / "kf" / f"{name}_1344x768.png"
    dst = IMG / f"{name}.jpg"
    if not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime:
        im = Image.open(src).convert("RGB")
        im.thumbnail((960, 960), Image.LANCZOS)
        im.save(dst, quality=86)
    return rel(dst)


def full(name: str) -> str:
    return rel(NS / "kf" / f"{name}_1344x768.png")


def root_of(name: str) -> str:
    seen = name
    while FRAMES.get(seen, {}).get("edit_of"):
        seen = FRAMES[seen]["edit_of"]
    return seen


def era_of(name: str) -> str:
    return ERA_EXTRA.get(name) or ERA_OF_ROOT.get(root_of(name), "—")


def source_audit(name: str) -> tuple[str, str]:
    """(等级, 说明)。等级：ok / warn / bad。"""
    f = FRAMES[name]
    base = f.get("edit_of")
    refs = [Path(r).stem.removesuffix("_raw") for r in f.get("refs", [])]
    turn = [r for r in refs if r.startswith("ref_")]
    other = [r for r in refs if not r.startswith(("ref_", "env_"))]
    parts = []
    if base:
        parts.append(f"底图 <b>{e(base)}</b>")
    if turn:
        parts.append("三视图 " + "、".join(e(r) for r in turn))
    if other:
        parts.append("另参考 " + "、".join(e(r) for r in other) + "（衣着/站位）")
    desc = " ＋ ".join(parts) or "纯文生图"
    if base and not base.startswith("env_"):
        return "bad", f"{desc}<br>从其他镜头派生，<b>未按流程</b>（应改为 edit_of 环境图）"
    if not base:
        if not turn and "NO people" in f["prompt"]:
            return "warn", f"{desc}<br>无人空镜插入，没有环境图"
        if not turn:
            return "bad", f"{desc}<br>没有环境图，也没有三视图参考"
        return "warn", f"{desc}<br>单次出现的场景，没有环境图"
    return "ok", desc


def badge(level: str) -> str:
    return {"src0": "", "ok": '<span class="b ok">按流程</span>', "warn": '<span class="b warn">无环境图</span>',
            "bad": '<span class="b bad">链式派生</span>'}[level]


def era_tag(era: str) -> str:
    c = ERA_COLOR.get(era.split(" · ")[0], "#999")
    return f'<span class="era" style="--c:{c}">{e(era)}</span>'


def ver(name: str) -> str:
    return str(int((NS / "kf" / f"{name}_1344x768.png").stat().st_mtime))


def card(name: str, cap: str = "", show_prompt: bool = True, ctx: str = "") -> str:
    f = FRAMES[name]
    if name.startswith(("ref_", "env_")):  # 源头图不套镜头审计，只写参考了什么
        refs = [Path(r).stem.removesuffix("_raw") for r in f.get("refs", [])]
        lvl, desc = "src0", ("参考 " + "、".join(e(r) for r in refs) if refs else "文生图（源头）")
    else:
        lvl, desc = source_audit(name)
    pr = f'<details><summary>提示词</summary><p class="prompt">{e(f["prompt"])}</p></details>' if show_prompt else ""
    # 评审后重做过的帧：附最近一次备份（kf_vN = 第 N 轮评审前的版本）
    olds = sorted(NS.glob(f"kf_v*/{name}_1344x768.png"), key=lambda p: int(p.parent.name[4:]))
    if olds:
        old = olds[-1]
        pr += (f'<details class="prev"><summary>看上一版（第 {old.parent.name[4:]} 轮评审前）</summary>'
               f'<a href="{rel(old)}" target="_blank"><img loading="lazy" src="{rel(old)}" style="width:100%;opacity:.85"></a></details>')
    v = ver(name)
    label = f"{ctx} {name}".strip()
    return (f'<figure class="kf" data-target="kf:{name}" data-label="{e(label)}" data-img="{full(name)}?v={v}" data-ver="{v}">'
            f'<a href="{full(name)}" target="_blank"><img loading="lazy" src="{thumb(name)}?v={v}"></a>'
            f'<figcaption><code>{e(name)}</code> {cap}</figcaption>'
            f'<div class="src {lvl}">{badge(lvl)} {desc}</div>{pr}</figure>')


def stills() -> list[tuple[str, str]]:
    out = []
    for t, cap in [(5.0, "片头标题（5.0 s）"), (20.5, "时代字卡 + 歌词字幕（20.5 s）"), (192.0, "片尾字卡（192 s）")]:
        dst = IMG / f"still_{t:05.1f}.jpg"
        im = nf.frame_at(t, True)
        im.thumbnail((960, 960), Image.LANCZOS)
        im.save(dst, quality=86)
        out.append((rel(dst), cap, t))
    return out


def shot_rows() -> str:
    rows = []
    jobs = JOBS["jobs"]
    for i, s in enumerate(nf.SHOTS, 1):
        dur = s.t1 - s.t0
        lyr = [("…" if t0 < s.t0 - 0.05 else "") + ln for t0, t1, ln in nf.LYRICS if t0 < s.t1 and t1 > s.t0 + 0.05]
        era_lbl = [txt for t0, _, txt in nf.ERAS if abs(t0 - s.t0) < 0.05]
        cap1 = "首帧" if s.last else ("静帧" if not s.job else "首帧 = 尾帧")
        imgs = card(s.first, cap1, ctx=f"#{i:02d} {cap1}")
        if s.last:
            imgs += card(s.last, "尾帧", ctx=f"#{i:02d} 尾帧")
        js = [j for j in jobs if s.job and j["id"].startswith(s.job + "_T")]
        if js:
            need = dur + (0.6 if any(abs(x - s.t1) < 0.05 for x in nf.LONG_XFADE) else nf.XFADE) + s.src_in
            have = js[0]["length"] / H3_FPS / s.speed
            warn = "" if have >= need else f' <span class="b bad">片段比镜头短 {need - have:.1f}s</span>'
            seeds = "、".join(f'{j["id"][-2:]} seed {j["seed"]}' for j in js)
            tk = nf.TAKES.get(s.job)
            pick = next((j for j in js if tk and j["id"] == f"{s.job}_T{tk}"), js[0])
            sheet = HERE / "out" / "samples" / "songifted_nora" / "sheets" / f"{pick['id']}.jpg"
            mode = "只锁首帧" if pick.get("first_only") else "首尾帧"
            extra = (f'，合成时慢放 {s.speed}×（避开片尾硬切）' if s.speed < 1 else '') + (f'，从 {s.src_in:.1f}s 起循环播放（{s.loop:.0f}s 交叉淡化）' if s.loop else '')
            h3 = (f'<div class="h3"><b>H3 选用 {e(pick["id"])}</b>（{mode}，{pick["length"]} 帧 ≈ {pick["length"] / H3_FPS:.1f}s{extra}）'
                  f' · 共渲 {len(js)} 条：{e(seeds)}'
                  + (f'<details><summary>选用片段联系表（每 0.5 秒一格）</summary><a href="{rel(sheet)}" target="_blank"><img loading="lazy" src="{rel(sheet)}" style="width:100%"></a></details>' if sheet.exists() else '')
                  + f'<details><summary>H3 提示词</summary><p class="prompt">{e(pick["prompt"])}</p></details></div>')
        else:
            h3 = '<div class="h3"><b>不走 H3</b>：静帧 + 慢推（合成时做）</div>'
        motion = "首尾帧不同（有走位/状态变化）" if s.last else "首尾同帧（原地动作）"
        if s.zoom[1] < 1:
            motion += " · 合成时慢慢拉远"
        rows.append(f"""
<section class="shot" id="s{i}" data-target="shot:{i:02d}" data-label="#{i:02d} 镜头（节奏/歌词/H3）">
  <div class="meta">
    <div class="num">#{i:02d}</div>
    <div class="time">{s.t0:.1f} – {s.t1:.1f} s<br><small>{dur:.1f} 秒</small></div>
    {era_tag(era_of(s.first))}
    {''.join(f'<div class="eralbl">字卡「{e(x)}」</div>' for x in era_lbl)}
    <div class="lyr">{''.join(f'<p>“{e(x)}”</p>' for x in lyr) or '<p class="dim">（前奏/间奏，无歌词）</p>'}</div>
    <div class="dim small">{e(motion)}</div>
  </div>
  <div class="frames">{imgs}</div>
  {h3}
</section>""")
    return "".join(rows)


def main():
    IMG.mkdir(parents=True, exist_ok=True)
    refs = [n for n in FRAMES if n.startswith("ref_")]
    envs = [n for n in FRAMES if n.startswith("env_")]
    shots_kf = [n for n in FRAMES if n.startswith("n")]
    audit = {n: source_audit(n)[0] for n in shots_kf}
    n_ok, n_warn, n_bad = (sum(v == k for v in audit.values()) for k in ("ok", "warn", "bad"))
    bad_list = "、".join(f'<code>{n}</code>←{FRAMES[n].get("edit_of") or "无"}' for n, v in audit.items() if v == "bad")
    warn_list = "、".join(f"<code>{n}</code>" for n, v in audit.items() if v == "warn")
    jobs = JOBS["jobs"]
    gpu_min = sum(j["length"] for j in jobs) / 141 * (101 / 28)  # batch 4 实测：28 条 141 帧共 101 G4 分钟（含开机加载）
    used_jobs = {j["id"].rsplit("_T", 1)[0] for j in jobs}
    short = []
    for i, s_ in enumerate(nf.SHOTS, 1):
        js = [j for j in jobs if s_.job and j["id"].startswith(s_.job + "_T")]
        if js:
            xf = 0.6 if any(abs(x - s_.t1) < 0.05 for x in nf.LONG_XFADE) else nf.XFADE
            gap = s_.t1 - s_.t0 + xf + s_.src_in - js[0]["length"] / H3_FPS / s_.speed
            if gap > 0:
                short.append((i, s_.job, gap))
    short_big = "、".join(f"#{i:02d} {j}（差 {g:.1f}s）" for i, j, g in short if g > 1) or "无"

    lyr_rows = "".join(f'<div class="lyrrow" data-target="lyric:{k:02d}" data-label="歌词 {t0:.1f}s「{e(ln[:40])}」"><span>{t0:.1f}</span><span>{t1:.1f}</span><span>{e(ln)}</span></div>'
                       for k, (t0, t1, ln) in enumerate(nf.LYRICS, 1))
    still_html = "".join(f'<figure class="kf" data-target="still:{t:05.1f}" data-label="{e(c)}" data-img="{p}"><a href="{p}" target="_blank"><img src="{p}"></a><figcaption>{e(c)}</figcaption></figure>'
                         for p, c, t in stills())
    poster = rel(IMG / "still_005.0.jpg")
    if nf.OUT.exists():  # H3 成片
        video = (f'<div data-target="video:final" data-label="成片（带时间点）"><video controls preload="metadata" poster="{poster}" src="{rel(nf.OUT)}?v={int(nf.OUT.stat().st_mtime)}"></video>'
                 f'<p class="dim small">{e(nf.OUT.name)}（27 个镜头全部是 H3 动态片段）· 对照用：<a href="{rel(ANIMATIC)}" target="_blank">关键帧样片</a></p></div>')
    else:
        video = (f'<div data-target="video:animatic" data-label="样片（带时间点）"><video controls preload="metadata" poster="{poster}" src="{rel(ANIMATIC)}"></video>'
                 f'<p class="dim small">{e(ANIMATIC.name)}（全部用关键帧静帧，0 CCU；开机后换成 H3 动态片段）</p></div>'
                 if ANIMATIC.exists() else '<p class="b bad">样片还没渲染：python3 nora_film.py --animatic</p>')

    REVIEW_CSS = (HERE / "review_kit" / "ui.css").read_text()
    REVIEW_JS = (HERE / "review_kit" / "ui.js").read_text()
    page = f"""<!doctype html><html lang="zh"><head><meta charset="utf-8"><title>《Nora》审核页</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
:root{{--bg:#16130f;--card:#211c17;--line:#3a3129;--fg:#f1e8de;--dim:#a8998a;--coral:#ff6f5e}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.6 -apple-system,"PingFang SC",sans-serif}}
header{{padding:36px 48px 20px;border-bottom:1px solid var(--line)}}h1{{margin:0;font:600 40px/1.2 Georgia,serif}}
nav{{position:sticky;top:0;z-index:5;background:#16130fee;backdrop-filter:blur(6px);padding:10px 48px;border-bottom:1px solid var(--line);display:flex;gap:18px;flex-wrap:wrap}}
nav a{{color:var(--dim);text-decoration:none}}nav a:hover{{color:var(--fg)}}
main{{padding:0 48px 80px;max-width:1600px}}h2{{margin:48px 0 12px;font:600 26px Georgia,serif}}
.dim{{color:var(--dim)}}.small{{font-size:13px}}code{{background:#2c251e;padding:1px 5px;border-radius:4px;font-size:13px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(420px,1fr));gap:18px}}
.kf{{margin:0;background:var(--card);border:1px solid var(--line);border-radius:10px;overflow:hidden}}
.kf img{{width:100%;display:block;aspect-ratio:1344/768;object-fit:cover;background:#000}}
.kf figcaption{{padding:8px 12px 0}}.kf .src{{padding:4px 12px 8px;font-size:13px;color:var(--dim)}}
.kf details{{padding:0 12px 10px;font-size:13px}}summary{{cursor:pointer;color:var(--dim)}}.prompt{{white-space:pre-wrap;margin:6px 0 0;color:#d8cbbd}}
.b{{display:inline-block;padding:0 7px;border-radius:9px;font-size:12px;font-weight:600}}
.b.ok{{background:#2f4a2c;color:#bfe3b4}}.b.warn{{background:#4d4020;color:#f0d68c}}.b.bad{{background:#5a2522;color:#ffb4ab}}
.src.bad{{color:#ffb4ab}}
.shot{{display:grid;grid-template-columns:230px 1fr;gap:18px;padding:22px 0;border-bottom:1px solid var(--line)}}
.shot .frames{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}}
.shot .h3{{grid-column:2;font-size:13px;color:var(--dim)}}.shot .h3 b{{color:var(--fg)}}
.num{{font:600 28px Georgia,serif;color:var(--coral)}}.time{{font-variant-numeric:tabular-nums;margin:2px 0 8px}}
.era{{display:inline-block;border-left:4px solid var(--c);padding:0 8px;background:#2a231c;border-radius:3px;font-size:13px}}
.eralbl{{margin-top:6px;font-size:13px;color:#f0d68c}}.lyr p{{margin:8px 0 0;font-family:Georgia,serif;font-style:italic}}
.box{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px 20px;margin:12px 0}}
.box.todo{{border-color:var(--coral)}}table{{border-collapse:collapse;font-size:14px}}td,th{{padding:3px 12px;border-bottom:1px solid var(--line);text-align:left}}
video{{width:100%;max-width:1280px;border-radius:10px;background:#000}}
.strip{{display:flex;height:22px;border-radius:5px;overflow:hidden;margin:8px 0 4px}}.strip a{{display:block;height:100%;border-right:1px solid var(--bg)}}
.lyrtab{{max-width:1100px}}.lyrrow{{display:grid;grid-template-columns:60px 60px 1fr auto;align-items:center;border-bottom:1px solid var(--line);padding:3px 0}}
.lyrrow.head{{color:var(--dim);font-size:13px}}.lyrrow>.rv-bar{{padding:0 0 0 8px}}.lyrrow>.rv-thread{{grid-column:1/-1}}
{REVIEW_CSS}
</style></head><body data-project="songifted_nora">
<header>
<h1>Nora</h1>
<p class="dim">Songifted 横屏故事片 · 1920×1080 · {nf.T_TOTAL:.0f} 秒 · 配乐 <code>/demos/for-wife.mp3</code> 整首（虚构的 Nora，3:10）· 产品只在片尾出现</p>
<p>{e(KF["note"])}</p>
</header>
<nav><a href="#todo">待你确认</a><a href="#film">样片</a><a href="#cast">人物</a><a href="#env">环境图</a><a href="#audit">来源审计</a><a href="#board">分镜</a><a href="#lyrics">歌词字幕</a><a href="#card">字卡</a><a href="#render">渲染计划</a></nav>
<main>

<h2 id="todo">待你确认（第 2 轮后状态）</h2>
<div class="box todo"><ol>
<li data-target="todo:1" data-label="待确认 1：「最难的那一年」拍成他生病住"><b>「最难的那一年」拍成他生病住院</b>（镜头 #14–#17）：✅ 第 2 轮评审通过时一并确认，按这个方向出片。</li>
<li data-target="todo:2" data-label="待确认 2：歌词字幕"><b>歌词字幕</b>是 whisper 听写再对照首页校的。H3 出片后成片会换成动态画面，到时请在「歌词字幕」那节对着成片再听一遍，特别是 “laughed at nothing” 和 “Everyone remembers wedding photographs”。</li>
<li data-target="todo:3" data-label="待确认 3：关键帧来源"><b>关键帧来源</b>：{n_ok} 张按流程，{n_warn} 张没有环境图，{n_bad} 张是从别的镜头派生的（见「来源审计」）。✅ 第 2 轮你说图片评审通过，这些帧不再重做。</li>
<li data-target="todo:4" data-label="待确认 4：H3 片段长度"><b>H3 片段长度</b>：✅ 已处理。不够长的镜头都加了一档 length；#28 屋外渲 362 帧（15.1 秒），合成时慢放 0.74×，帧间混合补帧，到约 20 秒。{"现在没有镜头比片段长。" if not short else f"仍有 {len(short)} 个镜头偏短：{short_big}。"}</li>
<li data-target="todo:5" data-label="待确认 5：开机渲染"><b>H3 出片</b>：✅ 已完成，三轮共渲出 63 条，用了 <b>56.5 CCU</b>。第一轮有一半不能用：首尾同图的镜头，H3 会自己推成特写再拉回或者硬切回来；另外独角特写里提到画外的人，H3 会自己编一个出来。这些镜头第二轮改成「只锁首帧」重渲，提示词也只写画面里有的东西。每个镜头选哪条、为什么，见下面分镜表里的「H3 选用」，可以展开联系表看。<b>请看上面的成片，有问题直接在视频或分镜上评论。</b></li>
</ol></div>

<h2 id="film">样片</h2>
{video}
<div class="strip">{''.join(f'<a href="#s{i}" title="#{i:02d} {s.t0:.1f}s {e(era_of(s.first))}" style="flex:{s.t1 - s.t0};background:{ERA_COLOR.get(era_of(s.first).split(" · ")[0], "#999")}"></a>' for i, s in enumerate(nf.SHOTS, 1))}</div>
<p class="dim small">时间轴色条：{''.join(f'<span class="era" style="--c:{c}">{k}</span> ' for k, c in ERA_COLOR.items())}点色块跳到对应镜头</p>

<h2 id="cast">人物三视图</h2>
<p class="dim">正面 / 90° 侧面 / 背面，中性站姿，双手空着，不带道具。所有出现人物的帧都以这 4 张作参考。</p>
<div class="grid">{''.join(card(n) for n in refs)}</div>

<h2 id="env">环境图（空景，没有人）</h2>
<div class="grid">{''.join(card(n, era_tag(ERA_OF_ROOT.get(n, ""))) for n in envs)}</div>

<h2 id="audit">关键帧来源审计</h2>
<div class="box">
<p><span class="b ok">按流程</span> {n_ok} 张：底图是环境图，加三视图参考。</p>
<p><span class="b warn">无环境图</span> {n_warn} 张：{warn_list}。车内、婚礼照片、路边、屋外这些场景只出现一次，没有另做环境图。</p>
<p><span class="b bad">链式派生</span> {n_bad} 张：{bad_list}</p>
<p class="dim small">流程：人物三视图 → 空环境图 → 每张首帧和尾帧都 edit_of 环境图，加三视图参考；只有在要求「同一身衣服」或「站在完全相同的位置」时，才把另一帧放进参考图。</p>
</div>

<h2 id="board">分镜（{len(nf.SHOTS)} 个镜头，切点卡在歌词换句上）</h2>
<p class="dim small">点图看 1344×768 原图。H3 片段长度按 {H3_FPS} fps 计算，并检查是否够镜头时长加交叉淡化再加入点。</p>
{shot_rows()}

<h2 id="lyrics">歌词字幕</h2>
<div class="lyrtab"><div class="lyrrow head"><span>起 s</span><span>止 s</span><span>字幕</span></div>{lyr_rows}</div>
<p class="dim small">时代字卡：{"；".join(f"{t0:.1f}s「{e(x)}」" for t0, _, x in nf.ERAS)}</p>

<h2 id="card">片头、字幕、片尾</h2>
<div class="grid">{still_html}</div>
<div class="box small" data-target="endcard" data-label="片尾文案"><p>片尾文案（OFFER 照抄 brand.json）：<br>“He made her a song with her name in it.” · songifted.com<br>{e(nf.OFFER)}<br>{e(nf.CREDIT)}</p>
<p class="dim">画面上没有 AI 角标。披露走两处：YouTube 的「Altered or synthetic content = Yes」设置，以及片尾这行 credit。</p></div>

<h2 id="render">渲染计划</h2>
<div class="box small" data-target="render" data-label="渲染计划">
<p>H3 FL2VA · {JOBS["width"]}×{JOBS["height"]} · {JOBS["steps"]} 步 · {e(JOBS["style_mode"])} · realism LoRA {JOBS["realism_lora_strength"]} · 原声全部静音</p>
<p>{len(jobs)} 条任务，覆盖 {len(used_jobs)} 个镜头；有走位或变化的镜头跑 2 个 seed 挑一个。#08 婚礼照片不走 H3。</p>
<p>估算：约 {gpu_min:.0f} GPU 分钟 ≈ {gpu_min * CCU_PER_GPU_MIN:.0f} CCU（按 batch 4 实测速率折算，已含开机加载；G4 每小时 10.05 CCU）。计费用 colab_meter 包裹（会话 sitech-g4）。</p>
</div>
</main><script>{REVIEW_JS}</script></body></html>"""
    (OUT / "index.html").write_text(page)
    print(OUT / "index.html", f"ok={n_ok} warn={n_warn} bad={n_bad}")


if __name__ == "__main__":
    main()
