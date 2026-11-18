#!/usr/bin/env python3
"""Cloud L4 Standalone English Dual-Engine TTS Studio for Workflow 10 (`10_ai_influencer_matrix`).

Runs on Colab L4 (`1.71 CCU/h`, zero ComfyUI dependency, zero 42GB video model downloads):
- Uses cached Qwen3-TTS-12Hz-1.7B (`VoiceDesign` + `Base`) on `/content/drive/MyDrive/AI_Models/TTS_Cache/`
  (or fast HF CDN pull on first boot) and optionally `IndexTTS-2` (`--mode hybrid | qwen`).
- Uses English F0 Pitch Guard across candidate seeds to lock mature, non-anime voice seeds per persona
  (`vivian`, `june`, `wen`; personas come from `influencer_config.json`).
- Synthesizes each requested script ID (`V01`..`W10`), pads 0.30s leading + 0.40s trailing silence,
  normalizes to -1.1 dBFS, calculates exact WAV duration and smallest legal `17k + 5` H3 frame count,
  and persists outputs to `/content/drive/MyDrive/AI_Influencer_Matrix/tts/` + `/tmp/wf10_tts/`.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

if os.path.isdir("/content/drive/My Drive") and not os.path.exists("/content/drive/MyDrive"):
    os.symlink("/content/drive/My Drive", "/content/drive/MyDrive")

DRIVE_ROOT = Path("/content/drive/MyDrive")
DRIVE_TTS_CACHE = DRIVE_ROOT / "AI_Models/TTS_Cache"
DRIVE_HF_CACHE = DRIVE_TTS_CACHE / "hf_cache"
DRIVE_INDEXTTS_CACHE = DRIVE_TTS_CACHE / "IndexTTS-2"
DRIVE_OUT_TTS = DRIVE_ROOT / "AI_Influencer_Matrix/tts"
DRIVE_COMFY_IN = DRIVE_ROOT / "AI_Workstation/ComfyUI/input"

LOCAL_NVME_CACHE = Path("/content/nvme_tts_cache")
LOCAL_HF_CACHE = LOCAL_NVME_CACHE / "hf_cache"
LOCAL_INDEXTTS_REPO = Path("/content/index-tts")
LOCAL_INDEXTTS_CKPT = LOCAL_NVME_CACHE / "IndexTTS-2"
LOCAL_OUT = Path("/tmp/wf10_tts")

LEGAL_FRAMES = [90, 107, 124, 141, 158, 175, 192, 209, 226, 243, 260, 277, 294, 311, 328, 345, 362]


def sh(cmd: str) -> str:
    print(f"🔧 $ {cmd}", flush=True)
    p = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    if p.returncode != 0 and p.stderr:
        print(f"⚠️ {p.stderr[-500:]}", flush=True)
    return p.stdout


def snap_h3_frames(duration_sec: float, fps: float = 24.0) -> int:
    """Return smallest legal `17k + 5` frame count >= (duration_sec + 0.25) * fps, within [124, 362]."""
    needed = math.ceil((duration_sec + 0.25) * fps)
    for f in LEGAL_FRAMES:
        if f >= max(124, needed):
            return f
    return 362


def ensure_tts_env(need_indextts: bool = False) -> None:
    LOCAL_HF_CACHE.mkdir(parents=True, exist_ok=True)
    LOCAL_OUT.mkdir(parents=True, exist_ok=True)
    if DRIVE_ROOT.exists():
        DRIVE_OUT_TTS.mkdir(parents=True, exist_ok=True)
        DRIVE_COMFY_IN.mkdir(parents=True, exist_ok=True)

    chk = subprocess.run(
        [sys.executable, "-c", "from qwen_tts import Qwen3TTSModel; import soundfile, librosa, scipy"],
        capture_output=True,
    )
    if chk.returncode != 0:
        print("⚡ Installing Qwen3-TTS core dependencies...", flush=True)
        sh("pip install -q uv && uv pip install --system qwen-tts hf_transfer soundfile librosa scipy accelerate sentencepiece 'protobuf>=5.26.1' 'numpy<=2.2.6'")

    if need_indextts:
        LOCAL_INDEXTTS_CKPT.mkdir(parents=True, exist_ok=True)
        chk_idx = (
            subprocess.run(
                ["/content/venv_idx/bin/python", "-c", "import numba, whisper, transformers; assert transformers.__version__ == '4.52.1'"],
                capture_output=True,
            )
            if Path("/content/venv_idx/bin/python").exists()
            else subprocess.run(["false"])
        )
        if chk_idx.returncode != 0:
            sh("apt-get update -qq && apt-get install -y -qq aria2 rsync sox libsox-dev")
            sh("uv pip install --system omegaconf munch einops jieba cn2an pypinyin g2p-en openai-whisper tiktoken json5 matplotlib modelscope 'numpy<=2.2.6'")
            sh("uv pip install --system --no-deps descript-audiotools argbind julius ffmpy flatten-dict markdown2 randomname")
            sh("rm -rf /content/venv_idx && uv venv --system-site-packages /content/venv_idx")
            sh("uv pip install --python /content/venv_idx/bin/python --no-deps 'transformers==4.52.1' 'tokenizers==0.21.4'")
        if not (LOCAL_INDEXTTS_REPO / "indextts/infer_v2.py").exists():
            sh("git clone --depth 1 https://github.com/index-tts/index-tts.git /content/index-tts")
        if DRIVE_INDEXTTS_CACHE.exists() and not (LOCAL_INDEXTTS_CKPT / "gpt.pth").exists():
            sh(f"rsync -a {DRIVE_INDEXTTS_CACHE}/ {LOCAL_INDEXTTS_CKPT}/")
        if not (LOCAL_INDEXTTS_CKPT / "gpt.pth").exists():
            sh(
                "HF_HUB_ENABLE_HF_TRANSFER=1 python3 -c \"from huggingface_hub import snapshot_download; "
                "snapshot_download('IndexTeam/IndexTTS-2', local_dir='/content/nvme_tts_cache/IndexTTS-2')\""
            )


def main() -> None:
    ap = argparse.ArgumentParser(description="Workflow 10 Cloud L4 English TTS Synthesizer")
    ap.add_argument("--config", required=True, help="Path to influencer_config.json")
    ap.add_argument("--scripts", required=True, help="Path to scripts_30_manifest.json")
    ap.add_argument("--ids", default="", help="Comma-separated script IDs (default: all)")
    ap.add_argument("--mode", default="qwen", choices=["qwen", "hybrid"], help="Synthesis backend (default: qwen)")
    ap.add_argument("--temperature", type=float, default=0.40)
    ap.add_argument("--locked-seed-dir", default="", help="Dir with seed_<persona>.wav from an earlier run; personas found there skip voice design so the voice stays identical across batches")
    ap.add_argument("--locked-seed-meta", default="", help="Path to JSON {persona: {seed, f0_hz, seed_text}} for the locked seeds")
    args = ap.parse_args()

    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    manifest = json.loads(Path(args.scripts).read_text(encoding="utf-8"))
    selected_ids = {x.strip() for x in args.ids.split(",") if x.strip()} if args.ids else None
    tasks = [s for s in manifest["scripts"] if (not selected_ids or s["id"] in selected_ids)]
    if not tasks:
        raise SystemExit("❌ No matching script IDs found.")

    need_idx = args.mode == "hybrid"
    ensure_tts_env(need_indextts=need_idx)

    os.environ["HF_HOME"] = str(LOCAL_HF_CACHE)
    os.environ["HF_HUB_CACHE"] = str(LOCAL_HF_CACHE)
    os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"

    import librosa
    import numpy as np
    import soundfile as sf
    import torch
    from qwen_tts import Qwen3TTSModel

    def clean_and_level(wav: np.ndarray, sr: int, target_sr: int = 24000, pad_head: float = 0.0, pad_tail: float = 0.0) -> np.ndarray:
        y = np.asarray(wav, dtype=np.float32)
        if sr != target_sr:
            y = librosa.resample(y, orig_sr=sr, target_sr=target_sr)
        yc, _ = librosa.effects.trim(y, top_db=34, frame_length=1024, hop_length=256)
        if len(yc) == 0:
            yc = y
        pk = float(np.max(np.abs(yc)))
        if pk > 0.01:
            yc = yc / pk * 0.88
        fade = min(int(0.015 * target_sr), max(1, len(yc) // 8))
        yc[:fade] *= np.linspace(0.0, 1.0, fade)
        yc[-fade:] *= np.linspace(1.0, 0.0, fade)
        if pad_head > 0 or pad_tail > 0:
            yc = np.concatenate([
                np.zeros(int(pad_head * target_sr), dtype=np.float32),
                yc,
                np.zeros(int(pad_tail * target_sr), dtype=np.float32),
            ])
        return yc.astype(np.float32)

    def measure_f0(wav: np.ndarray, sr: int) -> float:
        try:
            f0, _, _ = librosa.pyin(np.asarray(wav, dtype=np.float32), fmin=60.0, fmax=360.0, sr=sr, frame_length=1024)
            valid = f0[~np.isnan(f0)]
            return float(np.median(valid)) if len(valid) > 0 else 0.0
        except Exception:
            return 0.0

    t0 = time.time()
    print("⏳ Loading Qwen3-TTS-12Hz-1.7B VoiceDesign & Base onto GPU...", flush=True)
    design_model = Qwen3TTSModel.from_pretrained("Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign", device_map="cuda:0", dtype=torch.bfloat16)
    base_model = Qwen3TTSModel.from_pretrained("Qwen/Qwen3-TTS-12Hz-1.7B-Base", device_map="cuda:0", dtype=torch.bfloat16)
    print(f"✅ Models ready in {time.time() - t0:.1f}s", flush=True)

    sr = 24000
    needed_personas = sorted({t["persona"] for t in tasks})
    seed_paths: dict[str, Path] = {}
    seed_meta: dict[str, dict] = {}

    locked_dir = Path(args.locked_seed_dir) if args.locked_seed_dir else None
    locked_meta = json.loads(Path(args.locked_seed_meta).read_text()) if args.locked_seed_meta else {}
    LOCAL_OUT.mkdir(parents=True, exist_ok=True)
    for pk in needed_personas:
        v_cfg = cfg["personas"][pk]["voice"]
        # 已锁定的声线直接复用：声音设计是采样出来的，同一个 seed 重跑也不保证是同一个声音
        if locked_dir and (locked_dir / f"seed_{pk}.wav").exists():
            sp = LOCAL_OUT / f"seed_{pk}.wav"
            shutil.copy2(locked_dir / f"seed_{pk}.wav", sp)
            seed_paths[pk] = sp
            seed_meta[pk] = locked_meta.get(pk, {"seed": "locked", "seed_text": v_cfg["seed_text"]})
            print(f"🔒 Reusing locked [{pk}] voice from {locked_dir.name}/seed_{pk}.wav", flush=True)
            continue
        lo_f0, hi_f0 = v_cfg["f0_range_hz"]
        mid_f0 = 0.5 * (lo_f0 + hi_f0)
        best_wav = None
        best_dist = 9999.0
        best_f0 = 0.0
        best_sd = v_cfg["seeds"][0]

        for sd in v_cfg["seeds"]:
            torch.manual_seed(sd)
            torch.cuda.manual_seed_all(sd)
            wavs, wsr = design_model.generate_voice_design(
                text=v_cfg["seed_text"],
                language=v_cfg.get("language", "English"),
                instruct=v_cfg["instruct"],
                temperature=args.temperature,
                top_p=0.75,
            )
            cand = clean_and_level(wavs[0], wsr, target_sr=sr)
            f0 = measure_f0(cand, sr)
            dist = abs(f0 - mid_f0) * 0.2 if (lo_f0 <= f0 <= hi_f0) else (min(abs(f0 - lo_f0), abs(f0 - hi_f0)) + 50.0)
            print(f"🔍 [{pk}] candidate seed={sd} -> F0={f0:.1f} Hz (target {lo_f0:.0f}-{hi_f0:.0f} Hz)", flush=True)
            if dist < best_dist:
                best_dist = dist
                best_wav = cand
                best_f0 = f0
                best_sd = sd

        sp = LOCAL_OUT / f"seed_{pk}.wav"
        sf.write(str(sp), best_wav, sr, subtype="PCM_16")
        seed_paths[pk] = sp
        seed_meta[pk] = {"seed": best_sd, "f0_hz": round(best_f0, 1), "seed_text": v_cfg["seed_text"]}
        print(f"🔒 Locked [{pk}] voice seed={best_sd} (F0={best_f0:.1f} Hz)", flush=True)

    results: list[dict] = []
    if args.mode == "qwen":
        for item in tasks:
            pk = item["persona"]
            v_cfg = cfg["personas"][pk]["voice"]
            wavs, wsr = base_model.generate_voice_clone(
                text=item["spoken_en"],
                language=v_cfg.get("language", "English"),
                ref_audio=str(seed_paths[pk]),
                ref_text=v_cfg["seed_text"],
                temperature=args.temperature,
                top_p=0.78,
            )
            final_wav = clean_and_level(wavs[0], wsr, target_sr=sr, pad_head=0.30, pad_tail=0.40)
            out_wav = LOCAL_OUT / f"{item['id']}.wav"
            sf.write(str(out_wav), final_wav, sr, subtype="PCM_16")
            dur = round(len(final_wav) / sr, 3)
            frames = snap_h3_frames(dur)
            results.append({"id": item["id"], "persona": pk, "wav": out_wav.name, "duration_sec": dur, "h3_frames": frames})
            print(f"🎙️ [{item['id']}] {dur:.2f}s -> {frames} frames ({frames / 24.0:.2f}s)", flush=True)
    else:
        # Optional IndexTTS-2 synthesis path using locked Qwen seeds
        idx_tasks = []
        for item in tasks:
            pk = item["persona"]
            raw_p = str(LOCAL_OUT / f"{item['id']}_raw_idx.wav")
            idx_tasks.append({"id": item["id"], "ref_p": str(seed_paths[pk]), "txt": item["spoken_en"], "raw_out": raw_p})
        worker_py = Path("/tmp/wf10_idx_worker.py")
        worker_py.write_text(
            "import json, sys\n"
            "sys.path.insert(0, '/content/index-tts')\n"
            "from indextts.infer_v2 import IndexTTS2\n"
            "tasks = json.loads(sys.argv[1])\n"
            "tts = IndexTTS2(cfg_path='/content/nvme_tts_cache/IndexTTS-2/config.yaml', model_dir='/content/nvme_tts_cache/IndexTTS-2', use_fp16=True, device='cuda:0', use_cuda_kernel=False)\n"
            "for it in tasks:\n"
            "    tts.infer(spk_audio_prompt=it['ref_p'], text=it['txt'], output_path=it['raw_out'], use_random=False, verbose=False)\n",
            encoding="utf-8",
        )
        subprocess.run(["/content/venv_idx/bin/python", str(worker_py), json.dumps(idx_tasks)], check=True)
        for item in tasks:
            y, wsr = librosa.load(str(LOCAL_OUT / f"{item['id']}_raw_idx.wav"), sr=sr, mono=True)
            final_wav = clean_and_level(y, wsr, target_sr=sr, pad_head=0.30, pad_tail=0.40)
            out_wav = LOCAL_OUT / f"{item['id']}.wav"
            sf.write(str(out_wav), final_wav, sr, subtype="PCM_16")
            dur = round(len(final_wav) / sr, 3)
            frames = snap_h3_frames(dur)
            results.append({"id": item["id"], "persona": item["persona"], "wav": out_wav.name, "duration_sec": dur, "h3_frames": frames})
            print(f"🎙️ [{item['id']}] {dur:.2f}s -> {frames} frames", flush=True)

    manifest_out = LOCAL_OUT / "tts_manifest.json"
    manifest_out.write_text(json.dumps({"mode": args.mode, "seeds": seed_meta, "clips": results}, indent=2), encoding="utf-8")

    if DRIVE_ROOT.exists():
        DRIVE_OUT_TTS.mkdir(parents=True, exist_ok=True)
        for f in LOCAL_OUT.glob("*.wav"):
            shutil.copy2(f, DRIVE_OUT_TTS / f.name)
            shutil.copy2(f, DRIVE_COMFY_IN / f.name)
        shutil.copy2(manifest_out, DRIVE_OUT_TTS / "tts_manifest.json")
        print(f"☁️ Synced {len(results)} WAVs + seeds to Drive ({DRIVE_OUT_TTS}) and ComfyUI/input", flush=True)


if __name__ == "__main__":
    main()
