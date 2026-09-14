"""discovery_fabric/engine/benchmark_split.py — CEO E16-A: independent
benchmark strata.

The CEO E15 audit identified the benchmark's deepest weakness:

    "the benchmark is derived from the same portfolio that the system is
     trying to reproduce ... a generator can deliberately produce
     [the floor values] and pass the benchmark without actually possessing
     the reasoning quality of the original."

E16-A therefore splits the frozen 15-package corpus into three strata:

    TRAINING_REFERENCE     (10 packages) — the ONLY stratum from which
                           benchmark floors/dimensions are derived.
    DEVELOPMENT_HOLDOUT    (3 packages)  — available for development
                           validation, never part of floor derivation.
    BLIND_HOLDOUT          (2 packages)  — vectors are SEALED. The
                           generator and benchmark-derivation logic never
                           read them; only the E16-B blind evaluator and
                           the E16-H holdout release gate open the seal,
                           at EVALUATION time.

Split rule (deterministic, transparent, no cherry-picking) — packages
sorted by package_id, 0-based index i over the 15:

    BLIND_HOLDOUT        if i % 8 == 0   -> indices {0, 8}      (2 pkgs)
    DEVELOPMENT_HOLDOUT  if i % 5 == 4   -> indices {4, 9, 14}  (3 pkgs)
    TRAINING_REFERENCE   otherwise       -> the remaining 10

The rule is recorded verbatim in the artifact so any auditor can re-derive
the assignment from the frozen corpus alone.

Constitutional properties:
  - The frozen portfolio is read-only (never modified).
  - Every package's provenance is a sha256 of its manifest+traceability.
  - The sealed blind vectors carry a seal hash recorded in the split
    artifact (tamper-evidence, Art. XII).
  - A static guard test (tests/test_e16_series.py) proves NO module under
    discovery_fabric/engine/ reads the sealed blind vectors except the
    release gate's holdout check and the blind evaluator (evaluation-time
    only, never floor derivation).
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# R455-LEAN-1: this module was relocated 2 levels deeper
# (archive/r455_retired/...); REPO_ROOT is 4 parents up
REPO_ROOT = Path(__file__).resolve().parents[4]
FROZEN_PORTFOLIO = Path(__file__).resolve().parents[4] / \
    "BENCHMARK_ENGINEERING_DOSSIERS" / "frozen_corpus_r370"
BENCHMARK_DIR = REPO_ROOT / "BENCHMARK_ENGINEERING_DOSSIERS"
SPLIT_ARTIFACT = BENCHMARK_DIR / "E16_BENCHMARK_SPLIT.json"
SEALED_DIR = BENCHMARK_DIR / "BLIND_HOLDOUT"
SEALED_VECTORS = SEALED_DIR / "SEALED_VECTORS.json"

STRATA = ("TRAINING_REFERENCE", "DEVELOPMENT_HOLDOUT", "BLIND_HOLDOUT")

SPLIT_RULE = (
    "packages sorted by package_id, 0-based index i over the 15: "
    "BLIND_HOLDOUT if i % 8 == 0 (indices {0, 8}); "
    "DEVELOPMENT_HOLDOUT if i % 5 == 4 and not blind (indices {4, 9, 14}); "
    "TRAINING_REFERENCE otherwise (the remaining 10). Deterministic, "
    "transparent, re-derivable from the frozen corpus alone.")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z"


def _pkg_provenance(pkg_dir: Path) -> str:
    h = hashlib.sha256()
    for name in ("PACKAGE_MANIFEST.json", "ENGINEERING_TRACEABILITY.json",
                 "MATURITY_BASIS.json"):
        p = pkg_dir / name
        if p.exists():
            h.update(name.encode())
            h.update(p.read_bytes())
    return h.hexdigest()


def list_frozen_packages(corpus_root: Optional[Path] = None) -> List[Path]:
    root = Path(corpus_root) if corpus_root else FROZEN_PORTFOLIO
    return sorted(d for d in root.iterdir()
                  if d.is_dir() and (d / "PACKAGE_MANIFEST.json").exists())


def assign_strata(corpus_root: Optional[Path] = None,
                  ) -> Dict[str, List[str]]:
    """Apply the documented split rule; refuse any corpus other than the
    frozen 15 (benchmark integrity, Art. XII)."""
    dirs = list_frozen_packages(corpus_root)
    if len(dirs) != 15:
        raise RuntimeError(
            f"expected the frozen 15-package corpus, found {len(dirs)} — "
            "stratification refused (E16-A benchmark integrity)")
    ids = [d.name for d in dirs]
    strata: Dict[str, List[str]] = {s: [] for s in STRATA}
    for i, pkg_id in enumerate(ids):
        if i % 8 == 0:
            strata["BLIND_HOLDOUT"].append(pkg_id)
        elif i % 5 == 4:
            strata["DEVELOPMENT_HOLDOUT"].append(pkg_id)
        else:
            strata["TRAINING_REFERENCE"].append(pkg_id)
    assert len(strata["TRAINING_REFERENCE"]) == 10
    assert len(strata["DEVELOPMENT_HOLDOUT"]) == 3
    assert len(strata["BLIND_HOLDOUT"]) == 2
    return strata


def stratum_of(pkg_id: str,
               strata: Optional[Dict[str, List[str]]] = None) -> str:
    strata = strata or load_split()["strata"]
    for s, members in strata.items():
        if pkg_id in members:
            return s
    raise KeyError(pkg_id)


def write_canonical_artifacts(corpus_root: Optional[Path] = None) -> Path:
    """Write E16_BENCHMARK_SPLIT.json + the SEALED blind vectors."""
    from archive.r455_retired.discovery_fabric.engine.benchmark_dossiers import extract_package_vector
    dirs = list_frozen_packages(corpus_root)
    strata = assign_strata(corpus_root)
    per_package = {}
    for d in dirs:
        per_package[d.name] = {
            "stratum": stratum_of(d.name, strata),
            "provenance_sha256": _pkg_provenance(d)}
    blind_vectors = {}
    for d in dirs:
        if stratum_of(d.name, strata) == "BLIND_HOLDOUT":
            v = extract_package_vector(d)
            # E16-H: the sealed holdout carries BOTH the structural vector
            # and the E16-C content vector (the holdout release gate
            # compares the generated package's content against the blind
            # distribution, opened only at evaluation time)
            from discovery_fabric.engine.substance_metrics import content_vector
            blind_vectors[d.name] = {
                "structural": {k: v[k] for k in
                               ("package_id", "engineering_sections",
                                "design_input_count", "design_output_count",
                                "failure_mode_count", "verification_count",
                                "validation_count", "equation_count",
                                "parameter_count", "provenance_density",
                                "traceability_density",
                                "manufacturing_depth", "regulatory_depth",
                                "transfer_depth", "buyer_decision_depth",
                                "engineering_actionability")},
                "content": content_vector(d)}
    BENCHMARK_DIR.mkdir(parents=True, exist_ok=True)
    SEALED_DIR.mkdir(parents=True, exist_ok=True)
    sealed_payload = {
        "sealed": "BLIND_HOLDOUT vectors (E16-A) — opened ONLY at "
                  "evaluation time by the E16-B blind evaluator and the "
                  "E16-H holdout release gate; NEVER by benchmark-floor "
                  "derivation or generator development",
        "sealed_at": utc_now(),
        "vectors": blind_vectors,
    }
    SEALED_VECTORS.write_text(json.dumps(sealed_payload, indent=2,
                                         ensure_ascii=False))
    seal_hash = hashlib.sha256(SEALED_VECTORS.read_bytes()).hexdigest()
    artifact = {
        "artifact": "E16_BENCHMARK_SPLIT (E16-A)",
        "version": "1.0.0",
        "split_rule": SPLIT_RULE,
        "strata": strata,
        "per_package": per_package,
        "sealed_vectors_file": str(SEALED_VECTORS.relative_to(REPO_ROOT)),
        "sealed_vectors_sha256": seal_hash,
        "rule": ("benchmark floors are derived from TRAINING_REFERENCE "
                 "ONLY; DEVELOPMENT_HOLDOUT never informs floors; "
                 "BLIND_HOLDOUT vectors are sealed until evaluation"),
        "generated_at": utc_now(),
    }
    SPLIT_ARTIFACT.write_text(json.dumps(artifact, indent=2,
                                         ensure_ascii=False))
    return SPLIT_ARTIFACT


def load_split() -> Dict[str, Any]:
    return json.loads(SPLIT_ARTIFACT.read_text())


def training_reference_ids() -> List[str]:
    return load_split()["strata"]["TRAINING_REFERENCE"]


def open_sealed_blind_vectors() -> Dict[str, Any]:
    """EVALUATION-TIME ONLY (E16-B blind evaluator, E16-H holdout gate).
    Verifies the seal hash before returning the vectors; a tampered seal
    refuses to open (Art. XII)."""
    split = load_split()
    body = SEALED_VECTORS.read_bytes()
    if hashlib.sha256(body).hexdigest() != split["sealed_vectors_sha256"]:
        raise RuntimeError(
            "BLIND_HOLDOUT seal hash mismatch — the sealed vectors were "
            "modified after the split was recorded (refusing to evaluate "
            "against tampered holdout data, Art. XII)")
    return json.loads(body)
