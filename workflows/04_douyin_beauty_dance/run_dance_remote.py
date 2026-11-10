#!/usr/bin/env python3
"""Local Remote Controller for Workflow 04: 9:16 Vertical Douyin Beauty Dance + Tessera 2K Refinement on Colab G4 (96GB Blackwell).

Follows Colab Ultra Workstation Zero-Burn SOP (Iron Rules A ~ G):
1. Local 0-CCU prep & OAuth check (`colab login` + `colab dfs consent`).
2. Dual-Track CCU Meter (`colab_meter.py start` / `stop`).
3. Silent browser-free 20TB/30TB Google Drive mount (`colab dfs mount`).
4. Chunked base64 staging of scripts & missing sample assets to `/tmp/`.
5. Detached `nohup` execution + `alarm 25` timeout polling (Iron Rule C).
6. Drive verification (`size > 0`), local MP4 pull-back, and automatic G4 teardown (`0.00 CCU/h`).
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

try:
    import colab_cli  # noqa: F401
except ImportError:
    _uv_py = Path.home() / ".local/share/uv/tools/google-colab-cli/bin/python"
    if _uv_py.exists() and str(sys.executable) != str(_uv_py):
        os.execv(str(_uv_py), [str(_uv_py), *sys.argv])

WORKFLOW_DIR = Path(__file__).resolve().parent
REPO_ROOT = WORKFLOW_DIR.parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
LOCAL_OUT_DIR = WORKFLOW_DIR / "outputs"
COLAB_BIN = str(Path.home() / ".local/bin/colab")
COLAB_PY = str(Path.home() / ".local/share/uv/tools/google-colab-cli/bin/python")
CONFIG_DIR = Path.home() / ".config/colab-cli"


def build_env() -> dict[str, str]:
    env = dict(os.environ)
    env["no_proxy"] = "localhost,127.0.0.1"
    env["NO_PROXY"] = "localhost,127.0.0.1"
    return env


ENV = build_env()


def has_valid_drive_scope() -> bool:
    dfs_cred = CONFIG_DIR / "dfs_credentials.json"
    if not dfs_cred.exists():
        return False
    try:
        data = json.loads(dfs_cred.read_text(encoding="utf-8"))
        scopes = data.get("scopes", [])
        return bool(data.get("refresh_token")) and any("auth/drive" in s for s in scopes)
    except Exception:
        return False


def ensure_local_oauth(session_to_pause: str = "dance-g4") -> None:
    """Ensure both colab-cli OAuth and colab-dfs-ext OAuth (with drive scope!) are completed at 0 CCU."""
    try:
        from colab_cli.common import state
        state.sync_sessions()
    except Exception as exc:
        print(f"🔐 检测到 colab CLI 尚未登录 ({exc})，正在打开浏览器进行首次 OAuth 登录...", flush=True)
        r = subprocess.run([COLAB_BIN, "auth", "login"], env=ENV)
        if r.returncode != 0:
            subprocess.run([COLAB_BIN, "usage"], check=True, env=ENV)

    if not has_valid_drive_scope():
        # Zero-Burn Guard: never leave a G4 session burning CCU while waiting for human browser consent!
        try:
            from colab_cli.common import state
            _, assignments = state.sync_sessions()
            if assignments:
                print("🛡️ [防烧钱守门员] 检测到 Drive 授权尚未完成但存在运行中实例，先暂停释放实例以确保等待人工勾选期间 0 CCU 消耗...", flush=True)
                subprocess.run([COLAB_PY, str(SCRIPTS_DIR / "colab_meter.py"), "stop", "-s", session_to_pause], check=False, env=ENV)
        except Exception:
            pass

        while not has_valid_drive_scope():
            print(
                "\n🚨 检测到 Google Drive 权限未勾选（缺少 https://www.googleapis.com/auth/drive 权限）！\n"
                "👉 在浏览器弹出的 Google 授权页中，【查看、编辑、创建和删除您的所有 Google 云端硬盘文件】复选框默认是未勾选的，请务必【手动打勾 ✅】后再点击继续！\n",
                flush=True,
            )
            dfs_creds_py = Path.home() / ".colab-dfs-ext/colab_dfs_ext/dfs_creds.py"
            if dfs_creds_py.exists():
                subprocess.run(
                    [
                        COLAB_PY,
                        str(dfs_creds_py),
                        "consent",
                        "--flavor",
                        "dfs",
                        "--scopes",
                        "https://www.googleapis.com/auth/drive",
                    ]
                    # account hints are optional and stay out of the repo: export COLAB_DFS_USER_ID / COLAB_DFS_EMAIL locally
                    + (["--user-id", os.environ["COLAB_DFS_USER_ID"]] if os.environ.get("COLAB_DFS_USER_ID") else [])
                    + (["--email", os.environ["COLAB_DFS_EMAIL"]] if os.environ.get("COLAB_DFS_EMAIL") else []),
                    check=True,
                    env=ENV,
                )
            else:
                subprocess.run([COLAB_BIN, "dfs", "consent"], check=True, env=ENV)
        print("✅ 已验证 Token 包含完整 Google Drive (https://www.googleapis.com/auth/drive) 权限！", flush=True)


def colab_exec_short(session: str, py_code: str, timeout_sec: int = 30, check: bool = False, retries: int = 3) -> str:
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as tf:
        tf.write(py_code)
        tmp_path = tf.name
    try:
        for attempt in range(retries):
            cmd = ["perl", "-e", f"alarm {timeout_sec}; exec @ARGV", COLAB_BIN, "exec", "-s", session, "-f", tmp_path]
            r = subprocess.run(cmd, text=True, capture_output=True, env=ENV)
            if r.returncode == 0:
                return r.stdout
            if attempt < retries - 1:
                time.sleep(2.5)
                continue
            if check:
                raise RuntimeError(f"❌ colab exec 失败 (exit={r.returncode}):\n{r.stderr}\n{r.stdout}")
            if r.stderr:
                print(f"⚠️ [colab exec] {r.stderr.strip()[-300:]}", flush=True)
        return r.stdout
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def mount_drive_with_retry(session_name: str, retries: int = 3) -> None:
    for i in range(retries):
        chk = colab_exec_short(
            session_name,
            'import os; print("MOUNTED_OK" if os.path.isdir("/content/drive/My Drive") or os.path.isdir("/content/drive/MyDrive") else "NOT_MOUNTED")',
        )
        if "MOUNTED_OK" in chk:
            print("✅ Google Drive 已挂载就绪！", flush=True)
            return
        print(f"📂 正在零浏览器静默挂载 Google Drive (尝试 {i+1}/{retries})...", flush=True)
        r = subprocess.run([COLAB_BIN, "dfs", "mount", "-s", session_name], env=ENV)
        if r.returncode == 0:
            return
        time.sleep(3)
    raise RuntimeError("❌ Google Drive 挂载失败")


def ensure_g4_session(session_name: str = "dance-g4") -> str:
    from colab_cli.common import state

    sessions, assignments = state.sync_sessions()
    if assignments:
        active_ep = assignments[0].endpoint
        matched = [s.name for s in sessions.values() if getattr(s, "endpoint", None) == active_ep]
        sname = matched[0] if matched else session_name
        print(f"⚡ 复用已开启的云端实例: {sname} ({active_ep})", flush=True)
        subprocess.run([COLAB_PY, str(SCRIPTS_DIR / "colab_meter.py"), "start", "-s", sname, "-g", "G4"], check=False, env=ENV)
        mount_drive_with_retry(sname)
        return sname

    print(f"🚀 正在启动 Colab G4 (96GB RTX PRO 6000 Blackwell, 10.05 CCU/h) 实例 [{session_name}]...", flush=True)
    subprocess.run([COLAB_PY, str(SCRIPTS_DIR / "colab_meter.py"), "start", "-s", session_name, "-g", "G4"], check=False, env=ENV)
    subprocess.run([COLAB_BIN, "new", "-s", session_name, "--gpu", "G4"], check=True, env=ENV)
    mount_drive_with_retry(session_name)
    return session_name


def upload_file_chunked(session: str, local_path: Path, remote_path: str, chunk_bytes: int = 384 * 1024) -> None:
    raw = local_path.read_bytes()
    total = len(raw)
    if total <= chunk_bytes:
        b64 = base64.b64encode(raw).decode("ascii")
        code = (
            f"import base64; from pathlib import Path; "
            f"p = Path({json.dumps(remote_path)}); p.parent.mkdir(parents=True, exist_ok=True); "
            f"p.write_bytes(base64.b64decode('{b64}')); print('UPLOAD_OK', p.stat().st_size)"
        )
        colab_exec_short(session, code, timeout_sec=30, check=True)
        return

    colab_exec_short(
        session,
        f"from pathlib import Path; p = Path({json.dumps(remote_path)}); p.parent.mkdir(parents=True, exist_ok=True); p.unlink(missing_ok=True)",
        timeout_sec=20,
        check=True,
    )
    for offset in range(0, total, chunk_bytes):
        chunk = raw[offset : offset + chunk_bytes]
        b64 = base64.b64encode(chunk).decode("ascii")
        code = (
            f"import base64; from pathlib import Path; "
            f"p = Path({json.dumps(remote_path)}); "
            f"f = p.open('ab'); f.write(base64.b64decode('{b64}')); f.close(); "
            f"print('CHUNK_OK', p.stat().st_size)"
        )
        colab_exec_short(session, code, timeout_sec=35, check=True)
    print(f"📤 已上传至云端 {remote_path} ({total / 1024:.1f} KB)", flush=True)


def stage_scripts_and_inputs(session: str) -> None:
    print("📦 正在同步最新引擎脚本与工作流配置至云端 /tmp/ ...", flush=True)
    text_files = [
        (SCRIPTS_DIR / "launch_g4_comfyui_fast.py", "/tmp/launch_g4_comfyui_fast.py"),
        (WORKFLOW_DIR / "run_dance.py", "/tmp/run_dance.py"),
        (WORKFLOW_DIR / "run_tessera_2k.py", "/tmp/run_tessera_2k.py"),
        (WORKFLOW_DIR / "dance_config.json", "/tmp/dance_config.json"),
        (WORKFLOW_DIR / "workflow_douyin_dance_2seg.json", "/tmp/workflow_douyin_dance_2seg.json"),
        (WORKFLOW_DIR / "workflow_tessera_2k_refine.json", "/tmp/workflow_tessera_2k_refine.json"),
    ]
    for src, dst in text_files:
        upload_file_chunked(session, src, dst)

    sample_files = [
        "ref_realgirl_v3_2k.png",
        "ref_realgirl_v3_closeup_9x16.png",
        "master_bgm_15s.wav",
        "seg01_bgm_8s.wav",
        "seg02_bgm_8s.wav",
    ]
    check_py = f"""
import json, os, shutil
from pathlib import Path
if os.path.isdir("/content/drive/My Drive") and not os.path.exists("/content/drive/MyDrive"):
    os.symlink("/content/drive/My Drive", "/content/drive/MyDrive")
drv_in = Path("/content/drive/MyDrive/AI_Workstation/ComfyUI/input")
missing = []
for fn in {json.dumps(sample_files)}:
    t = Path("/tmp") / fn
    d = drv_in / fn
    if t.exists() and t.stat().st_size > 1000:
        continue
    if d.exists() and d.stat().st_size > 1000:
        shutil.copy2(d, t)
        continue
    missing.append(fn)
print("MISSING_JSON:" + json.dumps(missing))
"""
    out = colab_exec_short(session, check_py, timeout_sec=25, check=True)
    missing = json.loads(out.split("MISSING_JSON:", 1)[1].splitlines()[0]) if "MISSING_JSON:" in out else sample_files
    for fn in missing:
        local_f = WORKFLOW_DIR / "sample_inputs" / fn
        if local_f.exists():
            upload_file_chunked(session, local_f, f"/tmp/{fn}")


def run_detached_pipeline(session: str, run_stage2_tessera: bool = True, tessera_profile: str = "g4_optimal") -> None:
    launch_py = f"""
import subprocess, sys
from pathlib import Path

for flag in ("/tmp/dance_job_done.flag", "/tmp/dance_job_err.flag"):
    Path(flag).unlink(missing_ok=True)

runner_code = '''import subprocess, sys
from pathlib import Path

cmds = [
    [sys.executable, "-u", "/tmp/run_dance.py", "--config", "/tmp/dance_config.json", "--workflow", "/tmp/workflow_douyin_dance_2seg.json"],
]
if {repr(run_stage2_tessera)}:
    cmds.append([sys.executable, "-u", "/tmp/run_tessera_2k.py", "--profile", {repr(tessera_profile)}])

for c in cmds:
    print("==================================================================", flush=True)
    print("🚀 Running:", " ".join(c), flush=True)
    print("==================================================================", flush=True)
    p = subprocess.run(c)
    if p.returncode != 0:
        Path("/tmp/dance_job_err.flag").write_text(str(p.returncode))
        sys.exit(p.returncode)

Path("/tmp/dance_job_done.flag").write_text("OK")
'''
Path("/tmp/run_dance_job.py").write_text(runner_code)
subprocess.Popen("nohup python3 -u /tmp/run_dance_job.py > /tmp/dance_job.log 2>&1 &", shell=True)
print("LAUNCHED_DETACHED_OK")
"""
    out = colab_exec_short(session, launch_py, timeout_sec=25, check=True)
    if "LAUNCHED_DETACHED_OK" not in out:
        raise RuntimeError(f"❌ 远端脱机启动失败:\n{out}")
    print("🎬 云端 MiniMax-H3 工作流 04 (Stage 1 原生热舞 + Stage 2 Tessera 2K 精修) 已脱机启动！", flush=True)

    t0 = time.time()
    last_lines: list[str] = []
    consec_failures = 0
    for _ in range(360):  # up to 48 minutes (8s * 360)
        time.sleep(8)
        poll_py = """
import json
from pathlib import Path
job_txt = Path("/tmp/dance_job.log").read_text(errors="ignore") if Path("/tmp/dance_job.log").exists() else ""
state = "DONE" if Path("/tmp/dance_job_done.flag").exists() else ("ERR" if Path("/tmp/dance_job_err.flag").exists() else "RUNNING")
tail = [l.strip() for l in job_txt.splitlines() if l.strip()][-4:]
print("POLL_JSON:" + json.dumps({"state": state, "tail": tail}))
"""
        p_out = colab_exec_short(session, poll_py, timeout_sec=25)
        if "POLL_JSON:" not in p_out:
            consec_failures += 1
            if consec_failures >= 6:
                raise RuntimeError("❌ 连续 6 次轮询超时未响应，中止以防卡死。")
            continue
        consec_failures = 0
        data = json.loads(p_out.split("POLL_JSON:", 1)[1].splitlines()[0])
        tail = data["tail"]
        if tail != last_lines:
            print(f"  [{int(time.time() - t0)}s] " + " | ".join(tail[-2:]), flush=True)
            last_lines = tail
        if data["state"] == "DONE":
            print(f"\n✅ 云端渲染全部完成！总耗时: {time.time() - t0:.1f}s", flush=True)
            for ln in tail:
                print("  " + ln, flush=True)
            return
        if data["state"] == "ERR":
            err_dump = colab_exec_short(
                session,
                'from pathlib import Path\n'
                'for p in ("/tmp/dance_job.log", "/tmp/comfyui.log", "/tmp/comfyui_tessera.log"):\n'
                '    if Path(p).exists(): print(f"=== {p} ===\\n" + Path(p).read_text(errors="ignore")[-2500:])',
                timeout_sec=30,
            )
            raise RuntimeError(f"❌ 云端渲染任务报错:\n{err_dump}")
    raise TimeoutError("❌ 超过最大轮询等待时间")


def pull_outputs_from_drive_api() -> list[Path]:
    """Pull generated MP4 files directly from Google Drive v3 API at 0.00 CCU/h."""
    import urllib.parse
    import urllib.request

    LOCAL_OUT_DIR.mkdir(parents=True, exist_ok=True)
    tok_out = subprocess.check_output([COLAB_BIN, "dfs", "token"], text=True, env=ENV)
    tok = json.loads(tok_out)["access_token"]
    params = urllib.parse.urlencode(
        {
            "q": "trashed = false and name contains 'DouyinDance' and name contains '.mp4'",
            "fields": "files(id,name,size)",
            "pageSize": 30,
        }
    )
    req = urllib.request.Request(
        f"https://www.googleapis.com/drive/v3/files?{params}",
        headers={"Authorization": f"Bearer {tok}"},
    )
    files = json.loads(urllib.request.urlopen(req, timeout=15).read().decode()).get("files", [])
    downloaded: list[Path] = []
    for f in files:
        if int(f.get("size", 0)) <= 10_000:
            continue
        dst = LOCAL_OUT_DIR / f["name"]
        dl_req = urllib.request.Request(
            f"https://www.googleapis.com/drive/v3/files/{f['id']}?alt=media",
            headers={"Authorization": f"Bearer {tok}"},
        )
        with urllib.request.urlopen(dl_req, timeout=90) as resp:
            dst.write_bytes(resp.read())
        print(f"📥 [Drive API 0-CCU] 已回传成片至本地: {dst} ({dst.stat().st_size / (1024**2):.2f} MB)", flush=True)
        downloaded.append(dst)
    return downloaded


def main() -> None:
    parser = argparse.ArgumentParser(description="Remote G4 Runner for Workflow 04 Douyin Beauty Dance")
    parser.add_argument("-s", "--session", default="dance-g4", help="Colab session name")
    parser.add_argument("--skip-tessera-2k", action="store_true", help="Run only Stage 1 (768x1344) without Stage 2 Tessera 2K refinement")
    parser.add_argument("--tessera-profile", default="g4_optimal", choices=["g4_optimal", "g4_fast_face"], help="Stage 2 Tessera profile")
    parser.add_argument("--keep-alive", action="store_true", help="Do not unassign G4 instance after completion")
    args = parser.parse_args()

    ensure_local_oauth(session_to_pause=args.session)
    sname = args.session
    try:
        sname = ensure_g4_session(args.session)
        stage_scripts_and_inputs(sname)
        run_detached_pipeline(sname, run_stage2_tessera=not args.skip_tessera_2k, tessera_profile=args.tessera_profile)
    finally:
        if not args.keep_alive:
            print("🛑 任务结束，正在释放 G4 实例并生成双轨 CCU 计费核验报告...", flush=True)
            subprocess.run([COLAB_PY, str(SCRIPTS_DIR / "colab_meter.py"), "stop", "-s", sname], check=False, env=ENV)
        try:
            pull_outputs_from_drive_api()
        except Exception as exc:
            print(f"⚠️ 从 Google Drive 拉取视频跳过: {exc}", flush=True)


if __name__ == "__main__":
    main()
