#!/usr/bin/env python3
"""R504 — hermetic tests for the RBG battery v4.1 corpus-leg-only MODE.

The mode is an instrument scope extension (Art. VII disclosed — the v3.1
precedent: MODE only, no fixture re-authored, no expectation changed).
These tests pin the mode's invariants:

  1. ONLY F12/F13 are measured; F1-F11 are TYPED SKIPS (pass=null) —
     never passes, never failures, never verdicts (Art. XXV/LXI).
  2. ZERO PatentBear debits: no PatentBear transport is constructed in
     corpus mode (the shared bucket stands 19/20, the last debit
     preserved) — the quota ledger is empty.
  3. The verdict sequence covers the two measured fixtures only; with a
     LIVE free layer (mocked) all_fixtures_pass is True.
  4. The full and patent-leg modes are byte-identical in behavior — the
     mode cannot have changed them (battery_version stays "4").
  5. ADVERSARIAL: the skips can never offset a failing measured fixture.
  6. The seal record is scope-typed: BOTH standing leg seals (R495
     Scopus 3/3, R498 patent-leg 3/3) are referenced, never re-claimed.
  7. The seal driver passes --corpus-leg-only to the battery subprocess;
     the two mode flags are mutually exclusive (exit 2).
  8. No novelty verdict exists in any record (Art. XLVI).

No live provider is contacted by this suite (mocked layers only); the
live seal is the repetition-based measurement, run separately (R502).
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
class FakeFreeSourceLayer:
    """The R499-measured free-source states, frozen for hermetic pinning
    (the same stub contract the R498 mode tests use; +R504: the
    credential_mode field the wired layer records per measurement)."""

    name = "free_sources"

    MEASURED = {
        "hf_hub_catalog": {"state": "LIVE_200",
                           "credential_mode": "ANONYMOUS",
                           "dataset_count_returned": 100,
                           "role": "DISCOVERY_LISTING_COUNT_SIGNAL_ONLY"},
        "hf_corpus_rows": {"state": "LIVE_200",
                           "credential_mode": "AUTHENTICATED_HF_TOKEN",
                           "rows_returned": 2,
                           "has_long_text_field": True,
                           "role": "CONTENT_BEARING_COVERAGE_SOURCE"},
        "hf_corpus_size_served_view": {"state": "LIVE_200",
                                       "credential_mode": "AUTHENTICATED_HF_TOKEN",
                                       "measured_num_rows_served": 131755,
                                       "role": "CLAIM_VERIFICATION_EVIDENCE"},
        "google_github_substrate": {"state": "LIVE_200",
                                    "role": "TOOLING_DOCS_SUBSTRATE"},
        "epo_ops_boundary": {"state": "CREDENTIAL_REQUIRED",
                             "role": "KEYLESS_BOUNDARY_MEASUREMENT"},
        "uspto_portal_shape": {"state": "WEB_SHELL_NOT_JSON_API",
                               "role": "KEYLESS_SHAPE_MEASUREMENT"},
        "patentsview_reachability": {"state": "DNS_UNRESOLVED_THIS_ENVIRONMENT",
                                     "role": "ENVIRONMENT_REACHABILITY_MEASUREMENT"},
    }

    def __init__(self):
        self.measured = {}

    def self_measure(self):
        import copy
        self.measured = copy.deepcopy(self.MEASURED)
        return self.measured

    def fetch_dataset_rows(self, dataset, config, split, length=2):
        # the R499 smoke measured AUTH_FAILED (datasets-server answers 403
        # for nonexistent ids) -- the F13-measured reality, mocked
        return "AUTH_FAILED", None

    def coverage_declaration(self):
        m = self.measured or self.self_measure()
        rows_m = m.get("hf_corpus_rows", {})
        covered = bool(rows_m.get("state") == "LIVE_200"
                       and rows_m.get("rows_returned")
                       and rows_m.get("has_long_text_field"))
        return {
            "coverage_statement": ("CORPUS_COVERAGE_LIVE_THIS_RUN" if covered
                                   else "PATENT_CORPUS_BLIND_FOR_THIS_RUN"),
            "live_content_sources": ["hf_corpus_rows"] if covered else [],
            "per_source_states": {k: v.get("state") for k, v in m.items()},
            "measured_num_rows_served": 131755,
            "brief_claim_verification": "EXTERNAL_CLAIM_UNVERIFIED_AT_SERVED_VIEW",
            "not_a_novelty_verdict": True,
        }


class SpyLayer(FakeFreeSourceLayer):
    """Records whether ANY metered transport was constructed."""

    constructed = []


@pytest.fixture
def no_credentials(monkeypatch):
    for k in ("ELSEVIER_API_KEY", "PATENTBEAR_API_KEY",
              "LENS_API_KEY", "PATSNAP_API_KEY", "HF_TOKEN"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(g, "FreePatentSourceLayer", FakeFreeSourceLayer)
    # corpus mode must NEVER construct a DEBIT-BEARING transport (the
    # PatentBear layer spends a search debit on self-measurement; the
    # bear transport on a record fetch). ScopusTransport() construction
    # is network-free and debit-free, so it is not guarded (the battery
    # constructs it before the mode branches; F1-F8 never CALL it in
    # corpus mode).
    class Boom:
        def __init__(self, *a, **k):
            raise AssertionError("debit-bearing transport constructed in "
                                 "a hermetic corpus-mode test")

    monkeypatch.setattr(g, "PatentTransportLayer", Boom)
    monkeypatch.setattr(g, "PatentBearTransport", Boom)


# ---------------------------------------------------------------- tests
def test_corpus_mode_measures_only_f12_f13(no_credentials):
    rep = b.run_battery("C1", corpus_leg_only=True)
    measured = [f for f in rep["fixtures"] if not f.get("skipped")]
    skipped = {f["fixture_id"]: f for f in rep["fixtures"] if f.get("skipped")}
    assert [f["fixture_id"] for f in measured] == ["F12", "F13"]
    assert set(skipped) == {"F1", "F2", "F3", "F4", "F5", "F6",
                            "F7", "F8", "F9", "F10", "F11"}
    for f in skipped.values():
        assert f["pass"] is None                     # neither pass nor fail
        assert f["observed_verdict"] == "SKIPPED_UNCONFIGURED_THIS_RUN"
        # BOTH standing leg seals referenced, never re-claimed
        assert "R495_RBG_SEAL_RECORD" in f["details"]["standing_seal_reference"]
        assert "R498_RBG_PATENT_LEG_SEAL_RECORD" in \
            f["details"]["standing_seal_reference"]
    assert rep["battery_mode"] == "corpus_leg_only"
    assert rep["battery_version"] == "4.1"           # the disclosed v4.1 mode


def test_corpus_mode_zero_metered_debits(no_credentials):
    rep = b.run_battery("C2", corpus_leg_only=True)
    assert rep["patentbear_quota_ledger"] == []
    # no provider coverage statement exists in this mode's scope
    assert rep["patent_coverage_declaration"]["state"] == "OUT_OF_SCOPE_THIS_MODE"
    assert rep["anchor_record_custody"]["state"] == "SKIPPED_UNCONFIGURED_THIS_RUN"


def test_corpus_mode_live_mock_all_pass(no_credentials):
    rep = b.run_battery("C3", corpus_leg_only=True)
    by_id = {f["fixture_id"]: f for f in rep["fixtures"]}
    assert by_id["F12"]["observed_verdict"] == g.CORPUS_COVERED
    assert by_id["F12"]["pass"] is True
    assert by_id["F13"]["observed_verdict"] == "CORPUS_ATTACK_REFUSED"
    assert by_id["F13"]["pass"] is True
    assert rep["all_fixtures_pass"] is True
    assert rep["observed_verdict_sequence"] == [g.CORPUS_COVERED,
                                                "CORPUS_ATTACK_REFUSED"]
    assert rep["verdict_sequence_sha256"] == g.sha256(
        "|".join(rep["observed_verdict_sequence"]))


def test_corpus_mode_skips_never_offset_failure(no_credentials, monkeypatch):
    """A failing MEASURED fixture must fail the repetition even with
    eleven skipped fixtures -- a skip is never a compensating verdict."""
    class BrokenFreeLayer(FakeFreeSourceLayer):
        MEASURED = dict(FakeFreeSourceLayer.MEASURED)
        MEASURED["hf_corpus_rows"] = dict(
            FakeFreeSourceLayer.MEASURED["hf_corpus_rows"],
            has_long_text_field=False)   # the content-bearing state fails

        def coverage_declaration(self):
            m = self.measured or self.self_measure()
            return {
                "coverage_statement": "PATENT_CORPUS_BLIND_FOR_THIS_RUN",
                "live_content_sources": [],
                "per_source_states": {k: v.get("state") for k, v in m.items()},
                "measured_num_rows_served": 131755,
                "brief_claim_verification": "EXTERNAL_CLAIM_UNVERIFIED",
                "not_a_novelty_verdict": True,
            }

    monkeypatch.setattr(g, "FreePatentSourceLayer", BrokenFreeLayer)
    rep = b.run_battery("C4", corpus_leg_only=True)
    assert rep["all_fixtures_pass"] is False         # honest fail


def test_full_and_patent_modes_unchanged(no_credentials, monkeypatch):
    # the corpus guard must not have moved ANY other mode's behavior: the
    # full battery is 13 measured fixtures, the patent leg 4, versions "4"
    # (the corpus flag cannot leak into the other modes). The debit-bearing
    # transports get inert fakes here (these modes legitimately construct
    # them; the Boom guard is a corpus-mode-only invariant).
    class InertLayer:
        def __init__(self, *a, **k):
            self.measured = {"patentbear": {"status": g.T_UNCONFIGURED,
                                            "evidence": "absent (inert)"}}

        def status(self):
            return g.T_UNCONFIGURED

        def live_providers(self):
            return []

        def blind_declaration(self):
            return {"transport": "patent_layer", "status": self.status(),
                    "live_providers": self.live_providers(),
                    "provider_measurements": dict(self.measured),
                    "declaration": "PATENT_BLIND_FOR_THIS_RUN",
                    "coverage_statement": None}

    class InertBear:
        def __init__(self, *a, **k):
            pass

        def fetch_record_text(self, pid):
            return g.T_SEARCH_FAILED, None, {}

    monkeypatch.setattr(g, "PatentTransportLayer", InertLayer)
    monkeypatch.setattr(g, "PatentBearTransport", InertBear)
    full = b.run_battery("C5", patent_leg_only=False, corpus_leg_only=False)
    assert full["battery_version"] == "4"
    assert full["battery_mode"] == "full"
    assert len(full["observed_verdict_sequence"]) == 13
    leg = b.run_battery("C6", patent_leg_only=True, corpus_leg_only=False)
    assert leg["battery_version"] == "4"
    assert leg["battery_mode"] == "patent_leg_only"
    # the corpus flag cannot silently leak into the other modes
    assert leg["skipped_fixture_ids"] == ["F1", "F2", "F3", "F4", "F5", "F7", "F8"]


def test_seal_record_corpus_scope_typing():
    reps = [{"repetition_id": "R%d" % i, "all_fixtures_pass": True,
             "verdict_sequence_sha256": "a" * 64,
             "observed_verdicts": ["CORPUS_COVERAGE_LIVE_THIS_RUN",
                                   "CORPUS_ATTACK_REFUSED"]}
            for i in (1, 2, 3)]
    seal = rbg_seal.compute_seal(reps, 3, "R502", corpus_leg_only=True)
    assert seal["sealed"] is True
    assert seal["seal_id"] == "R502_RBG_CORPUS_LEG_SEAL"
    assert "CORPUS_LEG_ONLY" in seal["scope"]
    claims = " ".join(seal["explicitly_not_claimed"])
    assert "NOT sealed" in claims or "not sealed" in claims
    assert "db336e97" in claims   # the standing Scopus seal referenced
    assert "2e0545a3" in claims   # the standing patent-leg seal referenced
    assert seal["other_legs_status"]["state"] == "NOT_MEASURED_THIS_RUN"
    assert seal["seal_id"] != "R502_RBG_SEAL"        # never the full id
    assert seal["seal_id"] != "R502_RBG_PATENT_LEG_SEAL"


def test_seal_driver_corpus_flag_and_mutual_exclusion(monkeypatch, tmp_path):
    captured = {}

    class FakeProc:
        returncode = 0
        stderr = ""
        stdout = json.dumps({
            "repetition_id": "R1", "all_fixtures_pass": True,
            "verdict_sequence_sha256": "c" * 64,
            "observed_verdicts": ["CORPUS_COVERAGE_LIVE_THIS_RUN",
                                  "CORPUS_ATTACK_REFUSED"]}) + "\n"

    def fake_run(argv, **kw):
        captured["argv"] = argv
        return FakeProc()

    monkeypatch.setattr(subprocess, "run", fake_run)
    rbg_seal.run_repetitions(str(tmp_path), 1, "R502", corpus_leg_only=True)
    assert captured["argv"][-1] == "--corpus-leg-only"
    assert captured["argv"][1].endswith("rbg_battery.py")
    # the default (full) invocation must NOT carry the flag
    rbg_seal.run_repetitions(str(tmp_path), 1, "R502")
    assert "--corpus-leg-only" not in captured["argv"]
    # CLI-level mutual exclusion: undo the fake_run patch first, then both
    # real drivers must refuse the flag pair (exit 2)
    monkeypatch.undo()
    proc = subprocess.run(
        [sys.executable, os.path.join(RBG, "rbg_battery.py"), "X",
         str(tmp_path / "o.json"), "--patent-leg-only", "--corpus-leg-only"],
        capture_output=True, text=True)
    assert proc.returncode == 2
    proc2 = subprocess.run(
        [sys.executable, os.path.join(RBG, "rbg_seal.py"), str(tmp_path),
         "--patent-leg-only", "--corpus-leg-only"],
        capture_output=True, text=True)
    assert proc2.returncode == 2


def test_no_novelty_word_in_corpus_records(no_credentials):
    """Art. XLVI: no novelty verdict exists in any scope."""
    rep = b.run_battery("C8", corpus_leg_only=True)
    blob = json.dumps(rep)
    for bad in ("IS_NOVEL", "NOVELTY_VERDICT", "novelty_proven",
                "NOVELTY_CONFIRMED"):
        assert bad not in blob
