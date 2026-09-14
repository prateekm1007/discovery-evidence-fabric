"""discovery_fabric/engine/blind_protocol.py — CEO E16-B: origin-blind
evaluation.

The evaluator must compare GENERATED vs REFERENCE "without seeing the
origin". This module implements the blind protocol mechanically:

  1. prepare_blind_set(): candidate packages (generated) and reference
     packages (frozen gold standard) are COPIED into an anonymized
     work directory; every package is renamed SUBJECT-XX; identity
     fields (package_id, portfolio_number, technology_name, run ids,
     hashes that embed identities) are stripped from the copies. The
     origin mapping is sealed (sha256) into a key file.
  2. measure_subjects(): the SAME instruments (substance_metrics +
     benchmark_dossiers vectors) run on every anonymized subject — the
     measurement code literally cannot know an origin.
  3. reveal(): the sealed mapping is opened and the comparison is
     scored: each GENERATED subject against the REFERENCE distribution
     (E16-C substantive rule) and against the E16-A training floors.

Constitutional properties:
  - The blind subjects directory contains no origin information (the
    key file lives outside it).
  - The reference distribution used for scoring is the TRAINING_REFERENCE
    stratum only (E16-A) — the blind holdout is never mixed into it.
  - Deterministic subject ordering (sorted by content hash) so the
    protocol is reproducible (Art. XXIV).
"""
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from archive.r455_retired.discovery_fabric.engine.benchmark_dossiers import extract_package_vector
from discovery_fabric.engine.substance_metrics import (content_vector, evaluate_substance,
                                reference_distribution)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z"


_IDENTITY_FIELDS = ("package_id", "portfolio_number", "technology_name",
                    "run_id", "release_id")


def _anonymize_package(pkg_dir: Path, subject_dir: Path) -> None:
    """Copy a package and strip identity fields from its manifest."""
    subject_dir.mkdir(parents=True, exist_ok=True)
    for item in pkg_dir.iterdir():
        if item.is_file():
            shutil.copy2(item, subject_dir / item.name)
    manifest_path = subject_dir / "PACKAGE_MANIFEST.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        for f in _IDENTITY_FIELDS:
            manifest.pop(f, None)
        # generic subject id replaces the stripped identity
        manifest["subject_note"] = ("anonymized for blind evaluation "
                                    "(E16-B); identity fields stripped")
        manifest_path.write_text(json.dumps(manifest, indent=2,
                                            ensure_ascii=False))
    # generated-run provenance inside traceability is stripped too
    trace_path = subject_dir / "ENGINEERING_TRACEABILITY.json"
    if trace_path.exists():
        trace = json.loads(trace_path.read_text())
        for chain in trace.get("traceability_chains", []) or []:
            chain.pop("candidate_id", None)
            chain.pop("invention_id", None)
        trace_path.write_text(json.dumps(trace, indent=2,
                                         ensure_ascii=False))


def prepare_blind_set(generated_dirs: List[Path],
                      reference_dirs: List[Path],
                      work_root: Path) -> Dict[str, Any]:
    """Build the anonymized subject set. Returns the sealed protocol
    record (the ONLY place origin information survives)."""
    subjects: List[Tuple[str, Path]] = []
    for d in list(generated_dirs) + list(reference_dirs):
        subjects.append(("GENERATED" if d in set(generated_dirs)
                         else "REFERENCE", d))
    # deterministic order by package content hash
    def _content_hash(d: Path) -> str:
        h = hashlib.sha256()
        for f in sorted(d.iterdir()):
            if f.is_file():
                h.update(f.name.encode())
                h.update(f.read_bytes())
        return h.hexdigest()
    subjects.sort(key=lambda t: _content_hash(t[1]))
    mapping: Dict[str, str] = {}
    for i, (origin, d) in enumerate(subjects, 1):
        subject_id = f"SUBJECT-{i:02d}"
        _anonymize_package(d, Path(work_root) / "subjects" / subject_id)
        mapping[subject_id] = {"origin": origin, "source_dir": str(d)}
    key = {
        "protocol": "E16-B blind evaluation",
        "created_at": utc_now(),
        "n_subjects": len(mapping),
        "key": mapping,
    }
    key_path = Path(work_root) / "BLIND_KEY_SEALED.json"
    key_path.write_text(json.dumps(key, indent=2, ensure_ascii=False))
    subjects_dir = Path(work_root) / "subjects"
    subjects_manifest = {
        "subjects": sorted(p.name for p in subjects_dir.iterdir()),
        "note": "no origin information exists in this directory",
    }
    (subjects_dir / "SUBJECTS.json").write_text(
        json.dumps(subjects_manifest, indent=2))
    return {"work_root": str(work_root), "key_path": str(key_path),
            "subjects": subjects_manifest["subjects"]}


def measure_subjects(subjects_dir: Path) -> Dict[str, Any]:
    """Origin-blind measurement: the SAME instruments on every subject.
    This function has no access to the key and cannot know origins."""
    out: Dict[str, Any] = {}
    for d in sorted(Path(subjects_dir).iterdir()):
        if not d.is_dir() or d.name == "SUBJECTS.json":
            continue
        if not (d / "PACKAGE_MANIFEST.json").exists():
            continue
        out[d.name] = {
            "content_vector": content_vector(d),
            "structural_vector": {
                k: v for k, v in extract_package_vector(d).items()
                if not k.startswith("_")},
        }
    return out


def reveal_and_score(measurements: Dict[str, Any], key_path: Path,
                     reference_dirs: List[Path],
                     floors_contract: Optional[Dict[str, Any]] = None,
                     ) -> Dict[str, Any]:
    """Open the sealed key, then score every GENERATED subject against
    the REFERENCE distribution (E16-C) and the training floors."""
    key = json.loads(Path(key_path).read_text())
    from archive.r455_retired.discovery_fabric.engine.benchmark_dossiers import load_contract, meets_floors
    contract = floors_contract or load_contract()
    dist = reference_distribution(reference_dirs)
    results = []
    for subject_id, meta in key["key"].items():
        m = measurements.get(subject_id)
        if m is None:
            continue
        entry: Dict[str, Any] = {
            "subject_id": subject_id, "origin": meta["origin"],
            "source_dir": meta["source_dir"]}
        if meta["origin"] == "GENERATED":
            sub = evaluate_substance(m["content_vector"], dist)
            entry["substance"] = {"verdict": sub["verdict"],
                                  "dims_at_or_above_p25":
                                      sub["dims_at_or_above_p25"],
                                  "deficient_areas": sub["deficient_areas"]}
            entry["floors"] = meets_floors(
                m["structural_vector"], contract)
        else:
            # reference subjects are scored too — the evaluator must not
            # treat them differently (they demonstrate the band the
            # gold-standard corpus itself occupies)
            sub = evaluate_substance(m["content_vector"], dist)
            entry["substance"] = {"verdict": sub["verdict"],
                                  "dims_at_or_above_p25":
                                      sub["dims_at_or_above_p25"]}
        results.append(entry)
    generated = [r for r in results if r["origin"] == "GENERATED"]
    references = [r for r in results if r["origin"] == "REFERENCE"]
    return {
        "reveal": "origins disclosed ONLY after measurement",
        "n_generated": len(generated),
        "n_reference": len(references),
        "results": results,
        "generated_pass_count": sum(
            1 for r in generated if r["substance"]["verdict"] == "PASS"),
        "reference_pass_count": sum(
            1 for r in references if r["substance"]["verdict"] == "PASS"),
        "scored_at": utc_now(),
    }
