#!/usr/bin/env python3
"""Workflow 10 口型质检（0 CCU，本地）：H3 原始素材里人物到底有没有跟着配音张嘴。

H3 偶尔会把口播当成画外音，人物全程闭嘴（W01 第一版因为倒茶动作、J02 第一版原因不明）。
复用 05 号 rap 项目的 mediapipe 打分器（~/.cache/rap_lipeval + 05/scripts/lipcheck.py）：
嘴部开合幅度和配音响度做相关，取 ±8 帧内最好的相关系数。

2026-11-18 标定：正常片 0.25–0.39，没张嘴的片 -0.08 / -0.03，阈值取 0.15。

usage: python3 lip_qa.py --ids V02,J02,W02      # 不给 --ids 就查 outputs/raw 里所有片号
输出表格 + work/lip_qa.json，最后一行打印不合格片号（可直接喂给 run_influencer_video_remote.py --ids）。
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW_DIR = HERE / "outputs" / "raw"
TTS_DIR = HERE / "work" / "tts"
LIPEVAL = Path.home() / ".cache/rap_lipeval/lipeval.py"
LIPEVAL_PY = Path.home() / ".cache/rap_lipeval_venv/bin/python"
LIPCHECK_DIR = HERE.parent / "05_ancient_rap_battle" / "scripts"
MIN_CORR = 0.15
MIN_FACE_HIT = 0.9


def wav_duration(p: Path) -> float:
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)], text=True)
    return float(out.strip())


def latest_raw(clip_id: str) -> Path | None:
    cands = sorted(RAW_DIR.glob(f"AIInf_{clip_id}_*-audio.mp4"), key=lambda p: p.stat().st_mtime)
    return cands[-1] if cands else None


def score(clip_id: str) -> dict:
    raw, wav = latest_raw(clip_id), TTS_DIR / f"{clip_id}.wav"
    if raw is None or not wav.exists():
        return {"id": clip_id, "ok": False, "reason": "missing raw mp4 or wav"}
    r = subprocess.run(
        [str(LIPEVAL_PY), str(LIPEVAL), str(LIPCHECK_DIR), str(raw), str(wav), f"{wav_duration(wav):.3f}"],
        capture_output=True, text=True,
    )
    try:
        res = json.loads(r.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        return {"id": clip_id, "raw": raw.name, "ok": False, "reason": f"scorer failed: {r.stderr[-300:]}"}
    corr = res.get("corr_best")
    ok = corr is not None and corr == corr and corr >= MIN_CORR and res.get("face_hit", 0) >= MIN_FACE_HIT
    reason = "" if ok else ("face not found" if res.get("face_hit", 0) < MIN_FACE_HIT else "mouth does not follow the voice")
    return {"id": clip_id, "raw": raw.name, "ok": ok, "corr_best": corr, "face_hit": res.get("face_hit"),
            "mouth_p90": res.get("mouth_active_p10_p90", [None, None])[1], "reason": reason}


def main() -> None:
    ap = argparse.ArgumentParser(description="Workflow 10 lip-sync QA (0 CCU)")
    ap.add_argument("--ids", default="")
    args = ap.parse_args()
    for need in (LIPEVAL, LIPEVAL_PY, LIPCHECK_DIR / "lipcheck.py"):
        if not need.exists():
            raise SystemExit(f"❌ 缺少口型打分器依赖：{need}")
    ids = [x.strip() for x in args.ids.split(",") if x.strip()] or sorted(
        {p.name.split("_")[1] for p in RAW_DIR.glob("AIInf_*-audio.mp4")}
    )
    results = []
    for i in ids:
        res = score(i)
        results.append(res)
        mark = "✅" if res["ok"] else "❌"
        print(f"{mark} {i}  corr={res.get('corr_best')}  face={res.get('face_hit')}  {res.get('raw', '')}  {res.get('reason', '')}", flush=True)
    (HERE / "work").mkdir(exist_ok=True)
    (HERE / "work" / "lip_qa.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    bad = [r["id"] for r in results if not r["ok"]]
    print(f"\nFAILED: {','.join(bad) if bad else '(none)'}")


if __name__ == "__main__":
    main()
