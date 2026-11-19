#!/usr/bin/env python3
"""R95 CI-wired acceptance tests for the tool-grounded critic corrector
(discovery_fabric/engine/tool_grounded_critic.py — claim c-0109, CRITIC
pattern attribution per AM82). Every threshold was COMPUTED FIRST on the
committed corpus (scripts/r95_probe_bill_rows.py + the in-test corpus
walk), never assumed. The ORACLE is the frozen machine's own base_scan
(scripts/r22_a1w_v5_repair.py — the byte the machine runs at
r40_machine_v77.py:484): the corrected bytes must satisfy THE MACHINE'S
OWN CONTRACT, not a private one. Art. 22: fixtures prove MECHANICS; the
machine-side wiring + its live ablation are the typed next steps."""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))  # r22's own import surface


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


r22 = _load("r22scan", "scripts/r22_a1w_v5_repair.py")
tgc = _load("tgc", "discovery_fabric/engine/tool_grounded_critic.py")

# the sealed corpora (committed bytes; the v9+v10 sealed generation sets)
_CORPUS = sorted((REPO / "eval/holdout_v9_generation/rows").glob("*.json"))
_v10 = REPO / "eval/holdout_v10_generation/rows"
if _v10.exists():
    _CORPUS += sorted(_v10.glob("*.json"))


def _answers():
    for f in _CORPUS:
        row = json.loads(f.read_text())
        ans = row.get("a1_answer") or row.get("answer") or ""
        if ans:
            yield f.name, ans


# ------------------------------------------ detection parity with the oracle
def test_untagged_detection_is_byte_parity_with_the_machine_scan():
    """The engine module's notion of an untagged row must equal the frozen
    machine's own base_scan's notion — on every committed answer."""
    for name, ans in _answers():
        scan_rows = r22.scan(ans).get("BILL_UNTAGGED", [])
        m = tgc.BILL_SECTION.search(ans)
        engine_rows = [ans[m.start(1):m.end(1)].splitlines()[i].strip()[:90]
                       for i in tgc._untagged_rows(m.group(1))] if m else []
        # exact-multiset parity, no re-strip (the oracle's strings are the
        # [:90] cuts; re-stripping them would mutate the comparison)
        assert sorted(engine_rows) == sorted(scan_rows), \
            f"parity broken on {name}"


# ------------------------------------------------- the computed correction
def test_tagger_mechanically_corrects_the_computed_share():
    """COMPUTED FIRST: 901 flagged rows across the 60 sealed answers ->
    515 after the tagger (42.8%) under the final ambiguity matrix;
    48/60 rows improved. The floor asserts the corpus-level effect stays
    material and stable."""
    before_total = after_total = improved = 0
    for name, ans in _answers():
        before = len(r22.scan(ans).get("BILL_UNTAGGED", []))
        corrected, rec = tgc.tag_bill(ans)
        after = len(r22.scan(corrected).get("BILL_UNTAGGED", []))
        assert after <= before, f"tagger made {name} WORSE"
        before_total += before
        after_total += after
        improved += int(after < before)
    assert before_total == 901, before_total  # corpus bytes are frozen
    assert after_total <= 515, after_total
    assert improved >= 48, improved
    rate = 100 * (before_total - after_total) / before_total
    assert rate >= 42.0, rate  # the computed 42.8% holds


def test_tagger_never_guesses_ambiguous_or_protocol_rows():
    typed = {
        "1.  **Hardware**: Zero new hardware installed. Rides on the "
        "existing dosing pumps.": "a",  # (a) wins over the bare noun
        "2.  **Additive**: Commercial-grade glue solution, stock 100 ppm.": "b",
        "3.  **Procedure**: Reconfigure the dosing controller to pulse mode.": "c",
        "*   **Pass:** If PFC proxy decreases by >= 10%.": None,  # protocol
        # AM91 v14 (claim c-0116, forward-only): the machine's own
        # ledger keys are the answer format's structure — a bare
        # known-ledger header is the (c) pricing/duty family, and a
        # setpoint edit on the EXISTING controller is the auditor-read
        # (c) retuning family
        "**Operational Loss Pricing:**": "c",
        "5.  **Mystery**: The catalyst exhibits both commercial-grade "
        "support and schedule flexibility.": None,                # ambiguous
        "6.  **Schedule**: The dosing runs on an existing continuous "
        "controller.": "c",
    }
    for row, want in typed.items():
        assert tgc.classify_bill_row(row) == want, row


def test_tagged_format_is_normalized_to_the_scannable_contract():
    ans = ("IMPLEMENTATION BILL\n"
           "1.  **Hardware**: Zero new hardware, existing pumps. (Tag: a)\n"
           "2.  **Additive**: Commercial-grade glue. (Tag: b)\n")
    corrected, rec = tgc.tag_bill(ans)
    assert rec["normalized"] == 2 and rec["corrected"] == 0
    assert r22.scan(corrected).get("BILL_UNTAGGED") is None


def test_tagged_rows_carry_the_scan_contract_format():
    ans = ("IMPLEMENTATION BILL\n"
           "1.  **Hardware**: Zero new hardware installed; rides on the "
           "existing pumps.\n"
           "2.  **Additive**: Commercial-grade glue solution.\n"
           "3.  **Procedure**: Reconfigure the dosing controller to pulse "
           "mode.\n")
    corrected, rec = tgc.tag_bill(ans)
    assert rec["corrected"] == 3
    assert r22.scan(corrected).get("BILL_UNTAGGED") is None
    assert "existing pumps. (a)" in corrected
    assert "glue solution. (b)" in corrected
    assert "pulse mode. (c)" in corrected


# --------------------------------------------- computed-chemistry leg
def test_inverted_chemistry_claim_is_rewritten_mechanically():
    verdict = {"computed_verdict": "INVERTED", "claimed_direction":
               "decrease", "computed_direction": "up"}
    ans = ("The proposed measure reduces the formation of CO2 in the "
           "flue gas, which makes it attractive.")
    fixed, rec = tgc.correct_inverted_chemistry(ans, verdict)
    assert rec["chemistry_rewrites"] == 1
    assert "increases the formation of CO2" in fixed


def test_consistent_or_unverifiable_chemistry_is_a_noop():
    ans = "Excess oxidant favors the formation of CO2 at this temperature."
    for v in ({"computed_verdict": "CONSISTENT", "claimed_direction":
               "increase"},
              {"computed_verdict": "UNVERIFIABLE"},
              {}):
        fixed, rec = tgc.correct_inverted_chemistry(ans, v)
        assert fixed == ans and rec["chemistry_rewrites"] == 0


# ------------------------------------------------------ composed surface
def test_grounded_critique_requires_the_machine_scan_as_oracle():
    with pytest.raises(TypeError):
        tgc.grounded_critique("IMPLEMENTATION BILL\n1. **Hardware**: "
                              "existing pumps.")


def test_grounded_critique_end_to_end_reduces_the_residual():
    ans = ("IMPLEMENTATION BILL\n"
           "1.  **Hardware**: Zero new hardware installed; rides on the "
           "existing pumps.\n"
           "2.  **Additive**: Commercial-grade glue solution.\n"
           "3.  **Procedure**: Reconfigure the dosing controller to pulse "
           "mode.\n"
           "*   **Pass:** If PFC proxy decreases by >= 10%.\n")
    rec = tgc.grounded_critique(ans, scan_parity=r22.scan)
    assert rec["corrected"] == 3
    assert rec["residual_bill_untagged"] == 1  # the protocol row stays
    assert "Pass:" in rec["residual_findings"]["BILL_UNTAGGED"][0]


def test_grounding_record_is_typed():
    _, rec = tgc.tag_bill("no bill here")
    assert rec["record"] == "TOOL_GROUNDED_CRITIC/1.0.0"


# ------------------------------------------------------------ guards
def test_determinism():
    ans = ("IMPLEMENTATION BILL\n1.  **Hardware**: Zero new hardware; "
           "existing pumps.\n")
    a = tgc.tag_bill(ans)
    b = tgc.tag_bill(ans)
    assert a == b


def test_engine_module_is_self_contained():
    src = (REPO / "discovery_fabric/engine/tool_grounded_critic.py") \
        .read_text()
    for banned in ("import r22", "import scripts", "from scripts",
                   "import socket", "import requests", "import urllib",
                   "import http", "urlopen", "subprocess"):
        assert banned not in src, f"violation: {banned}"


def test_frozen_baselines_untouched():
    rec = json.loads((REPO / "eval/r64_v9_preflight.json").read_text())
    fb = rec["checks"]["freeze_baselines_sha16"]
    for f, expected in fb.items():
        got = hashlib.sha256((REPO / f).read_bytes()).hexdigest()[:16]
        assert got == expected, f"the frozen file {f} MOVED (typed abort)"
