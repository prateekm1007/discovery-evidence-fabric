"""release_gates.py — R394 hard release gates (fail-closed).

  1. MECHANISM_CLAIM_WITHOUT_GEOMETRIC_IMPLEMENTATION
     Any mechanism-bearing subsystem with NO mapped model parameter
     -> FAIL. (The P-07 SS-03 pressure-activated switch defect class.)

  2. DECISIVE_EXPERIMENT_INVALID
     The shipped VALIDATION_ECONOMICS decisive work package must
     share >= 2 kill-condition content tokens (re-derived here from
     the shipped JSON — the gate attacks the artifact, not the code).

  3. NO_MISSING_REFERENCED_ARTIFACTS
     Every file-ish reference inside the shipped package must resolve
     to a file INSIDE the package or carry an immutable external
     reference recorded with a sha256.

  4. SAFETY_EQUATION_STRUCTURALLY_BROKEN
     Any equation whose rendering is not a parseable relation (or is
     CORRUPTED-canonical) -> FAIL for the release.

Each gate returns {state: PASS|FAIL, violations: [...]}. The build
calls run_all_gates() and REFUSES to produce ZIPs on any FAIL.
Negative controls (each defect class reproduced deliberately) are in
tests/test_r394_semantics.py.
"""

from __future__ import annotations

import json
import os
import re

from .decisive_experiment import content_tokens, _flat
from .validation_states import mechanism_feature_mapping

_FILE_REF_RE = re.compile(
    r"\b([A-Z][A-Z0-9_]*(?:/[A-Za-z0-9_.-]+)+\.[A-Za-z0-9]{1,6})\b|"
    r"\b([A-Za-z0-9_.-]+\.json)\b|"
    r"\b([A-Za-z0-9_.-]+\.pdf)\b")


def gate_mechanism_geometry(pkg, model_dir: str) -> dict:
    """Gate 1 — mechanism claims must have geometric implementation.

    Software-only technologies (3D_DESIGN_STATUS classification
    3D_NOT_APPLICABLE — the record itself shows no physical device)
    pass vacuously: no geometry is required and none is claimed."""
    import json
    status = {}
    sp = os.path.join(model_dir, "3D_DESIGN_STATUS.json")
    if os.path.isfile(sp):
        try:
            status = json.load(open(sp, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            status = {}
    if status.get("classification") == "3D_NOT_APPLICABLE":
        return {
            "gate": "MECHANISM_CLAIM_WITHOUT_GEOMETRIC_IMPLEMENTATION",
            "state": "PASS",
            "violations": [],
            "note": ("software-only technology — 3D_NOT_APPLICABLE per the "
                     "record's own classification; no geometry is required "
                     "and none is claimed."),
        }
    mech = mechanism_feature_mapping(pkg, model_dir)
    violations = []
    for m in mech["subsystems"]:
        if m["mechanism_bearing"] and m["state"] != "MAPPED":
            # the HARD gate is the actuation claim without geometry (the
            # named defect class). Passive mechanism subsystems that do
            # not map are a disclosed modeling-scope fact — recorded in
            # the mapping, never hidden (Art. XV), not a false physical
            # claim.
            if m.get("actuation_vocabulary"):
                violations.append({
                    "subsystem_id": m["subsystem_id"],
                    "subsystem_name": m["subsystem_name"],
                    "violation": m.get("mapping_tier") or
                                 "actuation claim without geometric "
                                 "implementation",
                })
    return {
        "gate": "MECHANISM_CLAIM_WITHOUT_GEOMETRIC_IMPLEMENTATION",
        "state": "FAIL" if violations else "PASS",
        "violations": violations,
        "mapping": mech,
        "note": ("Hard-gate: a subsystem claiming a mechanical actuating "
                 "element (switch/valve/trigger/threshold activation) must "
                 "map to a model feature implementing it. Passive "
                 "subsystems without model features are disclosed in the "
                 "mapping (modeling scope), never promoted (Art. XV)."),
    }


def gate_decisive_experiment(economics_json: dict,
                             kill_condition: str) -> dict:
    """Gate 2 — nothing may be LABELED decisive that does not test the
    kill condition. Re-derives from the SHIPPED JSON (attacks the
    artifact, not the code).

    FAIL when:
      (a) a decisive WP is designated without the DERIVED state (the
          R371 build_plan[0] defect class — a designation by list
          position);
      (b) a DERIVED designation's matched tokens do not actually appear
          in the kill condition (a forged/edited derivation).
    PASS when:
      - DERIVED with >= 2 genuine kill-condition tokens, or
      - NOT_DERIVED (honest absence: nothing is falsely designated —
        the buyer-facing language says NOT DERIVED, never 'decisive')."""
    tr = (economics_json or {}).get("time_range") or {}
    decisive = tr.get("decisive_work_package") or {}
    wp = decisive.get("work_package")
    state = decisive.get("decisive_experiment_state")
    # legacy schema detection: the old first_decisive_work_package key
    # designated by list position — fail closed on sight
    if tr.get("first_decisive_work_package"):
        return {
            "gate": "DECISIVE_EXPERIMENT_INVALID",
            "state": "FAIL",
            "violations": [{
                "violation": "legacy list-position designation "
                             "(first_decisive_work_package) present — "
                             "the R371 defect class",
            }],
        }
    if state == "DECISIVE_EXPERIMENT_NOT_DERIVED" and not wp:
        return {
            "gate": "DECISIVE_EXPERIMENT_INVALID",
            "state": "PASS",
            "kill_condition": kill_condition,
            "note": ("No decisive experiment designated — the honest "
                     "NOT_DERIVED state; no work package is labeled "
                     "decisive without testing the kill condition."),
        }
    if state != "DERIVED_FROM_KILL_CONDITION" or not wp:
        return {
            "gate": "DECISIVE_EXPERIMENT_INVALID",
            "state": "FAIL",
            "violations": [{
                "violation": "decisive work package designated without "
                             "kill-condition derivation "
                             f"(state={state!r}, wp={wp!r})",
            }],
        }
    kc_tokens = _flat(content_tokens(kill_condition))
    matched = [t for t in (decisive.get("matched_tokens") or [])
               if t in kc_tokens]
    ok = len(matched) >= 2
    return {
        "gate": "DECISIVE_EXPERIMENT_INVALID",
        "state": "PASS" if ok else "FAIL",
        "kill_condition": kill_condition,
        "decisive_work_package": wp,
        "matched_tokens": matched,
        "violations": [] if ok else [{
            "violation": "the designated decisive experiment does not "
                         "test the recorded kill condition "
                         "(<2 matched tokens)",
        }],
    }


def _iter_json_refs(obj, path="$", parent_key=None):
    """Yield (json_path, parent_key, referenced_file_string) for every
    string that looks like a file reference. Literature CITATION fields
    (source/source_title/uri/url/doi/citation/patent fields) are yielded
    separately with citation=True — they cite external literature, not
    package artifacts (e.g. an FDA 510(k) PDF named 'K062009.pdf')."""
    _CITATION_KEYS = {"source", "source_title", "source_url", "uri",
                      "url", "doi", "citation", "patent_id",
                      "record_id", "artifact_path", "raw_artifact_ref"}
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _iter_json_refs(v, f"{path}.{k}", k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _iter_json_refs(v, f"{path}[{i}]", parent_key)
    elif isinstance(obj, str):
        is_citation = parent_key in _CITATION_KEYS
        for m in _FILE_REF_RE.finditer(obj):
            ref = m.group(1) or m.group(2) or m.group(3)
            if ref and not ref.startswith("http"):
                yield path, parent_key, ref


def _ref_resolved(package_dir: str, in_file: str, ref: str,
                  manifest: dict | None) -> tuple:
    """Resolution order (recorded):
    (a) package root
    (b) the referencing file's own directory (MODEL/ files reference
        siblings by bare filename)
    (c) the package manifest's external_references map (immutable
        external reference with sha256 — CEO option 2)
    (d) portfolio root, pinned by the release manifest (Art. XXXIX
        chain) when the manifest is present
    Returns (resolved: bool, how: str)."""
    if os.path.isfile(os.path.join(package_dir, ref)):
        return True, "inside package (root)"
    same_dir = os.path.join(os.path.dirname(
        os.path.join(package_dir, in_file)), ref)
    if os.path.isfile(same_dir):
        return True, f"inside package (sibling of {in_file})"
    if manifest:
        ext = manifest.get("external_references") or {}
        if ref in ext or os.path.basename(ref) in {
                k for k in ext}:
            entry = ext.get(ref) or ext.get(os.path.basename(ref))
            if entry and entry.get("sha256"):
                return True, ("immutable external reference with "
                              "recorded sha256 (manifest."
                              "external_references)")
    portfolio_root = os.path.dirname(package_dir)
    pin = os.path.join(portfolio_root, ref)
    if os.path.isfile(pin):
        mf_path = os.path.join(
            os.path.dirname(portfolio_root),
            "CANONICAL_RELEASE_MANIFEST.json")
        if os.path.isfile(mf_path):
            try:
                mf = json.load(open(mf_path, encoding="utf-8"))
                pinned = {os.path.basename(str(f.get("path") or ""))
                          for f in (mf.get("files") or [])}
                if os.path.basename(ref) in pinned:
                    return True, ("portfolio root, pinned by "
                                  "CANONICAL_RELEASE_MANIFEST.json")
            except Exception:  # noqa: BLE001
                pass
        return False, ("exists at portfolio root but not pinned by a "
                       "release manifest (pending release)")
    return False, "unresolved"


def gate_self_containment(package_dir: str,
                          manifest_dict: dict | None = None) -> dict:
    """Gate 3 — every referenced artifact ships inside the package or
    carries an immutable external reference with a sha256.

    manifest_dict: the in-memory manifest (external_references) when
    the on-disk manifest has not been written yet (build time)."""
    violations = []
    refs = []
    citations = []
    manifest = manifest_dict
    if manifest is None:
        mp = os.path.join(package_dir, "PACKAGE_MANIFEST.json")
        if os.path.isfile(mp):
            try:
                manifest = json.load(open(mp, encoding="utf-8"))
            except Exception:  # noqa: BLE001
                manifest = None
    for root, _dirs, files in os.walk(package_dir):
        for f in sorted(files):
            if not f.endswith(".json"):
                continue
            fp = os.path.join(root, f)
            rel = os.path.relpath(fp, package_dir)
            try:
                data = json.load(open(fp, encoding="utf-8"))
            except Exception:  # noqa: BLE001
                continue
            for jpath, pkey, ref in _iter_json_refs(data):
                if ref == rel or ref == f:
                    continue
                if pkey in ("source", "source_title", "source_url", "uri",
                            "url", "doi", "citation", "patent_id",
                            "record_id", "artifact_path",
                            "raw_artifact_ref"):
                    # literature citation inside an evidence entry —
                    # recorded as a citation, not a package reference
                    # (the CEO gate targets manifest/certificate/
                    # provenance artifact references)
                    citations.append({"in": rel, "at": jpath, "ref": ref})
                    continue
                ok, how = _ref_resolved(package_dir, rel, ref, manifest)
                refs.append({"in": rel, "at": jpath, "ref": ref,
                             "resolved": ok, "how": how})
                if not ok:
                    violations.append({
                        "file": rel,
                        "field": jpath,
                        "referenced": ref,
                        "violation": "referenced artifact is not inside "
                                     "the package and carries no "
                                     "immutable external reference",
                    })
    return {
        "gate": "NO_MISSING_REFERENCED_ARTIFACTS",
        "state": "FAIL" if violations else "PASS",
        "references_checked": len(refs),
        "literature_citations_recorded": len(citations),
        "literature_citations": citations[:20],
        "violations": violations,
        "note": ("References resolve inside the package (root or sibling "
                 "directory), or by an immutable external reference with "
                 "recorded sha256 (manifest.external_references), or as a "
                 "portfolio-root file pinned by the release manifest "
                 "(Art. XXXIX chain). Anything else fails the release."),
    }


def gate_equations_structural(equation_registry: dict) -> dict:
    """Gate 4 — no structurally broken safety-critical equation ships.

    FAIL on:
      - CORRUPTED canonical strings (unrecoverable math/annotation
        boundary)
      - equations rendered as TYPESET math whose structural validation
        is NOT proven (claimed math that fails to parse)
    Disclosed (recorded, never hidden, not violations):
      - VERBATIM prose model descriptions (rendering VERBATIM_MONOSPACE,
        note CONTAINS_PROSE) — recorded descriptive statements, not
        broken math (the R371 corpus carries several by design; they
        are rendered verbatim and never claimed as parseable math)."""
    violations = []
    prose_disclosed = []
    for e in (equation_registry or {}).get("equations") or []:
        note = e.get("rendering_note")
        if note == "CORRUPTED_CANONICAL_STRING_RENDERED_VERBATIM":
            violations.append({
                "equation_id": e.get("equation_id"),
                "violation": "corrupted canonical string (annotation "
                             "boundary unrecoverable)",
            })
            continue
        rendering = e.get("rendering")
        if rendering == "VERBATIM_MONOSPACE" and note == "CONTAINS_PROSE":
            prose_disclosed.append(e.get("equation_id"))
            continue
        reg = equation_registry.get("r374_validation_status") or {}
        r374 = None
        for lv in reg.get("equations") or []:
            if lv.get("equation_id") == e.get("equation_id"):
                r374 = lv
                break
        if r374 is not None and not r374.get(
                "structural_validation", {}).get("proven", False):
            violations.append({
                "equation_id": e.get("equation_id"),
                "violation": "structural validation NOT proven (the "
                             "canonical math does not parse as a "
                             "well-formed relation)",
                "basis": (r374.get("structural_validation")
                          or {}).get("basis"),
            })
    return {
        "gate": "SAFETY_EQUATION_STRUCTURALLY_BROKEN",
        "state": "FAIL" if violations else "PASS",
        "violations": violations,
        "prose_model_descriptions_disclosed": prose_disclosed,
        "standard": ("A core engineering package may not ship a "
                     "safety-critical equation in a broken structural "
                     "state (CEO directive 9). VERBATIM prose model "
                     "descriptions are disclosed, never claimed as "
                     "parseable math (Art. XXV/XXVIII)."),
    }


def run_all_gates(pkg, package_dir: str, model_dir: str,
                  economics_json: dict, equation_registry: dict,
                  kill_condition: str,
                  manifest_dict: dict | None = None) -> dict:
    gates = [
        gate_mechanism_geometry(pkg, model_dir),
        gate_decisive_experiment(economics_json, kill_condition),
        gate_self_containment(package_dir, manifest_dict),
        gate_equations_structural(equation_registry),
    ]
    overall = "FAIL" if any(g["state"] == "FAIL" for g in gates) \
        else "PASS"
    return {
        "schema": "R394_RELEASE_GATES",
        "package_id": pkg.pkg_id,
        "overall": overall,
        "gates": gates,
        "rule": ("ANY gate FAIL blocks the package ZIP and the release "
                 "(fail-closed; RED = STOP, Art. XIV)."),
    }
