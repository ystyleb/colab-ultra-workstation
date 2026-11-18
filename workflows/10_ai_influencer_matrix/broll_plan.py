#!/usr/bin/env python3
"""Workflow 10「动作开场 + 插入空镜」形式（2026-11-18 起，先在 J03/J04/V06/W04/W10 试点）。

一条成片 = 配音时间轴上的三层：
  [0, hook_cut)          开场动作镜头（H3，无台词，静音参考音锁住嘴不动），钩子句以画外音压在上面
  [hook_cut, cta_cut)    对镜说话（H3，只喂这一段配音，前后各留一点静音）
  inserts[*].at          插入空镜盖在说话段上，台词照常继续：静态图本地缓推（0 CCU），或 H3 短镜头
  [cta_cut, +card_sec)   片尾 CTA 字卡（subtitle_and_finalize.py 负责）

为什么把动作和说话分开出：H3 一边说话一边做手上动作就会闭嘴（W01 倒茶、June 坐站矛盾都踩过），
分开以后每段只做一件事。manifest 里脚本的 "broll" 字段定义这些镜头，时间点都是配音秒数。

本文件给两处用：
- run_influencer_video_remote.py --broll：build_jobs() 生成任务清单 + 要上传的图和音频
- subtitle_and_finalize.py：build_composite() 把各段原始素材拼成一条 768x1344 视频
"""

from __future__ import annotations

import json
import math
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONFIG_PATH = HERE / "influencer_config.json"
MANIFEST_PATH = HERE / "scripts_30_manifest.json"
SAMPLE_DIR = HERE / "sample_inputs"
TTS_DIR = HERE / "work" / "tts"
BROLL_WAV_DIR = TTS_DIR / "broll"
RAW_DIR = HERE / "outputs" / "raw"
CTA_CUTS = TTS_DIR / "cta_cut.json"
FPS = 24.0
W, H = 768, 1344

# 空镜/开场不要 closeup LoRA：它会把镜头往脸部大特写推，空镜里根本没有脸
BROLL_OVERRIDES = {"closeup_strength": 0.0}
OPENER_CAMERA = "The camera pushes in with small amplitude at slow speed."
INSERT_CAMERA = "The camera shakes slightly at slow speed like a steady handheld camera."


def legal_frames(sec: float) -> int:
    """H3 帧数必须是 17k+5，向上取整，最多 362 帧（15.08 秒）。"""
    k = max(1, math.ceil((sec * FPS - 5) / 17))
    frames = 17 * k + 5
    if frames > 362:
        raise ValueError(f"{sec:.2f}s 超过 H3 单段上限 15.08s")
    return frames


def cta_cuts() -> dict:
    return json.loads(CTA_CUTS.read_text(encoding="utf-8")) if CTA_CUTS.exists() else {}


WORDS_DIR = TTS_DIR / "words"


def _norm(w: str) -> str:
    return "".join(ch for ch in w.lower() if ch.isalnum())


def phrase_span(sid: str, phrase: str) -> tuple[float, float]:
    """台词片段在配音里的 (开始, 结束) 秒数：whisper 词时间戳 + difflib 模糊对齐（whisper 会把 TEA 听成 T、twenty 写成 20）。"""
    import difflib

    words = json.loads((WORDS_DIR / f"{sid}.json").read_text(encoding="utf-8"))
    hyp = [_norm(w["word"]) for w in words]
    ref = [t for t in (_norm(x) for x in phrase.split()) if t]
    sm = difflib.SequenceMatcher(a=ref, b=hyp, autojunk=False)
    blocks = [b for b in sm.get_matching_blocks() if b.size]
    if not blocks or sum(b.size for b in blocks) < max(1, len(ref) // 2):
        raise ValueError(f"{sid}: 在配音里对不上台词片段「{phrase}」")
    return words[blocks[0].b]["start"], words[blocks[-1].b + blocks[-1].size - 1]["end"]


def _snap(sid: str, t: float, side: str) -> float:
    """把切点挪进最近的静音段：side='after' 取 t 之后的停顿中点，'before' 取 t 之前的停顿中点（0.4s 内）。"""
    from subtitle_and_finalize import detect_pauses

    best = None
    for s, e in detect_pauses(TTS_DIR / f"{sid}.wav", noise_db=-38, min_sil=0.09):
        mid = (s + e) / 2
        if side == "after" and s >= t - 0.15 and s - t <= 0.4:
            best = mid if best is None else min(best, mid)
        if side == "before" and e <= t + 0.15 and t - e <= 0.4:
            best = mid if best is None else max(best, mid)
    return round(best if best is not None else (t + 0.12 if side == "after" else t - 0.12), 2)


def resolve_times(s: dict) -> dict:
    """broll 的时间点可以写成台词文字（hook_text / inserts[].at_text），换配音或改语速后自动重算成秒。"""
    b = json.loads(json.dumps(s["broll"]))
    if "hook_text" in b:
        b["hook_cut"] = _snap(s["id"], phrase_span(s["id"], b["hook_text"])[1], "after")
    for ins in b.get("inserts", []):
        if "at_text" in ins:
            a, e = phrase_span(s["id"], ins["at_text"])
            ins["at"] = [_snap(s["id"], a, "before"), _snap(s["id"], e, "after")]
    return b


def talk_text(s: dict, b: dict) -> str:
    """说话段台词 = 全文去掉钩子句和结尾 Comment X."""
    import re

    full = re.sub(r"\s*Comment\s+[A-Z]+\.?\s*$", "", s["spoken_en"].strip())
    if "hook_text" in b and full.startswith(b["hook_text"].strip()):
        return full[len(b["hook_text"].strip()):].strip()
    return b["talk"]["text"]


def broll_prompt(persona: dict, scene_cfg: dict, action_en: str, dur_sec: float, person: bool, camera_en: str) -> str:
    """无台词镜头的 H3 提示词。<Audio 1> 是静音参考音，嘴巴靠音频锁住，文字里也写明不说话。"""
    ts_end = f"00:{dur_sec - 0.10:06.3f}"
    look = persona["look_en"]
    if scene_cfg.get("outfit_en"):
        look = f"{look}, wearing {scene_cfg['outfit_en']}"
    subj = (
        f"<Subject 1> is {persona['display_name']} ({look}) from <Picture 1>, "
        "warm natural lifelike human skin tone with realistic fine pores and subtle authentic facial lines.\n"
        if person
        else ""
    )
    keep = (
        "<Subject 1> (appears in [Shot 1]): fully_preserved - Strictly preserve exact facial bone structure, eye color, "
        "hairstyle and outfit from <Picture 1>.\n"
        if person
        else ""
    )
    hush = "Nobody speaks: <Subject 1>'s lips stay gently closed the whole time. " if person else "Nobody speaks. "
    return (
        "subject_definitions:\n"
        f"{subj}"
        "<Audio 1> is a quiet room-tone reference with no speech.\n\n"
        "retention_analysis:\n"
        f"{keep}"
        "Scene (appears in [Shot 1]): fully_preserved - Keep the exact framing, location, props, lighting and color of <Picture 1> "
        f"({scene_cfg['bg_en']}).\n\n"
        "summary:\n"
        "[reference generation + audio reference]\n"
        f"Shot 1 (00:00.000 - {ts_end}): Live-action 35mm cinema vertical 9:16 B-roll shot that starts exactly from the "
        f"composition of <Picture 1>. {action_en} One single continuous shot from start to end, no cuts. {camera_en} {hush}"
        "Only quiet natural room ambiance, no speech, no music. "
        "Clean live-action optical realism, zero subtitles, zero on-screen text, zero watermarks."
    )


def _ffmpeg(args: list[str]) -> None:
    subprocess.run(["ffmpeg", "-y", "-v", "error", *args], check=True)


def make_talk_wav(s: dict, b: dict, cut: float, out: Path) -> float:
    """说话段配音：前面 lead 秒静音 + 配音[hook_cut, cta_cut) + 0.3 秒静音。返回总时长。"""
    lead = b["talk"].get("lead", 0.25)
    src = TTS_DIR / f"{s['id']}.wav"
    a, e = b["hook_cut"], cut
    out.parent.mkdir(parents=True, exist_ok=True)
    _ffmpeg([
        "-i", str(src), "-af",
        f"atrim={a:.3f}:{e:.3f},asetpts=PTS-STARTPTS,afade=t=in:d=0.03,afade=t=out:st={e - a - 0.05:.3f}:d=0.05,"
        f"adelay={int(lead * 1000)}:all=1,apad=pad_dur=0.3",
        "-ac", "1", str(out),
    ])
    return lead + (e - a) + 0.3


def make_silence_wav(out: Path, sec: float) -> None:
    """静音参考音：-60 dB 左右的底噪，避免全零输入让音频编码器出怪值。"""
    out.parent.mkdir(parents=True, exist_ok=True)
    _ffmpeg(["-f", "lavfi", "-i", f"anoisesrc=color=pink:amplitude=0.001:duration={sec:.3f}:sample_rate=24000", "-ac", "1", str(out)])


def _raw_len(job_id: str) -> float:
    r = latest_raw(job_id)
    if not r:
        return 0.0
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(r)], text=True))


def build_jobs(ids: list[str], reuse: bool = True) -> tuple[list[dict], list[Path]]:
    """为带 broll 的脚本生成 H3 任务清单。返回 (jobs, 需要上传的文件)。

    开场/插入镜头是无台词的，和配音无关：reuse=True 时本地已有且够长的原始素材直接复用，不再上云。
    说话段口型跟着配音走，配音一改就必须重出，永远不复用。帧数按配音里实际需要的时长自动取。
    """
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    cuts = cta_cuts()
    from cloud_influencer_h3 import build_h3_prompt

    jobs: list[dict] = []
    files: set[Path] = set()
    for s in manifest["scripts"]:
        if s["id"] not in ids:
            continue
        if "broll" not in s:
            raise ValueError(f"{s['id']} 没有 broll 配置")
        b = resolve_times(s)
        persona = cfg["personas"][s["persona"]]
        scene_cfg = persona["scenes"][s["scene"]]

        # 1) 开场动作镜头
        op = b["opener"]
        need = b["hook_cut"] + op.get("in", 0.5) + 0.2
        if not (reuse and _raw_len(f"{s['id']}open") >= need):
            frames = legal_frames(need + 0.3)
            wav = BROLL_WAV_DIR / f"{s['id']}open.wav"
            make_silence_wav(wav, frames / FPS)
            jobs.append({
                "job_id": f"{s['id']}open", "kind": "opener", "persona": s["persona"], "image": op["image"], "audio": wav.name,
                "frames": frames, "h3_overrides": BROLL_OVERRIDES,
                "prompt": broll_prompt(persona, scene_cfg, op["action_en"], frames / FPS, True, OPENER_CAMERA),
            })
            files |= {SAMPLE_DIR / op["image"], wav}

        # 2) 对镜说话段
        cut = cuts[s["id"]]["cut"]
        wav = BROLL_WAV_DIR / f"{s['id']}talk.wav"
        dur = make_talk_wav(s, b, cut, wav)
        frames = legal_frames(dur)
        item = {"id": f"{s['id']}talk", "persona": s["persona"], "camera_action_en": b["talk"]["action_en"], "spoken_en": talk_text(s, b)}
        jobs.append({
            "job_id": item["id"], "kind": "talk", "persona": s["persona"], "image": scene_cfg["image"], "audio": wav.name,
            "frames": frames, "prompt": build_h3_prompt(persona, scene_cfg, item, frames / FPS),
        })
        files |= {SAMPLE_DIR / scene_cfg["image"], wav}

        # 3) 需要 H3 的插入空镜（静态图插入不上云）
        for k, ins in enumerate(b.get("inserts", [])):
            if "action_en" not in ins:
                continue
            need = ins["at"][1] - ins["at"][0] + ins.get("in", 0.6) + 0.1
            if reuse and _raw_len(f"{s['id']}ins{k}") >= need:
                continue
            frames = legal_frames(need + 0.3)
            wav = BROLL_WAV_DIR / f"{s['id']}ins{k}.wav"
            make_silence_wav(wav, frames / FPS)
            jobs.append({
                "job_id": f"{s['id']}ins{k}", "kind": "insert", "persona": s["persona"], "image": ins["image"], "audio": wav.name,
                "frames": frames, "h3_overrides": BROLL_OVERRIDES,
                "prompt": broll_prompt(persona, scene_cfg, ins["action_en"], frames / FPS, ins.get("person", False), INSERT_CAMERA),
            })
            files |= {SAMPLE_DIR / ins["image"], wav}
    return jobs, sorted(files)


def latest_raw(job_id: str) -> Path | None:
    cands = sorted(RAW_DIR.glob(f"AIInf_{job_id}_*.mp4"), key=lambda p: p.stat().st_mtime)
    return cands[-1] if cands else None


def _zoom_crop(z: str, anchor_y: float = 0.5) -> str:
    """按 z(t) 放大后裁回 768x1344；z 是 ffmpeg 表达式，t 为该段自己的时间。"""
    return (f"scale=w='trunc({W}*({z})/2)*2':h='trunc({H}*({z})/2)*2':eval=frame:flags=lanczos,"
            f"crop={W}:{H}:(iw-{W})/2:(ih-{H})*{anchor_y}")


def build_composite(s: dict, out: Path, total: float) -> Path:
    """按配音时间轴拼出 768x1344 素材：开场 -> 说话段（插入后景别略近）-> 插入空镜盖在上面。无音轨。"""
    b = resolve_times(s)
    opener, talk = latest_raw(f"{s['id']}open"), latest_raw(f"{s['id']}talk")
    if not opener or not talk:
        raise FileNotFoundError(f"{s['id']}: 缺开场或说话段原始素材（outputs/raw/AIInf_{s['id']}open_* / talk_*）")
    c1 = b["hook_cut"]
    o_in = b["opener"].get("in", 0.5)
    lead = b["talk"].get("lead", 0.25)
    inserts = b.get("inserts", [])
    after = b.get("after_insert_zoom", 1.0)
    ins_end = max((i["at"][1] for i in inserts), default=None)

    cmd = ["-i", str(opener), "-i", str(talk)]
    # 说话段：插入镜头之后切近一档（剪辑式景别变化），时间换算到这一段自己的 t
    z_talk = f"if(gte(t,{ins_end - c1:.3f}),{after},1.0)" if (ins_end and after != 1.0) else "1.0"
    fc = [
        f"[0:v]trim=start={o_in:.3f},setpts=PTS-STARTPTS,fps={FPS},tpad=stop_mode=clone:stop_duration=3,trim=duration={c1:.3f},scale={W}:{H},setsar=1[A]",
        f"[1:v]trim=start={lead:.3f},setpts=PTS-STARTPTS,fps={FPS},tpad=stop_mode=clone:stop_duration=4,"
        f"trim=duration={total - c1:.3f},{_zoom_crop(z_talk, 0.32)},setsar=1[B]",
        "[A][B]concat=n=2:v=1:a=0[base]",
    ]
    prev, idx = "base", 2
    for k, ins in enumerate(inserts):
        a, e = ins["at"]
        d = e - a
        if "action_en" in ins:  # H3 插入镜头
            src = latest_raw(f"{s['id']}ins{k}")
            if not src:
                raise FileNotFoundError(f"{s['id']}: 缺插入镜头素材 AIInf_{s['id']}ins{k}_*")
            cmd += ["-i", str(src)]
            chain = f"[{idx}:v]trim=start={ins.get('in', 0.6):.3f}:duration={d:.3f},setpts=PTS-STARTPTS,fps={FPS},scale={W}:{H}"
        else:  # 静态图缓推，0 CCU
            z0, z1 = ins.get("zoom", [1.0, 1.08])
            cmd += ["-loop", "1", "-framerate", str(FPS), "-t", f"{d:.3f}", "-i", str(SAMPLE_DIR / ins["still"])]
            chain = f"[{idx}:v]scale={W}:{H},{_zoom_crop(f'{z0}+({z1 - z0})*t/{d:.3f}', 0.5)}"
        fc.append(f"{chain},setsar=1,setpts=PTS+{a:.3f}/TB[i{k}]")
        fc.append(f"[{prev}][i{k}]overlay=0:0:eof_action=pass:enable='between(t,{a:.3f},{e:.3f})'[o{k}]")
        prev, idx = f"o{k}", idx + 1

    out.parent.mkdir(parents=True, exist_ok=True)
    _ffmpeg([*cmd, "-filter_complex", ";".join(fc), "-map", f"[{prev}]", "-t", f"{total:.3f}",
             "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-pix_fmt", "yuv420p", str(out)])
    return out


def composite_tmp(s: dict, total: float) -> Path:
    d = Path(tempfile.mkdtemp(prefix=f"wf10_comp_{s['id']}_", dir="/tmp"))
    return build_composite(s, d / f"{s['id']}_composite.mp4", total)
