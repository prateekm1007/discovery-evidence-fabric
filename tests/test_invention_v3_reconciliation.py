#!/usr/bin/env python3
"""Tests for invention V3 reconciliation integrity."""
import sys, os, json, pytest
from pathlib import Path

REPO = Path(__file__).parent.parent
MANIFEST_PATH = REPO / "inventions" / "INVENTION_GENERATION_V3_MANIFEST.json"
RAW_DIR = REPO / "inventions" / "v3" / "raw"

VALID_COMMERCIAL = {"A", "B", "C", "D", "UNASSESSED"}
VALID_PIPELINE = {"INVENTION_EVALUATED", "INVENTION_INSUFFICIENT_EVIDENCE",
                  "INVENTION_KILLED", "PIPELINE_CALL_FAILED"}


def load_manifest():
    with open(MANIFEST_PATH) as f:
        return json.load(f)


class TestManifestConsistency:
    def test_manifest_exists(self):
        assert MANIFEST_PATH.exists()

    def test_attempt_count(self):
        m = load_manifest()
        assert m["attempt_count"] == 20

    def test_substantive_plus_failed_equals_attempt(self):
        m = load_manifest()
        assert m["substantive_output_count"] + m["operational_failure_count"] == m["attempt_count"]

    def test_pass_plus_insuf_plus_kill_equals_substantive(self):
        m = load_manifest()
        assert m["PASS"] + m["INSUFFICIENT_EVIDENCE"] + m["KILL"] == m["substantive_output_count"]


class TestInventionIdentity:
    def test_all_invention_ids_unique(self):
        m = load_manifest()
        ids = [i["invention_id"] for i in m["inventions"]]
        assert len(ids) == len(set(ids))

    def test_all_parent_aic_ids_exist(self):
        m = load_manifest()
        for inv in m["inventions"]:
            assert inv["parent_aic_id"], f"{inv['invention_id']}: missing parent_aic_id"

    def test_raw_matches_manifest(self):
        m = load_manifest()
        for inv_summary in m["inventions"]:
            inv_id = inv_summary["invention_id"]
            raw_path = RAW_DIR / f"{inv_id}.json"
            assert raw_path.exists(), f"{inv_id}: raw file missing"
            raw = json.load(open(raw_path))
            assert raw.get("pipeline_status") == inv_summary["pipeline_status"], \
                f"{inv_id}: pipeline_status mismatch raw={raw.get('pipeline_status')} vs manifest={inv_summary['pipeline_status']}"


class TestCommercialEnum:
    def test_all_commercial_valid_enum(self):
        m = load_manifest()
        for inv in m["inventions"]:
            assert inv["commercial_classification"] in VALID_COMMERCIAL, \
                f"{inv['invention_id']}: invalid commercial_classification '{inv['commercial_classification']}'"

    def test_no_free_text_commercial(self):
        m = load_manifest()
        for inv in m["inventions"]:
            c = inv["commercial_classification"]
            assert len(c) <= 10, f"{inv['invention_id']}: commercial_classification too long: '{c}'"

    def test_raw_commercial_normalized(self):
        for i in range(1, 21):
            inv_id = f"INV_V3_{i:03d}"
            raw_path = RAW_DIR / f"{inv_id}.json"
            if not raw_path.exists():
                continue
            raw = json.load(open(raw_path))
            c = raw.get("commercial_classification", "UNASSESSED")
            assert c in VALID_COMMERCIAL, f"{inv_id}: raw commercial not normalized: '{c}'"


class TestPipelineStatus:
    def test_all_pipeline_status_valid(self):
        m = load_manifest()
        for inv in m["inventions"]:
            assert inv["pipeline_status"] in VALID_PIPELINE, \
                f"{inv['invention_id']}: invalid pipeline_status '{inv['pipeline_status']}'"

    def test_pipeline_failures_not_scientific(self):
        m = load_manifest()
        for inv in m["inventions"]:
            if inv["pipeline_status"] == "PIPELINE_CALL_FAILED":
                assert inv["adversarial_state"] == "PIPELINE_CALL_FAILED", \
                    f"{inv['invention_id']}: pipeline failed but adversarial_state is '{inv['adversarial_state']}'"

    def test_no_stage_names_as_status(self):
        m = load_manifest()
        stage_names = {"PASS1_FAILED", "PASS2_FAILED", "PASS3_FAILED", "EXCEPTION"}
        for inv in m["inventions"]:
            assert inv["pipeline_status"] not in stage_names, \
                f"{inv['invention_id']}: stage name used as pipeline_status"

    def test_failed_stage_separate_from_status(self):
        m = load_manifest()
        for inv in m["inventions"]:
            if inv["pipeline_status"] == "PIPELINE_CALL_FAILED":
                assert inv.get("failed_stage") is not None or inv.get("failed_stage") == "", \
                    f"{inv['invention_id']}: failed_stage should be recorded for failed pipelines"


class TestReportFromManifest:
    def test_report_exists(self):
        assert (REPO / "inventions" / "INVENTION_GENERATION_V3_REPORT.md").exists()

    def test_report_contains_manifest_counts(self):
        m = load_manifest()
        report = (REPO / "inventions" / "INVENTION_GENERATION_V3_REPORT.md").read_text()
        assert str(m["attempt_count"]) in report
        assert str(m["substantive_output_count"]) in report


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
