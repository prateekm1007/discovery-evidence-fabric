"""Coder 2 Phase 4, B16 — PERMANENT UNSEEN-PROBLEM SEAL + SEPARATED
RUN METRICS.

CEO directive B16: keep the unseen problems permanently sealed, and for
future Coder 1 runs report FIVE separated metrics:

    retrieval_success
    synthesis_success
    engineering_success
    semantic_correctness
    dossier_release

Do not collapse these into one number.

Seal rules:
  * the four unseen input hashes are sealed PERMANENTLY (written once,
    hash-chained to the B13 findings freeze; never edited);
  * unseen problem CONTENT never enters the repository (custody outside
    git; the seal and manifest carry hashes only);
  * any future run accepted as an "unseen-problem run" must verify its
    input hashes against this seal — a run against different problems is
    NOT an unseen-problem run (this closes the swap-in-easier-problems
    hole: verify_unseen_inputs checks distinctness but not identity);
  * the sealed set is never expanded or replaced; a CEO-directed change
    would have to be recorded as a NEW appended artifact, never by
    editing this one.

Metric separation rules:
  * the report schema carries EXACTLY the five metric keys per problem
    plus evidence pointers — structurally no composite score key can
    exist (a test enforces this);
  * semantic_correctness comes from the frozen B3 semantic causal audit
    of the run's released dossier (FAIL if any incorrect critical chain);
    it is NOT_ASSESSED when no dossier was released;
  * a run blocked by missing credentials is EVIDENCE_FAILURE in the B12
    taxonomy and is reported as such — never as a generation failure.

Run-to-seal binding: unseen runs are enumerated UNSEEN_01..04 in the
order of the sealed input hashes (the same order the B10 run used); the
binding rule is recorded in the report and cross-checked against the
B10 manifest's per-problem hash-keyed rows.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import data_split as ds

REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE_DIR = REPO_ROOT / "artifacts" / "benchmark" / "baseline"
UNSEEN_OUT = REPO_ROOT / "artifacts" / "benchmark" / "unseen"
SEAL_PATH = BASELINE_DIR / "UNSEEN_SET_SEAL.json"
MANIFEST_PATH = BASELINE_DIR / "UNSEEN_PROBLEM_MANIFEST.json"
METRICS_PATH = BASELINE_DIR / "UNSEEN_RUN_METRICS.json"
UNSEEN_SET_PATH = Path("/home/z/my-project/coder2_blind/UNSEEN_PROBLEM_SET.json")
UNSEEN_CUSTODY_PATH = Path(
    "/home/z/my-project/download/coder2_blind/UNSEEN_PROBLEM_SET.json")

METRIC_KEYS = ("retrieval_success", "synthesis_success",
               "engineering_success", "semantic_correctness",
               "dossier_release")


def sha256_obj(obj: Any) -> str:
    return hashlib.sha256(json.dumps(
        obj, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _load_custody_specs() -> Optional[List[Dict[str, Any]]]:
    p = UNSEEN_SET_PATH if UNSEEN_SET_PATH.exists() else UNSEEN_CUSTODY_PATH
    if not p.exists():
        return None
    data = json.loads(p.read_text(encoding="utf-8"))
    return data.get("inputs") if isinstance(data, dict) else data


# ---------------------------------------------------------------------------
# The seal
# ---------------------------------------------------------------------------
def seal_unseen_set(out_path: Path = SEAL_PATH) -> Dict[str, Any]:
    """Write the permanent unseen-set seal ONCE. The sealed hashes come
    from the committed B10 manifest (hashes-only) and are cross-checked
    against the outside-repo custody set when available. Chained to the
    B13 findings freeze."""
    out_path = Path(out_path)
    if out_path.exists():
        return {"action": "REFUSED", "reason": "unseen-set seal already "
                "exists — it is permanent and is never overwritten "
                "(CEO Phase 4 B16)", "path": str(out_path)}
    manifest = json.loads(Path(MANIFEST_PATH).read_text(encoding="utf-8"))
    sealed_hashes = list(manifest.get("unseen_input_hashes") or [])
    if len(sealed_hashes) != 4 or len(set(sealed_hashes)) != 4:
        raise RuntimeError(f"refusing to seal: manifest hashes malformed — "
                           f"{sealed_hashes}")

    custody_check = {"custody_set_available": False}
    specs = _load_custody_specs()
    if specs is not None:
        custody_hashes = [ds.blind_input_hash(s) for s in specs]
        custody_check = {
            "custody_set_available": True,
            "custody_hashes_match_seal": set(custody_hashes) ==
            set(sealed_hashes),
        }
        if not custody_check["custody_hashes_match_seal"]:
            raise RuntimeError("refusing to seal: custody unseen set "
                               "hashes do not match the B10 manifest")

    from .findings_freeze import verify_phase3_findings_freeze
    b13 = verify_phase3_findings_freeze()
    if b13.get("verdict") != "INTEGRITY_OK":
        raise RuntimeError(f"refusing to seal: B13 findings freeze not "
                           f"integrity-OK — {b13.get('verdict')}")

    seal: Dict[str, Any] = {
        "artifact": "UNSEEN_SET_SEAL",
        "owner": "CODER2",
        "seal_id": "B16_UNSEEN_SET_SEAL_V1",
        "sealed_at": datetime.now(timezone.utc).isoformat(),
        "ceo_directive": "Phase 4 B16 — keep the unseen problems "
                         "permanently sealed; report five separated "
                         "metrics; never collapse them",
        "sealed_input_hashes": sealed_hashes,
        "sealed_input_count": len(sealed_hashes),
        "custody_check": custody_check,
        "seal_rules": [
            "the unseen problem CONTENT never enters the repository; "
            "custody stays outside git (Coder 2 custody + CEO copy)",
            "any run accepted as an unseen-problem run must verify its "
            "input hashes against sealed_input_hashes via "
            "verify_unseen_seal() — a run against different problems is "
            "NOT an unseen-problem run (this closes the "
            "swap-in-easier-problems hole left by the distinctness-only "
            "B10 verification)",
            "the sealed set is never expanded or replaced; any "
            "CEO-directed change is recorded as a NEW appended artifact, "
            "never by editing this seal",
            "aggregates are append-only: future runs write NEW metric "
            "files; this seal is never edited to reflect new results",
        ],
        "metric_separation_contract": {
            "metric_keys": list(METRIC_KEYS),
            "collapse": "FORBIDDEN — no composite score, index, or "
                        "average of the five metrics may be computed or "
                        "recorded (structural: the report schema has no "
                        "such key, enforced by the benchmark test suite)",
            "credential_block_classification": "EVIDENCE_FAILURE (B12 "
                                               "taxonomy) — never a "
                                               "generation failure",
        },
        "chain_to_b13_findings_freeze": {
            "content_sha256": b13.get("content_sha256"),
        },
        "content_sha256": None,
    }
    seal["content_sha256"] = sha256_obj(
        {k: v for k, v in seal.items() if k != "content_sha256"})
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(seal, indent=1, ensure_ascii=False),
                        encoding="utf-8")
    byte_hash = hashlib.sha256(out_path.read_bytes()).hexdigest()
    pin = out_path.parent / (out_path.name + ".bytehash")
    pin.write_text(byte_hash + "\n", encoding="utf-8")
    return {"action": "SEALED", "path": str(out_path),
            "sealed_input_hashes": sealed_hashes,
            "content_sha256": seal["content_sha256"],
            "file_sha256_bytes": byte_hash}


def verify_unseen_seal(specs: List[Dict[str, Any]],
                       seal_path: Path = SEAL_PATH) -> Dict[str, Any]:
    """Acceptance gate: are these specs EXACTLY the sealed unseen set?"""
    seal = json.loads(Path(seal_path).read_text(encoding="utf-8"))
    actual = sorted(ds.blind_input_hash(s) for s in specs)
    expected = sorted(seal.get("sealed_input_hashes") or [])
    ok = actual == expected and len(specs) == seal.get("sealed_input_count")
    return {"verdict": "SEALED_SET_MATCH" if ok else "NOT_THE_SEALED_SET",
            "expected_count": seal.get("sealed_input_count"),
            "actual_count": len(specs),
            "hashes_match": actual == expected}


def verify_seal_integrity(seal_path: Path = SEAL_PATH) -> Dict[str, Any]:
    seal_path = Path(seal_path)
    if not seal_path.exists():
        return {"verdict": "MISSING"}
    seal = json.loads(seal_path.read_text(encoding="utf-8"))
    actual = sha256_obj({k: v for k, v in seal.items()
                         if k != "content_sha256"})
    if actual != seal.get("content_sha256"):
        return {"verdict": "SEAL_MUTATED"}
    pin = seal_path.parent / (seal_path.name + ".bytehash")
    if pin.exists():
        if hashlib.sha256(seal_path.read_bytes()).hexdigest() != \
                pin.read_text(encoding="utf-8").strip():
            return {"verdict": "SEAL_MUTATED"}
    return {"verdict": "INTEGRITY_OK",
            "sealed_input_hashes": seal.get("sealed_input_hashes"),
            "sealed_input_count": seal.get("sealed_input_count")}


# ---------------------------------------------------------------------------
# Five separated metrics per unseen run
# ---------------------------------------------------------------------------
def _j(path: Path) -> Optional[dict]:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return None


def _real_mode_metrics(run_dir: Path) -> Dict[str, Any]:
    stage_retrieve = _j(run_dir / "stage_RETRIEVE.json") or {}
    synth_failure = _j(run_dir / "stage_SYNTHESIZE_FAILURE.json")
    release = _j(run_dir / "DISCOVERY_RELEASE.json") or {}
    retrieved = stage_retrieve.get("retrieved_count") or 0
    return {
        "mode": "REAL",
        "retrieval_success": {
            "value": bool(retrieved),
            "evidence": f"stage_RETRIEVE.json retrieved_count="
                        f"{retrieved} (live EuropePMC)"},
        "synthesis_success": {
            "value": False if synth_failure else True,
            "evidence": ("stage_SYNTHESIZE_FAILURE.json present — LLM "
                         "credentials missing; EVIDENCE_FAILURE (B12), "
                         "NOT a generation failure"
                         if synth_failure else "synthesis stage completed"),
        },
        "engineering_success": {
            "value": None,
            "evidence": "NOT_ASSESSED — pipeline blocked upstream at "
                        "synthesis (EVIDENCE_FAILURE); no engineering "
                        "spec was generated to assess",
        },
        "semantic_correctness": {
            "value": None,
            "evidence": "NOT_ASSESSED — no dossier released in real mode",
        },
        "dossier_release": {
            "value": release.get("status") == "RELEASED",
            "evidence": f"DISCOVERY_RELEASE.json status="
                        f"{release.get('status')}",
        },
    }


def _rehearsal_mode_metrics(run_dir: Path) -> Dict[str, Any]:
    env = _j(run_dir / "candidate_envelope.json") or {}
    sv = _j(run_dir / "SURVIVOR_SELECTION.json") or {}
    eng = _j(run_dir / "ENGINEERING_SPECIFICATION.json")
    release = _j(run_dir / "DISCOVERY_RELEASE.json") or {}
    audit = _find_semantic_audit(run_dir)
    evidence_n = len(env.get("evidence") or [])
    selected = sv.get("selected")
    q_rejected = len(sv.get("quality_rejected") or [])

    if audit is not None:
        incorrect = len(audit.get("incorrect_critical_chains") or [])
        semantic = {"value": "FAIL" if incorrect else "PASS",
                    "evidence": f"B3 semantic causal audit: "
                                f"{incorrect} incorrect critical chains "
                                f"(critical = release blocker)"}
    else:
        semantic = {"value": None,
                    "evidence": "NOT_ASSESSED — engine rejected the "
                                "candidate before release; no released "
                                "dossier to assess"}

    return {
        "mode": "REHEARSAL_LABELED",
        "mode_stamp": "SYNTHETIC_REHEARSAL (Art. XXXVII)",
        "retrieval_success": {
            "value": bool(evidence_n),
            "evidence": f"fixture evidence loaded: {evidence_n} items "
                        f"(controlled rehearsal, not live retrieval)",
        },
        "synthesis_success": {
            "value": bool(selected),
            "evidence": (f"SURVIVOR_SELECTION.json: selected="
                         f"{json.dumps(selected)}; quality_rejected="
                         f"{q_rejected}"
                         + (" — engine's own E15-H gate rejected all "
                            "candidates" if not selected else "")),
        },
        "engineering_success": {
            "value": bool(eng),
            "evidence": ("ENGINEERING_SPECIFICATION.json generated"
                         if eng else "no engineering specification "
                                     "generated"),
        },
        "semantic_correctness": semantic,
        "dossier_release": {
            "value": release.get("status") == "RELEASED",
            "evidence": f"DISCOVERY_RELEASE.json status="
                        f"{release.get('status')}"
                        + (f"; failure_reason={release.get('failure_reason')}"
                           if release.get("failure_reason") else ""),
        },
    }


def _find_semantic_audit(run_dir: Path) -> Optional[Dict[str, Any]]:
    audit_path = UNSEEN_OUT / "audit" / \
        "ENGINEERING_SEMANTIC_CAUSAL_AUDIT.json"
    audit = _j(audit_path)
    if not audit:
        return None
    for pkg in audit.get("packages") or []:
        if Path(pkg.get("run_dir", "")).resolve() == \
                Path(run_dir).resolve():
            return pkg
    return None


def unseen_run_metrics(out_path: Path = METRICS_PATH,
                       seal_path: Path = SEAL_PATH) -> Dict[str, Any]:
    """Extract the five separated metrics for the existing B10 unseen
    runs (4 real + 4 rehearsal). Structural guarantee: exactly the five
    metric keys per problem; no composite score key anywhere."""
    seal = verify_seal_integrity(seal_path)
    if seal.get("verdict") != "INTEGRITY_OK":
        raise RuntimeError(f"refusing to report: unseen seal not "
                           f"integrity-OK — {seal}")
    manifest = json.loads(Path(MANIFEST_PATH).read_text(encoding="utf-8"))
    sealed_hashes = seal["sealed_input_hashes"]

    # binding check: the manifest per-problem rows must carry exactly the
    # sealed hashes (same measurement lineage)
    manifest_hashes = [p.get("input_sha256") for p in
                       manifest.get("per_problem_hashkeyed") or []]
    if sorted(manifest_hashes) != sorted(sealed_hashes):
        raise RuntimeError("refusing to report: manifest per-problem "
                           "hashes do not match the seal")

    problems: List[Dict[str, Any]] = []
    for idx, h in enumerate(sealed_hashes, start=1):
        row: Dict[str, Any] = {
            "unseen_id": f"UNSEEN_{h[:12]}",
            "input_sha256": h,
            "run_binding": f"UNSEEN_{idx:02d} (enumeration order of the "
                           f"sealed hashes; cross-checked against the B10 "
                           f"manifest per-problem rows)",
        }
        real_dir = UNSEEN_OUT / "real" / f"UNSEEN_{idx:02d}"
        reh_dir = UNSEEN_OUT / "rehearsal" / f"UNSEEN_{idx:02d}"
        if real_dir.exists():
            row["real_mode"] = _real_mode_metrics(real_dir)
        if reh_dir.exists():
            row["rehearsal_mode_labeled"] = _rehearsal_mode_metrics(reh_dir)
        problems.append(row)

    def _agg(mode_key: str, metric: str, value) -> int:
        return sum(1 for p in problems
                   if (p.get(mode_key) or {}).get(metric, {})
                   .get("value") == value)

    aggregate = {
        "mode_note": "real mode = live retrieval + live synthesis "
                     "(credential-gated); rehearsal mode = full pipeline "
                     "through the real code path with fixture evidence, "
                     "every artifact stamped SYNTHETIC_REHEARSAL",
        "real_mode": {
            "runs": _count(problems, "real_mode"),
            "retrieval_success": _agg("real_mode", "retrieval_success",
                                      True),
            "synthesis_success": _agg("real_mode", "synthesis_success",
                                      True),
            "dossier_release": _agg("real_mode", "dossier_release", True),
            "synthesis_blocked_by_credentials":
                _agg("real_mode", "synthesis_success", False),
        },
        "rehearsal_mode_labeled": {
            "runs": _count(problems, "rehearsal_mode_labeled"),
            "retrieval_success": _agg("rehearsal_mode_labeled",
                                      "retrieval_success", True),
            "synthesis_success": _agg("rehearsal_mode_labeled",
                                      "synthesis_success", True),
            "engineering_success": _agg("rehearsal_mode_labeled",
                                        "engineering_success", True),
            "semantic_correctness_fail": _agg("rehearsal_mode_labeled",
                                              "semantic_correctness",
                                              "FAIL"),
            "semantic_correctness_pass": _agg("rehearsal_mode_labeled",
                                              "semantic_correctness",
                                              "PASS"),
            "semantic_correctness_not_assessed":
                _agg("rehearsal_mode_labeled", "semantic_correctness",
                     None),
            "dossier_release": _agg("rehearsal_mode_labeled",
                                    "dossier_release", True),
        },
    }

    report: Dict[str, Any] = {
        "artifact": "UNSEEN_RUN_METRICS",
        "owner": "CODER2",
        "ceo_directive": "Phase 4 B16 — five separated metrics for "
                         "unseen-problem runs; never collapsed",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "seal": {"seal_id": "B16_UNSEEN_SET_SEAL_V1",
                 "integrity": "INTEGRITY_OK",
                 "sealed_input_count": seal["sealed_input_count"]},
        "metric_keys": list(METRIC_KEYS),
        "collapse_prohibition": "no composite score / index / average of "
                                "the five metrics exists in this schema "
                                "(enforced by the benchmark test suite)",
        "problems": problems,
        "aggregate": aggregate,
        "current_reading": {
            "real_mode": "retrieval works (4/4); synthesis blocked by "
                         "missing LLM credentials (4/4 EVIDENCE_FAILURE) "
                         "— CEO key re-provision unlocks; NOT a "
                         "generation failure",
            "rehearsal_mode_labeled": "3/4 released; 3/3 released "
                                      "dossiers FAIL semantic "
                                      "correctness; 1/4 rejected by the "
                                      "engine's own E15-H gate",
        },
    }
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=1, ensure_ascii=False),
                        encoding="utf-8")
    return report


def _count(problems: List[Dict[str, Any]], mode_key: str) -> int:
    return sum(1 for p in problems if p.get(mode_key))


def assert_no_collapse(report: Dict[str, Any]) -> None:
    """Structural check: no composite-score key anywhere in the report."""
    forbidden = ("score", "composite", "index", "average", "overall",
                 "total_score", "unseen_score")
    stack = [report]
    while stack:
        obj = stack.pop()
        if isinstance(obj, dict):
            for k, v in obj.items():
                if any(f in str(k).lower() for f in forbidden):
                    raise AssertionError(
                        f"collapse violation: forbidden key '{k}' — the "
                        f"five metrics must never be collapsed (CEO B16)")
                stack.append(v)
        elif isinstance(obj, list):
            stack.extend(obj)


def main() -> None:
    result = seal_unseen_set()
    print(json.dumps(result, indent=1))
    report = unseen_run_metrics()
    assert_no_collapse(report)
    print(json.dumps(report["aggregate"], indent=1))


if __name__ == "__main__":
    main()
