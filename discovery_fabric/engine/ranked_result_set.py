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
            return json.loads(path.read_text(encoding="utf-8"))
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


def _locate_zip(run_dir: Path, zip_name: Optional[str]) -> Optional[Path]:
    """The candidate-bound ZIP on disk (the DOWNLOAD tree first, then
    the run root — the two legal locations the binding resolves)."""
    if not zip_name:
        return None
    for cand in (run_dir / "DOWNLOAD" / zip_name, run_dir / zip_name):
        try:
            if cand.exists():
                return cand
        except Exception:  # noqa: BLE001 — absent stays absent
            continue
    return None


# the six-part discovery record as machine files inside a
# candidate-bound package (the current compiler layout; the
# TECHNOLOGY_PACKAGE/ prefix is optional — matched by suffix).
_CONTENT_FILES = {
    "manifest": ("PACKAGE_MANIFEST.json",),
    "model": ("TECHNOLOGY_PACKAGE_MODEL.json",),
    "evidence": ("03_EVIDENCE_SUMMARY.json",),
    "engineering": ("02_ENGINEERING_DEFINITION.json",),
    "experiment": ("04_DECISIVE_EXPERIMENT.json",),
    "provenance": ("PROVENANCE.json",),
    "model_manifest": ("MODEL/MODEL_MANIFEST.json",),
    "parameters": ("MODEL/PARAMETERS.json",),
}


def verify_package_contents(
        zip_path: Path,
        candidate_id: Optional[str],
        package_id: Optional[str],
        invention_id: Optional[str],
        disposition: Optional[str],
) -> Dict[str, Any]:
    """R544: open the ACTUAL ZIP bytes and mechanically check the
    six-part discovery record is inside — for THIS candidate.

    Proves (not claims): the manifest exists; the model identity names
    this package_id + invention_id + ranked candidate_id; the recorded
    adversarial disposition equals the row's disposition; evidence
    records exist; mechanism + kill condition are stated; the
    engineering definition exists; the MODEL layer carries a model_id
    + at least one GLB; parameters exist; the decisive experiment
    carries hypothesis arms + a decision rule.

    Never trusts a record field: every check reads the ZIP bytes.
    Returns {ok, checks{}, missing[], identity{}}. A missing part is
    named exactly (never a silent pass)."""
    import zipfile as _zf
    checks: Dict[str, bool] = {}
    missing: List[str] = []
    identity: Dict[str, Any] = {}

    def _need(name: str, good: bool, why: str) -> None:
        checks[name] = bool(good)
        if not good:
            missing.append(f"{name}: {why}")

    try:
        zf = _zf.ZipFile(str(zip_path))
        names = zf.namelist()
    except Exception as exc:  # noqa: BLE001 — unreadable bytes fail
        return {"ok": False, "checks": {"readable_zip": False},
                "missing": [f"readable_zip: {type(exc).__name__}"],
                "identity": {}}
    checks["readable_zip"] = True

    def _find(*suffixes: str) -> Optional[str]:
        for want in suffixes:
            for n in names:
                if n == want or n.endswith("/" + want):
                    return n
        return None

    def _load(name: Optional[str]) -> Optional[Dict[str, Any]]:
        if not name:
            return None
        try:
            return json.loads(zf.read(name).decode("utf-8"))
        except Exception:  # noqa: BLE001 — unparseable fails the part
            return None

    _need("manifest_present",
          _find(*_CONTENT_FILES["manifest"]) is not None,
          "PACKAGE_MANIFEST.json absent from the ZIP bytes")
    model_doc = _load(_find(*_CONTENT_FILES["model"]))
    _need("model_present", isinstance(model_doc, dict),
          "TECHNOLOGY_PACKAGE_MODEL.json absent/unparseable in the ZIP")
    ident = (model_doc or {}).get("identity") or {}
    if not isinstance(ident, dict):
        ident = {}
    identity = {k: ident.get(k) for k in (
        "package_id", "invention_id", "ranked_candidate_id",
        "ranked_disposition")}
    _need("identity_package_id",
          bool(package_id) and ident.get("package_id") == package_id,
          f"model identity package_id {ident.get('package_id')!r} != "
          f"package record {package_id!r}")
    _need("identity_invention_id",
          bool(invention_id) and ident.get("invention_id") == invention_id,
          "model identity invention_id != the candidate's specification "
          "invention_id")
    _need("identity_candidate_id",
          bool(candidate_id) and ident.get("ranked_candidate_id")
          == candidate_id,
          f"model identity ranked_candidate_id "
          f"{ident.get('ranked_candidate_id')!r} != ranked row "
          f"{candidate_id!r}")
    _need("identity_disposition",
          bool(disposition) and ident.get("ranked_disposition")
          == disposition,
          f"model identity ranked_disposition "
          f"{ident.get('ranked_disposition')!r} != recorded row "
          f"disposition {disposition!r}")

    ev_doc = _load(_find(*_CONTENT_FILES["evidence"]))
    _ev_ok = False
    if isinstance(ev_doc, dict):
        try:
            total = sum(int(r.get("count") or 0)
                        for r in (ev_doc.get("roles") or [])
                        if isinstance(r, dict))
        except Exception:  # noqa: BLE001 — malformed roles fail
            total = 0
        _ev_ok = total > 0
    _need("evidence_records", _ev_ok,
          "03_EVIDENCE_SUMMARY.json absent or carries zero records")

    _chain = ((model_doc or {}).get("causal_mechanism") or {}).get(
        "chain") or {}
    if not isinstance(_chain, dict):
        _chain = {}
    _need("mechanism_stated",
          bool(str(_chain.get("mechanism") or "").strip()),
          "causal_mechanism.chain.mechanism empty in the ZIP model")
    _need("kill_condition_stated",
          bool(str(_chain.get("falsification_test") or "").strip()),
          "causal_mechanism.chain.falsification_test empty in the ZIP")

    _need("engineering_definition",
          _load(_find(*_CONTENT_FILES["engineering"])) is not None,
          "02_ENGINEERING_DEFINITION.json absent/unparseable in the ZIP")
    _need("provenance_record",
          _load(_find(*_CONTENT_FILES["provenance"])) is not None,
          "PROVENANCE.json absent/unparseable in the ZIP")

    mman = _load(_find(*_CONTENT_FILES["model_manifest"]))
    _glbs = [n for n in names
             if n.lower().endswith(".glb")
             and "MODEL/" in n.replace("\\", "/").upper()]
    _need("model_layer",
          isinstance(mman, dict) and bool(mman.get("model_id"))
          and len(_glbs) >= 1,
          "MODEL/MODEL_MANIFEST.json without model_id, or no MODEL/*.glb "
          "in the ZIP bytes")
    _need("parameters_present",
          _load(_find(*_CONTENT_FILES["parameters"])) is not None,
          "MODEL/PARAMETERS.json absent/unparseable in the ZIP")

    dec = _load(_find(*_CONTENT_FILES["experiment"]))
    _arms = 0
    _rule = False
    if isinstance(dec, dict):
        _contract = dec.get("contract") or {}
        _hyps = (_contract.get("hypothesis")
                 if isinstance(_contract, dict) else None)
        # value-wrapped synthesis output ({value: [...], status}) or a
        # plain arm list — either form counts when arms carry
        # descriptions (never a bare arm count).
        if isinstance(_hyps, dict) and "value" in _hyps:
            _hyps = _hyps.get("value")
        if not isinstance(_hyps, list):
            _hyps = []
        _arms = sum(
            1 for h in _hyps if isinstance(h, dict)
            and str(h.get("description") or "").strip())
        _blob = json.dumps(dec, default=str)
        _rule = ("decision_rule" in _blob.lower()
                 or "decision rule" in _blob.lower())
    _need("experiment_arms", _arms >= 1,
          "04_DECISIVE_EXPERIMENT.json carries no hypothesis arms")
    _need("decision_rule", bool(_rule),
          "no decision rule recorded in the packaged experiment")
    try:
        zf.close()
    except Exception:  # noqa: BLE001 — result stands regardless
        pass
    return {"ok": not missing, "checks": checks, "missing": missing,
            "identity": identity}


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
    if isinstance(mm, dict) and "value" in mm:
        mm = mm.get("value") or {}
    span = mm.get("mechanism_source_span") if isinstance(mm, dict) else None
    # R543-2: the evidence answer shape carries the ACTUAL source
    # provenance, not just a count — the recorded source identities
    # (deduped, in record order) so the conversation states where the
    # evidence came from.
    sources = sorted({str(r.get("source") or r.get("source_id")
                        or r.get("source_uri") or "")
                      for r in records if isinstance(r, dict)
                      and (r.get("source") or r.get("source_id")
                           or r.get("source_uri"))})
    return {
        "records": view,
        "sources": sources,
        "mechanism_source_span": span or "",
        "evidence_status": "verified_against_frozen_evidence"
                          if view else "NONE_REACHED_ENVELOPE",
    }


def _manifest_candidate_id(manifest: Any) -> Optional[str]:
    """R543-4: the candidate identity recorded INSIDE a package's
    manifest ( PACKAGE_MANIFEST.json / the manifest record). Any of the
    recorded identity fields count (the engine records
    candidate_id / ranked_candidate_id on both the manifest and the
    package record); a manifest that records NONE carries no candidate
    identity (an honest absence, never a silent pass)."""
    if isinstance(manifest, dict):
        cid = manifest.get("candidate_id") or \
            manifest.get("ranked_candidate_id")
        if cid is None and isinstance(manifest.get("identity"), dict):
            cid = manifest["identity"].get("candidate_id")
        if cid:
            return str(cid)
    if isinstance(manifest, (list, tuple)):
        # file-list manifest: no candidate identity is carried by the
        # file inventory itself — the package RECORD is the authority
        return None
    return None


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

    # the candidate-bound package record, when the engine compiled it.
    # Records are keyed by the candidate_id (or the ranked_candidate_key
    # when the candidate_id itself is a per-key identity); either form
    # resolves the same candidate-bound package.
    rec = (pkg_records.get("packages") or {}).get(cid) \
        or (pkg_records.get("packages") or {}).get(key) \
        or pkg_records.get("by_candidate_id", {}).get(cid) \
        or pkg_records.get("by_candidate_id", {}).get(key)
    # R543-4: a package record only PROVES the candidate binding when
    # it records the candidate identity itself. The engine's package
    # compiler sets candidate_id on every record it compiles; a record
    # that names the candidate only by its lookup key (the
    # candidate-id-keyed table form) carries no recorded identity of
    # its own — an absent recorded candidate_id on a complete package
    # is a binding FAILURE, never a silent pass.
    has_recorded_identity = isinstance(rec, dict) and \
        rec.get("candidate_id") is not None
    if not isinstance(rec, dict) or not rec.get("complete") \
            or not has_recorded_identity:
        # no complete candidate-bound package with a recorded candidate
        # identity on disk — an UNRESOLVED candidate, a not-yet-
        # compiled package, or a record that cannot prove the binding.
        # Honest absence; NEVER a borrowed #1 package and NEVER a
        # claimed TECHNOLOGY_PACKAGE (the contract's #1/#5/#6
        # invariants).
        return {
            "kind": "ABSENT_NOT_COMPILED",
            "package_id": None,
            "zip_name": None,
            "zip_sha256": None,
            "manifest": None,
            "candidate_id": rec.get("candidate_id")
            if isinstance(rec, dict) else cid,
            "rank": rank,
            "candidate_identity_bound": False,
            "complete": False,
            "note": ("no complete candidate-bound package with a "
                     "recorded candidate identity on disk for this "
                     "ranked candidate (the #1 package is NOT reused "
                     "as this candidate's package)"),
        }

    # the candidate-bound ZIP must exist on disk and its hash must match.
    # The engine promotes the candidate-bound ZIP into the run's
    # DOWNLOAD/ tree (candidate-bound by name); fall back to the run
    # root if it sits there instead.
    zip_name = rec.get("zip_name")
    zip_sha = rec.get("zip_sha256")
    zip_path = None
    if zip_name:
        for _cand in (run_dir / "DOWNLOAD" / zip_name,
                      run_dir / zip_name):
            if _cand.exists():
                zip_path = _cand
                break
    measured = _sha256_file(zip_path) if zip_path else None
    hash_matches = (zip_sha is not None) and (measured == zip_sha)
    manifest = rec.get("manifest") or rec.get("manifest_files")

    # R543-4: candidate-identity binding — a complete package PROVES
    # the binding only when the recorded identity (the package record's
    # own candidate_id, set by the engine's package compiler, plus the
    # manifest's recorded candidate identity when present) matches
    # this ranked row's candidate. A manifest that names a DIFFERENT
    # candidate is a cross-candidate package — a binding failure,
    # never a silent pass. The manifest is consulted ONLY when the
    # record itself did not already record its own candidate identity:
    # the engine writes the manifest's candidate_id FROM the record, so
    # when both are recorded and agree, the record is the authority;
    # when only the manifest records an identity (the record is
    # identity-less), a mismatched manifest is a cross-candidate
    # package.
    rec_cid = rec.get("candidate_id")
    manifest_cid = _manifest_candidate_id(manifest)
    if rec_cid is not None:
        # the record records its own identity: it must equal the row.
        identity_bound = (str(rec_cid) == str(cid)
                          and (manifest_cid is None
                               or manifest_cid == str(cid)))
    else:
        # the record is identity-less: the manifest is the only
        # candidate-identity evidence; a mismatched manifest (naming a
        # different candidate) is a cross-candidate package, and an
        # identity-less manifest cannot PROVE the binding either.
        identity_bound = (manifest_cid is not None
                          and manifest_cid == str(cid))

    return {
        "kind": "TECHNOLOGY_PACKAGE",
        "package_id": rec.get("package_id") or str(cid),
        "zip_name": zip_name,
        "zip_sha256": zip_sha,
        "zip_sha256_measured": measured,
        "zip_sha256_matches": bool(hash_matches),
        "manifest": manifest,
        "manifest_candidate_id": manifest_cid,
        "candidate_id": rec_cid if rec_cid is not None else cid,
        "rank": rank,
        "candidate_identity_bound": bool(identity_bound),
        # R544: the independent package-quality gate posture, recorded
        # by the engine at compile time on the package record (the
        # gate runs on the promoted ZIP bytes — the same gate the
        # bridge release path runs). COMPLETE_CANDIDATE_PACKAGE
        # (compiled + bound + hash-verified) is NOT the same claim as
        # a quality-verified package; the completion contract
        # requires quality_verified == PASS, and the UI surfaces the
        # posture distinctly (a candidate package is never presented
        # as a buyer release unless the gate passed).
        "quality_verified": rec.get("quality_verified"),
        "quality_failed_gates": list(rec.get("quality_failed_gates")
                                     or []),
        "quality_gate_error": rec.get("quality_gate_error"),
        "complete": bool(rec.get("complete") and hash_matches
                         and identity_bound),
        "note": ("candidate-bound technology package; the ZIP hash is "
                 "re-measured from the on-disk artifact and the "
                 "recorded candidate identity is re-checked against "
                 "the ranked row (Art. II/III/X: the measured bytes + "
                 "recorded candidate identity are the authority)"),
    }


def _pkg_rec(pkg_records: Dict[str, Any],
             cid: Optional[str], key: str) -> Dict[str, Any]:
    """The candidate's own package record (RANKED_PACKAGE_RECORDS),
    resolving either keying form — candidate_id or ranked key."""
    pkgs = (pkg_records or {}).get("packages") or {}
    by_cid = (pkg_records or {}).get("by_candidate_id") or {}
    return pkgs.get(cid) or pkgs.get(key) or by_cid.get(cid) \
        or by_cid.get(key) or {}


def resolve_model_class(run_dir: Path, key: Optional[str],
                        eng: Dict[str, Any],
                        pkg_rec: Optional[Dict[str, Any]]
                        ) -> Dict[str, Any]:
    """R542: the ONE honest model-class resolution chain (Art. XXVIII).

    A model class is either EARNED (the run's own geometry record:
    ENGINEERING_SPECIFICATION.geometry or the canonical GEOMETRY_OUT)
    or an EXPLICIT recorded classification (the spec's visualizability
    class, else the package compiler's classification of this
    candidate's model) or ABSENT (None — never a vague 'see package'
    placeholder, which is not a model artifact). Shared by the ranked
    projection and the completion contract (one authority)."""
    geo = eng.get("geometry") if isinstance(eng, dict) else None
    if isinstance(geo, dict) and (geo.get("class")
                                  or geo.get("glb_sha256")):
        return {"model_class": geo.get("class") or "ENGINEERING_3D",
                "source": "ENGINEERING_SPECIFICATION.geometry",
                "earned_geometry": True}
    if key in (None, "primary"):
        gout = _read_json(Path(run_dir) / "GEOMETRY_OUT.json")
        if isinstance(gout, dict) and (gout.get("glb_sha256")
                                       or gout.get("glb_bytes")):
            return {"model_class": gout.get("visualizability_class")
                    or "ENGINEERING_3D",
                    "source": "GEOMETRY_OUT.json",
                    "earned_geometry": True}
    vis = eng.get("visualizability_class") if isinstance(eng, dict) \
        else None
    if isinstance(vis, str) and vis:
        return {"model_class": vis,
                "source": "ENGINEERING_SPECIFICATION.visualizability_class",
                "earned_geometry": vis.startswith(("ENGINEERING", "CAD"))}
    if isinstance(pkg_rec, dict) and pkg_rec.get("visualizability_class"):
        vc = str(pkg_rec["visualizability_class"])
        return {"model_class": vc,
                "source": "RANKED_PACKAGE_RECORDS.json",
                "earned_geometry": vc.startswith(("ENGINEERING", "CAD"))}
    return {"model_class": None, "source": None, "earned_geometry": False}


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

    # per-candidate canonical trio (R541; R543-3 strictened): a
    # NON-PRIMARY candidate resolves ONLY its OWN suffixed artifacts.
    # Missing suffixed artifact = a typed component gap on THIS
    # candidate (it drives the completion contract's missing
    # components and blocks FINISHED_DISCOVERY) — it is NEVER
    # substituted by the primary candidate's canonical artifact,
    # because that would silently present candidate A's evidence /
    # mechanism / engineering / experiment / geometry as candidate
    # B's. The primary candidate keeps its canonical un-suffixed
    # files (the same record by construction).
    missing_artifacts: List[str] = []
    if key != "primary":
        _per_inv = _read_json(
            run_dir / f"INVENTION_SPECIFICATION_{key}.json")
        _per_eng = _read_json(
            run_dir / f"ENGINEERING_SPECIFICATION_{key}.json")
        _per_dec = _read_json(
            run_dir / f"DECISIVE_EXPERIMENT_{key}.json")
        if _per_inv is None:
            missing_artifacts.append(
                f"INVENTION_SPECIFICATION_{key}.json")
            inv_spec = {}
        else:
            inv_spec = _per_inv
        if _per_eng is None:
            missing_artifacts.append(
                f"ENGINEERING_SPECIFICATION_{key}.json")
            eng_spec = {}
        else:
            eng_spec = _per_eng
        if _per_dec is None:
            missing_artifacts.append(
                f"DECISIVE_EXPERIMENT_{key}.json")
            decisive = {}
        else:
            decisive = _per_dec

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
    # R542: the recorded home of the kill condition differs by artifact
    # era — the mechanism block (fixture/legacy), the causal chain (the
    # engine's synthesis output: causal_chain.value.falsification_test),
    # or the engineering kill condition (ENGINEERING_SPECIFICATION.
    # kill_condition.falsification_test). The projection carries the
    # FIRST recorded non-empty value; the completion contract reads
    # THIS projection (one authority, Art. X) — a kill condition that
    # exists on disk is never reported missing because one field is
    # empty.
    if not str(mechanism.get("falsification_test") or "").strip():
        _cc = inv_spec.get("causal_chain") if isinstance(inv_spec, dict) \
            else {}
        if isinstance(_cc, dict) and "value" in _cc:
            _cc = _cc.get("value") or {}
        _kill = str(_cc.get("falsification_test") or "").strip() \
            if isinstance(_cc, dict) else ""
        if not _kill:
            _kc = eng_spec.get("kill_condition") \
                if isinstance(eng_spec, dict) else {}
            _kill = str(_kc.get("falsification_test") or "").strip() \
                if isinstance(_kc, dict) else ""
        if _kill:
            mechanism["falsification_test"] = _kill
    mechanism["competing_considered"] = [
        r.get("candidate_id") for r in selection.get("ranked", [])
        if r.get("candidate_id") != cid]
    # R543-2: the authoritative ranked projection carries the COMPLETE
    # competing-candidate summaries, not only IDs. Every materially
    # investigated candidate (including kills and gate exclusions)
    # rides its own candidate / mechanism / kill condition /
    # disposition on the record — the conversation must not be left
    # to reconstruct this from unrelated stage records.
    competing_summaries: List[Dict[str, Any]] = []
    for r in selection.get("ranked", []) or []:
        if not isinstance(r, dict) or r.get("candidate_id") == cid:
            continue
        comp_key = r.get("key") or "primary"
        comp_cid = r.get("candidate_id")
        comp_mech: Dict[str, Any] = {}
        comp_kill: str = ""
        if comp_key in (None, "primary"):
            _cs = inv_spec if key in (None, "primary") else {}
        else:
            _cs = _read_json(
                run_dir / f"INVENTION_SPECIFICATION_{comp_key}.json") or {}
        _cm = _cs.get("mechanism") if isinstance(_cs, dict) else {}
        if isinstance(_cm, dict) and "value" in _cm:
            _cm = _cm.get("value") or {}
        if isinstance(_cm, dict):
            comp_mech = {
                "mechanism": _cm.get("mechanism") or "",
                "intervention": _cm.get("intervention") or "",
            }
            comp_kill = (str(_cm.get("falsification_test") or "").strip())
        if not comp_kill:
            comp_kill = str(
                (r.get("kill_condition")
                 or r.get("falsification_test") or "")).strip()
        # R544: the engine stamps mechanism/intervention/
        # falsification_test onto every investigated selection row
        # (kills that never built a spec carry their structured
        # candidate's fields). The projection reads the row first —
        # a killed competitor's reasoning path must ride the
        # record, never render blank.
        if not comp_mech.get("mechanism"):
            comp_mech["mechanism"] = r.get("mechanism") or ""
        if not comp_mech.get("intervention"):
            comp_mech["intervention"] = r.get("intervention") or ""
        if not comp_kill:
            # cheap-screen kills: the skipped record preserves the
            # full structured candidate (mechanism + testable
            # prediction); the envelope is the last resort.
            _sk = _read_json(
                run_dir / "PACKAGE_SKIPPED_CHEAP_SCREEN_"
                f"{comp_key}.json") or {}
            _sc = _sk.get("structured_candidate") or {}
            if not isinstance(_sc, dict):
                _sc = {}
            if not comp_mech.get("mechanism"):
                comp_mech["mechanism"] = _sc.get("mechanism") or ""
            if not comp_mech.get("intervention"):
                comp_mech["intervention"] = _sc.get("intervention") or ""
            comp_kill = str(_sc.get("testable_prediction") or "").strip()
            if not (comp_mech.get("mechanism") and comp_kill):
                _env = _read_json(
                    run_dir / f"ENVELOPE_{comp_key}.json") or {}
                _mm = _env.get("mechanism_map") or {}
                if not isinstance(_mm, dict):
                    _mm = {}
                if not comp_mech.get("mechanism"):
                    comp_mech["mechanism"] = _mm.get("mechanism") or ""
                if not comp_mech.get("intervention"):
                    comp_mech["intervention"] = _mm.get("intervention") or ""
                if not comp_kill:
                    comp_kill = str(
                        _mm.get("falsification_test") or "").strip()
        competing_summaries.append({
            "candidate_id": comp_cid,
            "mechanism": comp_mech.get("mechanism") or "",
            "intervention": comp_mech.get("intervention") or "",
            "what_would_kill_it": comp_kill,
            "disposition": r.get("disposition") or "UNRESOLVED",
        })
    mechanism["competing_candidates"] = competing_summaries

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
        "excluded": disposition == "EXCLUDED",
        "unresolved": disposition == "UNRESOLVED",
        "quality_verdict": ranked_row.get("quality_verdict"),
        "deficient_areas": ranked_row.get("quality_deficient_count"),
    }

    # component 4 — engineering definition + model (geometry where
    # warranted, explicit conceptual classification where not)
    eng_core = eng_spec.get("engineering_core") if isinstance(eng_spec, dict) \
        else {}
    geometry = eng_spec.get("geometry") if isinstance(eng_spec, dict) else {}
    _mc = resolve_model_class(run_dir, key, eng_spec,
                              _pkg_rec(pkg_records, cid, key))
    # R544: the thread-visible engineering definition (the proposed
    # design statement from the candidate's OWN spec — mechanism +
    # design input, verbatim, truncated) and the critical parameters
    # (name/value/unit, honestly UNKNOWN when unsourced — Art.
    # XXVII: never invented). Both ride the record so the
    # conversation shows them without re-reading stage files.
    _prop = (eng_core.get("proposed_design")
             if isinstance(eng_core, dict) else {}) or {}
    if not isinstance(_prop, dict):
        _prop = {"statement": str(_prop)}
    _definition = str(_prop.get("mechanism") or _prop.get("input")
                      or _prop.get("statement") or "").strip()[:500]
    _cps = (eng_core.get("critical_parameters")
            if isinstance(eng_core, dict) else []) or []
    _params = [{"name": str(p.get("name") or p.get("parameter") or ""),
                "value": str(p.get("value") or ""),
                "unit": str(p.get("unit") or ""),
                "value_status": str(p.get("value_status") or "")}
               for p in _cps if isinstance(p, dict)][:12]
    engineering = {
        "geometry_present": bool(geometry),
        "geometry": geometry or {"class": "NOT_ESTABLISHED"},
        "engineering_core": eng_core or {},
        "model_class": _mc.get("model_class"),
        "model_class_source": _mc.get("source"),
        "earned_engineering_geometry": bool(_mc.get("earned_geometry")),
        "definition": _definition,
        "parameters": _params,
        "limitations": ("domain does not warrant physical geometry — "
                        "conceptual classification, explicitly stated"
                        if not geometry else ""),
    }

    # component 5 — decisive experiment (selected discriminator + decision)
    decisive_rec = (decisive.get("selected")
                    if isinstance(decisive, dict) else None) or {}
    _fc = (decisive.get("falsification_contract") or {}) \
        if isinstance(decisive, dict) else {}
    _hyps = [h for h in (decisive_rec.get("hypotheses") or [])
             if isinstance(h, dict)]
    experiment = {
        "experiment": decisive_rec.get("name")
                      or decisive_rec.get("experiment") or "",
        "predicted_discriminator":
            decisive_rec.get("predicted_discriminator")
            or decisive_rec.get("outcomes")
            or " | ".join(str(h.get("description") or h.get("name") or "")
                          for h in _hyps).strip(" |"),
        # R542: the recorded decision rule is the ARTICULATED
        # falsification threshold (state_integrity's authority — the
        # outcome that kills the mechanism, stated from records); the
        # selector's own decision_rule/falsification fields are only a
        # fallback for legacy records that carried them inline.
        "decision_rule": decisive_rec.get("decision_rule")
                         or decisive_rec.get("falsification")
                         or str(_fc.get("FALSIFICATION_THRESHOLD") or ""),
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

    # R543-3: a non-primary candidate with a missing own-artifact trio
    # carries the typed gap on its record — the completion contract
    # (mechanisms / adversarial / experiment components) reads THESE
    # empty records and reports the missing component by name, and
    # FINISHED_DISCOVERY is blocked. Never a silent substitution of
    # the primary candidate's content.
    if missing_artifacts:
        mechanism["own_artifact_missing"] = missing_artifacts
        engineering["own_artifact_missing"] = missing_artifacts
        experiment["own_artifact_missing"] = missing_artifacts

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
        # R541/R542: only a RECORDED SURVIVED disposition is admissible.
        # A missing disposition (a row the engine never resolved) and
        # EXCLUDED/KILLED/UNRESOLVED rows are never a finished survivor;
        # legacy runs that predate the stamp honestly project 0
        # admissible survivors (Art. X: the record is the authority).
        if _adm and (row.get("disposition") or "") == "SURVIVED":
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
        # R543-4: a complete candidate-bound package proves binding only
        # when its recorded candidate identity is EXPLICIT and equals
        # the ranked row's candidate_id (and the manifest, when it
        # carries a candidate identity, names that same candidate). An
        # absent candidate_id on a complete package is a binding
        # FAILURE, never a pass.
        binding_ok = (complete
                      and bool(pkg.get("candidate_identity_bound"))
                      and bool(pkg.get("candidate_id"))) \
            or (not complete
                and pkg.get("kind") in ("ABSENT_KILLED",
                                        "ABSENT_NOT_COMPILED"))
        # re-measure the ZIP hash from disk when a zip is recorded
        measured = None
        if complete and zip_name:
            for _cand in (run_dir / "DOWNLOAD" / zip_name,
                          run_dir / zip_name):
                if _cand.exists():
                    measured = _sha256_file(_cand)
                    break
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
            if complete:
                violations.append(
                    f"candidate {cid} rank {rank}: complete "
                    "candidate-bound package without a verified "
                    "candidate identity (recorded candidate_id "
                    f"{pkg.get('candidate_id')!r} must equal the "
                    "ranked row and the manifest's candidate identity) "
                    "— binding unproven")
            else:
                violations.append(
                    f"candidate {cid} rank {rank}: the package's "
                    "recorded candidate_id does not equal the ranked "
                    "row's candidate_id — cross-candidate package "
                    "binding")
        if complete and not hash_ok:
            violations.append(
                f"candidate {cid} rank {rank}: recorded ZIP SHA-256 "
                f"({zip_sha}) does not match the on-disk bytes "
                f"(measured {measured}) — the package artifact is not "
                "the one the result record claims")
        if not complete and pkg.get("kind") != "ABSENT_KILLED":
            violations.append(
                f"candidate {cid} rank {rank}: no complete candidate-"
                "bound technology package (package_complete=False) — "
                "the ranked set cannot be a finished discovery without "
                "this candidate's own package")
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
                                  ensure_ascii=False, default=str), encoding="utf-8")
    except Exception:  # noqa: BLE001 — persistence is best-effort,
        pass           # the return value is the record
    return record
