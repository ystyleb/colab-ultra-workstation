#!/usr/bin/env python3
"""Local Remote Controller for Workflow 10 Cloud L4 English TTS Synthesis.

- `--dry-run` runs purely locally at 0.00 CCU: validates scripts/config, estimates durations
  at ~2.55 words/sec, maps to legal `17k + 5` H3 frames, and prints L4 CCU cost estimates.
- Live mode wraps execution with `colab_meter.py start/stop`, detached `nohup`, `alarm 25` polling,
  Drive v3 size verification, and downloads synthesized `.wav` + `tts_manifest.json` into `work/tts/`.
"""

from __future__ import annotations

import argparse
import base64
import json
import math
import os
import ssl
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
CONFIG_PATH = HERE / "influencer_config.json"
MANIFEST_PATH = HERE / "scripts_30_manifest.json"
LOCAL_TTS_DIR = HERE / "work" / "tts"
CLOUD_SCRIPT = HERE / "cloud_influencer_tts.py"

COLAB_BIN = os.path.expanduser("~/.local/bin/colab")
COLAB_PY = os.path.expanduser("~/.local/share/uv/tools/google-colab-cli/bin/python")

ENV = dict(os.environ)
ENV.setdefault("https_proxy", "http://127.0.0.1:7890")
ENV.setdefault("http_proxy", "http://127.0.0.1:7890")
ENV.setdefault("no_proxy", "localhost,127.0.0.1")


def ensure_colab_python_env() -> None:
    try:
        import colab_cli  # noqa: F401
    except ImportError:
        uv_py = Path.home() / ".local/share/uv/tools/google-colab-cli/bin/python"
        if uv_py.exists() and str(sys.executable) != str(uv_py):
            os.execv(str(uv_py), [str(uv_py), *sys.argv])


def parse_colab_token_json(raw: str) -> str:
    cleaned = raw[raw.index("{") : raw.rindex("}") + 1]
    return json.loads(cleaned)["access_token"]


def urlopen_retry(req, timeout: int = 20, tries: int = 5):
    for k in range(tries):
        try:
            return urllib.request.urlopen(req, timeout=timeout)
        except (urllib.error.URLError, ssl.SSLError, TimeoutError, ConnectionError) as exc:
            if k == tries - 1:
                raise
            time.sleep((2**k) * 2)


def snap_frames(duration_sec: float, legal_frames: list[int]) -> int:
    needed = math.ceil((duration_sec + 0.25) * 24.0)
    for f in legal_frames:
        if f >= max(124, needed):
            return f
    return legal_frames[-1]


def run_dry_run(cfg: dict, scripts: list[dict], mode: str) -> None:
    legal = cfg["project_meta"]["legal_h3_frames"]
    print(f"🧪 [0-CCU DRY-RUN] Cloud L4 English TTS Planner (mode={mode})")
    print(f"   Session: {cfg['project_meta']['tts_session']} | GPU: L4 (1.71 CCU/h)")
    print(f"   Selected scripts: {len(scripts)}\n")

    for s in scripts:
        wc = len(s["spoken_en"].split())
        est_dur = round(wc / 2.55 + 0.70, 2)  # 0.30s head + 0.40s tail pad
        est_frames = snap_frames(est_dur, legal)
        assert (s["default_frames"] - 5) % 17 == 0, f"Illegal default_frames in {s['id']}"
        print(
            f"   • {s['id']} [{s['persona']:6s} | {s['scene']:10s}] "
            f"{wc:2d}w | est {est_dur:5.2f}s -> {est_frames}f (manifest={s['default_frames']}f) | {s['title']}"
        )

    boot_min = 4.0
    synth_min = len(scripts) * 0.14
    total_min = boot_min + synth_min
    est_ccu = (total_min / 60.0) * 1.71
    print(f"\n📊 L4 预计总耗时: ~{total_min:.1f} 分钟 | 预计消耗: ~{est_ccu:.2f} CCU (1.71 CCU/h)")


def colab_exec_short(session: str, py_code: str, timeout_sec: int = 30, check: bool = False) -> str:
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as tf:
        tf.write(py_code)
        tmp_p = tf.name
    try:
        for attempt in range(3):
            cmd = ["perl", "-e", f"alarm {timeout_sec}; exec @ARGV", COLAB_BIN, "exec", "-s", session, "-f", tmp_p]
            r = subprocess.run(cmd, text=True, capture_output=True, env=ENV)
            if r.returncode == 0:
                return r.stdout
            if attempt < 2:
                time.sleep(2.5)
                continue
            if check:
                raise RuntimeError(f"❌ colab exec failed (exit={r.returncode}):\n{r.stderr}\n{r.stdout}")
        return ""
    finally:
        Path(tmp_p).unlink(missing_ok=True)


def mount_drive(session: str) -> None:
    chk = colab_exec_short(
        session,
        'import os; print("MOUNT_OK" if os.path.isdir("/content/drive/My Drive") or os.path.isdir("/content/drive/MyDrive") else "NO")',
    )
    if "MOUNT_OK" not in chk:
        subprocess.run([COLAB_BIN, "dfs", "mount", "-s", session], check=True, env=ENV)


def pull_tts_from_drive(filenames: list[str]) -> list[Path]:
    LOCAL_TTS_DIR.mkdir(parents=True, exist_ok=True)
    tok = parse_colab_token_json(subprocess.check_output([COLAB_BIN, "dfs", "token"], text=True, env=ENV))
    wanted = set(filenames) | {"tts_manifest.json"}
    params = urllib.parse.urlencode(
        {
            "q": "trashed = false and (name contains '.wav' or name = 'tts_manifest.json')",
            "fields": "files(id,name,size,modifiedTime)",
            "orderBy": "modifiedTime desc",
            "pageSize": 60,
        }
    )
    req = urllib.request.Request(
        f"https://www.googleapis.com/drive/v3/files?{params}",
        headers={"Authorization": f"Bearer {tok}"},
    )
    files = json.loads(urlopen_retry(req).read().decode()).get("files", [])
    pulled: list[Path] = []
    seen: set[str] = set()
    for f in files:
        name = f["name"]
        if name not in wanted or name in seen or int(f.get("size", 0)) <= 0:
            continue
        seen.add(name)
        dl_req = urllib.request.Request(
            f"https://www.googleapis.com/drive/v3/files/{f['id']}?alt=media",
            headers={"Authorization": f"Bearer {tok}"},
        )
        data = urlopen_retry(dl_req, timeout=60).read()
        dst = LOCAL_TTS_DIR / name
        dst.write_bytes(data)
        pulled.append(dst)
        print(f"⬇️ Pulled {name} ({len(data) / 1024:.1f} KB)", flush=True)
    return pulled


def main() -> None:
    ap = argparse.ArgumentParser(description="Workflow 10 Cloud L4 English TTS Remote Controller")
    ap.add_argument("--ids", default="", help="Comma-separated script IDs (e.g. V01,J01,W01)")
    ap.add_argument("--mode", default="qwen", choices=["qwen", "hybrid"])
    ap.add_argument("--dry-run", action="store_true", help="0-CCU local validation and CCU estimate")
    ap.add_argument("--pull-only", action="store_true", help="0-CCU pull generated WAVs from Drive")
    ap.add_argument("--keep-alive", action="store_true", help="Keep L4 session alive after completion")
    args = ap.parse_args()

    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    sel = {x.strip() for x in args.ids.split(",") if x.strip()} if args.ids else None
    scripts = [s for s in manifest["scripts"] if (not sel or s["id"] in sel)]
    if not scripts:
        raise SystemExit("❌ No matching scripts selected.")

    if args.dry_run:
        run_dry_run(cfg, scripts, args.mode)
        return

    if args.pull_only:
        names = [f"{s['id']}.wav" for s in scripts] + [f"seed_{p}.wav" for p in {s['persona'] for s in scripts}]
        pull_tts_from_drive(names)
        return

    ensure_colab_python_env()
    session = cfg["project_meta"]["tts_session"]
    ids_arg = ",".join(s["id"] for s in scripts)

    subprocess.run([sys.executable, str(SCRIPTS_DIR / "colab_meter.py"), "start", "-s", session, "-g", "L4"], check=False, env=ENV)
    try:
        subprocess.run([COLAB_BIN, "new", "-s", session, "--gpu", "L4"], check=True, env=ENV)
        mount_drive(session)

        b64_py = base64.b64encode(CLOUD_SCRIPT.read_bytes()).decode("ascii")
        b64_cfg = base64.b64encode(CONFIG_PATH.read_bytes()).decode("ascii")
        b64_man = base64.b64encode(MANIFEST_PATH.read_bytes()).decode("ascii")

        launch_py = f"""
import base64, json, subprocess, sys
from pathlib import Path
Path("/tmp/cloud_influencer_tts.py").write_bytes(base64.b64decode("{b64_py}"))
Path("/tmp/wf10_config.json").write_bytes(base64.b64decode("{b64_cfg}"))
Path("/tmp/wf10_scripts.json").write_bytes(base64.b64decode("{b64_man}"))
Path("/tmp/wf10_tts.done").unlink(missing_ok=True)
Path("/tmp/wf10_tts.err").unlink(missing_ok=True)
runner = '''import subprocess, sys
from pathlib import Path
p = subprocess.run([sys.executable, "-u", "/tmp/cloud_influencer_tts.py", "--config", "/tmp/wf10_config.json", "--scripts", "/tmp/wf10_scripts.json", "--ids", {json.dumps(ids_arg)}, "--mode", {json.dumps(args.mode)}])
(Path("/tmp/wf10_tts.done") if p.returncode == 0 else Path("/tmp/wf10_tts.err")).write_text(str(p.returncode))
'''
Path("/tmp/wf10_tts_runner.py").write_text(runner)
subprocess.Popen("nohup python3 -u /tmp/wf10_tts_runner.py > /tmp/wf10_tts.log 2>&1 &", shell=True)
print("TTS_LAUNCHED")
"""
        out = colab_exec_short(session, launch_py, timeout_sec=30, check=True)
        if "TTS_LAUNCHED" not in out:
            raise RuntimeError(f"Failed to launch detached TTS job:\n{out}")

        seen_lines = 0
        for _ in range(180):
            time.sleep(8)
            poll = colab_exec_short(
                session,
                """import json
from pathlib import Path
lines = Path("/tmp/wf10_tts.log").read_text(errors="ignore").splitlines() if Path("/tmp/wf10_tts.log").exists() else []
print(json.dumps({"n": len(lines), "lines": lines, "done": Path("/tmp/wf10_tts.done").exists(), "err": Path("/tmp/wf10_tts.err").exists()}))""",
                timeout_sec=25,
            )
            if not poll.strip():
                continue
            info = json.loads(poll.strip().splitlines()[-1])
            for ln in info["lines"][seen_lines:]:
                print(f"  [L4] {ln}", flush=True)
            seen_lines = info["n"]
            if info["err"]:
                raise RuntimeError("❌ Cloud L4 TTS job exited with error. Check /tmp/wf10_tts.log.")
            if info["done"]:
                break
        else:
            raise TimeoutError("❌ Cloud L4 TTS timed out waiting for completion.")

        names = [f"{s['id']}.wav" for s in scripts] + [f"seed_{p}.wav" for p in {s['persona'] for s in scripts}]
        pulled = pull_tts_from_drive(names)
        if not pulled:
            raise RuntimeError("❌ Drive v3 verification found zero synthesized WAV files.")
    finally:
        if not args.keep_alive:
            subprocess.run([sys.executable, str(SCRIPTS_DIR / "colab_meter.py"), "stop", "-s", session], check=False, env=ENV)


if __name__ == "__main__":
    main()
