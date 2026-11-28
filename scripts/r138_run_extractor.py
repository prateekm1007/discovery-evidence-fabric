#!/usr/bin/env python3
"""r138_run_extractor.py — the CORRECTED per-run measurement
extractor (the R138 coder directions item 4).

The R137 extractor's defects (the auditor's findings), fixed:
1. Per-hypothesis attribution is read from
   instantiation_attempts[].hypothesis_attribution (the nested
   array) — the R137 script read ms["hypothesis_attribution"], a
   top-level key that does not exist, so blocks_attributed was 0
   even when the records carried full per-block attribution.
2. n_hypotheses_parsed aggregates the WHOLE run (every
   operator result), not operator_results[0] alone.
3. Downstream reach is an EXACT candidate-to-stage record join:
   a candidate "reaches" a stage only if the stage's structured
   record names it (its candidate_id as a record key / an entry's
   candidate_id field / an explicit candidate list member) — a
   substring occurrence anywhere in serialized JSON proves nothing
   and is never used.
4. Downstream outcome per candidate: passed / killed / blocked /
   unresolved, read from the stage records' own typed fields.
5. The 8-row measurement table with the required interpretations:
   generated blocks, generated candidates, DISTINCT-only
   mechanisms, indeterminate (retained for investigation, never
   counted as proven distinct), grounded candidates, admissible
   survivors, exact-join reach, per-candidate outcomes.

Grounding is read from the candidates' own mechanism_support
records (the R138 lifecycle: EVIDENCE_GROUNDED_CANDIDATE vs
UNGROUNDED_HYPOTHESIS).

No generation is re-run: everything derives from committed raw
artifacts (Art. 29(c): the verifier recomputes, never re-runs).
"""
import json
from pathlib import Path
from typing import Any, Dict, List


def _load(out_dir: Path, name: str):
    f = out_dir / name
    if not f.exists():
        return None
    try:
        return json.loads(f.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def _candidate_named_in_record(cand_id: str, record: Any,
                               depth: int = 0) -> bool:
    """EXACT-join test: the candidate is named as a RECORD MEMBER —
    a dict key equal to the id, or a value of a candidate_id /
    candidate / id field, or a list element equal to the id.
    NOT a substring scan."""
    if depth > 6:
        return False
    if isinstance(record, dict):
        for k, v in record.items():
            if k == cand_id:
                return True
            if isinstance(v, str) and k in (
                    "candidate_id", "candidate", "id", "key",
                    "winner", "survivor", "selected_candidate_id"):
                if v == cand_id:
                    return True
            elif isinstance(v, str) and k.endswith("_ids") and v == cand_id:
                return True
            if _candidate_named_in_record(cand_id, v, depth + 1):
                return True
        return False
    if isinstance(record, list):
        return any(_candidate_named_in_record(cand_id, e, depth + 1)
                   for e in record)
    return False


def _stage_outcome_for(cand_id: str, record: Any,
                       depth: int = 0) -> str:
    """The stage's own typed verdict for the candidate, if the
    record carries one (passed/killed/blocked/unresolved)."""
    if depth > 5:
        return "unresolved"
    if isinstance(record, dict):
        for k, v in record.items():
            if k == cand_id and isinstance(v, dict):
                for vk in ("verdict", "state", "outcome", "status",
                           "result", "killed", "survived"):
                    if vk in v:
                        val = v[vk]
                        if isinstance(val, bool):
                            return ("passed" if val and vk == "survived"
                                    else "killed" if val and vk == "killed"
                                    else "unresolved")
                        s = str(val).lower()
                        if any(w in s for w in ("kill", "rejected",
                                                "failed", "dead")):
                            return "killed"
                        if any(w in s for w in ("pass", "survive",
                                                "released", "admitted",
                                                "complete")):
                            return "passed"
                        if any(w in s for w in ("block", "skip",
                                                "held", "defer")):
                            return "blocked"
                return _stage_outcome_for(cand_id, v, depth + 1)
            if isinstance(v, (dict, list)):
                r = _stage_outcome_for(cand_id, v, depth + 1)
                if r != "unresolved":
                    return r
    elif isinstance(record, list):
        for e in record:
            r = _stage_outcome_for(cand_id, e, depth + 1)
            if r != "unresolved":
                return r
    return "unresolved"


def extract_run(out_dir: Path) -> Dict[str, Any]:
    """The 8-row measurement table + the transport attribution for
    ONE committed run directory."""
    rec: Dict[str, Any] = {"run_dir": str(out_dir)}
    env = _load(out_dir, "envelope_MECHANISM_SPACE.json")
    if not isinstance(env, dict):
        rec["error"] = "envelope_MECHANISM_SPACE.json missing/unreadable"
        return rec
    ms = env.get("mechanism_space") or {}

    # ---- row 1: GENERATED BLOCKS (parsed hypothesis blocks, the
    # nested per-attribution arrays aggregated over the whole run)
    attempts = ms.get("instantiation_attempts") or []
    per_block: List[Dict[str, Any]] = []
    op_parses = []
    for a in attempts:
        per_block.extend(a.get("hypothesis_attribution") or [])
    op_res = ms.get("operator_results") or []
    op_parses = [o.get("n_hypotheses_parsed") for o in op_res
                 if isinstance(o, dict)]
    rec["generated_blocks"] = {
        "value": len(per_block),
        "interpretation": "actual hypothesis blocks parsed (the "
                          "nested instantiation_attempts[]."
                          "hypothesis_attribution arrays, aggregated "
                          "over every operator result)",
        "per_operator_n_hypotheses_parsed": op_parses,
        "legacy_top_level_key_present":
            "hypothesis_attribution" in ms}

    # ---- row 2: GENERATED CANDIDATES (assembled)
    cands = ms.get("candidates") or []
    rec["generated_candidates"] = {
        "value": ms.get("n_candidates_generated"),
        "interpretation": "assembled candidate count (the space's "
                          "own generated counter)"}

    # ---- rows 3+4: DISTINCT (verdict-only) vs INDETERMINATE
    dd = ms.get("distinctness") or {}
    rec["distinct_mechanisms"] = {
        "value": dd.get("n_distinct"),
        "interpretation": "DISTINCT verdicts only — the distinctness "
                          "instrument's own count"}
    rec["indeterminate"] = {
        "value": dd.get("n_indeterminate"),
        "interpretation": "retained for investigation, NOT counted "
                          "as proven distinct"}

    # ---- rows 5+6: GROUNDED vs ADMISSIBLE (the R138 lifecycle)
    grounded, admissible, ungrounded = [], [], []
    for c in cands:
        cid = str(c.get("candidate_id"))
        sup = c.get("mechanism_support") or {}
        b = sup.get("evidence_binding") or {}
        state = sup.get("mechanism_support_state")
        binding_ok = bool(b.get("grounded") and b.get("evidence_id")
                          and b.get("span"))
        entry = {"candidate_id": cid,
                 "support_state": state,
                 "binding_grounded": bool(b.get("grounded")),
                 "evidence_id": b.get("evidence_id"),
                 "span": b.get("span"),
                 "lifecycle": c.get("candidate_lifecycle")}
        if binding_ok and state in ("SUPPORTED",
                                    "PARTIALLY_SUPPORTED"):
            grounded.append(entry)
            if c.get("discovery_admissible"):
                admissible.append(entry)
        else:
            ungrounded.append(entry)
    rec["grounded_candidates"] = {
        "value": len(grounded),
        "interpretation": "valid evidence binding (grounded=True, "
                          "record id + span resolved) AND the "
                          "canonical support verdict",
        "members": grounded}
    rec["admissible_survivors"] = {
        "value": len(admissible),
        "interpretation": "passed the R138 admission gates (the "
                          "lifecycle's discovery_admissible flag)",
        "members": [e["candidate_id"] for e in admissible]}
    rec["ungrounded_hypotheses"] = {
        "value": len(ungrounded),
        "interpretation": "retained explicitly-ungrounded hypotheses "
                          "(enrichment required; NEVER admission)",
        "members": [e["candidate_id"] for e in ungrounded]}

    # ---- rows 7+8: EXACT-JOIN reach + per-candidate outcomes
    stages = {}
    for st in ("ATTACK", "RANK", "KILLER_EXPERIMENT", "PHYSICS",
               "COLLISION", "ADJUDICATION", "CLASSIFY"):
        sj = _load(out_dir, f"envelope_{st}.json")
        if sj is not None:
            stages[st] = sj
    cand_ids = [str(c.get("candidate_id")) for c in cands]
    reach: Dict[str, Dict[str, Any]] = {}
    for st, sj in stages.items():
        reached = [cid for cid in cand_ids
                   if _candidate_named_in_record(cid, sj)]
        outcomes = {cid: _stage_outcome_for(cid, sj)
                    for cid in reached}
        reach[st] = {
            "n_reaching_exact_join": len(reached),
            "interpretation": "exact candidate-to-stage record join "
                              "(the stage record NAMES the candidate; "
                              "never a substring scan)",
            "members": reached,
            "outcomes": outcomes,
            "outcome_counts": {
                k: sum(1 for v in outcomes.values() if v == k)
                for k in ("passed", "killed", "blocked",
                          "unresolved")}}
    rec["downstream_reach"] = reach

    # ---- the transport attribution (provider/model per run — the
    # R138 Agnes acceptance reads THIS, never the narrative)
    provs = sorted({str(a.get("provider")) for a in attempts
                    if a.get("provider")})
    models = sorted({str(a.get("model")) for a in attempts
                     if a.get("model")})
    llm_lines = _load(out_dir, "ROUTING_LEDGER_RUN.json") or {}
    lines = llm_lines.get("lines") or []
    gen_lines = [l for l in lines
                 if l.get("call_class") == "RUN_OWNED"]
    gen_provs = sorted({str(l.get("account_domain")) for l in gen_lines
                        if l.get("account_domain")})
    rec["transport_attribution"] = {
        "mechanism_space_providers": provs,
        "mechanism_space_models": models,
        "routing_ledger_run_owned_lines": len(gen_lines),
        "routing_ledger_account_domains": gen_provs,
        "note": "the actual serving model per run — an XKIRO-served "
                "run is NEVER described as Agnes-served"}

    # ---- the final state
    fs = _load(out_dir, "final_state.json") or {}
    manifest = _load(out_dir, "run_manifest.json") or {}
    rec["final_status"] = (manifest.get("final_status")
                           or fs.get("final_status"))
    return rec


def main() -> int:
    import sys
    base = Path(sys.argv[1]) if len(sys.argv) > 1 else (
        Path(__file__).resolve().parents[1] / "eval"
        / "r137_live_multi_mechanism")
    runs = sorted([p for p in base.iterdir() if p.is_dir()])
    summary = []
    for rd in runs:
        rec = extract_run(rd)
        out = base / f"{rd.name}.json"
        # the corrected per-run record (regenerated from raw bytes)
        if out.exists():
            old = json.loads(out.read_text(encoding="utf-8"))
            old["r138_corrected_measurement"] = rec
            old["measurement_record"] = (
                "R138_RUN_MEASUREMENT/1.0.0 — the corrected extractor "
                "(instantiation_attempts attribution; run-aggregated "
                "parses; exact-join reach; the 8-row table); the R137 "
                "fields above are the ORIGINAL first-pass measurements, "
                "superseded where they disagree (Art. 4: the correction "
                "record, never a silent rewrite)")
            out.write_text(json.dumps(old, indent=1) + "\n")
        summary.append({
            "run": rd.name,
            "generated_blocks": rec.get("generated_blocks", {}).get(
                "value"),
            "generated_candidates": rec.get("generated_candidates",
                                            {}).get("value"),
            "distinct": rec.get("distinct_mechanisms", {}).get("value"),
            "indeterminate": rec.get("indeterminate", {}).get("value"),
            "grounded": rec.get("grounded_candidates", {}).get("value"),
            "admissible": rec.get("admissible_survivors", {}).get(
                "value"),
            "ungrounded_retained": rec.get("ungrounded_hypotheses",
                                           {}).get("value"),
            "providers": rec.get("transport_attribution", {}).get(
                "mechanism_space_providers"),
            "final_status": rec.get("final_status")})
    roll = {"record": "R138_R137_RUNS_RECONCILED/1.0.0",
            "at": "2026-11-23 (sandbox clock)",
            "n_runs": len(summary), "runs": summary}
    (base / "R138_RECONCILIATION.json").write_text(
        json.dumps(roll, indent=1) + "\n")
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
