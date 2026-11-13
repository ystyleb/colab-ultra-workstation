#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Call KIE Suno Lyrics API (ai-music-api/generate-lyrics, ~0.40 credits) to generate
native battle-rap slang, multisyllabic internal rhymes, and cadence variations for an episode.

Saves output to <episode_dir>/work/suno_lyrics_polish.json.
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import die, jload, jsave, load_episode  # noqa: E402
from kie_suno import kie_call  # noqa: E402

LYRICS_MODEL = "ai-music-api/generate-lyrics"


def default_prompt_from_episode(e: dict) -> str:
    """Build a concise (<950 chars) Suno generate-lyrics prompt dynamically from episode.json."""
    custom = (e.get("lyrics_polish_prompt") or "").strip()
    if custom:
        return custom[:940]

    a = e["a"]
    b = e["b"]
    a_name = a["name_en"]
    b_name = b["name_en"]
    a_desc = a.get("aka") or a.get("voice", "male rapper")
    b_desc = b.get("aka") or b.get("voice", "male rapper")
    era = (e.get("era_en") or "").strip()
    style = (e.get("suno_style") or "").strip()

    # Extract concise thematic hooks from existing draft lyrics if available
    draft_a = " / ".join(e.get("lyrics", {}).get("a", [])[:4])
    draft_b = " / ".join(e.get("lyrics", {}).get("b", [])[:4])

    parts = [
        f"32-line English battle rap between {a_name} ({a_desc}; {a.get('voice', '')[:75]}) "
        f"and {b_name} ({b_desc}; {b.get('voice', '')[:75]}).",
    ]
    if era:
        parts.append(f"Setting: {era[:140]}.")
    if style:
        parts.append(f"Sound/Beat Switch: {style[:220]}.")
    if draft_a or draft_b:
        parts.append(
            f"Keep hard-hitting lore roasts & punchlines inspired by: "
            f"{a_name}: {draft_a[:160]} | {b_name}: {draft_b[:160]}."
        )
    parts.append(
        "Tight AABB rhymes, 10-13 syllables per bar, crisp multi-syllabic internal rhymes, "
        "sharp acronyms dotted if spelled out (e.g. U.N.S.C., F.I.B.), savage battle-rap punchlines."
    )
    prompt = " ".join(parts)
    if len(prompt) > 940:
        prompt = prompt[:937].rstrip() + "..."
    return prompt


def extract_lyrics_variants(task_data: dict) -> list:
    r = task_data.get("resultJson")
    if isinstance(r, str) and r:
        try:
            r = json.loads(r)
        except Exception:
            r = {"raw": r}
    if not isinstance(r, dict):
        r = {}
    ro = r.get("resultObject") or (task_data.get("response") or {}).get("resultObject") or {}
    lst = (
        ro.get("lyricsData")
        or r.get("data")
        or r.get("lyricsData")
        or (r.get("response") or {}).get("data")
        or (task_data.get("response") or {}).get("data")
        or []
    )
    if isinstance(lst, dict):
        lst = [lst]
    return lst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ep", help="Episode directory")
    ap.add_argument("--prompt", default=None, help="Custom concise prompt (<950 chars) for Suno generate-lyrics")
    ap.add_argument("--force", action="store_true", help="Re-run even if work/suno_lyrics_polish.json exists")
    args = ap.parse_args()

    ep = args.ep
    e = load_episode(ep)
    work = os.path.join(ep, "work")
    os.makedirs(work, exist_ok=True)
    out_path = os.path.join(work, "suno_lyrics_polish.json")

    if os.path.exists(out_path) and not args.force:
        cached = jload(out_path)
        print(f"♻️ Cached Suno lyrics polish found at {out_path} (taskId={cached.get('taskId')})")
        for idx, item in enumerate(cached.get("variants", []), 1):
            print(f"\n=== Variant {idx}: {item.get('title', 'Untitled')} ===")
            print(item.get("text") or item.get("lyrics") or json.dumps(item, ensure_ascii=False, indent=2))
        return

    prompt = (args.prompt or default_prompt_from_episode(e)).strip()
    print(f"📝 Prompt ({len(prompt)} chars):\n{prompt}\n")

    before_credit = kie_call("GET", "/api/v1/chat/credit")
    print(f"💳 KIE Credit Before: {before_credit}")

    payload = {
        "model": LYRICS_MODEL,
        "callBackUrl": "https://makeitrap.com/api/kie-callback",
        "input": {"prompt": prompt},
    }
    res = kie_call("POST", "/api/v1/jobs/createTask", payload)
    task_id = res["taskId"]
    print(f"🚀 Submitted {LYRICS_MODEL} -> taskId={task_id}")

    t0 = time.time()
    last_state = ""
    while True:
        time.sleep(3)
        d = kie_call("GET", f"/api/v1/jobs/recordInfo?taskId={task_id}")
        st = d.get("state", "waiting")
        if st != last_state:
            print(f"   [{time.time() - t0:.0f}s] state = {st}")
            last_state = st
        if st == "success":
            variants = extract_lyrics_variants(d)
            break
        if st == "fail":
            die(f"KIE generate-lyrics failed: {d.get('failCode')} {d.get('failMsg')}")
        if time.time() - t0 > 240:
            die(f"KIE generate-lyrics timed out after 240s (taskId={task_id})")

    after_credit = kie_call("GET", "/api/v1/chat/credit")
    spent = round(float(before_credit) - float(after_credit), 4) if isinstance(before_credit, (int, float)) else None
    out_obj = {
        "taskId": task_id,
        "prompt": prompt,
        "spent_credits": spent,
        "variants": variants,
        "raw_record": d,
    }
    jsave(out_path, out_obj)
    print(f"✅ Saved Suno lyrics polish -> {out_path} | KIE Credit After: {after_credit} (spent: {spent})")

    for idx, item in enumerate(variants, 1):
        print(f"\n==================== VARIANT {idx}: {item.get('title', 'Untitled')} ====================")
        print(item.get("text") or item.get("lyrics") or json.dumps(item, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
