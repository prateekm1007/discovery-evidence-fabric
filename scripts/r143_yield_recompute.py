#!/usr/bin/env python3
"""r143_yield_recompute — the DIR-4 acceptance recompute v2 over the
committed run bytes (NO LLM calls, no re-roll): the driver's own
verifier-convention pass (the frozen set re-collected from the freeze
envelope, every admitted binding re-resolved) with the two typed
supplements the live run predates:

  1. the binding-repair save-path fix (ab23406ec): a candidate whose
     ledger attempt carries a verbatim-quote binding repair (the
     compliance-proven anchor) is re-resolved with the REPAIRED
     binding, not the stale malformed one the old save path left;
  2. the custody join (the twin's Art. XLIV snapshot): the frozen
     acceptance set = the freeze envelope's records UNION the
     ENRICHMENT_SNAPSHOT.json items (both are committed, hash-pinned
     bytes; the runtime identity gate resolved against exactly this
     union).

The raw generation bytes (the stage envelopes + the ledgers) are
NEVER rewritten — only the derived acceptance records (.mech.json +
SUMMARY.json) are recomputed, and the recompute is typed in them."""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
OUT = REPO / "eval" / "r143_yield_run"


def _walk(o, frozen, seen):
    if isinstance(o, dict):
        rid = o.get("id")
        if rid and (o.get("content_hash") or o.get("title")):
            if rid not in seen:
                seen.add(rid)
                frozen.append(o)
        for v in o.values():
            _walk(v, frozen, seen)
    elif isinstance(o, list):
        for v in o:
            _walk(v, frozen, seen)


def main() -> int:
    from discovery_fabric.engine.adapters import _resolve_binding_identity

    probs = sorted(p.name[:-len(".mech.json")]
                   for p in OUT.glob("*.mech.json"))
    summary = {"record": "R143_YIELD_RUN_ACCEPTANCE_V2/1.0.0",
               "claim": "c-0233",
               "work_id": "r143-grounded-yield-broaden",
               "session": "builder-r142s2",
               "at": "2026-11-23 (sandbox clock)",
               "recompute_note": (
                   "the acceptance recompute v2 over the committed run "
                   "bytes: no LLM calls, no re-roll; the frozen set = "
                   "the freeze envelope UNION the ENRICHMENT_SNAPSHOT "
                   "custody join; the binding-repair save-path fix "
                   "(ab23406ec) applied offline — a ledger-repaired "
                   "verbatim-quote binding re-resolves against it"),
               "per_problem": []}
    tot_g = tot_bad = 0
    grounded_problems = 0
    for pid in probs:
        d = OUT / pid
        env_ms = json.loads(
            (d / "envelope_MECHANISM_SPACE.json").read_text())
        cands = (env_ms.get("mechanism_space") or {}).get(
            "candidates") or []
        freeze = json.loads((d / "envelope_FREEZE.json").read_text())
        frozen, seen = [], set()
        _walk(freeze, frozen, seen)
        snap_path = d / "ENRICHMENT_SNAPSHOT.json"
        n_snap = 0
        if snap_path.exists():
            snap = json.loads(snap_path.read_text())
            for it in (snap.get("items") or []):
                if it.get("id") and it.get("id") not in seen:
                    seen.add(str(it.get("id")))
                    frozen.append({"id": it.get("id"),
                                   "content_hash": it.get("content_hash"),
                                   "title": it.get("title"),
                                   "abstract": it.get("abstract")})
                    n_snap += 1
        ledger = {}
        led_path = d / "ENRICHMENT_LEDGER.json"
        if led_path.exists():
            for a in (json.loads(led_path.read_text())
                      .get("attempts") or []):
                ledger[str(a.get("candidate_id"))] = a
        detail, n_adm, n_g, n_bad = [], 0, 0, 0
        for c in cands:
            b = ((c.get("mechanism_support") or {})
                 .get("evidence_binding") or {})
            ok, reason, resolved = _resolve_binding_identity(b, frozen)
            repaired = None
            if not ok and c.get("discovery_admissible"):
                att = ledger.get(str(c.get("candidate_id")))
                if att and att.get("binding_repair") and \
                        att.get("binding", {}).get("evidence_id"):
                    rb = att["binding"]
                    ok, reason, resolved = _resolve_binding_identity(
                        rb, frozen)
                    if ok:
                        repaired = {
                            "from": "ledger_verbatim_quote_repair",
                            "record_id": rb.get("evidence_id")}
            if c.get("discovery_admissible"):
                n_adm += 1
                if ok:
                    n_g += 1
                else:
                    n_bad += 1
                detail.append({
                    "candidate_id": c.get("candidate_id"),
                    "lifecycle": c.get("candidate_lifecycle"),
                    "support_state": (c.get("mechanism_support") or {})
                    .get("mechanism_support_state"),
                    "resolves": ok, "typed_reason": reason,
                    "resolved_record_id": (resolved or {}).get("id"),
                    "binding_repair_applied": repaired,
                    "enriched": (c.get("candidate_lifecycle") or "")
                    .endswith("_ENRICHED")})
        rec = json.loads((OUT / f"{pid}.mech.json").read_text())
        rec["acceptance_v2"] = {
            "recomputed": True,
            "n_admitted": n_adm, "n_identity_true_grounded": n_g,
            "n_bad_admissions": n_bad,
            "n_frozen_records": len(frozen),
            "n_snapshot_records": n_snap,
            "detail": detail,
            "note": ("the derived acceptance record recomputed offline "
                     "from the committed envelopes (the raw generation "
                     "bytes untouched); the save-path fix ab23406ec "
                     "applied; the ledger-repaired verbatim bindings "
                     "re-resolved")}
        rec["n_admitted"] = n_adm
        rec["n_identity_true_grounded"] = n_g
        rec["n_bad_admissions"] = n_bad
        (OUT / f"{pid}.mech.json").write_text(
            json.dumps(rec, indent=1, ensure_ascii=False) + "\n")
        summary["per_problem"].append({
            "pid": pid, "candidates": rec.get("n_candidates"),
            "admitted": n_adm, "grounded": n_g, "bad": n_bad})
        tot_g += n_g
        tot_bad += n_bad
        if n_g > 0:
            grounded_problems += 1
        print(f"{pid}: adm={n_adm} grounded={n_g} bad={n_bad}")
    summary["runs"] = len(probs)
    summary["problems_grounded"] = grounded_problems
    summary["total_identity_true_grounded"] = tot_g
    summary["total_bad_admissions"] = tot_bad
    summary["acceptance_ge_2_of_5"] = grounded_problems >= 2
    summary["zero_bad_admissions"] = tot_bad == 0
    (OUT / "SUMMARY.json").write_text(
        json.dumps(summary, indent=1) + "\n")
    print(f"TOTAL: problems_grounded={grounded_problems}/5 "
          f"total_grounded={tot_g} total_bad={tot_bad} "
          f"acceptance_ge_2_of_5={grounded_problems >= 2} "
          f"zero_bad={tot_bad == 0}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
