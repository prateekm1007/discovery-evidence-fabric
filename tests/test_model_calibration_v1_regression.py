"""Model calibration v1 regression tests."""
import pytest, json, sys
from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
MC_DIR = REPO_ROOT / "experiments" / "model_calibration_v1"

class TestModelCalibrationV1:
    def test_protocol_exists(self):
        assert (MC_DIR / "PROTOCOL.json").exists()
        assert (MC_DIR / "PROTOCOL.sha256").exists()
    def test_gemma_results_exist(self):
        assert (MC_DIR / "GEMMA_RESULTS.json").exists()
    def test_nemotron_results_exist(self):
        assert (MC_DIR / "NEMOTRON_RESULTS.json").exists()
    def test_model_comparison_exists(self):
        assert (MC_DIR / "MODEL_COMPARISON.md").exists()
    def test_report_exists(self):
        assert (MC_DIR / "REPORT.md").exists()
    def test_gemma_20_cases(self):
        data = json.loads((MC_DIR / "GEMMA_RESULTS.json").read_text())
        assert len(data["per_case"]) == 20
    def test_nemotron_20_cases(self):
        data = json.loads((MC_DIR / "NEMOTRON_RESULTS.json").read_text())
        assert len(data["per_case"]) == 20
    def test_gemma_metrics_recorded(self):
        data = json.loads((MC_DIR / "GEMMA_RESULTS.json").read_text())
        for k in ["overall_accuracy", "103_accuracy", "103_precision", "false_reject_rate"]:
            assert k in data["metrics"]
    def test_nemotron_metrics_recorded(self):
        data = json.loads((MC_DIR / "NEMOTRON_RESULTS.json").read_text())
        for k in ["overall_accuracy", "103_accuracy", "103_precision", "false_reject_rate"]:
            assert k in data["metrics"]
    def test_gemma_status_blocked(self):
        data = json.loads((MC_DIR / "GEMMA_RESULTS.json").read_text())
        assert data["metrics"]["status"] == "CALIBRATION_BLOCKED"
    def test_nemotron_status_blocked(self):
        data = json.loads((MC_DIR / "NEMOTRON_RESULTS.json").read_text())
        assert data["metrics"]["status"] == "CALIBRATION_BLOCKED"
    def test_models_are_opposites(self):
        """Gemma should be aggressive (high 103 TP), Nemotron conservative (0 103 TP)."""
        g = json.loads((MC_DIR / "GEMMA_RESULTS.json").read_text())["metrics"]
        n = json.loads((MC_DIR / "NEMOTRON_RESULTS.json").read_text())["metrics"]
        # Gemma finds obviousness (TP > 0)
        assert g["103_tp"] > 0
        # Nemotron finds almost no obviousness (TP == 0 or very low)
        assert n["103_tp"] <= 2
