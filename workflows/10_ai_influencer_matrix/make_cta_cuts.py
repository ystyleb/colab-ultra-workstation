#!/usr/bin/env python3
"""生成 work/tts/cta_cut.json：每条配音里口播 CTA（'Comment RULES.'）从哪剪掉（0 CCU，本地）。

subtitle_and_finalize.py 在剪点截断配音、接 CTA 字卡；broll_plan.py 的说话段配音也截到这里。
两步定位（2026-11-18）：
1. mlx_whisper 词级时间戳找最后一个 Comment（TTS 常把它念得像 "common"，所以按 comm 前缀匹配）
2. 在 Comment 起点附近找真实静音段，剪点 = 静音段开头 + min(0.3s, 60% 段长)
   只按「最后一个停顿」剪不行：J01 念成 "Comment.（停顿）Notice."，会把 Comment 留在片里；
   whisper 的词边界又有 ±0.2s 误差（J07 的 "her." 和 Comment 只隔 0.1s），所以要落到静音段里。
换了配音后重跑：python3 make_cta_cuts.py [--ids V01,J01]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

from subtitle_and_finalize import detect_pauses

HERE = Path(__file__).resolve().parent
TTS_DIR = HERE / "work" / "tts"
OUT = TTS_DIR / "cta_cut.json"
WORDS_DIR = TTS_DIR / "words"  # 词级时间戳，broll_plan.py 按台词文字定位剪点/插入镜头用


def whisper_words(wav: Path, tmp: Path) -> list[dict]:
    subprocess.run(
        ["mlx_whisper", str(wav), "--word-timestamps", "True", "--output-format", "json",
         "--output-dir", str(tmp), "--language", "en", "--verbose", "False"],
        check=True, capture_output=True,
    )
    d = json.loads((tmp / f"{wav.stem}.json").read_text(encoding="utf-8"))
    words = [{"word": w["word"], "start": round(w["start"], 3), "end": round(w["end"], 3)} for s in d["segments"] for w in s["words"]]
    WORDS_DIR.mkdir(parents=True, exist_ok=True)
    (WORDS_DIR / f"{wav.stem}.json").write_text(json.dumps(words, ensure_ascii=False), encoding="utf-8")
    return words


def cut_for(wav: Path, tmp: Path) -> dict:
    ws = whisper_words(wav, tmp)
    k = max(i for i, w in enumerate(ws) if w["word"].strip().lower().strip(".,!?").startswith("comm"))
    speech_end, c_start = ws[k - 1]["end"], ws[k]["start"]
    rec = {"speech_end": round(speech_end, 2), "comment_start": round(c_start, 2),
           "cut": round(min(speech_end + 0.30, (speech_end + c_start) / 2 + 0.1, c_start - 0.05), 2),
           "tail": " ".join(w["word"].strip() for w in ws[k - 2:]), "pause": None}
    spans = detect_pauses(wav, noise_db=-38, min_sil=0.09)
    cands = [(s, e) for s, e in spans if s <= c_start + 0.1 and e >= c_start - 0.35 and s > 1.0]
    if cands:
        s, e = cands[-1]
        rec["cut"] = round(s + min(0.3, (e - s) * 0.6), 2)
        rec["pause"] = [round(s, 2), round(e, 2)]
    return rec


def main() -> None:
    ap = argparse.ArgumentParser(description="定位口播 CTA 剪点 -> work/tts/cta_cut.json")
    ap.add_argument("--ids", default="")
    args = ap.parse_args()
    ids = [x.strip() for x in args.ids.split(",") if x.strip()]
    wavs = [TTS_DIR / f"{i}.wav" for i in ids] if ids else sorted(TTS_DIR.glob("[VJW][0-9][0-9].wav"))
    data = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    with tempfile.TemporaryDirectory(prefix="wf10_cta_") as tmp:
        for wav in wavs:
            data[wav.stem] = rec = cut_for(wav, Path(tmp))
            flag = "" if rec["pause"] else "  ⚠️ 没找到静音段，用 whisper 估计值，建议人工听一下"
            print(f"{wav.stem} cut={rec['cut']:.2f} pause={rec['pause']} | {rec['tail']}{flag}", flush=True)
    OUT.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
