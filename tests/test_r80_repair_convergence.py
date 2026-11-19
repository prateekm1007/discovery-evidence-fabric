#!/usr/bin/env python3
"""R80 CI-wired acceptance tests for the repair-loop CONVERGENCE prototype
(scripts/r80_repair_convergence.py — Reflexion reflection-memory + Self-Refine
structured stop, patterns only). Deterministic, zero-LLM, zero-network
(Art. 22: fixtures prove MECHANICS only; the >=50%-on-sealed-rows convergence
gate stays with the next sealed measurement — this suite proves the layer
converges when the row improves, stops only on provably non-improving
repeats, and never moves a frozen byte)."""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    "r80c", REPO / "scripts" / "r80_repair_convergence.py")
r80c = importlib.util.module_from_spec(spec)
sys.modules["r80c"] = r80c
spec.loader.exec_module(r80c)


def _attempt(scan_vios, disclosed=(), critic="FLAG", tg=None):
    return {"critic_verdict": critic,
            "type_gate": tg or {"verdict": "CLEAN"},
            "scan": scan_vios,
            "findings_disclosed": list(disclosed)}


def _model(seq):
    """A deterministic row model: attempt i returns seq[i] (problems as a
    scan-violations dict); never self-declares done — convergence is the
    clean-problems path, exactly like the frozen machine."""
    def model(i, note):
        return _attempt(seq[min(i, len(seq) - 1)]), False
    return model


# ------------------------------------------------------------ signature
def test_signature_is_order_insensitive_and_stable():
    a = _attempt({"BILL_UNTAGGED": ["x", "y"]}, ["z"])
    b = _attempt({"BILL_UNTAGGED": ["y", "x"]}, ["z"])
    assert r80c.failure_signature(a) == r80c.failure_signature(b)
    c = _attempt({"BILL_UNTAGGED": ["x"]}, ["z"])
    assert r80c.failure_signature(c) != r80c.failure_signature(a)


def test_clean_attempt_has_empty_problem_set():
    assert r80c._attempt_problems(_attempt({}, critic="CLEAN")) == []


# -------------------------------------------------------------- memory
def test_memory_note_carries_lesson_text_and_dedupes():
    m = r80c.ReflectionMemory()
    e1 = m.observe(_attempt({"BILL_UNTAGGED": ["q1"]}))
    assert e1 and any("untagged" in t for t in e1["lessons"])
    assert m.observe(_attempt({"BILL_UNTAGGED": ["q1"]})) is None  # same sig
    e2 = m.observe(_attempt({"PREDICTOR_VIOLATION": ["v"]}))
    assert e2 and any("leading indicators" in t for t in e2["lessons"])
    note = m.note()
    assert "PRIOR-ATTEMPT REFLECTION" in note and "untagged" in note


def test_directive_enrichment_appends_note_and_keeps_base_template():
    m = r80c.ReflectionMemory()
    m.observe(_attempt({"DEV_NEED": ["n1"]}))
    base = "REPAIR (findings: {findings})"
    d = r80c.build_repair_directive(["DEV_NEED:x"], m, base)
    assert "REPAIR (findings: DEV_NEED:x)" in d
    assert "PRIOR-ATTEMPT REFLECTION" in d and "need" in d.lower()
    m2 = r80c.ReflectionMemory()
    d2 = r80c.build_repair_directive(["DEV_NEED:x"], m2, base)
    assert d2 == "REPAIR (findings: DEV_NEED:x)"  # no memory -> no note


# ---------------------------------------------------------- stop criterion
def test_stop_never_fires_on_draft_or_clean_or_improving():
    a0 = _attempt({"BILL_UNTAGGED": ["x"]})
    assert not r80c.should_stop([a0])                    # draft only
    clean = _attempt({}, critic="CLEAN")
    assert not r80c.should_stop([a0, clean])             # clean = converged
    better = _attempt({"BILL_UNTAGGED": ["x"]})          # fewer problems
    worse = _attempt({"BILL_UNTAGGED": ["x"], "DEV_NEED": ["y"]})
    assert not r80c.should_stop([worse, better])         # improved -> keep going


def test_stop_fires_only_on_exact_signature_repeat():
    a = _attempt({"BILL_UNTAGGED": ["x"]})
    assert r80c.should_stop([a, a]) is True              # provably non-improving


# ----------------------------------------------------- loop acceptance set
def _row_improving(i, note):
    seq = [{"BILL_UNTAGGED": ["a"], "DEV_NEED": ["b"]},
           {"BILL_UNTAGGED": ["a"]},
           {}]
    return _attempt(seq[min(i, len(seq) - 1)]), False


def _row_nonimproving(i, note):
    return _attempt({"BILL_UNTAGGED": ["a"]}), False


def _row_churn(i, note):
    seq = [{"BILL_UNTAGGED": ["a"]},
           {"PREDICTOR_VIOLATION": ["b"]},
           {"BILL_UNTAGGED": ["a"], "PREDICTOR_VIOLATION": ["b"]},
           {"REASONING_THRASH_LEAK": ["c"]}]
    return _attempt(seq[min(i, len(seq) - 1)]), False


def _row_clean_draft(i, note):
    return _attempt({}, critic="CLEAN"), False


FIXTURES = {"clean_draft": _row_clean_draft,
            "improving": _row_improving,
            "nonimproving_repeat": _row_nonimproving,
            "churn": _row_churn}


def test_acceptance_convergence_matches_or_beats_baseline_on_every_row():
    results = {}
    for name, model in FIXTURES.items():
        base = r80c.run_loop(model, budget=3, convergence=False)
        conv = r80c.run_loop(model, budget=3, convergence=True)
        results[name] = (base, conv)
        # safety: the layer NEVER uses more repairs than the baseline
        assert conv["repairs_used"] <= base["repairs_used"], name
        # safety: convergence is never lost where the baseline converged
        assert conv["converged"] >= base["converged"], name
        # the stop criterion never fires an improving row into non-convergence
        if base["converged"]:
            assert conv["converged"], name + " (stop killed a converging row)"
    # the headline mechanics result on DEV fixtures: the non-improving
    # repeat stops early instead of burning the full budget (the measured
    # 86.7% burn class), and no row regresses.
    base_burn = sum(1 for b, _ in results.values() if b["budget_burned_full"])
    conv_burn = sum(1 for _, c in results.values() if c["budget_burned_full"])
    assert conv_burn < base_burn, (base_burn, conv_burn)
    b, c = results["nonimproving_repeat"]
    assert b["budget_burned_full"] and not c["budget_burned_full"]
    assert c["repairs_used"] < b["repairs_used"]
    # honest typing: the early stop SAVES budget, it does NOT claim the row
    # converged (the row stays unresolved — disclosed, never hidden)
    assert not c["converged"] and c["attempts"] == 2


# ------------------------------------------------------------ freeze guard
def test_frozen_baselines_untouched():
    rec = json.loads((REPO / "eval" / "r64_v9_preflight.json").read_text())
    fb = rec["checks"]["freeze_baselines_sha16"]
    for f, expected in fb.items():
        got = hashlib.sha256((REPO / f).read_bytes()).hexdigest()[:16]
        assert got == expected, f"the frozen file {f} MOVED (typed abort)"


def test_module_is_zero_network():
    src = (REPO / "scripts" / "r80_repair_convergence.py").read_text()
    for banned in ("import socket", "import requests", "import urllib",
                   "import http", "urlopen", "subprocess"):
        assert banned not in src, f"zero-network violation: {banned}"
