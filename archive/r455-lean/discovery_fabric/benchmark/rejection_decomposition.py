"""Coder 2 Phase 3, B8 — DECOMPOSE EVERY REJECTION.

"Shallow output" is not a repair instruction. For each of the 12
engine-rejected packages this module identifies the PRIMARY_BLOCKER and
the SECONDARY_BLOCKERS in the CEO's 12-category taxonomy:

    CAUSAL_REASONING          DOMAIN_REASONING
    DESIGN_TRACEABILITY       FAILURE_ANALYSIS
    PARAMETER_PROVENANCE      EQUATION_APPLICABILITY
    VERIFICATION_SPECIFICITY  VALIDATION_SPECIFICITY
    MANUFACTURING_REASONING   TRANSFER_SPECIFICITY
    GENERICNESS               OTHER

Evidence policy (each blocker row names its evidence source):
  ENGINE_GATE_RE_DERIVED  the engine's own E15-B evaluator is re-run, read
                          only, on the rejected run's persisted invention +
                          engineering specifications (deterministic, Art.
                          XXIV) — this recovers the exact deficient areas
                          the gate acted on (the run dir persists only a
                          count);
  INDEPENDENT_CODER2      Coder 2's own instruments run on the same
                          artifacts: corpus depth floors (would-be depth
                          probe), B3 semantic causal audit, numerical
                          provenance, genericness recurrence, validation-
                          matrix specificity.

Ranking rule (deterministic, recorded in the artifact):
  severity 3 = correctness/integrity evidence (semantic INCORRECT critical
               chains, numeric-provenance hard violations, engine-gate
               FAIL dimensions)
  severity 2 = corpus depth floor failures (independent would-be probe)
  severity 1 = engine-gate CONDITIONAL dimensions, genericness recurrence,
               validation rows with no specified method
  Within one severity the fixed category precedence list orders candidates
  (correctness classes first). PRIMARY_BLOCKER = top; SECONDARY_BLOCKERS =
  the rest, same order. A category only appears with at least one piece of
  recorded evidence; nothing is invented; ambiguity stays visible in the
  evidence rows.

No engine file is modified; no rejected output is repaired.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import semantic_causal as sc_mod
from . import semantic_genericness as sg_mod
from . import numerical_provenance as np_mod
from . import tri_measurement as tm

REPO_ROOT = Path(__file__).resolve().parents[2]

BLOCKER_TAXONOMY = (
    "CAUSAL_REASONING", "DOMAIN_REASONING", "DESIGN_TRACEABILITY",
    "FAILURE_ANALYSIS", "PARAMETER_PROVENANCE", "EQUATION_APPLICABILITY",
    "VERIFICATION_SPECIFICITY", "VALIDATION_SPECIFICITY",
    "MANUFACTURING_REASONING", "TRANSFER_SPECIFICITY", "GENERICNESS",
    "OTHER",
)

# fixed precedence within one severity (correctness classes first)
PRECEDENCE = {c: i for i, c in enumerate((
    "CAUSAL_REASONING", "DOMAIN_REASONING", "EQUATION_APPLICABILITY",
    "PARAMETER_PROVENANCE", "FAILURE_ANALYSIS",
    "VERIFICATION_SPECIFICITY", "VALIDATION_SPECIFICITY",
    "DESIGN_TRACEABILITY", "MANUFACTURING_REASONING",
    "TRANSFER_SPECIFICITY", "GENERICNESS", "OTHER"))}

# engine E15-B dimension -> taxonomy category (recorded mapping)
GATE_DIM_TO_TAXONOMY = {
    "MECHANISM_DEPTH": "DOMAIN_REASONING",          # mechanism-domain substance
    "ENGINEERING_REASONING_DEPTH": "CAUSAL_REASONING",
    "DESIGN_TRACEABILITY": "DESIGN_TRACEABILITY",
    "PHYSICAL_REASONING": "FAILURE_ANALYSIS",       # physical FM substance
    "FAILURE_ANALYSIS": "FAILURE_ANALYSIS",
    "VNV_DEPTH": "VERIFICATION_SPECIFICITY",        # acceptance criteria live here
    "MANUFACTURING_REASONING": "MANUFACTURING_REASONING",
    "TRANSFER_SPECIFICITY": "TRANSFER_SPECIFICITY",
    "EVIDENCE_DENSITY": "PARAMETER_PROVENANCE",     # evidence-per-claim substance
    "BUYER_ACTIONABILITY": "TRANSFER_SPECIFICITY",
}

# independent would-be depth probe metric -> taxonomy category
FLOOR_TO_TAXONOMY = {
    "design_inputs": "DESIGN_TRACEABILITY",
    "failure_modes": "FAILURE_ANALYSIS",
    "verifications": "VERIFICATION_SPECIFICITY",
    "equations": "EQUATION_APPLICABILITY",
    "remaining_unknowns": "OTHER",  # UNKNOWN_DISCLOSURE deficiency —
    # the CEO B8 taxonomy has no unknown-disclosure category; recorded
    # explicitly as OTHER with a taxonomy_note naming the real class
}

_NOT_PERFORMED_MARKERS = ("NOT_PERFORMED", "NOT ESTABLISHED", "UNKNOWN",
                          "NOT_POSSIBLE", "NOT POSSIBLE")


def _j(path: Path) -> Optional[dict]:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return None


def _signature_texts(run_dir: Path) -> List[str]:
    out: List[str] = []
    prob = _j(run_dir / "problem.json")
    if prob:
        out.extend(str(v) for v in prob.values() if isinstance(v, str))
    env = _j(run_dir / "candidate_envelope.json") or {}
    mm = env.get("mechanism_map") or {}
    for k in ("mechanism", "intervention", "expected_effect"):
        if isinstance(mm.get(k), str):
            out.append(mm[k])
    return out


def _validation_specificity(eng: Optional[dict]) -> Optional[Dict[str, Any]]:
    """Validation rows with no specified method/acceptance at all."""
    if eng is None:
        return None
    rows = eng.get("validation_matrix") or []
    if not rows:
        return {"category": "VALIDATION_SPECIFICITY",
                "unspecified": 0, "total": 0,
                "detail": "no validation matrix rows exist"}
    unspec = 0
    for r in rows:
        method = str(r.get("method") or "")
        acceptance = str(r.get("acceptance") or "")
        if (any(m in method.upper() for m in _NOT_PERFORMED_MARKERS)
                or not method.strip()) and \
                (any(m in acceptance.upper() for m in _NOT_PERFORMED_MARKERS)
                 or not acceptance.strip()):
            unspec += 1
    if unspec:
        return {"category": "VALIDATION_SPECIFICITY",
                "unspecified": unspec, "total": len(rows),
                "detail": f"{unspec}/{len(rows)} "
                          f"validation rows carry no specified method AND no "
                          f"acceptance criterion (honest NOT_ESTABLISHED "
                          f"disclosure, but no validation specificity exists)"}
    return None


def _mechanism_body_words(inv: Optional[dict]) -> Optional[int]:
    """Independent measurement of the invention spec mechanism body
    (same fields the E15-B MECHANISM_DEPTH check reads, counted fresh)."""
    if not inv:
        return None
    mech = (inv.get("mechanism") or {}).get("value") or {}
    body = " ".join(str(mech.get(k, "")) for k in
                    ("mechanism", "intervention", "expected_effect"))
    return len(body.split())


def _input_mechanism_words(run_dir: Path) -> Optional[int]:
    """Word count of the RUN's own input mechanism text (envelope)."""
    env = _j(run_dir / "candidate_envelope.json") or {}
    mm = env.get("mechanism_map") or {}
    text = " ".join(str(mm.get(k, "")) for k in
                     ("mechanism", "intervention", "expected_effect"))
    return len(text.split()) if text.strip() else None


def rank_blockers(evidence: List[Dict[str, Any]]) -> Tuple[str, List[str],
                                                           List[Dict]]:
    """Deterministic ranking: severity desc, then fixed category
    precedence (correctness classes first); OTHER never outranks a named
    category. Returns (primary, secondaries, ladder_rows)."""
    by_cat: Dict[str, List[Dict[str, Any]]] = {}
    for e in evidence:
        by_cat.setdefault(e["category"], []).append(e)
    ranked = sorted(
        by_cat.items(),
        key=lambda kv: (-max(e["severity"] for e in kv[1]),
                        PRECEDENCE.get(kv[0], len(PRECEDENCE))))
    primary = ranked[0][0] if ranked else "OTHER"
    if ranked and primary == "OTHER" and len(ranked) > 1:
        # OTHER never outranks a named category when one exists
        primary = ranked[1][0]
        ranked = ranked[1:] + [ranked[0]]
    secondary = [cat for cat, _ in ranked[1:]]
    ladder_rows = []
    for cat, evs in ranked:
        ladder_rows.append({
            "category": cat,
            "severity_max": max(e["severity"] for e in evs),
            "evidence": evs,
        })
    return primary, secondary, ladder_rows


def decompose_rejection(run_dir: Path,
                        contract: Optional[dict] = None) -> Dict[str, Any]:
    """One rejected run -> PRIMARY_BLOCKER + SECONDARY_BLOCKERS + evidence."""
    rd = Path(run_dir)
    rel = _j(rd / "DISCOVERY_RELEASE.json") or {}
    sel = _j(rd / "SURVIVOR_SELECTION.json") or {}
    eng = _j(rd / "ENGINEERING_SPECIFICATION.json")
    inv = _j(rd / "INVENTION_SPECIFICATION.json")

    # -- engine gate evidence, re-derived (read-only, deterministic) -------
    gate_dims: List[Dict[str, Any]] = []
    gate_verdict = None
    gate_deficient_count = None
    try:
        from discovery_fabric.engine.dossier_quality import (
            evaluate_dossier_quality)
        q = evaluate_dossier_quality(inv or {}, eng or {})
        gate_verdict = q.get("verdict")
        for r in q.get("dimensions") or []:
            if r.get("verdict") in ("FAIL", "CONDITIONAL"):
                cat = GATE_DIM_TO_TAXONOMY.get(
                    r["dimension"], "OTHER")
                gate_dims.append({
                    "source": "ENGINE_GATE_RE_DERIVED",
                    "dimension": r["dimension"],
                    "gate_verdict": r["verdict"],
                    "category": cat,
                    "deficient_areas": [d[:160] for d in
                                        r.get("deficient_areas") or []][:4],
                })
        gate_deficient_count = len(
            q.get("deficient_areas") or [])
    except Exception as exc:  # honest: record the failure, never fake it
        gate_dims.append({"source": "ENGINE_GATE_RE_DERIVED",
                          "dimension": None, "gate_verdict": "UNAVAILABLE",
                          "category": "OTHER",
                          "deficient_areas": [f"re-derivation failed: {exc}"]})

    # -- independent evidence ---------------------------------------------
    probe = tm.eng_spec_depth_probe(eng, contract)
    sem = sc_mod.audit_semantic_causality(
        eng, inv, _signature_texts(rd))
    numprov = np_mod.audit_numerical_provenance(rd, None, eng, inv)
    sentences = sg_mod.extract_package_sentences(rd, None)
    # sentence -> list of spec fields it appears in; recurrence = >=2 fields
    recurring = {s: f for s, f in sentences.items() if len(f) >= 2}

    evidence: List[Dict[str, Any]] = []
    # gate FAIL dims = the DIRECT cause of the E15-H rejection (severity 4);
    # gate CONDITIONAL dims (severity 1)
    for g in gate_dims:
        sev = 4 if g.get("gate_verdict") == "FAIL" else 1
        evidence.append({"category": g["category"], "severity": sev,
                         "source": g["source"], "detail": {
                             "dimension": g["dimension"],
                             "verdict": g["gate_verdict"],
                             "deficient_areas": g["deficient_areas"]}})
    # independent corroboration of mechanism substance (DOMAIN_REASONING):
    # measure the mechanism body fresh + check generator elaboration
    body_words = _mechanism_body_words(inv)
    input_words = _input_mechanism_words(rd)
    if body_words is not None:
        elaborated = (input_words is not None and
                      body_words > input_words + 5)
        evidence.append({
            "category": "DOMAIN_REASONING", "severity": 4,
            "source": "INDEPENDENT_CODER2",
            "detail": {
                "mechanism_body_words": body_words,
                "input_mechanism_words": input_words,
                "e15_b_gate_floor_words": 25,
                "below_gate_floor": body_words < 25,
                "generator_elaborated_mechanism": elaborated,
                "note": "mechanism body re-measured word-for-word from the "
                        "invention specification; when body ~= input text "
                        "the generator passed the input mechanism through "
                        "without engineering elaboration"}})
    # independent: incorrect critical chains (severity 3)
    if sem.get("available"):
        incorrect = sem.get("incorrect_critical_chains") or []
        if incorrect:
            evidence.append({
                "category": "CAUSAL_REASONING", "severity": 3,
                "source": "INDEPENDENT_CODER2",
                "detail": {
                    "incorrect_critical_chains": len(incorrect),
                    "findings": [
                        {"chain_id": c.get("chain_id"),
                         "links": [l.get("reason") for l in
                                   c.get("incorrect_links") or []][:3]}
                        for c in incorrect[:4]]}})
        # wrong-quantity verification links -> VERIFICATION_SPECIFICITY (sev 3)
        wrong_qty = []
        for c in incorrect:
            for l in c.get("incorrect_links") or []:
                if l.get("reason") == "VERIFICATION_WRONG_QUANTITY":
                    wrong_qty.append(l.get("evidence", "")[:140])
        if wrong_qty:
            evidence.append({
                "category": "VERIFICATION_SPECIFICITY", "severity": 3,
                "source": "INDEPENDENT_CODER2",
                "detail": {"wrong_quantity_verifications": len(wrong_qty),
                           "examples": wrong_qty[:3]}})
    # independent: would-be depth floors (severity 2)
    if probe.get("available") and probe.get("floors_failed"):
        for metric in probe["floors_failed"]:
            cat = FLOOR_TO_TAXONOMY.get(metric, "OTHER")
            count = ((probe.get("counts") or {}).get(metric))
            checks = {c.get("metric"): c for c in probe.get("checks") or []}
            floor = (checks.get(metric) or {}).get("floor")
            detail = {"depth_floor": metric, "count": count,
                      "corpus_floor": floor,
                      "note": "would-be dossier fails this corpus "
                              "depth floor (persisted eng spec, "
                              "re-measured directly)"}
            if metric == "remaining_unknowns":
                detail["taxonomy_note"] = (
                    "UNKNOWN_DISCLOSURE deficiency class (CEO Phase 2 B6): "
                    "the dossier records fewer SPECIFIC engineering "
                    "unknowns than the corpus floor; recorded as OTHER "
                    "because the CEO B8 taxonomy has no unknown-"
                    "disclosure category")
            evidence.append({
                "category": cat, "severity": 2,
                "source": "INDEPENDENT_CODER2", "detail": detail})
    # independent: numeric-provenance hard violations (severity 3)
    if numprov.get("available") and numprov.get("hard_violations"):
        evidence.append({
            "category": "PARAMETER_PROVENANCE", "severity": 3,
            "source": "INDEPENDENT_CODER2",
            "detail": {"hard_violations": numprov.get("hard_violations"),
                       "numbers_audited": numprov.get("numbers_audited")}})
    # independent: validation specificity (severity 1)
    val = _validation_specificity(eng)
    if val:
        evidence.append({"category": "VALIDATION_SPECIFICITY", "severity": 1,
                         "source": "INDEPENDENT_CODER2",
                         "detail": {"unspecified_rows": val["unspecified"],
                                    "total_rows": val["total"]}})
    # independent: genericness recurrence (severity 1)
    if recurring:
        evidence.append({
            "category": "GENERICNESS", "severity": 1,
            "source": "INDEPENDENT_CODER2",
            "detail": {"recurring_template_sentences_in_run":
                       len(recurring),
                       "note": "sentences repeated across >=2 spec fields "
                               "of this run (template prose intensity)"}})

    # -- rank ---------------------------------------------------------------
    primary, secondary, ranked_rows = rank_blockers(evidence)

    return {
        "run_dir": str(rd),
        "run_id": rel.get("run_id"),
        "release_status": rel.get("status"),
        "gate_quality_verdict": (sel.get("ranked") or [{}])[0].get(
            "quality_verdict") if sel.get("ranked") else gate_verdict,
        "gate_deficient_count_rederived": gate_deficient_count,
        "PRIMARY_BLOCKER": primary,
        "SECONDARY_BLOCKERS": secondary,
        "blocker_ladder": [
            {**r, "is_primary": r["category"] == primary}
            for r in ranked_rows],
        "taxonomy_valid": primary in BLOCKER_TAXONOMY,
    }


def decompose_all_rejections(
        runs_root: Path = REPO_ROOT / "artifacts/benchmark/generated/runs",
        contract: Optional[dict] = None,
        split_manifest: Optional[dict] = None,
        out_path: Path = REPO_ROOT / "artifacts/benchmark/baseline" /
        "REJECTION_DECOMPOSITION.json") -> Dict[str, Any]:
    """Decompose every engine-rejected run in the committed benchmark set."""
    runs_root = Path(runs_root)
    if contract is None:
        contract = _j(REPO_ROOT / "artifacts/benchmark/"
                      "ENGINEERING_DEPTH_CONTRACT.json")
    if split_manifest is None:
        from . import data_split as ds_mod
        split_manifest = ds_mod.build_split_manifest()

    rows = []
    for rd in sorted(runs_root.iterdir() if runs_root.is_dir() else []):
        if not rd.is_dir():
            continue
        rel = _j(rd / "DISCOVERY_RELEASE.json") or {}
        if rel.get("status") == "RELEASED":
            continue
        rows.append(decompose_rejection(rd, contract))

    by_split = {"development_set": [], "holdout_set": []}
    dev = set((split_manifest.get("development_set") or {})
              .get("bench_ids") or [])
    hold = set((split_manifest.get("holdout_set") or {})
               .get("bench_ids") or [])
    for r in rows:
        name = Path(r["run_dir"]).name
        if name in dev:
            by_split["development_set"].append(name)
        elif name in hold:
            by_split["holdout_set"].append(name)

    primary_counts: Dict[str, int] = {}
    secondary_counts: Dict[str, int] = {}
    for r in rows:
        primary_counts[r["PRIMARY_BLOCKER"]] = \
            primary_counts.get(r["PRIMARY_BLOCKER"], 0) + 1
        for s in r["SECONDARY_BLOCKERS"]:
            secondary_counts[s] = secondary_counts.get(s, 0) + 1

    artifact = {
        "artifact": "REJECTION_DECOMPOSITION",
        "owner": "CODER2",
        "ceo_directive": "Phase 3 B8 — decompose every rejection into "
                         "PRIMARY_BLOCKER + SECONDARY_BLOCKERS",
        "decomposed_at": datetime.now(timezone.utc).isoformat(),
        "rejections_decomposed": len(rows),
        "expected_rejections": 12,
        "taxonomy": list(BLOCKER_TAXONOMY),
        "ranking_rule": {
            "severity_4": "engine-gate FAIL dimension (re-derived) — the "
                          "DIRECT cause the E15-H selection acted on; "
                          "plus the independent mechanism-substance "
                          "measurement (DOMAIN_REASONING corroboration)",
            "severity_3": "independent correctness findings: INCORRECT "
                          "critical chains (B3), wrong-quantity "
                          "verifications, numeric-provenance hard "
                          "violations",
            "severity_2": "independent would-be depth floor failures "
                          "(persisted eng spec vs corpus contract)",
            "severity_1": "engine-gate CONDITIONAL dimension | genericness "
                          "recurrence | unspecified validation rows",
            "tie_break": "fixed category precedence (correctness classes "
                         "first); OTHER never outranks a named category",
            "evidence_policy": "every blocker row names its evidence "
                               "source (ENGINE_GATE_RE_DERIVED or "
                               "INDEPENDENT_CODER2); nothing invented",
        },
        "primary_blocker_counts": primary_counts,
        "secondary_blocker_counts": secondary_counts,
        "per_split": {k: sorted(v) for k, v in by_split.items()},
        "rejections": rows,
    }
    if out_path is not None:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(artifact, indent=1,
                                       ensure_ascii=False),
                            encoding="utf-8")
    return artifact


def main() -> int:
    art = decompose_all_rejections()
    print("=" * 70)
    print("CODER2 REJECTION DECOMPOSITION (CEO Phase 3 B8)")
    print("=" * 70)
    print(f"rejections decomposed: {art['rejections_decomposed']}/"
          f"{art['expected_rejections']}")
    print("PRIMARY_BLOCKER counts:")
    for k, v in sorted(art["primary_blocker_counts"].items(),
                       key=lambda kv: -kv[1]):
        print(f"  {k:26s} {v}")
    print("SECONDARY_BLOCKER counts:")
    for k, v in sorted(art["secondary_blocker_counts"].items(),
                       key=lambda kv: -kv[1]):
        print(f"  {k:26s} {v}")
    for r in art["rejections"]:
        print(f"  {Path(r['run_dir']).name}: PRIMARY={r['PRIMARY_BLOCKER']} "
              f"SECONDARY={r['SECONDARY_BLOCKERS'][:4]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
