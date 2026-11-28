"""tests/test_r6_delivery_funnel.py — owner audit round 2026-11-13 P1.

Pins the durable five-level delivery accounting in eval/run.py:

  delivered -> contract_valid -> evidence_supported ->
  engineering_validated -> discovery_survivor

and the provider instrumentation (attempts, retries, tokens,
transport failures, per-stage LLM wall time) read from the run's own
routing-ledger slice.

What is pinned:
  1. The levels are SEPARATE: an invalid-delivered answer is delivered
     but not contract-valid, and no stronger level is ever True on a
     failed weaker level.
  2. Each level is three-valued: a missing/unreadable durable source is
     UNKNOWN (None), never silently False and never rounded up.
  3. Each decision is bound to the exact record bytes (sha256).
  4. Provider instrumentation is DERIVED from ledger lines: attempts
     from generate spans, retries = attempts-1, transport failures from
     the typed failure class / ok flag, tokens only when reported (no
     estimation).
  5. The table summary keeps True counts and UNKNOWN counts apart.

Hermetic: temp dirs only; zero network, zero LLM.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import eval.run as ev  # noqa: E402


def _write(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj), encoding="utf-8")


def _composed(d: Path, *, state: str, answer, valid) -> None:
    _write(d / "pipeline" / "ANSWER_COMPOSED.json", {
        "state": state,
        "answer": answer,
        "contract": {"valid": valid, "violations": []},
        "problem_id": "p1",
    })


def _completion(d: Path, *, evidence: bool, engineering: bool,
                survivor: bool) -> None:
    _write(d / "pipeline" / "COMPLETION_CONTRACT.json", {
        "components": {
            "evidence": {"complete": evidence},
            "engineering_model": {"complete": engineering},
        },
        "preconditions": {
            "EVIDENCE_BOUND": evidence,
            "AT_LEAST_ONE_ADMISSIBLE_SURVIVOR": survivor,
        },
    })


def test_all_five_levels_true_and_bound_to_bytes(tmp_path):
    d = tmp_path
    _composed(d, state="COMPOSED_CONTRACT_VALID",
              answer="A substantial delivered answer.", valid=True)
    _completion(d, evidence=True, engineering=True, survivor=True)
    out = ev.delivery_funnel(
        d, {}, {"state": "COMPOSED_CONTRACT_VALID",
                "answer": "A substantial delivered answer.",
                "contract": {"valid": True}, "problem_id": "p1"},
        "COMPOSED_CONTRACT_VALID", {"valid": True})
    assert out["schema"] == "r6_delivery_funnel/1.0.0"
    for lvl in ("delivered", "contract_valid", "evidence_supported",
                "engineering_validated", "discovery_survivor"):
        assert out["levels"][lvl]["state"] is True, lvl
    assert out["strongest_level"] == "discovery_survivor"
    for k, v in out["source_sha256"].items():
        assert isinstance(v, str) and len(v) == 64, k
    assert (out["levels"]["contract_valid"]
            ["agrees_with_eval_validator"] is True)


def test_invalid_delivered_is_not_contract_valid_or_stronger(tmp_path):
    d = tmp_path
    _composed(d, state="COMPOSED_CONTRACT_INVALID_DELIVERED",
              answer="Delivered with an open defect.", valid=False)
    # even a survivor record cannot promote the invalid delivery upward
    _completion(d, evidence=True, engineering=True, survivor=True)
    out = ev.delivery_funnel(
        d, {}, {"state": "COMPOSED_CONTRACT_INVALID_DELIVERED",
                "answer": "Delivered with an open defect.",
                "contract": {"valid": False}, "problem_id": "p1"},
        "COMPOSED_CONTRACT_INVALID_DELIVERED", {"valid": False})
    st = {k: v["state"] for k, v in out["levels"].items()}
    assert st["delivered"] is True
    assert st["contract_valid"] is False
    assert st["evidence_supported"] is False
    assert st["engineering_validated"] is False
    # survivor is an independent completion-contract fact and is not
    # laundered into answer validity
    assert st["discovery_survivor"] is True
    assert out["strongest_level"] == "discovery_survivor"


def test_missing_completion_contract_is_unknown_not_false(tmp_path):
    d = tmp_path
    _composed(d, state="COMPOSED_CONTRACT_VALID",
              answer="A substantial delivered answer.", valid=True)
    out = ev.delivery_funnel(
        d, {}, {"state": "COMPOSED_CONTRACT_VALID",
                "answer": "A substantial delivered answer.",
                "contract": {"valid": True}},
        "COMPOSED_CONTRACT_VALID", {"valid": True})
    st = {k: v["state"] for k, v in out["levels"].items()}
    assert st["delivered"] is True
    assert st["contract_valid"] is True
    assert st["evidence_supported"] is None
    assert st["engineering_validated"] is None
    assert st["discovery_survivor"] is None
    assert out["source_sha256"]["COMPLETION_CONTRACT.json"] is None


def test_evidence_bound_but_engineering_incomplete(tmp_path):
    d = tmp_path
    _composed(d, state="COMPOSED_CONTRACT_VALID",
              answer="A substantial delivered answer.", valid=True)
    _completion(d, evidence=True, engineering=False, survivor=True)
    out = ev.delivery_funnel(
        d, {}, {"state": "COMPOSED_CONTRACT_VALID",
                "answer": "A substantial delivered answer.",
                "contract": {"valid": True}},
        "COMPOSED_CONTRACT_VALID", {"valid": True})
    st = {k: v["state"] for k, v in out["levels"].items()}
    assert st["evidence_supported"] is True
    assert st["engineering_validated"] is False


def test_no_composer_record_is_not_delivered():
    out = ev.delivery_funnel(Path("/nonexistent-problem-dir"), {}, {}, None,
                             {})
    st = {k: v["state"] for k, v in out["levels"].items()}
    assert st["delivered"] is False
    assert st["contract_valid"] is False
    assert st["evidence_supported"] is False
    assert st["discovery_survivor"] is None


def test_provider_instrumentation_missing_ledger_is_honest(tmp_path):
    out = ev.provider_instrumentation(tmp_path)
    assert out["state"] == "NOT_INSTRUMENTED"
    assert out["n_provider_attempts"] is None
    assert out["tokens"]["state"] == "NOT_REPORTED"
    assert out["transport_failures"] is None


def test_provider_instrumentation_counts_attempts_retries_tokens(tmp_path):
    d = tmp_path
    _write(d / "pipeline" / "ROUTING_LEDGER_RUN.json", {
        "lines": [
            {
                "provider": "p1", "engine_stage": "SYNTHESIZE",
                "ok": True, "status": "OK", "attempt": 2,
                "tokens": {"prompt_tokens": 100,
                           "completion_tokens": 40,
                           "total_tokens": 140},
                "generate_spans": {
                    "generate_elapsed_s": 2.5,
                    "rungs": [{"attempts": [{}, {}]}],
                },
            },
            {
                "provider": "p2", "engine_stage": "ATTACK",
                "ok": False, "status": "PROVIDER_FAILURE",
                "failure_class": "RATE_LIMITED", "attempt": 1,
                "tokens": None,
                "fallback_to": "p1",
                "generate_spans": {
                    "generate_elapsed_s": 1.25,
                    "rungs": [{"attempts": [{}]}],
                },
            },
        ],
    })
    out = ev.provider_instrumentation(d)
    assert out["state"] == "INSTRUMENTED"
    assert out["n_logical_calls"] == 2
    assert out["n_provider_attempts"] == 3
    assert out["n_retries"] == 1
    assert out["n_fallbacks"] == 1
    assert out["transport_failures"] == 1
    assert out["failure_classes"] == {"RATE_LIMITED": 1}
    assert out["providers"] == {"p1": 1, "p2": 1}
    assert out["tokens"]["state"] == "REPORTED"
    assert out["tokens"]["total"] == 140
    assert out["tokens"]["n_lines_missing"] == 1
    assert out["per_stage_llm_wall_s"] == {"SYNTHESIZE": 2.5,
                                           "ATTACK": 1.25}


def test_tokens_are_never_estimated(tmp_path):
    d = tmp_path
    _write(d / "pipeline" / "ROUTING_LEDGER_RUN.json", {
        "lines": [{"provider": "p1", "engine_stage": "SYNTHESIZE",
                   "ok": True, "status": "OK", "tokens": None,
                   "generate_spans": {"rungs": [{"attempts": [{}]}]}}],
    })
    out = ev.provider_instrumentation(d)
    assert out["tokens"]["state"] == "NOT_REPORTED"
    assert out["tokens"]["total"] is None
    assert out["tokens"]["n_lines_reported"] == 0


def test_summary_keeps_true_and_unknown_apart():
    rows = [
        {"delivery_funnel": {"levels": {
            "delivered": {"state": True},
            "contract_valid": {"state": True},
            "evidence_supported": {"state": None},
            "engineering_validated": {"state": None},
            "discovery_survivor": {"state": False}}}},
        {"delivery_funnel": {"levels": {
            "delivered": {"state": True},
            "contract_valid": {"state": False},
            "evidence_supported": {"state": False},
            "engineering_validated": {"state": False},
            "discovery_survivor": {"state": True}}}},
        {"provider_instrumentation": {
            "state": "INSTRUMENTED", "n_provider_attempts": 3,
            "n_retries": 1, "transport_failures": 1,
            "n_fallbacks": 0, "failure_classes": {"X": 1},
            "providers": {"p1": 2},
            "tokens": {"state": "REPORTED", "prompt": 10,
                       "completion": 5, "total": 15},
            "per_stage_llm_wall_s": {"SYNTHESIZE": 2.0}}},
    ]
    s = ev._delivery_funnel_summary(rows)
    assert s["counts"]["delivered"] == 2
    assert s["counts"]["contract_valid"] == 1
    assert s["counts"]["evidence_supported"] == 0
    assert s["unknown"]["evidence_supported"] == 1
    assert s["counts"]["discovery_survivor"] == 1
    assert s["n"] == 3
    assert s["n_with_funnel"] == 2
    p = ev._provider_instrumentation_summary(rows)
    assert p["states"] == {"INSTRUMENTED": 1}
    assert p["n_with_instrumentation"] == 1
    assert p["n_provider_attempts"] == 3
    assert p["n_retries"] == 1
    assert p["transport_failures"] == 1
    assert p["tokens"]["total"] == 15
    assert p["per_stage_llm_wall_s"] == {"SYNTHESIZE": 2.0}
