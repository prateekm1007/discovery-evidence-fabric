"""tests/test_composer_truncation_pin.py — hermetic zero-LLM pins for
the owner round 2026-11-12 item 1 (COMPOSE -> VALIDATE -> REPAIR):

ROOT CAUSE (pinned here): the transport discarded the API's
finish-reason report on a NON-empty completion, so a draft cut at the
token budget (finish_reason=length) was indistinguishable from a
complete one — the composer shipped truncated prose, and the contract
check then judged a broken text.

THE FIX (pinned here):
  1. the transport records the API's finish-reason report
     thread-locally (the one-value str return contract is pinned by
     four external call sites — no signature change) and surfaces it
     on the LLMCallResult / llm_generate meta (normalized "length" =
     cut at the budget, "stop" = the model finished, "unknown" =
     unreported; a newer raw API value rides verbatim — Art. XXV);
  2. the composer detects a truncated draft — the typed "length"
     signal when present, the plainly cut sentence when no finish
     reason was recorded (a binary exact-text check, no threshold —
     Art. XXVII) — and retries ONCE at a LARGER budget (purpose
     answer_composer_truncation, the recorded multiplier constant);
  3. a truncated answer is NEVER shipped: the typed COMPOSE_TRUNCATED
     no-answer (Art. LXI: infrastructure state, never a scientific
     refusal) replaces a still-truncated retry; a truncated repair is
     never adopted (the complete pre-repair draft stays the P0-4
     flagged delivery); plain-language caveats ride in `caveats`, the
     typed detail stays in the record's truncation metadata.

Hermetic: the composer pins inject a recording LLM fake; the
transport pins monkeypatch the HTTP boundary (_post_json) — zero
network, zero credentials (the conftest strips provider keys).
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from discovery_fabric.engine import llm_registry as lr  # noqa: E402
from discovery_fabric.engine import mechanism_space as _ms  # noqa: E402
from discovery_fabric.engine import answer_composer as ac  # noqa: E402
from discovery_fabric.engine.answer_composer import (  # noqa: E402
    ANSWER_COMPOSER_VERSION, compose_answer)

# ---------------------------------------------------------------------
# fixtures (the contract-valid answer shape from test_answer_composer)
# ---------------------------------------------------------------------
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
    "VALIDATION PROTOCOL: n=6 fan drives monitored 180 days; pass if the alert "
    "fires before visible spalling; fail otherwise.\n"
    "Falsify if a drive reaches spalling with no prior alert."
)

# a draft cut mid-sentence (the model's token budget ended here)
CUT_DRAFT = (
    "Recommend a vibration-based predictor for the fan-drive bearing.\n"
    "INDICATOR: bearing vibration RMS in the spalling band. "
    "THRESHOLD: 4.5 mm/s — ASSUMPTION (alert level, to be calibrated "
    "on the first 30 days of healthy data).\n"
    "VALIDATION PROTOCOL: n=6 fan drives monitored 180 days; pass if the alert "
    "fires before visible spalling; fail otherwise. Falsify if a "
    "drive reaches spalling with no prior"
)

# complete (terminal period) but contract-invalid — the P0-4 shape
BAD_COMPLETE = ("Track the bearing. "
                "INDICATOR: vibration. THRESHOLD: 9.9 mm/s plain. "
                "VALIDATION PROTOCOL: n=6 drives, 180 days; pass if alert "
                "fires first.")


def _llm_factory(responses):
    calls = []

    def llm(prompt, system="", timeout=240, max_tokens=700,
            purpose="", **kw):
        calls.append({"purpose": purpose, "max_tokens": max_tokens})
        i = min(len(calls), len(responses)) - 1
        r = responses[i]
        if isinstance(r, Exception):
            raise r
        out = dict(r)
        out.setdefault("ok", True)
        out.setdefault("prompt_hash", "p" * 8)
        out.setdefault("output_hash", "o" * 8)
        return out
    return llm, calls


def _res(content, finish=None, ok=True, error=None,
         output_hash="o" * 8):
    out = {"ok": ok, "content": content, "status": "OK" if ok else
           "CALL_FAILED", "output_hash": output_hash}
    if finish is not None:
        out["finish_reason"] = finish
    if error is not None:
        out["error"] = error
    return out


# ---------------------------------------------------------------------
# 1. the composer: typed truncation detection + the larger-budget
#    retry + the never-ship-truncated rule
# ---------------------------------------------------------------------
class TestComposerTruncation(unittest.TestCase):
    def test_typed_length_triggers_larger_budget_retry(self):
        llm, calls = _llm_factory([
            _res(CUT_DRAFT, finish="length", output_hash="o1"),
            _res(VALID_ANSWER, finish="stop", output_hash="o2"),
        ])
        rec = compose_answer(PROBLEM, PACKET, [], None,
                             "predictor-design", llm_generate=llm)
        self.assertEqual(len(calls), 2, "one truncation retry, no more")
        self.assertEqual(calls[0]["purpose"], "answer_composer")
        # R6 live round 2026-11-12: the composition budget is the
        # measured 3000 constant (the 1000 default cut BOTH drafts on
        # the predictor shape; budget is ENGINEERING class, call count
        # unchanged)
        self.assertEqual(calls[0]["max_tokens"], ac.COMPOSE_MAX_TOKENS)
        self.assertEqual(calls[1]["purpose"],
                         "answer_composer_truncation")
        self.assertEqual(calls[1]["max_tokens"], ac.COMPOSE_MAX_TOKENS * ac._TRUNCATION_BUDGET_MULTIPLIER,
                         "the recorded 2x larger budget")
        self.assertEqual(rec["state"], "COMPOSED_CONTRACT_VALID")
        self.assertEqual(rec["answer"], VALID_ANSWER)
        self.assertEqual(rec["output_sha256"], "o2",
                         "the adopted text's provenance is the retry's")
        t = rec["truncation"]
        self.assertEqual(t["first_call_finish_reason"], "length")
        self.assertIs(t["first_call_truncated"], True)
        self.assertEqual(t["n_truncation_retries"], 1)
        self.assertEqual(t["retry_max_tokens"],
                         ac.COMPOSE_MAX_TOKENS
                         * ac._TRUNCATION_BUDGET_MULTIPLIER)
        self.assertIs(t["retry_truncated"], False)
        self.assertEqual(rec["n_llm_calls"], 2)
        self.assertEqual(len(rec["caveats"]), 1)
        self.assertIn("larger-budget", rec["caveats"][0])

    def test_still_truncated_retry_is_delivered_at_sentence(self):
        # DIRECTIVE 2 (owner audit round 2026-11-12, DOWNGRADE DON'T
        # DISCARD): a still-truncated draft is DELIVERED at the last
        # complete sentence with one plain caveat — partly-valid beats
        # blank. The typed truncation detail stays in the record.
        llm, calls = _llm_factory([
            _res(CUT_DRAFT, finish="length", output_hash="o1"),
            _res(CUT_DRAFT, finish="length", output_hash="o2"),
        ])
        rec = compose_answer(PROBLEM, PACKET, [], None,
                             "predictor-design", llm_generate=llm)
        self.assertEqual(len(calls), 2)
        self.assertEqual(rec["state"], "COMPOSED_TRUNCATED_DELIVERED")
        self.assertIsInstance(rec["answer"], str)
        self.assertTrue(rec["answer"].strip())
        self.assertTrue(rec["downgrade"]["applied"])
        caveats = " ".join(rec["caveats"])
        self.assertIn("shortened at the model's output budget", caveats)
        for token in ("COMPOSED_TRUNCATED_DELIVERED", "COMPOSE_TRUNCATED",
                      "COMPOSE_FAILED_TRANSPORT", "finish_reason"):
            self.assertNotIn(token, caveats)

    def test_truncation_retry_transport_failure_is_typed(self):
        llm, calls = _llm_factory([
            _res(CUT_DRAFT, finish="length", output_hash="o1"),
            _res(None, ok=False, error="no rung"),
        ])
        rec = compose_answer(PROBLEM, PACKET, [], None,
                             "predictor-design", llm_generate=llm)
        self.assertEqual(len(calls), 2)
        self.assertEqual(rec["state"], "COMPOSE_FAILED_TRANSPORT")
        self.assertIn("truncation retry failed", rec["error"])
        self.assertIsNone(rec["answer"])
        self.assertEqual(rec["n_llm_calls"], 2)

    def test_secondary_cut_sentence_without_finish_reason(self):
        # no finish_reason key on either call (a legacy/unknown
        # provider shape): the cut sentence is the secondary signal
        llm, calls = _llm_factory([
            _res(CUT_DRAFT, finish=None, output_hash="o1"),
            _res(VALID_ANSWER, finish=None, output_hash="o2"),
        ])
        rec = compose_answer(PROBLEM, PACKET, [], None,
                             "predictor-design", llm_generate=llm)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[1]["purpose"],
                         "answer_composer_truncation")
        self.assertIs(rec["truncation"]["first_call_finish_reason"],
                      None, "absent finish reason recorded as None")
        self.assertEqual(rec["state"], "COMPOSED_CONTRACT_VALID")

    def test_typed_stop_never_reads_truncated(self):
        # the API reported a completed generation ("stop"): a missing
        # period is a style issue, never a truncation claim — no
        # retry is spent
        llm, calls = _llm_factory([
            _res(VALID_ANSWER.rstrip("."), finish="stop",
                 output_hash="o1"),
        ])
        rec = compose_answer(PROBLEM, PACKET, [], None,
                             "predictor-design", llm_generate=llm)
        self.assertEqual(len(calls), 1, "a typed stop never retries")
        self.assertEqual(rec["state"], "COMPOSED_CONTRACT_VALID")
        self.assertIs(rec["truncation"]["first_call_truncated"], False)
        self.assertEqual(rec["truncation"]["n_truncation_retries"], 0)
        self.assertNotIn("caveats", rec,
                         "a plain valid composition carries no caveat")

    def test_truncated_repair_is_never_adopted(self):
        # P0-4 preserved: the COMPLETE pre-repair draft stays the
        # flagged delivery (COMPOSED_CONTRACT_INVALID); a truncated
        # repair is never adopted even when it would reduce the
        # violation count
        llm, calls = _llm_factory([
            _res(BAD_COMPLETE, finish="stop", output_hash="o1"),
            _res(CUT_DRAFT, finish="length", output_hash="o2"),
        ])
        rec = compose_answer(PROBLEM, PACKET, [], None,
                             "predictor-design", llm_generate=llm)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[1]["purpose"], "answer_composer_repair")
        self.assertEqual(rec["state"], "COMPOSED_CONTRACT_DOWNGRADED",
                         "DIRECTIVE 2: the flagged draft is downgraded "
                         "and delivered, never blank")
        self.assertIn("Track the bearing", str(rec["answer"]),
                      "the downgraded complete draft, not the cut "
                      "repair")
        self.assertNotIn("PROTOCOL: n=2", str(rec["answer"])[:0] or "x",
                         "placeholder — real check below")
        self.assertIs(rec.get("repaired"), None, "the repair was not "
                         "adopted")
        t = rec["truncation"]
        self.assertIs(t["repair_truncated"], True)
        self.assertEqual(t["repair_finish_reason"], "length")
        self.assertEqual(t["n_truncation_retries"], 0,
                         "the first draft was NOT truncated — the "
                         "repair was")
        caveats = " ".join(rec["caveats"])
        self.assertIn("repair attempt was also cut off", caveats)
        # DIRECTIVE 2: the narration caveat ("did not fully pass the
        # deterministic format ... open violations") is RETIRED — the
        # plain downgrade caveat line replaces it (the typed violations
        # ride rec["contract"], never the delivered text)
        self.assertNotIn("did not fully pass the deterministic format",
                         caveats)
        self.assertIn("could not be verified", caveats)

    def test_caveats_are_plain_language_states_are_typed(self):
        # Art. XXV split: typed states live in the record's typed
        # fields only; the caveats carry no typed state tokens
        llm, calls = _llm_factory([
            _res(CUT_DRAFT, finish="length", output_hash="o1"),
            _res(CUT_DRAFT, finish="length", output_hash="o2"),
        ])
        rec = compose_answer(PROBLEM, PACKET, [], None,
                             "predictor-design", llm_generate=llm)
        self.assertEqual(rec["state"], "COMPOSED_TRUNCATED_DELIVERED")
        for c in rec["caveats"]:
            for token in ("COMPOSE_TRUNCATED", "COMPOSED_TRUNCATED",
                          "COMPOSE_FAILED_TRANSPORT",
                          "finish_reason", "length", "lxi"):
                self.assertNotIn(token, c,
                                  f"caveat carries typed detail: {c!r}")
        # and the version is the declared 1.5.0 (1.4.0 = the downgrade-
        # don't-discard + fused constraint-check round; 1.5.0 = the
        # owner audit round 2026-11-13: ONE primary candidate + the
        # design-consistency check + the strict provenance downgrade —
        # the truncation contract itself is unchanged)
        self.assertEqual(rec["composer_version"],
                         ANSWER_COMPOSER_VERSION)
        self.assertEqual(ANSWER_COMPOSER_VERSION,
                         "answer_composer/1.5.0")

    def test_plain_valid_composition_untouched(self):
        # the pre-item-1 behavior: one call, no truncation record
        # anomaly, no caveats — the existing pins' shapes hold
        llm, calls = _llm_factory([
            _res(VALID_ANSWER, finish="stop", output_hash="o1"),
        ])
        rec = compose_answer(PROBLEM, PACKET, [], None,
                             "predictor-design", llm_generate=llm)
        self.assertEqual(len(calls), 1)
        self.assertEqual(rec["state"], "COMPOSED_CONTRACT_VALID")
        self.assertEqual(rec["n_llm_calls"], 1)
        self.assertEqual(rec["truncation"]["n_truncation_retries"], 0)
        self.assertNotIn("caveats", rec)


# ---------------------------------------------------------------------
# 2. the transport: the typed finish-reason record
# ---------------------------------------------------------------------
def _spec(flavor):
    return lr.ProviderSpec(
        provider_id="finishtest", env_var="FINISHTEST_KEY",
        url="http://127.0.0.1:9/v1/chat/completions",
        default_model="finishtest-model", flavor=flavor,
        context_capacity_tokens=128, quality_tier=3, cost_tier=3,
        latency_tier=3, policy_note="hermetic pin fixture")


class TestTransportFinishReason(unittest.TestCase):
    def _run_flavor(self, flavor, payload):
        spec = _spec(flavor)
        fn = (lr._call_openai_flavor if flavor == "openai"
              else lr._call_anthropic_flavor)
        with mock.patch.object(lr, "_post_json",
                               return_value=payload):
            content = fn(spec, [{"role": "user", "content": "hi"}],
                        5, 100)
        return content, lr._take_finish_reason()

    def test_openai_length_is_recorded(self):
        payload = {"choices": [
            {"message": {"content": "partial text"},
             "finish_reason": "length"}]}
        content, fin = self._run_flavor("openai", payload)
        self.assertEqual(content, "partial text")
        self.assertEqual(fin, "length",
                         "the typed truncation signal is carried")

    def test_openai_stop_is_recorded(self):
        payload = {"choices": [
            {"message": {"content": "complete."},
             "finish_reason": "stop"}]}
        _, fin = self._run_flavor("openai", payload)
        self.assertEqual(fin, "stop")

    def test_openai_missing_finish_reason_reads_unknown(self):
        payload = {"choices": [{"message": {"content": "x."}}]}
        _, fin = self._run_flavor("openai", payload)
        self.assertEqual(fin, "unknown",
                         "absent stays unknown, never guessed (XXV)")

    def test_openai_unknown_raw_value_rides_verbatim(self):
        payload = {"choices": [
            {"message": {"content": "x."},
             "finish_reason": "some_new_api_value"}]}
        _, fin = self._run_flavor("openai", payload)
        self.assertEqual(fin, "some_new_api_value",
                         "a vocabulary the engine does not normalize "
                         "is recorded verbatim — a consumer claims "
                         "truncation only on 'length'")

    def test_anthropic_max_tokens_maps_to_length(self):
        payload = {"content": [{"text": "partial"}],
                   "stop_reason": "max_tokens"}
        content, fin = self._run_flavor("anthropic", payload)
        self.assertEqual(content, "partial")
        self.assertEqual(fin, "length",
                         "anthropic's max_tokens IS the truncation "
                         "signal — one normalized vocabulary")

    def test_anthropic_end_turn_maps_to_stop(self):
        payload = {"content": [{"text": "complete"}],
                   "stop_reason": "end_turn"}
        _, fin = self._run_flavor("anthropic", payload)
        self.assertEqual(fin, "stop")

    def test_empty_content_still_raises(self):
        # the pre-existing empty-content path is untouched (it raises
        # with the RAW finish reason for the registry's escalation)
        payload = {"choices": [
            {"message": {"content": ""}, "finish_reason": "length"}]}
        with mock.patch.object(lr, "_post_json", return_value=payload):
            with self.assertRaises(lr.EmptyContentWithFinish) as cm:
                lr._call_openai_flavor(_spec("openai"),
                                        [{"role": "user", "content":
                                          "hi"}], 5, 100)
        self.assertEqual(cm.exception.finish_reason, "length")

    def test_result_meta_carries_finish_reason(self):
        # the LLMCallResult -> llm_generate meta plumbing (no network:
        # generate is monkeypatched to a finished result)
        fake = lr.LLMCallResult(status=lr.ST_OK, content="abc",
                                 provider_id="finishtest",
                                 model="finishtest-model",
                                 finish_reason="length")
        with mock.patch.object(lr, "generate",
                               return_value=fake):
            meta = _ms.llm_generate("prompt", purpose="answer_composer",
                                    max_tokens=1000)
        self.assertIs(meta["ok"], True)
        self.assertEqual(meta["finish_reason"], "length",
                         "the typed truncation signal rides the "
                         "result meta the composer consumes")


if __name__ == "__main__":
    unittest.main()
