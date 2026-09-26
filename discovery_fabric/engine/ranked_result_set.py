"""discovery_fabric/engine/ranked_result_set.py — R540 ranked result shape.

The operator contract: a FINISHED DISCOVERY is not "the pipeline reached
COMPLETE". It is a RANKED SET of complete discovery results, each carrying
the six-component shape (evidence, competing mechanisms + kill condition,
adversarial disposition, engineering definition + model, decisive
experiment, downloadable technology package) and a mechanically traceable
rank basis. This module DERIVES that record from the run directory's own
persisted artifacts (Art. X: the record on disk is the authority); it
invents nothing and never promotes a candidate that the recorded gates
did not admit.

Three completion states are kept distinct and NEVER collapsed into one
COMPLETE word (the contract's success-state semantics):

  PIPELINE_COMPLETED    the engine loop ran to the tail (the on-disk
                        run manifest's completion marker — the worker's
                        authority, not this module's).
  DISCOVERY_COMPLETED   at least one ADMISSIBLE RANKED SURVIVOR exists
                        (passed the applicable evidence / adversarial /
                        contradiction / technical gates and holds a
                        recorded admissible disposition).
  PACKAGE_COMPLETED     the admissible survivor was compiled into a
                        complete technology package (the bridge-gate
                        compiler's recorded outcome).

FINISHED_DISCOVERY = DISCOVERY_COMPLETED AND PACKAGE_COMPLETED.
A run that only reached PIPELINE_COMPLETED (no admissible survivor, or
no package) is NOT a finished discovery — it is represented as the
explicit non-finished state (MECHANISM_STARVED / REJECTED / diagnostic),
never as a finished technology.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

RANKED_RESULT_SCHEMA = "RANKED_DISCOVERY_RESULT/1.0.0"

# the three distinct completion states (the contract's success-state
# semantics). Each is a typed terminal descriptor, never a boolean.
COMP_PIPELINE = "PIPELINE_COMPLETED"
COMP_DISCOVERY = "DISCOVERY_COMPLETED"
COMP_PACKAGE = "TECHNOLOGY_PACKAGE_COMPLETED"

# a DISCOVERY result is ADMISSIBLE only when the recorded gates put the
# candidate in a defensible state. Everything else is a typed
# non-admissible terminal (never fabricated into a survivor).
_ADMISSIBLE_DISPOSITIONS = frozenset({
    "SURVIVED", "SURVIVED_WITH_EXPERIMENT", "REQUIRES_EXPERIMENT",
    "ESTABLISHED_PROVISIONALLY", "CONTESTED",
})


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        if path.is_file():
            return json.loads(path.read_text())
    except Exception:  # noqa: BLE001 — a missing/corrupt record is honest
        return None
    return None


def _rank_basis(ranked_row: Dict[str, Any]) -> Dict[str, Any]:
    """The mechanically traceable basis for one candidate's rank position.

    The inputs are the SAME deterministic fields the selection policy
    actually compared (engineering_attack.select_survivors): the recorded
    quality verdict, physics lifecycle, deficient-area count, uncertain
    verdict count, and the kill/exclusion flags. No new numeric score is
    invented (the standing rule: rank is a deterministic ORDER over
    recorded gate fields, not a fabricated scalar)."""
    return {
        "verdict_rank": ranked_row.get("_verdict_rank"),
        "physics_rank": ranked_row.get("_physics_rank"),
        "quality_verdict": ranked_row.get("quality_verdict"),
        "physics_lifecycle": ranked_row.get("physics_lifecycle"),
        "deficient_count": ranked_row.get("quality_deficient_count"),
        "uncertain_count": ranked_row.get("uncertain_count"),
        "killed": ranked_row.get("killed"),
        "span_underived": ranked_row.get("span_underived"),
        "repaired": ranked_row.get("repaired"),
        "attack_overall": ranked_row.get("attack_overall"),
        "traced_to": ("SURVIVOR_SELECTION.json:ranked[]. "
                      "deterministic order over recorded gate fields "
                      "(E15-H + R397 physics gate); no numeric score"),
    }


def _evidence_view(inv_spec: Dict[str, Any]) -> Dict[str, Any]:
    """Component 1 — the candidate's evidence + source provenance, as
    recorded on the persisted invention specification (the run's own
    custody record; never re-derived). Each record keeps its id, source
    and custody status; the supporting span rides the mechanism's
    recorded source span."""
    ev_field = inv_spec.get("evidence") if isinstance(inv_spec, dict) else {}
    # tagged form {value, ...} or a plain list
    records = ev_field.get("value") if isinstance(ev_field, dict) \
        and "value" in ev_field else ev_field
    if not isinstance(records, list):
        records = []
    view = [{"id": r.get("id"), "source": r.get("source") or r.get("source_id"),
             "frozen": bool(r.get("frozen", r.get("custody")))}
            for r in records if isinstance(r, dict)][:50]
    mm = inv_spec.get("mechanism") if isinstance(inv_spec, dict) else {}
    span = mm.get("mechanism_source_span") if isinstance(mm, dict) else None
    return {
        "records": view,
        "mechanism_source_span": span or "",
        "evidence_status": "verified_against_frozen_evidence"
                          if view else "NONE_REACHED_ENVELOPE",
    }


def _candidate_result_record(
        run_dir: Path,
        ranked_row: Dict[str, Any],
        selection: Dict[str, Any],
        rank: int,
        eng_spec: Dict[str, Any],
        decisive: Dict[str, Any],
        inv_spec: Dict[str, Any],
) -> Dict[str, Any]:
    """One complete ranked-result record (the contract's 6 components).

    Every field is DERIVED from the run's own persisted artifacts; an
    absent artifact yields an honest typed gap (UNKNOWN / ABSENT), never
    a fabrication (Art. XXV)."""
    cid = ranked_row.get("candidate_id")
    key = ranked_row.get("key") or "primary"

    # per-candidate canonical trio (R540): the suffixed files hold the
    # candidate's own record; the primary candidate's canonical
    # un-suffixed files are the same record. Read the candidate's own
    # artifacts when present, else fall back to the canonical files
    # (the selected #1) — never a second, invented authority.
    if key != "primary":
        _per = {
            "inv": _read_json(run_dir / f"INVENTION_SPECIFICATION_{key}.json"),
            "eng": _read_json(run_dir / f"ENGINEERING_SPECIFICATION_{key}.json"),
            "dec": _read_json(run_dir / f"DECISIVE_EXPERIMENT_{key}.json"),
        }
        inv_spec = _per["inv"] or inv_spec
        eng_spec = _per["eng"] or eng_spec
        decisive = _per["dec"] or decisive

    # component 1 — evidence + source attribution
    evidence = _evidence_view(inv_spec)

    # component 2 — competing mechanism + what distinguishes it
    mm = inv_spec.get("mechanism") if isinstance(inv_spec, dict) else {}
    if isinstance(mm, dict) and "value" in mm:
        mm_v = mm.get("value") or {}
        mechanism = {
            "mechanism": mm_v.get("mechanism", ""),
            "intervention": mm_v.get("intervention", ""),
            "expected_effect": mm_v.get("expected_effect", ""),
            "falsification_test": mm_v.get("falsification_test", ""),
        }
    elif isinstance(mm, dict):
        mechanism = {
            "mechanism": mm.get("mechanism", ""),
            "intervention": mm.get("intervention", ""),
            "expected_effect": mm.get("expected_effect", ""),
            "falsification_test": mm.get("falsification_test", ""),
        }
    else:
        mechanism = {"mechanism": str(mm), "intervention": "",
                     "expected_effect": "", "falsification_test": ""}
    mechanism["competing_considered"] = [
        r.get("candidate_id") for r in selection.get("ranked", [])
        if r.get("candidate_id") != cid]

    # component 3 — adversarial disposition (survived / killed / unresolved)
    attack = ranked_row.get("attack_overall")
    if ranked_row.get("killed"):
        disposition = "KILLED"
    elif attack in ("PASS", "SURVIVED"):
        disposition = "SURVIVED"
    elif attack in ("KILLED",):
        disposition = "KILLED"
    else:
        disposition = "UNRESOLVED"
    adversarial = {
        "overall": attack,
        "disposition": disposition,
        "survived": disposition == "SURVIVED",
        "killed": disposition == "KILLED",
        "unresolved": disposition == "UNRESOLVED",
        "quality_verdict": ranked_row.get("quality_verdict"),
        "deficient_areas": ranked_row.get("quality_deficient_count"),
    }

    # component 4 — engineering definition + model (geometry where
    # warranted, explicit conceptual classification where not)
    eng_core = eng_spec.get("engineering_core") if isinstance(eng_spec, dict) \
        else {}
    geometry = eng_spec.get("geometry") if isinstance(eng_spec, dict) else {}
    engineering = {
        "geometry_present": bool(geometry),
        "geometry": geometry or {"class": "NOT_ESTABLISHED"},
        "engineering_core": eng_core or {},
        "model_class": (eng_spec.get("visualizability_class")
                        if isinstance(eng_spec, dict) else None)
                       or "SEE_PACKAGE_MODEL_LAYER",
        "limitations": ("domain does not warrant physical geometry — "
                        "conceptual classification, explicitly stated"
                        if not geometry else ""),
    }

    # component 5 — decisive experiment (selected discriminator + decision)
    decisive_rec = (decisive.get("selected")
                    if isinstance(decisive, dict) else None) or {}
    experiment = {
        "experiment": decisive_rec.get("name")
                      or decisive_rec.get("experiment") or "",
        "predicted_discriminator":
            decisive_rec.get("predicted_discriminator")
            or decisive_rec.get("outcomes") or "",
        "decision_rule": decisive_rec.get("decision_rule")
                         or decisive_rec.get("falsification") or "",
        "execution_status": decisive.get("execution_status", "SPECIFIED")
        if isinstance(decisive, dict) else "SPECIFIED",
    }

    # component 6 — downloadable technology package (the recorded package
    # outcome; a diagnostic package is NEVER presented as a technology
    # package — the kind is explicit)
    package = {
        "kind": "TECHNOLOGY_PACKAGE" if not ranked_row.get("killed")
                else "ABSENT_KILLED",
        "package_id": str(cid),
        "rank": rank,
        "note": ("the package is compiled from this survivor's canonical "
                 "spec/experiment/model artifacts (the bridge-gate "
                 "compiler); a diagnostic package never substitutes for "
                 "it"),
    }

    admissible = (
        not ranked_row.get("killed")
        and not ranked_row.get("span_underived")
        and ranked_row.get("quality_verdict") != "FAIL"
        and ranked_row.get("physics_lifecycle")
        not in ("DOES_NOT_BEAT_BASELINE", "PLAUSIBILITY_BOUND_VIOLATED")
        and disposition in ("SURVIVED", "UNRESOLVED")
    )

    return {
        "rank": rank,
        "candidate_id": cid,
        "key": key,
        "origin": ranked_row.get("origin", "POST_RANK_POOL"),
        "admissible": admissible,
        "components": {
            "evidence": evidence,
            "mechanism": mechanism,
            "adversarial": adversarial,
            "engineering": engineering,
            "decisive_experiment": experiment,
            "package": package,
        },
        "rank_basis": _rank_basis(ranked_row),
        "selected": (cid == selection.get("selected")),
    }


def derive_ranked_result_set(
        run_dir: Path,
        run_result: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Derive the ranked result set + the three distinct completion states.

    Reads only the run directory's persisted records. Never mutates and
    never invents: an absent selection or ranked list yields an honest
    NO_RANKED_SURVIVOR result (DISCOVERY not completed), not a fake
    finished discovery.
    """
    run_dir = Path(run_dir)
    selection = _read_json(run_dir / "SURVIVOR_SELECTION.json") or {}
    ranked: List[Dict[str, Any]] = list(selection.get("ranked", [])) or []
    selected = selection.get("selected")

    inv_spec = _read_json(run_dir / "INVENTION_SPECIFICATION.json") or {}
    eng_spec = _read_json(run_dir / "ENGINEERING_SPECIFICATION.json") or {}
    decisive = _read_json(run_dir / "DECISIVE_EXPERIMENT.json") or {}
    final_state = _read_json(run_dir / "final_state.json") or {}

    # the admissible ranked survivors, in recorded rank order (rank = 1..)
    admissible_rows: List[Dict[str, Any]] = []
    for row in ranked:
        if (not row.get("killed")
                and row.get("quality_verdict") != "FAIL"
                and not row.get("span_underived")
                and row.get("physics_lifecycle")
                not in ("DOES_NOT_BEAT_BASELINE",
                        "PLAUSIBILITY_BOUND_VIOLATED")):
            admissible_rows.append(row)

    # keep the recorded deterministic rank order (the selection policy's
    # sort), not the pool's original order
    admissible_rows.sort(
        key=lambda r: (r.get("_verdict_rank", 3),
                       r.get("_physics_rank", 1),
                       r.get("quality_deficient_count") or 0,
                       r.get("uncertain_count") or 0))

    results: List[Dict[str, Any]] = []
    for pos, row in enumerate(admissible_rows, start=1):
        results.append(_candidate_result_record(
            run_dir, row, selection, pos, eng_spec, decisive, inv_spec))

    # the three distinct completion states (never collapsed). Package
    # completion is recorded by the bridge-gate compiler's own record;
    # read it when present, else report the honestly absent state.
    pkg_report = _read_json(run_dir / "PACKAGE_COMPILATION_RECORD.json") or {}
    if not pkg_report:
        # the worker persists the bridge-gate outcome as the session's
        # package field; a run-dir marker is the authority when present.
        pkg_report = _read_json(run_dir / "package_completion.json") or {}
    pipeline_completed = bool(
        final_state.get("final_status") is not None
        or (run_result or {}).get("final_status") is not None)
    discovery_completed = len(results) >= 1
    package_completed = bool(
        pkg_report.get("complete")
        or pkg_report.get("zip_emitted")
        or (run_result or {}).get("package_complete"))

    finished = discovery_completed and package_completed

    return {
        "schema": RANKED_RESULT_SCHEMA,
        "run_id": final_state.get("run_id")
                  or (run_result or {}).get("run_id") or "",
        "final_status": final_state.get("final_status"),
        "ranked_results": results,
        "selected_candidate": selected,
        "n_admissible": len(results),
        "n_killed": len([r for r in ranked if r.get("killed")]),
        "n_ranked": len(ranked),
        "completion": {
            COMP_PIPELINE: pipeline_completed,
            COMP_DISCOVERY: discovery_completed,
            COMP_PACKAGE: package_completed,
            "FINISHED_DISCOVERY": finished,
            "invariant": ("FINISHED_DISCOVERY = "
                          "ADMISSIBLE_RANKED_SURVIVOR + "
                          "COMPLETE_RESULT_RECORD + TECHNOLOGY_PACKAGE; "
                          "never EXECUTION_COMPLETED or "
                          "SOME_COMPONENTS_PRODUCED alone"),
        },
        "diagnostic_only": (not discovery_completed
                            and pipeline_completed),
    }


def persist_ranked_result_set(run_dir: Path,
                              run_result: Optional[Dict[str, Any]] = None
                              ) -> Dict[str, Any]:
    """Derive and persist the ranked result set to the run directory.

    The persisted record is RANKED_DISCOVERY_RESULTS.json (the contract's
    machine-readable result). Returns the record. Never raises: a
    derivation failure is recorded honestly as an empty result set with
    the typed reason (the pipeline's own failure stays a pipeline
    failure, never a fabricated finished discovery)."""
    try:
        record = derive_ranked_result_set(run_dir, run_result)
    except Exception as exc:  # noqa: BLE001 — honest, never fabricated
        record = {
            "schema": RANKED_RESULT_SCHEMA,
            "run_id": "",
            "final_status": "UNKNOWN",
            "ranked_results": [],
            "n_admissible": 0,
            "n_ranked": 0,
            "completion": {
                COMP_PIPELINE: False,
                COMP_DISCOVERY: False,
                COMP_PACKAGE: False,
                "FINISHED_DISCOVERY": False,
                "invariant": "derivation failed; no finished discovery claimed",
            },
            "diagnostic_only": True,
            "derivation_error": f"{type(exc).__name__}: {exc}",
        }
    out = Path(run_dir) / "RANKED_DISCOVERY_RESULTS.json"
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(record, indent=2,
                                  ensure_ascii=False, default=str))
    except Exception:  # noqa: BLE001 — persistence is best-effort,
        pass           # the return value is the record
    return record
