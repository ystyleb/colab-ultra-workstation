#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate the Rap Battle song & exact line timestamps via KIE Suno API (ai-music-api/generate + get-timestamped-lyrics).

Usage:
  python3 workflows/05_ancient_rap_battle/scripts/kie_suno.py <episode_dir> [--reuse]
"""
import argparse
import difflib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import wave
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import P, die, jload, jsave, load_episode  # noqa: E402

KIE_API = os.environ.get("KIE_BASE_URL", "https://api.kie.ai").rstrip("/")
SUNO_MODEL = "ai-music-api/generate"
BRACKET_TAG = re.compile(r"\[[^\]]*\]")


def get_kie_key() -> str:
    k = os.environ.get("KIE_API_KEY", "").strip()
    if k:
        return k
    fallback_paths = [
        "/Volumes/WorkData/Workspace/projects/ai-meme-studio/.env.local",
        "/Volumes/WorkData/Workspace/projects/makeitrap/.dev.vars",
    ]
    for p in fallback_paths:
        if os.path.exists(p):
            try:
                txt = open(p, encoding="utf-8", errors="ignore").read()
                m = re.search(r"KIE_API_KEY[=\"\s:]+([a-fA-F0-9]{24,40})", txt)
                if m:
                    return m.group(1)
            except Exception:
                pass
    die("KIE_API_KEY not found in environment or local .env files")


def kie_call(method: str, path: str, body: dict = None, timeout: int = 60):
    key = get_kie_key()
    headers = {
        "Authorization": f"Bearer {key}",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept": "application/json",
    }
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(f"{KIE_API}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            resp = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_txt = e.read().decode("utf-8", errors="replace")[:400]
        raise RuntimeError(f"KIE HTTP {e.code} on {path}: {err_txt}")
    code = resp.get("code")
    if code is not None and code != 200:
        raise RuntimeError(f"KIE API error {code} on {path}: {resp.get('msg') or resp}")
    return resp.get("data")


def clean_word(w: str) -> str:
    if not isinstance(w, str):
        return ""
    return BRACKET_TAG.sub("", w).replace("\r", " ").replace("\n", " ").strip()


def norm_token(s: str) -> str:
    zh = "".join(ch for ch in s if "\u4e00" <= ch <= "\u9fff")
    if zh:
        return zh
    return "".join(ch for ch in s.lower() if ("a" <= ch <= "z") or ("0" <= ch <= "9"))


def sung_order(e: dict) -> list:
    """[(who, n, text)] in the order the lines are sung. episode.json `structure` (optional) lists sections like
    {"type": "verse", "who": "a", "from": 1, "to": 8, "tag": "..."}; without it: all of A, then all of B."""
    if not e.get("structure"):
        return [(w, i, t) for w in ("a", "b") for i, t in enumerate(e["lyrics"][w], 1)]
    out = []
    for sec in e["structure"]:
        if sec.get("type") == "verse":
            for n in range(sec["from"], sec["to"] + 1):
                out.append((sec["who"], n, e["lyrics"][sec["who"]][n - 1]))
    return out


def build_suno_lyrics(e: dict) -> str:
    if e.get("structure"):
        lines = []
        for sec in e["structure"]:
            lines.append("[%s]" % sec["tag"])
            if sec.get("type") == "verse":
                lines += [e["lyrics"][sec["who"]][n - 1] for n in range(sec["from"], sec["to"] + 1)]
            elif sec.get("text"):
                lines.append(sec["text"])
            lines.append("")
        return "\n".join(lines + ["[End]"])
    b_name = e["b"]["name_en"]
    chant = e.get("outro_chant", b_name.split()[-1].upper())
    lines = ["[Intro: short DJ scratch and electric hum]", ""]
    lines.append("[Verse 1: deep gritty baritone male rapper]")
    for l in e["lyrics"]["a"]:
        lines.append(l)
    lines += ["", "[Break: crowd chanting]", f"{chant}! {chant}!", ""]
    lines.append("[Verse 2: sharp fast tenor male rapper]")
    for l in e["lyrics"]["b"]:
        lines.append(l)
    lines += ["", "[Outro: crowd chanting]", f"{chant}! {chant}!", "[End]"]
    return "\n".join(lines)


def build_suno_style(e: dict) -> str:
    # 每集的配器/氛围不同（电流之战用电弧声，滑铁卢用军鼓），episode.json 里写了就用它的
    if e.get("suno_style"):
        return e["suno_style"]
    if e.get("language") == "en":
        return (
            "English battle rap, classic old school boom bap, 95 BPM, dark cinematic steampunk, "
            "hard punchy drums, vinyl scratches, electric arc zaps, brass hits, deep sub bass, "
            "live crowd hype, two contrasting male rappers, "
            "clear English diction, very short intro, short ending"
            + (", two-round battle, short loud crowd reactions between verses" if e.get("structure") else "")
        )
    return (
        "Chinese battle rap, old school boom bap, 95 BPM, dark cinematic, hard punchy drums, "
        "vinyl scratches, guqin and guzheng samples, war drums, deep sub bass, live crowd hype, "
        "male rapper, clear Mandarin diction, very short intro, short ending"
    )


def extract_suno_tracks(task_data: dict) -> list:
    r = task_data.get("resultJson")
    if isinstance(r, str) and r:
        try:
            r = json.loads(r)
        except Exception:
            r = {}
    if not isinstance(r, dict):
        r = {}
    lst = (
        r.get("data")
        or r.get("sunoData")
        or (r.get("response") or {}).get("data")
        or (task_data.get("response") or {}).get("data")
        or (task_data.get("response") or {}).get("sunoData")
        or []
    )
    tracks = []
    for x in lst:
        if not x:
            continue
        url = x.get("audio_url") or x.get("audioUrl")
        if url:
            tracks.append({
                "id": x.get("id"),
                "audioUrl": url,
                "duration": float(x.get("duration") or 0.0),
                "title": x.get("title") or "",
            })
    return tracks


def match_lines_to_words(words: list, e: dict, bar_sec: float = 240.0 / 95.0):
    """Map each lyric line in episode['lyrics']['a'] and ['b'] to its exact start/end in alignedWords."""
    clean_ws = []
    in_bracket = False
    for w in words:
        if not isinstance(w, dict) or w.get("success") is False:
            continue
        raw_w = w.get("word", "")
        if not isinstance(raw_w, str):
            continue
        # Strip bracketed stage directions even when split across multiple alignedWords
        out_chars = []
        for ch in raw_w:
            if ch == "[":
                in_bracket = True
            elif ch == "]":
                in_bracket = False
            elif not in_bracket:
                out_chars.append(ch)
        cw = "".join(out_chars).replace("\r", " ").replace("\n", " ").strip()
        if not cw:
            continue
        s_t = float(w.get("startS", 0.0))
        e_t = float(w.get("endS", s_t + 0.2))
        parts = [p for p in cw.split() if norm_token(p)]
        if not parts:
            continue
        dur = max(0.05, e_t - s_t) / len(parts)
        for idx, p in enumerate(parts):
            clean_ws.append({
                "w": p,
                "norm": norm_token(p),
                "s": round(s_t + idx * dur, 3),
                "e": round(s_t + (idx + 1) * dur, 3),
            })

    all_specs = []
    for who, idx, text in sung_order(e):
        toks = [norm_token(t) for t in text.split() if norm_token(t)]
        all_specs.append({"who": who, "n": idx, "text": text, "toks": toks})

    word_norms = [w["norm"] for w in clean_ws]
    cursor = 0
    matched_lines = []
    total_score = 0.0

    for spec_idx, spec in enumerate(all_specs):
        target_toks = spec["toks"]
        n_tok = len(target_toks)
        best = (-1.0, cursor, min(len(clean_ws) - 1, cursor + n_tok))
        search_end = min(len(clean_ws), cursor + max(25, n_tok * 4))
        for i in range(cursor, search_end):
            for span_len in range(max(2, n_tok - 3), min(n_tok + 4, len(clean_ws) - i + 1)):
                cand = word_norms[i : i + span_len]
                sm = difflib.SequenceMatcher(None, cand, target_toks)
                score = sum(b.size for b in sm.get_matching_blocks()) / max(1, len(target_toks))
                boundary_bonus = 0.05 * (1 if cand[0] == target_toks[0] else 0) + 0.05 * (1 if cand[-1] == target_toks[-1] else 0)
                len_penalty = 0.02 * abs(span_len - n_tok)
                pos_penalty = 0.005 * max(0, i - cursor)
                total_cand = score + boundary_bonus - len_penalty - pos_penalty
                if total_cand > best[0]:
                    best = (total_cand, i, i + span_len - 1)
        sc, i0, i1 = best
        total_score += min(1.0, max(0.0, sc))
        s_time = clean_ws[i0]["s"] if clean_ws else spec_idx * bar_sec
        e_time = clean_ws[i1]["e"] if clean_ws else (spec_idx + 1) * bar_sec
        heard = " ".join(w["w"] for w in clean_ws[i0 : i1 + 1])
        matched_lines.append({
            "who": spec["who"],
            "n": spec["n"],
            "text": spec["text"],
            "orig_start": round(s_time, 3),
            "orig_end": round(e_time, 3),
            "heard": heard,
            "score": round(min(1.0, sc), 3),
        })
        cursor = min(len(clean_ws) - 1, i1 + 1)

    avg_score = total_score / max(1, len(all_specs))
    return matched_lines, avg_score, clean_ws


def srt_time(t: float) -> str:
    t = max(0.0, t)
    h, m, s = int(t // 3600), int(t % 3600 // 60), t % 60
    return "%02d:%02d:%06.3f" % (h, m, s)


def read_wav_f32(path: str):
    with wave.open(path, "rb") as wf:
        sr = wf.getframerate()
        nch = wf.getnchannels()
        raw = wf.readframes(wf.getnframes())
    x = np.frombuffer(raw, dtype=np.int16).astype(np.float32).reshape(-1, nch) / 32768.0
    return x, sr


def write_wav_f32(path: str, x: np.ndarray, sr: int):
    x_clip = np.clip(x, -0.99, 0.99)
    pcm = (x_clip * 32767.0).astype(np.int16)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(x.shape[1] if x.ndim > 1 else 1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())


def stft_separate_vocals(stereo: np.ndarray, sr: int = 44100):
    """Separate center-panned harmonic lead vocals from stereo instrumentation and percussive drums."""
    L, R = stereo[:, 0], stereo[:, 1]
    mid = 0.5 * (L + R)
    side = 0.5 * (L - R)
    n_fft = 2048
    hop = 512
    win = np.hanning(n_fft).astype(np.float32)
    pad = n_fft
    mid_p = np.pad(mid, (pad, pad), mode="reflect")
    side_p = np.pad(side, (pad, pad), mode="reflect")
    n_frames = 1 + (len(mid_p) - n_fft) // hop
    idx = np.arange(n_fft)[None, :] + hop * np.arange(n_frames)[:, None]
    M = np.fft.rfft(mid_p[idx] * win, axis=1)
    S = np.fft.rfft(side_p[idx] * win, axis=1)
    mag_M = np.abs(M)
    mag_S = np.abs(S)

    # 1. Center spatial mask (lead rap vocals are panned dead center: |M| >> |S|)
    center_mask = np.clip((mag_M**2 - 1.35 * mag_S**2) / (mag_M**2 + mag_S**2 + 1e-8), 0.0, 1.0) ** 1.15

    # 2. Harmonic-Percussive Separation (HPSS) via sliding median along time vs frequency
    t_pad = np.pad(mag_M, ((4, 4), (0, 0)), mode="edge")
    H = np.median(sliding_window_view(t_pad, 9, axis=0), axis=-1)
    f_pad = np.pad(mag_M, ((0, 0), (8, 8)), mode="edge")
    P = np.median(sliding_window_view(f_pad, 17, axis=1), axis=-1)
    hpss_mask = (H**2) / (H**2 + (1.20 * P) ** 2 + 1e-8)

    # 3. Vocal frequency band mask (125 Hz .. 7200 Hz with smooth cosine roll-off)
    freqs = np.fft.rfftfreq(n_fft, 1.0 / sr)
    f_mask = np.ones_like(freqs, dtype=np.float32)
    f_mask[freqs < 115] = 0.0
    lo_trans = (freqs >= 115) & (freqs < 175)
    f_mask[lo_trans] = 0.5 * (1 - np.cos(np.pi * (freqs[lo_trans] - 115) / 60.0))
    hi_trans = (freqs > 5500) & (freqs <= 7500)
    f_mask[hi_trans] = 0.5 * (1 + np.cos(np.pi * (freqs[hi_trans] - 5500) / 2000.0))
    f_mask[freqs > 7500] = 0.0

    voc_mask = center_mask * hpss_mask * f_mask[None, :]
    V_spec = M * voc_mask
    frames_v = np.fft.irfft(V_spec, axis=1) * win
    voc_mono = np.zeros(len(mid_p), dtype=np.float32)
    win_sum = np.zeros(len(mid_p), dtype=np.float32)
    win_sq = win**2
    for t in range(n_frames):
        s0 = t * hop
        voc_mono[s0 : s0 + n_fft] += frames_v[t]
        win_sum[s0 : s0 + n_fft] += win_sq
    voc_mono /= np.maximum(win_sum, 1e-6)
    voc_mono = voc_mono[pad : pad + len(mid)]
    voc_stereo = np.stack([voc_mono, voc_mono], axis=1)
    inst_stereo = stereo - voc_stereo
    return voc_stereo, inst_stereo


def pitch_shift_vocal(src_wav: str, semis: float, out_wav: str, role: str = "a"):
    if abs(semis) < 0.05:
        shutil.copy(src_wav, out_wav)
        return
    ratio = 2.0 ** (semis / 12.0)
    if role == "a":
        # Deep gritty baritone-bass warmth for Character A (Edison)
        eq_chain = ",equalizer=f=210:t=q:w=1.1:g=3.2,equalizer=f=3200:t=q:w=1.4:g=-1.5"
    else:
        # Crisp electric tenor presence for Character B (Tesla)
        eq_chain = ",equalizer=f=190:t=q:w=1.2:g=-2.2,equalizer=f=3300:t=q:w=1.2:g=3.5"
    af = f"rubberband=pitch={ratio:.6f}:formant=shifted:pitchq=quality:transients=crisp{eq_chain}"
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", src_wav, "-af", af, "-ac", "2", "-ar", "44100", out_wav],
        check=True,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ep")
    ap.add_argument("--reuse", action="store_true", help="Reuse cached KIE Suno task in work/kie_suno.json if present")
    args = ap.parse_args()

    ep = args.ep
    e = load_episode(ep)
    work = os.path.join(ep, "work")
    os.makedirs(work, exist_ok=True)
    meta_path = os.path.join(work, "kie_suno.json")

    if args.reuse and os.path.exists(meta_path):
        meta = jload(meta_path)
        task_id = meta["taskId"]
        tracks = meta["tracks"]
        print(f"♻️ Reusing existing KIE Suno task {task_id} ({len(tracks)} tracks)")
    else:
        before_credit = kie_call("GET", "/api/v1/chat/credit")
        print(f"💳 KIE Credit Balance: {before_credit}")
        lyrics = build_suno_lyrics(e)
        style = build_suno_style(e)
        inp = {
            "model": "V6",
            "custom_mode": True,
            "instrumental": False,
            "title": e["title"][:80],
            "lyrics": lyrics,
            "style": style,
            "vocal_gender": "m",
        }
        print("🎵 Submitting Suno V6 battle rap generation to KIE (ai-music-api/generate)...")
        res = kie_call("POST", "/api/v1/jobs/createTask", {"model": SUNO_MODEL, "input": inp})
        task_id = res["taskId"]
        print(f"   Task ID: {task_id}")
        t0 = time.time()
        last_state = ""
        while True:
            time.sleep(5)
            d = kie_call("GET", f"/api/v1/jobs/recordInfo?taskId={task_id}")
            st = d.get("state", "waiting")
            if st != last_state:
                print(f"   [{time.time() - t0:.0f}s] state = {st}")
                last_state = st
            if st == "success":
                tracks = extract_suno_tracks(d)
                break
            if st == "fail":
                die(f"KIE Suno generation failed: {d.get('failCode')} {d.get('failMsg')}")
            if time.time() - t0 > 600:
                die(f"KIE Suno generation timed out after 600s (taskId={task_id})")

        for idx, tr in enumerate(tracks):
            mp3_path = os.path.join(work, f"suno_v{idx + 1}.mp3")
            print(f"⬇️ Downloading track v{idx + 1} ({tr['duration']:.1f}s) -> {mp3_path}")
            urllib.request.urlretrieve(tr["audioUrl"], mp3_path)
            tr["local_mp3"] = mp3_path
            print(f"⏱️ Fetching timestamped lyrics for v{idx + 1} (audioId={tr['id']})...")
            ts_data = kie_call("POST", "/api/v1/generate/get-timestamped-lyrics", {"taskId": task_id, "audioId": tr["id"]})
            tr["alignedWords"] = ts_data.get("alignedWords") or []

        meta = {"taskId": task_id, "tracks": tracks}
        jsave(meta_path, meta)
        after_credit = kie_call("GET", "/api/v1/chat/credit")
        print(f"💳 KIE Credit After Suno + Timestamps: {after_credit} (spent: {before_credit - after_credit:.2f} credits)")

    # Evaluate both tracks and pick the best aligned one
    bpm = 95.0
    bar = 240.0 / bpm
    # tie-break: vocal span closest to one bar per line (+ one bar per crowd section); legacy 8 lines ~ 24 s
    n_crowd = sum(1 for sec in e.get("structure", []) if sec.get("type") == "crowd") if e.get("structure") else 1
    expected_span = 24.0 if not e.get("structure") else (len(sung_order(e)) + n_crowd) * bar
    best_pick = None
    for idx, tr in enumerate(tracks):
        matched, avg_sc, clean_ws = match_lines_to_words(tr.get("alignedWords", []), e, bar)
        span = matched[-1]["orig_end"] - matched[0]["orig_start"] if matched else 999.0
        print(f"📊 Track v{idx + 1}: duration={tr['duration']:.1f}s, vocal_span={span:.1f}s, match_score={avg_sc:.2f}")
        for m in matched:
            print(f"   {m['who'].upper()}{m['n']:02d} [{m['orig_start']:5.2f}s - {m['orig_end']:5.2f}s] (sc={m['score']:.2f}) heard: '{m['heard']}'")
        cand = (avg_sc, -abs(span - expected_span), idx, tr, matched, clean_ws)
        if best_pick is None or cand[:2] > best_pick[:2]:
            best_pick = cand

    _, _, best_idx, best_tr, matched, clean_ws = best_pick
    print(f"\n🏆 Selected Track v{best_idx + 1} (audioId={best_tr['id']})")
    src_mp3 = best_tr["local_mp3"]
    shutil.copy(src_mp3, os.path.join(ep, "song.mp3"))

    # Trim intro so A1 starts at ~2.53s (1 bar intro), and outro ends ~4.5s after B's last line
    intro_keep = bar  # 2.526s before A1
    outro_keep = 4.6  # 4.6s after B4 ends for END shot + crowd chant
    a1_orig = matched[0]["orig_start"]
    b_last_orig = matched[-1]["orig_end"]
    probe_dur = float(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", src_mp3
    ]).decode().strip())

    trim_start = max(0.0, a1_orig - intro_keep)
    trim_end = min(probe_dur, b_last_orig + outro_keep)
    final_dur = round(trim_end - trim_start, 3)
    print(f"✂️ Trimming song [{trim_start:.2f}s .. {trim_end:.2f}s] -> {final_dur:.2f}s total")

    # Shift timestamps by -trim_start and build work/lines.json, work/grid.json, 字幕.srt
    lines = []
    na = len(e["lyrics"]["a"])
    for idx, m in enumerate(matched):
        st = round(max(0.0, m["orig_start"] - trim_start), 3)
        raw_en = round(max(st + 1.2, m["orig_end"] - trim_start), 3)
        # If next line is in the same verse, extend end up to next line's start - 0.04s
        if idx + 1 < len(matched) and matched[idx + 1]["who"] == m["who"]:
            next_st = round(max(0.0, matched[idx + 1]["orig_start"] - trim_start), 3)
            en = round(min(max(raw_en, next_st - 0.05), next_st - 0.02), 3)
        else:
            en = round(max(raw_en, st + bar * 0.92), 3)
        lines.append({
            "who": m["who"],
            "n": m["n"],
            "text": m["text"],
            "start": st,
            "end": en,
            "bar": st,
            "heard": m["heard"],
            "orig_start": m["orig_start"],
            "orig_bar": m["orig_start"],
        })

    jsave(os.path.join(work, "lines.json"), lines)
    # 词级时间轴（剪辑时间，含 [段落标签] 和观众喊词）：分镜脚本的「唱完才切」断言、assemble.py 的甩镜避让都读它
    # Suno 会把段落标签和下一个词粘成一个 token（"[Crowd reacts]\nOOOH!"），只留换行后的词，否则全大写判断认不出观众喊词
    words_edit, in_tag = [], False
    for w in best_tr.get("alignedWords", []):
        raw = w.get("word", "")
        if not raw.strip() or w["startS"] < trim_start:
            for ch in raw:
                if ch == "[":
                    in_tag = True
                elif ch == "]":
                    in_tag = False
            continue
        s = re.sub(r"\[[^\]]*\]", "", raw)
        if in_tag:
            if "]" in s:
                s = s.split("]", 1)[1]
                in_tag = False
            else:
                s = ""
        if "[" in s:
            s = s.split("[", 1)[0]
            in_tag = True
        s = re.sub(r'\s*\n\s*"+\s*$', "", s).strip()
        if not re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]", "", s):
            continue
        words_edit.append({"w": s, "t0": round(w["startS"] - trim_start, 3), "t1": round(w["endS"] - trim_start, 3)})
    jsave(os.path.join(work, "words_edit.json"), words_edit)
    verse_a_start = lines[0]["start"]
    verse_a_end = max(l["end"] for l in lines if l["who"] == "a")
    verse_b_start = next(l["start"] for l in lines if l["who"] == "b" and l["n"] == 1)
    verse_b_end = max(l["end"] for l in lines if l["who"] == "b")

    # Export trimmed raw stereo master, separate vocals vs instrumental, and apply dual-character vocal pitch/formant shifting
    raw_trimmed = os.path.join(work, "music_trimmed_raw.wav")
    vocals_cut = os.path.join(work, "vocals_cut.wav")
    inst_cut = os.path.join(work, "inst_cut.wav")
    voc_a_wav = os.path.join(work, "voc_a.wav")
    voc_b_wav = os.path.join(work, "voc_b.wav")
    music_final = os.path.join(work, "music_final.wav")
    vocals_final = os.path.join(work, "vocals_final.wav")

    subprocess.run([
        "ffmpeg", "-y", "-v", "error",
        "-ss", f"{trim_start:.3f}", "-t", f"{final_dur:.3f}",
        "-i", src_mp3,
        "-af", f"afade=t=in:d=0.05,afade=t=out:st={max(0.1, final_dur - 1.2):.3f}:d=1.2",
        "-ac", "2", "-ar", "44100", raw_trimmed
    ], check=True)

    stereo_raw, sr = read_wav_f32(raw_trimmed)
    voc_stereo, inst_stereo = stft_separate_vocals(stereo_raw, sr)
    write_wav_f32(vocals_cut, voc_stereo, sr)
    write_wav_f32(inst_cut, inst_stereo, sr)

    pitch_a = float(e["a"].get("pitch", -2.5))
    pitch_b = float(e["b"].get("pitch", 1.5))
    print(f"🎙️ Dual-Voice Stem Remastering: {e['a']['name_en']} ({pitch_a:+.1f} st) vs {e['b']['name_en']} ({pitch_b:+.1f} st)...")
    pitch_shift_vocal(vocals_cut, pitch_a, voc_a_wav, role="a")
    pitch_shift_vocal(vocals_cut, pitch_b, voc_b_wav, role="b")

    base_v, _ = read_wav_f32(vocals_cut)
    va, _ = read_wav_f32(voc_a_wav)
    vb, _ = read_wav_f32(voc_b_wav)
    inst_c, _ = read_wav_f32(inst_cut)
    n_samp = min(len(base_v), len(va), len(vb), len(inst_c))
    base_v, va, vb, inst_c = base_v[:n_samp], va[:n_samp], vb[:n_samp], inst_c[:n_samp]

    wa = np.zeros(n_samp, dtype=np.float32)
    wb = np.zeros(n_samp, dtype=np.float32)

    def ramp(w: np.ndarray, t0: float, t1: float, x: float = 0.08):
        i0, i1, k = max(0, int(t0 * sr)), min(n_samp, int(t1 * sr)), int(x * sr)
        if i1 <= i0 + 2 * k:
            return
        w[i0:i1] = 1.0
        w[i0 : i0 + k] = np.linspace(0.0, 1.0, k, dtype=np.float32)
        w[i1 - k : i1] = np.linspace(1.0, 0.0, k, dtype=np.float32)

    runs = []  # contiguous runs of the same rapper, in sung order
    for l in lines:
        if runs and runs[-1][0] == l["who"]:
            runs[-1][2] = l["end"]
        else:
            runs.append([l["who"], l["start"], l["end"]])
    for who, r0, r1 in runs:
        ramp(wa if who == "a" else wb, max(0.0, r0 - 0.18), min(final_dur, r1 + 0.25))
    print("🎚️ Voice runs: " + ", ".join("%s %.2f-%.2fs" % (w.upper(), r0, r1) for w, r0, r1 in runs), flush=True)

    # Boost shifted vocal stems slightly (+1.15x) so the differentiated voice dominates cleanly over any residual bleed
    voc_dual = base_v * (1.0 - wa - wb)[:, None] + (1.15 * va) * wa[:, None] + (1.15 * vb) * wb[:, None]
    write_wav_f32(vocals_final, voc_dual, sr)

    mix = voc_dual + inst_c
    pk = float(np.abs(mix).max())
    if pk > 0.98:
        mix *= 0.98 / pk
    write_wav_f32(music_final, mix, sr)
    shutil.copy(music_final, os.path.join(ep, "音乐_最终.wav"))
    jsave(os.path.join(work, "grid.json"), {
        "bpm": bpm,
        "beat0": verse_a_start % (60.0 / bpm),
        "bar": bar,
        "keep": [[round(trim_start, 3), round(trim_end, 3)]],
        "length": final_dur,
        "verse_a": verse_a_start,
        "verse_b": verse_b_start,
    })

    srt_path = os.path.join(ep, "字幕.srt")
    with open(srt_path, "w", encoding="utf-8") as f:
        for i, l in enumerate(lines, 1):
            f.write("%d\n%s --> %s\n%s\n\n" % (
                i,
                srt_time(l["start"] - 0.05).replace(".", ","),
                srt_time(l["end"] - 0.05).replace(".", ","),
                l["text"],
            ))

    print(f"\n✅ Wrote {music_final} ({final_dur:.2f}s), work/lines.json, and 字幕.srt")
    for l in lines:
        print(f"   {l['who'].upper()}{l['n']:02d} {l['start']:6.2f}s -> {l['end']:6.2f}s | {l['text']}")


if __name__ == "__main__":
    main()
