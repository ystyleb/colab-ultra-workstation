#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Zero-Waste Local Controller for Workflow 05 (Historical / Ancient Rap Battle on Colab G4).

Follows all Zero-Burn Iron Rules:
1. Local prep (`kie_suno.py`, `make_clips.py`, `refs/*.png`) must be completed at 0 CCU before invoking this script.
2. Starts/attaches G4 with `colab new -s rap-g4-<run-timestamp> --gpu G4` + `colab_meter.py start -s rap-g4-<run-timestamp> -g G4`, mounts Google Drive (`colab dfs mount -s rap-g4-<run-timestamp>`), stages the prepared episode bundle via Drive v3 API, and runs `h3_colab_runner.py` via detached `nohup`.
3. Immediately after rendering finishes and clips are synced to Google Drive, stops the G4 instance (`colab stop -s rap-g4-<run-timestamp>` + `colab_meter.py stop -s rap-g4-<run-timestamp>`, this session only -> 0.00 CCU/h).
4. Pulls clips from Google Drive v3 API at 0 CCU and runs `assemble.py` + `package.py` + `cover.py` locally on macOS.
"""
import argparse
import base64
from contextlib import contextmanager
import fcntl
import json
import shlex
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

_uv_py = Path.home() / ".local/share/uv/tools/google-colab-cli/bin/python"
if _uv_py.exists() and str(sys.executable) != str(_uv_py):
    os.execv(str(_uv_py), [str(_uv_py), *sys.argv])

ROOT_DIR = Path(__file__).resolve().parents[2]
WF_DIR = Path(__file__).resolve().parent
COLAB_BIN = str(Path.home() / ".local" / "bin" / "colab")
# Unique per run (including PID so parallel workers launched in the same second never collide).
SESSION_NAME = os.environ.get("RAP_G4_SESSION") or f"rap-g4-{time.strftime('%m%d-%H%M%S')}-{os.getpid() % 10000:04d}"
STATE_LOCK_FILE = Path("/tmp/rap_colab_cli_state.lock")


@contextmanager
def local_state_lock():
    """Serialize local colab-cli state.json / session_tracker.json / picks.json updates across parallel workers."""
    STATE_LOCK_FILE.touch(exist_ok=True)
    with STATE_LOCK_FILE.open("r+") as lf:
        fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lf.fileno(), fcntl.LOCK_UN)


def run_local(cmd: list, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=check, text=True)


def colab_exec_py(session: str, py_code: str, timeout_s: int = 35, retries: int = 3, check: bool = True) -> str:
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as tf:
        tf.write(py_code)
        tmp_path = tf.name
    try:
        for attempt in range(retries):
            full_cmd = ["perl", "-e", f"alarm {timeout_s}; exec @ARGV", COLAB_BIN, "exec", "-s", session, "-f", tmp_path]
            res = subprocess.run(full_cmd, capture_output=True, text=True)
            if res.returncode == 0:
                return res.stdout
            if attempt < retries - 1:
                time.sleep(3)
                continue
            if check:
                raise RuntimeError(f"colab exec failed ({res.returncode}): {res.stderr or res.stdout}")
            return res.stdout
        return ""
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def get_drive_token() -> str:
    store = Path.home() / ".config/colab-cli/dfs_credentials.json"
    cfg = json.loads(store.read_text(encoding="utf-8"))
    now = time.time()
    if cfg.get("access_token") and float(cfg.get("expires_at", 0)) - 180 > now:
        return cfg["access_token"]
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": cfg["refresh_token"],
        "client_id": cfg["client_id"],
    }
    if cfg.get("client_secret"):
        payload["client_secret"] = cfg["client_secret"]
    req = urllib.request.Request(
        cfg.get("token_uri", "https://oauth2.googleapis.com/token"),
        urllib.parse.urlencode(payload).encode("utf-8"),
        {"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.load(resp)
    cfg["access_token"] = data["access_token"]
    cfg["expires_at"] = now + int(data.get("expires_in", 3599))
    try:
        store.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    except Exception:
        pass
    return data["access_token"]


def upload_bundle_to_drive(local_path: Path) -> str:
    """Upload bundle tar.gz via Google Drive v3 resumable upload and return file_id (with proxy TLS retry)."""
    raw_bytes = local_path.read_bytes()
    for attempt in range(4):
        try:
            token = get_drive_token()
            init_req = urllib.request.Request(
                "https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable",
                data=json.dumps({"name": local_path.name}).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json; charset=UTF-8",
                },
                method="POST",
            )
            with urllib.request.urlopen(init_req, timeout=30) as resp:
                upload_url = resp.headers["Location"]

            put_req = urllib.request.Request(
                upload_url,
                data=raw_bytes,
                headers={
                    "Content-Length": str(len(raw_bytes)),
                    "Content-Type": "application/gzip",
                },
                method="PUT",
            )
            with urllib.request.urlopen(put_req, timeout=120) as resp:
                meta = json.loads(resp.read().decode("utf-8"))
            return meta["id"]
        except (urllib.error.URLError, ConnectionError, TimeoutError) as err:
            if attempt == 3:
                raise
            print(f"⚠️ Drive bundle upload TLS retry {attempt + 1}/3 ({err})...", flush=True)
            time.sleep(3 * (attempt + 1))
    raise RuntimeError("Unreachable")


def delete_drive_file(file_id: str | None) -> None:
    if not file_id:
        return
    try:
        token = get_drive_token()
        req = urllib.request.Request(
            f"https://www.googleapis.com/drive/v3/files/{file_id}",
            headers={"Authorization": f"Bearer {token}"},
            method="DELETE",
        )
        urllib.request.urlopen(req, timeout=20)
    except Exception:
        pass


def ensure_g4_and_mount(session: str = SESSION_NAME) -> None:
    check_code = f"""
import json
from colab_cli.common import state
sessions, assignments = state.sync_sessions()
if not assignments and "{session}" in sessions:
    try:
        state.store.remove("{session}")
        sessions.pop("{session}", None)
    except Exception:
        pass
has_session = "{session}" in sessions and bool(getattr(sessions["{session}"], "endpoint", None))
active_names = [f"{{s.session_id}}({{getattr(s, 'accelerator', 'GPU')}})" for s in sessions.values() if getattr(s, "endpoint", None)]
print(json.dumps({{
    "has_session": has_session,
    "assignments": len(assignments),
    "active": active_names,
}}))
"""
    wait_t0 = time.time()
    max_wait_s = int(os.environ.get("RAP_G4_WAIT_TIMEOUT", "3600"))
    while True:
        with local_state_lock():
            r = None
            for _chk_try in range(4):
                r = subprocess.run([sys.executable, "-c", check_code], capture_output=True, text=True)
                if r.returncode == 0 and r.stdout.strip():
                    break
                time.sleep(3 * (_chk_try + 1))
            if r is None or r.returncode != 0:
                raise RuntimeError(f"state.sync_sessions failed: {r.stderr if r else ''}")
            info = json.loads(r.stdout.strip().splitlines()[-1])
            if info["has_session"]:
                print(f"⚡ Reusing active Colab G4 session '{session}'", flush=True)
                break
            if info["assignments"] < 3:
                print(f"🚀 Connecting Colab G4 (96GB Blackwell) session '{session}' (active={info['assignments']}/3)...", flush=True)
                res = subprocess.run([COLAB_BIN, "new", "-s", session, "--gpu", "G4"], capture_output=True, text=True)
                if res.returncode == 0:
                    if res.stdout:
                        print(res.stdout.strip(), flush=True)
                    run_local([sys.executable, str(ROOT_DIR / "scripts" / "colab_meter.py"), "start", "-s", session, "-g", "G4"], check=False)
                    break
                err_msg = (res.stderr or res.stdout or "").strip()
            else:
                res = None
                err_msg = ""
        if info["assignments"] >= 3:
            elapsed = int(time.time() - wait_t0)
            if elapsed > max_wait_s:
                raise RuntimeError(f"Timed out after {elapsed}s waiting for a free G4 slot (active={info['active']})")
            print(f"⏳ [{elapsed}s] {info['assignments']}/3 GPU slots in use ({', '.join(info['active'])}); waiting 30s for a slot to free up (0 CCU)...", flush=True)
            time.sleep(30)
            continue
        elapsed = int(time.time() - wait_t0)
        if elapsed < max_wait_s and any(k in err_msg.lower() for k in ("precondition failed", "allocation refused", "503", "unavailable", "capacity")):
            print(f"⏳ [{elapsed}s] G4 allocation busy ({err_msg.splitlines()[-1] if err_msg else 'retry'}); retrying in 30s (0 CCU)...", flush=True)
            time.sleep(30)
            continue
        raise RuntimeError(f"colab new failed ({res.returncode if res else -1}): {err_msg}")

    for attempt in range(3):
        chk = colab_exec_py(
            session,
            'import os; print("MOUNTED_OK" if os.path.isdir("/content/drive/My Drive") or os.path.isdir("/content/drive/MyDrive") else "NOT_MOUNTED")',
            check=False,
        )
        if "MOUNTED_OK" in chk:
            print("✅ Google Drive mounted on G4!", flush=True)
            return
        print(f"📂 Mounting Google Drive via colab-dfs-ext (attempt {attempt+1}/3)...", flush=True)
        subprocess.run([COLAB_BIN, "dfs", "mount", "-s", session], check=False)
        time.sleep(3)

    chk = colab_exec_py(
        session,
        'import os; print("MOUNTED_OK" if os.path.isdir("/content/drive/My Drive") or os.path.isdir("/content/drive/MyDrive") else "NOT_MOUNTED")',
        check=True,
    )
    if "MOUNTED_OK" not in chk:
        raise RuntimeError("Failed to mount /content/drive on G4")


def pull_clips_from_drive(ep_dir: Path, title: str) -> int:
    token = get_drive_token()
    headers = {"Authorization": f"Bearer {token}"}

    def retry(fn, what: str, tries: int = 3):
        # Local proxy occasionally drops TLS mid-handshake (SSLEOFError); the G4 is already released here, so retrying is free.
        for i in range(1, tries + 1):
            try:
                return fn()
            except (urllib.error.URLError, ConnectionError, TimeoutError) as err:
                if i == tries:
                    raise
                print(f"   ⚠️ {what} failed ({err}); retry {i}/{tries - 1} in {3 * i}s", flush=True)
                time.sleep(3 * i)

    def gdrive_list(q: str) -> list:
        url = "https://www.googleapis.com/drive/v3/files?" + urllib.parse.urlencode({
            "q": q,
            "fields": "files(id,name,size,mimeType,modifiedTime)",
            "pageSize": 100,
        })
        req = urllib.request.Request(url, headers=headers)
        return retry(lambda: json.loads(urllib.request.urlopen(req, timeout=30).read().decode())["files"], "Drive list")

    def gdrive_download(file_id: str, dst: Path, timeout: int) -> None:
        tmp = dst.with_name(f"{dst.name}.{os.getpid()}.part")
        req = urllib.request.Request(f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media", headers=headers)

        def _dl():
            with urllib.request.urlopen(req, timeout=timeout) as r, open(tmp, "wb") as f:
                shutil.copyfileobj(r, f)
        retry(_dl, f"Download {dst.name}")
        tmp.replace(dst)

    rb_folders = gdrive_list("name = 'rap_battle' and mimeType = 'application/vnd.google-apps.folder' and trashed = false")
    if not rb_folders:
        raise RuntimeError("Drive folder 'rap_battle' not found")
    rb_id = rb_folders[0]["id"]
    ep_folders = gdrive_list(f"'{rb_id}' in parents and name = '{title}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false")
    if not ep_folders:
        raise RuntimeError(f"Drive folder 'rap_battle/{title}' not found")
    ep_id = ep_folders[0]["id"]

    for jf in gdrive_list(f"'{ep_id}' in parents and trashed = false"):
        if jf["name"] in ("picks.json", "shifts.json"):
            dst_j = ep_dir / "work" / jf["name"]
            tmp_j = ep_dir / "work" / f".{jf['name']}.{os.getpid()}.tmp"
            gdrive_download(jf["id"], tmp_j, timeout=60)
            try:
                remote_d = json.loads(tmp_j.read_text(encoding="utf-8"))
                with local_state_lock():
                    local_d = json.loads(dst_j.read_text(encoding="utf-8")) if dst_j.exists() else {}
                    merged = {**local_d, **remote_d}
                    dst_j.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")
            finally:
                tmp_j.unlink(missing_ok=True)

    clip_folders = gdrive_list(f"'{ep_id}' in parents and name = 'clips' and mimeType = 'application/vnd.google-apps.folder' and trashed = false")
    if not clip_folders:
        raise RuntimeError(f"Drive folder 'rap_battle/{title}/clips' not found")
    clips_id = clip_folders[0]["id"]

    local_clips = ep_dir / "clips"
    local_clips.mkdir(parents=True, exist_ok=True)
    files = gdrive_list(f"'{clips_id}' in parents and trashed = false")
    count = 0
    for fmeta in sorted(files, key=lambda x: x["name"]):
        if not fmeta["name"].endswith(".mp4"):
            continue
        dst = local_clips / fmeta["name"]
        if dst.exists() and str(dst.stat().st_size) == str(fmeta.get("size")):
            continue  # already pulled by an earlier run
        if dst.exists() and fmeta.get("modifiedTime"):
            # a local take swapped in by hand (e.g. a sample promoted to _t1) is newer than the stale Drive copy:
            # never let an old upload overwrite it
            from datetime import datetime
            drive_t = datetime.fromisoformat(fmeta["modifiedTime"].replace("Z", "+00:00")).timestamp()
            if dst.stat().st_mtime >= drive_t:
                print(f"   ⏭️ Kept local {dst.name} (newer than the Drive copy)", flush=True)
                continue
        gdrive_download(fmeta["id"], dst, timeout=120)
        count += 1
        print(f"   ⬇️ Pulled {dst.name} ({dst.stat().st_size / 1048576:.2f} MB)", flush=True)

    # Parallel-worker safeguard: ensure every pulled <cid>_t1.mp4 is registered in local picks.json
    with local_state_lock():
        picks_f = ep_dir / "work" / "picks.json"
        picks_d = json.loads(picks_f.read_text(encoding="utf-8")) if picks_f.exists() else {}
        changed = False
        for mp4 in sorted(local_clips.glob("*_t1.mp4")):
            cid = mp4.name[:-7]
            if cid and cid not in picks_d:
                picks_d[cid] = 1
                changed = True
        if changed:
            picks_f.write_text(json.dumps(picks_d, indent=2, ensure_ascii=False), encoding="utf-8")
    return count


def main():
    global SESSION_NAME
    ap = argparse.ArgumentParser()
    ap.add_argument("ep", nargs="+", help="Path(s) to episode directory")
    ap.add_argument("--steps", type=int, default=8)
    ap.add_argument("--ids", nargs="*", default=None)
    ap.add_argument("--session", default=None, help="Explicit Colab G4 session name (for parallel workers)")
    ap.add_argument("--runner-args", default="", help="Extra args for h3_colab_runner.py, e.g. \"--fit --lock-strength 1.0 --tag lock\"")
    ap.add_argument("--no-post", action="store_true", help="Only pull clips; skip assemble/package/cover (sample runs)")
    args = ap.parse_args()
    if args.session:
        SESSION_NAME = args.session
    runner_extra = shlex.split(args.runner_args)

    ep_dirs = [Path(p).resolve() for p in args.ep]
    titles = [json.loads((d / "episode.json").read_text(encoding="utf-8"))["title"] for d in ep_dirs]

    bundle_tar = Path(f"/tmp/rap_episode_bundle_{SESSION_NAME}.tar.gz")
    with tarfile.open(bundle_tar, "w:gz") as tar:
        for idx, d in enumerate(ep_dirs):
            prefix = f"episode_{idx}"
            tar.add(d / "episode.json", arcname=f"{prefix}/episode.json")
            has_voc_final = (d / "work" / "vocals_final.wav").is_file()
            has_mus_final = (d / "work" / "music_final.wav").is_file()
            for sub in ("refs", "work"):
                for p in (d / sub).glob("*"):
                    if not p.is_file() or p.suffix not in (".png", ".json", ".wav", ".mp3"):
                        continue
                    if sub == "work":
                        if p.name.endswith("_raw_orig.png") or p.suffix == ".mp3":
                            continue
                        if p.suffix == ".wav":
                            keep_wav = "vocals_final.wav" if has_voc_final else ("music_final.wav" if has_mus_final else p.name)
                            if p.name != keep_wav:
                                continue
                    tar.add(p, arcname=f"{prefix}/{sub}/{p.name}")
        for s_py in ("common.py", "qa.py", "h3_colab_runner.py"):
            tar.add(WF_DIR / "scripts" / s_py, arcname=f"scripts/{s_py}")

    print(f"📦 Packed {len(ep_dirs)} episode bundle(s) -> {bundle_tar} ({bundle_tar.stat().st_size / 1048576:.2f} MB)", flush=True)
    bundle_file_id = None

    try:
        drive_token = get_drive_token()
        bundle_file_id = upload_bundle_to_drive(bundle_tar)
        print(f"☁️ Staged bundle to Google Drive (file_id={bundle_file_id})", flush=True)
        launcher_b64 = base64.b64encode((ROOT_DIR / "scripts" / "launch_g4_comfyui_fast.py").read_bytes()).decode("ascii")

        print("\n🚀 [Step 1/4] Starting Colab G4 & mounting Google Drive...", flush=True)
        ensure_g4_and_mount(SESSION_NAME)

        print("\n📤 [Step 2/4] Pulling episode bundle onto G4 local NVMe & launching runner...", flush=True)
        ids_list = args.ids if args.ids else []
        launch_py = f"""
import base64, json, os, shutil, subprocess, sys, tarfile, urllib.request
from pathlib import Path

Path("/tmp/launch_g4_comfyui_fast.py").write_bytes(base64.b64decode("{launcher_b64}"))

dl_req = urllib.request.Request(
    "https://www.googleapis.com/drive/v3/files/{bundle_file_id}?alt=media",
    headers={{"Authorization": "Bearer {drive_token}"}}
)
with urllib.request.urlopen(dl_req, timeout=60) as r, open("/tmp/rap_episode_bundle.tar.gz", "wb") as f:
    shutil.copyfileobj(r, f)

job_dir = Path("/tmp/rap_job")
if job_dir.exists():
    shutil.rmtree(job_dir)
job_dir.mkdir(parents=True, exist_ok=True)
with tarfile.open("/tmp/rap_episode_bundle.tar.gz", "r:gz") as tar:
    tar.extractall(job_dir)

Path("/tmp/rap_job_done.flag").unlink(missing_ok=True)
Path("/tmp/rap_job_err.flag").unlink(missing_ok=True)

wrapper = '''import subprocess, sys
from pathlib import Path
rc = 0
for idx in range({len(ep_dirs)}):
    cmd = [sys.executable, "-u", "/tmp/rap_job/scripts/h3_colab_runner.py", f"/tmp/rap_job/episode_{{idx}}", "--steps", "{args.steps}"]
    ids = {json.dumps(ids_list)}
    if ids:
        cmd.extend(["--ids"] + ids)
    cmd.extend({json.dumps(runner_extra)})
    p = subprocess.run(cmd)
    if p.returncode != 0:
        rc = p.returncode
        break
subprocess.run(["sync"])
if rc == 0:
    Path("/tmp/rap_job_done.flag").write_text("OK")
else:
    Path("/tmp/rap_job_err.flag").write_text(str(rc))
'''
Path("/tmp/run_rap_wrapper.py").write_text(wrapper)
subprocess.Popen("nohup python3 -u /tmp/run_rap_wrapper.py > /tmp/rap_battle_run.log 2>&1 < /dev/null &", shell=True)
print("LAUNCHED_RAP_RUNNER_OK")
"""
        print(f"\n🎬 [Step 3/4] Launching h3_colab_runner.py on G4 (steps={args.steps}, episodes={len(ep_dirs)})...", flush=True)
        out = colab_exec_py(SESSION_NAME, launch_py, timeout_s=45)
        if "LAUNCHED_RAP_RUNNER_OK" not in out:
            raise RuntimeError(f"Failed to launch h3_colab_runner.py: {out}")

        t0 = time.time()
        poll_py = """
import json
from pathlib import Path
log_txt = Path("/tmp/rap_battle_run.log").read_text(errors="ignore") if Path("/tmp/rap_battle_run.log").exists() else ""
state = "DONE" if Path("/tmp/rap_job_done.flag").exists() else ("ERR" if Path("/tmp/rap_job_err.flag").exists() else "RUNNING")
print("POLL_JSON:" + json.dumps({"state": state, "tail": log_txt.splitlines()[-8:]}))
"""
        consec_err = 0
        while True:
            time.sleep(15)
            p_out = colab_exec_py(SESSION_NAME, poll_py, timeout_s=30, check=False)
            if "POLL_JSON:" not in p_out:
                consec_err += 1
                print(f"⚠️ [Poll transient warning #{consec_err}]", flush=True)
                # ~5 min of failed polls: long batches survived a 90 s local proxy blip badly (G4 keeps rendering
                # and syncing clips to Drive meanwhile, so waiting costs little and a resume is cheap)
                if consec_err >= 20:
                    raise RuntimeError("Lost connection to G4 during polling")
                continue
            consec_err = 0
            data = json.loads(p_out.split("POLL_JSON:", 1)[1].splitlines()[0])
            tail_str = "\n".join("   " + l for l in data["tail"][-5:])
            print(f"⏱️ [{int(time.time() - t0)}s | {data['state']}]\n{tail_str}", flush=True)
            if data["state"] == "DONE":
                break
            if data["state"] == "ERR":
                err_tail = "\n".join(data["tail"])
                raise RuntimeError(f"h3_colab_runner.py exited with error:\n{err_tail}")

        flush_py = """
import subprocess, time
subprocess.run(["sync"])
time.sleep(4)
print("DRIVE_SYNC_OK")
"""
        colab_exec_py(SESSION_NAME, flush_py, timeout_s=30, check=False)
    finally:
        bundle_tar.unlink(missing_ok=True)
        delete_drive_file(bundle_file_id)
        print("\n🛑 [Step 4/4] Immediately stopping Colab G4 instance to stop CCU burn...", flush=True)
        with local_state_lock():
            subprocess.run([COLAB_BIN, "stop", "-s", SESSION_NAME], check=False)
            time.sleep(2)
            run_local([sys.executable, str(ROOT_DIR / "scripts" / "colab_meter.py"), "stop", "-s", SESSION_NAME], check=False)

    print("\n⬇️ [0-CCU Post-Processing] Pulling rendered clips from Google Drive & packaging final video...", flush=True)
    for ep_dir, title in zip(ep_dirs, titles):
        pull_clips_from_drive(ep_dir, title)
    if args.no_post:
        print("✅ --no-post: clips pulled, skipping assemble/package.", flush=True)
        return
    local_py = shutil.which("python3") or "/opt/homebrew/bin/python3"
    for ep_dir, title in zip(ep_dirs, titles):
        ep_cfg = json.loads((ep_dir / "episode.json").read_text(encoding="utf-8"))
        use_film = bool(ep_cfg.get("film_look") or "--realism-v2" in runner_extra)
        if use_film:
            run_local([local_py, str(WF_DIR / "scripts" / "assemble.py"), str(ep_dir), "--film", "--out", "preview/草稿_胶片母带.mp4"])
            run_local([local_py, str(WF_DIR / "scripts" / "package.py"), str(ep_dir), "--src", "preview/草稿_胶片母带.mp4", "--film", "--1080p", "--phone"])
            out_file = ep_dir / "final" / f"{title}_1080p_胶片版.mp4"
        else:
            run_local([local_py, str(WF_DIR / "scripts" / "assemble.py"), str(ep_dir)])
            run_local([local_py, str(WF_DIR / "scripts" / "package.py"), str(ep_dir), "--phone"])
            out_file = ep_dir / "final" / f"{title}_成片.mp4"
        faceoff_png = ep_dir / "cover" / "faceoff_frame.png"
        if faceoff_png.exists():
            run_local([local_py, str(WF_DIR / "scripts" / "cover.py"), str(ep_dir), "--frame", str(faceoff_png), "--no-mirror"])
        print(f"\n🎉 Done! Final packaged video: {out_file}", flush=True)


if __name__ == "__main__":
    main()
