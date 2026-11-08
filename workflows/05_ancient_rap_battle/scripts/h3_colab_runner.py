#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Colab G4 (96GB Blackwell) Open-Weight MiniMax-H3 Batch Clip Runner for Ancient/Historical Rap Battle.
Replaces the paid $16 MiniMax commercial API (`h3run.py`) with local ComfyUI `MiniMaxH3ReferenceToVideo` on Colab G4.

Usage on Colab G4:
  python3 h3_colab_runner.py <episode_dir> [--ids A01 A02 ...] [--steps 8]
"""
import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qa  # noqa: E402
from common import die, jload, jsave, load_episode  # noqa: E402

if os.path.isdir("/content/drive/My Drive") and not os.path.exists("/content/drive/MyDrive"):
    os.symlink("/content/drive/My Drive", "/content/drive/MyDrive")

DRIVE_COMFY = Path("/content/drive/MyDrive/AI_Workstation/ComfyUI")
LOCAL_COMFY = Path("/content/ComfyUI")
API_URL = "http://127.0.0.1:8188"


def is_comfy_up() -> bool:
    try:
        urllib.request.urlopen(f"{API_URL}/system_stats", timeout=3)
        return True
    except Exception:
        return False


def ensure_comfy_running() -> None:
    if is_comfy_up():
        print("⚡ ComfyUI 已在 127.0.0.1:8188 运行中！", flush=True)
        return
    launcher = Path("/tmp/launch_g4_comfyui_fast.py")
    if not launcher.exists():
        launcher = Path("/content/drive/MyDrive/AI_Workstation/scripts/launch_g4_comfyui_fast.py")
    print("🚀 正在启动 launch_g4_comfyui_fast.py (scheme_dance 极速模式)...", flush=True)
    subprocess.run([sys.executable, "-u", str(launcher), "--profile", "scheme_dance"], check=True)
    for _ in range(60):
        if is_comfy_up():
            return
        time.sleep(2)
    raise RuntimeError("❌ ComfyUI 启动超时，请检查 /tmp/comfyui.log")


def cut_audio(ep: str, c: dict, total_dur: float = 5.167) -> str:
    out = os.path.join(ep, "work", "audio", c["id"] + ".wav")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    a, b = c["audio"]
    dur = max(1.8, min(total_dur - 0.05, b - a))
    # Fade out cleanly at the end of the lyric line, then pad with silence to the exact clip duration
    # so the audio latent aligns 1:1 with the video latent window [0.000s .. total_dur].
    af = "afade=t=in:d=0.02,afade=t=out:st=%.3f:d=0.05" % max(0.05, dur - 0.05)
    if c.get("lead"):
        af += ",adelay=%d:all=1" % int(c["lead"] * 1000)
    af += ",apad=whole_dur=%.3f" % total_dur
    src_wav = os.path.join(ep, "work", "vocals_final.wav")
    if not os.path.exists(src_wav):
        src_wav = os.path.join(ep, "work", "music_final.wav")
    subprocess.run([
        "ffmpeg", "-y", "-v", "error",
        "-ss", "%.3f" % max(0.0, a), "-t", "%.3f" % dur,
        "-i", src_wav, "-af", af, "-t", "%.3f" % total_dur, "-ac", "2", "-ar", "44100", out
    ], check=True)
    return out


STATIC_CAM = (" on a locked-off static tripod, holding the same tight chest-up framing with a fixed focal length "
              "from the very first frame to the last frame")


def adapt_prompt_for_comfy_h3(c: dict, e: dict, total_dur: float = 5.167, mic: str = "handheld",
                              static_cam: bool = False) -> str:
    """Build the official 6-section MiniMaxH3ReferenceToVideo structured prompt (`ref-en.txt` protocol)."""
    lang = e.get("language", "en")
    if c["kind"] != "rap" or not c.get("text"):
        p = c["prompt"]
        for i in range(1, 10):
            p = re.sub(rf"\bImage {i}\b", f"<Picture {i}>", p)
        p = re.sub(r"\bAudio 1\b", "<Audio 1>", p)
        return "r34l1sm, Facial Realism, " + p

    who = c.get("who", "a")
    me = e[who]
    them = e["b" if who == "a" else "a"]
    two_shot = bool(c.get("two_shot"))
    lang_tag = "English" if lang == "en" else "Mandarin"
    a0, a1 = c["audio"]
    lead = float(c.get("lead") or 0.0)
    t_start = lead
    t_end = min(total_dur - 0.05, lead + max(1.8, a1 - a0))
    ts_total_str = f"00:0{total_dur:05.3f}"
    ts_start_str = f"00:0{t_start:05.3f}"
    ts_end_str = f"00:0{t_end:05.3f}"
    if mic == "stand":
        mic_summary = ("rapping into a vintage chrome microphone on a floor stand that stands at mid-chest height slightly to one side, "
                       "well below his chin, never in front of his mouth; both hands are free")
        mic_detail = ("with a vintage chrome microphone on a floor stand placed at mid-chest height slightly to one side of him "
                      "(he never holds or lifts it, and it never covers his mouth, lips or jaw, which stay 100% unobstructed and visible)")
    else:
        mic_summary = "holding the vintage microphone at upper-chest height below his chin so his mouth and lips remain 100% uncovered"
        mic_detail = ("holding the silver corded microphone in his right hand at upper-chest height a few inches below his chin "
                      "(completely clear of his face so his mouth, lips, and jaw are 100% unobstructed and visible)")
    venue_desc = e.get("venue_en", "an 1890s industrial power plant rap battle arena")
    action_desc = c.get("action") or "fierce and confident, his free hand chopping the air on the beat"
    move = c.get("move", "M3")

    if c.get("cam"):
        cam_desc = c["cam"] + (STATIC_CAM if static_cam else "")
    elif move == "M2":
        cam_desc = (
            "The camera holds a chest-up close-up shot at eye level" + (STATIC_CAM if static_cam else " with a subtle slow push-in") + ", framing "
            "<Subject 1>'s face and upper chest large and centered in the 16:9 frame with comfortable headroom"
        )
    elif two_shot:
        cam_desc = (
            "The camera holds a balanced chest-up medium two-shot at eye level from the south side of the 180-degree axis, "
            "framing <Subject 1> on screen-left turned three-quarters toward the lens and <Subject 2> on screen-right in profile"
        )
    else:
        cam_desc = (
            "The camera holds a chest-up medium close-up shot at eye level" + (STATIC_CAM if static_cam else " with a gentle slow push-in") + ", "
            "framing <Subject 1> turned three-quarters toward the lens with his face and lips large and clearly readable"
        )

    subj_lines = [
        f"<Subject 1> is {me['name_en']} ({me['look']}) from <Picture 1>, natural matte skin texture with fine pores."
    ]
    ret_lines = [
        f"<Subject 1> (appears in [Shot 1]): fully_preserved - Strictly preserve exact facial bone structure, hairstyle, moustache, outfit, and {me.get('prop', 'prop')} from <Picture 1>."
    ]
    if two_shot:
        subj_lines.append(
            f"<Subject 2> is {them['name_en']} ({them['look']}) from <Picture 2>, natural matte skin texture."
        )
        ret_lines.append(
            f"<Subject 2> (appears in [Shot 1]): fully_preserved - Strictly preserve exact facial structure and outfit from <Picture 2> on screen-right, keeping his mouth closed in silent listening throughout this clip."
        )
    subj_lines.append(
        f"<Audio 1> is the target rap vocal track for <Subject 1>, providing his exact vocal timbre ({me.get('voice', 'male rapper')}) and syllable-by-syllable rhythm during {ts_start_str}–{ts_end_str}, followed by silence."
    )
    ret_lines.append(
        f"<Audio 1>: fully_copy - Reused 1:1 as the target vocal track; synchronize <Subject 1>'s lip movements, jaw openings, and syllable articulation directly to <Audio 1> during {ts_start_str}–{ts_end_str}."
    )

    listener_clause = (
        c.get("listener")
        or (f" while <Subject 2> stands on screen-right facing left with his mouth completely closed, watching silently"
            if two_shot else "")
    )

    return (
        "subject_definitions:\n"
        + "\n".join(subj_lines)
        + "\n\nsummary:\n"
        + f"[reference generation + audio reuse] Inside {venue_desc}, <Subject 1> performs an energetic {lang_tag} battle-rap line synced syllable-by-syllable to <Audio 1>, {mic_summary}{listener_clause}.\n\n"
        + "retention_analysis:\n"
        + "\n".join(ret_lines)
        + "\n\ndetailed_description:\n"
        + f"[Shot 1] r34l1sm, Facial Realism, realistic ARRI Alexa Mini LF 50mm lens cinematography, Kodak Vision3 500T film look, natural soft matte skin texture with fine pores, zero oily shine, dramatic low-key 1890s spotlighting with warm amber glow against cool electric blue haze. {cam_desc}. "
        + f"During {ts_start_str}–{ts_end_str}, {mic_detail}, <Subject 1> raps directly into the camera with lively, unmistakable syllable-by-syllable lip-sync and expressive jaw articulation matching <Audio 1>, {action_desc}{listener_clause}: <d>[{lang_tag}]{c['text']}</d> "
        + f"Immediately during {ts_end_str}–{ts_total_str}, <Subject 1> closes his mouth naturally and holds a fierce, confident stare into the lens{listener_clause}. No subtitles, no on-screen text.\n\n"
        + "overall_soundscape:\n"
        + f"Clear, punchy foreground rap vocal performance from <Subject 1> during {ts_start_str}–{ts_end_str} synced 1:1 to <Audio 1> in an underground industrial arena.\n\n"
        + "non_diegetic_music:\n"
        + "N/A — <Audio 1> is directly reused 1:1 as the target vocal track."
    )


def fit_frames(line_dur: float, fps: int = 24) -> int:
    """Pick the clip length (frames) for a rap line of `line_dur` seconds.

    Must return a 17k+5 frame count (73, 90, 107, 124, ...) so the H3 temporal latent grid stays aligned.
    """
    # 0.35 s tail: H3 sometimes starts singing 0.1-0.3 s late (see qa.py), plus the 0.05 s fade-out.
    # Shortest 17k+5 length that fits line + tail, capped at the legacy 124 frames (5.167 s).
    need = math.ceil((line_dur + 0.35) * fps)
    k = max(4, math.ceil((need - 5) / 17))
    return min(17 * k + 5, 124)


def build_single_clip_workflow(
    c: dict,
    comfy_img_names: list,
    comfy_audio_name: str,
    prompt_text: str,
    steps: int = 8,
    seed: int = 2026110501,
    length_frames: int = 124,
    lock_strength: float = 0.85,
) -> dict:
    """Build a self-contained ComfyUI API graph for a single MiniMax-H3 clip (default 124 frames = 17*7+5, 1344x768)."""
    assert (length_frames - 5) % 17 == 0, f"length_frames={length_frames} breaks the 17k+5 ladder"
    wf = {
        "1": {
            "class_type": "UNETLoader",
            "inputs": {
                "unet_name": "minimax_h3_ref2va_pruned_int8_convrot.safetensors",
                "weight_dtype": "default",
            },
        },
        "2": {
            "class_type": "LoraLoaderModelOnly",
            "inputs": {
                "model": ["1", 0],
                "lora_name": "h3-realism-people-t2v-i2v-r2v.safetensors",
                "strength_model": 0.65,
            },
        },
        "3": {
            "class_type": "LoraLoaderModelOnly",
            "inputs": {
                "model": ["2", 0],
                "lora_name": "minimax-h3-facial-realism-closeup-cp2000.safetensors",
                "strength_model": 0.35,
            },
        },
        "4": {
            "class_type": "LoraLoaderModelOnly",
            "inputs": {
                "model": ["3", 0],
                "lora_name": "minimax_h3_ref2v_turbo_8step_v1.1_768p_comfyui_bf16.safetensors",
                "strength_model": 0.70 if steps <= 8 else 0.55,
            },
        },
        "5": {
            "class_type": "MiniMaxH3SigmaShift",
            "inputs": {
                "model": ["4", 0],
                "shift_video": 12.0,
                "shift_audio": 1.5,
            },
        },
        "6": {
            "class_type": "CLIPLoader",
            "inputs": {
                "clip_name": "qwen3vl_32b_heretic_minimax_h3_nvfp4.safetensors",
                "type": "minimax",
                "device": "default",
            },
        },
        "7": {
            "class_type": "VAELoader",
            "inputs": {"vae_name": "minimax_h3_video_vae_fp16.safetensors"},
        },
        "8": {
            "class_type": "VAELoader",
            "inputs": {"vae_name": "minimax_h3_audio_vae_fp32.safetensors"},
        },
        "14": {
            "class_type": "BasicScheduler",
            "inputs": {
                "model": ["5", 0],
                "scheduler": "simple",
                "steps": steps,
                "denoise": 1.0,
            },
        },
        "15": {
            "class_type": "MiniMaxH3SigmasTail",
            "inputs": {
                "sigmas": ["14", 0],
                "tail_steps": 2 if steps <= 8 else 3,
                "strength": 0.6,
            },
        },
        "16": {
            "class_type": "KSamplerSelect",
            "inputs": {"sampler_name": "res_multistep"},
        },
    }

    r2v_inputs = {
        "clip": ["6", 0],
        "vae": ["7", 0],
        "audio_vae": ["8", 0],
        "width": 1344,
        "height": 768,
        "length": length_frames,
        "ref_image_size": "max",
        "prompt": prompt_text,
    }

    for idx, img_name in enumerate(comfy_img_names[:5]):
        nid = str(100 + idx)
        wf[nid] = {"class_type": "LoadImage", "inputs": {"image": img_name}}
        r2v_inputs[f"ref_images.ref_image_{idx}"] = [nid, 0]

    sampler_latent_src = ["20", 1]
    if comfy_audio_name:
        wf["110"] = {"class_type": "LoadAudio", "inputs": {"audio": comfy_audio_name}}
        r2v_inputs["ref_audios.ref_audio_0"] = ["110", 0]
        wf["111"] = {
            "class_type": "VAEEncodeAudio",
            "inputs": {"audio": ["110", 0], "vae": ["8", 0]},
        }
        wf["22"] = {
            "class_type": "H3LockAudioLatent",
            "inputs": {
                "av_latent": ["20", 1],
                "encoded_audio": ["111", 0],
                "lock_strength": lock_strength,
            },
        }
        sampler_latent_src = ["22", 0]

    wf["20"] = {"class_type": "MiniMaxH3ReferenceToVideo", "inputs": r2v_inputs}
    wf["21"] = {
        "class_type": "BunnyH3ConditioningBridge",
        "inputs": {
            "conditioning": ["20", 0],
            "adapter": "BUNNY_H3_ActionLogic_Bridge_V2.safetensors",
            "alpha": 0.14 if c["kind"] == "rap" else 0.22,
            "magnitude_match": "per_token",
            "enabled": True,
        },
    }
    wf["25"] = {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}}
    wf["26"] = {
        "class_type": "BasicGuider",
        "inputs": {"model": ["5", 0], "conditioning": ["21", 0]},
    }
    wf["27"] = {
        "class_type": "SamplerCustomAdvanced",
        "inputs": {
            "noise": ["25", 0],
            "guider": ["26", 0],
            "sampler": ["16", 0],
            "sigmas": ["15", 0],
            "latent_image": sampler_latent_src,
        },
    }
    wf["30"] = {"class_type": "LTXVSeparateAVLatent", "inputs": {"av_latent": ["27", 0]}}
    wf["31"] = {"class_type": "VAEDecode", "inputs": {"samples": ["30", 0], "vae": ["7", 0]}}
    wf["32"] = {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["30", 1], "vae": ["8", 0]}}
    wf["35"] = {
        "class_type": "VHS_VideoCombine",
        "inputs": {
            "images": ["31", 0],
            "audio": ["32", 0],
            "frame_rate": 24.0,
            "loop_count": 0,
            "filename_prefix": f"RapBattle_{c['id']}",
            "format": "video/h264-mp4",
            "pix_fmt": "yuv420p",
            "crf": 18,
            "save_metadata": False,
            "trim_to_audio": False,
            "pingpong": False,
            "save_output": True,
        },
    }
    return wf


def submit_and_wait(wf: dict, clip_id: str) -> Path:
    req = urllib.request.Request(
        f"{API_URL}/prompt",
        data=json.dumps({"prompt": wf}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    resp = json.loads(urllib.request.urlopen(req, timeout=30).read().decode("utf-8"))
    pid = resp["prompt_id"]
    print(f"   ▶ Submitted {clip_id} -> prompt_id={pid}", flush=True)
    t0 = time.time()
    while True:
        time.sleep(4)
        h_raw = urllib.request.urlopen(f"{API_URL}/history/{pid}", timeout=15).read().decode("utf-8")
        h = json.loads(h_raw) if h_raw else {}
        if pid in h:
            st = h[pid].get("status", {})
            if st.get("status_str") == "error":
                raise RuntimeError(f"ComfyUI error on {clip_id}: {json.dumps(st)[:500]}")
            outputs = h[pid].get("outputs", {})
            if "35" in outputs:
                gifs = outputs["35"].get("gifs") or outputs["35"].get("videos") or []
                # Prefer the muxed `-audio.mp4` file so qa.py can verify audio-visual lip-sync correlation
                for prefer_audio in (True, False):
                    for g in gifs:
                        fn = g.get("filename", "")
                        sub = g.get("subfolder", "")
                        if fn.endswith("-audio.mp4") if prefer_audio else fn.endswith(".mp4"):
                            cand = LOCAL_COMFY / "output" / sub / fn
                            if cand.exists():
                                print(f"   ✅ {clip_id} rendered in {time.time() - t0:.1f}s -> {cand.name}", flush=True)
                                return cand
                # Fallback glob (prefer -audio.mp4 first)
                matches_aud = sorted((LOCAL_COMFY / "output").glob(f"RapBattle_{clip_id}*-audio.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
                if matches_aud:
                    print(f"   ✅ {clip_id} rendered in {time.time() - t0:.1f}s -> {matches_aud[0].name}", flush=True)
                    return matches_aud[0]
                matches = sorted((LOCAL_COMFY / "output").glob(f"RapBattle_{clip_id}*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
                if matches:
                    print(f"   ✅ {clip_id} rendered in {time.time() - t0:.1f}s -> {matches[0].name}", flush=True)
                    return matches[0]
            break
    raise RuntimeError(f"Output MP4 not found for {clip_id} (prompt_id={pid})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ep")
    ap.add_argument("--ids", nargs="*", default=None)
    ap.add_argument("--steps", type=int, default=8)
    ap.add_argument("--lock-strength", type=float, default=0.85,
                    help="H3LockAudioLatent strength; 1.0 = keep our vocal latent bit-exact (no re-singing)")
    ap.add_argument("--fit", action="store_true", help="Size each rap clip to its line (17k+5 frames) instead of fixed 124")
    ap.add_argument("--tag", default=None, help="Sample mode: write clips/<id>_<tag>.mp4 and leave picks/shifts untouched")
    ap.add_argument("--seed", type=int, default=None, help="Base seed (default 2026110600)")
    ap.add_argument("--mic", choices=["handheld", "stand"], default="handheld", help="Microphone staging for rap shots")
    ap.add_argument("--static-cam", action="store_true", help="Locked-off chest-up framing for rap shots (no push-in)")
    args = ap.parse_args()

    ep = os.path.abspath(args.ep)
    e = load_episode(ep)
    clips_list = jload(os.path.join(ep, "work", "clips.json"))
    clips_map = {c["id"]: c for c in clips_list}
    picks_p = os.path.join(ep, "work", "picks.json")
    shifts_p = os.path.join(ep, "work", "shifts.json")
    picks = jload(picks_p) if os.path.exists(picks_p) else {}
    shifts = jload(shifts_p) if os.path.exists(shifts_p) else {}

    target_ids = args.ids if args.ids else [c["id"] for c in clips_list if c["id"] not in picks]
    if not target_ids:
        print("✅ All clips already generated in picks.json!", flush=True)
        return

    ensure_comfy_running()
    comfy_in = LOCAL_COMFY / "input"
    comfy_in.mkdir(parents=True, exist_ok=True)
    drive_out_dir = DRIVE_COMFY / "output" / "rap_battle" / e["title"] / "clips"
    drive_out_dir.mkdir(parents=True, exist_ok=True)
    os.makedirs(os.path.join(ep, "clips"), exist_ok=True)

    # Copy all unique reference images to /content/ComfyUI/input/
    for ref_png in (Path(ep) / "refs").glob("*.png"):
        shutil.copy2(ref_png, comfy_in / f"rap_{ref_png.name}")
    for src_p in (Path(ep) / "work").glob("*.png"):  # busts, clean face crops, ...
        shutil.copy2(src_p, comfy_in / f"rap_{src_p.name}")

    total_t0 = time.time()
    for idx, cid in enumerate(target_ids, 1):
        c = clips_map[cid]
        print(f"\n🎬 [{idx}/{len(target_ids)}] Rendering {cid} ({c['move']}, kind={c['kind']})...", flush=True)
        comfy_imgs = [f"rap_{k}.png" for k in c["image_keys"]]
        comfy_aud = None
        local_aud = None
        if c.get("frames"):
            n_frames = int(c["frames"])
        else:
            n_frames = fit_frames(c["audio"][1] - c["audio"][0]) if (args.fit and c["kind"] == "rap") else 124
        total_dur = round(n_frames / 24.0, 3)
        print(f"   ⏱️ {n_frames} frames = {total_dur:.3f}s | lock_strength={args.lock_strength} | steps={args.steps}", flush=True)
        if c["kind"] == "rap":
            local_aud = cut_audio(ep, c, total_dur)
            comfy_aud = f"rap_audio_{cid}.wav"
            shutil.copy2(local_aud, comfy_in / comfy_aud)

        prompt_text = adapt_prompt_for_comfy_h3(c, e, total_dur, mic=args.mic, static_cam=args.static_cam)
        seed = (args.seed if args.seed is not None else 2026110600) + idx
        wf = build_single_clip_workflow(c, comfy_imgs, comfy_aud, prompt_text, steps=args.steps, seed=seed,
                                        length_frames=n_frames, lock_strength=args.lock_strength)
        raw_mp4 = submit_and_wait(wf, cid)

        take = 1
        final_clip = Path(ep) / "clips" / (f"{cid}_{args.tag}.mp4" if args.tag else f"{cid}_t{take}.mp4")
        shutil.copy2(raw_mp4, final_clip)
        shutil.copy2(final_clip, drive_out_dir / final_clip.name)

        if local_aud:
            try:
                verdict = qa.analyze(str(final_clip), local_aud)
                print(f"   🔍 QA {cid}: {verdict}", flush=True)
                if verdict.get("shift", 0) > 0.03 and verdict.get("corr", 0) >= 0.5:
                    shifts[cid] = verdict["shift"]
            except Exception as qa_err:
                print(f"   ⚠️ QA warning on {cid}: {qa_err}", flush=True)
        if args.tag:  # sample run: keep picks/shifts untouched
            continue
        picks[cid] = take
        jsave(picks_p, picks)
        jsave(shifts_p, shifts)
        shutil.copy2(picks_p, drive_out_dir.parent / "picks.json")
        shutil.copy2(shifts_p, drive_out_dir.parent / "shifts.json")

    print(f"\n🎉 All {len(target_ids)} clips rendered in {(time.time() - total_t0)/60:.1f} min!", flush=True)


if __name__ == "__main__":
    main()
