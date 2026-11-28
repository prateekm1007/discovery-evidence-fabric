"""tests/test_r6_answer_delivery_states.py — hermetic zero-LLM
pins for the owner round 2026-11-12 directive 1 (three DISTINCT
delivery outcomes + specific caveats + delivery accounting).

WHAT IS PINNED (the directive-1 contract):
  1. COMPOSED_CONTRACT_VALID is the first outcome.
  2. COMPOSED_CONTRACT_DOWNGRADED — only when the downgraded text
     revalidates clean (the relabel repairs the failing support).
  3. COMPOSED_CONTRACT_INVALID_DELIVERED — delivered under the owner's
     delivery policy but STILL contract-invalid; ONE specific caveat
     naming the open defects; never represented as valid; excluded from
     scientific superiority scoring (the scoring gate requires
     answer_contract.valid is True, which an INVALID_DELIVERED fails by
     construction).
  4. Constraint violations surviving every bounded repair ship with ONE
     specific caveat (never a generic line concealing a specific
     technical defect).
  5. The delivery harness counts INVALID_DELIVERED as delivered for the
     rate, reports it per-class, and it is never counted as a win, tie
     or loss by any superiority instrument.

Hermetic: the LLM is an injected fake; constraint audit is
monkeypatched where the test pins the audit-violation path; zero
network, zero credentials.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from discovery_fabric.engine import answer_composer as _comp  # noqa: E402
from discovery_fabric.engine.answer_composer import compose_answer  # noqa: E402
from discovery_fabric.engine.answer_contract import validate_answer  # noqa: E402

EVAL_RUN = None
try:
    import eval.run as EVAL_RUN  # noqa: E402
except Exception:  # noqa: BLE001
    EVAL_RUN = None

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

INTERVENTION_PROBLEM = dict(PROBLEM,
                            question_type="intervention-proposal")

PACKET = [{"id": "iso281", "title": "ISO 281 bearing life",
           "abstract": "modified rating life accounts for contamination "
                       "and lubrication; vibration RMS rises before "
                       "spalling becomes visible"}]

# plain THRESHOLD with NO provenance basis: predictor contract fails by
# construction and the downgrade (citation/jargon/EB relabel only) cannot
# repair it — the revalidation cannot pass
BAD_THRESHOLD = (
    "Recommend a vibration-based predictor.\n"
    "INDICATOR: bearing vibration RMS in the spalling band.\n"
    "THRESHOLD: 4.5 mm/s.\n"
    "PROTOCOL: n=6 fan drives monitored 180 days; pass if the alert "
    "fires before visible spalling; fail otherwise.\n"
    "Falsify if a drive reaches spalling with no prior alert.")

VALID_ANSWER = (
    "Recommend a vibration-based predictor for the fan-drive bearing.\n"
    "INDICATOR: bearing vibration RMS in the spalling band. "
    "THRESHOLD: 4.5 mm/s — ASSUMPTION (alert level, to be calibrated "
    "on the first 30 days of healthy data).\n"
    "PROTOCOL: n=6 fan drives monitored 180 days; pass if the alert "
    "fires before visible spalling; fail otherwise.\n"
    "Falsify if a drive reaches spalling with no prior alert.")

# EVIDENCE-BACKED with a citation that is NOT in the frozen packet:
# relabeled ASSUMPTION + citation dropped by the downgrade, then the
# revalidating contract passes — the valid-downgrade outcome
BAD_CITE = (
    "Recommend reducing the inner-race infeed.\n"
    "FEED RATE: 2.0 mm/rev — EVIDENCE-BACKED [ns-998877-xyz-gone].\n"
    "Falsify if edge chipping rises on the post-change lot.")

# predictor answer missing the VALIDATION-PROTOCOL section entirely —
# no EB/citation to repair; revalidation cannot pass
NO_PROTOCOL = (
    "Recommend replacing the bearing every 5,000 hours of run time. "
    "INDICATOR: vibration RMS — ASSUMPTION. "
    "THRESHOLD: ASSUMPTION 4.5 mm/s.")


def _llm_factory(responses):
    calls = []

    def llm(prompt, system="", timeout=240, max_tokens=700,
            purpose="", **kw):
        calls.append({"purpose": purpose, "max_tokens": max_tokens,
                      "prompt": prompt})
        i = min(len(calls), len(responses)) - 1
        r = responses[i]
        if isinstance(r, Exception):
            raise r
        out = dict(r)
        out.setdefault("ok", True)
        out.setdefault("prompt_hash", "p" * 8)
        out.setdefault("output_hash", "o" * 8)
        out.setdefault("finish_reason", "stop")
        return out
    return llm, calls


def _res(content, finish="stop", ok=True, error=None):
    out = {"ok": ok, "content": content,
           "status": "OK" if ok else "CALL_FAILED",
           "output_hash": "o" * 8,
           "finish_reason": finish}
    if error is not None:
        out["error"] = error
    return out


def _run(answer, problem=None, question_type=None, **extra):
    llm, calls = _llm_factory([_res(answer)] * 6)
    rec = compose_answer(problem or PROBLEM, PACKET, [], None,
                         question_type or (problem or PROBLEM)
                         .get("question_type"),
                         llm_generate=llm, **extra)
    return rec, calls


def _write_composer(d: Path, state: str, answer) -> Path:
    p = d / "ANSWER_COMPOSED.json"
    p.write_text(json.dumps({"state": state, "answer": answer}),
                 encoding="utf-8")
    return p


class TestThreeDistinctOutcomes(unittest.TestCase):
    def test_valid_outcome_is_first_class(self):
        rec, _ = _run(VALID_ANSWER)
        self.assertEqual(rec["state"], "COMPOSED_CONTRACT_VALID",
                         f"valid composition must be typed VALID: {rec.get('state')}")
        self.assertTrue(rec["contract"]["valid"])
        self.assertNotIn("COMPOSED_CONTRACT_INVALID_DELIVERED",
                         rec["state"])

    def test_invalid_threshold_provenance_is_invalid_delivered(self):
        rec, _ = _run(BAD_THRESHOLD)
        self.assertEqual(rec["state"], "COMPOSED_CONTRACT_INVALID_DELIVERED",
                         f"plain THRESHOLD must ride the policy path: {rec.get('state')}")
        self.assertIsNotNone(rec["answer"])
        self.assertFalse(rec["contract"]["valid"])
        self.assertFalse((rec.get("downgrade") or {})
                         .get("valid_after_downgrade"))

    def test_no_protocol_cannot_be_repaired_by_downgrade(self):
        rec, _ = _run(NO_PROTOCOL)
        self.assertEqual(rec["state"], "COMPOSED_CONTRACT_INVALID_DELIVERED",
                         f"missing PROTOCOL must survive the downgrade: {rec.get('state')}")
        # one specific caveat: it must NAME a defect, not carry only
        # the generic downgrade line — and never a generic line alone
        self.assertTrue(rec.get("caveats"),
                        "an invalid-delivered record must carry its caveat")
        caveats = " | ".join(str(c) for c in rec["caveats"])
        self.assertIn("protocol", caveats.lower(),
                      f"the caveat must name the violated contract check: {caveats}")

    def test_failed_downgrade_revalidation_ships_specific_caveat(self):
        rec, _ = _run(BAD_THRESHOLD)
        self.assertEqual(rec["state"], "COMPOSED_CONTRACT_INVALID_DELIVERED")
        self.assertTrue(rec.get("caveats"))
        caveats = " | ".join(str(c) for c in rec["caveats"])
        # the defect, not a generic banner: the predictor violation
        # string carries "threshold"
        self.assertIn("threshold", caveats.lower(),
                      f"the caveat must surface the numeric-provenance defect verbatim: {caveats}")

    def test_invalid_delivered_answer_is_not_scoreable(self):
        rec, _ = _run(BAD_THRESHOLD)
        result = validate_answer(rec["answer"], "predictor-design",
                                 packet=PACKET)
        self.assertFalse(result["valid"],
                         "an invalid-delivered answer must FAIL the deterministic contract re-validation — it can never be full_scoreable")

    def test_valid_downgrade(self):
        rec, _ = _run(BAD_CITE, problem=INTERVENTION_PROBLEM)
        self.assertEqual(rec["state"], "COMPOSED_CONTRACT_DOWNGRADED",
                         f"repairable citation defect must ship the downgraded form: {rec.get('state')}")
        self.assertTrue((rec.get("downgrade") or {})
                        .get("valid_after_downgrade"))
        self.assertNotIn("ns-998877-xyz-gone", rec["answer"],
                         "the invalid citation must be dropped")
        self.assertNotIn("EVIDENCE-BACKED", rec["answer"])
        self.assertIn("ASSUMPTION", rec["answer"])
        self.assertTrue(rec.get("caveats"),
                        "a downgraded delivery carries ONE plain caveat")

    def test_unsupported_claim_is_relabeled_and_counted(self):
        rec, _ = _run(BAD_CITE, problem=INTERVENTION_PROBLEM)
        dg = rec.get("downgrade") or {}
        self.assertGreaterEqual(dg.get("n_relabels", 0), 1)
        self.assertGreaterEqual(dg.get("n_citations_dropped", 0), 1)

    def test_invalid_citation_dropped_from_answer(self):
        rec, _ = _run(BAD_CITE, problem=INTERVENTION_PROBLEM)
        self.assertNotIn("ns-998877-xyz-gone", rec["answer"])
        self.assertEqual(rec["downgrade"]["citations_dropped"][0]
                         .lower()[:20], "ns-998877-xyz-gone")

    def test_repair_truncated_not_adopted(self):
        # compose is invalid; repair is cut off at the output budget —
        # never adopted; the delivered answer is the complete
        # pre-repair draft unless the downgrade ships it
        llm, calls = _llm_factory(
            [_res(BAD_THRESHOLD),
             _res("INDICATOR: bearing vibration RMS — ASSUMPTION. "
                  "THRESHOLD:", finish="length")])
        with mock.patch.dict("os.environ", {"FABRIC_CONSTRAINT_AUDIT": "0"}):
            rec = compose_answer(PROBLEM, PACKET, [], None,
                                 "predictor-design",
                                 llm_generate=llm)
        self.assertEqual(rec.get("state"), "COMPOSED_CONTRACT_INVALID_DELIVERED",
                         f"truncated repair must not be adopted: {rec.get('state')}")
        self.assertIn("4.5 mm/s", rec["answer"],
                      "the pre-repair (complete) draft is the delivered text")

    def test_constraint_violation_surviving_repair_gets_specific_caveat(self):
        # monkeypatch the deterministic audit to always report one
        # surviving violation; the contract is clean, so the answer is
        # VALID-delivered — and the caveat must NAME the specific defect
        dirty = {"state": "CONSTRAINT_VIOLATIONS",
                 "n_violations": 1,
                 "violations": [{"type": "RESTATES_USER_CONSTRAINT",
                                 "detail": ("near-verbatim echo of the "
                                            "user variable 'maintain 350 "
                                            "kW duty' — the constraint "
                                            "listed, not a design change"),
                                 "context": "maintain 350 kW duty"}]}
        from discovery_fabric.engine import constraint_audit as _ca
        with mock.patch.object(_ca, "audit_constraints",
                               return_value=dirty):
            rec, _ = _run(VALID_ANSWER)
        self.assertEqual(rec["state"], "COMPOSED_CONTRACT_VALID",
                         f"contract-valid draft stays VALID: {rec.get('state')}")
        self.assertTrue(rec.get("caveats"),
                        "a dirty audit must never ship a bare answer")
        self.assertIn("near-verbatim echo",
                      " ".join(str(c) for c in rec["caveats"]).lower(),
                      "the surviving constraint defect must be named verbatim")
        self.assertEqual(rec["constraint_audit"]["state"],
                         "CONSTRAINT_VIOLATIONS")


class TestDeliveryAccounting(unittest.TestCase):
    def test_delivery_harness_distinguishes_states(self):
        if EVAL_RUN is None:
            self.skipTest("eval.run not importable on this host")
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            cases = [("VALID_P", "COMPOSED_CONTRACT_VALID", "ship-valid"),
                     ("DG_P", "COMPOSED_CONTRACT_DOWNGRADED", "ship-dg"),
                     ("BAD_P", "COMPOSED_CONTRACT_INVALID_DELIVERED", "ship-bad"),
                     ("REFUSAL_P", "NO_ADMISSIBLE_CANDIDATES", None),
                     ("TRANSPORT_P", "COMPOSE_FAILED_TRANSPORT", None)]
            dirs = []
            for name, state, ans in cases:
                d = base / name
                d.mkdir()
                _write_composer(d, state, ans)
                dirs.append(d)
            out = EVAL_RUN.delivery_rate_from_dirs(dirs)
        self.assertEqual(out["total"], 5)
        self.assertEqual(out["delivered"], 3,
                         "valid+downgraded+invalid-delivered all ship")
        self.assertEqual(out["rate"], 0.6)
        self.assertEqual(out["n_invalid_delivered"], 1)
        self.assertEqual(out["delivery_classes"]["COMPOSED_CONTRACT_INVALID_DELIVERED"], 1)
        self.assertEqual(out["delivery_classes"]["COMPOSE_FAILED_TRANSPORT"], 1)

    def test_no_delivery_when_all_refused(self):
        if EVAL_RUN is None:
            self.skipTest("eval.run not importable on this host")
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            dirs = []
            for name, state in (("A", "NO_ADMISSIBLE_CANDIDATES"),
                                ("B", "COMPOSE_FAILED_TRANSPORT")):
                d = base / name
                d.mkdir()
                _write_composer(d, state, None)
                dirs.append(d)
            out = EVAL_RUN.delivery_rate_from_dirs(dirs)
        self.assertEqual(out["delivered"], 0)
        self.assertEqual(out["rate"], 0.0)


if __name__ == "__main__":
    unittest.main()
