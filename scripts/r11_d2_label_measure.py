#!/usr/bin/env python3
"""r11_d2_label_measure.py — MEASURE before escalate (Art. L): run the
prototype semantic user-label audit over the 12 PRE-repair R3 answers
and print per-label verdicts with the byte basis. The escalation design
is decided from this measurement, never guessed."""
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SNAP = REPO / "eval" / "critic_regression_r3" / "prerepair"
STOP = set("""the a an of and or to for with at by on in per from is are
was were be been this that these those than then its it as not no user
constraint requirement stated approved specified target limit service
design choice parameter assumption maintains required their""".split())


def noun_ctx(txt: str) -> set:
    return {w for w in re.findall(r"[a-z]{4,}", txt.lower())} - STOP


def semantic_check(value_tok: str, label_txt: str, pt: str) -> dict:
    """value must occur in pt AND at least one occurrence window must
    share a content noun with the label's own context."""
    if value_tok not in pt:
        return {"verdict": "ABSENT", "windows": 0}
    wins = []
    lc = noun_ctx(label_txt)
    for m in re.finditer(re.escape(value_tok), pt):
        w = pt[max(0, m.start() - 90):m.end() + 90]
        shared = lc & noun_ctx(w)
        wins.append(sorted(shared)[:4])
        if shared:
            return {"verdict": "VERIFIED", "windows": 1,
                    "shared": sorted(shared)[:4]}
    return {"verdict": "SEMANTIC_MISMATCH", "windows": len(wins),
            "windows": wins[:3]}


def main() -> int:
    probs = json.loads((REPO / "eval" / "problems_dev12.json")
                       .read_text(encoding="utf-8"))
    plist = probs if isinstance(probs, list) else probs.get("problems", [])
    pt_by_id = {p["problem_id"]: json.dumps(p, ensure_ascii=False)
                for p in plist}
    # the number the label attributes: nearest number BEFORE the bracket
    _NUM = re.compile(r"(\d+(?:\.\d+)?)")
    _BR = re.compile(r"\((?:user[ -]?constraint|user[ -]stated|"
                     r"user[ -]approved)[^)]*\)|\[(?:user[ -]?constraint)"
                     r"[^\]]*\]|user[ -](?:approved|stated|specified)\b",
                     re.IGNORECASE)
    for f in sorted(SNAP.glob("*.json")):
        rec = json.loads(f.read_text(encoding="utf-8"))
        a = rec.get("a1_answer_prerepair") or ""
        pid = rec["problem_id"]
        pt = pt_by_id.get(pid, "")
        print(f"== {pid}")
        for m in _BR.finditer(a):
            # nearest number in the 130 chars before the bracket
            back = a[max(0, m.start() - 130):m.start()]
            nums = list(_NUM.finditer(back))
            if not nums:
                continue
            nm = nums[-1]
            value = nm.group(1)
            label_txt = back[max(0, nm.start() - 60):] + \
                a[m.start():m.end() + 60]
            r = semantic_check(value, label_txt, pt)
            print(f"   {value:>8} -> {r['verdict']:<17} "
                  f"ctx='{label_txt.strip()[:70]}' shared={r.get('shared')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
