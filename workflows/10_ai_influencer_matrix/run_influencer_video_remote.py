#!/usr/bin/env python3
"""Local Remote Controller for Workflow 10 Cloud G4 MiniMax-H3 Video Batch Generation.

- `--dry-run` (0 CCU): verifies 6 local Codex PNGs (`sample_inputs/`), TTS WAV availability (`work/tts/`),
  legal `17k + 5` frame counts across all selected scripts, sample Iron-Rule-F prompt, and exact G4 CCU estimate.
- `--pull-only` (0 CCU): recovers/downloads finished `AIInf_*.mp4` files from Google Drive v3 API.
- Live mode: wraps `colab_meter.py start/stop -s inf-h3-g4 -g G4`, mounts Drive, uploads runner/inputs,
  launches detached `nohup`, polls with `alarm 25`, verifies Drive v3 `size > 0` before teardown, and downloads MP4s.
"""

from __future__ import annotations

import argparse
import base64
import json
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
SAMPLE_DIR = HERE / "sample_inputs"
LOCAL_TTS_DIR = HERE / "work" / "tts"
LOCAL_RAW_OUT = HERE / "outputs" / "raw"
CONFIG_PATH = HERE / "influencer_config.json"
MANIFEST_PATH = HERE / "scripts_30_manifest.json"
CLOUD_VIDEO_PY = HERE / "cloud_influencer_h3.py"
FAST_LAUNCHER_PY = SCRIPTS_DIR / "launch_g4_comfyui_fast.py"

COLAB_BIN = os.path.expanduser("~/.local/bin/colab")

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
        except (urllib.error.URLError, ssl.SSLError, TimeoutError, ConnectionError):
            if k == tries - 1:
                raise
            time.sleep((2**k) * 2)


def run_dry_run(cfg: dict, scripts: list[dict]) -> None:
    from cloud_influencer_h3 import build_h3_prompt

    print("🧪 [0-CCU DRY-RUN] Cloud G4 MiniMax-H3 Ref2VA 9:16 Video Batch Planner")
    print(f"   Session: {cfg['project_meta']['video_session']} | GPU: G4 (10.05 CCU/h) | {cfg['h3_defaults']['width']}x{cfg['h3_defaults']['height']}")

    missing_imgs: list[str] = []
    ready_wavs = 0
    for s in scripts:
        pk = s["persona"]
        sc = s["scene"]
        img_name = cfg["personas"][pk]["scenes"][sc]["image"]
        img_path = SAMPLE_DIR / img_name
        if not img_path.exists():
            missing_imgs.append(str(img_path))
        wav_ok = (LOCAL_TTS_DIR / f"{s['id']}.wav").exists()
        if wav_ok:
            ready_wavs += 1
        assert (s["default_frames"] - 5) % 17 == 0, f"Illegal frame count in {s['id']}"

    if missing_imgs:
        raise FileNotFoundError(f"❌ Missing reference images:\n" + "\n".join(set(missing_imgs)))

    print(f"   ✅ Reference Keyframes: ALL present ({len(set(cfg['personas'][s['persona']]['scenes'][s['scene']]['image'] for s in scripts))} unique PNGs verified)")
    print(f"   🎙️ Local TTS WAVs staged: {ready_wavs}/{len(scripts)} in {LOCAL_TTS_DIR}")

    sample = scripts[0]
    p_cfg = cfg["personas"][sample["persona"]]
    sc_cfg = p_cfg["scenes"][sample["scene"]]
    sample_prompt = build_h3_prompt(p_cfg, sc_cfg, sample, sample["default_frames"] / 24.0)
    print(f"\n📝 Sample Iron-Rule-F Prompt ({sample['id']}):\n---\n{sample_prompt}\n---")

    def est_ccu(n_clips: int) -> tuple[float, float]:
        # ~4.5 min cold NVMe stage + ComfyUI load, ~3.6 min per 14-15s clip on G4
        mins = 4.5 + n_clips * 3.6
        return mins, (mins / 60.0) * 10.05

    m_sel, c_sel = est_ccu(len(scripts))
    m_3, c_3 = est_ccu(3)
    m_30, c_30 = est_ccu(30)
    print("\n💰 G4 CCU Budget Estimates (10.05 CCU/h):")
    print(f"   • 3-Clip Pilot (V01,J01,W01):   ~{m_3:.1f} min  (~{c_3:.2f} CCU)  [+ ~0.12 CCU L4 TTS]")
    print(f"   • Selected Batch ({len(scripts):2d} clips):    ~{m_sel:.1f} min (~{c_sel:.2f} CCU)")
    print(f"   • Full 30-Clip Matrix:          ~{m_30:.1f} min (~{c_30:.2f} CCU)")


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
                raise RuntimeError(f"❌ colab exec failed:\n{r.stderr}\n{r.stdout}")
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


def upload_bytes_chunked(session: str, remote_path: str, data: bytes, chunk_size: int = 45_000) -> None:
    b64 = base64.b64encode(data).decode("ascii")
    colab_exec_short(session, f'from pathlib import Path; p=Path("{remote_path}"); p.parent.mkdir(parents=True, exist_ok=True); p.unlink(missing_ok=True)', check=True)
    for i in range(0, len(b64), chunk_size):
        seg = b64[i : i + chunk_size]
        colab_exec_short(
            session,
            f'import base64\nwith open("{remote_path}", "ab") as f: f.write(base64.b64decode("{seg}"))',
            timeout_sec=30,
            check=True,
        )


def pull_videos_from_drive(ids: list[str] | None = None) -> list[Path]:
    LOCAL_RAW_OUT.mkdir(parents=True, exist_ok=True)
    tok = parse_colab_token_json(subprocess.check_output([COLAB_BIN, "dfs", "token"], text=True, env=ENV))
    params = urllib.parse.urlencode(
        {
            "q": "trashed = false and name contains 'AIInf_' and name contains '.mp4'",
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
    wanted_prefixes = {f"AIInf_{i}_" for i in ids} if ids else None
    pulled: list[Path] = []
    seen: set[str] = set()
    for f in files:
        name = f["name"]
        if int(f.get("size", 0)) <= 10_000 or name in seen:
            continue
        if wanted_prefixes and not any(name.startswith(p) for p in wanted_prefixes):
            continue
        seen.add(name)
        dl_req = urllib.request.Request(
            f"https://www.googleapis.com/drive/v3/files/{f['id']}?alt=media",
            headers={"Authorization": f"Bearer {tok}"},
        )
        raw = urlopen_retry(dl_req, timeout=180).read()
        dst = LOCAL_RAW_OUT / name
        dst.write_bytes(raw)
        pulled.append(dst)
        print(f"⬇️ Pulled {name} ({len(raw) / 1e6:.2f} MB)", flush=True)
    return pulled


def main() -> None:
    ap = argparse.ArgumentParser(description="Workflow 10 Cloud G4 MiniMax-H3 Remote Controller")
    ap.add_argument("--ids", default="", help="Comma-separated script IDs (e.g. V01,J01,W01)")
    ap.add_argument("--dry-run", action="store_true", help="0-CCU local check and CCU estimate")
    ap.add_argument("--pull-only", action="store_true", help="0-CCU pull finished MP4s from Drive")
    ap.add_argument("--keep-alive", action="store_true", help="Keep G4 session alive after completion")
    args = ap.parse_args()

    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    sel = {x.strip() for x in args.ids.split(",") if x.strip()} if args.ids else None
    scripts = [s for s in manifest["scripts"] if (not sel or s["id"] in sel)]
    if not scripts:
        raise SystemExit("❌ No matching scripts selected.")

    if args.dry_run:
        run_dry_run(cfg, scripts)
        return

    if args.pull_only:
        pull_videos_from_drive([s["id"] for s in scripts] if sel else None)
        return

    ensure_colab_python_env()
    session = cfg["project_meta"]["video_session"]
    ids_arg = ",".join(s["id"] for s in scripts)

    # Verify all required inputs exist locally before booting G4
    req_imgs = sorted({cfg["personas"][s["persona"]]["scenes"][s["scene"]]["image"] for s in scripts})
    for img in req_imgs:
        if not (SAMPLE_DIR / img).exists():
            raise FileNotFoundError(f"Missing reference PNG: {SAMPLE_DIR / img}")
    for s in scripts:
        if not (LOCAL_TTS_DIR / f"{s['id']}.wav").exists():
            raise FileNotFoundError(f"Missing TTS WAV: {LOCAL_TTS_DIR / (s['id'] + '.wav')}. Run run_influencer_tts_remote.py first.")

    subprocess.run([sys.executable, str(SCRIPTS_DIR / "colab_meter.py"), "start", "-s", session, "-g", "G4"], check=False, env=ENV)
    try:
        subprocess.run([COLAB_BIN, "new", "-s", session, "--gpu", "G4"], check=True, env=ENV)
        mount_drive(session)

        print("📤 Uploading fast launcher, H3 runner, config & inputs...", flush=True)
        if FAST_LAUNCHER_PY.exists():
            upload_bytes_chunked(session, "/tmp/launch_g4_comfyui_fast.py", FAST_LAUNCHER_PY.read_bytes())
        upload_bytes_chunked(session, "/tmp/cloud_influencer_h3.py", CLOUD_VIDEO_PY.read_bytes())
        upload_bytes_chunked(session, "/tmp/wf10_config.json", CONFIG_PATH.read_bytes())
        upload_bytes_chunked(session, "/tmp/wf10_scripts.json", MANIFEST_PATH.read_bytes())
        if (LOCAL_TTS_DIR / "tts_manifest.json").exists():
            upload_bytes_chunked(session, "/tmp/wf10_tts_manifest.json", (LOCAL_TTS_DIR / "tts_manifest.json").read_bytes())
        for img in req_imgs:
            upload_bytes_chunked(session, f"/tmp/wf10_inputs/{img}", (SAMPLE_DIR / img).read_bytes())
        for s in scripts:
            w = LOCAL_TTS_DIR / f"{s['id']}.wav"
            upload_bytes_chunked(session, f"/tmp/wf10_inputs/{w.name}", w.read_bytes())

        launch_py = f"""
import json, subprocess, sys
from pathlib import Path
Path("/tmp/wf10_h3.done").unlink(missing_ok=True)
Path("/tmp/wf10_h3.err").unlink(missing_ok=True)
cmd = [sys.executable, "-u", "/tmp/cloud_influencer_h3.py", "--config", "/tmp/wf10_config.json", "--scripts", "/tmp/wf10_scripts.json", "--ids", {json.dumps(ids_arg)}]
if Path("/tmp/wf10_tts_manifest.json").exists():
    cmd += ["--tts-manifest", "/tmp/wf10_tts_manifest.json"]
runner = "import subprocess\\nfrom pathlib import Path\\np = subprocess.run(" + repr(cmd) + ")\\n(Path('/tmp/wf10_h3.done') if p.returncode == 0 else Path('/tmp/wf10_h3.err')).write_text(str(p.returncode))\\n"
Path("/tmp/wf10_h3_runner.py").write_text(runner)
subprocess.Popen("nohup python3 -u /tmp/wf10_h3_runner.py > /tmp/wf10_h3.log 2>&1 &", shell=True)
print("H3_LAUNCHED")
"""
        out = colab_exec_short(session, launch_py, timeout_sec=30, check=True)
        if "H3_LAUNCHED" not in out:
            raise RuntimeError(f"Failed to launch H3 batch:\n{out}")

        seen_lines = 0
        for _ in range(360):
            time.sleep(10)
            poll = colab_exec_short(
                session,
                """import json
from pathlib import Path
lines = Path("/tmp/wf10_h3.log").read_text(errors="ignore").splitlines() if Path("/tmp/wf10_h3.log").exists() else []
print(json.dumps({"n": len(lines), "lines": lines, "done": Path("/tmp/wf10_h3.done").exists(), "err": Path("/tmp/wf10_h3.err").exists()}))""",
                timeout_sec=25,
            )
            if not poll.strip():
                continue
            info = json.loads(poll.strip().splitlines()[-1])
            for ln in info["lines"][seen_lines:]:
                print(f"  [G4] {ln}", flush=True)
            seen_lines = info["n"]
            if info["err"]:
                raise RuntimeError("❌ Cloud G4 H3 batch failed. Check /tmp/wf10_h3.log.")
            if info["done"]:
                break
        else:
            raise TimeoutError("❌ Cloud G4 H3 batch timed out.")

        pulled = pull_videos_from_drive([s["id"] for s in scripts])
        if len(pulled) < len(scripts):
            raise RuntimeError(f"❌ Expected {len(scripts)} MP4s on Drive, found {len(pulled)}.")
    finally:
        if not args.keep_alive:
            subprocess.run([sys.executable, str(SCRIPTS_DIR / "colab_meter.py"), "stop", "-s", session], check=False, env=ENV)


if __name__ == "__main__":
    main()
