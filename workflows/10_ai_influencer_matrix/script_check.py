#!/usr/bin/env python3
"""30 条脚本检查 + 严格版盲听测试卷生成（纯本地，0 CCU）。

用法：
  python3 script_check.py                 # 检查 scripts_30_manifest.json，并生成盲听卷
  python3 script_check.py --seed 7        # 换一种题目顺序
  python3 script_check.py --file x.json   # 检查别的脚本文件

检查项对应 PERSONA_BIBLE_V3.md：
  1.3 完整交付：全条 30–38 词，去掉 CTA 后正文 ≤ 33 词，最后一句不是预告
  1.1 风控：效果承诺 / 资质 / 治疗类措辞（命中只是提示，最终要人读整句判断）
  1.2 绝对化：never / always 等（讲角色自己时允许，所以只提示）
  管线：hook_banner 只能用 Latin-1（subtitle_and_finalize.py 的 Arial/Impact 没有中文字形）；每人 10 条
输出：
  work/blind_test_sheet.md        给测试者的卷子（遮掉称呼和职业提示词，乱序，不说明三人各讲什么）
  work/blind_test_answer_key.json 答案（不要发给测试者）
"""
import argparse
import collections
import json
import random
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "scripts_30_manifest.json"
WORK = HERE / "work"
PER_PERSONA = 10

CTA_RE = re.compile(r"\s*Comment [A-Z]+\.\s*$")
TEASER_RE = re.compile(r"here's (what|the|how)|let me explain|stay tuned|part two", re.I)
RISK_RE = re.compile(
    r"worked for me|changed my life|guarantee|you'?ll finally|will make (him|her|them)|"
    r"\bcure|\bheal|therap(y|ist)|as a (financial|licensed|doctor|counsel)|my readers|"
    r"proven|results", re.I)
ABSOLUTE_RE = re.compile(r"\b(never|always|rarely|nobody|everyone)\b", re.I)

# 严格版盲听要遮掉的提示词（档案 1.2）
MASKS = [
    (r",?\s*\bdarling\b,?", ""),
    (r",?\s*\bmy friend\b,?", ""),
    (r"\ba wedding\b", "a party"),
    (r"\b(destination )?weddings\b", "parties"),
    (r"\b(destination )?wedding\b", "party"),
    (r"\b(the )?(bride|groom)'s\b", "the host's"),
    (r"\b(bride|groom)\b", "host"),
    (r"\bI've photographed\b", "I've seen"),
    (r"\bever photographed\b", "ever saw"),
    (r"\bphotographs\b", "posts"),
    (r"\bcamera\b", "phone"),
    (r"\btea\b", "coffee"),
    (r"\bmy counter\b", "my table"),
    (r"\b(Zhuangzi|Lao Tzu)('s)?\b", "an old book\\2"),
]


def words(s: str) -> int:
    return len(s.split())


def body_of(s: dict) -> str:
    return CTA_RE.sub("", s["spoken_en"])


def check(scripts: list, lo: int, hi: int) -> int:
    hard_total = 0
    for s in scripts:
        spoken, body = s["spoken_en"], body_of(s)
        hard, soft = [], []
        n, nb = words(spoken), words(body)
        if not lo <= n <= hi:
            hard.append(f"全条 {n} 词，超出 {lo}–{hi}")
        if nb > 33:
            hard.append(f"正文 {nb} 词 > 33")
        if body == spoken:
            hard.append("缺 CTA（Comment XXX.）")
        # 只看最后一句：正文中间的 "here's what I added" 可能是交付本身，结尾的才是预告
        last = re.split(r"(?<=[.?!])\s+", body.strip())[-1]
        if TEASER_RE.search(last):
            hard.append("以预告句收尾（1.3）")
        if "AI-generated" not in s["ig_caption"]:
            hard.append("ig_caption 缺 AI 标注")
        if any(ord(c) > 0xFF for c in s["hook_banner"]):  # Arial/Impact 覆盖 Latin-1（含 ·），不含中文
            hard.append(f"hook_banner 含 Latin-1 以外字符「{s['hook_banner']}」，现有字体会出方块")
        for field in ("spoken_en", "ig_caption", "pinned_comment"):
            for m in RISK_RE.finditer(s[field]):
                soft.append(f"⚠️ 风控词「{m.group(0)}」@{field}（人读整句判断）")
        for m in ABSOLUTE_RE.finditer(body):
            soft.append(f"· 绝对化「{m.group(0)}」（讲自己 / 描述可留）")
        hard_total += len(hard)
        print(f"{'❌' if hard else '✅'} {s['id']:4} {n:2} 词（正文 {nb:2}） {s['title']}")
        for x in hard + soft:
            print(f"     {x}")
    count = collections.Counter(s["persona"] for s in scripts)
    if len(scripts) == 3 * PER_PERSONA and set(count.values()) != {PER_PERSONA}:
        print(f"❌ 每人应 {PER_PERSONA} 条，实际 {dict(count)}")
        hard_total += 1
    return hard_total


def mask(s: str) -> str:
    for pat, rep in MASKS:
        s = re.sub(pat, rep, s, flags=re.I)
    s = re.sub(r"\s{2,}", " ", s).strip(" ,")
    # 遮词后句首可能变小写（". an old book says"），统一补回大写
    return re.sub(r"(^|[.?!]\s+)([a-z])", lambda m: m.group(1) + m.group(2).upper(), s)


def build_sheet(scripts: list, seed: int):
    items = [(s["id"], s["persona"], mask(body_of(s))) for s in scripts]
    random.Random(seed).shuffle(items)
    k = len(items) // 3
    WORK.mkdir(exist_ok=True)
    md = ["# 盲听测试卷（严格版 · 分组）", "",
          f"下面 {len(items)} 段话来自三个不同的人，每人 {k} 段。称呼和职业线索已经遮掉。",
          "请把它们分成三组（甲 / 乙 / 丙，组名随意），在每段后面写组名，并用一句话写你凭什么归到这一组。",
          "最后用一两句话分别描述每组「这个人」是怎样的人。", ""]
    for i, (_, _, line) in enumerate(items, 1):
        md += [f"{i}. {line}", "   组：____　理由：________________", ""]
    md += ["## 三组各是怎样的人", "", "甲：", "", "乙：", "", "丙：", ""]
    (WORK / "blind_test_sheet.md").write_text("\n".join(md))
    key = {"how_to_grade": "按多数票把每组对应到一个人物，再数归错的题",
           "answers": [{"no": i, "persona": p, "id": sid} for i, (sid, p, _) in enumerate(items, 1)]}
    (WORK / "blind_test_answer_key.json").write_text(json.dumps(key, ensure_ascii=False, indent=1))
    print(f"\n📝 盲听卷 {len(items)} 题 → {WORK / 'blind_test_sheet.md'}")
    print(f"🔑 答案 → {WORK / 'blind_test_answer_key.json'}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=str(MANIFEST))
    ap.add_argument("--seed", type=int, default=31)
    a = ap.parse_args()
    data = json.loads(Path(a.file).read_text())
    lo, hi = data["word_count_range"]
    bad = check(data["scripts"], lo, hi)
    build_sheet(data["scripts"], a.seed)
    raise SystemExit(1 if bad else 0)


if __name__ == "__main__":
    main()
