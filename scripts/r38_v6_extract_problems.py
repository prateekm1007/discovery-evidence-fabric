#!/usr/bin/env python3
"""r38_v6_extract_problems.py — extract the SEALED v6 problems from
the pinned audit tip into the builder tree (problems ONLY; the
PRIVATE rubric is never read). Run AFTER the serving window verifies
and IMMEDIATELY before the one-shot driver (claim c-0038 is already
PUSHED — Art. 29(b) order satisfied since R35)."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AUDIT_REF = "origin/audit/r11-auditor-verdict-20261114"
SRC = "audit/holdout_v6/holdout_v6_problems.json"
DST = REPO / "eval" / "holdout_v6_problems.json"
REGISTERED = "4d60488a581897b9b7452158158049e65656c26ac58ea7e611236047a9aab804"


def canonical_tuple_hash(doc):
    fresh = [p for p in doc["problems"]
             if p.get("contamination_tag") is None]
    payload = [
        [p.get("problem_id"), p.get("device"), p.get("failure"),
         p.get("question"), p.get("question_type"),
         list(p.get("user_variables") or [])]
        for p in sorted(fresh, key=lambda x: str(x.get("problem_id")))]
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def main() -> int:
    r = subprocess.run(["git", "show", f"{AUDIT_REF}:{SRC}"],
                       capture_output=True, text=True, check=True)
    raw = r.stdout.encode()
    doc = json.loads(raw)
    n = len(doc.get("problems") or [])
    h = canonical_tuple_hash(doc)
    reg = doc.get("selection_sha256")
    print(f"problems={n} file_sha16={hashlib.sha256(raw).hexdigest()[:16]} "
          f"anchor16={h[:16]} registered16={(reg or 'NONE')[:16]}")
    if h != REGISTERED or (reg and reg != REGISTERED):
        print("TYPED: seal anchor MISMATCH — extraction refused, "
              "NO BURN (Art. 3)")
        return 2
    DST.write_bytes(raw)
    print(f"extracted -> {DST} (rubric NEVER read)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
