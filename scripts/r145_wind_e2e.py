#!/usr/bin/env python3
"""r145_wind_e2e.py — DIR-4's live test: the wind problem through the
CURRENT engine with the domain-anchored re-query lever.

The r143 yield run's wind row: 0 candidates, 0 grounded (the primary
retrieval served arxiv mathematics papers; the classifier typed 0
support; NO_EVIDENCE). THE LEVER (this run): on 0 support the
mechanism-space stage fires ONE typed second retrieval with the
abrasion_erosion family's domain anchors forced ('erosion wear
coating protection surface engineering' + the device head 'onshore
wind turbine'), the SAME classifier admits fresh records, and the
math-paper exclusion keeps pure mathematics records out of the fresh
set for this engineering problem.

ACCEPT (DIR 4): wind >=1 grounded candidate; 0 math-paper records in
the fresh retrieval; the yield >=2/5 stability unchanged (the other
four rows ride the committed r143 bytes).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

OUT = REPO / "eval" / "r145_wind_e2e"
OUT.mkdir(exist_ok=True)

WIND = {
    "problem_id": "r141-fresh-02-wind-blade-leading-edge-erosion",
    "device": "onshore wind turbine (4 MW, 150 m rotor, offshore-"
              "style composite blades)",
    "failure": "leading-edge rain/hail erosion of the composite "
               "blades drops annual energy production 4-6% and "
               "forces premature blade repair campaigns",
    "failure_mode": "leading-edge erosion energy loss",
    "constraint": "no blade geometry redesign (certified rotor); "
                  "repairs only at scheduled service windows",
    "domain": "wind-energy",
    "question": "What engineering change, intervention, or design "
                "would prevent or mitigate the stated failure?",
    "user_variables": [
        "no blade geometry redesign (certified rotor)",
        "repairs only at scheduled service windows",
        "device of record: 4 MW, 150 m rotor onshore turbine"],
    "split": "R145_WIND_E2E",
}


def main() -> int:
    from r7_queue_runner import _load_key_vault
    _load_key_vault()
    from discovery_fabric.engine.adapters import (
        _resolve_binding_identity)
    from discovery_fabric.engine.run import EngineRun

    out_dir = OUT / WIND["problem_id"]
    out_dir.mkdir(exist_ok=True)
    t0 = time.monotonic()
    print(f"=== R145 WIND E2E {WIND['problem_id']} ...", flush=True)
    run = EngineRun(dict(WIND), str(out_dir),
                    run_id="r145-wind-e2e",
                    with_package=False, resume=False)
    manifest = run.run()
    wall = time.monotonic() - t0

    env_ms = json.loads(
        (out_dir / "envelope_MECHANISM_SPACE.json").read_text())
    mss = env_ms.get("mechanism_space") or {}
    cands = mss.get("candidates") or []
    requery = mss.get("domain_requery")
    print(f"candidates: {len(cands)} | requery state: "
          f"{(requery or {}).get('state')}", flush=True)
    if requery:
        print(f"  requery query: {requery.get('query')}", flush=True)
        print(f"  fresh: {requery.get('n_fresh_records')} | "
              f"promoted: {requery.get('n_promoted')} | "
              f"excluded math: {len(requery.get('excluded_math') or [])}",
              flush=True)

    # the frozen custody (the verifier convention)
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
        except Exception:  # noqa: BLE001
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

    # DIR-4's math-paper check: NO math-titled record anywhere in the
    # fresh retrieval (the excluded list is the lever's own catch; the
    # frozen set is checked independently below)
    from discovery_fabric.engine.domain_requery import MATH_TITLE_RX
    math_frozen = [f.get("title") for f in frozen
                   if MATH_TITLE_RX.search(str(f.get("title") or ""))]

    rec = {
        "record": "R145_WIND_E2E/1.0.0",
        "claim": "c-0243", "session": "builder-r144s1",
        "at": "2026-11-24 (sandbox clock)",
        "run_id": "r145-wind-e2e",
        "problem": {"problem_id": WIND["problem_id"],
                    "domain": WIND["domain"]},
        "n_candidates": len(cands),
        "n_frozen_records": len(frozen),
        "n_admitted": n_adm,
        "n_identity_true_grounded": n_grounded,
        "n_bad_admissions": n_bad,
        "requery": requery,
        "math_titled_records_in_frozen_set": math_frozen,
        "acceptance": {
            "wind_ge_1_grounded": n_grounded >= 1,
            "zero_math_records": len(math_frozen) == 0,
            "note": ("the frozen set's math check runs on the LIVE "
                     "fresh retrieval; the excluded_math list is the "
                     "lever's own typed catch"),
        },
        "detail": detail,
        "wall_s": round(wall, 1),
        "manifest_stages": ([s.get("stage") for s in
                              manifest.get("stage_log")]
                             if isinstance(manifest, dict) else None)
        or (manifest if isinstance(manifest, list) else None),
    }
    outf = OUT / "wind_e2e.json"
    outf.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n")
    print(f"RESULT: candidates={len(cands)} admitted={n_adm} "
          f"grounded={n_grounded} bad={n_bad} "
          f"math_in_frozen={len(math_frozen)} ({round(wall,1)}s)",
          flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
