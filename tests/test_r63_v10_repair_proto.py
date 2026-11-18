#!/usr/bin/env python3
"""Offline tests for the V10 repair-loop prototype (claim c-0086).

ZERO LLM PROBES (direction 1: the 429 window stays dark): gen_fn,
critic_fn and gate_fn are stubs; the deterministic scan stack is the
REAL production composition (byte-reuse proven by identity). What is
under test is the STRATEGY: targeted directives, the convergence guard,
the value ledger — and the freeze discipline (budget constant 3,
imported, never redefined).
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from r63_machine_v10_proto import (  # noqa: E402
    REPAIR_BUDGET_V10, finding_signature, machine_generate_v10_proto,
    targeted_directive, v10_scan_stack)
import r40_machine_v77  # noqa: E402


def _prob():
    d = json.loads((REPO / "eval" / "dev_holdout_problems"
                    / "holdout_v2_problems.burned_dev.json")
                   .read_text(encoding="utf-8"))
    return d["problems"][0]


def _clean_critic(final):
    return {"verdict": "CLEAN", "checks": []}


def _flag_critic(final):
    return {"verdict": "FLAG",
            "checks": [{"verdict": "FLAG", "anchor": "PHYSICS CHECK"}]}


def _match_gate(final, prob):
    return {"verdict": "MATCH", "reason": "stub"}


# ---- stub scan stacks (the loop-logic tests inject these; the REAL
# stack is exercised separately in t8) ----

def scans_always_same(prob, final, used=None):
    """A stuck axis: one finding, forever (the V7.7 failure mode)."""
    return {"MECHANISM_CLASS_UNSTATED": ["no MECHANISM CLASS line"]}


class _SwappingScans:
    """Repairs change the finding set but never reduce the load:
    one finding is swapped for another each pass (delta 0, 0, ...)."""

    def __init__(self):
        self.n = 0
        self.keys = ("MECHANISM_CLASS_UNSTATED", "UNPRICED_DUTY_CYCLE",
                     "INPUT_UNAVAILABLE", "CONSTRAINT_EXCLUSION",
                     "STANDARD_BILL")

    def __call__(self, prob, final, used=None):
        k = self.keys[self.n % len(self.keys)]
        self.n += 1
        return {k: ["swapped finding"]}


def _ImprovingScans(loads):
    """loads[i] = violation count at attempt i (findings shrink); key
    names rotate per attempt so the finding SET differs every time
    (only the load shrinks — a genuinely improving, non-stuck axis)."""
    state = {"i": 0}

    def fn(prob, final, used=None):
        i = state["i"]
        n = loads[min(i, len(loads) - 1)]
        state["i"] += 1
        return {f"FINDING_{i}_{j}": ["x"] for j in range(n)}
    return fn


def test_1_clean_path_zero_repairs():
    attempts = {"n": 0}

    def gen(q):
        attempts["n"] += 1
        return "a perfect bill"
    final, att, meta = machine_generate_v10_proto(
        _prob(), gen, _clean_critic, _match_gate,
        scans_fn=lambda p, f, u=None: {})
    assert meta["repairs"] == 0 and meta["convergence"] == "CLEAN"
    assert meta["residual_findings"] == {}
    assert attempts["n"] == 1, "the CLEAN path must not churn"
    assert len(att) == 1 and att[0]["stage"] == "draft"


def test_2_stuck_axis_stops_after_one_repair():
    """The V7.7 failure mode, fixed: the same finding set twice in a
    row is a STUCK AXIS — typed EARLY_STOP, budget preserved."""
    calls = {"n": 0}

    def gen(q):
        calls["n"] += 1
        return f"bill draft {calls['n']}"
    final, att, meta = machine_generate_v10_proto(
        _prob(), gen, _flag_critic, _match_gate,
        scans_fn=scans_always_same)
    assert meta["convergence"] == "STUCK_AXIS", meta
    assert meta["repairs"] == 1, meta
    assert len(att) == 2, "stop BEFORE re-rolling the stuck axis again"
    assert meta["residual_findings"], "residuals stay disclosed"
    assert meta["critic_verdict"] == "FLAG"


def test_3_no_marginal_value_stops_before_budget():
    """Two consecutive value-zero repairs (finding swaps, load flat)
    -> EARLY_STOP:NO_MARGINAL_VALUE before the last budget slot."""
    final, att, meta = machine_generate_v10_proto(
        _prob(), lambda q: f"bill {len(q) % 7}", _clean_critic,
        _match_gate, scans_fn=_SwappingScans())
    assert meta["convergence"] == "NO_MARGINAL_VALUE", meta
    assert meta["repairs"] == 2, meta
    deltas = [a["value"]["value_delta"] for a in att[1:]]
    assert deltas == [0, 0], deltas


def test_4_budget_exhausted_when_improving():
    """Findings shrink every attempt but never reach zero: the loop
    legitimately runs to the (unchanged) budget and types it."""
    final, att, meta = machine_generate_v10_proto(
        _prob(), lambda q: f"bill {len(q) % 5}", _clean_critic,
        _match_gate, scans_fn=_ImprovingScans([3, 2, 1, 1, 1]))
    assert meta["convergence"] == "BUDGET_EXHAUSTED", meta
    assert meta["repairs"] == 3 == REPAIR_BUDGET_V10
    assert att[1]["value"]["value_delta"] < 0, "repair 1 improved"
    assert att[2]["value"]["value_delta"] < 0, "repair 2 improved"


def test_5_directive_is_targeted_not_megastack():
    from r40_v77_directive import V77_REPAIR_DIRECTIVE
    vio = {"INPUT_UNAVAILABLE": ["online surface-charge sensing"],
           "UNPRICED_DUTY_CYCLE": ["throughput modulation unpriced"]}
    d = targeted_directive(vio, ["PHYSICS CHECK"], False)
    assert "BYTE-KEEP CONSTRAINT" in d
    assert "INPUT_UNAVAILABLE" in d and "re-choose the mechanism" in d
    assert "UNPRICED_DUTY_CYCLE" in d and "OPERATIONAL COST line" in d
    assert "PHYSICS CHECK" in d, "critic anchors carried"
    # the full static stack is NOT re-quoted (the V7.7 defect)
    assert "THE DIRECTION-CORRECTNESS CLAUSE" not in d
    assert len(d) < len(V77_REPAIR_DIRECTIVE) // 2


def test_6_scan_stack_is_byte_reused():
    import r63_machine_v10_proto as proto
    assert proto.scan_input_availability is \
        r40_machine_v77.scan_input_availability
    assert proto.scan_duty_cycle_pricing is \
        r40_machine_v77.scan_duty_cycle_pricing
    assert proto.scan_mechanism_template is \
        r40_machine_v77.scan_mechanism_template
    assert proto.base_scan is r40_machine_v77.base_scan


def test_7_budget_constant_untouched():
    assert REPAIR_BUDGET_V10 == r40_machine_v77.REPAIR_BUDGET == 3
    assert "REPAIR_BUDGET_V10 = REPAIR_BUDGET" in (
        Path(REPO / "scripts" / "r63_machine_v10_proto.py")
        .read_text(encoding="utf-8"))


def test_8_real_scan_stack_runs_on_holdout_problem():
    """The production scan composition executes on a real problem
    without raising (zero probes; the loop then treats its verdict)."""
    prob = _prob()
    vio = v10_scan_stack(prob, "MECHANISM CLASS: thermal shock test")
    assert isinstance(vio, dict)
    final, att, meta = machine_generate_v10_proto(
        prob, lambda q: "MECHANISM CLASS: thermal shock test",
        _clean_critic, _match_gate, scans_fn=v10_scan_stack)
    assert set(meta) >= {"critic_verdict", "repairs",
                         "residual_findings", "convergence"}
    assert meta["repairs"] <= REPAIR_BUDGET_V10


def test_9_signature_excludes_empty_and_carries_critic():
    s1 = finding_signature({"A": []}, ["PHYSICS CHECK"], False)
    assert s1 == frozenset({"CRITIC::PHYSICS CHECK"})
    s2 = finding_signature({"A": ["x"]}, [], True)
    assert "A" in s2 and "GATE::MISMATCH" in s2


