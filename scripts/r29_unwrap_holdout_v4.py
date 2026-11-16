#!/usr/bin/env python3
"""r29_unwrap_holdout_v4.py — ZERO-LLM re-serialization fix (typed):
the c-0029 one-shot driver had a serialization artifact (the rec
literal parsed as a one-element tuple, so every json.dumps emitted a
[dict] array wrapper). The MACHINE-PRODUCED content is unchanged:
this script unwraps each [rec] -> rec and verifies the inner record's
a1_answer_sha256_16 recomputes from the a1_answer bytes (the
no-re-draw proof — the answers are the one-shot bytes, byte-identical;
Art. 29(c) respected)."""
import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
D = REPO / "eval" / "holdout_v4_generation"


def _sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


fixed = 0
for f in sorted(D.glob("HO4-*.json")):
    d = json.loads(f.read_text(encoding="utf-8"))
    if isinstance(d, list) and len(d) == 1 and isinstance(d[0], dict):
        rec = d[0]
        assert rec["a1_answer_sha256_16"] == _sha(rec["a1_answer"]), \
            f"sha mismatch on {f.name} — NOT the machine bytes"
        f.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n",
                     encoding="utf-8")
        fixed += 1
rec_path = D / "holdout_v4_generation_record.json"
r = json.loads(rec_path.read_text(encoding="utf-8"))
assert all(isinstance(x, list) and len(x) == 1 for x in r["results"])
r["results"] = [x[0] for x in r["results"]]
assert all(x["a1_answer_sha256_16"] == _sha(x["a1_answer"])
           for x in r["results"])
r["serialization_note"] = (
    "the c-0029 driver emitted [rec] array wrappers (rec literal "
    "parsed as a one-element tuple — a serialization artifact of the "
    "driver, not a machine output); unwrapped ZERO-LLM from the same "
    "bytes with per-record a1_answer_sha256_16 recompute verified "
    "(the answers are the one-shot bytes, byte-identical)")
rec_path.write_text(json.dumps(r, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")
print(f"unwrapped {fixed} per-problem records + the generation record "
      f"({len(r['results'])} rows); all sha recomputes PASS")
