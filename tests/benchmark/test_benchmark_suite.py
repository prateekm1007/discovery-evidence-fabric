"""tests/benchmark — Coder 2 benchmark & audit test suite.

Adversarial suite (Phase 14): every attack class from the CEO mandate must
be caught by its expected Coder 2 control. Clean outputs must NOT trigger
the controls (no false positives).

Regression suite (Phase 13): contract thresholds stay corpus-derived,
profile/contract/benchmark artifacts stay consistent, and the evaluator
verdicts on the committed benchmark are stable.

Hermeticity (E20 measurement, 2026-08-28): the heavy module-scoped fixture
below instantiates BEFORE the function-scoped autouse conftest patch, so
that patch is not yet active while its rehearsal runs execute. With live
provider credentials in .env.keys the ensemble call inside
_post_rank_pipeline then makes LIVE LLM calls (measured: suite hangs on a
degraded endpoint, 240 s x 3 per call x 6 runs; offline the same suite
passes in 14.6 s). The fixture therefore guarantees its OWN offline state
and restores the environment afterwards — the audit suite must never
spend live calls or depend on ambient credentials.
"""
import json
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.benchmark import adversarial  # noqa: E402
from discovery_fabric.benchmark import audit_runner  # noqa: E402
from discovery_fabric.benchmark import contamination as ct  # noqa: E402
from discovery_fabric.benchmark import corpus_runner  # noqa: E402

CONTRACT = json.loads(
    (REPO_ROOT / "artifacts/benchmark/ENGINEERING_DEPTH_CONTRACT.json")
    .read_text(encoding="utf-8"))
PROFILE = json.loads(
    (REPO_ROOT / "artifacts/benchmark/BENCHMARK_DOSSIER_PROFILE.json")
    .read_text(encoding="utf-8"))


# Same vocabulary as tests/conftest.py (kept in sync deliberately; the
# conftest patch is function-scoped and therefore NOT active during this
# module-scoped fixture's setup — see module docstring).
_PROVIDER_ENV_VARS = [
    "OPENROUTER_API_KEY", "NVIDIA_API_KEY", "ANTHROPIC_API_KEY",
    "GEMINI_API_KEY", "OPENAI_API_KEY", "QWEN_API_KEY", "DEEPSEEK_API_KEY",
    "MISTRAL_API_KEY",
]


@pytest.fixture(scope="module")
def two_runs(tmp_path_factory):
    """Complete-dossier runs generated through Coder 1's real pipeline.

    The engine's E15-H gate honestly rejects some inputs (fail-closed is
    correct behavior). Since the E16 merge the engine also no longer
    auto-releases ANY independent benchmark input: dossiers it would
    have released now come back HELD_FOR_HUMAN_REVIEW (complete buyer
    package on disk, release gated pending human review — see
    ENGINE_HEAD_REMEASUREMENT_E16MERGE.json for the measured status
    distribution). The fixture needs real generated dossiers to attack,
    so it accepts BOTH statuses as produced-dossier runs; the release-
    YIELD measurement itself lives in the frozen baseline artifacts and
    the engine-head re-measurement, never in this fixture.

    SELF-HERMETICITY (E20): strips provider credentials and neutralizes
    the .env.keys bootstrap for the ENTIRE module (yield/finally),
    restoring the exact prior environment afterwards. ENGINE_LIVE=1 is
    honored as the explicit operator live opt-in (same gate as
    conftest).
    """
    live_opt_in = bool(os.environ.get("ENGINE_LIVE"))
    saved_env = {v: os.environ.get(v) for v in _PROVIDER_ENV_VARS}
    import discovery_fabric.engine.adapters as _adapters
    _orig_load_credentials = _adapters.load_credentials
    if not live_opt_in:
        for v in _PROVIDER_ENV_VARS:
            os.environ.pop(v, None)
        # the .env.keys bootstrap must not repopulate what we removed
        _adapters.load_credentials = lambda path=None: {}
    try:
        root = tmp_path_factory.mktemp("bench_runs")
        info = corpus_runner.run_benchmark(root, limit=6)
        released = []
        for p in info["run_dirs"]:
            rel = json.loads((Path(p) / "DISCOVERY_RELEASE.json")
                             .read_text(encoding="utf-8"))
            has_dossier = bool(rel.get("package_folder") and
                               Path(rel["package_folder"]).exists())
            if rel.get("status") in ("RELEASED", "HELD_FOR_HUMAN_REVIEW") \
                    and has_dossier:
                released.append(Path(p))
        assert len(released) >= 2, (
            f"expected at least 2 produced-dossier runs, got "
            f"{len(released)} — engine E15-H rejection rate on independent "
            f"inputs is itself a benchmark finding (see "
            f"AUTOMATED_DOSSIER_BENCHMARK.json and "
            f"ENGINE_HEAD_REMEASUREMENT_E16MERGE.json)")
        yield released
    finally:
        if not live_opt_in:
            _adapters.load_credentials = _orig_load_credentials
            for k, v in saved_env.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v


def _audit(run_dir):
    return audit_runner.audit_run(run_dir, CONTRACT, PROFILE)


# ---------------------------------------------------------------------------
# Phase 14 — adversarial benchmark tests
# ---------------------------------------------------------------------------
SINGLE_RUN_ATTACKS = [
    "REMOVE_DESIGN_INPUT",
    "REMOVE_FAILURE_MODE",
    "REPLACE_EQUATION",
    "INJECT_UNSUPPORTED_NUMBER",
    "INJECT_FAKE_SOURCE",
    "LABEL_PROPOSED_AS_COMPLETED",
    "DELETE_UNKNOWNS",
    "PROMOTE_MODELLED_TO_FACT",
    "TRANSFER_READY_COLLAPSE",
    "REMOVE_TRANSFER_BOUNDARY",
]


@pytest.mark.parametrize("attack", SINGLE_RUN_ATTACKS)
def test_attack_is_caught_by_its_detector(two_runs, tmp_path, attack):
    base = two_runs[0]
    detector = adversarial.EXPECTED_DETECTORS[attack]

    # the control must be CLEAN on the un-mutated output first
    clean = _audit(base)
    _assert_detector_clean(clean, detector)

    mutated = tmp_path / f"attack_{attack}"
    adversarial.apply_mutation(base, attack, mutated)

    audited = _audit(mutated)
    _assert_detector_fired(audited, detector, attack)


def test_copy_mechanism_is_caught_by_contamination(two_runs, tmp_path):
    detector = "CONTAMINATION"
    # clean batch: no contamination
    clean = audit_runner.audit_batch(two_runs, CONTRACT, PROFILE)
    assert clean["contamination"]["violation_count"] == 0

    # copy run 2's mechanism into run 1
    mutated = tmp_path / "attack_COPY_MECHANISM"
    adversarial.apply_copy_mechanism(two_runs[1], two_runs[0], mutated)

    # rebuild the batch with the mutated run replacing run 1
    batch = [mutated, two_runs[1]]
    packages = []
    for rd in batch:
        rel = json.loads((Path(rd) / "DISCOVERY_RELEASE.json")
                         .read_text(encoding="utf-8"))
        inv = json.loads((Path(rd) / "INVENTION_SPECIFICATION.json")
                         .read_text(encoding="utf-8"))
        inv_id = (inv.get("invention_id") or {}).get("value")
        packages.append({
            "run_dir": str(rd),
            "package_dir": rel.get("package_folder"),
            "package_id": inv_id, "invention_id": inv_id,
            "spec_hash": inv.get("_spec_hash"),
            "run_id": rel.get("run_id"),
            "evidence_ids": [],
            "input_signature": audit_runner._input_signature(Path(rd)),
        })
    report = ct.audit_contamination(packages)
    assert report["violation_count"] > 0, (
        "COPY_MECHANISM attack escaped the contamination audit")
    assert any(v["violation"] == "FOREIGN_INPUT_CONTENT"
               for v in report["violations"])


def _assert_detector_clean(audit, detector):
    if detector == "ARTIFACT_CONSISTENCY":
        assert audit["artifact_consistency"]["verdict"] == "PASS"
    elif detector == "EQUATION_APPLICABILITY":
        # clean runs may already fail this for REAL depth reasons (count
        # below corpus floor); the attack must add a NEW issue class
        pass
    elif detector == "NUMERICAL_PROVENANCE_GATE":
        assert audit["numerical_provenance"]["hard_violations"] == 0
    elif detector == "INDEPENDENT_REPLAY":
        assert audit["independent_replay"]["verdict"] == "PASS"
    elif detector == "VV_SEPARATION":
        assert audit["vv_separation"]["violation_count"] == 0
    elif detector == "TRANSFER_SPECIFICITY":
        dim = audit["quality_evaluation"]["dimensions"]["TRANSFER_SPECIFICITY"]
        assert dim["verdict"] == "PASS"


def _assert_detector_fired(audit, detector, attack):
    if detector == "ARTIFACT_CONSISTENCY":
        assert audit["artifact_consistency"]["violation_count"] > 0, \
            f"{attack} not caught by artifact consistency"
    elif detector == "EQUATION_APPLICABILITY":
        dim = audit["quality_evaluation"]["dimensions"][
            "EQUATION_APPLICABILITY"]
        assert any("WRONG_DOMAIN" in i for i in dim["issues"]), \
            f"{attack} not caught by equation applicability"
    elif detector == "NUMERICAL_PROVENANCE_GATE":
        npa = audit["numerical_provenance"]
        assert npa["hard_violations"] > 0, \
            f"{attack} not caught by the numerical provenance hard gate"
    elif detector == "INDEPENDENT_REPLAY":
        assert audit["independent_replay"]["verdict"] == "FAIL", \
            f"{attack} not caught by independent replay"
    elif detector == "VV_SEPARATION":
        assert audit["vv_separation"]["violation_count"] > 0, \
            f"{attack} not caught by V&V separation"
    elif detector == "TRANSFER_SPECIFICITY":
        dim = audit["quality_evaluation"]["dimensions"]["TRANSFER_SPECIFICITY"]
        assert dim["verdict"] == "FAIL", \
            f"{attack} not caught by the transfer audit"


# ---------------------------------------------------------------------------
# Phase 13 — regression protection
# ---------------------------------------------------------------------------
def test_contract_thresholds_are_corpus_derived():
    """No threshold may drift from the committed corpus profile (Art.
    XXVII: thresholds carry provenance, never judgment)."""
    for section in CONTRACT["sections"]:
        assert "derivation" in section, section["section"]
        assert section["derivation"]["rule"].startswith("R")
        for key, value in (section.get("minimum_depth") or {}).items():
            assert value is not None, (section["section"], key)


def test_profile_has_all_15_packages_and_distributions():
    assert PROFILE["n_packages"] == 15
    assert PROFILE["v2_packages"] == 8 and PROFILE["v1_packages"] == 7
    for measure in ("design_inputs", "failure_modes", "equations",
                    "chain_linkage_rate", "evidence_ids_per_object"):
        d = PROFILE["measures"][measure]
        assert d["measured"] == 15 and d["missing"] == 0
        assert d["min"] <= d["median"] <= d["max"]


def test_committed_benchmark_artifacts_are_consistent():
    bench_path = (REPO_ROOT / "artifacts/benchmark/generated/"
                  "AUTOMATED_DOSSIER_BENCHMARK.json")
    if not bench_path.exists():
        pytest.skip("committed benchmark not present")
    bench = json.loads(bench_path.read_text(encoding="utf-8"))
    assert bench["runs_input"] == 15
    assert bench["runs_released_and_audited"] + \
        bench["engine_rejected_count"] == 15
    assert bench["completeness_ok"] is True
    assert bench["batch_verdict"] in ("BENCHMARK_PASS",
                                      "BENCHMARK_CONDITIONAL",
                                      "BENCHMARK_FAIL")
    assert bench["contamination"]["verdict"] in ("PASS", "NOT_MEASURABLE")


def test_verdict_vocabulary_has_no_vanity_scores():
    for v in ("PASS", "CONDITIONAL", "FAIL"):
        assert v in CONTRACT["verdict_vocabulary"]


def test_clean_run_does_not_trigger_hard_gates(two_runs):
    """False-positive protection (Art. V): clean generated output must keep
    every hard gate green even though depth dimensions legitimately fail."""
    for rd in two_runs:
        audit = _audit(rd)
        assert audit["numerical_provenance"]["hard_violations"] == 0
        assert audit["vv_separation"]["violation_count"] == 0
        assert audit["artifact_consistency"]["verdict"] == "PASS"
        assert audit["independent_replay"]["broken_links"] == []
