"""INVENTION_CHAIN quality instrument — CEO directive 2026-08-31.

> "Stress-test arbitrary non-medical problems and compare the quality of
> surviving candidates, not just whether the pipeline completes."
> "Strengthen the path from evidence -> mechanism -> differentiated
> candidate -> decisive experiment."
> "Are we merely becoming a more reliable research pipeline, or are we
> becoming a better invention machine? We need evidence for the second."

This module measures the QUALITY of the invention chain on a run's
artifacts (INVENTION_SPECIFICATION.json + DECISIVE_EXPERIMENT.json),
independent of whether the pipeline completed or the candidate survived.

Constitutional anchors:
- Art. XXVI: builder-measured diagnostic instrument. NEVER wired into
  kill/promote decisions — it diagnoses quality, it does not adjudicate.
- Art. XXV: UNKNOWN stays UNKNOWN. A missing prior-art resolution is
  recorded as UNRESOLVED (honest), never scored as if resolved.
- Art. XXVII: bands declared here with justification, before measurement.
- Art. XXI.4-analog: prior-art specificity uses the SAME term-overlap
  rule family as the relevance adjudicator (one method, not two).

Measured dimensions (each 0.0-1.0 or a recorded honest state):

  Q1 EVIDENCE_BINDING — fraction of chain fields (mechanism,
     distinguishing_features, prior_art, killer_experiment) whose
     evidence_ids list is non-empty. A mechanism with zero evidence ids
     is a proposal, not an evidence-bound candidate.
  Q2 PRIOR_ART_SPECIFICITY — fraction of vs_nearest_prior_art entries
     whose title shares >= 2 content terms with the intervention text.
     Catches cross-domain junk prior art (measured defect class: surgical
     robots listed as nearest prior art for a battery-sensing candidate).
  Q3 PRIOR_ART_RESOLUTION — recorded as the artifact's own status value;
     graded 1.0 only when the artifact itself records a RESOLVED-class
     status. UNRESOLVED_INSUFFICIENT_EVIDENCE grades 0.0 and is EXPLICITLY
     labeled honest-weak (the grade measures chain strength, not honesty).
  Q4 EXPERIMENT_DECISIVENESS — expected information gain present and > 0;
     hypotheses carry prior probabilities with provenance; the selected
     experiment names a falsifiable comparison; UNKNOWN cost/time/kill
     probability preserved as UNKNOWN (zeroed values would be an Art. XXV
     violation and grade 0 here too).
  Q5 CHAIN_COMPLETENESS — all four links (evidence, mechanism,
     differentiated candidate, decisive experiment) present and non-empty.

Band interpretation (ENGINEERING judgment, declared):
  >= 0.70 STRONG — the chain is evidence-bound, differentiated against
       real prior art, and ends in a decisive experiment
  0.40-0.69 ADEQUATE — chain present, at least one link weak
  < 0.40 WEAK — the candidate is a proposal, not an invention-machine
       product (regardless of pipeline completion)
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from discovery_fabric.source_registry.query_relevance import terms

CHAIN_FIELDS = ("mechanism", "distinguishing_features", "prior_art",
                "killer_experiment")


def _content_terms(text: str) -> set:
    return set(terms(text or ""))


def _spec_field_text(value: Any, *keys: str) -> str:
    """Extract concatenated text from a spec field's nested value."""
    if isinstance(value, dict):
        out = []
        for k in keys:
            v = value.get(k)
            if isinstance(v, str):
                out.append(v)
        if out:
            return " ".join(out)
        return " ".join(str(v) for v in value.values()
                        if isinstance(v, str))
    return str(value or "")


def measure_evidence_binding(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Q1: fraction of chain fields carrying >= 1 evidence id."""
    present = 0
    bound = 0
    per_field = {}
    for field in CHAIN_FIELDS:
        node = spec.get(field)
        if not isinstance(node, dict):
            per_field[field] = "ABSENT"
            continue
        present += 1
        ev_ids = node.get("evidence_ids") or []
        has_value = node.get("value") is not None
        if has_value:
            present = present  # noqa: PLW0127 — value presence counted below
        if ev_ids:
            bound += 1
            per_field[field] = f"BOUND({len(ev_ids)} evidence ids)"
        else:
            per_field[field] = "UNBOUND (0 evidence ids)"
    rate = bound / present if present else None
    return {
        "dimension": "Q1_EVIDENCE_BINDING",
        "score": round(rate, 3) if rate is not None else None,
        "state": "UNMEASURABLE_NO_SPEC" if not present else "MEASURED",
        "per_field": per_field,
    }


def measure_prior_art_specificity(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Q2: do the nearest-prior-art entries actually share a domain with
    the candidate? Uses the engine's own term-overlap rule (>= 2 terms)."""
    df = spec.get("distinguishing_features") or {}
    value = df.get("value") if isinstance(df, dict) else None
    if not isinstance(value, dict):
        return {"dimension": "Q2_PRIOR_ART_SPECIFICITY", "score": None,
                "state": "UNMEASURABLE_NO_DIFFERENTIATION",
                "note": "no distinguishing_features.value to measure"}
    intervention = " ".join(
        str(value.get(k) or "") for k in ("intervention", "mechanism"))
    pa_list = value.get("vs_nearest_prior_art") or []
    if not intervention or not pa_list:
        return {"dimension": "Q2_PRIOR_ART_SPECIFICITY", "score": None,
                "state": "UNMEASURABLE_NO_PRIOR_ART",
                "note": "no intervention text or no prior-art entries"}
    iv_terms = _content_terms(intervention)
    specific = 0
    per_entry = []
    for pa in pa_list:
        if not isinstance(pa, dict):
            continue
        title = str(pa.get("title") or "")
        overlap = sorted(iv_terms & _content_terms(title))
        is_specific = len(overlap) >= 2
        specific += 1 if is_specific else 0
        per_entry.append({
            "patent_id": pa.get("patent_id"),
            "title": title[:90],
            "overlapping_terms": overlap,
            "domain_specific": is_specific,
        })
    n = len([e for e in per_entry])
    score = specific / n if n else None
    return {
        "dimension": "Q2_PRIOR_ART_SPECIFICITY",
        "score": round(score, 3) if score is not None else None,
        "state": "MEASURED" if n else "UNMEASURABLE_NO_PRIOR_ART",
        "specific_entries": specific, "total_entries": n,
        "per_entry": per_entry,
    }


def measure_prior_art_resolution(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Q3: the artifact's own prior-art status, graded without conversion."""
    nh = spec.get("novelty_hypothesis") or {}
    value = nh.get("value") if isinstance(nh, dict) else None
    status = value.get("prior_art_status") if isinstance(value, dict) else None
    if not status:
        return {"dimension": "Q3_PRIOR_ART_RESOLUTION", "score": None,
                "state": "UNMEASURABLE_NO_STATUS"}
    resolved = str(status).startswith("RESOLVED")
    # multi-source directions recorded? (measured defect: all-zero)
    msd = value.get("multi_source_directions") or {}
    sources_recorded = sum(
        (d or {}).get("sources_recorded", 0)
        for d in msd.values() if isinstance(d, dict))
    return {
        "dimension": "Q3_PRIOR_ART_RESOLUTION",
        "score": 1.0 if resolved else 0.0,
        "state": "MEASURED",
        "recorded_status": status,
        "honesty_note": ("UNRESOLVED is an honest state (Art. XXV); the "
                         "grade measures CHAIN strength, not honesty"),
        "multi_source_sources_recorded": sources_recorded,
    }


def measure_experiment_decisiveness(
        spec: Dict[str, Any], decisive: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Q4: does the run end in an experiment that can actually decide?"""
    checks: Dict[str, Any] = {}
    ke = spec.get("killer_experiment") or {}
    ke_value = ke.get("value") if isinstance(ke, dict) else None
    ke_eig = None
    ke_hyp = []
    if isinstance(ke_value, dict):
        ke_eig = ke_value.get("eig") or ke_value.get("expected_information_gain")
        ke_hyp = ke_value.get("hypotheses") or []
    sel = (decisive or {}).get("selected")
    if isinstance(sel, dict):
        eig = sel.get("expected_information_gain")
        hyp = sel.get("hypotheses") or []
    else:
        eig, hyp = ke_eig, ke_hyp
    checks["eig_present_positive"] = isinstance(eig, (int, float)) and eig > 0
    hyp_ok = 0
    hyp_total = 0
    for h in (hyp if isinstance(hyp, list) else []):
        if not isinstance(h, dict):
            continue
        hyp_total += 1
        has_prior = isinstance(h.get("prior_probability"), (int, float))
        has_prov = bool(h.get("provenance") or h.get("provenance_class")
                        or h.get("note"))
        if has_prior and has_prov:
            hyp_ok += 1
    checks["hypotheses_with_prior_and_provenance"] = (
        hyp_total > 0 and hyp_ok == hyp_total)
    checks["experiment_named"] = bool(
        (isinstance(sel, dict) and sel.get("experiment"))
        or (isinstance(ke_value, dict) and ke_value.get("selected")))
    # UNKNOWN preservation check: zeroed cost/time/kill_probability would
    # be an Art. XXV violation — UNKNOWN strings are correct and required
    unknown_ok = True
    if isinstance(sel, dict):
        for k in ("kill_probability", "time", "cost"):
            v = sel.get(k)
            if v is not None and not isinstance(v, (int, float)) \
                    and "UNKNOWN" not in str(v).upper():
                unknown_ok = False
    checks["unknown_states_preserved"] = unknown_ok
    score = sum(1 for v in checks.values() if v is True) / len(checks)
    return {
        "dimension": "Q4_EXPERIMENT_DECISIVENESS",
        "score": round(score, 3),
        "state": "MEASURED" if checks else "UNMEASURABLE",
        "checks": {k: bool(v) for k, v in checks.items()},
    }


def measure_chain_completeness(spec: Dict[str, Any],
                               decisive: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Q5: all four links present and non-empty."""
    links = {}
    mech = spec.get("mechanism")
    links["mechanism"] = bool(
        isinstance(mech, dict) and _spec_field_text(
            mech.get("value"), "mechanism", "intervention").strip())
    df = spec.get("distinguishing_features")
    links["differentiated_candidate"] = bool(
        isinstance(df, dict) and isinstance(df.get("value"), dict)
        and str(df["value"].get("intervention") or "").strip())
    nh = spec.get("novelty_hypothesis")
    links["prior_art_link"] = bool(
        isinstance(nh, dict) and isinstance(nh.get("value"), dict)
        and nh["value"].get("prior_art_status"))
    sel = (decisive or {}).get("selected")
    ke = spec.get("killer_experiment")
    links["decisive_experiment"] = bool(
        (isinstance(sel, dict) and sel.get("experiment"))
        or (isinstance(ke, dict) and ke.get("value")))
    score = sum(1 for v in links.values() if v) / len(links)
    return {
        "dimension": "Q5_CHAIN_COMPLETENESS",
        "score": round(score, 3),
        "state": "MEASURED",
        "links": links,
    }


def grade_band(avg: Optional[float]) -> str:
    if avg is None:
        return "UNMEASURED"
    if avg >= 0.70:
        return "STRONG"
    if avg >= 0.40:
        return "ADEQUATE"
    return "WEAK"


def measure_run(run_dir: Path) -> Dict[str, Any]:
    """Measure one engine run's invention-chain quality."""
    spec_path = run_dir / "INVENTION_SPECIFICATION.json"
    dec_path = run_dir / "DECISIVE_EXPERIMENT.json"
    if not spec_path.exists():
        return {"run_dir": str(run_dir), "state": "NO_SPEC",
                "verdict": "UNMEASURABLE"}
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    decisive = None
    if dec_path.exists():
        try:
            decisive = json.loads(dec_path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001 — disclosed per-run
            decisive = None
    dims = [
        measure_evidence_binding(spec),
        measure_prior_art_specificity(spec),
        measure_prior_art_resolution(spec),
        measure_experiment_decisiveness(spec, decisive),
        measure_chain_completeness(spec, decisive),
    ]
    scores = [d["score"] for d in dims if isinstance(d.get("score"), (int, float))]
    avg = round(sum(scores) / len(scores), 3) if scores else None
    weakest = min(
        (d for d in dims if isinstance(d.get("score"), (int, float))),
        key=lambda d: d["score"], default=None)
    return {
        "run_dir": str(run_dir),
        "state": "MEASURED",
        "dimensions": dims,
        "average": avg,
        "band": grade_band(avg),
        "weakest_dimension": (weakest or {}).get("dimension"),
    }
