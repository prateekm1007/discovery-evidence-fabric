"""tests/test_tool_grounded_critic_v14.py — the c-0109 v14
water-domain vocabulary CI (AM91, claim c-0116): the mined typed
rules behave per their procurement semantics on the burned-cluster
fixtures, and the DEV-only convergence gate (>=50% of the 21
non-converged rows reach zero residual findings) holds on the
committed bytes (deterministic, zero LLM)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from discovery_fabric.engine import tool_grounded_critic as tgc  # noqa


def test_burden_ledger_zero_assertion_is_a() -> None:
    assert tgc.classify_bill_row(
        "*   **Procurement Burden:** Zero. No new parts purchased.") \
        == "a"


def test_burden_ledger_consequence_is_c() -> None:
    assert tgc.classify_bill_row(
        "*   **Throughput:** Reduced by 20\u201325% during the "
        "implementation window. This is the cost of the "
        "intervention.") == "c"


def test_test_protocol_label_is_c() -> None:
    assert tgc.classify_bill_row(
        "*   **Pass/Fail**: Fail if the NO3 indicator rises above "
        "0.5 mg/L within 14 days.") == "c"
    assert tgc.classify_bill_row(
        "*   **Kill Criterion**: If anammox activity declines >10%, "
        "halt the test.") == "c"


def test_configuration_on_existing_is_c() -> None:
    assert tgc.classify_bill_row(
        "*   *Basis*: Change to operating point/procedure on "
        "existing equipment.") == "c"
    assert tgc.classify_bill_row(
        "- **Detail:** Utilize existing DCS/HMI alarm panel to "
        "display \"SLUDGE BUILDUP RISK\". No new displays.") == "c"


def test_input_label_is_a() -> None:
    assert tgc.classify_bill_row(
        "- **Input:** $\\sigma_d, Q_d, Q_f, T$.") == "a"


def test_clause_labels_classify() -> None:
    assert tgc.classify_bill_row(
        "*   **DEPLOYED-PART CLAUSE:** The mechanism does not modify "
        "any part of the module.") == "a"
    assert tgc.classify_bill_row(
        "*   **UNPRICED_DUTY_CYCLE:** Operational loss (energy) is "
        "priced in the Burden Ledger.") == "c"


def test_no_prose_regression() -> None:
    """The v13 narrative guard is untouched: first-person
    deliberation and bare unknown headers stay flagged (never a
    guessed tag)."""
    assert tgc.classify_bill_row(
        "*   Note: I think the mechanism might be stronger.") is None
    assert tgc.classify_bill_row(
        "*   Some unknown header:") is None


def test_v14_convergence_gate_on_burned_bytes() -> None:
    """The >=50% water-domain convergence gate, recomputed from the
    committed mining record AND re-derived from the burned bytes
    (deterministic re-run, never trusted from the summary)."""
    rec = json.loads((REPO / "eval" / "r101_water_mining_record.json")
                     .read_text(encoding="utf-8"))
    assert rec["gate_pass"] is True
    assert rec["proxy_convergence_rate"] >= 0.50
    # independent re-derive (Art. 13): the same deterministic pass
    import r40_machine_v77 as m77
    scan = m77.base_scan
    rows_dir = REPO / "eval" / "holdout_v14_generation" / "rows"
    rows = [json.loads(f.read_text(encoding="utf-8"))
            for f in sorted(rows_dir.glob("*.json"))]
    pop = [r for r in rows
           if r["final_meta"]["stop_reason"]
           != "CONVERGED_ZERO_FINDINGS"]
    converged = []
    for r in pop:
        rec2 = tgc.grounded_critique(r["a1_answer"], scan_parity=scan)
        bu = rec2.get("residual_bill_untagged", 0)
        others = any(len(v) for k, v in
                     (rec2.get("residual_findings") or {}).items()
                     if k != "BILL_UNTAGGED")
        if bu == 0 and not others:
            converged.append(r["problem_id"])
    assert len(converged) / len(pop) >= 0.50, converged
    assert sorted(converged) == sorted(rec["proxy_converged_rows"])
