#!/usr/bin/env python3
"""tests/test_r106_panel_agreement.py — the CI fixtures for the
score-8 agreement instruments (engine panel_agreement.py + the
additive blind_panel quota/canary surfaces).

Art. 22: fixtures prove MECHANICS only — every expected number below
is hand-computable from the definitions in the module docstring.
Deterministic, zero-LLM, zero-network. The prereg parity pin reads
the committed eval/r106_score8_prereg.json bytes.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine import panel_agreement as pa          # noqa: E402
from discovery_fabric.engine import blind_panel as bp             # noqa: E402
from discovery_fabric.engine.blind_panel import (                 # noqa: E402
    PanelSeat, QuotaBudget, run_panel, serve_with_retry, scan_canary)


# ---------------------------------------------------------------------------
# Krippendorff alpha (hand-computed fixtures)
# ---------------------------------------------------------------------------
def test_alpha_perfect_agreement_is_one():
    units = [[1, 1, 1], [2, 2, 2], [1, 1, 1]]
    r = pa.krippendorff_alpha(units, "nominal")
    assert r["alpha"] == 1.0
    assert r["d_o"] == 0.0
    assert r["degenerate_class"] is None


def test_alpha_hand_computed_nominal():
    """Units [[1,1,2],[2,2,1]]: pooled {1:3, 2:3}, n'=6.
    D_o: per unit 4 disagreeing ordered pairs of 6 -> (4+4)/12 = 2/3.
    D_e: ordered cross pairs 9+9=18 of 30 -> 0.6.
    alpha = 1 - (2/3)/0.6 = 1 - 10/9 = -1/9."""
    r = pa.krippendorff_alpha([[1, 1, 2], [2, 2, 1]], "nominal")
    assert r["d_o"] == round(2 / 3, 6)
    assert r["d_e"] == 0.6
    assert r["alpha"] == round(1 - (2 / 3) / 0.6, 6)
    assert r["pooled_counts"] == {"1": 3, "2": 3}


def test_alpha_missing_values_drop_out():
    """None is missing, never zero: [[1,None,1],[2,2,None]] keeps two
    pairable units of k=2 each with perfect agreement -> alpha 1."""
    r = pa.krippendorff_alpha([[1, None, 1], [2, 2, None]], "nominal")
    assert r["alpha"] == 1.0
    assert r["n_pairable"] == 2


def test_alpha_interval_metric_hand_computed():
    """[[0, 2], [0, 2]]: D_o per unit = (0-2)^2+(2-0)^2 over 2 ordered
    pairs = 8/2 = 4; D_o = 4. Pooled {0:2, 2:2}, n'=4:
    D_e = (0*2*2^2 ... ordered cross pairs 2*2*4*2)/(4*3) = 32/12 = 8/3.
    alpha = 1 - 4/(8/3) = 1 - 1.5 = -0.5."""
    r = pa.krippendorff_alpha([[0, 2], [0, 2]], "interval")
    assert r["d_o"] == 4.0
    assert r["d_e"] == round(8 / 3, 6)
    assert r["alpha"] == -0.5


def test_alpha_degenerate_cases_typed():
    r = pa.krippendorff_alpha([[1], [None]], "nominal")
    assert r["alpha"] is None and r["degenerate_class"] == "no_pairable_units"
    # a single distinct pooled value: zero expected disagreement
    r2 = pa.krippendorff_alpha([[1, 1], [1]], "nominal")
    assert r2["alpha"] is None
    assert r2["degenerate_class"] == "zero_expected_disagreement"
    try:
        pa.krippendorff_alpha([[1, 2]], "spearman")
        assert False, "unknown metric must refuse"
    except ValueError as e:
        assert "typed refusal" in str(e)


# ---------------------------------------------------------------------------
# Proportion agreement / kappa / rho (hand-computed)
# ---------------------------------------------------------------------------
def test_proportion_agreement_hand_computed():
    r = pa.proportion_agreement([[1, 1, 2], [2, 1]])
    # pairs: unit1 (1,1) match, (1,2) no, (1,2) no; unit2 (2,1) no -> 1/4
    assert r["proportion"] == 0.25
    assert r["total_pairs"] == 4 and r["matching_pairs"] == 1


def test_cohen_kappa_hand_computed():
    """xs=[1,0,1,0], ys=[1,0,0,0]: obs = 3/4; expected = .5*.5+.5*.5=.5;
    kappa = (0.75-0.5)/0.5 = 0.5."""
    r = pa.cohen_kappa([1, 0, 1, 0], [1, 0, 0, 0])
    assert r["kappa"] == 0.5
    assert r["observed_agreement"] == 0.75
    assert r["degenerate_class"] is None


def test_cohen_kappa_degenerate():
    r = pa.cohen_kappa([1, 1, 1], [1, 1, 1])
    assert r["kappa"] is None and r["degenerate_class"] == "one_label_only"
    r2 = pa.cohen_kappa([1, None], [None, 0])
    assert r2["kappa"] is None and r2["degenerate_class"] == "no_complete_pairs"


def test_spearman_rho_hand_computed():
    r = pa.spearman_rho([1, 2, 3, 4], [10, 20, 30, 40])
    assert r["rho"] == 1.0
    r2 = pa.spearman_rho([1, 2, 3, 4], [4, 3, 2, 1])
    assert r2["rho"] == -1.0


def test_spearman_rho_ties_and_degenerate():
    # ties on both sides still compute (tie-corrected ranks)
    r = pa.spearman_rho([1, 1, 2, 2], [1, 2, 2, 1])
    assert r["rho"] is not None and -1.0 <= r["rho"] <= 1.0
    # zero-variance side -> typed None
    r2 = pa.spearman_rho([5, 5, 5], [1, 2, 3])
    assert r2["rho"] is None and r2["degenerate_class"] == "zero_variance_side"


# ---------------------------------------------------------------------------
# The preregistered consensus mapping
# ---------------------------------------------------------------------------
def _rt(no, known):
    return {"non_obviousness": no, "viability": 3,
            "recognizes_known_practice": known, "rationale": "r",
            "served_model": "m", "attempts": 1, "retry_used": False}


def test_consensus_mapping_both_conjuncts():
    served = [_rt(4, False), _rt(5, False), _rt(4, True)]
    c = pa.consensus_novel(served)
    # median = 4 (>= 4) AND known majority False (1 of 3) -> novel
    assert c["consensus_novel"] is True
    assert c["median_non_obviousness"] == 4
    assert c["known_majority"] is False
    assert c["component_no_alone"] and c["component_known_alone"]


def test_consensus_mapping_median_below_refuses():
    c = pa.consensus_novel([_rt(3, False), _rt(3, False), _rt(2, False)])
    assert c["consensus_novel"] is False
    assert c["median_non_obviousness"] == 3


def test_consensus_mapping_known_majority_refuses():
    """median >= 4 but 2 of 3 agents recognize the practice -> the
    second conjunct fails -> NOT novel (never a one-leg verdict)."""
    c = pa.consensus_novel([_rt(5, True), _rt(4, True), _rt(4, False)])
    assert c["consensus_novel"] is False
    assert c["component_no_alone"] is True
    assert c["component_known_alone"] is False


def test_consensus_missing_and_empty_typed():
    # typed error entries drop out; missing shapes drop out
    mixed = [{"error": "QUOTA_REFUSED: x", "agent": "A1"},
             _rt(4, False), _rt(5, False)]
    c = pa.consensus_novel(mixed)
    assert c["consensus_novel"] is True and c["n_served"] == 2
    empty = pa.consensus_novel([{"error": "x", "agent": "A1"}])
    assert empty["consensus_novel"] is None
    assert empty["degenerate_class"] == "no_served_ratings"


# ---------------------------------------------------------------------------
# The composed panel-vs-gate cross-check
# ---------------------------------------------------------------------------
def test_panel_gate_agreement_hand_computed():
    panel = {
        "r1": [_rt(4, False), _rt(5, False)],
        "r2": [_rt(2, True), _rt(3, True)],
        "r3": [_rt(4, True), _rt(5, True)],    # median ok, known-maj True
        "r4": [_rt(1, False), _rt(2, False)],
        "r5": [{"error": "x", "agent": "A1"}],  # no served -> excluded
        "r6": [_rt(5, False)],
    }
    gate = {"r1": True, "r2": False, "r3": True, "r4": False,
            "r7": True}
    r = pa.panel_gate_agreement(panel, gate)
    # shared = panel ∩ gate = {r1, r2, r3, r4} (r5 no served ratings
    # stays in shared but is consensus-None; r6 is panel-only; r7
    # gate-only)
    assert r["n_shared"] == 4
    assert set(r["shared_row_ids"]) == {"r1", "r2", "r3", "r4"}
    assert r["excluded_panel_only"] == ["r5", "r6"]
    assert r["excluded_gate_only"] == ["r7"]
    # scored pairs: r1 (T,T) tp; r2 (F,F) tn; r3 (F,T) fn; r4 (F,F) tn
    assert r["n_scored_pairs"] == 4
    assert r["confusion"] == {"true_positive": 1, "false_positive": 0,
                              "false_negative": 1, "true_negative": 2}
    assert r["proportion_agreement"] == 0.75


def test_panel_gate_agreement_empty_typed():
    r = pa.panel_gate_agreement({}, {})
    assert r["n_shared"] == 0 and r["proportion_agreement"] is None


# ---------------------------------------------------------------------------
# Prereg parity (the mapping constants pinned against the JSON bytes)
# ---------------------------------------------------------------------------
def test_prereg_constants_pinned():
    src = subprocess.run(
        ["git", "show", "HEAD:eval/r106_score8_prereg.json"],
        capture_output=True, cwd=str(REPO))
    if src.returncode != 0:
        src_bytes = (REPO / "eval/r106_score8_prereg.json").read_bytes()
    else:
        src_bytes = src.stdout
    prereg = json.loads(src_bytes)
    m = prereg["agreement_preregistration"]["panel_vs_gate_cross_check"]
    assert ">= 4" in m["consensus_mapping_preregistered"]
    assert pa.CONSENSUS_NO_MIN == 4
    assert pa.CONSENSUS_KNOWN_MAJORITY is False
    q = prereg["quota_budget_preregistration"]
    assert q["ceiling_tokens"] == 150000
    assert "256" in q["per_serve_estimate_arithmetic"]
    assert "320" in q["per_serve_estimate_arithmetic"]


# ---------------------------------------------------------------------------
# Canary sweep + the prompt assert (the P4 canary clause surface)
# ---------------------------------------------------------------------------
def test_scan_canary_finds_and_cleans():
    hits = scan_canary("answer for HO15-01-jet-dye-unlevel in holdout v15")
    pats = {h["pattern"] for h in hits}
    assert any("HO[" in p for p in pats)
    assert "holdout" in pats
    assert scan_canary("a clean rating rationale sentence") == []


def test_built_prompt_carries_no_canary_pattern():
    prob = {"device": "desalter", "failure": "emulsion",
            "question": "predict", "user_variables": "T=80C"}
    p = bp.build_rating_prompt(prob, "use HO15-07 style magnet rod")
    assert "[redacted-id]" in p and "HO15" not in p
    assert scan_canary(p) == []


# ---------------------------------------------------------------------------
# The additive per-serve quota kwarg (transport-honest accounting)
# ---------------------------------------------------------------------------
def _fake_serve_ok(agent, prompt):
    return (json.dumps({"non_obviousness": 3, "viability": 4,
                        "rationale": "ok",
                        "recognizes_known_practice": False}),
            agent["model"])


def test_per_serve_estimate_accounting_recorded():
    seats = [PanelSeat("A1", "cohere", "cohere/command-a", "xkiro", 512),
             PanelSeat("A3", "z-ai-sdk", "z-ai chat", "zai-cli", 512)]
    rows = {"r1": "s1", "r2": "s2"}
    probs = {r: {"device": "d", "failure": "f", "question": "q",
                 "user_variables": "u"} for r in rows}
    budget = QuotaBudget(ceiling_tokens=100)
    rec = run_panel(seats, rows, probs, _fake_serve_ok, budget=budget,
                    per_row_token_estimate=999,
                    per_serve_estimate=lambda s: 0 if s.transport == "zai-cli"
                    else 60)
    assert budget.spent_tokens == 60
    assert budget.refusals == 1
    # A3 served BOTH rows (never budget-limited): agents_served has A3
    assert "A3" in rec["panel_valid"]["agents_served"]
    # the r2 A1 entry carries the typed quota refusal
    refused = [e for e in rec["ratings"]
               if "QUOTA_REFUSED" in e["ratings"]["A1"].get("error", "")]
    assert len(refused) == 1


def test_scalar_path_unchanged_default():
    """The default (no per_serve_estimate) preserves the committed
    scalar behavior byte-for-byte: the scalar estimate applies to
    EVERY seat."""
    seats = [PanelSeat("A1", "cohere", "cohere/command-a", "xkiro", 512)]
    rows = {"r1": "s1"}
    probs = {"r1": {"device": "d", "failure": "f", "question": "q",
                    "user_variables": "u"}}
    budget = QuotaBudget(ceiling_tokens=50)
    rec = run_panel(seats, rows, probs, _fake_serve_ok, budget=budget,
                    per_row_token_estimate=60)
    # 0 + 60 > 50 -> the serve is refused BEFORE it happens; the
    # budget never moves (spent 0), the refusal is typed.
    assert budget.spent_tokens == 0
    assert budget.refusals == 1
    assert "QUOTA_REFUSED" in rec["ratings"][0]["ratings"]["A1"]["error"]


def test_retry_accounts_within_one_estimate():
    """The estimate covers ONE serve-with-retry cycle (up to 2
    attempts): the retry is INSIDE serve_with_retry, the budget
    accounting wraps the cycle. The conservatism for the retry class
    comes from the allowance headroom (256/320 vs the ~80-150-token
    measured reply class), and the record discloses the REAL usage —
    the budget never under-counts below the pre-registered estimate."""
    calls = {"n": 0}

    def flaky(agent, prompt):
        calls["n"] += 1
        if calls["n"] == 1:
            return ("not json at all", agent["model"])
        return _fake_serve_ok(agent, prompt)

    seats = [PanelSeat("A1", "cohere", "cohere/command-a", "xkiro", 512)]
    rows = {"r1": "s1"}
    probs = {"r1": {"device": "d", "failure": "f", "question": "q",
                    "user_variables": "u"}}
    budget = QuotaBudget(ceiling_tokens=200)
    rec = run_panel(seats, rows, probs, flaky, budget=budget,
                    per_row_token_estimate=60)
    assert budget.spent_tokens == 60
    assert rec["ratings"][0]["ratings"]["A1"]["retry_used"] is True


# ---------------------------------------------------------------------------
# Determinism (Art. 15: canonical serialization across hash seeds)
# ---------------------------------------------------------------------------
def test_canonical_record_deterministic():
    r = pa.panel_gate_agreement(
        {"a": [_rt(4, False)]}, {"a": True})
    s1 = pa.canonical_json(r)
    s2 = pa.canonical_json(r)
    assert s1 == s2
    assert s1 == json.dumps(r, indent=1, ensure_ascii=False,
                            sort_keys=True)
