"""V3.8 regression tests."""
import pytest, json, sys
from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
from discovery_fabric.prior_art_v2.obviousness_v38 import ObviousnessEvidenceV38, OBVIOUSNESS_ADVERSARY_V38_PROMPT_HASH
from archive.r455_retired.discovery_fabric.prior_art_v2.calibration_v3_8 import CaseResultV38, calculate_v38_metrics
V38_DIR = REPO_ROOT / "experiments" / "autonomous_calibration_v3_8"

class TestV38Results:
    def test_protocol_exists(self):
        assert (V38_DIR / "PROTOCOL.json").exists()
        assert (V38_DIR / "PROTOCOL.sha256").exists()
    def test_all_artifacts_exist(self):
        for f in ["PROTOCOL.json","PROTOCOL.sha256","PROTOCOL.md","METRICS.json","REPORT.md","103_CASE_FORENSICS.json","ERROR_ANALYSIS.json","GROUND_TRUTH.json"]:
            assert (V38_DIR / f).exists(), f"Missing: {f}"
    def test_20_cases(self):
        m = json.loads((V38_DIR / "METRICS.json").read_text())
        assert m["metrics"]["total_cases"] == 20
    def test_status_blocked(self):
        m = json.loads((V38_DIR / "METRICS.json").read_text())
        assert m["metrics"]["status"] == "CALIBRATION_BLOCKED"
    def test_103_accuracy_improved(self):
        """V3.8 103 accuracy should be significantly better than V3.7 (30%)."""
        m = json.loads((V38_DIR / "METRICS.json").read_text())
        assert m["metrics"]["103_accuracy"] >= 0.50  # was 30% in V3.7
    def test_hindsight_high_zero(self):
        """V3.8 hindsight fix: 0 HIGH (was 17 in V3.7)."""
        m = json.loads((V38_DIR / "METRICS.json").read_text())
        assert m["metrics"]["hindsight_high"] == 0
    def test_motivation_edges_improved(self):
        """V3.8 avg motivation edges should be > 1 (was 0.15 in V3.7)."""
        m = json.loads((V38_DIR / "METRICS.json").read_text())
        assert m["metrics"]["avg_motivation_edges"] > 1.0
    def test_102_accuracy_preserved(self):
        m = json.loads((V38_DIR / "METRICS.json").read_text())
        assert m["metrics"]["102_accuracy"] >= 0.85
    def test_v3_7_preserved(self):
        v37 = REPO_ROOT / "experiments" / "autonomous_calibration_v3_7"
        assert (v37 / "METRICS.json").exists()
