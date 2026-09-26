"""discovery_fabric/engine/ranked_result_set.py — R540/R541 ranked result shape.

The operator contract: a FINISHED DISCOVERY is not "the pipeline reached
COMPLETE". It is a RANKED SET of complete discovery results, each carrying
the six-component shape (evidence, competing mechanisms + kill condition,
adversarial disposition, engineering definition + model, decisive
experiment, downloadable technology package) and a mechanically traceable
rank basis.

R541 correction of the R540 presentation defect: this module does NOT
invent package existence and does NOT keep a second survivor-admission
authority. The architecture is:

    SURVIVOR_SELECTION.json (the engine's AUTHORITATIVE ranked survivor
    records — the selection/admission decision; Art. X one authority)
            |
            v
    ranked result records (each PROJECTS the selection row + the
    candidate's own persisted spec trio + a real candidate-bound
    package identity)
            |
            +---- candidate A -> ... -> package A (candidate-bound ZIP)
            +---- candidate B -> ... -> package B (candidate-bound ZIP)
            +---- candidate C -> ... -> package C (candidate-bound ZIP)

Every ranked result carries an immutable package identity
(candidate_id, rank, package_id, zip_name, zip_sha256, manifest,
complete) that is PROVEN from the candidate-bound package artifact on
disk (RANKED_PACKAGE_RECORDS.json + the actual ZIP hash), never derived
from candidate state alone (Art. II/III/X: the record proves the
artifact; the artifact's hash is the authority).

Three completion states are kept distinct and NEVER collapsed into one
COMPLETE word (the contract's success-state semantics):

  PIPELINE_COMPLETED    the engine loop ran to the tail (the run
                        manifest's completion marker).
  DISCOVERY_COMPLETED   at least one authoritative ADMISSIBLE ranked
                        survivor exists whose adversarial disposition is
                        SURVIVED (an UNRESOLVED candidate is NOT a
                        finished survivor — Art. XXV: unknown stays
                        unknown; a candidate that never survived the
                        challenge is not presented as a finished
                        discovery).
  TECHNOLOGY_PACKAGE_COMPLETED
                        the run's full ranked set has a COMPLETE
                        candidate-bound package for EVERY displayed
                        admissible survivor (one package for the
                        selected #1 is NOT package completion for the
                        whole ranked set).

FINISHED_DISCOVERY = DISCOVERY_COMPLETED AND TECHNOLOGY_PACKAGE_COMPLETED
AND every displayed ranked survivor has its own complete candidate-bound
package. No candidate may receive a package merely because the pipeline
reached COMPLETE; a candidate that the gates did not admit (killed,
UNRESOLVED, or span-unsupported) has no package.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

RANKED_RESULT_SCHEMA = "RANKED_DISCOVERY_RESULT/2.0.0"

# the three distinct completion states (the contract's success-state
# semantics). Each is a typed terminal descriptor, never a boolean.
COMP_PIPELINE = "PIPELINE_COMPLETED"
COMP_DISCOVERY = "DISCOVERY_COMPLETED"
COMP_PACKAGE = "TECHNOLOGY_PACKAGE_COMPLETED"


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        if path.is_file():
            return json.loads(path.read_text())
    except Exception:  # noqa: BLE001 — a missing/corrupt record is honest
        return None
    return None


def _sha256_file(path: Path) -> Optional[str]:
    """The actual on-disk SHA-256 of a file (Art. II/III: the hash is the
    authority, never a claimed value). None when the file is absent."""
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
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


def _package_binding(run_dir: Path,
                     ranked_row: Dict[str, Any],
                     rank: int,
                     disposition: str,
                     pkg_records: Dict[str, Any],
                     ) -> Dict[str, Any]:
    """The candidate-bound package identity for one ranked result.

    PROVEN, never classified: the package record must come from the
    run's own RANKED_PACKAGE_RECORDS.json (the engine's per-candidate
    package build record), the candidate-bound ZIP must exist on disk,
    and its SHA-256 must match the recorded value. A killed / UNRESOLVED
    candidate (or a candidate whose package was never compiled) carries
    an honestly absent package (complete=False, kind=ABSENT_*), NEVER a
    borrowed / invented TECHNOLOGY_PACKAGE.

    The identity invariant (enforced here and re-verified by
    verify_ranked_result_set):
        ranked_results[i].candidate_id == package_record.candidate_id
        ranked_results[i].package.zip_sha256 == SHA256(actual ZIP)
        ranked_results[i].package.complete == (ZIP exists and passes)
    """
    cid = ranked_row.get("candidate_id")
    key = ranked_row.get("key") or "primary"

    # a killed candidate never receives a technology package (contract
    # #10) — the kind is explicit, complete is False.
    if disposition == "KILLED":
        return {
            "kind": "ABSENT_KILLED",
            "package_id": None,
            "zip_name": None,
            "zip_sha256": None,
            "manifest": None,
            "candidate_id": cid,
            "rank": rank,
            "complete": False,
            "note": "killed candidate — no technology package (CEO rule 9)",
        }

    # the candidate-bound package record, when the engine compiled it
    rec = (pkg_records.get("packages") or {}).get(key) \
        or pkg_records.get("by_candidate_id", {}).get(cid)
    if not isinstance(rec, dict) or not rec.get("complete"):
        # no complete candidate-bound package exists on disk — an
        # UNRESOLVED candidate or a not-yet-compiled package. Honest
        # absence; NEVER a borrowed #1 package and NEVER a claimed
        # TECHNOLOGY_PACKAGE (the contract's #1/#5/#6 invariants).
        return {
            "kind": "ABSENT_NOT_COMPILED",
            "package_id": None,
            "zip_name": None,
            "zip_sha256": None,
            "manifest": None,
            "candidate_id": cid,
            "rank": rank,
            "complete": False,
            "note": ("no complete candidate-bound package on disk for "
                     "this ranked candidate (the #1 package is NOT "
                     "reused as this candidate's package)"),
        }

    # the candidate-bound ZIP must exist on disk and its hash must match
    zip_name = rec.get("zip_name")
    zip_sha = rec.get("zip_sha256")
    zip_path = run_dir / zip_name if zip_name else None
    measured = _sha256_file(zip_path) if zip_path and zip_path.exists() \
        else None
    hash_matches = (zip_sha is not None) and (measured == zip_sha)
    manifest = rec.get("manifest") or rec.get("manifest_files")

    return {
        "kind": "TECHNOLOGY_PACKAGE",
        "package_id": rec.get("package_id") or str(cid),
        "zip_name": zip_name,
        "zip_sha256": zip_sha,
        "zip_sha256_measured": measured,
        "zip_sha256_matches": bool(hash_matches),
        "manifest": manifest,
        "candidate_id": rec.get("candidate_id") or cid,
        "rank": rank,
        "complete": bool(rec.get("complete") and hash_matches),
        "note": ("candidate-bound technology package; the ZIP hash is "
                 "re-measured from the on-disk artifact (Art. II/III: "
                 "the measured bytes are the authority)"),
    }


def _candidate_result_record(
        run_dir: Path,
        ranked_row: Dict[str, Any],
        selection: Dict[str, Any],
        rank: int,
        eng_spec: Dict[str, Any],
        decisive: Dict[str, Any],
        inv_spec: Dict[str, Any],
        pkg_records: Dict[str, Any],
) -> Dict[str, Any]:
    """One complete ranked-result record (the contract's 6 components).

    Every field is DERIVED from the run's own persisted artifacts; an
    absent artifact yields an honest typed gap (UNKNOWN / ABSENT), never
    a fabrication (Art. XXV)."""
    cid = ranked_row.get("candidate_id")
    key = ranked_row.get("key") or "primary"

    # per-candidate canonical trio (R541): the suffixed files hold the
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

    # component 3 — adversarial disposition. R541: the disposition is
    # the AUTHORITATIVE value recorded on the SURVIVOR_SELECTION row
    # (the engine's own admission decision, Art. X) — NOT re-derived
    # here from candidate state. A row whose disposition is UNRESOLVED
    # (the challenge never produced a recorded verdict) is NOT a
    # finished survivor.
    disposition = ranked_row.get("disposition") or "UNRESOLVED"
    adversarial = {
        "overall": ranked_row.get("attack_overall"),
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

    # component 6 — candidate-bound technology package (PROVEN, never
    # classified)
    package = _package_binding(run_dir, ranked_row, rank, disposition,
                               pkg_records)

    # admissibility is the AUTHORITATIVE recorded decision (the
    # SURVIVOR_SELECTION row's ranked_admissible flag when present, else
    # the row's recorded gate fields) — NOT a second admission policy.
    # R541: an UNRESOLVED adversarial disposition is NOT a finished
    # survivor — only a recorded SURVIVED disposition is admissible.
    recorded_adm = ranked_row.get("ranked_admissible")
    admissible = (
        bool(recorded_adm) if recorded_adm is not None
        else (not ranked_row.get("killed")
              and ranked_row.get("quality_verdict") != "FAIL"
              and not ranked_row.get("span_underived")
              and ranked_row.get("physics_lifecycle")
              not in ("DOES_NOT_BEAT_BASELINE",
                      "PLAUSIBILITY_BOUND_VIOLATED")))
    admissible = admissible and disposition == "SURVIVED"

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

    PROJECTS the engine's authoritative SURVIVOR_SELECTION.json (the
    survivor/admission record) — it never re-derives admission (no
    second authority, Art. X). Each admissible survivor's package
    identity is bound from the candidate-bound package record on disk
    (PROVEN, never classified). A diagnostic-only run (no admissible
    ranked survivor) is an honest non-finished state, never a fake
    finished discovery."""
    run_dir = Path(run_dir)
    selection = _read_json(run_dir / "SURVIVOR_SELECTION.json") or {}
    ranked: List[Dict[str, Any]] = list(selection.get("ranked", [])) or []
    selected = selection.get("selected")

    inv_spec = _read_json(run_dir / "INVENTION_SPECIFICATION.json") or {}
    eng_spec = _read_json(run_dir / "ENGINEERING_SPECIFICATION.json") or {}
    decisive = _read_json(run_dir / "DECISIVE_EXPERIMENT.json") or {}
    final_state = _read_json(run_dir / "final_state.json") or {}
    pkg_records = _read_json(run_dir / "RANKED_PACKAGE_RECORDS.json") or {}

    # the authoritative admissible rows, in the RECORDED deterministic
    # rank order (the selection policy's sort) — the engine's own
    # admission decision, not a re-derived policy.
    admissible_rows: List[Dict[str, Any]] = []
    for row in ranked:
        _adm = row.get("ranked_admissible")
        if _adm is None:
            _adm = (not row.get("killed")
                    and row.get("quality_verdict") != "FAIL"
                    and not row.get("span_underived")
                    and row.get("physics_lifecycle")
                    not in ("DOES_NOT_BEAT_BASELINE",
                            "PLAUSIBILITY_BOUND_VIOLATED"))
        # R541: an UNRESOLVED adversarial disposition is not a finished
        # survivor — only a recorded SURVIVED disposition is admissible.
        if _adm and (row.get("disposition") or "SURVIVED") == "SURVIVED":
            admissible_rows.append(row)

    admissible_rows.sort(
        key=lambda r: (r.get("_verdict_rank", 3),
                       r.get("_physics_rank", 1),
                       r.get("quality_deficient_count") or 0,
                       r.get("uncertain_count") or 0))

    results: List[Dict[str, Any]] = []
    for pos, row in enumerate(admissible_rows, start=1):
        results.append(_candidate_result_record(
            run_dir, row, selection, pos, eng_spec, decisive, inv_spec,
            pkg_records))

    # ---- the three distinct completion states (never collapsed) ------
    pipeline_completed = bool(
        final_state.get("final_status") is not None
        or (run_result or {}).get("final_status") is not None)
    # DISCOVERY_COMPLETED: an authoritative admissible ranked survivor
    # exists (the selection record's own admission decision).
    discovery_completed = len(results) >= 1
    # TECHNOLOGY_PACKAGE_COMPLETED: EVERY displayed admissible survivor
    # has its own complete candidate-bound package. One package for the
    # selected #1 does NOT complete the whole ranked set.
    n_complete_pkgs = sum(
        1 for r in results if r["components"]["package"].get("complete"))
    package_completed = bool(results) and (n_complete_pkgs == len(results))

    finished = discovery_completed and package_completed

    return {
        "schema": RANKED_RESULT_SCHEMA,
        "run_id": final_state.get("run_id")
                  or (run_result or {}).get("run_id") or "",
        "final_status": final_state.get("final_status"),
        "ranked_results": results,
        "selected_candidate": selected,
        "n_admissible": len(results),
        "n_complete_packages": n_complete_pkgs,
        "n_killed": len([r for r in ranked if r.get("killed")]),
        "n_ranked": len(ranked),
        "completion": {
            COMP_PIPELINE: pipeline_completed,
            COMP_DISCOVERY: discovery_completed,
            COMP_PACKAGE: package_completed,
            "FINISHED_DISCOVERY": finished,
            "invariant": ("FINISHED_DISCOVERY = every displayed "
                          "admissible ranked survivor has its own "
                          "complete result record AND its own complete "
                          "candidate-bound technology package; never "
                          "EXECUTION_COMPLETED or "
                          "SOME_COMPONENTS_PRODUCED alone, and never "
                          "one package for the selected #1 standing in "
                          "for the ranked set"),
        },
        "diagnostic_only": (not discovery_completed
                            and pipeline_completed),
    }


def verify_ranked_result_set(record: Dict[str, Any],
                             run_dir: Path) -> Dict[str, Any]:
    """R541: the mechanical finished-discovery invariant, re-verified
    against the run directory's own artifacts (Art. III: the verifier
    never trusts the claimant — the recorded ZIP hash is re-measured
    from the on-disk bytes; the candidate binding is re-checked).

    Returns {verified, violations[], per_candidate[{candidate_id,
    rank, package_complete, zip_sha256_matches, candidate_binding_ok}]}.
    A verification failure is a typed list of violations, never a silent
    pass (the contract's invariants are mechanically enforced)."""
    run_dir = Path(run_dir)
    violations: List[str] = []
    per: List[Dict[str, Any]] = []
    for rr in record.get("ranked_results", []) or []:
        cid = rr.get("candidate_id")
        rank = rr.get("rank")
        pkg = rr.get("components", {}).get("package") or {}
        complete = bool(pkg.get("complete"))
        zip_sha = pkg.get("zip_sha256")
        zip_name = pkg.get("zip_name")
        # the candidate binding: the package's candidate_id must equal
        # the ranked row's candidate_id (no cross-candidate package)
        pkg_cid = pkg.get("candidate_id")
        binding_ok = (pkg_cid is None) or (pkg_cid == cid) or (
            pkg.get("kind") in ("ABSENT_KILLED", "ABSENT_NOT_COMPILED"))
        # re-measure the ZIP hash from disk when a zip is recorded
        measured = None
        if complete and zip_name:
            measured = _sha256_file(run_dir / zip_name)
        hash_ok = (not complete) or (zip_sha is not None
                                     and measured == zip_sha)
        per.append({
            "candidate_id": cid,
            "rank": rank,
            "package_complete": complete,
            "zip_sha256": zip_sha,
            "zip_sha256_measured": measured,
            "zip_sha256_matches": bool(hash_ok),
            "candidate_binding_ok": bool(binding_ok),
        })
        if not binding_ok:
            violations.append(
                f"candidate {cid} rank {rank}: the package's recorded "
                f"candidate_id ({pkg_cid}) does not equal the ranked "
                "row's candidate_id — cross-candidate package binding")
        if complete and not hash_ok:
            violations.append(
                f"candidate {cid} rank {rank}: recorded ZIP SHA-256 "
                f"({zip_sha}) does not match the on-disk bytes "
                f"(measured {measured}) — the package artifact is not "
                "the one the result record claims")
    # FINISHED_DISCOVERY is true only when every admissible survivor has
    # a complete, candidate-bound, hash-verified package (the contract
    # invariant, never a single-#1 completion)
    completion = record.get("completion") or {}
    n_adm = record.get("n_admissible") or 0
    n_pk = record.get("n_complete_packages") or 0
    finished_ok = (n_adm >= 1 and n_pk == n_adm
                   and not violations
                   and completion.get("FINISHED_DISCOVERY"))
    return {
        "verified": bool(finished_ok and not record.get(
            "diagnostic_only", False)),
        "diagnostic_only": bool(record.get("diagnostic_only", False)),
        "violations": violations,
        "per_candidate": per,
        "invariant": ("FINISHED_DISCOVERY = every displayed admissible "
                      "ranked survivor -> its own complete result record "
                      "-> its own complete candidate-bound technology "
                      "package (re-verified against the on-disk ZIP)"),
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
            "n_complete_packages": 0,
            "n_ranked": 0,
            "completion": {
                COMP_PIPELINE: False,
                COMP_DISCOVERY: False,
                COMP_PACKAGE: False,
                "FINISHED_DISCOVERY": False,
                "invariant": "derivation failed; no finished discovery "
                             "claimed",
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
