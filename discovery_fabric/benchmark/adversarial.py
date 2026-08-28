"""Phase 14 — adversarial benchmark suite (Coder 2).

Every control must survive an attempted bypass (Constitution Art. VIII /
XVII / XXX). This module implements the CEO-mandated attack classes as
deterministic mutations applied to COPIES of a generated run (Art. IX:
never mutate the audited original):

    REMOVE_DESIGN_INPUT          remove a design input from the eng spec
    REMOVE_FAILURE_MODE          remove a failure mode row
    REPLACE_EQUATION             swap an equation's domain to an unrelated
                                 one (wrong-domain applicability)
    INJECT_UNSUPPORTED_NUMBER    add a critical parameter with an
                                 unsourced fabricated value
    INJECT_FAKE_SOURCE           reference an evidence id that does not
                                 exist in the run
    COPY_MECHANISM               write another package's mechanism text
                                 into this run's invention specification
    LABEL_PROPOSED_AS_COMPLETED  set a verification result to PASS
    DELETE_UNKNOWNS              replace UNKNOWN values with fabricated
                                 definite numbers
    PROMOTE_MODELLED_TO_FACT     re-class a MODELLED design input as
                                 SOURCE_FACT with a source that does not
                                 contain it
    TRANSFER_READY_COLLAPSE      set transfer_ready TRUE without evidence
    REMOVE_TRANSFER_BOUNDARY     empty the structured transfer boundary
                                 and strip the PDF-side block marker

Each attack is caught by a DIFFERENT Coder 2 control; the expected
detector is recorded per attack.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Callable, Dict, Optional

EXPECTED_DETECTORS = {
    "REMOVE_DESIGN_INPUT": "ARTIFACT_CONSISTENCY",
    "REMOVE_FAILURE_MODE": "ARTIFACT_CONSISTENCY",
    "REPLACE_EQUATION": "EQUATION_APPLICABILITY",
    "INJECT_UNSUPPORTED_NUMBER": "NUMERICAL_PROVENANCE_GATE",
    "INJECT_FAKE_SOURCE": "INDEPENDENT_REPLAY",
    "COPY_MECHANISM": "CONTAMINATION",
    "LABEL_PROPOSED_AS_COMPLETED": "VV_SEPARATION",
    "DELETE_UNKNOWNS": "NUMERICAL_PROVENANCE_GATE",
    "PROMOTE_MODELLED_TO_FACT": "NUMERICAL_PROVENANCE_GATE",
    "TRANSFER_READY_COLLAPSE": "TRANSFER_SPECIFICITY",
    "REMOVE_TRANSFER_BOUNDARY": "TRANSFER_SPECIFICITY",
}


def _load(p: Path) -> Dict[str, Any]:
    return json.loads(p.read_text(encoding="utf-8"))


def _save(p: Path, data: Dict[str, Any]) -> None:
    p.write_text(json.dumps(data, indent=1, ensure_ascii=False),
                 encoding="utf-8")


def _eng(run: Path) -> Dict[str, Any]:
    return _load(run / "ENGINEERING_SPECIFICATION.json")


def _save_eng(run: Path, eng: Dict[str, Any]) -> None:
    _save(run / "ENGINEERING_SPECIFICATION.json", eng)


def mutate_remove_design_input(run: Path) -> str:
    eng = _eng(run)
    dis = eng.get("design_inputs") or []
    if not dis:
        raise ValueError("no design inputs to remove")
    removed = dis.pop(0)
    # remove its traceability chain too — a forger would scrub the record;
    # the maturity COUNT still disagrees, which is what gets caught
    tr_path = _find_package_file(run, "ENGINEERING_TRACEABILITY.json")
    if tr_path:
        tr = _load(tr_path)
        tr["traceability_chains"] = [
            c for c in (tr.get("traceability_chains") or [])
            if not (isinstance(c, dict) and
                    c.get("node_id") == removed.get("id"))]
        _save(tr_path, tr)
    _save_eng(run, eng)
    return f"removed {removed.get('id')}"


def mutate_remove_failure_mode(run: Path) -> str:
    eng = _eng(run)
    fms = eng.get("failure_analysis") or []
    if not fms:
        raise ValueError("no failure modes to remove")
    removed = fms.pop(0)
    tr_path = _find_package_file(run, "ENGINEERING_TRACEABILITY.json")
    if tr_path:
        tr = _load(tr_path)
        tr["traceability_chains"] = [
            c for c in (tr.get("traceability_chains") or [])
            if not (isinstance(c, dict) and
                    c.get("node_id") == removed.get("graph_id"))]
        _save(tr_path, tr)
    _save_eng(run, eng)
    return f"removed {removed.get('graph_id')}"


def mutate_replace_equation(run: Path) -> str:
    eng = _eng(run)
    eqs = ((eng.get("engineering_core") or {}).get("governing_model")
           or {}).get("equations") or []
    if not eqs:
        raise ValueError("no equations to replace")
    eq = eqs[0]
    eq["judged_for_domain"] = "unrelated_domain_for_attack"
    eq["applicability"] = dict(eq.get("applicability") or {})
    eq["applicability"]["judged_for_domain"] = "unrelated_domain_for_attack"
    _save_eng(run, eng)
    return f"re-pointed {eq.get('equation_id')} to unrelated domain"


def mutate_inject_unsupported_number(run: Path) -> str:
    eng = _eng(run)
    cps = (eng.get("engineering_core") or {}).setdefault(
        "critical_parameters", [])
    cps.append({
        "parameter": "attack fabricated efficiency",
        "name": "attack fabricated efficiency",
        "value": "0.87",
        "unit": "ratio",
        "basis": "SOURCE_FACT (attack injection)",
        "source_id": "problem.json",
        "verification_requirement": "none (attack)",
    })
    _save_eng(run, eng)
    return "injected fabricated 0.87 efficiency as SOURCE_FACT"


def mutate_inject_fake_source(run: Path) -> str:
    eng = _eng(run)
    dis = eng.get("design_inputs") or []
    if not dis:
        raise ValueError("no design inputs")
    dis[0]["evidence_refs"] = ["evidence:FAKE-ATTACK-000"]
    dis[0]["evidence_class"] = "SOURCE_FACT"
    # rebind the traceability chain to the fake evidence id
    tr_path = _find_package_file(run, "ENGINEERING_TRACEABILITY.json")
    if tr_path:
        tr = _load(tr_path)
        for c in (tr.get("traceability_chains") or []):
            if isinstance(c, dict) and c.get("node_id") == dis[0].get("id"):
                c["evidence_ids"] = ["evidence:FAKE-ATTACK-000"]
        _save(tr_path, tr)
    _save_eng(run, eng)
    return "referenced nonexistent evidence id"


def mutate_label_proposed_as_completed(run: Path) -> str:
    eng = _eng(run)
    vfs = eng.get("verification_matrix") or []
    if not vfs:
        raise ValueError("no verification rows")
    vfs[0]["result"] = "PASS"
    _save_eng(run, eng)
    return "set verification result to PASS without a test"


def mutate_delete_unknowns(run: Path) -> str:
    eng = _eng(run)
    ec = eng.get("engineering_core") or {}
    for cp in (ec.get("critical_parameters") or []):
        if isinstance(cp, dict) and "UNKNOWN" in str(cp.get("value", "")):
            cp["value"] = "42"
            cp["unit"] = "SI"
            cp["basis"] = "SOURCE_FACT (attack)"
            cp["source_id"] = "problem.json"
    ec["remaining_unknowns"] = []
    _save_eng(run, eng)
    return "replaced UNKNOWNs with fabricated definite values"


def mutate_promote_modelled_to_fact(run: Path) -> str:
    eng = _eng(run)
    dis = eng.get("design_inputs") or []
    target = None
    for d in dis:
        if isinstance(d, dict) and d.get("evidence_class") == "MODELLED":
            target = d
            break
    if target is None:
        if dis:
            target = dis[-1]
        else:
            raise ValueError("no design inputs")
    target["evidence_class"] = "SOURCE_FACT"
    target["evidence_refs"] = ["problem.json"]
    _save_eng(run, eng)
    return f"promoted {target.get('id')} MODELLED -> SOURCE_FACT"


def mutate_transfer_ready_collapse(run: Path) -> str:
    pm_path = _find_package_file(run, "PACKAGE_MANIFEST.json")
    if pm_path:
        pm = _load(pm_path)
        pm["transfer_ready"] = True
        pm["loop_verification_state"] = "NONE"
        pm["real_loop_verified"] = False
        _save(pm_path, pm)
    return "collapsed transfer_ready to TRUE without evidence"


def mutate_remove_transfer_boundary(run: Path) -> str:
    eng = _eng(run)
    eng["transfer_boundary"] = {"buyer_receives": [],
                                "buyer_must_create": []}
    _save_eng(run, eng)
    return "emptied the structured transfer boundary"


MUTATIONS: Dict[str, Callable[[Path], str]] = {
    "REMOVE_DESIGN_INPUT": mutate_remove_design_input,
    "REMOVE_FAILURE_MODE": mutate_remove_failure_mode,
    "REPLACE_EQUATION": mutate_replace_equation,
    "INJECT_UNSUPPORTED_NUMBER": mutate_inject_unsupported_number,
    "INJECT_FAKE_SOURCE": mutate_inject_fake_source,
    "COPY_MECHANISM": None,  # handled at batch level (needs two runs)
    "LABEL_PROPOSED_AS_COMPLETED": mutate_label_proposed_as_completed,
    "DELETE_UNKNOWNS": mutate_delete_unknowns,
    "PROMOTE_MODELLED_TO_FACT": mutate_promote_modelled_to_fact,
    "TRANSFER_READY_COLLAPSE": mutate_transfer_ready_collapse,
    "REMOVE_TRANSFER_BOUNDARY": mutate_remove_transfer_boundary,
}


def apply_mutation(base_run: Path, attack: str, dest: Path) -> str:
    """Copy base_run to dest and apply the attack. Returns what changed."""
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(base_run, dest)
    _rebind_release_paths(base_run, dest)
    fn = MUTATIONS.get(attack)
    if fn is None:
        raise ValueError(f"attack {attack} is batch-level or unknown")
    return fn(dest)


def _rebind_release_paths(base_run: Path, dest: Path) -> None:
    """Point the copied DISCOVERY_RELEASE.json at the COPY's package paths.

    The release records absolute paths into the original run; without
    rebinding, audits on the copy would read the ORIGINAL package and
    package-side mutations would be invisible (a real audit hole, caught
    by the adversarial suite itself).
    """
    rel_path = dest / "DISCOVERY_RELEASE.json"
    if not rel_path.exists():
        return
    rel = json.loads(rel_path.read_text(encoding="utf-8"))
    changed = False
    for key in ("package_folder", "package_zip"):
        val = rel.get(key)
        if isinstance(val, str) and val.startswith(str(base_run)):
            rel[key] = str(dest) + val[len(str(base_run)):]
            changed = True
    if changed:
        rel_path.write_text(json.dumps(rel, indent=1, ensure_ascii=False),
                            encoding="utf-8")


def apply_copy_mechanism(source_run: Path, target_run: Path,
                         dest: Path) -> str:
    """COPY_MECHANISM attack: put source run's mechanism text into target
    run's invention specification (batch-level, caught by contamination)."""
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(target_run, dest)
    _rebind_release_paths(target_run, dest)
    src_inv = _load(source_run / "INVENTION_SPECIFICATION.json")
    src_mechanism = ((src_inv.get("mechanism") or {}).get("value") or {})
    if isinstance(src_mechanism, dict):
        src_text = src_mechanism.get("mechanism", "")
    else:
        src_text = str(src_mechanism)
    inv = _load(dest / "INVENTION_SPECIFICATION.json")
    mech = inv.setdefault("mechanism", {})
    if isinstance(mech.get("value"), dict):
        mech["value"]["mechanism"] = src_text
    else:
        mech["value"] = src_text
    _save(dest / "INVENTION_SPECIFICATION.json", inv)
    return f"copied mechanism from {source_run.name} into {dest.name}"


def _find_package_file(run: Path, name: str) -> Optional[Path]:
    for candidate in (run / "DOWNLOAD", ):
        if candidate.is_dir():
            for sub in candidate.iterdir():
                if sub.is_dir() and (sub / name).exists():
                    return sub / name
    return None
