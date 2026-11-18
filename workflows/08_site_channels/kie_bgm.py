#!/usr/bin/env python3
"""08 号：用 Kie Suno 生成纯音乐配乐（instrumental），一次出 2 条备选。

复用 05 号 kie_suno.py 的 kie_call / 读 key 逻辑，不改 05 的文件。
Songifted 不用这个脚本（固定用站里的 demo 歌）。

用法：
    python3 workflows/08_site_channels/kie_bgm.py --title "Into the Frame" \
        --style "whimsical orchestral, pizzicato strings, celesta..." --out out/bgm/pawmotif
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "05_ancient_rap_battle" / "scripts"))
import kie_suno as ks  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", required=True)
    ap.add_argument("--style", required=True)
    ap.add_argument("--out", required=True, help="输出目录（相对 08 目录或绝对路径）")
    ap.add_argument("--model", default="V6")
    args = ap.parse_args()

    out = Path(args.out)
    out = out if out.is_absolute() else HERE / out
    out.mkdir(parents=True, exist_ok=True)

    before = ks.kie_call("GET", "/api/v1/chat/credit")
    inp = {
        "model": args.model,
        "custom_mode": True,
        "instrumental": True,
        "title": args.title[:80],
        "style": args.style[:1000],
    }
    res = ks.kie_call("POST", "/api/v1/jobs/createTask", {"model": ks.SUNO_MODEL, "input": inp})
    task_id = res["taskId"]
    print(f"🎵 Kie Suno task {task_id} | credit before {before}", flush=True)
    t0 = time.time()
    while True:
        time.sleep(6)
        d = ks.kie_call("GET", f"/api/v1/jobs/recordInfo?taskId={task_id}")
        st = d.get("state", "waiting")
        if st == "success":
            tracks = ks.extract_suno_tracks(d)
            break
        if st == "fail":
            raise SystemExit(f"❌ Suno 失败: {d.get('failCode')} {d.get('failMsg')}")
        if time.time() - t0 > 600:
            raise SystemExit(f"❌ Suno 超时 taskId={task_id}")
    for i, tr in enumerate(tracks, 1):
        dst = out / f"bgm_v{i}.mp3"
        urllib.request.urlretrieve(tr["audioUrl"], dst)
        tr["local_mp3"] = str(dst)
        print(f"⬇️ {dst} ({tr.get('duration', 0):.1f}s)", flush=True)
    (out / "kie_bgm.json").write_text(json.dumps({"taskId": task_id, "input": inp, "tracks": tracks}, ensure_ascii=False, indent=1), encoding="utf-8")
    after = ks.kie_call("GET", "/api/v1/chat/credit")
    print(f"💳 credit after {after} (spent {before - after:.2f})", flush=True)


if __name__ == "__main__":
    main()
