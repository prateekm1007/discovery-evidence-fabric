"""Coder 2 Phase 4, B13 — FREEZE THE CURRENT FINDINGS PERMANENTLY.

Per CEO Phase 4 directive (B13), preserve permanently:

    BASELINE                              = 3/15
    UNSEEN_SEMANTIC_FAILURE               = CONFIRMED
    DOMAIN_REASONING_PRIMARY_DEFECT       = CONFIRMED
    26/30 ADJUDICATOR_DISAGREEMENTS       = PRESERVED

Discipline (same as B7):
  * every frozen number is DERIVED from the underlying committed artifact
    at freeze time (Art. XXIV: an artifact outranks any summary) — the
    freeze refuses to run if a source artifact is missing or does not
    actually support the finding (fail-closed, Art. IV/V);
  * written ONCE, never overwritten (an existing freeze => REFUSED);
  * double-hashed: canonical-content sha256 INSIDE the file + byte-level
    sha256 pinned EXTERNALLY in PHASE3_FINDINGS_FREEZE.bytehash (a file
    cannot contain the hash of its own bytes);
  * HASH-CHAINED to the B7 freeze (which is itself chained to B1), so the
    findings provably describe the SAME measurement lineage;
  * verify_phase3_findings_freeze() detects any post-freeze mutation;
  * the benchmark test suite pins the byte hash so accidental modification
    fails CI.

No benchmark weakening. No baseline change. No engine file modified.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

BASELINE_DIR = Path(__file__).resolve().parents[2] / \
    "artifacts" / "benchmark" / "baseline"
FREEZE_PATH = BASELINE_DIR / "PHASE3_FINDINGS_FREEZE.json"
BYTEHASH_PIN_PATH = BASELINE_DIR / "PHASE3_FINDINGS_FREEZE.bytehash"

SOURCE_PATHS = {
    "b7_freeze": BASELINE_DIR / "INDEPENDENT_BASELINE_FREEZE.json",
    "rejection_decomposition_b8": BASELINE_DIR /
    "REJECTION_DECOMPOSITION.json",
    "blind_semantic_adjudication_b9": BASELINE_DIR /
    "BLIND_SEMANTIC_ADJUDICATION.json",
    "unseen_problem_manifest_b10": BASELINE_DIR /
    "UNSEEN_PROBLEM_MANIFEST.json",
}


def sha256_obj(obj: Any) -> str:
    return hashlib.sha256(json.dumps(
        obj, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# Derive each finding from its source artifact (fail-closed)
# ---------------------------------------------------------------------------
def _derive_baseline(b7_integrity: Dict[str, Any]) -> Dict[str, Any]:
    """BASELINE = 3/15 released, 12/15 rejected — from the verified B7
    freeze (never from a hand-copied number)."""
    if b7_integrity.get("verdict") != "INTEGRITY_OK":
        raise RuntimeError(
            f"refusing to freeze: B7 independent baseline freeze is not "
            f"integrity-OK — {b7_integrity}")
    return {
        "finding": "BASELINE",
        "value": {
            "released": b7_integrity["baseline_release_yield"]["released"],
            "total": b7_integrity["baseline_release_yield"]["total"],
            "rejected": b7_integrity["quality_rejections"]["rejected"],
        },
        "status": "FROZEN",
        "evidence": {
            "source": "INDEPENDENT_BASELINE_FREEZE.json (B7, verified)",
            "content_sha256": b7_integrity["content_sha256"],
        },
    }


def _derive_domain_reasoning_defect() -> Dict[str, Any]:
    """DOMAIN_REASONING_PRIMARY_DEFECT = CONFIRMED — every one of the 12
    rejections decomposes to PRIMARY_BLOCKER = DOMAIN_REASONING."""
    path = SOURCE_PATHS["rejection_decomposition_b8"]
    if not path.exists():
        raise RuntimeError("refusing to freeze: REJECTION_DECOMPOSITION.json "
                           "(B8) is missing")
    d = json.loads(path.read_text(encoding="utf-8"))
    counts = d.get("primary_blocker_counts") or {}
    rejections = d.get("rejections") or []
    expected = d.get("expected_rejections")
    domain = counts.get("DOMAIN_REASONING", 0)
    confirmed = (
        expected == 12 and len(rejections) == 12 and domain == 12
        and all(r.get("PRIMARY_BLOCKER") == "DOMAIN_REASONING"
                for r in rejections)
    )
    if not confirmed:
        raise RuntimeError(
            f"refusing to freeze: B8 decomposition does not support "
            f"DOMAIN_REASONING primary defect on all 12 rejections — "
            f"counts={counts}, rows={len(rejections)}")
    return {
        "finding": "DOMAIN_REASONING_PRIMARY_DEFECT",
        "value": {
            "status": "CONFIRMED",
            "primary_domain_reasoning": domain,
            "of_rejections": len(rejections),
            "defect": "mechanism text effectively passed through rather "
                      "than engineered (mechanism body word count equals "
                      "the input mechanism word count — zero elaboration)",
        },
        "evidence": {
            "source": "REJECTION_DECOMPOSITION.json (B8)",
            "file_sha256": _sha256_file(path),
        },
    }


def _derive_adjudicator_disagreements() -> Dict[str, Any]:
    """26/30 ADJUDICATOR DISAGREEMENTS = PRESERVED — counted from the B9
    artifact itself (never re-tallied by hand)."""
    path = SOURCE_PATHS["blind_semantic_adjudication_b9"]
    if not path.exists():
        raise RuntimeError("refusing to freeze: BLIND_SEMANTIC_"
                           "ADJUDICATION.json (B9) is missing")
    d = json.loads(path.read_text(encoding="utf-8"))
    stats = d.get("agreement_stats") or {}
    axes_disagreed = {a: s.get("disagreed") for a, s in stats.items()}
    total_disagreements = d.get("disagreement_count")
    recomputed = sum(v or 0 for v in axes_disagreed.values())
    sample = (d.get("sampling") or {}).get("sample_size")
    total_verdicts = None
    if isinstance(sample, int) and len(stats) == 5:
        total_verdicts = sample * 5
    if total_disagreements != recomputed or total_verdicts != 30 \
            or recomputed != 26:
        raise RuntimeError(
            f"refusing to freeze: B9 disagreement count does not match "
            f"the frozen 26/30 expectation — artifact says "
            f"{total_disagreements}/{total_verdicts}, recomputed "
            f"{recomputed}/{total_verdicts}")
    return {
        "finding": "ADJUDICATOR_DISAGREEMENTS",
        "value": {
            "status": "PRESERVED",
            "disagreements": total_disagreements,
            "total_verdicts": total_verdicts,
            "per_axis_disagreed": axes_disagreed,
            "resolution": "NONE — disagreements are preserved with both "
                          "verdicts, never averaged or forced to consensus "
                          "(CEO B9/B13)",
        },
        "evidence": {
            "source": "BLIND_SEMANTIC_ADJUDICATION.json (B9)",
            "file_sha256": _sha256_file(path),
        },
    }


def _derive_unseen_semantic_failure() -> Dict[str, Any]:
    """UNSEEN_SEMANTIC_FAILURE = CONFIRMED — all released unseen-problem
    rehearsal dossiers failed semantic correctness (B10)."""
    path = SOURCE_PATHS["unseen_problem_manifest_b10"]
    if not path.exists():
        raise RuntimeError("refusing to freeze: UNSEEN_PROBLEM_MANIFEST.json "
                           "(B10) is missing")
    d = json.loads(path.read_text(encoding="utf-8"))
    corr = d.get("UNSEEN_PROBLEM_CORRECTNESS") or {}
    released = corr.get("released_rehearsal_dossiers")
    fails = corr.get("semantic_fail_count")
    per_problem = d.get("per_problem_hashkeyed") or []
    released_ids = [p.get("unseen_id") for p in per_problem
                    if p.get("rehearsal_release_status") == "RELEASED"]
    if not isinstance(released, int) or not isinstance(fails, int) \
            or released <= 0 or fails != released or len(released_ids) != released:
        raise RuntimeError(
            f"refusing to freeze: B10 manifest does not support "
            f"'all released unseen dossiers failed semantic correctness' — "
            f"released={released}, semantic_fail_count={fails}")
    return {
        "finding": "UNSEEN_SEMANTIC_FAILURE",
        "value": {
            "status": "CONFIRMED",
            "released_rehearsal_dossiers": released,
            "semantic_fail_count": fails,
            "meaning": "the shallow-generation / wrong-content defect "
                       "class GENERALIZES to genuinely unseen problem "
                       "families — not merely overfitting to the "
                       "15-package benchmark",
        },
        "evidence": {
            "source": "UNSEEN_PROBLEM_MANIFEST.json (B10)",
            "file_sha256": _sha256_file(path),
            "released_unseen_ids": released_ids,
        },
    }


# ---------------------------------------------------------------------------
# Freeze / verify / load
# ---------------------------------------------------------------------------
def freeze_phase3_findings(
        out_path: Path = FREEZE_PATH,
        frozen_at: str = None) -> Dict[str, Any]:
    """Write the B13 findings freeze ONCE. Refuses to overwrite."""
    from .independent_freeze import verify_independent_baseline
    out_path = Path(out_path)
    if out_path.exists():
        existing = verify_phase3_findings_freeze(out_path)
        return {
            "action": "REFUSED",
            "reason": "Phase-3 findings freeze already exists — it is "
                      "permanent and is never overwritten (CEO Phase 4 B13)",
            "path": str(out_path),
            "existing_integrity": existing.get("verdict"),
            "existing_file_sha256_bytes": existing.get("file_sha256_bytes"),
        }

    b7_integrity = verify_independent_baseline()
    findings = {
        "BASELINE": _derive_baseline(b7_integrity),
        "DOMAIN_REASONING_PRIMARY_DEFECT":
            _derive_domain_reasoning_defect(),
        "ADJUDICATOR_DISAGREEMENTS": _derive_adjudicator_disagreements(),
        "UNSEEN_SEMANTIC_FAILURE": _derive_unseen_semantic_failure(),
    }

    freeze: Dict[str, Any] = {
        "artifact": "CODER2_PHASE3_FINDINGS_FREEZE",
        "owner": "CODER2",
        "freeze_id": "B13_PHASE3_FINDINGS_V1",
        "frozen_at": frozen_at or datetime.now(timezone.utc).isoformat(),
        "ceo_directive": "Phase 4 B13 — freeze the current findings "
                         "permanently; no benchmark weakening",
        "findings": findings,
        "chain_to_b7_freeze": {
            "freeze_id": "B7_INDEPENDENT_BASELINE_V1",
            "content_sha256": b7_integrity.get("content_sha256"),
            "baseline_release_yield": b7_integrity.get(
                "baseline_release_yield"),
            "quality_rejections": b7_integrity.get("quality_rejections"),
            "chained_to_B1": b7_integrity.get("chain_to_b1"),
        },
        "permanence_contract": {
            "never_overwritten": True,
            "numbers_derived_from_source_artifacts": True,
            "content_hash": "canonical-content sha256 inside this file "
                            "(self-verifiable)",
            "byte_hash_pin": "byte-level sha256 of this file pinned "
                             "EXTERNALLY in PHASE3_FINDINGS_FREEZE.bytehash "
                             "+ the benchmark test suite",
            "mutation_detection": "verify_phase3_findings_freeze() checks "
                                  "both hashes; either failing means "
                                  "FINDINGS_FREEZE_MUTATED",
            "use": "permanent record of what Coder 2 has PROVEN as of the "
                   "Phase-3 audit; new measurements are written to NEW "
                   "files, never by editing this one",
        },
        "content_sha256": None,
    }
    freeze["content_sha256"] = sha256_obj(
        {k: v for k, v in freeze.items() if k != "content_sha256"})
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(freeze, indent=1, ensure_ascii=False),
                        encoding="utf-8")
    byte_hash = hashlib.sha256(out_path.read_bytes()).hexdigest()
    pin_path = out_path.parent / (out_path.name + ".bytehash")
    pin_path.write_text(byte_hash + "\n", encoding="utf-8")
    return {"action": "FROZEN", "path": str(out_path),
            "content_sha256": freeze["content_sha256"],
            "file_sha256_bytes": byte_hash,
            "bytehash_pin": str(pin_path)}


def verify_phase3_findings_freeze(
        path: Path = FREEZE_PATH) -> Dict[str, Any]:
    """Integrity check: internal content hash + external byte-hash pin."""
    path = Path(path)
    if not path.exists():
        return {"available": False, "verdict": "MISSING",
                "reason": f"no Phase-3 findings freeze at {path}"}
    try:
        freeze = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"available": False, "verdict": "FINDINGS_FREEZE_MUTATED",
                "reason": f"unparseable freeze: {exc}"}
    recorded = freeze.get("content_sha256")
    if not recorded:
        return {"available": True, "verdict": "FINDINGS_FREEZE_MUTATED",
                "reason": "freeze carries no content hash"}
    actual = sha256_obj(
        {k: v for k, v in freeze.items() if k != "content_sha256"})
    if actual != recorded:
        return {"available": True, "verdict": "FINDINGS_FREEZE_MUTATED",
                "reason": f"content hash mismatch: recorded "
                          f"{recorded[:12]} != actual {actual[:12]}"}
    pin = path.parent / (path.name + ".bytehash")
    byte_hash = None
    if pin.exists():
        byte_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        pinned = pin.read_text(encoding="utf-8").strip()
        if byte_hash != pinned:
            return {
                "available": True, "verdict": "FINDINGS_FREEZE_MUTATED",
                "reason": f"file byte hash mismatch: pinned {pinned[:12]} "
                          f"!= actual {byte_hash[:12]} — the file bytes "
                          f"changed after freezing",
            }
    findings = freeze.get("findings") or {}
    return {
        "available": True, "verdict": "INTEGRITY_OK",
        "content_sha256": actual,
        "file_sha256_bytes": byte_hash,
        "bytehash_pin": str(pin) if pin.exists() else None,
        "baseline": (findings.get("BASELINE") or {}).get("value"),
        "domain_reasoning_primary_defect":
            (findings.get("DOMAIN_REASONING_PRIMARY_DEFECT") or {})
            .get("value", {}).get("status"),
        "adjudicator_disagreements":
            (findings.get("ADJUDICATOR_DISAGREEMENTS") or {})
            .get("value", {}),
        "unseen_semantic_failure":
            (findings.get("UNSEEN_SEMANTIC_FAILURE") or {})
            .get("value", {}).get("status"),
        "chain_to_b7": (freeze.get("chain_to_b7_freeze") or {})
        .get("content_sha256"),
    }


def load_phase3_findings(
        path: Path = FREEZE_PATH) -> Dict[str, Any]:
    path = Path(path)
    integrity = verify_phase3_findings_freeze(path)
    if integrity.get("verdict") != "INTEGRITY_OK":
        raise RuntimeError(
            f"Phase-3 findings freeze integrity failure: {integrity} — "
            f"refusing to use a mutated freeze as the reference record")
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    result = freeze_phase3_findings()
    print(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
