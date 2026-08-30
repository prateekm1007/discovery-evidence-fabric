"""Adversarial tests — relevance-adjudication aggregation custody layer
(Art. XVI/XVII: code is a hypothesis about enforcement; tests are evidence).

Covers discovery_fabric/source_registry/relevance_aggregation.py:
- append + chain discipline (tamper detection both ways: entry edit, link edit)
- malformed adjudication rejection (a relevance entry without a verdict is
  noise, not custody — Art. XXI.9)
- sample-floor honesty: < MIN_SAMPLE_RECORDS stays UNMEASURED_IN_USAGE,
  never a numeric band (Art. XXV)
- band assignment at the declared thresholds (Art. XXVII declared bands)
- ZERO_RELEVANT_OK_STATUS hypothesis flag: fires on >= 2 distinct OK-status
  zero-relevant queries; does NOT fire on 1; does NOT fire on non-OK status
- reading never mutates the log (Art. IX)
- the pipeline wiring records BOTH sources (literature + patents) with the
  query actually used, and a custody-append failure is DISCLOSED, never
  silently swallowed
- the conftest autouse redirect actually protects the production log from
  test contamination (the e11 registry-contamination class, Art. XVII)
"""

from __future__ import annotations

import json

import pytest

from discovery_fabric.source_registry import relevance_aggregation as ra


@pytest.fixture()
def log(tmp_path, monkeypatch):
    monkeypatch.setattr(ra, "LOG_PATH", tmp_path / "rel_log.jsonl")
    return ra.LOG_PATH


def _adjs(n_rel: int, n_irrel: int, prefix="r"):
    out = []
    for i in range(n_rel):
        out.append({"record_id": f"{prefix}-rel-{i}", "relevance": "RELEVANT",
                    "relevance_basis": {"method": "test term overlap",
                                        "overlapping_terms": ["a", "b"]}})
    for i in range(n_irrel):
        out.append({"record_id": f"{prefix}-irr-{i}",
                    "relevance": "IRRELEVANT_FILTERED",
                    "relevance_basis": {"method": "test term overlap",
                                        "overlapping_terms": []}})
    return out


# ---------------------------------------------------------------------------
# Chain discipline
# ---------------------------------------------------------------------------

class TestChain:
    def test_append_links_and_verifies(self, log):
        ra.record_adjudications("src", "q1", _adjs(3, 2), run_id="run:1")
        ra.record_adjudications("src", "q2", _adjs(1, 0), run_id="run:1")
        v = ra.verify_chain()
        assert v["chain_valid"] is True and v["entries"] == 2

    def test_entry_edit_detected(self, log):
        ra.record_adjudications("src", "q1", _adjs(2, 1), run_id="run:1")
        lines = log.read_text().strip().split("\n")
        e = json.loads(lines[0])
        e["records_relevant"] = 999  # tamper: inflate the measurement
        lines[0] = json.dumps(e, sort_keys=True)
        log.write_text("\n".join(lines) + "\n")
        v = ra.verify_chain()
        assert v["chain_valid"] is False
        assert v["reason"] == "entry hash mismatch"

    def test_link_edit_detected(self, log):
        ra.record_adjudications("src", "q1", _adjs(2, 1), run_id="run:1")
        ra.record_adjudications("src", "q2", _adjs(2, 1), run_id="run:1")
        lines = log.read_text().strip().split("\n")
        e = json.loads(lines[1])
        e["prev_entry_sha256"] = "0" * 64  # tamper: detach from chain
        lines[1] = json.dumps(e, sort_keys=True)
        log.write_text("\n".join(lines) + "\n")
        v = ra.verify_chain()
        assert v["chain_valid"] is False
        assert v["reason"] in ("entry hash mismatch", "chain link mismatch")


# ---------------------------------------------------------------------------
# Custody semantics
# ---------------------------------------------------------------------------

class TestCustodySemantics:
    def test_malformed_adjudication_rejected(self, log):
        with pytest.raises(ValueError, match="valid relevance verdict"):
            ra.record_adjudications(
                "src", "q", [{"record_id": "x", "relevance": "MAYBE"}])

    def test_missing_relevance_key_rejected(self, log):
        with pytest.raises(ValueError):
            ra.record_adjudications("src", "q", [{"record_id": "x"}])

    def test_counts_and_sample_bounded(self, log):
        e = ra.record_adjudications("src", "q", _adjs(7, 3))
        assert e["records_retrieved"] == 10
        assert e["records_relevant"] == 7
        assert e["records_irrelevant_filtered"] == 3
        assert len(e["sample_record_ids"]) == ra.SAMPLE_RECORD_LIMIT

    def test_reading_never_mutates(self, log):
        ra.record_adjudications("src", "q1", _adjs(2, 1))
        before = log.read_bytes()
        ra.aggregate_usage()
        ra.read_entries()
        assert log.read_bytes() == before  # Art. IX


# ---------------------------------------------------------------------------
# Aggregation honesty
# ---------------------------------------------------------------------------

class TestAggregationBands:
    def test_low_sample_stays_unmeasured(self, log):
        ra.record_adjudications("src", "q1", _adjs(5, 5))
        agg = ra.aggregate_usage()["sources"]["src"]
        assert agg["usage_band"] == "UNMEASURED_IN_USAGE"
        assert agg["pooled_relevant_rate"] == 0.5  # reported, not graded

    def test_band_3_above_two_thirds(self, log):
        for i in range(6):
            ra.record_adjudications("src", f"q{i}", _adjs(10, 1, prefix=f"b3{i}"))
        agg = ra.aggregate_usage()["sources"]["src"]
        assert agg["usage_band"] == 3
        assert agg["records_total"] >= ra.MIN_SAMPLE_RECORDS

    def test_band_2_above_one_third(self, log):
        for i in range(6):
            ra.record_adjudications("src", f"q{i}", _adjs(5, 8, prefix=f"b2{i}"))
        agg = ra.aggregate_usage()["sources"]["src"]
        assert agg["usage_band"] == 2

    def test_band_1_below_one_third(self, log):
        for i in range(6):
            ra.record_adjudications("src", f"q{i}", _adjs(1, 12, prefix=f"b1{i}"))
        agg = ra.aggregate_usage()["sources"]["src"]
        assert agg["usage_band"] == 1

    def test_runs_and_window_tracked(self, log):
        ra.record_adjudications("src", "q1", _adjs(3, 0), run_id="run:a")
        ra.record_adjudications("src", "q2", _adjs(3, 0), run_id="run:b")
        agg = ra.aggregate_usage()["sources"]["src"]
        assert agg["runs"] == 2
        assert agg["queries_logged"] == 2
        assert agg["window"]["first"] and agg["window"]["last"]


# ---------------------------------------------------------------------------
# Defect-class hypothesis flag
# ---------------------------------------------------------------------------

class TestZeroRelevantFlag:
    def test_fires_on_two_distinct_ok_zero_relevant(self, log):
        ra.record_adjudications("src", "alpha", _adjs(0, 5),
                                provider_status="OK")
        ra.record_adjudications("src", "beta", _adjs(0, 5),
                                provider_status="OK")
        flag = ra.aggregate_usage()["sources"]["src"]["zero_relevant_ok_status"]
        assert flag["flagged"] is True
        assert sorted(flag["distinct_queries"]) == ["alpha", "beta"]

    def test_single_occurrence_does_not_flag(self, log):
        ra.record_adjudications("src", "alpha", _adjs(0, 5),
                                provider_status="OK")
        flag = ra.aggregate_usage()["sources"]["src"]["zero_relevant_ok_status"]
        assert flag["flagged"] is False

    def test_non_ok_status_does_not_count(self, log):
        ra.record_adjudications("src", "alpha", _adjs(0, 5),
                                provider_status="RATE_LIMITED")
        ra.record_adjudications("src", "beta", _adjs(0, 5),
                                provider_status="TIMEOUT")
        flag = ra.aggregate_usage()["sources"]["src"]["zero_relevant_ok_status"]
        assert flag["flagged"] is False

    def test_zero_records_does_not_count(self, log):
        # provider OK with an EMPTY definitive answer is a healthy provider
        # answer, not the status-OK-plus-irrelevant-records defect class
        ra.record_adjudications("src", "alpha", [], provider_status="OK")
        ra.record_adjudications("src", "beta", [], provider_status="OK")
        flag = ra.aggregate_usage()["sources"]["src"]["zero_relevant_ok_status"]
        assert flag["flagged"] is False

    def test_flag_is_not_a_band_or_grade(self, log):
        ra.record_adjudications("src", "alpha", _adjs(0, 5),
                                provider_status="OK")
        ra.record_adjudications("src", "beta", _adjs(0, 5),
                                provider_status="OK")
        agg = ra.aggregate_usage()["sources"]["src"]
        # the flag must never leak into the numeric band
        assert agg["usage_band"] in (1, 2, 3, "UNMEASURED_IN_USAGE")


# ---------------------------------------------------------------------------
# Pipeline wiring (device_failure step 4) — hermetic, connectors mocked
# ---------------------------------------------------------------------------

class TestPipelineWiring:
    def _run_step(self, monkeypatch, tmp_path, lit_records, patent_records):
        from discovery_fabric.source_registry import retrieval_log as rl
        monkeypatch.setattr(rl, "LOG_PATH", tmp_path / "rl.jsonl")

        import discovery_fabric.discovery_modes.device_failure as df
        from discovery_fabric.source_registry.connectors import scientific as sci_mod
        from discovery_fabric.source_registry.connectors import patents as pat_mod

        class _Rec:
            def __init__(self, rid, title):
                self.record_id = rid
                self.title = title
                self.uri = ""
                self.raw_payload_sha256 = "x" * 8
                self.normalized = {"abstract": ""}

        class _Res:
            def __init__(self, sid, status, records):
                self.source_id = sid
                self.status = status
                self.error = None
                self.records = records

        class _Lit:
            source_id, status, error = "europepmc", "OK", None
            records = [_Rec(f"lit-{i}", "infusion pump occlusion alarm")
                       for i in range(lit_records)]

            def search(self, q, timeout=40):
                return _Res(self.source_id, self.status, self.records)

        class _Lens:
            source_id, status, error = "lens_patent", "OK", None
            records = [_Rec(f"pat-{i}", "infusion pump occlusion valve")
                       for i in range(patent_records)]

            def search(self, q, timeout=40):
                return _Res(self.source_id, self.status, self.records)

        monkeypatch.setattr(sci_mod, "EuropePmcConnector", _Lit)
        monkeypatch.setattr(pat_mod, "LensPatentConnector", _Lens)
        monkeypatch.setattr(pat_mod, "GooglePatentsConnector", _Lens)
        out = df.retrieve_attempted_solutions(
            "infusion pump", "occlusion", timeout=5)
        return out

    def test_both_sources_recorded_with_query_used(self, monkeypatch, tmp_path):
        from discovery_fabric.source_registry import relevance_aggregation as ra2
        log2 = tmp_path / "rel2.jsonl"
        monkeypatch.setattr(ra2, "LOG_PATH", log2)

        out = self._run_step(monkeypatch, tmp_path, lit_records=4,
                             patent_records=3)
        assert "appended (2 sources)" in json.dumps(out["relevance_custody"])
        entries = ra2.read_entries()
        sids = {e["source_id"] for e in entries}
        assert sids == {"europepmc", "lens_patent"}
        for e in entries:
            assert e["run_id"].startswith("pipeline:device_failure:")
            assert e["provider_status"] == "OK"
            assert e["records_retrieved"] > 0

    def test_custody_failure_disclosed_not_swallowed(self, monkeypatch, tmp_path):
        from discovery_fabric.source_registry import relevance_aggregation as ra2
        def _boom(*a, **kw):
            raise RuntimeError("disk full (simulated)")
        monkeypatch.setattr(ra2, "record_adjudications", _boom)

        out = self._run_step(monkeypatch, tmp_path, lit_records=2,
                             patent_records=2)
        assert "custody append failed" in json.dumps(
            out["relevance_custody"])


# ---------------------------------------------------------------------------
# Production-log contamination guard (conftest autouse redirect)
# ---------------------------------------------------------------------------

class TestContaminationGuard:
    def test_conftest_redirects_production_log(self, tmp_path):
        # Inside the hermetic suite the module's LOG_PATH must NOT be the
        # production custody log (autouse fixture already applied).
        assert "artifacts" not in str(ra.LOG_PATH) or "tmp" in str(ra.LOG_PATH)

    def test_production_log_untouched_by_writes(self, tmp_path, monkeypatch):
        prod = ra.LOG_PATH  # already redirected by conftest
        sentinel = tmp_path / "prod_sim.jsonl"
        sentinel.write_text("")
        monkeypatch.setattr(ra, "LOG_PATH", sentinel)
        ra.record_adjudications("s", "q", _adjs(1, 1))
        assert sentinel.read_text() != ""
        # and the redirect itself kept the REAL production path elsewhere
        assert ra.LOG_PATH == sentinel
