#!/usr/bin/env python3
"""去「数字感」画风对比（2026-11-18）：同一段配音、同一个种子，只换画风。

A = 现有说话段（不重出）
B = 原参考图 + People 写实 LoRA 触发词 r34l1sm + 哑光皮肤描述 + 关掉 closeup LoRA
C = B + 纪录片访谈参考图（keyframes_look.json：侧窗光、人物偏一侧、视线看镜头旁的采访者）

用法：python3 look_test.py  -> work/look_test_jobs.json
     python3 run_influencer_video_remote.py --ids V06,W10 --jobs-file work/look_test_jobs.json --session inf-h3-g4-look
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from broll_plan import BROLL_WAV_DIR, FPS, LOOK, SAMPLE_DIR, legal_frames
from cloud_influencer_h3 import build_h3_prompt

HERE = Path(__file__).resolve().parent

LOOK_B = LOOK  # 用户选了 B，已成为 broll_plan 的正式画风
LOOK_C = {
    **LOOK_B,
    "shot_en": "documentary interview shot on <Subject 1>, chest-up medium close-up through a 50mm lens, <Subject 1> placed off-center exactly as in <Picture 1>, soft side window light.",
    "speak_en": "Looking just off-camera at an interviewer sitting beside the lens, never into the lens, <Subject 1> speaks in a clear, grounded tone",
}
OVERRIDES = {"closeup_strength": 0.0}

TESTS = [  # (片号, 原种子 = A 版说话段的种子, C 版参考图, C 版动作)
    ("V06", 2026111921, "ref_vivian_flowers_doc_768x1344.png",
     "Vivian stands among the flowers, hands low and out of frame, talking to the interviewer just off-camera with small natural nods and a warm, knowing half-smile."),
    ("W10", 2026111925, "ref_wen_counter_doc_768x1344.png",
     "Wen stands behind his tea counter, hands low and out of frame, talking to the interviewer just off-camera with small natural nods and a quiet, knowing look."),
]


def main() -> None:
    cfg = json.loads((HERE / "influencer_config.json").read_text(encoding="utf-8"))
    manifest = {s["id"]: s for s in json.loads((HERE / "scripts_30_manifest.json").read_text(encoding="utf-8"))["scripts"]}
    from broll_plan import resolve_times, talk_text

    jobs, files = [], set()
    for sid, seed, doc_img, doc_action in TESTS:
        s = manifest[sid]
        persona = cfg["personas"][s["persona"]]
        scene_cfg = persona["scenes"][s["scene"]]
        b = resolve_times(s)
        wav = BROLL_WAV_DIR / f"{sid}talk.wav"  # 和 A 版同一段配音
        frames = legal_frames(float(__import__("subprocess").check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(wav)], text=True)))
        text = talk_text(s, b)
        for tag, img, action, look in (("B", scene_cfg["image"], b["talk"]["action_en"], LOOK_B), ("C", doc_img, doc_action, LOOK_C)):
            job_id = f"{sid}talk{tag}"
            item = {"id": job_id, "persona": s["persona"], "camera_action_en": action, "spoken_en": text}
            jobs.append({"job_id": job_id, "kind": "talk", "persona": s["persona"], "image": img, "audio": wav.name,
                         "frames": frames, "seed": seed, "h3_overrides": OVERRIDES,
                         "prompt": build_h3_prompt(persona, scene_cfg, item, frames / FPS, look)})
            files |= {SAMPLE_DIR / img, wav}
            shutil.copy2(wav, BROLL_WAV_DIR / f"{job_id}.wav")  # lip_qa.py 按片号找配音
    out = HERE / "work" / "look_test_jobs.json"
    out.write_text(json.dumps({"jobs": jobs, "files": [str(f) for f in sorted(files)]}, ensure_ascii=False, indent=1), encoding="utf-8")
    for j in jobs:
        print(j["job_id"], j["frames"], j["seed"], j["image"])
    print("\n示例 C 提示词:\n" + jobs[-1]["prompt"])


def finalize_variants() -> None:
    """每条出 A/B/C 三版完整成片 + 一条三版并排对比（outputs/look_test/）。"""
    import subprocess
    import sys

    import broll_plan
    import subtitle_and_finalize as sf

    cfg = json.loads((HERE / "influencer_config.json").read_text(encoding="utf-8"))
    manifest = {s["id"]: s for s in json.loads((HERE / "scripts_30_manifest.json").read_text(encoding="utf-8"))["scripts"]}
    cuts = broll_plan.cta_cuts()
    out_dir = HERE / "outputs" / "look_test"
    out_dir.mkdir(parents=True, exist_ok=True)
    film = cfg["finalize"]["film"]["filter"]
    orig_latest = broll_plan.latest_raw
    for sid, seed, _, _ in TESTS:
        s = manifest[sid]
        cc = cuts[sid]
        cta = {"cut": cc["cut"], "speech_end": (cc.get("pause") or [cc["speech_end"]])[0], "card_sec": 1.8, "hold": 0.9, "fade": 0.35, **cfg["personas"][s["persona"]]["cta"]}
        if s.get("end_card") == "question":
            cta["question"] = s["question_en"]
        bgm = {"path": HERE / "bgm" / cfg["finalize"]["bgm"]["tracks"][s["persona"]], "gain_db": cfg["finalize"]["bgm"].get("gain_db", -20)}
        outs = []
        for tag in ("A", "B", "C"):
            talk_raw = sorted((HERE / "outputs" / "raw").glob(f"AIInf_{sid}talk{'' if tag == 'A' else tag}_seed{seed}_*-audio.mp4"))
            if not talk_raw:
                print(f"⏭️ {sid} {tag}: 没有素材", flush=True)
                continue
            broll_plan.latest_raw = lambda job, _t=talk_raw[-1], _s=sid: _t if job == f"{_s}talk" else orig_latest(job)
            comp = broll_plan.composite_tmp(s, sf.card_at(cta) + cta["card_sec"])
            dst = out_dir / f"{sid}_{tag}.mp4"
            sf.finalize_clip(comp, dst, s["spoken_en"], s["hook_banner"], ext_wav=HERE / "work" / "tts" / f"{sid}.wav",
                             cta=cta, bgm=bgm, film=None if tag == "A" else film)
            outs.append((tag, dst))
            print(f"✅ {dst.name}", flush=True)
        broll_plan.latest_raw = orig_latest
        if len(outs) == 3:  # 三版并排，标签写在顶部
            cmd = ["ffmpeg", "-y", "-v", "error"]
            for _, f in outs:
                cmd += ["-i", str(f)]
            labels = {"A": "A now", "B": "B realism fix", "C": "C documentary"}
            fc = ";".join(f"[{k}:v]scale=540:960,drawtext=fontfile=/System/Library/Fonts/Helvetica.ttc:text='{labels[t]}':x=20:y=20:fontsize=34:fontcolor=white:box=1:boxcolor=black@0.6[p{k}]"
                          for k, (t, _) in enumerate(outs))
            fc += ";[p0][p1][p2]hstack=3[v]"
            subprocess.run(cmd + ["-filter_complex", fc, "-map", "[v]", "-map", "0:a", "-c:v", "libx264", "-crf", "18",
                                  "-pix_fmt", "yuv420p", "-c:a", "aac", str(out_dir / f"{sid}_ABC_side_by_side.mp4")], check=True)
            print(f"🎞️ {sid}_ABC_side_by_side.mp4", flush=True)


if __name__ == "__main__":
    import sys

    finalize_variants() if "--finalize" in sys.argv else main()
