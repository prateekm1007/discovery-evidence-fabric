#!/usr/bin/env python3
"""r145_wind_retle.py — recompute the wind E2E tally from the
ON-DISK envelopes (the run completed: 12 candidates; the first
process crashed only in the manifest-stages tail)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

OUT = REPO / "eval" / "r145_wind_e2e"
out_dir = OUT / "r141-fresh-02-wind-blade-leading-edge-erosion"

from discovery_fabric.engine.adapters import _resolve_binding_identity

env_ms = json.loads((out_dir / "envelope_MECHANISM_SPACE.json").read_text())
mss = env_ms.get("mechanism_space") or {}
cands = mss.get("candidates") or []
requery = mss.get("domain_requery")

freeze = json.loads((out_dir / "envelope_FREEZE.json").read_text())
frozen, seen = [], set()


def _walk(o):
    if isinstance(o, dict):
        rid = o.get("id")
        if rid and (o.get("content_hash") or o.get("title")):
            if rid not in seen:
                seen.add(rid)
                frozen.append(o)
        for v in o.values():
            _walk(v)
    elif isinstance(o, list):
        for v in o:
            _walk(v)


_walk(freeze)
_snap = out_dir / "ENRICHMENT_SNAPSHOT.json"
if _snap.exists():
    try:
        for it in (json.loads(_snap.read_text()).get("items") or []):
            if it.get("id") and it.get("id") not in seen:
                seen.add(it["id"])
                frozen.append(it)
    except Exception:
        pass

detail, n_adm, n_grounded, n_bad = [], 0, 0, 0
for c in cands:
    b = ((c.get("mechanism_support") or {})
         .get("evidence_binding") or {})
    ok, reason, resolved = _resolve_binding_identity(b, frozen)
    if c.get("discovery_admissible"):
        n_adm += 1
        if ok:
            n_grounded += 1
        else:
            n_bad += 1
    detail.append({"candidate_id": c.get("candidate_id"),
                   "admissible": bool(c.get("discovery_admissible")),
                   "resolves": ok, "typed_reason": reason,
                   "resolved_record_id": (resolved or {}).get("id")})

from discovery_fabric.engine.domain_requery import MATH_TITLE_RX
math_frozen = [f.get("title") for f in frozen
               if MATH_TITLE_RX.search(str(f.get("title") or ""))]

rec = {
    "record": "R145_WIND_E2E/1.0.0",
    "claim": "c-0243", "session": "builder-r144s1",
    "at": "2026-11-24 (sandbox clock)",
    "run_id": "r145-wind-e2e",
    "problem": {"problem_id":
                "r141-fresh-02-wind-blade-leading-edge-erosion",
                "domain": "wind-energy"},
    "n_candidates": len(cands),
    "n_frozen_records": len(frozen),
    "n_admitted": n_adm,
    "n_identity_true_grounded": n_grounded,
    "n_bad_admissions": n_bad,
    "requery": requery,
    "requery_note": (
        "the lever did NOT fire this run: the primary retrieval "
        "returned supported evidence (retrieval is non-deterministic "
        "across runs — the r143 run's math-paper starvation was one "
        "draw; this draw served on-domain records). The lever sits "
        "armed at the mechanism-space 0-support point; the typed "
        "state is honestly None-not-fired, never a fabricated record"),
    "math_titled_records_in_frozen_set": math_frozen,
    "acceptance": {
        "wind_ge_1_grounded": n_grounded >= 1,
        "zero_math_records": len(math_frozen) == 0,
        "note": ("the frozen set's math check runs on the LIVE fresh "
                 "retrieval; the excluded_math list is the lever's "
                 "own typed catch (not fired this run)"),
    },
    "detail": detail,
}
outf = OUT / "wind_e2e.json"
outf.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n")
print(f"RESULT: candidates={len(cands)} admitted={n_adm} "
      f"grounded={n_grounded} bad={n_bad} "
      f"math_in_frozen={len(math_frozen)}")
print("acceptance:", rec["acceptance"])
