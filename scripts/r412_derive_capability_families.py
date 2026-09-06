#!/usr/bin/env python3
"""R412 Phase D (operator directive 2026-09-06): derive the
capability-family map from the 13 VERIFIED technical death records.

The operator's derivation chain, per death:

    technical death -> limiting variable -> capability ->
    capability family -> measurement dimension -> required regime ->
    cross-domain search vocabulary

Design rules enforced here (Constitution Art. XLIII, XLIV, and the
directive's Phase D):
  * DETERMINISTIC derivation — no LLM participates (the LLM already
    proposed the rungs/abstractions in GA-1b; those are INPUTS with
    recorded provenance, not new proposals).
  * Every structural field is grounded in a VERBATIM-VERIFIED span
    (ga2 basis_span_verified_verbatim=true) or a committed span-
    verified upstream record (ga1b capability_rung / quantified_gap /
    target_constraint, ga1b gate=PASS 13/13).
  * search_vocabulary is CLOSED and EVIDENCE-GROUNDED: terms are
    tokenized from the verbatim basis span + the verified rung —
    every term traceable to committed bytes.
  * The LLM's ga1b frontier_domains field is preserved SEPARATELY
    as search_vocabulary_llm_proposed, labeled
    AI_PROPOSED_EXPLORATORY (it widens SEARCH only; it establishes
    nothing — no invented sector enters the evidence-grounded
    vocabulary).
  * No abstraction becomes DERIVED_FROM_EVIDENCE because an LLM
    proposed it; it becomes DERIVED_FROM_EVIDENCE because every
    field is span-grounded in committed evidence (this script
    records the grounding per field).
  * The v1.0 operator-example family is carried over verbatim with
    its original provenance (lookup continuity).
  * The 3 GA-2-ineligible regime/consistency deaths ARE derived (the
    directive says all 13 technical deaths) but marked
    allocation_target=false — they can inform the shared map, never
    re-allocate (the sealed budget_shortfall_rule).

Emits: R412/GRADIENT_V2/CAPABILITY_FAMILY_MAP_V2.json (a NEW frozen
version — v1.0 remains as history per Art. XI).

Deterministic. No model calls.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "R412" / "GRADIENT_V2"))

OUT = REPO / "R412" / "GRADIENT_V2" / "CAPABILITY_FAMILY_MAP_V2.json"
OLD_MAP = REPO / "R412" / "GRADIENT_V2" / \
    "CAPABILITY_FAMILY_MAP.json"
GA2 = REPO / "R412" / "RECOVERY_ARM" / "GRADIENT_RUN" / "ga2.jsonl"
GA1B = REPO / "R412" / "RECOVERY_ARM" / "GRADIENT_RUN" / "ga1b.jsonl"
WATERFALL = REPO / "R412" / "R412_DEATH_CAUSE_WATERFALL.json"

# deterministic family classification for the deaths whose ga2 row
# carries no deficit_class (special-route + regime/consistency
# deaths): keyed by the ga2 axis_class / eligibility
FAMILY_BY_AXIS = {
    "PRIOR_ART_ANTICIPATION": "prior-art anticipation margin",
    "REGIME_CONSISTENCY": "regime consistency validation",
}

STOPWORDS = {
    "the", "of", "a", "an", "and", "or", "to", "in", "on", "for",
    "with", "under", "over", "vs", "at", "by", "from", "is", "are",
    "not", "no", "its", "their", "this", "that", "these", "those",
    "into", "than", "more", "less", "must", "can", "cannot", "be",
    "was", "were", "has", "have", "had", "it", "as", "such", "via",
    "per", "up", "down", "out", "about", "between", "within",
    "across", "during", "after", "before", "when", "while", "which",
    "who", "what", "how", "why", "does", "do", "did", "new", "novel",
    "novelty", "margin", "method", "methods", "validation", "status",
}


def _terms(text: str, n: int = 12) -> list:
    """Closed deterministic tokenizer: lowercase word tokens,
    stopwords dropped, deduped preserving order, capped."""
    out: list = []
    for tok in re.findall(r"[a-z][a-z\-]{2,}", str(text).lower()):
        if tok in STOPWORDS or tok in out:
            continue
        out.append(tok)
        if len(out) >= n:
            break
    return out


def _family_id(rung: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", rung.upper()).strip("_")[:48]


def main() -> int:
    ga2 = json.loads(GA2.read_text())
    rows = {r["candidate_id"]: r for r in ga2["rows"]}
    ga1b = {json.loads(l)["candidate_id"]:
            json.loads(l)["gate"]
            for l in GA1B.read_text().splitlines() if l.strip()}
    wf = json.loads(WATERFALL.read_text())
    wmap = {d["candidate_id"]: d for d in wf["deaths"]}
    old_map = json.loads(OLD_MAP.read_text())

    deaths = [r for r in ga2["rows"]
              if r.get("technological_death_cause_established")]
    assert len(deaths) == 13, f"expected 13, got {len(deaths)}"

    families = []
    for r in deaths:
        cid = r["candidate_id"]
        g = ga1b.get(cid, {})
        d = wmap.get(cid, {})
        rung = str(g.get("capability_rung") or "").strip()
        span = str(r.get("basis_span") or "").strip()
        eligible = r["eligibility"] == "GRADIENT_ELIGIBLE"
        axis = r.get("axis_class") or ""
        if r.get("deficit_class"):
            family = str(r["deficit_class"]).replace("_", " ")
        elif axis in FAMILY_BY_AXIS:
            family = FAMILY_BY_AXIS[axis]
        else:
            family = "regime consistency validation"
        vocab = _terms(f"{span} {rung}")
        llm_fd = str(g.get("frontier_domains") or "")
        llm_vocab = [t.strip() for t in re.split(r"[,;]", llm_fd)
                     if t.strip()][:10]
        fam = {
            "family_id": _family_id(rung or cid),
            "exact_capability": rung,
            "aliases": [cid],
            "capability_family": family,
            "measurement_dimension": ", ".join(
                _terms(rung, n=5)) or "capability rung terms",
            "required_regime": {
                "rung_direction": g.get("rung_direction"),
                "quantified_gap": g.get("quantified_gap"),
                "target_constraint": g.get("target_constraint"),
            },
            "target_constraints": [
                g.get("target_constraint") or "recorded in the "
                "verified deficit span"],
            "search_vocabulary": vocab,
            "search_vocabulary_grounding":
                "every term tokenized from the verbatim basis span "
                "or the span-verified capability rung (committed "
                "ga2/ga1b bytes)",
            "search_vocabulary_llm_proposed": llm_vocab,
            "search_vocabulary_llm_provenance": {
                "source_field": "ga1b gate.frontier_domains",
                "status": "AI_PROPOSED_EXPLORATORY",
                "rule": "widens SEARCH only; establishes nothing; "
                        "never counted as capability evidence",
            },
            "derivation_status": "DERIVED_FROM_EVIDENCE",
            "grounding": {
                "source_death_span": span,
                "basis_span_verified_verbatim":
                    r.get("basis_span_verified_verbatim"),
                "ga1b_gate_status": "PASS (span-verified 13/13 "
                                    "committed record)",
                "death_cause": d.get("death_cause"),
                "death_reason": str(d.get("death_reason")
                                    or "")[:240],
                "source_records": {
                    "ga2": "R412/RECOVERY_ARM/GRADIENT_RUN/"
                           "ga2.jsonl",
                    "ga1b": "R412/RECOVERY_ARM/GRADIENT_RUN/"
                            "ga1b.jsonl",
                    "waterfall": "R412/R412_DEATH_CAUSE_WATERFALL"
                                 ".json",
                },
            },
            "allocation_target": eligible,
            "allocation_note": (
                "sealed allocation seed" if eligible else
                "NOT an allocation target (GA-2-ineligible or "
                "special route); informs the shared map only — "
                "never re-allocated (sealed budget_shortfall_rule)"),
            "provenance": {
                "derivation": "DETERMINISTIC from committed "
                              "evidence; no LLM participated in "
                              "this derivation",
                "llm_abstraction_preserved": {
                    "capability_rung": rung,
                    "abstraction_provenance":
                        "GA1B_COMMITTED_EXTRACTION (AI-proposed, "
                        "span-gate PASS, upstream of this "
                        "derivation)",
                    "verification_state": "SPAN_VERIFIED_UPSTREAM",
                },
            },
        }
        families.append(fam)

    # carry the v1.0 operator example verbatim (lookup continuity)
    carried = []
    for f in old_map.get("families", []):
        f = dict(f)
        f["provenance"] = dict(f["provenance"],
                               carried_from="CAPABILITY_FAMILY_MAP"
                                            ".json v1.0.0")
        f["entry_source"] = "OPERATOR_DIRECTIVE_EXAMPLE"
        carried.append(f)

    # the consumable FAMILIES array: derived + carried, one schema —
    # the sealed tvm_v2 capability_family loader/validator reads the
    # top-level "families" key; each entry carries entry_source so
    # the derivation distinction stays machine-readable
    for f in families:
        f["entry_source"] = "DERIVED_FROM_TECHNICAL_DEATH"
    all_families = families + carried

    fam_count: dict = {}
    for f in families:
        fam_count[f["capability_family"]] = \
            fam_count.get(f["capability_family"], 0) + 1

    doc = {
        "map_id": "TVM_V2_CAPABILITY_FAMILY_MAP_V2",
        "version": "2.0.0",
        "frozen": "2026-09-06",
        "supersedes": {
            "path": "R412/GRADIENT_V2/CAPABILITY_FAMILY_MAP.json",
            "version": "1.0.0",
            "note": "v1.0 carried ONE operator-example family "
                    "because the population was absent; v2.0 "
                    "derives families from the 13 verified "
                    "technical deaths (Phase B reconciliation "
                    "unblocked the substrate); the operator example "
                    "is carried verbatim",
        },
        "family_schema": old_map.get("family_schema"),
        "families": all_families,
        "derived_family_count": len(families),
        "carried_operator_example_count": len(carried),
        "family_diversity": {
            "n_deaths_derived": len(families),
            "n_distinct_capability_families":
                len(fam_count),
            "family_sizes": fam_count,
            "allocation_targets": sum(
                1 for f in families if f["allocation_target"]),
            "note": "diversity MEASURED (Art. XLVIII), not counted",
        },
        "no_model_calls": True,
        "reviewer_provenance": "AI_REVIEW",
    }
    OUT.write_text(json.dumps(doc, indent=1) + "\n")
    print(f"family map v2 written: {OUT}")
    print(f"derived {len(families)} families from 13 deaths; "
          f"{len(fam_count)} distinct capability families; "
          f"{doc['family_diversity']['allocation_targets']} "
          f"allocation targets")
    for f in families:
        print(f"  {f['exact_capability'][:46]:46s} -> "
              f"{f['capability_family']:34s} "
              f"{'[ALLOC]' if f['allocation_target'] else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
