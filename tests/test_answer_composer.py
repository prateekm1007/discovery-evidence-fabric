"""R6 ANSWER COMPOSER tests (owner directive 2026-11-11, item 3).

The composer must:
  - make exactly ONE LLM call for a contract-valid composition;
  - make exactly ONE repair retry (2 total) when the first pass
    violates the deterministic contract, and adopt the repair only if
    it improves (fewer violations / valid);
  - return a typed failure (never a fake answer) on transport failure;
  - apply the answer-shape contract to the composed text.

The LLM is injected (tests monkeypatch; Art. X — one transport path in
production, one fake in tests).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discovery_fabric.engine.answer_composer import compose_answer

PROBLEM = {
    "device": "rolling-element bearing in a 350 kW industrial fan drive",
    "failure": "incipient spalling on the inner race",
    "failure_mode": "incipient-spalling",
    "constraint": "maintain 350 kW duty without unscheduled downtime",
    "question_type": "predictor-design",
    "user_variables": ["maintain 350 kW duty without unscheduled downtime",
                       "device of record: 350 kW industrial fan drive",
                       "failure to address: incipient spalling"],
}

PACKET = [{"id": "iso281", "title": "ISO 281 bearing life",
           "abstract": "modified rating life accounts for contamination "
                       "and lubrication; vibration RMS rises before "
                       "spalling becomes visible"}]

VALID_ANSWER = (
    "Recommend a vibration-based predictor for the fan-drive bearing.\n"
    "INDICATOR: bearing vibration RMS in the spalling band. "
    "THRESHOLD: 4.5 mm/s — ASSUMPTION (alert level, to be calibrated "
    "on the first 30 days of healthy data).\n"
    "PROTOCOL: n=6 fan drives monitored 180 days; pass if the alert "
    "fires before visible spalling; fail otherwise.\n"
    "Falsify if a drive reaches spalling with no prior alert."
)


def _llm_factory(responses):
    calls = {"n": 0}

    def llm(prompt, system="", timeout=240, max_tokens=700,
            purpose="", **kw):
        calls["n"] += 1
        i = min(calls["n"], len(responses)) - 1
        r = responses[i]
        if isinstance(r, Exception):
            raise r
        out = dict(r)
        out.setdefault("ok", True)
        out.setdefault("prompt_hash", "p" * 8)
        out.setdefault("output_hash", "o" * 8)
        return out
    return llm, calls


def test_composer_one_call_contract_valid():
    llm, calls = _llm_factory([{"content": VALID_ANSWER}])
    rec = compose_answer(PROBLEM, PACKET, [], None,
                         "predictor-design", llm_generate=llm)
    assert calls["n"] == 1, f"expected ONE call, got {calls['n']}"
    assert rec["state"] == "COMPOSED_CONTRACT_VALID", rec
    assert rec["contract"]["valid"] is True


def test_composer_repair_retry_on_violation():
    bad = ("Track the bearing. "
           "INDICATOR: vibration. THRESHOLD: 9.9 mm/s plain. "
           "PROTOCOL: n=6 drives, 180 days; pass if alert fires first.")
    llm, calls = _llm_factory([{"content": bad}, {"content": VALID_ANSWER}])
    rec = compose_answer(PROBLEM, PACKET, [], None,
                         "predictor-design", llm_generate=llm)
    assert calls["n"] == 2, f"expected repair retry, got {calls['n']}"
    assert rec["state"] == "COMPOSED_CONTRACT_VALID"
    assert rec.get("repaired") is True
    assert rec["contract_first_pass"]["valid"] is False


def test_composer_transport_failure_is_typed():
    llm, calls = _llm_factory([{"ok": False, "status": "PROVIDER_UNAVAILABLE",
                                "content": None, "error": "no rung"}])
    rec = compose_answer(PROBLEM, PACKET, [], None,
                         "predictor-design", llm_generate=llm)
    assert calls["n"] == 1
    assert rec["state"] == "COMPOSE_FAILED_TRANSPORT"
    assert rec["answer"] is None


def test_composer_contract_invalid_recorded_honestly():
    # repair still violates: the record says so (never fake-valid).
    # OWNER AUDIT ROUND 2026-11-12, DIRECTIVE 1: compose -> validate ->
    # REPAIR UNTIL VALID — the loop is bounded at MAX_REPAIR_ROUNDS
    # repairs. DIRECTIVE 2 (same round, DOWNGRADE DON'T DISCARD): a
    # still-invalid composition is DOWNGRADED (failing EVIDENCE-BACKED
    # relabeled ASSUMPTION, invalid citations dropped) and DELIVERED
    # with one plain caveat — the typed violations stay recorded
    # honestly (never fake-valid), the state is
    # COMPOSED_CONTRACT_DOWNGRADED.
    from discovery_fabric.engine.answer_composer import MAX_REPAIR_ROUNDS
    bad1 = ("Do maintenance sometimes. "
            "INDICATOR: something vague. THRESHOLD: 9.9 mm/s plain. "
            "PROTOCOL: n=6 drives; pass if fine.")
    bad2 = ("Still vague. INDICATOR: nothing. THRESHOLD: 3.3 mm/s plain. "
            "PROTOCOL: n=2 drives.")
    bad3 = ("Still vague again. INDICATOR: nothing. "
            "THRESHOLD: 3.3 mm/s plain. PROTOCOL: n=2 drives.")
    llm, calls = _llm_factory([{"content": bad1}, {"content": bad2},
                               {"content": bad3}])
    rec = compose_answer(PROBLEM, PACKET, [], None,
                         "predictor-design", llm_generate=llm)
    assert calls["n"] == 1 + MAX_REPAIR_ROUNDS
    assert rec["state"] == "COMPOSED_CONTRACT_DOWNGRADED"
    assert rec["contract"]["valid"] is False
    assert rec["contract"]["violations"]
    assert rec["repair_rounds_used"] == MAX_REPAIR_ROUNDS
    assert rec["downgrade"]["applied"] is True
    assert isinstance(rec["answer"], str) and rec["answer"].strip()


def test_composer_killed_candidate_never_endorsed():
    # the prompt must tell the composer a killed candidate is never the
    # recommendation and the text stays CLEAN (owner audit round
    # 2026-11-12, directive 1: no internal state names, no pipeline
    # narration; the unverified proposal is plainly flagged)
    from discovery_fabric.engine.answer_composer import _COMPOSER_SYSTEM
    assert "UNVERIFIED" in _COMPOSER_SYSTEM
    assert "NO internal state names" in _COMPOSER_SYSTEM
    assert "NO SURVIVING CANDIDATES" in _COMPOSER_SYSTEM
    assert "needs the stated test" in _COMPOSER_SYSTEM
