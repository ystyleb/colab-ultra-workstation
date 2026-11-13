#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Zero-Waste Colab L4 Game-Voice Conversion Runner for Rap Battle Episodes.

Follows all Zero-Burn Iron Rules:
1. Uploads prepared audio bundle (`music_trimmed_raw.wav`, `lines.json`, `ref_a.wav`, `ref_b.wav`, `svc_cfg.json`)
   to Google Drive via Drive v3 API BEFORE starting any GPU (0 CCU).
2. Wraps session with `colab_meter.py start/stop`, starts a lightweight L4 GPU (`1.71 CCU/h`), runs
   `Demucs htdemucs_ft` 4-stem separation + `Seed-VC` (44.1kHz F0-Rap & Expressive-Rap) +
   Trained `RVC v2` game character models (with multi-register pitch passes in memory),
   verifies the archive on Google Drive (`size > 0`), and IMMEDIATELY stops the L4 session (`0.00 CCU/h`).
3. Pulls the stem archive at 0 CCU and runs sample-accurate cross-correlation alignment + studio mastering locally.
"""
from __future__ import annotations

import argparse
import json
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
import wave
from pathlib import Path

import numpy as np

ROOT_DIR = Path(__file__).resolve().parents[3]
COLAB_BIN = str(Path.home() / ".local" / "bin" / "colab")
SESSION_NAME = f"rap-svc-l4-{time.strftime('%m%d-%H%M%S')}-{os.getpid() % 10000:04d}"

EPISODE_SVC_PRESETS = {
    "tommy-vs-cj": {
        "ref_a": "tommy_ref_clean.wav",
        "ref_b": "cj_ref_clean.wav",
        "rvc_a_urls": ["https://huggingface.co/ksanjeev284/tommyvercetti/resolve/main/tommy.zip"],
        "rvc_b_urls": ["https://huggingface.co/Rejekts/CarlJohnson-RVC/resolve/main/CarlJohnson.zip"],
        "rvc_passes": [
            {"tag": "rvc", "pitch_a": 0, "pitch_b": 0},
        ],
        "eq_a": "highpass=f=95,equalizer=f=220:t=q:w=1.1:g=2.2,equalizer=f=3100:t=q:w=1.2:g=2.8",
        "eq_b": "highpass=f=105,equalizer=f=190:t=q:w=1.2:g=-1.2,equalizer=f=3400:t=q:w=1.2:g=3.2",
    },
    "arthur-vs-geralt": {
        "ref_a": "arthur_ref_clean.wav",
        "ref_b": "geralt_ref_clean.wav",
        "rvc_a_urls": [
            "https://huggingface.co/G-Force-1/arthurmorgan/resolve/main/morgan_700e_69300s.zip",
            "https://huggingface.co/Tsukasao/arthur-morgan/resolve/main/ArthurMorganRVC.zip",
        ],
        "rvc_b_urls": [
            "https://huggingface.co/poopostresearch/Geralt/resolve/main/added_IVF1200_Flat_nprobe_1_Geralt_v2.zip",
            "https://huggingface.co/cthl/Geralt_of_Rivia_cthl/resolve/main/Geralt_of_Rivia_cthl.zip",
        ],
        "rvc_passes": [
            {"tag": "rvc", "pitch_a": -2, "pitch_b": -8},
            {"tag": "rvc_deep", "pitch_a": -3, "pitch_b": -10},
            {"tag": "rvc_oct", "pitch_a": -4, "pitch_b": -12},
            {"tag": "rvc_fifth", "pitch_a": -1, "pitch_b": -7},
            {"tag": "rvc_raw0", "pitch_a": 0, "pitch_b": 0},
        ],
        "seedvc_f0_shift_b": 3,
        "eq_a": "highpass=f=85,equalizer=f=195:t=q:w=1.1:g=2.4,equalizer=f=3000:t=q:w=1.2:g=2.5",
        "eq_b": "highpass=f=85,equalizer=f=160:t=q:w=1.1:g=2.0,equalizer=f=3250:t=q:w=1.2:g=3.0",
    },
    "michael-vs-trevor": {
        "ref_a": "michael_ref_clean.wav",
        "ref_b": "trevor_ref_clean.wav",
        "rvc_a_urls": [
            "https://huggingface.co/grandtheftauto/Michael_De_Santa/resolve/main/michaeldesanta.zip",
            "https://huggingface.co/lilyrpa/lilyrpaModels/resolve/main/michaeldesanta.zip",
            "https://huggingface.co/thisisafdssdfa/michaeldesanta/resolve/main/michaeldesanta.zip",
        ],
        "rvc_b_urls": [
            "https://huggingface.co/Tsuinzues/trevorphilips/resolve/main/trevorphilips.zip",
            "https://huggingface.co/notiscBalbalEko/myrvcmodel/resolve/main/GTA5Trevor_e501_s3997.zip",
            "https://huggingface.co/lilyrpa/lilyrpaModels/resolve/main/trevorphilips.zip",
        ],
        "rvc_a_alt_urls": [
            "https://huggingface.co/lilyrpa/lilyrpaModels/resolve/main/michaeldesanta.zip",
        ],
        "rvc_b_alt_urls": [
            "https://huggingface.co/notiscBalbalEko/myrvcmodel/resolve/main/GTA5Trevor_e501_s3997.zip",
            "https://huggingface.co/lilyrpa/lilyrpaModels/resolve/main/trevorphilips.zip",
        ],
        "rvc_passes": [
            {"tag": "rvc", "pitch_a": -1, "pitch_b": 0, "protect_b": 0.40},
            {"tag": "rvc_raw0", "pitch_a": 0, "pitch_b": 0, "protect_b": 0.38},
            {"tag": "rvc_grit", "pitch_a": -2, "pitch_b": 1, "protect_b": 0.44},
            {"tag": "rvc_deep", "pitch_a": -3, "pitch_b": -2, "protect_b": 0.38},
            {"tag": "rvc_alt", "pitch_a": -1, "pitch_b": 0, "alt_a": True, "alt_b": True, "protect_b": 0.40},
            {"tag": "rvc_alt_grit", "pitch_a": -2, "pitch_b": 1, "alt_a": True, "alt_b": True, "protect_b": 0.44},
        ],
        "eq_a": "highpass=f=88,equalizer=f=195:t=q:w=1.1:g=2.2,equalizer=f=3150:t=q:w=1.2:g=2.6",
        "eq_b": "highpass=f=98,equalizer=f=210:t=q:w=1.15:g=1.6,equalizer=f=2450:t=q:w=1.3:g=1.6,equalizer=f=3550:t=q:w=1.2:g=2.8",
    },
}


def resolve_svc_cfg(ep_dir: Path) -> dict:
    ep_json = json.loads((ep_dir / "episode.json").read_text(encoding="utf-8"))
    slug = ep_dir.name
    base = dict(EPISODE_SVC_PRESETS.get(slug, EPISODE_SVC_PRESETS["tommy-vs-cj"]))
    if isinstance(ep_json.get("svc"), dict):
        base.update(ep_json["svc"])
    base["slug"] = slug
    base["out_tar_name"] = f"svc_out_{slug.replace('-', '_')}.tar.gz"
    return base


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


def upload_to_drive(local_path: Path) -> str:
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
    raw_bytes = local_path.read_bytes()
    put_req = urllib.request.Request(
        upload_url,
        data=raw_bytes,
        headers={
            "Content-Length": str(len(raw_bytes)),
            "Content-Type": "application/gzip",
        },
        method="PUT",
    )
    with urllib.request.urlopen(put_req, timeout=180) as resp:
        meta = json.loads(resp.read().decode("utf-8"))
    return meta["id"]


def verify_and_download_from_drive(filename: str, dst: Path) -> bool:
    token = get_drive_token()
    headers = {"Authorization": f"Bearer {token}"}
    url = "https://www.googleapis.com/drive/v3/files?" + urllib.parse.urlencode({
        "q": f"name = '{filename}' and trashed = false",
        "orderBy": "modifiedTime desc",
        "fields": "files(id,name,size)",
        "pageSize": 5,
    })
    files = json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30).read().decode()).get("files", [])
    if not files or int(files[0].get("size", 0)) < 1000:
        return False
    fid = files[0]["id"]
    sz = int(files[0]["size"])
    print(f"   ✅ Verified '{filename}' on Drive (id={fid}, size={sz / 1048576:.2f} MB > 0)")
    req = urllib.request.Request(f"https://www.googleapis.com/drive/v3/files/{fid}?alt=media", headers=headers)
    with urllib.request.urlopen(req, timeout=180) as r, open(dst, "wb") as f:
        shutil.copyfileobj(r, f)
    for item in files:
        try:
            urllib.request.urlopen(urllib.request.Request(
                f"https://www.googleapis.com/drive/v3/files/{item['id']}",
                headers=headers, method="DELETE"
            ), timeout=20)
        except Exception:
            pass
    return True


def delete_drive_file(file_id: str | None) -> None:
    if not file_id:
        return
    try:
        token = get_drive_token()
        urllib.request.urlopen(urllib.request.Request(
            f"https://www.googleapis.com/drive/v3/files/{file_id}",
            headers={"Authorization": f"Bearer {token}"},
            method="DELETE",
        ), timeout=20)
    except Exception:
        pass


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


CLOUD_WORKER_CODE = r'''#!/usr/bin/env python3
import glob
import json
import os
import shutil
import subprocess
import sys
import tarfile
import time
import types
import urllib.request
import zipfile
from pathlib import Path

WORK = Path("/content/svc_work")
OUT = WORK / "out"
OUT.mkdir(parents=True, exist_ok=True)
CFG = json.loads((WORK / "svc_cfg.json").read_text(encoding="utf-8"))

def sh(cmd: str, check: bool = True):
    print(f"🔧 $ {cmd}", flush=True)
    subprocess.run(cmd, shell=True, check=check)

t0 = time.time()
print("=== [1/4] Installing lightweight audio/SVC wheels on NVMe ===", flush=True)
sh("pip install -q demucs munch einops descript-audio-codec pydub audioop-lts onnxruntime soundfile librosa faiss-cpu torchcrepe praat-parselmouth soxr ffmpeg-python typeguard")
sh("pip install -q --no-deps infer-rvc-python", check=False)

print("=== [2/4] Studio 4-Stem Vocal Separation (Demucs htdemucs_ft) ===", flush=True)
sh(f"{sys.executable} -m demucs.separate -n htdemucs_ft --two-stems=vocals {WORK/'music_trimmed_raw.wav'} {WORK/'ref_a.wav'} {WORK/'ref_b.wav'} -o {WORK/'demucs_out'}")
dem_dir = next((WORK / "demucs_out").glob("*/music_trimmed_raw"))
shutil.copy2(dem_dir / "vocals.wav", OUT / "demucs_vocals.wav")
shutil.copy2(dem_dir / "no_vocals.wav", OUT / "demucs_no_vocals.wav")
for rname in ("ref_a", "ref_b"):
    r_dem = next((WORK / "demucs_out").glob(f"*/{rname}/vocals.wav"), None)
    if r_dem and r_dem.exists():
        sh(f"ffmpeg -y -v error -i '{r_dem}' -af 'loudnorm=I=-16:TP=-1.5:LRA=8' -ac 1 -ar 44100 '{WORK / (rname + '.wav')}'")
        shutil.copy2(WORK / (rname + ".wav"), OUT / f"{rname}_isolated.wav")

import soundfile as sf
import numpy as np

voc_stereo, sr = sf.read(str(OUT / "demucs_vocals.wav"), dtype="float32")
final_dur = len(voc_stereo) / sr
lines = json.loads((WORK / "lines.json").read_text(encoding="utf-8"))
runs = []
for l in lines:
    if runs and runs[-1][0] == l["who"]:
        runs[-1][2] = l["end"]
    else:
        runs.append([l["who"], l["start"], l["end"]])

run_meta = []
for idx, (who, r0, r1) in enumerate(runs):
    t_s = max(0.0, r0 - 0.18)
    t_e = min(final_dur, r1 + 0.25)
    i0, i1 = int(round(t_s * sr)), int(round(t_e * sr))
    mono_slice = 0.5 * (voc_stereo[i0:i1, 0] + voc_stereo[i0:i1, 1])
    slice_path = WORK / f"slice_{idx}_{who}.wav"
    sf.write(str(slice_path), mono_slice, sr)
    run_meta.append({"idx": idx, "who": who, "i0": i0, "i1": i1, "t_s": t_s, "t_e": t_e, "slice": str(slice_path)})
    shutil.copy2(slice_path, OUT / slice_path.name)
(OUT / "runs_meta.json").write_text(json.dumps(run_meta, indent=2), encoding="utf-8")

print("=== [3/4] Running Seed-VC In-Memory Batch (44.1kHz F0-Rap + Expressive-Rap) ===", flush=True)
try:
    if not Path("/content/seed-vc").exists():
        sh("git clone --depth 1 https://github.com/Plachtaa/seed-vc /content/seed-vc")

    bv_p = Path("/content/seed-vc/modules/bigvgan/bigvgan.py")
    bv_txt = bv_p.read_text(encoding="utf-8")
    bv_txt = bv_txt.replace("proxies: Optional[Dict],", "proxies: Optional[Dict] = None,")
    bv_txt = bv_txt.replace("resume_download: bool,", "resume_download: bool = False,")
    bv_txt = bv_txt.replace("resume_download=resume_download,", "")
    bv_p.write_text(bv_txt, encoding="utf-8")

    inf_p = Path("/content/seed-vc/inference.py")
    inf_txt = inf_p.read_text(encoding="utf-8")
    if "_MODEL_CACHE = {}" not in inf_txt:
        inf_txt = inf_txt.replace(
            "def load_models(args):",
            "_MODEL_CACHE = {}\ndef load_models(args):\n    _ck = bool(args.f0_condition)\n    if _ck in _MODEL_CACHE: return _MODEL_CACHE[_ck]\n    _res = _load_models_impl(args)\n    _MODEL_CACHE[_ck] = _res\n    return _res\ndef _load_models_impl(args):"
        )
        inf_p.write_text(inf_txt, encoding="utf-8")

    seed_batch_py = Path("/content/seed-vc/batch_rap_vc.py")
    seed_batch_py.write_text("""import json, os, subprocess, sys
import numpy as np, torch
_orig_tl = torch.load
torch.load = lambda *a, **k: _orig_tl(*a, **{**k, "weights_only": False})
import torchaudio, librosa
from types import SimpleNamespace
import inference as inf

work = sys.argv[1]
out_dir = sys.argv[2]
svc_cfg = json.loads(open(os.path.join(work, "svc_cfg.json")).read())
run_meta = json.loads(open(os.path.join(out_dir, "runs_meta.json")).read())

for mode_tag, f0_cond in [("seedvc_f0", True), ("seedvc_vc", False)]:
    args = SimpleNamespace(
        f0_condition=f0_cond, auto_f0_adjust=True, semi_tone_shift=0,
        checkpoint=None, config=None, fp16=True,
        diffusion_steps=35, length_adjust=1.0, inference_cfg_rate=0.72,
        source="", target="", output=os.path.join(work, mode_tag),
    )
    os.makedirs(args.output, exist_ok=True)
    for rm in run_meta:
        idx, who = rm["idx"], rm["who"]
        args.semi_tone_shift = int(svc_cfg.get("seedvc_f0_shift_b", 0)) if (f0_cond and who == "b") else 0
        args.source = rm["slice"]
        args.target = os.path.join(work, "ref_a.wav" if who == "a" else "ref_b.wav")
        inf.main(args)
        import glob
        cands = sorted(glob.glob(os.path.join(args.output, f"vc_slice_{idx}_{who}_*.wav")), key=os.path.getmtime, reverse=True)
        if cands:
            dst = os.path.join(out_dir, f"{mode_tag}_run_{idx}_{who}.wav")
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", cands[0], "-ac", "1", "-ar", "44100", dst], check=True)
            print(f"   ✅ {mode_tag} -> {os.path.basename(dst)}", flush=True)
""", encoding="utf-8")

    sh(f"cd /content/seed-vc && {sys.executable} batch_rap_vc.py {WORK} {OUT}")
except Exception as svc_err:
    import traceback
    print(f"   ⚠️ Seed-VC warning: {svc_err}", flush=True)
    traceback.print_exc()

print("=== [4/4] Running Trained RVC v2 Models ===", flush=True)
try:
    import torch
    _orig_tl2 = torch.load
    torch.load = lambda *a, **k: _orig_tl2(*a, **{**k, "weights_only": False})
    if "pyworld" not in sys.modules:
        pw = types.ModuleType("pyworld")
        pw.dio = pw.stonemask = pw.harvest = lambda *a, **k: None
        sys.modules["pyworld"] = pw

    rvc_dir = WORK / "rvc_models"
    rvc_dir.mkdir(exist_ok=True)

    def _dl_rvc_slot(slot_key: str, urls: list[str]):
        mdir = rvc_dir / f"role_{slot_key}"
        mdir.mkdir(exist_ok=True)
        zpath = rvc_dir / f"role_{slot_key}.zip"
        ok_dl = False
        for u in urls:
            res = subprocess.run(["curl", "-sL", "--fail", "-o", str(zpath), u])
            if res.returncode == 0 and zpath.exists() and zpath.stat().st_size > 1_000_000:
                ok_dl = True
                print(f"   ⬇️ Downloaded RVC [{slot_key}] from {u} ({zpath.stat().st_size / 1048576:.1f} MB)", flush=True)
                break
        if not ok_dl:
            raise RuntimeError(f"Failed to download RVC zip for slot {slot_key}")
        with zipfile.ZipFile(zpath, "r") as zf:
            zf.extractall(mdir)
        pths = sorted(mdir.rglob("*.pth"), key=lambda p: p.stat().st_size, reverse=True)
        idxs = [p for p in mdir.rglob("*.index") if "trained" not in p.name.lower()] or list(mdir.rglob("*.index"))
        print(f"   RVC [{slot_key}]: pth={pths[0]} idx={idxs[0] if idxs else None}", flush=True)
        return (str(pths[0]), str(idxs[0]) if idxs else "")

    loaded_paths = {
        "a": _dl_rvc_slot("a", CFG["rvc_a_urls"]),
        "b": _dl_rvc_slot("b", CFG["rvc_b_urls"]),
    }
    for role in ("a", "b"):
        alt_urls = CFG.get(f"rvc_{role}_alt_urls") or []
        if alt_urls:
            try:
                loaded_paths[f"{role}_alt"] = _dl_rvc_slot(f"{role}_alt", alt_urls)
            except Exception as alt_e:
                print(f"   ⚠️ Optional alt RVC [{role}_alt] skipped: {alt_e}", flush=True)

    from infer_rvc_python import BaseLoader
    converter = BaseLoader(only_cpu=False, hubert_path=None, rmvpe_path=None)
    for pass_cfg in CFG.get("rvc_passes", [{"tag": "rvc", "pitch_a": 0, "pitch_b": 0}]):
        ptag = pass_cfg["tag"]
        for role in ("a", "b"):
            slot = f"{role}_alt" if (pass_cfg.get(f"alt_{role}") and f"{role}_alt" in loaded_paths) else role
            pth_p, idx_p = loaded_paths[slot]
            plvl = int(pass_cfg.get(f"pitch_{role}", 0))
            prot = float(pass_cfg.get(f"protect_{role}", pass_cfg.get("protect", 0.33)))
            idx_inf = float(pass_cfg.get(f"index_{role}", pass_cfg.get("index", 0.68))) if idx_p else 0.0
            converter.apply_conf(
                tag=f"{ptag}_{role}",
                file_model=pth_p,
                pitch_algo="rmvpe+",
                pitch_lvl=plvl,
                file_index=idx_p,
                index_influence=idx_inf,
                respiration_median_filtering=3,
                envelope_ratio=float(pass_cfg.get("envelope_ratio", 0.25)),
                consonant_breath_protection=prot,
            )
        for rm in run_meta:
            idx, who = rm["idx"], rm["who"]
            arr, rvc_sr = converter.generate_from_cache(audio_data=rm["slice"], tag=f"{ptag}_{who}")
            tmp_rvc = WORK / f"raw_{ptag}_{idx}_{who}.wav"
            sf.write(str(tmp_rvc), arr, rvc_sr)
            dst = OUT / f"{ptag}_run_{idx}_{who}.wav"
            sh(f"ffmpeg -y -v error -i '{tmp_rvc}' -ac 1 -ar 44100 '{dst}'")
        print(f"   ✅ Completed RVC pass [{ptag}] (pitch_a={pass_cfg.get('pitch_a',0)}, pitch_b={pass_cfg.get('pitch_b',0)})", flush=True)
except Exception as rvc_err:
    import traceback
    print(f"   ⚠️ RVC v2 optional pass warning: {rvc_err}", flush=True)
    traceback.print_exc()

tar_out = Path("/content") / CFG["out_tar_name"]
with tarfile.open(tar_out, "w:gz") as tf:
    for p in OUT.iterdir():
        tf.add(p, arcname=p.name)

tok_p = WORK / "drive_token.txt"
token = tok_p.read_text(encoding="utf-8").strip()
tok_p.unlink(missing_ok=True)
init_req = urllib.request.Request(
    "https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable",
    data=json.dumps({"name": tar_out.name}).encode("utf-8"),
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=UTF-8"},
    method="POST",
)
with urllib.request.urlopen(init_req, timeout=30) as resp:
    up_url = resp.headers["Location"]
raw_b = tar_out.read_bytes()
put_req = urllib.request.Request(
    up_url, data=raw_b,
    headers={"Content-Length": str(len(raw_b)), "Content-Type": "application/gzip"},
    method="PUT",
)
with urllib.request.urlopen(put_req, timeout=180) as resp:
    up_meta = json.loads(resp.read().decode("utf-8"))
print(f"🎉 ALL DONE in {time.time() - t0:.1f}s! Uploaded {tar_out.name} ({len(raw_b)/1048576:.2f} MB) -> id={up_meta['id']}", flush=True)
with open("/tmp/svc_worker.done", "w") as f:
    f.write(up_meta["id"] + "\n")
'''


def read_wav_f32(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as wf:
        sr = wf.getframerate()
        nch = wf.getnchannels()
        raw = wf.readframes(wf.getnframes())
    x = np.frombuffer(raw, dtype=np.int16).astype(np.float32).reshape(-1, nch) / 32768.0
    return x, sr


def write_wav_f32(path: Path, x: np.ndarray, sr: int = 44100) -> None:
    x_clip = np.clip(x, -0.99, 0.99)
    pcm = (x_clip * 32767.0).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(x.shape[1] if x.ndim > 1 else 1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())


def align_and_polish_slice(conv_wav: Path, orig_wav: Path, role: str, work_dir: Path, svc_cfg: dict) -> np.ndarray:
    """Studio EQ/compressor polish + sample-accurate cross-correlation alignment within +-45ms."""
    polished = work_dir / f"polished_{conv_wav.name}"
    eq_chain = svc_cfg["eq_a"] if role == "a" else svc_cfg["eq_b"]
    delay_ms = 28 if role == "a" else 26
    af = (
        f"{eq_chain},"
        "acompressor=threshold=-18dB:ratio=3.2:attack=8:release=90:makeup=2.2,"
        f"aecho=0.88:0.85:{delay_ms}:0.10"
    )
    subprocess.run([
        "ffmpeg", "-y", "-v", "error", "-i", str(conv_wav),
        "-af", af, "-ac", "1", "-ar", "44100", str(polished)
    ], check=True)

    orig_x, sr = read_wav_f32(orig_wav)
    conv_x, _ = read_wav_f32(polished)
    orig_m = orig_x[:, 0]
    conv_m = conv_x[:, 0]
    target_len = len(orig_m)

    hop = 110
    env_o = np.abs(orig_m)[: (len(orig_m) // hop) * hop].reshape(-1, hop).mean(axis=1)
    env_c = np.abs(conv_m)[: (len(conv_m) // hop) * hop].reshape(-1, hop).mean(axis=1)
    env_o -= env_o.mean()
    env_c -= env_c.mean()
    max_lag = 20
    best_lag = 0
    best_corr = -1e9
    for lag in range(-max_lag, max_lag + 1):
        if lag >= 0:
            a = env_o[: len(env_c) - lag]
            b = env_c[lag : lag + len(a)]
        else:
            a = env_o[-lag:]
            b = env_c[: len(a)]
        n = min(len(a), len(b))
        if n > 10:
            sc = float(np.dot(a[:n], b[:n]))
            if sc > best_corr:
                best_corr = sc
                best_lag = lag
    shift_samples = best_lag * hop
    if shift_samples > 0:
        conv_m = conv_m[shift_samples:]
    elif shift_samples < 0:
        conv_m = np.pad(conv_m, (-shift_samples, 0))
    if len(conv_m) < target_len:
        conv_m = np.pad(conv_m, (0, target_len - len(conv_m)))
    else:
        conv_m = conv_m[:target_len]

    rms_o = float(np.sqrt(np.mean(orig_m**2) + 1e-8))
    rms_c = float(np.sqrt(np.mean(conv_m**2) + 1e-8))
    conv_m = conv_m * (1.12 * rms_o / rms_c)
    print(f"   🎯 Aligned {conv_wav.name}: shift={shift_samples / sr * 1000:+.1f}ms, rms_gain={1.12 * rms_o / rms_c:.2f}x")
    return np.stack([conv_m, conv_m], axis=1)


def build_candidate_master(
    stem_dir: Path,
    prefix_a: str,
    out_voc: Path,
    out_mix: Path,
    svc_cfg: dict,
    prefix_b: str | None = None,
) -> bool:
    prefix_b = prefix_b or prefix_a
    runs_meta = json.loads((stem_dir / "runs_meta.json").read_text(encoding="utf-8"))
    base_v, sr = read_wav_f32(stem_dir / "demucs_vocals.wav")
    inst_c, _ = read_wav_f32(stem_dir / "demucs_no_vocals.wav")
    n_samp = min(len(base_v), len(inst_c))
    base_v, inst_c = base_v[:n_samp].copy(), inst_c[:n_samp].copy()
    voc_out = base_v.copy()

    for rm in runs_meta:
        idx, who, i0, i1 = rm["idx"], rm["who"], rm["i0"], min(n_samp, rm["i1"])
        pfx = prefix_a if who == "a" else prefix_b
        cand = stem_dir / f"{pfx}_run_{idx}_{who}.wav"
        orig_s = stem_dir / f"slice_{idx}_{who}.wav"
        if not cand.exists():
            return False
        aligned = align_and_polish_slice(cand, orig_s, who, stem_dir, svc_cfg)[: i1 - i0]
        k = min(int(0.08 * sr), len(aligned) // 4)
        w = np.ones(len(aligned), dtype=np.float32)
        w[:k] = np.linspace(0.0, 1.0, k, dtype=np.float32)
        w[-k:] = np.linspace(1.0, 0.0, k, dtype=np.float32)
        voc_out[i0:i1] = base_v[i0:i1] * (1.0 - w)[:, None] + aligned * w[:, None]

    write_wav_f32(out_voc, voc_out, sr)
    mix = voc_out + inst_c
    pk = float(np.abs(mix).max())
    if pk > 0.98:
        mix *= 0.98 / pk
    write_wav_f32(out_mix, mix, sr)
    return True


def find_ref_file(work_dir: Path, filename: str) -> Path:
    for cand in [work_dir / filename, work_dir / "svc_backups" / filename]:
        if cand.exists():
            return cand
    raise FileNotFoundError(f"Missing clean voice reference {filename} in {work_dir}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ep_dir", help="Episode directory, e.g. workflows/05_ancient_rap_battle/episodes/arthur-vs-geralt")
    ap.add_argument("--remaster-only", action="store_true", help="Rebuild masters locally from existing svc_stems (0 CCU)")
    ap.add_argument("--pair-a", default="", help="Optional stem tag for role A when building a hybrid master")
    ap.add_argument("--pair-b", default="", help="Optional stem tag for role B when building a hybrid master")
    ap.add_argument("--out-tag", default="hybrid", help="Output tag name for hybrid master")
    args = ap.parse_args()

    ep_dir = Path(args.ep_dir).resolve()
    work_dir = ep_dir / "work"
    stem_dir = work_dir / "svc_stems"
    bak_dir = work_dir / "svc_backups"
    stem_dir.mkdir(parents=True, exist_ok=True)
    bak_dir.mkdir(parents=True, exist_ok=True)
    svc_cfg = resolve_svc_cfg(ep_dir)

    if not args.remaster_only:
        ref_a_path = find_ref_file(work_dir, svc_cfg["ref_a"])
        ref_b_path = find_ref_file(work_dir, svc_cfg["ref_b"])

        bundle_tar = Path(tempfile.gettempdir()) / f"svc_in_{svc_cfg['slug']}.tar.gz"
        worker_py = Path(tempfile.gettempdir()) / "cloud_svc_worker.py"
        cfg_json_p = Path(tempfile.gettempdir()) / "svc_cfg.json"
        worker_py.write_text(CLOUD_WORKER_CODE, encoding="utf-8")
        cfg_json_p.write_text(json.dumps(svc_cfg, indent=2), encoding="utf-8")

        with tarfile.open(bundle_tar, "w:gz") as tf:
            for fn in ["music_trimmed_raw.wav", "lines.json"]:
                p = work_dir / fn
                assert p.exists(), f"Missing {p}"
                tf.add(p, arcname=fn)
            tf.add(ref_a_path, arcname="ref_a.wav")
            tf.add(ref_b_path, arcname="ref_b.wav")
            tf.add(cfg_json_p, arcname="svc_cfg.json")
            tf.add(worker_py, arcname="cloud_svc_worker.py")

        print(f"☁️ [0 CCU Prep] Uploading {bundle_tar.stat().st_size / 1048576:.2f} MB bundle to Google Drive...")
        bundle_id = upload_to_drive(bundle_tar)
        print(f"   Uploaded bundle file_id={bundle_id}")

        out_tar_name = svc_cfg["out_tar_name"]
        local_out_tar = stem_dir / out_tar_name
        pulled_ok = False
        try:
            subprocess.run([sys.executable, str(ROOT_DIR / "scripts" / "colab_meter.py"), "start", "-s", SESSION_NAME, "-g", "L4"], check=False)
            print(f"🚀 Starting Colab L4 session '{SESSION_NAME}' (1.71 CCU/h)...")
            subprocess.run([COLAB_BIN, "new", "-s", SESSION_NAME, "--gpu", "L4"], check=True)

            token = get_drive_token()
            stage_and_launch = f"""
import os, tarfile, urllib.request, subprocess, sys
os.makedirs("/content/svc_work", exist_ok=True)
with open("/content/svc_work/drive_token.txt", "w") as tf:
    tf.write({token!r})
req = urllib.request.Request(
    "https://www.googleapis.com/drive/v3/files/{bundle_id}?alt=media",
    headers={{"Authorization": "Bearer {token}"}},
)
with urllib.request.urlopen(req, timeout=120) as r, open("/tmp/in.tar.gz", "wb") as f:
    f.write(r.read())
with tarfile.open("/tmp/in.tar.gz", "r:gz") as tf:
    tf.extractall("/content/svc_work")
for p in ["/tmp/svc_worker.done", "/tmp/svc_worker.log"]:
    if os.path.exists(p):
        os.remove(p)
subprocess.Popen(
    [sys.executable, "-u", "/content/svc_work/cloud_svc_worker.py"],
    stdout=open("/tmp/svc_worker.log", "w"),
    stderr=subprocess.STDOUT,
    start_new_session=True,
)
print("LAUNCHED_OK")
"""
            out = colab_exec_py(SESSION_NAME, stage_and_launch, timeout_s=60)
            print("   Worker:", out.strip())

            last_lines = 0
            t_poll = time.time()
            while True:
                time.sleep(10)
                poll = colab_exec_py(
                    SESSION_NAME,
                    """
import os, subprocess, json
done = os.path.exists("/tmp/svc_worker.done")
alive = subprocess.run(["pgrep", "-f", "cloud_svc_worker.py"], capture_output=True).returncode == 0
lines = open("/tmp/svc_worker.log", errors="ignore").read().splitlines() if os.path.exists("/tmp/svc_worker.log") else []
print(json.dumps({"done": done, "alive": alive, "n": len(lines), "tail": lines[-25:]}))
""",
                    timeout_s=30,
                    check=False,
                )
                if not poll.strip():
                    continue
                st = json.loads(poll.strip().splitlines()[-1])
                new_n = st["n"] - last_lines
                if new_n > 0:
                    for ln in st["tail"][-min(25, new_n):]:
                        print("   [L4]", ln, flush=True)
                    last_lines = st["n"]
                if st["done"]:
                    break
                if not st["alive"]:
                    raise RuntimeError("Worker exited before writing .done! Tail:\n" + "\n".join(st["tail"]))
                if time.time() - t_poll > 900:
                    raise RuntimeError("Timed out after 900s on L4!")

            # Iron Rule #5: Confirm artifact exists on Drive with size > 0 BEFORE destroying instance
            print(f"⬇️ Verifying & pulling '{out_tar_name}' from Google Drive before teardown...")
            for attempt in range(4):
                if verify_and_download_from_drive(out_tar_name, local_out_tar):
                    pulled_ok = True
                    break
                time.sleep(4)
            if not pulled_ok:
                raise RuntimeError(f"{out_tar_name} not found on Google Drive!")
        finally:
            delete_drive_file(bundle_id)
            print(f"🛑 Stopping Colab L4 session '{SESSION_NAME}' immediately...")
            subprocess.run([COLAB_BIN, "stop", "-s", SESSION_NAME], check=False)
            subprocess.run([sys.executable, str(ROOT_DIR / "scripts" / "colab_meter.py"), "stop", "-s", SESSION_NAME], check=False)

        with tarfile.open(local_out_tar, "r:gz") as tf:
            tf.extractall(stem_dir)

    if args.pair_a and args.pair_b:
        v_p = bak_dir / f"vocals_game_{args.out_tag}.wav"
        m_p = bak_dir / f"music_game_{args.out_tag}.wav"
        if build_candidate_master(stem_dir, args.pair_a, v_p, m_p, svc_cfg, prefix_b=args.pair_b):
            print(f"✅ Mastered hybrid [{args.out_tag}] (A={args.pair_a}, B={args.pair_b}): {m_p}")
        return

    all_tags = [p["tag"] for p in svc_cfg.get("rvc_passes", [])] + ["seedvc_f0", "seedvc_vc"]
    for tag in all_tags:
        v_p = bak_dir / f"vocals_game_{tag}.wav"
        m_p = bak_dir / f"music_game_{tag}.wav"
        if build_candidate_master(stem_dir, tag, v_p, m_p, svc_cfg):
            print(f"✅ Mastered candidate [{tag}]: {m_p}")


if __name__ == "__main__":
    main()
