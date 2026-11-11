#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Colab G4 (96GB Blackwell) Open-Weight MiniMax-H3 Batch Clip Runner for Ancient/Historical Rap Battle.
Replaces the paid $16 MiniMax commercial API (`h3run.py`) with local ComfyUI `MiniMaxH3ReferenceToVideo` on Colab G4,
with optional Stage-2 3-Step `ComfyUI-Tessera` Native 2.7K (`2688x1536`) Latent Refinement (`--tessera-2k`).

Usage on Colab G4:
  python3 h3_colab_runner.py <episode_dir> [--ids A01 A02 ...] [--steps 12] [--realism-v2] [--tessera-2k]
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


FAST_MODELS = Path("/content/fast_models")
REF2V_TURBO_LORA = "minimax_h3_ref2v_turbo_8step_v1.1_768p_comfyui_bf16.safetensors"
REF2V_TURBO_URL = (
    "https://huggingface.co/lightx2v/Minimax-h3-Turbo/resolve/main/"
    "minimax_h3_ref2v_turbo_8step_v1.1_768p_comfyui_bf16.safetensors"
)
TAOMATE_3STEP_LORA = "TaoMate-H3-3step-ComfyUI.safetensors"
TAOMATE_3STEP_URL = (
    "https://huggingface.co/CZMartin22/TaoMate-H3-3step-ComfyUI/resolve/main/"
    "TaoMate-H3-3step-ComfyUI.safetensors"
)
LMS_R64_LORA = "minimax_h3_lms_v1.0_r64.safetensors"
LMS_R64_URL = (
    "https://huggingface.co/Alissonerdx/Minimax-H3-ComfyUI/resolve/main/loras/"
    "minimax_h3_lms_v1.0_r64.safetensors"
)
SINGULARITY_UNET = "Minimax-h3_Singularity_ref2va_Pruned_v1.3_int8.safetensors"


def is_comfy_up() -> bool:
    try:
        urllib.request.urlopen(f"{API_URL}/system_stats", timeout=3)
        return True
    except Exception:
        return False


def _ensure_lora_on_nvme(lora_name: str, hf_url: str, min_bytes: int = 10_000_000) -> None:
    """Guarantee a LoRA exists on local NVMe and is symlinked into /content/ComfyUI/models/loras."""
    nvme_lora = FAST_MODELS / "loras" / lora_name
    nvme_lora.parent.mkdir(parents=True, exist_ok=True)
    drive_lora = DRIVE_COMFY / "models" / "loras" / lora_name
    drive_lora.parent.mkdir(parents=True, exist_ok=True)
    if not (nvme_lora.exists() and nvme_lora.stat().st_size > min_bytes):
        if drive_lora.exists() and drive_lora.stat().st_size > min_bytes:
            print(f"⚡ Copying {lora_name} from Drive to local NVMe...", flush=True)
            shutil.copy2(drive_lora, nvme_lora)
        else:
            print(f"⬇️ Pulling {lora_name} from HF CDN to local NVMe...", flush=True)
            subprocess.run(["curl", "-sL", "--fail", "-o", str(nvme_lora), hf_url], check=True)
            try:
                shutil.copy2(nvme_lora, drive_lora)
            except Exception:
                pass
    comfy_loras = LOCAL_COMFY / "models" / "loras"
    if comfy_loras.exists():
        link_p = comfy_loras / lora_name
        if not link_p.exists():
            if link_p.is_symlink():
                link_p.unlink()
            os.symlink(nvme_lora, link_p)


def _ensure_ref2v_turbo_lora() -> None:
    _ensure_lora_on_nvme(REF2V_TURBO_LORA, REF2V_TURBO_URL, min_bytes=10_000_000)


def ensure_comfy_running(realism_v2: bool = False) -> None:
    profile = "scheme_a" if realism_v2 else "scheme_dance"
    if realism_v2:
        _ensure_ref2v_turbo_lora()
    if is_comfy_up():
        if realism_v2 and not (LOCAL_COMFY / "models" / "diffusion_models" / SINGULARITY_UNET).exists():
            print(f"🔄 ComfyUI 运行中但未挂载 {SINGULARITY_UNET}，切换至 scheme_a 重启...", flush=True)
        else:
            print("⚡ ComfyUI 已在 127.0.0.1:8188 运行中！", flush=True)
            return
    launcher = Path("/tmp/launch_g4_comfyui_fast.py")
    if not launcher.exists():
        launcher = Path("/content/drive/MyDrive/AI_Workstation/scripts/launch_g4_comfyui_fast.py")
    print(f"🚀 正在启动 launch_g4_comfyui_fast.py ({profile} 极速模式)...", flush=True)
    subprocess.run([sys.executable, "-u", str(launcher), "--profile", profile], check=True)
    if realism_v2:
        _ensure_ref2v_turbo_lora()
    for _ in range(60):
        if is_comfy_up():
            return
        time.sleep(2)
    raise RuntimeError("❌ ComfyUI 启动超时，请检查 /tmp/comfyui.log")


def _setup_tessera_and_restart_offload() -> dict:
    """Stage Tessera 3-step LoRAs, patch ComfyUI-Tessera, and restart ComfyUI without --highvram for 2.7K tiling."""
    _ensure_lora_on_nvme(TAOMATE_3STEP_LORA, TAOMATE_3STEP_URL, min_bytes=500_000_000)
    _ensure_lora_on_nvme(LMS_R64_LORA, LMS_R64_URL, min_bytes=500_000_000)

    tess_dir = LOCAL_COMFY / "custom_nodes" / "ComfyUI-Tessera"
    drv_tess = DRIVE_COMFY / "custom_nodes" / "ComfyUI-Tessera"
    if not (tess_dir / "tessera" / "nodes.py").exists():
        shutil.rmtree(tess_dir, ignore_errors=True)
        if (drv_tess / "tessera" / "nodes.py").exists():
            print("📦 Copying ComfyUI-Tessera from Drive to local NVMe...", flush=True)
            shutil.copytree(drv_tess, tess_dir)
        else:
            print("⬇️ Cloning ComfyUI-Tessera onto local NVMe...", flush=True)
            subprocess.run(
                ["git", "clone", "--depth", "1", "https://github.com/hashu786/ComfyUI-Tessera", str(tess_dir)],
                check=True,
            )
            try:
                shutil.rmtree(tess_dir / ".git", ignore_errors=True)
                shutil.copytree(tess_dir, drv_tess, dirs_exist_ok=True)
            except Exception:
                pass

    nodes_py = tess_dir / "tessera" / "nodes.py"
    nodes_txt = nodes_py.read_text(encoding="utf-8")
    old_prep = """    def prep(x):
        g = torch.nn.functional.avg_pool2d(
            x.float().mean(dim=(0, 3))[None, None], k, k)[0, 0]
        wy = torch.hann_window(g.shape[0], periodic=False).view(-1, 1)
        wx = torch.hann_window(g.shape[1], periodic=False).view(1, -1)
        return (g - g.mean()) * (wy * wx)"""
    new_prep = """    def prep(x):
        g = torch.nn.functional.avg_pool2d(
            x.detach().cpu().float().mean(dim=(0, 3))[None, None], k, k)[0, 0]
        wy = torch.hann_window(g.shape[0], periodic=False, device=g.device).view(-1, 1)
        wx = torch.hann_window(g.shape[1], periodic=False, device=g.device).view(1, -1)
        return (g - g.mean()) * (wy * wx)"""
    if old_prep in nodes_txt:
        nodes_txt = nodes_txt.replace(old_prep, new_prep)

    if "TesseraSigmas" not in nodes_txt:
        nodes_txt += """

class TesseraSigmas:
    CATEGORY = "Tessera"
    RETURN_TYPES = ("SIGMAS",)
    FUNCTION = "run"
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"sigmas": ("STRING", {"default": "1.0, 0.7, 0.4, 0.0"})}}
    def run(self, sigmas):
        vals = [float(x.strip()) for x in sigmas.replace(";", ",").split(",") if x.strip()]
        return (torch.tensor(vals, dtype=torch.float32),)

NODE_CLASS_MAPPINGS["TesseraSigmas"] = TesseraSigmas
NODE_DISPLAY_NAME_MAPPINGS["TesseraSigmas"] = "Tessera Sigmas"
"""
    nodes_py.write_text(nodes_txt, encoding="utf-8")

    # Restart ComfyUI WITHOUT --highvram so Qwen3-VL-32B offloads after text/video conditioning,
    # leaving the full 96GB Blackwell VRAM free for 2688x1536 DiT + Video VAE tiles.
    print("🔄 Restarting ComfyUI without --highvram for Stage-2 Tessera 2.7K (2688x1536) refinement...", flush=True)
    subprocess.run(["pkill", "-f", "python.*main.py"], check=False)
    time.sleep(2)
    tess_log = Path("/tmp/comfyui_tessera.log")
    log_f = open(tess_log, "w")
    subprocess.Popen(
        [sys.executable, "main.py", "--listen", "127.0.0.1", "--port", "8188", "--disable-mmap", "--fast"],
        cwd=str(LOCAL_COMFY),
        stdout=log_f,
        stderr=subprocess.STDOUT,
    )
    for _ in range(90):
        if is_comfy_up():
            try:
                obj_info = json.loads(urllib.request.urlopen(f"{API_URL}/object_info", timeout=10).read().decode("utf-8"))
                if "TesseraRefine" in obj_info and "TesseraEncode" in obj_info:
                    print("✅ ComfyUI + TesseraRefine 2.7K engine ready!", flush=True)
                    return obj_info
            except Exception:
                pass
        time.sleep(2)
    tail = tess_log.read_text(errors="ignore")[-2500:] if tess_log.exists() else ""
    raise RuntimeError(f"❌ ComfyUI Tessera restart failed or TesseraRefine missing:\n{tail}")


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
                              static_cam: bool = False, realism_v2: bool = False) -> str:
    """Build the official 6-section MiniMaxH3ReferenceToVideo structured prompt (`ref-en.txt` protocol)."""
    p = _adapt_prompt(c, e, total_dur, mic, static_cam, realism_v2=realism_v2)
    if c.get("aspect") == "9:16":   # vertical Shorts: every framing phrase must describe the tall frame
        p = p.replace("16:9 frame", "vertical 9:16 frame").replace("16:9", "vertical 9:16")
    return p


def _adapt_prompt(c: dict, e: dict, total_dur: float, mic: str, static_cam: bool, realism_v2: bool = False) -> str:
    lang = e.get("language", "en")
    if c["kind"] != "rap" or not c.get("text") or c.get("raw"):
        p = c["prompt"]
        for i in range(1, 10):
            p = re.sub(rf"\bImage {i}\b", f"<Picture {i}>", p)
        p = re.sub(r"\bAudio 1\b", "<Audio 1>", p)
        return "r34l1sm, Facial Realism, " + p

    who = c.get("who", "a")
    me = e[who]
    them = e["b" if who == "a" else "a"]
    two_shot = bool(c.get("two_shot"))
    wide = bool(c.get("wide"))  # wide / reverse shots: deep focus, no fixed screen side, not singing into the lens
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
    elif realism_v2:
        mic_name = e.get("mic_en", "vintage chrome handheld microphone with a round mesh head")
        mic_summary = (f"holding the {mic_name} close just below his lower lip angled upward at 45 degrees near the bottom edge of the frame, "
                       "chrome mesh head softly foreshortened in the lower foreground while his upper lip, mouth corners, and jaw stay 100% uncovered")
        mic_detail = (f"holding the {mic_name} in his right hand just an inch below his lower lip angled upward at 45 degrees "
                      "(the chrome mesh head sits prominently in the lower foreground like a real underground battle rapper, "
                      "never crossing or occluding his upper lip, mouth corners, or jaw)")
    else:
        mic_summary = f"holding the {e.get('mic_en', 'vintage microphone')} at upper-chest height below his chin so his mouth and lips remain 100% uncovered"
        mic_detail = (f"holding the {e.get('mic_en', 'silver corded microphone')} in his right hand at upper-chest height a few inches below his chin "
                      "(completely clear of his face so his mouth, lips, and jaw are 100% unobstructed and visible)")
    venue_desc = e.get("venue_en", "an 1890s industrial power plant rap battle arena")
    crowd_motion = e.get("crowd_motion_en", "")
    light_desc = e.get("light_en", "dramatic low-key 1890s spotlighting with warm amber glow against cool electric blue haze")
    action_desc = c.get("action") or "fierce and confident, his free hand chopping the air on the beat"
    if realism_v2:
        action_desc += (
            ", brows knitting and lifting fiercely on stressed syllables, eyes narrowing with raw live-action intensity, "
            "subtle skin creases flexing at the bridge of his nose, jaw and neck muscles tensing visibly, faint sweat sheen "
            "catching the backlight on his brow and cheekbones, torso leaning forward 15 degrees with natural boom-bap head nods on every beat"
        )
    move = c.get("move", "M3")

    if c.get("static") is not None:  # per-shot override of --static-cam (handheld / moving-camera shots)
        static_cam = bool(c["static"])
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
        f"<Subject 1> is {me['name_en']} ({me['look']}) from <Picture 1>, warm natural lifelike human skin tone with fine pores."
    ]
    ret_lines = [
        f"<Subject 1> (appears in [Shot 1]): fully_preserved - Strictly preserve exact facial bone structure, warm natural blood-toned skin, hairstyle, facial hair (or lack of it), outfit, and {me.get('prop', 'prop')} from <Picture 1>."
    ]
    if two_shot:
        subj_lines.append(
            f"<Subject 2> is {them['name_en']} ({them['look']}) from <Picture 2>, warm natural lifelike human skin tone with fine pores."
        )
        ret_lines.append(
            f"<Subject 2> (appears in [Shot 1]): fully_preserved - Strictly preserve exact facial structure, warm natural skin tone, and outfit from <Picture 2>{'' if wide else ' on ' + c.get('listener_side', 'screen-right')}, keeping his mouth closed in silent listening throughout this clip."
        )
    bg_clause = ""
    if c.get("bg"):  # shared stage plate so every shot of this singer sits in the same place of the same arena
        k = c["image_keys"].index(c["bg"]) + 1
        if realism_v2 and not wide:
            subj_lines.append(
                f"<Picture {k}> is the packed underground battle arena behind <Subject 1> rendered at shallow T2.2 optical bokeh: warm glowing 2700K candle chandeliers and out-of-focus cheering scholar silhouettes below the stage."
            )
            ret_lines.append(
                f"Background (appears in [Shot 1]): reference - Keep the warm 2700K amber chandelier bokeh and packed arena atmosphere of <Picture {k}> softly out of focus at shallow T2.2 depth of field behind <Subject 1>; the out-of-focus crowd silhouettes below stage level are alive and continuously bouncing, nodding heads, and pumping raised arms and hats on every boom-bap beat (softly blurred optical bokeh silhouettes only, never razor-sharp background faces, never an empty black wall)."
            )
            bg_clause = (
                f" Behind him, the packed arena from <Picture {k}> sits in creamy shallow T2.2 Cooke optical bokeh "
                "where warm 2700K candle chandelier bokeh orbs glow overhead and softly blurred crowd silhouettes below the stage bounce, sway, and pump their raised arms continuously to the boom-bap beat without any sharp background faces."
            )
        else:
            subj_lines.append(f"<Picture {k}> is the arena environment directly behind <Subject 1>: the same set, lights and "
                              f"crowd in every shot of him.")
            if c.get("bg_ref") == "reference":
                ret_lines.append(f"Background (appears in [Shot 1]): reference - Use <Picture {k}> only as a reference for the set, "
                                 f"flags, light colours and the costumes of the crowd behind <Subject 1>, "
                                 + ("in deep focus so the whole room reads clearly. " if wide else "softly out of focus with shallow depth of field. ")
                                 + "Every person in the crowd is newly animated and keeps moving to the beat the whole time.")
            else:
                ret_lines.append(f"Background (appears in [Shot 1]): fully_preserved - Keep the exact environment, set dressing, light "
                             f"colours and crowd of <Picture {k}> behind <Subject 1>, "
                             + ("in deep focus so the whole room reads clearly." if wide else "softly out of focus with shallow depth of field.")
                             + (" Preserve how the crowd looks, not its pose: the crowd is alive and keeps moving the whole time, "
                                "never a frozen still image." if crowd_motion else ""))
            bg_clause = f" The background behind him is the arena from <Picture {k}>" + (", in deep focus." if wide else ", softly out of focus.")
            if crowd_motion:
                bg_clause += f" The crowd behind him is never still: {crowd_motion}."
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

    cinema_header = (
        f"[Shot 1] r34l1sm, Facial Realism, live-action 35mm cinema film shot on ARRI Alexa Mini LF with vintage Cooke Panchro/i Classic {c.get('lens', '50mm')} prime lens at T2.2, crisp optical contrast with deep solid blacks (zero milky grey haze), Kodak Vision3 500T 5219 color negative film stock, warm natural blood-toned human skin with fine pores and micro-texture, zero CGI plastic sheen, {light_desc}."
        if realism_v2 else
        f"[Shot 1] r34l1sm, Facial Realism, realistic ARRI Alexa Mini LF {c.get('lens', '50mm')} lens cinematography, Kodak Vision3 500T film look, natural soft matte skin texture with fine pores, zero oily shine, {light_desc}."
    )

    return (
        "subject_definitions:\n"
        + "\n".join(subj_lines)
        + "\n\nsummary:\n"
        + f"[reference generation + audio reuse] Inside {venue_desc}, <Subject 1> performs an energetic {lang_tag} battle-rap line synced syllable-by-syllable to <Audio 1>, {mic_summary}{listener_clause}"
        + (f", while {crowd_motion}" if crowd_motion else "")
        + ".\n\n"
        + "retention_analysis:\n"
        + "\n".join(ret_lines)
        + "\n\ndetailed_description:\n"
        + f"{cinema_header} {cam_desc}.{bg_clause} "
        + f"During {ts_start_str}–{ts_end_str}, {mic_detail}, <Subject 1> raps {'out toward the arena' if wide else 'directly into the camera'} with lively, unmistakable syllable-by-syllable lip-sync and expressive jaw articulation matching <Audio 1>, {action_desc}{listener_clause}: <d>[{lang_tag}]{c['text']}</d> "
        + f"Immediately during {ts_end_str}–{ts_total_str}, <Subject 1> closes his mouth naturally and holds a fierce, confident stare {'at his opponent' if wide else 'into the lens'}{listener_clause}. No subtitles, no on-screen text.\n\n"
        + "overall_soundscape:\n"
        + f"Clear, punchy foreground rap vocal performance from <Subject 1> during {ts_start_str}–{ts_end_str} synced 1:1 to <Audio 1> in {e.get('arena_sound_en', 'an underground industrial arena')}.\n\n"
        + "non_diegetic_music:\n"
        + "N/A — <Audio 1> is directly reused 1:1 as the target vocal track."
    )


def fit_frames(line_dur: float, fps: int = 24) -> int:
    """Pick the clip length (frames) for a rap line of `line_dur` seconds.

    Must return a 17k+5 frame count (73, 90, 107, 124, ...) so the H3 temporal latent grid stays aligned.
    """
    need = math.ceil((line_dur + 0.35) * fps)
    k = max(4, math.ceil((need - 5) / 17))
    return min(17 * k + 5, 158)


def build_single_clip_workflow(
    c: dict,
    comfy_img_names: list,
    comfy_audio_name: str,
    prompt_text: str,
    steps: int = 8,
    seed: int = 2026110501,
    length_frames: int = 124,
    lock_strength: float = 0.85,
    realism_v2: bool = False,
) -> dict:
    """Build a self-contained ComfyUI API graph for a single MiniMax-H3 clip (default 124 frames = 17*7+5, 1344x768;
    768x1344 when c["aspect"] == "9:16")."""
    assert (length_frames - 5) % 17 == 0, f"length_frames={length_frames} breaks the 17k+5 ladder"
    default_closeup = 0.45 if realism_v2 else 0.35
    turbo_strength = 0.75 if (realism_v2 and steps >= 10) else (0.70 if steps <= 8 else 0.55)
    wf = {
        "1": {
            "class_type": "UNETLoader",
            "inputs": {
                "unet_name": SINGULARITY_UNET if realism_v2 else "minimax_h3_ref2va_pruned_int8_convrot.safetensors",
                "weight_dtype": "default",
            },
        },
        "2": {
            "class_type": "LoraLoaderModelOnly",
            "inputs": {
                "model": ["1", 0],
                "lora_name": "h3-realism-people-t2v-i2v-r2v.safetensors",
                "strength_model": 0.75 if realism_v2 else 0.65,
            },
        },
        "3": {
            "class_type": "LoraLoaderModelOnly",
            "inputs": {
                "model": ["2", 0],
                "lora_name": "minimax-h3-facial-realism-closeup-cp2000.safetensors",
                "strength_model": float(c.get("closeup_lora", default_closeup)),
            },
        },
        "4": {
            "class_type": "LoraLoaderModelOnly",
            "inputs": {
                "model": ["3", 0],
                "lora_name": REF2V_TURBO_LORA,
                "strength_model": turbo_strength,
            },
        },
        "5": {
            "class_type": "MiniMaxH3SigmaShift",
            "inputs": {
                "model": ["4", 0],
                "shift_video": 12.0,
                "shift_audio": 3.0 if realism_v2 else 1.5,
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
                "tail_steps": 3 if realism_v2 else (2 if steps <= 8 else 3),
                "strength": 0.50 if realism_v2 else 0.6,
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
        "width": 768 if c.get("aspect") == "9:16" else 1344,
        "height": 1344 if c.get("aspect") == "9:16" else 768,
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
            "alpha": 0.10 if (realism_v2 and c["kind"] == "rap") else (0.14 if c["kind"] == "rap" else 0.22),
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
            "crf": 14 if realism_v2 else 18,
            "save_metadata": False,
            "trim_to_audio": False,
            "pingpong": False,
            "save_output": True,
        },
    }
    return wf


def build_tessera_2k_workflow(
    c: dict,
    s1_mp4_name: str,
    length_frames: int,
    seed: int = 786110,
    realism_v2: bool = True,
    has_ultrasharp: bool = True,
    obj_info: dict | None = None,
) -> dict:
    """Build Stage-2 3-Step ComfyUI-Tessera Native 2.7K (2688x1536 / 1536x2688) latent refinement workflow."""
    is_vert = c.get("aspect") == "9:16"
    out_w, out_h = (1536, 2688) if is_vert else (2688, 1536)
    # Exact multiples of 64; <=90f fits in 2 tiles (1408x1536), >90f uses 3 tiles (1088x1536) well within 96GB VRAM
    if is_vert:
        tile_w, tile_h = 1536, (1408 if length_frames <= 90 else 1088)
    else:
        tile_w, tile_h = (1408 if length_frames <= 90 else 1088), 1536

    tess_prompt = (
        "subject_definitions:\n"
        "<Video 1>: the reference video. Its picture, motion, lip-sync, framing, warm cinema lighting, and content are the target video's content.\n"
        "<Picture 1> is a reference of a high resolution upscaled version of the first frame of the video.\n\n"
        "retention_analysis:\n"
        "<Video 1>: fully_preserved - <Video 1> is reproduced one to one as the target video. Every frame, mouth shape, and lighting ratio matches the source.\n\n"
        "Enhance this live-action 35mm cinema video with sharp, crisp 2K details, natural human skin pores, fine hair strands, "
        "and woven velvet fabric micro-texture while preserving warm natural skin tones, shallow optical bokeh in the background, and zero synthetic plastic sheen."
    )

    wf = {
        "1": {
            "class_type": "UNETLoader",
            "inputs": {
                "unet_name": SINGULARITY_UNET if realism_v2 else "minimax_h3_ref2va_pruned_int8_convrot.safetensors",
                "weight_dtype": "default",
            },
        },
        "3": {
            "class_type": "LoraLoaderModelOnly",
            "inputs": {
                "model": ["1", 0],
                "lora_name": TAOMATE_3STEP_LORA,
                "strength_model": 1.0,
            },
        },
        "4": {
            "class_type": "LoraLoaderModelOnly",
            "inputs": {
                "model": ["3", 0],
                "lora_name": LMS_R64_LORA,
                "strength_model": 0.42,
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
        "10": {
            "class_type": "LoadVideo",
            "inputs": {"file": s1_mp4_name},
        },
        "11": {
            "class_type": "GetVideoComponents",
            "inputs": {"video": ["10", 0]},
        },
        "12_f0": {
            "class_type": "ImageFromBatch",
            "inputs": {"image": ["11", 0], "batch_index": 0, "length": 1},
        },
        "14": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "er_sde"}},
        "15": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
        "16": {"class_type": "TesseraSigmas", "inputs": {"sigmas": "1.0, 0.7, 0.4, 0.0"}},
        "22": {
            "class_type": "MiniMaxH3ReferenceToVideo",
            "inputs": {
                "clip": ["6", 0],
                "vae": ["7", 0],
                "audio_vae": ["8", 0],
                "width": out_w,
                "height": out_h,
                "length": length_frames,
                "ref_image_size": "max",
                "ref_videos.ref_video_0": ["11", 0],
                "prompt": tess_prompt,
            },
        },
        "23": {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["22", 0]}},
        "24": {
            "class_type": "TesseraEncode",
            "inputs": {
                "images": ["11", 0],
                "vae": ["7", 0],
                "positive": ["22", 0],
                "upscale_by": 2.0,
                "upscale_method": "lanczos",
                "segment_frames": 56,
                "anchor": ["12", 0],
                "anchor_strength": 0.65,
                "anchor_spread": 3,
            },
        },
        "25": {"class_type": "VAEEncodeAudio", "inputs": {"audio": ["11", 1], "vae": ["8", 0]}},
        "26": {"class_type": "SolidMask", "inputs": {"value": 1.0, "width": 32, "height": 32}},
        "27": {"class_type": "SetLatentNoiseMask", "inputs": {"samples": ["25", 0], "mask": ["26", 0]}},
        "28": {
            "class_type": "LTXVConcatAVLatent",
            "inputs": {"video_latent": ["24", 1], "audio_latent": ["27", 0]},
        },
        "29": {
            "class_type": "TesseraArgs",
            "inputs": {
                "video_ref_crop": "per_tile",
                "image_ref_crop": "per_tile",
                "guide_noise": 0.0,
                "guide_noise_band": "full",
                "guide_noise_t": "per_frame",
                "guide_release": 0.50,
                "guide_inherit": True,
                "hero_guide_noise": -1.0,
                "motion_adapt": True,
                "motion_release_floor": 0.3,
                "fine_below_sigma": 0.75,
                "tile_select": "",
                "tile_limit": 0,
                "flat_skip": 4.0,
                "composite": "pixel",
            },
        },
        "30": {
            "class_type": "TesseraRefine",
            "inputs": {
                "model": ["4", 0],
                "positive": ["24", 0],
                "negative": ["23", 0],
                "latent": ["28", 0],
                "vae": ["7", 0],
                "sampler": ["14", 0],
                "sampler_fine": ["15", 0],
                "sigmas": ["16", 0],
                "args": ["29", 0],
                "spatial_tile": "custom",
                "tile_width": tile_w,
                "tile_height": tile_h,
                "temporal_tile": "off",
                "temporal_size": length_frames,
                "temporal_overlap": 4,
                "context_border": 64,
                "seam_overlap": 32,
                "hero_min": 896,
                "hero_fit": "median",
                "cfg": 1.0,
                "seed": seed,
                "seed_mode": "global",
                "pixel_out": True,
                "console_progress": "overall",
                "prompt": tess_prompt,
            },
        },
        "35": {
            "class_type": "VHS_VideoCombine",
            "inputs": {
                "images": ["30", 2],
                "audio": ["11", 1],
                "frame_rate": 24.0,
                "loop_count": 0,
                "filename_prefix": f"RapBattle2K_{c['id']}",
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

    if has_ultrasharp:
        wf["12_um"] = {"class_type": "UpscaleModelLoader", "inputs": {"model_name": "4x-UltraSharp.pth"}}
        wf["12_up"] = {
            "class_type": "ImageUpscaleWithModel",
            "inputs": {"upscale_model": ["12_um", 0], "image": ["12_f0", 0]},
        }
        wf["12"] = {
            "class_type": "ImageScale",
            "inputs": {
                "image": ["12_up", 0],
                "upscale_method": "lanczos",
                "width": out_w,
                "height": out_h,
                "crop": "disabled",
            },
        }
    else:
        wf["12"] = {
            "class_type": "ImageScale",
            "inputs": {
                "image": ["12_f0", 0],
                "upscale_method": "lanczos",
                "width": out_w,
                "height": out_h,
                "crop": "disabled",
            },
        }

    # Auto-reconcile Tessera node inputs & enum choices against live ComfyUI /object_info
    if obj_info:
        for nid in ("24", "29", "30"):
            ctype = wf[nid]["class_type"]
            c_in = obj_info.get(ctype, {}).get("input", {})
            req_defs = c_in.get("required", {})
            opt_defs = c_in.get("optional", {})
            all_defs = {**opt_defs, **req_defs}
            node_in = wf[nid]["inputs"]
            # Remove any deprecated keys no longer accepted by upstream ComfyUI-Tessera
            if all_defs:
                for k in list(node_in.keys()):
                    if k not in all_defs:
                        node_in.pop(k, None)
            # Fill missing required keys and coerce stale enum strings to valid defaults
            for k, spec in all_defs.items():
                is_req = k in req_defs
                enum_vals = spec[0] if (isinstance(spec, list) and len(spec) >= 1 and isinstance(spec[0], list)) else None
                meta = spec[1] if (isinstance(spec, list) and len(spec) >= 2 and isinstance(spec[1], dict)) else {}
                if k not in node_in and is_req:
                    if "default" in meta:
                        node_in[k] = meta["default"]
                    elif enum_vals:
                        node_in[k] = enum_vals[0]
                elif k in node_in and enum_vals and not isinstance(node_in[k], list) and node_in[k] not in enum_vals:
                    node_in[k] = meta["default"] if ("default" in meta and meta["default"] in enum_vals) else enum_vals[0]
    return wf


def submit_and_wait(wf: dict, clip_id: str, prefix: str | None = None, log_file: Path | None = None) -> Path:
    file_prefix = prefix or f"RapBattle_{clip_id}"
    req = urllib.request.Request(
        f"{API_URL}/prompt",
        data=json.dumps({"prompt": wf}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        resp = json.loads(urllib.request.urlopen(req, timeout=30).read().decode("utf-8"))
    except urllib.error.HTTPError as http_err:
        body = http_err.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"ComfyUI /prompt HTTP {http_err.code} on {clip_id}: {body[:1200]}") from http_err
    pid = resp["prompt_id"]
    print(f"   ▶ Submitted {clip_id} ({file_prefix}) -> prompt_id={pid}", flush=True)
    t0 = time.time()
    while True:
        time.sleep(4)
        h_raw = urllib.request.urlopen(f"{API_URL}/history/{pid}", timeout=15).read().decode("utf-8")
        h = json.loads(h_raw) if h_raw else {}
        if pid in h:
            st = h[pid].get("status", {})
            if st.get("status_str") == "error":
                extra = ""
                if log_file and log_file.exists():
                    extra = "\n" + log_file.read_text(errors="ignore")[-1800:]
                raise RuntimeError(f"ComfyUI error on {clip_id}: {json.dumps(st)[:600]}{extra}")
            outputs = h[pid].get("outputs", {})
            if "35" in outputs:
                gifs = outputs["35"].get("gifs") or outputs["35"].get("videos") or []
                for prefer_audio in (True, False):
                    for g in gifs:
                        fn = g.get("filename", "")
                        sub = g.get("subfolder", "")
                        if fn.endswith("-audio.mp4") if prefer_audio else fn.endswith(".mp4"):
                            cand = LOCAL_COMFY / "output" / sub / fn
                            if cand.exists():
                                print(f"   ✅ {clip_id} rendered in {time.time() - t0:.1f}s -> {cand.name}", flush=True)
                                return cand
                matches_aud = sorted(
                    (LOCAL_COMFY / "output").glob(f"{file_prefix}*-audio.mp4"),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True,
                )
                if matches_aud:
                    print(f"   ✅ {clip_id} rendered in {time.time() - t0:.1f}s -> {matches_aud[0].name}", flush=True)
                    return matches_aud[0]
                matches = sorted(
                    (LOCAL_COMFY / "output").glob(f"{file_prefix}*.mp4"),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True,
                )
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
    ap.add_argument("--realism-v2", action="store_true",
                    help="Live-action 35mm cinema upgrade: Singularity v1.3 + Cooke T2.2 bokeh + warm Rembrandt lighting + lip-level mic")
    ap.add_argument("--tessera-2k", action="store_true",
                    help="Run Stage-2 3-step ComfyUI-Tessera native 2.7K (2688x1536) latent detail refinement after Stage-1")
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

    ensure_comfy_running(realism_v2=args.realism_v2)
    comfy_in = LOCAL_COMFY / "input"
    comfy_in.mkdir(parents=True, exist_ok=True)
    drive_out_dir = DRIVE_COMFY / "output" / "rap_battle" / e["title"] / "clips"
    drive_out_dir.mkdir(parents=True, exist_ok=True)
    os.makedirs(os.path.join(ep, "clips"), exist_ok=True)

    # Copy all unique reference images to /content/ComfyUI/input/
    for ref_png in (Path(ep) / "refs").glob("*.png"):
        shutil.copy2(ref_png, comfy_in / f"rap_{ref_png.name}")
    for src_p in (Path(ep) / "work").glob("*.png"):
        shutil.copy2(src_p, comfy_in / f"rap_{src_p.name}")

    total_t0 = time.time()
    stage1_jobs = []

    for idx, cid in enumerate(target_ids, 1):
        c = clips_map[cid]
        if c.get("frames"):
            n_frames = int(c["frames"])
        else:
            n_frames = fit_frames(c["audio"][1] - c["audio"][0]) if (args.fit and c["kind"] == "rap") else 124
        total_dur = round(n_frames / 24.0, 3)
        local_aud = cut_audio(ep, c, total_dur) if c["kind"] == "rap" else None
        seed = (args.seed if args.seed is not None else 2026110600) + idx

        if args.tessera_2k:
            s1_clip = Path(ep) / "clips" / f"{cid}_s1_768p.mp4"
            drv_s1 = drive_out_dir / s1_clip.name
            if not (s1_clip.exists() and s1_clip.stat().st_size > 100_000) and drv_s1.exists() and drv_s1.stat().st_size > 100_000:
                print(f"♻️ [Stage-1 Checkpoint] Reusing cached {drv_s1.name} from Drive ({drv_s1.stat().st_size / 1048576:.2f} MB)!", flush=True)
                shutil.copy2(drv_s1, s1_clip)
            if s1_clip.exists() and s1_clip.stat().st_size > 100_000:
                stage1_jobs.append((idx, cid, c, n_frames, seed, local_aud, s1_clip))
                continue

        print(
            f"\n🎬 [Stage-1 {idx}/{len(target_ids)}] Rendering {cid} "
            f"({c['move']}, kind={c['kind']}, realism_v2={args.realism_v2}, tessera_2k={args.tessera_2k})...",
            flush=True,
        )
        comfy_imgs = [f"rap_{k}.png" for k in c["image_keys"]]
        comfy_aud = None
        print(f"   ⏱️ {n_frames} frames = {total_dur:.3f}s | lock_strength={args.lock_strength} | steps={args.steps}", flush=True)
        if local_aud:
            comfy_aud = f"rap_audio_{cid}.wav"
            shutil.copy2(local_aud, comfy_in / comfy_aud)

        prompt_text = adapt_prompt_for_comfy_h3(c, e, total_dur, mic=args.mic, static_cam=args.static_cam,
                                                realism_v2=args.realism_v2)
        wf = build_single_clip_workflow(c, comfy_imgs, comfy_aud, prompt_text, steps=args.steps, seed=seed,
                                        length_frames=n_frames, lock_strength=args.lock_strength,
                                        realism_v2=args.realism_v2)
        raw_mp4 = submit_and_wait(wf, cid, prefix=f"RapBattle_{cid}", log_file=Path("/tmp/comfyui.log"))

        if args.tessera_2k:
            s1_clip = Path(ep) / "clips" / f"{cid}_s1_768p.mp4"
            shutil.copy2(raw_mp4, s1_clip)
            shutil.copy2(s1_clip, drive_out_dir / s1_clip.name)
            stage1_jobs.append((idx, cid, c, n_frames, seed, local_aud, s1_clip))
            continue

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
        if args.tag:
            continue
        picks[cid] = take
        for d_name, local_p, cur_d in (("picks.json", Path(picks_p), picks), ("shifts.json", Path(shifts_p), shifts)):
            drv_p = drive_out_dir.parent / d_name
            if drv_p.exists():
                try:
                    cur_d.update({k: v for k, v in json.loads(drv_p.read_text(encoding="utf-8")).items() if k not in cur_d})
                except Exception:
                    pass
            jsave(str(local_p), cur_d)
            shutil.copy2(local_p, drv_p)

    if args.tessera_2k and stage1_jobs:
        obj_info = _setup_tessera_and_restart_offload()
        has_ultrasharp = (LOCAL_COMFY / "models" / "upscale_models" / "4x-UltraSharp.pth").exists()
        for idx, cid, c, n_frames, seed, local_aud, s1_clip in stage1_jobs:
            print(
                f"\n✨ [Stage-2 Tessera 2.7K {idx}/{len(stage1_jobs)}] Refining {cid} "
                f"(1344x768 -> 2688x1536, {n_frames}f, 3 steps)...",
                flush=True,
            )
            s1_in_name = f"rap_s1_{cid}.mp4"
            shutil.copy2(s1_clip, comfy_in / s1_in_name)
            wf2 = build_tessera_2k_workflow(
                c,
                s1_mp4_name=s1_in_name,
                length_frames=n_frames,
                seed=786110 + idx,
                realism_v2=args.realism_v2,
                has_ultrasharp=has_ultrasharp,
                obj_info=obj_info,
            )
            raw_2k = submit_and_wait(
                wf2,
                cid,
                prefix=f"RapBattle2K_{cid}",
                log_file=Path("/tmp/comfyui_tessera.log"),
            )
            take = 1
            final_clip = Path(ep) / "clips" / (f"{cid}_{args.tag}.mp4" if args.tag else f"{cid}_t{take}.mp4")
            shutil.copy2(raw_2k, final_clip)
            shutil.copy2(final_clip, drive_out_dir / final_clip.name)

            if local_aud:
                try:
                    verdict = qa.analyze(str(final_clip), local_aud)
                    print(f"   🔍 QA 2K {cid}: {verdict}", flush=True)
                    if verdict.get("shift", 0) > 0.03 and verdict.get("corr", 0) >= 0.5:
                        shifts[cid] = verdict["shift"]
                except Exception as qa_err:
                    print(f"   ⚠️ QA warning on 2K {cid}: {qa_err}", flush=True)
            if args.tag:
                continue
            picks[cid] = take
            jsave(picks_p, picks)
            jsave(shifts_p, shifts)
            shutil.copy2(picks_p, drive_out_dir.parent / "picks.json")
            shutil.copy2(shifts_p, drive_out_dir.parent / "shifts.json")

    print(f"\n🎉 All {len(target_ids)} clips rendered in {(time.time() - total_t0)/60:.1f} min!", flush=True)


if __name__ == "__main__":
    main()
