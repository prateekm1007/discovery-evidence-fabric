"""Coder 2 Phase 2, B2 — benchmark data split (DEV / HOLDOUT / BLIND).

The benchmark input universe is partitioned into three sets with
different disclosure guarantees:

    DEVELOPMENT_SET — committed inputs Coder 1 may iterate against.
                      Coder 1 receives full per-run results for these.
    HOLDOUT_SET     — committed inputs reserved for checkpoint audits.
                      Coder 1 has ALREADY seen their content (they were
                      committed before the split existed — this is
                      recorded honestly: HOLDOUT is reserved, NOT blind),
                      but per-run iteration feedback is not provided.
    BLIND_SET       — inputs whose CONTENT never enters the shared git
                      repository. Content lives only outside the repo
                      (CEO custody); the repo carries sha256 hashes only.
                      Coder 1 must never receive blind-set content or
                      the per-run blind details (aggregate verdicts only).

No engine file is modified. The split is Coder 2 measurement
infrastructure.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------------------
# Split of the 15 committed benchmark inputs (BENCH_01..BENCH_15).
#
# Rationale (recorded, not arbitrary):
#   * both sets contain released AND engine-rejected runs so each set
#     exercises both failure modes (DEV: 2 released / 6 rejected;
#     HOLDOUT: 1 released / 6 rejected);
#   * domain families are spread across both sets (DEV spans 7 families,
#     HOLDOUT spans 5);
#   * holdout is NOT blind: all 15 inputs were committed before this
#     split existed, so their content is already visible to Coder 1.
#     Only the BLIND set is content-hidden.
# ---------------------------------------------------------------------------
DEVELOPMENT_BENCH_IDS = list(range(1, 9))    # BENCH_01..BENCH_08
HOLDOUT_BENCH_IDS = list(range(9, 16))       # BENCH_09..BENCH_15

BLIND_INPUT_COUNT = 5

# Outside-repo custody locations for blind content (NEVER committed).
# Working copy for runs + a CEO-custody copy under download/ so a sandbox
# reset cannot silently destroy the blind corpus (the CEO can re-provision
# it; Coder 1 never receives it — the repo is the only shared channel).
BLIND_SET_PATH = Path("/home/z/my-project/coder2_blind/BLIND_SET.json")
BLIND_CUSTODY_PATH = Path(
    "/home/z/my-project/download/coder2_blind/BLIND_SET.json")

REQUIRED_SPEC_KEYS = (
    "domain", "device", "failure_mode", "failure", "constraint",
    "mechanism", "intervention", "effect", "fals",
)

KNOWN_DOMAINS = (
    "fluidics_hydraulic", "optical_photonic", "rf_wireless", "acoustic",
    "mri_nmr", "enzyme_biocatalytic", "phage_microbio", "ml_data",
    "mechanical_structural", "thermal", "energy_harvesting",
)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def blind_input_hash(spec: Dict[str, Any]) -> str:
    """Stable content hash of one blind input (canonical JSON)."""
    canon = json.dumps(
        {k: spec.get(k) for k in REQUIRED_SPEC_KEYS}, sort_keys=True,
        ensure_ascii=False)
    return sha256_text(canon)


def load_blind_set(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Load blind input specs from the outside-repo custody file.

    The committed code NEVER contains blind content — only this loader,
    which reads from a path that lives outside the repository.
    """
    p = Path(path) if path else BLIND_SET_PATH
    if not p.exists() and BLIND_CUSTODY_PATH.exists():
        p = BLIND_CUSTODY_PATH
    data = json.loads(p.read_text(encoding="utf-8"))
    specs = data.get("inputs") if isinstance(data, dict) else data
    if not isinstance(specs, list):
        raise ValueError(f"blind set file {p} has no inputs list")
    return specs


def verify_blind_inputs(specs: List[Dict[str, Any]],
                        committed_inputs: Optional[List[Dict[str, Any]]] = None,
                        expect_count: int = BLIND_INPUT_COUNT) -> Dict[str, Any]:
    """Structural + distinctness verification of the blind set.

    Checks (all machine-recorded):
      * count matches expectation;
      * every spec carries the full survivor-input shape;
      * domains are known families;
      * mechanisms are substantive (not one-word fixtures);
      * blind inputs are NOT near-duplicates of the committed inputs
        (significant-word Jaccard below 0.6 vs every committed input).
    """
    from .corpus_runner import BENCHMARK_INPUTS  # committed inputs

    committed = committed_inputs if committed_inputs is not None \
        else BENCHMARK_INPUTS
    problems: List[str] = []
    if len(specs) != expect_count:
        problems.append(f"expected {expect_count} blind inputs, "
                        f"found {len(specs)}")
    hashes = []
    for i, s in enumerate(specs):
        missing = [k for k in REQUIRED_SPEC_KEYS if not str(s.get(k, "")).strip()]
        if missing:
            problems.append(f"blind[{i}] missing keys: {missing}")
            continue
        if s["domain"] not in KNOWN_DOMAINS:
            problems.append(f"blind[{i}] unknown domain {s['domain']!r}")
        if len(s["mechanism"].split()) < 8:
            problems.append(f"blind[{i}] mechanism too thin "
                            f"({len(s['mechanism'].split())} words)")
        hashes.append(blind_input_hash(s))
        for j, c in enumerate(committed, start=1):
            jac = _jaccard(s["mechanism"], c["mechanism"])
            if jac >= 0.6:
                problems.append(
                    f"blind[{i}] mechanism too similar to committed "
                    f"BENCH_{j:02d} (Jaccard {jac:.2f}) — blind set must "
                    f"measure generalization, not memorized inputs")
    if len(set(hashes)) != len(hashes):
        problems.append("duplicate blind inputs (hash collision)")
    return {
        "check": "BLIND_SET_VERIFICATION",
        "owner": "CODER2",
        "count": len(specs),
        "expect_count": expect_count,
        "input_hashes": hashes,
        "distinct_from_committed": not any(
            "too similar" in p for p in problems),
        "problems": problems,
        "verdict": "PASS" if not problems else "FAIL",
    }


def build_split_manifest() -> Dict[str, Any]:
    """Committed split manifest — blind content NEVER included.

    The manifest carries: the DEV/HOLDOUT assignment of the committed
    inputs, the blind input count, and the sha256 hash of each blind
    input (content provable, content not disclosed).
    """
    return {
        "artifact": "CODER2_BENCHMARK_SPLIT_MANIFEST",
        "owner": "CODER2",
        "split_version": 1,
        "disclosure_contract": {
            "DEVELOPMENT_SET": "committed; Coder 1 receives full "
                               "per-run results; open iteration set",
            "HOLDOUT_SET": "committed (content already public before "
                           "the split — reserved, NOT blind); results "
                           "reported at audit checkpoints only",
            "BLIND_SET": "content NEVER committed to the shared repo; "
                         "repo carries hashes only; Coder 1 receives "
                         "aggregate verdicts only",
        },
        "development_set": {
            "bench_ids": [f"BENCH_{i:02d}" for i in DEVELOPMENT_BENCH_IDS],
            "count": len(DEVELOPMENT_BENCH_IDS),
        },
        "holdout_set": {
            "bench_ids": [f"BENCH_{i:02d}" for i in HOLDOUT_BENCH_IDS],
            "count": len(HOLDOUT_BENCH_IDS),
        },
        "blind_set": {
            "count": BLIND_INPUT_COUNT,
            "content_location": "outside the repository (Coder 2 "
                                "custody); CEO custody copy under "
                                "download/coder2_blind/",
            "inputs": "see BLIND_SET_MANIFEST.json (hashes only)",
        },
    }


def build_blind_manifest(specs: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Committed blind manifest — HASHES ONLY, never content."""
    if specs is None:
        specs = load_blind_set()
    ver = verify_blind_inputs(specs)
    return {
        "artifact": "CODER2_BLIND_SET_MANIFEST",
        "owner": "CODER2",
        "count": len(specs),
        "hash_algorithm": "sha256 over canonical JSON of the 9-key "
                          "survivor input spec",
        "inputs": [
            {"blind_id": f"BLIND_{i + 1:02d}",
             "sha256": blind_input_hash(s)}
            for i, s in enumerate(specs)
        ],
        "verification": {k: v for k, v in ver.items()},
        "note": "Content deliberately absent from this repository. "
                "Per-run blind results are published as aggregates "
                "only (no domains, devices, mechanisms, or quoted "
                "text).",
    }


def _words(text: str) -> set:
    import re
    stop = {"the", "a", "an", "of", "and", "or", "to", "in", "by", "with",
            "for", "as", "at", "is", "are", "that", "this", "it", "its",
            "from", "on", "be", "into", "when", "where", "which", "than"}
    ws = {w.lower() for w in re.findall(r"[a-z][a-z\-]+", str(text).lower())
          if len(w) > 3 and w not in stop}
    return ws


def _jaccard(a: str, b: str) -> float:
    wa, wb = _words(a), _words(b)
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)
