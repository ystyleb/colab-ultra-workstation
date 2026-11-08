# -*- coding: utf-8 -*-
"""Build work/clips.json + work/edl.json for 分镜表_v2.md (18 shots).

usage: python3 build_storyboard_v2.py            (run from anywhere; paths are relative to this file)

Rap clips (A01-B04) keep their song windows from the v1 clips.json and get a per-clip camera (`cam`), so the
4 lines of each verse rotate frontal CU -> 3/4 MCU -> low angle -> OTS/CU. Render them with
`--fit --lock-strength 1.0 --mic stand --static-cam`. Non-lip clips get explicit `frames` and free camera moves.
"""
import json
import os

EP = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(EP, "work")
e = json.load(open(os.path.join(EP, "episode.json"), encoding="utf-8"))
# Source song windows / actions from the v1 episode so re-running this script is idempotent.
V1_CLIPS = os.path.join(EP, "..", "edison-vs-tesla", "work", "clips.json")
old = {c["id"]: c for c in json.load(open(V1_CLIPS, encoding="utf-8"))}
A, B = e["a"], e["b"]

VENUE = e["venue_en"]
CONTINUITY = (
    "This shot must cut seamlessly with the rest of the film: same venue, same overhead spotlight as the key light from "
    f"above, 35-50mm lens look. Setting: {VENUE}, with a cold white spotlight beam cutting through thick haze onto the "
    f"circular stage floor. The crowd are {e['commoners_en']}. Nobody else stands inside the circle: the crowd is packed "
    "only beyond its edge, every person dressed differently, never matching uniforms. Low-key cinematic lighting with "
    "deep shadows, thick haze, high contrast, warm amber glow against cool blue-white electric light, shallow depth of "
    "field, gritty 35mm film grain; not glossy, not brightly lit.\n\n"
    "Keep every character's face, hairstyle, costume and colors exactly as in their reference images. {PROPS}"
    "Nobody holds a microphone; the two vintage chrome microphones stand on floor stands at the edge of the circle. "
    "No subtitles, no on-screen text, no logos, no watermark."
)

PROP_A = f"Thomas Edison's {A['prop']} is always {A['prop_desc']}. "
PROP_B = f"Nikola Tesla's {B['prop']} is always {B['prop_desc']}. "


def props_for(keys):
    """Face-only refs carry no props, so H3 hands props to whoever is on screen (Tesla got Edison's bulb in the
    first batch). Only describe the props of the characters actually in the shot."""
    a, b = "a_face_clean" in keys, "b_face_clean" in keys
    if a and not b:
        return PROP_A + "Edison holds his bulb in his left hand and his right hand is empty. "
    if b and not a:
        return PROP_B + "Tesla holds his Tesla coil in his left hand and his right hand is empty. "
    if a and b:
        return PROP_A + PROP_B + "The bulb belongs only to Edison, the Tesla coil only to Tesla. "
    return ""


def refs_text(keys):
    desc = {
        "a_face_clean": "Thomas Edison's face (keep his exact face, silver-streaked hair and charcoal tweed suit)",
        "b_face_clean": "Nikola Tesla's face (keep his exact face, parted jet-black hair, moustache and black frock coat)",
        "venue": f"the venue, {VENUE}",
        "crowd": "the crowd of 1890s New York workers and engineers",
        "dj": "the DJ at his steampunk booth",
    }
    return " ".join(f"Image {i} is {desc[k]}." for i, k in enumerate(keys, 1))


def still(cid, keys, frames, shot):
    return {"id": cid, "kind": "still", "move": "V2", "frames": frames, "image_keys": keys,
            "prompt": f"{refs_text(keys)}\n\nCinematic photoreal shot, 16:9. {shot}\n\n"
                      + CONTINUITY.replace("{PROPS}", props_for(keys))}


HOLD_PROP_A = f", the {A['prop']} stays in his left hand, clearly separate from the microphone stand"
HOLD_PROP_B = f", the {B['prop']} stays in his left hand, clearly separate from the microphone stand"
CU = ("The camera holds a tight head-and-shoulders close-up at eye level, frontal, his face filling the upper half of the "
      "16:9 frame")
TQ = "The camera holds a chest-up medium close-up from a three-quarter angle at eye level"
LOW = ("The camera holds a low-angle chest-up medium close-up looking slightly up at him, the overhead spotlight lamp "
       "glowing at the top of the frame")
OTS = ("The camera holds an over-the-shoulder two-shot from behind <Subject 2>'s right shoulder: <Subject 2> is a dark, "
       "out-of-focus shoulder and back of the head in the left foreground, <Subject 1> is chest-up and in sharp focus on "
       "screen-right facing the lens")


def rap(cid, cam, two_shot=False, listener=None, extra=""):
    c = dict(old[cid])
    who = c["who"]
    c["image_keys"] = ["a_face_clean", "b_face_clean"] if who == "a" else ["b_face_clean", "a_face_clean"]
    if not two_shot:
        c["image_keys"] = c["image_keys"][:1]
    c["two_shot"] = two_shot
    c["cam"] = cam
    if listener:
        c["listener"] = listener
    c["action"] = c["action"] + extra + (HOLD_PROP_A if who == "a" else HOLD_PROP_B)
    c.pop("prompt", None)
    c.pop("images", None)
    return c


clips = [
    still("OPEN", ["venue", "crowd", "a_face_clean", "b_face_clean"], 73,
          "The camera glides fast at head height over the backs of the cheering crowd toward the spotlit circular stage, "
          "where Thomas Edison (Image 3) and Nikola Tesla (Image 4) stand facing each other about three meters apart, "
          "raised fists and flat caps in the blurred foreground."),
    still("FACEOFF", ["a_face_clean", "b_face_clean", "venue"], 73,
          "Low-angle medium two-shot, static camera. Thomas Edison (Image 1) on screen-left and Nikola Tesla (Image 2) "
          "on screen-right face each other in profile, close enough to touch. Edison slowly raises his glowing amber "
          "bulb between them; Tesla answers by lifting his brass Tesla coil, blue-violet arcs crackling. Both stay "
          "silent, mouths closed, staring each other down."),
    rap("A01", CU),
    rap("A02", TQ + " from his left side"),
    still("R_T1", ["b_face_clean", "venue"], 73,
          "Close-up of Nikola Tesla (Image 1), frontal, eye level, static camera, the crowd blurred behind him. He "
          "listens silently with his mouth closed, unimpressed: one eyebrow rises, he tilts his head with a cold smirk, "
          "and tiny blue-violet sparks jump between his fingertips."),
    rap("A03", LOW),
    rap("A04", OTS, two_shot=True,
        listener=" while <Subject 2> stays a silent, blurred foreground shoulder with his back to the camera"),
    # take 1 (with the venue ref) came out as an empty stage: crowd-only ref + faces filling the frame
    still("CROWD_OOH", ["crowd"], 73,
          "Close medium shot packed with four or five workers from the front row (Image 1), their faces large and "
          "filling the 16:9 frame, handheld camera at their eye level, the spotlit stage only a blurred glow behind "
          "them. They react to a brutal punchline: one claps both hands over his mouth, one grabs his head with wide "
          "eyes, one doubles over laughing and shoves his friend. Energetic, joyful chaos."),
    still("DJ", ["dj", "venue", "crowd"], 73,
          "Medium shot from a slightly low angle of the DJ (Image 1) at the raised steampunk booth built on brass "
          "dynamos, scratching a record with one hand and pumping his fist with the other, the crowd behind and below "
          "him punching the air in rhythm."),
    still("B_STEP", ["b_face_clean", "venue", "crowd"], 73,
          "The camera swings in from his side and settles into a frontal medium shot at eye level as Nikola Tesla "
          "(Image 1) steps forward into the white spotlight, calmly straightens his cuffs and lifts his brass Tesla "
          "coil, which flares with blue-violet arcs. Mouth closed, cold confident stare into the lens."),
    rap("B01", CU),
    rap("B02", TQ + " from his right side"),
    still("R_E1", ["a_face_clean", "venue"], 73,
          "Close-up of Thomas Edison (Image 1), three-quarter view, eye level, static camera, crowd blurred behind. He "
          "listens silently with his mouth closed, stung: his jaw tightens, he tugs at his cravat and looks away, the "
          "amber bulb in his hand trembling slightly."),
    rap("B03", LOW),
    still("BLACKOUT", ["a_face_clean", "venue"], 73,
          "Close-up of Thomas Edison (Image 1) holding his glowing amber bulb near his face, static camera. During "
          "00:00.000-00:01.000 the bulb glows warmly on his face; at 00:01.000 it flickers twice and dies completely; "
          "from 00:01.500 his face is left almost in darkness, only a faint cold blue rim light from the Tesla coils "
          "behind him. Mouth closed, shocked stare."),
    rap("B04", CU, extra=", and when he sings 'high-voltage' bright blue-violet lightning arcs flare up behind him"),
    still("CROWD_ERUPT", ["crowd", "venue"], 73,
          "Wide-ish medium shot of the crowd erupting, handheld camera: everyone jumps and punches the air, chanting "
          "together, flat caps flying, blue-violet light flickering over their faces from the Tesla coils."),
    still("END", ["b_face_clean", "a_face_clean", "venue", "crowd"], 90,
          "Medium shot at eye level in the spotlit circle, slow push-in: Nikola Tesla (Image 1) stands triumphant and "
          "spreads his arms wide as lightning arcs crackle from the coils behind him, the crowd roaring beyond the "
          "circle. In the dark background, Thomas Edison (Image 2) turns away and walks out of the light. Mouths closed."),
]

edl_spec = [  # (t0, t1, clip, in) - in=None: lip-sync alignment from the clip's song window
    # Rule (user, 2026-11-08): never cut away while a line is still being sung. Every rap clip covers its whole
    # line up to the next line's start (last-word ends from work/words_edit.json); reactions live only in the
    # break (13.22-15.49) and the outro (26.17-30.76). R_T1 is rendered but unused.
    (0.00, 1.26, "OPEN", 0.6), (1.26, 2.53, "FACEOFF", 0.8),
    (2.53, 5.13, "A01", None), (5.13, 7.66, "A02", None), (7.66, 10.07, "A03", None), (10.07, 13.22, "A04", None),
    # break: H3 non-lip takes drift to a wide stage shot after ~1 s, so only their heads are used
    (13.22, 13.80, "CROWD_OOH", 0.2), (13.80, 14.50, "DJ", 0.0), (14.50, 15.49, "B_STEP", 0.4),
    (15.49, 18.00, "B01", None), (18.00, 20.86, "B02", None), (20.86, 23.25, "B03", None), (23.25, 26.17, "B04", None),
    # outro: crowd -> Edison stung -> his bulb dies -> Tesla triumphant
    (26.17, 27.27, "CROWD_ERUPT", 0.0), (27.27, 27.90, "R_E1", 0.4), (27.90, 28.50, "BLACKOUT", 0.55),
    (28.50, 30.759, "END", 0.2),
]
edl = [{"t0": a, "t1": b, "clip": c, "in": i} for a, b, c, i in edl_spec]

# sanity: contiguous timeline, every clip defined, non-lip windows fit their frames, lip clips cover their slot
ids = {c["id"]: c for c in clips}
for prev, cur in zip(edl, edl[1:]):
    assert abs(prev["t1"] - cur["t0"]) < 1e-6, (prev, cur)
for x in edl:
    c = ids[x["clip"]]
    if x["in"] is not None:
        assert x["in"] + (x["t1"] - x["t0"]) <= c["frames"] / 24 - 0.05, x
    else:
        assert x["t0"] >= c["audio"][0] - 1e-6, x

# guard: no cut while a line is still being sung (last word end from Suno alignment, 0.05 s tolerance)
WORDS = json.load(open(os.path.join(WORK, "words_edit.json"), encoding="utf-8"))
for x in edl:
    c = ids[x["clip"]]
    if c["kind"] == "rap":
        a0, a1 = c["audio"]
        last_end = max(w["t1"] for w in WORDS if a0 - 0.05 <= w["t0"] < a1)
        assert x["t1"] >= last_end - 0.05, f"{x['clip']} cut at {x['t1']:.2f} before its last word ends {last_end:.2f}"

# Edit-time effects (assemble.py fx_chain). Word times from work/words_edit.json.
fx = [
    {"type": "flash", "t0": 0.631, "t1": 0.711, "alpha": 0.7},             # first downbeat
    {"type": "punch", "t0": 8.807, "t1": 10.07, "amount": 0.08},           # A03 "Boy,"
    {"type": "punch", "t0": 11.573, "t1": 13.22, "amount": 0.12},          # A04 "without a single cent" (held to line end)
    {"type": "flash", "t0": 13.22, "t1": 13.30, "alpha": 0.8},             # crowd chant starts
    {"type": "punch", "t0": 24.835, "t1": 26.17, "amount": 0.08},          # B04 "high-voltage spark"
    {"type": "flash", "t0": 24.835, "t1": 24.915, "alpha": 0.85},
    {"type": "shake", "t0": 24.835, "t1": 25.40, "px": 9},
    {"type": "dark", "t0": 27.90, "t1": 28.50, "amount": 0.10},            # outro: Edison's bulb dies
]

json.dump(clips, open(os.path.join(WORK, "clips.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(fx, open(os.path.join(WORK, "fx.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(edl, open(os.path.join(WORK, "edl.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"wrote {len(clips)} clips, {len(edl)} edl entries, timeline {edl[0]['t0']:.2f}-{edl[-1]['t1']:.2f}s")
