#!/usr/bin/env python3
"""08 号：三个工具站频道的 Colab H3 FL2VA 出片（本地遥控器）。

复用 07 号的云端执行器 run_runway.py 和远程函数（上传、脱机运行、轮询），但不改 07 号的任何文件：
- 用自己生成的 config（从 07 的 runway_config.json 派生）覆盖 --config，
  把 07 已有的 preset 名 `fl2v_candid_look_camera` 重定义成本批次的 FL2VA 参数（因为 07 的 CLI 把 preset 名写死在 choices 里）。
- 画作类（PawMotif）用 style_mode=stylized：写实人像 LoRA 和特写 LoRA 都归零，保留画作笔触；
  真人类（Songifted/TryOnSwap）用 style_mode=photorealistic + realism_lora_strength=0.7（提示词以 r34l1sm 开头），特写 LoRA 始终 0（防推近）。
- --jobs 可以传多个文件，一次开机连出，省冷启动。
- 独立会话名（默认 sitech-g4），不复用、不停掉其他工作流的实例。

用法：
    python3 workflows/08_site_channels/render_samples.py --jobs workflows/08_site_channels/samples/pawmotif/jobs.json --dry-run
    python3 workflows/08_site_channels/render_samples.py --jobs a/jobs.json b/jobs.json   # 多个站一次开机
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
WF07 = REPO_ROOT / "workflows" / "07_street_fashion_runway"
SCRIPTS_DIR = REPO_ROOT / "scripts"
PRESET_KEY = "fl2v_candid_look_camera"  # 07 CLI choices 里已有的名字，内容由本脚本重定义
COLD_BOOT_MIN = 3.5
G4_CCU_PER_H = 10.05


def est_job_min(length: int) -> float:
    # 07 号实测：362 帧约 10.2 分钟，近似按帧数线性折算
    return 10.2 * length / 362


def build_config(spec: dict) -> dict:
    cfg = json.loads((WF07 / "runway_config.json").read_text(encoding="utf-8"))
    cfg = copy.deepcopy(cfg)
    length = int(spec.get("length", 192))
    assert (length - 5) % 17 == 0, f"length 必须满足 17k+5，当前 {length}"
    cfg["output_subdir"] = spec.get("output_subdir", "SiteChannels_Samples")
    cfg["bgm_mix_mode"] = "native_only"
    cfg["master_bgm_wav"] = ""
    cfg["presets"][PRESET_KEY] = {
        "description": f"08 site channels · FL2VA {length} 帧单段",
        "engine_mode": "fl2va",
        "unet_name": "minimax_h3_fl2va_pruned_fp8_scaled.safetensors",
        "turbo_lora_name": "minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors",
        "turbo_lora_strength": float(spec.get("turbo_lora_strength", 0.85)),
        "realism_lora_strength": float(spec.get("realism_lora_strength", 0.0)),
        "closeup_lora_strength": 0.0,
        "steps": int(spec.get("steps", 10)),
        "expected_segs": [1],
        "segments": [
            {
                "seg_id": 1,
                "length": length,
                "seed": 1,
                "first_frame": "__MUSE_FULLBODY__",
                "last_frame": "__MUSE_CLOSEUP__",
                "last_frame_idx": length - 5,
                "prompt": "",
            }
        ],
    }
    return cfg


def resolve(p: str, base: Path) -> Path:
    q = Path(p)
    return q if q.is_absolute() else (base / q)


def pull_from_drive(name: str, out_dir: Path, rrr) -> Path | None:
    import urllib.parse
    import urllib.request

    tok = json.loads(subprocess.check_output([rrr.COLAB_BIN, "dfs", "token"], text=True, env=rrr.ENV))["access_token"]
    q = urllib.parse.urlencode(
        {"q": f"trashed = false and name = '{name}'", "fields": "files(id,name,size,modifiedTime)", "orderBy": "modifiedTime desc", "pageSize": 3}
    )
    for _ in range(6):
        req = urllib.request.Request(f"https://www.googleapis.com/drive/v3/files?{q}", headers={"Authorization": f"Bearer {tok}"})
        files = [f for f in json.loads(urllib.request.urlopen(req, timeout=15).read().decode()).get("files", []) if int(f.get("size", 0)) > 10_000]
        if files:
            break
        time.sleep(3)
    else:
        return None
    f = files[0]
    out_dir.mkdir(parents=True, exist_ok=True)
    dst = out_dir / f["name"]
    req = urllib.request.Request(f"https://www.googleapis.com/drive/v3/files/{f['id']}?alt=media", headers={"Authorization": f"Bearer {tok}"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        dst.write_bytes(resp.read())
    print(f"📥 已从 Drive 拉回 {dst} ({dst.stat().st_size / 1024**2:.2f} MB, Drive size={f['size']})", flush=True)
    return dst


def main() -> None:
    ap = argparse.ArgumentParser(description="08 site channels: Colab H3 FL2VA sample renderer")
    ap.add_argument("--jobs", required=True, nargs="+", help="一个或多个 jobs.json")
    ap.add_argument("--only", default=None, help="逗号分隔的 job id")
    ap.add_argument("-s", "--session", default="sitech-g4")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--keep-alive", action="store_true")
    args = ap.parse_args()

    batches = []  # (spec, base, jobs, tag)
    for jp in args.jobs:
        jobs_path = Path(jp).resolve()
        spec = json.loads(jobs_path.read_text(encoding="utf-8"))
        jobs = spec["jobs"]
        if args.only:
            keep = {x.strip() for x in args.only.split(",")}
            jobs = [j for j in jobs if j["id"] in keep]
        if jobs:
            batches.append((spec, jobs_path.parent, jobs, jobs_path.parent.name))
    if not batches:
        raise SystemExit("❌ 没有要跑的 job")

    gpu_min = COLD_BOOT_MIN
    for spec, base, jobs, tag in batches:
        length = int(spec.get("length", 192))
        build_config(spec)  # 提前校验 17k+5
        for j in jobs:
            for k in ("first", "last"):
                p = resolve(j[k], base)
                if not p.exists():
                    raise FileNotFoundError(f"❌ [{j['id']}] 找不到 {k} 帧: {p}")
            gpu_min += est_job_min(length)
            print(f"  • [{tag}] {j['id']} {length} 帧 seed={j['seed']} | {Path(j['first']).name} -> {Path(j['last']).name}")
    n = sum(len(b[2]) for b in batches)
    print(f"🎬 共 {n} 条 | 会话 {args.session} | 预计 G4 {gpu_min:.1f} 分钟 ≈ {gpu_min / 60 * G4_CCU_PER_H:.2f} CCU（偏保守：实测热机 192 帧约 3.7 分钟/条）")
    if args.dry_run:
        print("✅ dry-run：素材齐全，未开机。")
        return

    try:
        import colab_cli  # noqa: F401
    except ImportError:
        uv_py = Path.home() / ".local/share/uv/tools/google-colab-cli/bin/python"
        if uv_py.exists() and str(sys.executable) != str(uv_py):
            os.execv(str(uv_py), [str(uv_py), *sys.argv])
    sys.path.insert(0, str(WF07))
    import run_runway_remote as rrr

    tmp = Path(tempfile.mkdtemp(prefix="site_samples_"))
    rrr.ensure_local_oauth(session_to_pause=args.session)
    sname = args.session
    results: dict[str, Path | None] = {}
    try:
        sname = rrr.ensure_g4_session(args.session)
        rrr.stage_scripts_and_inputs(sname, extra_local_files=[], only_sample_names=set())
        uploaded: set[str] = set()
        for spec, base, jobs, tag in batches:
            cfg_path = tmp / f"site_samples_config_{tag}.json"
            cfg_path.write_text(json.dumps(build_config(spec), ensure_ascii=False, indent=1), encoding="utf-8")
            rrr.upload_file_chunked(sname, cfg_path, f"/tmp/{cfg_path.name}")
            out_dir = resolve(spec.get("out_dir", "out"), base)
            for j in jobs:
                prefix = j["id"]
                pf = tmp / f"prompt_{prefix}.txt"
                pf.write_text(j["prompt"].strip(), encoding="utf-8")
                for f in (resolve(j["first"], base), resolve(j["last"], base)):
                    if f.name not in uploaded:
                        rrr.upload_file_chunked(sname, f, f"/tmp/{f.name}")
                        uploaded.add(f.name)
                rrr.upload_file_chunked(sname, pf, f"/tmp/{pf.name}")
                fwd = [
                    "--preset", PRESET_KEY,
                    "--style-mode", spec.get("style_mode", "stylized"),
                    "--prefix", prefix,
                    "--out-mp4", f"{prefix}_Master.mp4",
                    "--bgm-mix-mode", "native_only",
                    "--image", resolve(j["first"], base).name,
                    "--closeup-image", resolve(j["last"], base).name,
                    "--seed", str(j["seed"]),
                    "--prompt-file", f"/tmp/{pf.name}",
                    "--config", f"/tmp/{cfg_path.name}",  # 放最后，覆盖 rrr 默认的 /tmp/runway_config.json
                ]
                print(f"\n🚀 === [{tag}] {prefix} (seed={j['seed']}) ===", flush=True)
                try:
                    rrr.run_detached_pipeline(sname, forward_args=fwd)
                    # 销毁实例前先确认 Drive 上产物 size > 0（防烧钱硬规则 5）
                    results[prefix] = pull_from_drive(f"{prefix}_Master.mp4", out_dir, rrr)
                except Exception as exc:
                    print(f"⚠️ {prefix} 失败: {exc}", flush=True)
                    results[prefix] = None
    finally:
        if not args.keep_alive:
            print(f"🛑 释放 G4 实例 [{sname}] 并出计费报告...", flush=True)
            subprocess.run([rrr.COLAB_PY, str(SCRIPTS_DIR / "colab_meter.py"), "stop", "-s", sname], check=False, env=rrr.ENV)

    print("\n=== 汇总 ===")
    for k, v in results.items():
        print(f"  {'✅' if v else '❌'} {k}: {v}")
    if not all(results.values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
