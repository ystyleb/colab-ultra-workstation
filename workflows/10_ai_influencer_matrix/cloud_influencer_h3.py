#!/usr/bin/env python3
"""Cloud G4 Standalone MiniMax-H3 Ref2VA 9:16 Talking-Head Generator for Workflow 10.

Runs on Colab G4 (96GB Blackwell, `10.05 CCU/h`):
- Boots ComfyUI via `/tmp/launch_g4_comfyui_fast.py --profile scheme_a` (NVMe-staged weights).
- Ensures `minimax_h3_ref2v_turbo_8step_v1.1_768p_comfyui_bf16.safetensors` exists on local NVMe.
- Warms up `/object_info` before dispatching jobs (avoids cold-start timeout).
- Submits single-speaker `MiniMaxH3ReferenceToVideo` + `H3LockAudioLatent` 9:16 (`768x1344`) graphs
  aligned to Zero-Burn Iron Rule F (`subject_definitions`, `retention_analysis`, `<d>[English]...</d>`).
- Copies finished MP4s to `/content/drive/MyDrive/AI_Influencer_Matrix/raw/`.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

if os.path.isdir("/content/drive/My Drive") and not os.path.exists("/content/drive/MyDrive"):
    os.symlink("/content/drive/My Drive", "/content/drive/MyDrive")

DRIVE_ROOT = Path("/content/drive/MyDrive")
DRIVE_COMFY = DRIVE_ROOT / "AI_Workstation/ComfyUI"
LOCAL_COMFY = Path("/content/ComfyUI")
FAST_MODELS = Path("/content/fast_models")
DRIVE_RAW_OUT = DRIVE_ROOT / "AI_Influencer_Matrix/raw"
API_URL = "http://127.0.0.1:8188"

REF2V_TURBO_LORA = "minimax_h3_ref2v_turbo_8step_v1.1_768p_comfyui_bf16.safetensors"
REF2V_TURBO_URL = (
    "https://huggingface.co/lightx2v/Minimax-h3-Turbo/resolve/main/"
    "minimax_h3_ref2v_turbo_8step_v1.1_768p_comfyui_bf16.safetensors"
)


def is_comfy_up() -> bool:
    try:
        urllib.request.urlopen(f"{API_URL}/system_stats", timeout=3)
        return True
    except Exception:
        return False


def ensure_turbo_lora() -> None:
    nvme_lora = FAST_MODELS / "loras" / REF2V_TURBO_LORA
    nvme_lora.parent.mkdir(parents=True, exist_ok=True)
    drv_lora = DRIVE_COMFY / "models/loras" / REF2V_TURBO_LORA
    drv_lora.parent.mkdir(parents=True, exist_ok=True)
    if not (nvme_lora.exists() and nvme_lora.stat().st_size > 10_000_000):
        if drv_lora.exists() and drv_lora.stat().st_size > 10_000_000:
            shutil.copy2(drv_lora, nvme_lora)
        else:
            subprocess.run(["curl", "-sL", "--fail", "-o", str(nvme_lora), REF2V_TURBO_URL], check=True)
            try:
                shutil.copy2(nvme_lora, drv_lora)
            except Exception:
                pass
    comfy_loras = LOCAL_COMFY / "models/loras"
    if comfy_loras.exists():
        link_p = comfy_loras / REF2V_TURBO_LORA
        if not link_p.exists():
            if link_p.is_symlink():
                link_p.unlink()
            os.symlink(nvme_lora, link_p)


def ensure_comfy_running() -> None:
    ensure_turbo_lora()
    if not is_comfy_up():
        launcher = Path("/tmp/launch_g4_comfyui_fast.py")
        if not launcher.exists():
            launcher = DRIVE_ROOT / "AI_Workstation/scripts/launch_g4_comfyui_fast.py"
        subprocess.run([sys.executable, "-u", str(launcher), "--profile", "scheme_a"], check=True)
        ensure_turbo_lora()
        for _ in range(60):
            if is_comfy_up():
                break
            time.sleep(2)
        else:
            raise RuntimeError("❌ ComfyUI failed to start on 127.0.0.1:8188")

    # Warm up /object_info with generous timeout to avoid first-job cold failure
    for attempt in range(5):
        try:
            urllib.request.urlopen(f"{API_URL}/object_info", timeout=45).read()
            print("⚡ ComfyUI /object_info warmed up cleanly.", flush=True)
            return
        except Exception as exc:
            print(f"⏳ Waiting for /object_info warm-up ({attempt + 1}/5): {exc}", flush=True)
            time.sleep(4)
    raise RuntimeError("❌ ComfyUI /object_info failed to respond.")


def build_h3_prompt(persona: dict, scene_cfg: dict, item: dict, dur_sec: float) -> str:
    """Construct Iron-Rule-F compliant single-speaker MiniMax-H3 Ref2VA English talking-head prompt."""
    ts_end = f"00:{dur_sec - 0.10:06.3f}"
    # 服装随场景变化（同一人物两张关键帧穿的不一样），必须取场景级 outfit_en；
    # 写在人物级 look_en 会让文字和 <Picture 1> 打架，H3 可能改衣服。
    look = persona["look_en"]
    if scene_cfg.get("outfit_en"):
        look = f"{look}, wearing {scene_cfg['outfit_en']}"
    return (
        "subject_definitions:\n"
        f"<Subject 1> is {persona['display_name']} ({look}) from <Picture 1>, "
        "warm natural lifelike human skin tone with realistic fine pores and subtle authentic facial lines.\n"
        "<Audio 1> is the voice-timbre reference for <Subject 1>.\n\n"
        "retention_analysis:\n"
        "<Subject 1> (appears in [Shot 1]): fully_preserved - Strictly preserve exact facial bone structure, "
        "eye color, natural skin micro-texture, hairstyle, outfit, and chest-up framing from <Picture 1>.\n"
        "Background (appears in [Shot 1]): fully_preserved - Keep the exact location lighting and shallow T2.2 optical bokeh "
        f"from <Picture 1> ({scene_cfg['bg_en']}).\n\n"
        "summary:\n"
        "[reference generation + audio reference]\n"
        f"Shot 1 (00:00.000 - {ts_end}): Live-action 35mm cinema vertical 9:16 natural talking-head shot at eye level "
        f"on <Subject 1>, chest-up medium close-up. {item['camera_action_en']} "
        # 景别变化交给本地剪辑（subtitle_and_finalize.py 的 punch_in）。H3 里写推镜头会一路推到大特写，
        # 锁死机位又太僵；这里只要官方词表的 Shake Slightly，加上人物自己的小动作。2026-11-18 试了三版后定的。
        "The camera shakes slightly at slow speed like a steady handheld camera, keeping the same chest-up framing. "
        "<Subject 1>'s mouth, lips, and jaw remain 100% unobstructed and naturally expressive throughout. "
        "<Subject 1> is the on-screen speaker of every word, lips and jaw visibly forming each syllable in sync with the speech. "
        f"Speaking directly to the viewer in a clear, grounded tone, <Subject 1> delivers: <d>[English]{item['spoken_en']}</d> "
        "Clean live-action optical realism, natural room ambiance, zero subtitles, zero on-screen text, zero watermarks."
    )


def build_workflow(
    cfg: dict,
    item: dict,
    img_name: str,
    audio_name: str,
    prompt_text: str,
    frames: int,
    seed: int,
) -> dict:
    # 人设级 h3_overrides 覆盖全局默认（例：Vivian 关掉 closeup LoRA，它会把机位往大特写推）
    d = {**cfg["h3_defaults"], **cfg["personas"][item["persona"]].get("h3_overrides", {})}
    assert (frames - 5) % 17 == 0, f"Illegal frame count {frames} (must be 17k+5)"
    wf = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": d["unet"], "weight_dtype": "default"}},
        "2": {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["1", 0], "lora_name": d["realism_lora"], "strength_model": d["realism_strength"]}},
        "3": {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["2", 0], "lora_name": d["closeup_lora"], "strength_model": d["closeup_strength"]}},
        "4": {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["3", 0], "lora_name": d["turbo_lora"], "strength_model": d["turbo_strength"]}},
        "5": {"class_type": "MiniMaxH3SigmaShift", "inputs": {"model": ["4", 0], "shift_video": 12.0, "shift_audio": 3.0}},
        "6": {"class_type": "CLIPLoader", "inputs": {"clip_name": d["clip"], "type": "minimax", "device": "default"}},
        "7": {"class_type": "VAELoader", "inputs": {"vae_name": d["video_vae"]}},
        "8": {"class_type": "VAELoader", "inputs": {"vae_name": d["audio_vae"]}},
        "14": {"class_type": "BasicScheduler", "inputs": {"model": ["5", 0], "scheduler": "simple", "steps": d["steps"], "denoise": 1.0}},
        "15": {"class_type": "MiniMaxH3SigmasTail", "inputs": {"sigmas": ["14", 0], "tail_steps": 3, "strength": 0.50}},
        "16": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "res_multistep"}},
        "100": {"class_type": "LoadImage", "inputs": {"image": img_name}},
        "110": {"class_type": "LoadAudio", "inputs": {"audio": audio_name}},
        "111": {"class_type": "VAEEncodeAudio", "inputs": {"audio": ["110", 0], "vae": ["8", 0]}},
        "20": {
            "class_type": "MiniMaxH3ReferenceToVideo",
            "inputs": {
                "clip": ["6", 0],
                "vae": ["7", 0],
                "audio_vae": ["8", 0],
                "width": d["width"],
                "height": d["height"],
                "length": frames,
                "ref_image_size": "max",
                "prompt": prompt_text,
                "ref_images.ref_image_0": ["100", 0],
                "ref_audios.ref_audio_0": ["110", 0],
            },
        },
        "22": {
            "class_type": "H3LockAudioLatent",
            "inputs": {"av_latent": ["20", 1], "encoded_audio": ["111", 0], "lock_strength": d["audio_lock_strength"]},
        },
        "21": {
            "class_type": "BunnyH3ConditioningBridge",
            "inputs": {
                "conditioning": ["20", 0],
                "adapter": d["bunny_adapter"],
                "alpha": d["bunny_alpha"],
                "magnitude_match": "per_token",
                "enabled": True,
            },
        },
        "25": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
        "26": {"class_type": "BasicGuider", "inputs": {"model": ["5", 0], "conditioning": ["21", 0]}},
        "27": {
            "class_type": "SamplerCustomAdvanced",
            "inputs": {"noise": ["25", 0], "guider": ["26", 0], "sampler": ["16", 0], "sigmas": ["15", 0], "latent_image": ["22", 0]},
        },
        "30": {"class_type": "LTXVSeparateAVLatent", "inputs": {"av_latent": ["27", 0]}},
        "31": {"class_type": "VAEDecode", "inputs": {"samples": ["30", 0], "vae": ["7", 0]}},
        "32": {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["30", 1], "vae": ["8", 0]}},
        "35": {
            "class_type": "VHS_VideoCombine",
            "inputs": {
                "images": ["31", 0],
                "audio": ["32", 0],
                "frame_rate": d["fps"],
                "loop_count": 0,
                "filename_prefix": f"AIInf_{item['id']}_seed{seed}",
                "format": "video/h264-mp4",
                "pix_fmt": "yuv420p",
                "crf": 14,
                "save_metadata": False,
                "trim_to_audio": False,
                "pingpong": False,
                "save_output": True,
            },
        },
    }
    return wf


def submit_and_wait(wf: dict, timeout_sec: int = 900) -> Path:
    payload = json.dumps({"prompt": wf}).encode("utf-8")
    req = urllib.request.Request(f"{API_URL}/prompt", data=payload, headers={"Content-Type": "application/json"}, method="POST")
    resp = json.loads(urllib.request.urlopen(req, timeout=30).read().decode("utf-8"))
    pid = resp["prompt_id"]
    t0 = time.time()
    while time.time() - t0 < timeout_sec:
        hist = json.loads(urllib.request.urlopen(f"{API_URL}/history/{pid}", timeout=20).read().decode("utf-8"))
        if pid in hist:
            entry = hist[pid]
            if entry.get("status", {}).get("status_str") == "error":
                raise RuntimeError(f"ComfyUI execution error for {pid}: {entry.get('status')}")
            outs = entry.get("outputs", {})
            for node_out in outs.values():
                for vid in node_out.get("gifs", []) + node_out.get("videos", []):
                    fname = vid.get("filename")
                    if fname and fname.endswith(".mp4"):
                        sub = vid.get("subfolder", "")
                        return LOCAL_COMFY / "output" / sub / fname
            raise RuntimeError(f"Prompt {pid} finished without MP4 output.")
        time.sleep(3)
    raise TimeoutError(f"ComfyUI prompt {pid} timed out after {timeout_sec}s")


def main() -> None:
    ap = argparse.ArgumentParser(description="Workflow 10 Cloud G4 MiniMax-H3 Video Runner")
    ap.add_argument("--config", required=True)
    ap.add_argument("--scripts", required=True)
    ap.add_argument("--tts-manifest", default="")
    ap.add_argument("--ids", default="")
    ap.add_argument("--seed-base", type=int, default=2026111700)
    args = ap.parse_args()

    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    manifest = json.loads(Path(args.scripts).read_text(encoding="utf-8"))
    tts_map: dict[str, dict] = {}
    if args.tts_manifest and Path(args.tts_manifest).exists():
        tm = json.loads(Path(args.tts_manifest).read_text(encoding="utf-8"))
        tts_map = {c["id"]: c for c in tm.get("clips", [])}

    sel = {x.strip() for x in args.ids.split(",") if x.strip()} if args.ids else None
    tasks = [s for s in manifest["scripts"] if (not sel or s["id"] in sel)]
    if not tasks:
        raise SystemExit("❌ No matching script IDs.")

    ensure_comfy_running()
    DRIVE_RAW_OUT.mkdir(parents=True, exist_ok=True)
    comfy_in = LOCAL_COMFY / "input"
    comfy_in.mkdir(parents=True, exist_ok=True)

    # Copy staged assets into local NVMe input. Later dirs overwrite earlier ones, so the freshest
    # source goes last: AI_Influencer_Matrix/inputs is staged by the local controller right before boot;
    # older copies in ComfyUI/input (e.g. a replaced keyframe) must never win over it.
    for stage_dir in (
        DRIVE_COMFY / "input",
        DRIVE_ROOT / "AI_Influencer_Matrix/tts",
        Path("/tmp/wf10_inputs"),
        DRIVE_ROOT / "AI_Influencer_Matrix/inputs",
    ):
        if stage_dir.exists():
            for f in stage_dir.glob("*"):
                if f.is_file() and f.suffix.lower() in (".png", ".wav"):
                    shutil.copy2(f, comfy_in / f.name)

    for idx, item in enumerate(tasks):
        pk = item["persona"]
        persona = cfg["personas"][pk]
        scene_cfg = persona["scenes"][item["scene"]]
        img_name = scene_cfg["image"]
        audio_name = f"{item['id']}.wav"
        if not (comfy_in / audio_name).exists():
            raise FileNotFoundError(f"Missing synthesized WAV {audio_name} in {comfy_in}. Run L4 TTS first.")
        if not (comfy_in / img_name).exists():
            raise FileNotFoundError(f"Missing reference keyframe {img_name} in {comfy_in}.")

        frames = int(tts_map[item["id"]]["h3_frames"]) if item["id"] in tts_map else int(item["default_frames"])
        dur_sec = frames / 24.0
        seed = args.seed_base + idx + 1
        prompt = build_h3_prompt(persona, scene_cfg, item, dur_sec)
        wf = build_workflow(cfg, item, img_name, audio_name, prompt, frames, seed)

        t0 = time.time()
        print(f"🎬 [{idx + 1}/{len(tasks)}] Rendering {item['id']} ({pk}/{item['scene']}, {frames}f, seed={seed})...", flush=True)
        out_mp4 = submit_and_wait(wf)
        dst_drive = DRIVE_RAW_OUT / out_mp4.name
        shutil.copy2(out_mp4, dst_drive)
        print(f"✅ [{item['id']}] Finished in {time.time() - t0:.1f}s -> {dst_drive.name} ({dst_drive.stat().st_size / 1e6:.2f} MB)", flush=True)


if __name__ == "__main__":
    main()
