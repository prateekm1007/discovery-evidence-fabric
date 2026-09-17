#!/usr/bin/env python3
"""R498 — hermetic tests for the RBG battery v3.1 patent-leg-only MODE.

The mode is an instrument scope extension (Art. VII disclosed; no fixture
re-authored, no expectation changed). These tests pin the mode's invariants:

  1. Scopus fixtures become TYPED SKIPS (pass=null) -- never passes,
     never failures, never verdicts (Art. XXV/LXI).
  2. The verdict sequence covers measured fixtures only.
  3. The full battery is byte-identical in behavior (11 fixtures,
     original order, no skips) -- the mode cannot have changed it.
  4. With a LIVE patent provider (mocked), the patent leg passes end to
     end and all_fixtures_pass reflects ONLY the measured fixtures.
  5. ADVERSARIAL: skips can never offset a failing measured fixture.
  6. The seal record is scope-typed and explicitly not-claiming the full
     battery or the Scopus side.
  7. The seal driver passes --patent-leg-only to the battery subprocess.

No live provider is contacted by this suite (mocked transports only);
the live seal is the repetition-based measurement, run separately.
"""
import json
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
RBG = os.path.join(HERE, "..", "scripts", "r495_rbg")
sys.path.insert(0, RBG)

import rbg_gate as g  # noqa: E402
import rbg_battery as b  # noqa: E402
import rbg_seal  # noqa: E402


# ---------------------------------------------------------------- mocks
MOCK_TITLE = "Hydrocephalus shunt valve with anti-siphon control"
MOCK_ABSTRACT = ("A cerebrospinal fluid shunt valve assembly for "
                 "hydrocephalus management with pressure regulation.")
MOCK_HITS = [{"id": "US0000001B2", "title": MOCK_TITLE,
              "abstract": MOCK_ABSTRACT}]
MOCK_RECORD_TEXT = ("%s\n\nThe present invention relates to shunt valve "
                    "assemblies. %s Additional body text for the record."
                    % (MOCK_TITLE, MOCK_ABSTRACT))
MOCK_USAGE = {"allowed": True, "monthly_limit": 20,
              "monthly_used": 9, "monthly_remaining": 11}


class FakeLayer:
    """Stands in for rbg_gate.PatentTransportLayer. Garbage keys measure
    AUTH_FAILED (the R497-measured 401 boundary); the default constructor
    measures LIVE with the mock payload."""

    name = "patent_layer"

    def __init__(self, lens_key=None, patsnap_key=None,
                 patentbear_key=None, measure=True):
        garbage = (patentbear_key is not None
                   and patentbear_key.startswith("pb_live_")
                   and set(patentbear_key[8:]) == {"0"})
        if garbage:
            self.measured = {
                "lens": {"status": g.T_UNCONFIGURED, "evidence": "absent"},
                "patsnap": {"status": g.T_UNCONFIGURED, "evidence": "absent"},
                "patentbear": {"status": g.T_AUTH_FAILED,
                               "evidence": "measured 401 boundary"},
            }
        else:
            self.measured = {
                "lens": {"status": g.T_UNCONFIGURED, "evidence": "absent"},
                "patsnap": {"status": g.T_UNCONFIGURED, "evidence": "absent"},
                "patentbear": {"status": g.T_LIVE,
                               "evidence": "mocked LIVE",
                               "usage": dict(MOCK_USAGE),
                               "search_hits": [dict(h) for h in MOCK_HITS]},
            }

    def status(self):
        states = [v["status"] for v in self.measured.values()]
        if g.T_LIVE in states:
            return g.T_LIVE
        if all(s == g.T_UNCONFIGURED for s in states):
            return g.T_UNCONFIGURED
        return "AUTH_INCOMPLETE"

    def live_providers(self):
        return [k for k, v in self.measured.items()
                if v["status"] == g.T_LIVE]

    def blind_declaration(self):
        live = self.live_providers()
        return {
            "transport": self.name,
            "status": self.status(),
            "live_providers": live,
            "provider_measurements": dict(self.measured),
            "declaration": None if live else "PATENT_BLIND_FOR_THIS_RUN",
            "coverage_statement": g.T_COVERED if live else None,
        }


class FakeTransport:
    """Stands in for rbg_gate.PatentBearTransport; record text is
    configurable per-test (the adversarial test removes the abstract)."""

    record_text = MOCK_RECORD_TEXT

    def __init__(self, api_key=None):
        self.api_key = api_key or "mock"

    def fetch_record_text(self, pid):
        meta = {"record_id": pid, "usage": dict(MOCK_USAGE),
                "fetched_text_sha256": g.sha256(self.record_text),
                "fetched_text_len": len(self.record_text)}
        return g.T_LIVE, self.record_text, meta


@pytest.fixture
def mocked_live_patents(monkeypatch):
    monkeypatch.setattr(g, "PatentTransportLayer", FakeLayer)
    monkeypatch.setattr(g, "PatentBearTransport", FakeTransport)
    # the battery references these THROUGH the module: rbg_battery.g is
    # rbg_gate, so patching rbg_gate attributes is sufficient


@pytest.fixture
def no_credentials(monkeypatch):
    for k in ("ELSEVIER_API_KEY", "PATENTBEAR_API_KEY",
              "LENS_API_KEY", "PATSNAP_API_KEY"):
        monkeypatch.delenv(k, raising=False)


# ---------------------------------------------------------------- tests
def test_mode_skips_scopus_fixtures_with_typed_skip(no_credentials):
    rep = b.run_battery("T1", patent_leg_only=True)
    skipped = {f["fixture_id"]: f for f in rep["fixtures"]
               if f.get("skipped")}
    assert set(skipped) == {"F1", "F2", "F3", "F4", "F5", "F7", "F8"}
    for f in skipped.values():
        assert f["pass"] is None                     # neither pass nor fail
        assert f["observed_verdict"] == "SKIPPED_UNCONFIGURED_THIS_RUN"
        assert "R495_RBG_SEAL_RECORD" in \
            f["details"]["standing_seal_reference"]
    assert rep["battery_mode"] == "patent_leg_only"
    assert rep["battery_version"] == "3.1"


def test_skips_excluded_from_verdict_sequence(no_credentials):
    rep = b.run_battery("T2", patent_leg_only=True)
    assert rep["skipped_fixture_ids"] == ["F1", "F2", "F3", "F4",
                                          "F5", "F7", "F8"]
    # without credentials the patent leg is blind -> 4 measured verdicts
    assert len(rep["observed_verdict_sequence"]) == 4
    assert "SKIPPED_UNCONFIGURED_THIS_RUN" not in \
        rep["observed_verdict_sequence"]
    assert rep["all_fixtures_pass"] is False         # honest: cannot pass


def test_full_mode_unchanged(no_credentials):
    rep = b.run_battery("T3", patent_leg_only=False)
    ids = [f["fixture_id"] for f in rep["fixtures"]]
    assert ids == ["F1", "F2", "F3", "F4", "F5", "F6", "F9",
                   "F7", "F8", "F10", "F11"]
    assert rep["skipped_fixture_ids"] == []
    assert len(rep["observed_verdict_sequence"]) == 11
    assert rep["battery_mode"] == "full"


def test_patent_leg_live_mock_all_pass(no_credentials, mocked_live_patents):
    rep = b.run_battery("T4", patent_leg_only=True)
    by_id = {f["fixture_id"]: f for f in rep["fixtures"]}
    assert by_id["F6"]["observed_verdict"] == g.T_COVERED
    assert by_id["F9"]["observed_verdict"] == "BLINDNESS_RETAINED"
    assert by_id["F10"]["observed_verdict"] == g.V_COLLISION
    assert by_id["F10"]["details"]["byte_verdict_title"] == g.V_VERIFIED
    assert by_id["F10"]["details"]["byte_verdict_abstract"] == g.V_VERIFIED
    assert by_id["F11"]["observed_verdict"] == g.V_REFUTED
    assert rep["all_fixtures_pass"] is True
    assert len(rep["observed_verdict_sequence"]) == 4
    # quota ledger carries both usage objects (layer search + record fetch)
    assert len(rep["patentbear_quota_ledger"]) == 2


def test_adversarial_skips_never_offset_failure(
        no_credentials, mocked_live_patents, monkeypatch):
    """A failing MEASURED fixture must fail the repetition even with seven
    skipped fixtures -- a skip can never be counted as compensating."""
    class BrokenTransport(FakeTransport):
        record_text = MOCK_RECORD_TEXT.replace(MOCK_ABSTRACT,
                                               "some other text entirely")

    monkeypatch.setattr(g, "PatentBearTransport", BrokenTransport)
    rep = b.run_battery("T5", patent_leg_only=True)
    by_id = {f["fixture_id"]: f for f in rep["fixtures"]}
    assert by_id["F10"]["observed_verdict"] != g.V_COLLISION  # abstract not bound
    assert rep["all_fixtures_pass"] is False


def test_seal_record_scope_typing():
    reps = [{"repetition_id": "R1", "all_fixtures_pass": True,
             "verdict_sequence_sha256": "a" * 64,
             "observed_verdicts": ["x", "y", "z", "w"]},
            {"repetition_id": "R2", "all_fixtures_pass": True,
             "verdict_sequence_sha256": "a" * 64,
             "observed_verdicts": ["x", "y", "z", "w"]},
            {"repetition_id": "R3", "all_fixtures_pass": True,
             "verdict_sequence_sha256": "a" * 64,
             "observed_verdicts": ["x", "y", "z", "w"]}]
    seal = rbg_seal.compute_seal(reps, 3, "R498", patent_leg_only=True)
    assert seal["sealed"] is True
    assert seal["seal_id"] == "R498_RBG_PATENT_LEG_SEAL"
    assert "PATENT_LEG_ONLY" in seal["scope"]
    assert any("NOT sealed" in c or "not sealed" in c
               for c in seal["explicitly_not_claimed"])
    assert seal["scopus_side_status"]["state"] == "NOT_MEASURED_THIS_RUN"
    # the full-battery seal id must NOT be produced by the mode
    assert seal["seal_id"] != "R498_RBG_SEAL"


def test_seal_driver_passes_flag_to_battery(monkeypatch, tmp_path):
    captured = {}

    class FakeProc:
        returncode = 0
        stderr = ""
        stdout = json.dumps({
            "repetition_id": "R1", "all_fixtures_pass": True,
            "verdict_sequence_sha256": "b" * 64,
            "observed_verdicts": ["p", "q", "r", "s"]}) + "\n"

    def fake_run(argv, **kw):
        captured["argv"] = argv
        return FakeProc()

    monkeypatch.setattr(subprocess, "run", fake_run)
    rbg_seal.run_repetitions(str(tmp_path), 1, "R498",
                             patent_leg_only=True)
    assert captured["argv"][-1] == "--patent-leg-only"
    assert captured["argv"][1].endswith("rbg_battery.py")
    # and the default (full) invocation must NOT carry the flag
    rbg_seal.run_repetitions(str(tmp_path), 1, "R498",
                             patent_leg_only=False)
    assert "--patent-leg-only" not in captured["argv"]


def test_no_novelty_word_in_mode_records(no_credentials, mocked_live_patents):
    """Art. XLVI: no novelty verdict exists in any scope -- the mode's
    records must not introduce one."""
    rep = b.run_battery("T8", patent_leg_only=True)
    blob = json.dumps(rep)
    for bad in ("IS_NOVEL", "NOVELTY_VERDICT", "novelty_proven",
                "NOVELTY_CONFIRMED"):
        assert bad not in blob
