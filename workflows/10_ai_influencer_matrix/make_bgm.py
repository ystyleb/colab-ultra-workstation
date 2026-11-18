#!/usr/bin/env python3
"""三个人物各一首纯音乐垫底（KIE Suno，付费积分，2026-11-18 用户同意）。

每次请求 Suno 返回 2 个版本，都下载到 bgm/<persona>_v1.mp3 / _v2.mp3，元数据写 bgm/<persona>.json。
已存在就跳过（--force 重做）。混音在 subtitle_and_finalize.py 里做（人声下压、说话时再让一点）。
复用 05 号工作流的 kie_suno.py 的接口约定（jobs/createTask + recordInfo 轮询）。
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
BGM_DIR = HERE / "bgm"
KIE_SUNO = HERE.parent / "05_ancient_rap_battle" / "scripts" / "kie_suno.py"

STYLES = {
    "vivian": ("Quiet Money Underscore",
               "soft solo piano with gentle warm strings, slow 70 BPM, elegant, calm, intimate, sparse, "
               "cinematic underscore for a talking video, steady and unobtrusive, no drums, no vocals"),
    "june": ("Contact Sheet Underscore",
             "warm fingerpicked acoustic guitar with soft felt piano, slow 75 BPM, nostalgic, tender, "
             "Americana folk underscore for a talking video, steady and unobtrusive, no drums, no vocals"),
    "wen": ("Tea Drawer Underscore",
            "soft felt piano with sparse gentle guqin plucks over a warm ambient pad, slow 65 BPM, calm, unhurried, "
            "afternoon tea-shop underscore for a talking video, steady and unobtrusive, no drums, no gongs, no vocals"),
}


def load_kie():
    spec = importlib.util.spec_from_file_location("kie_suno", KIE_SUNO)
    mod = importlib.util.module_from_spec(spec)
    import sys

    sys.path.insert(0, str(KIE_SUNO.parent))
    spec.loader.exec_module(mod)
    return mod


def main() -> None:
    ap = argparse.ArgumentParser(description="KIE Suno 生成人物垫底纯音乐")
    ap.add_argument("--personas", default="vivian,june,wen")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    kie = load_kie()
    BGM_DIR.mkdir(exist_ok=True)
    before = kie.kie_call("GET", "/api/v1/chat/credit")
    print(f"💳 KIE credit before: {before}", flush=True)
    tasks = {}
    for pk in [x.strip() for x in args.personas.split(",") if x.strip()]:
        if (BGM_DIR / f"{pk}.json").exists() and not args.force:
            print(f"♻️ {pk}: 已有，跳过", flush=True)
            continue
        title, style = STYLES[pk]
        inp = {"model": "V6", "custom_mode": True, "instrumental": True, "title": title, "style": style}
        res = kie.kie_call("POST", "/api/v1/jobs/createTask", {"model": kie.SUNO_MODEL, "input": inp})
        tasks[pk] = res["taskId"]
        print(f"🎵 {pk}: task {res['taskId']}", flush=True)
    t0 = time.time()
    while tasks and time.time() - t0 < 900:
        time.sleep(8)
        for pk, tid in list(tasks.items()):
            d = kie.kie_call("GET", f"/api/v1/jobs/recordInfo?taskId={tid}")
            st = d.get("state")
            if st == "fail":
                print(f"❌ {pk}: {d.get('failCode')} {d.get('failMsg')}", flush=True)
                del tasks[pk]
            elif st == "success":
                tracks = kie.extract_suno_tracks(d)
                for k, tr in enumerate(tracks, 1):
                    dst = BGM_DIR / f"{pk}_v{k}.mp3"
                    urllib.request.urlretrieve(tr["audioUrl"], dst)
                    tr["local"] = dst.name
                    print(f"⬇️ {pk} v{k}: {tr['duration']:.0f}s -> {dst.name}", flush=True)
                (BGM_DIR / f"{pk}.json").write_text(json.dumps({"taskId": tid, "style": STYLES[pk][1], "tracks": tracks}, indent=1), encoding="utf-8")
                del tasks[pk]
    if tasks:
        print(f"⏰ 超时未完成: {tasks}", flush=True)
    after = kie.kie_call("GET", "/api/v1/chat/credit")
    print(f"💳 KIE credit after: {after} (spent {before - after:.2f})", flush=True)


if __name__ == "__main__":
    main()
