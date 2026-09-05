"""tests/test_r412_attacker_measurement.py — P0-1 measurement harness
seals.

Hermetic: every test runs against the sealed corpus + synthetic attack
records (no LLM, no network). Pins:
  - preflight refuses a mutated corpus (seal discipline, Art. VIII)
  - metric math on fixed synthetic outcomes (exact expected values)
  - conservative-vs-conditional denominators (incompleteness can never
    hide a miss: Art. XV/XXV/LXI)
  - threshold verdict reads the SEALED thresholds (not hardcoded
    numbers; Art. XXVII)
  - agreement between passes + disagreement listing (no ensemble)
  - structured death records: bare "KILLED" finals fall back with
    disclosure; kills with neither objection nor basis are violations
    (ban "KILLED: KILLED")
  - runner resume semantics: decisive cases never re-attacked;
    INCOMPLETE re-queued under the budget, not beyond it
  - pass env pins are pinned for the run and restored after (no leak)
"""
import json
import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
CAL = REPO / "R412" / "CALIBRATION"
sys.path.insert(0, str(CAL))

from calibration_metrics import (  # noqa: E402
    agreement, all_deaths_structured, outcome_of, pass_metrics,
    preflight, structured_death_record, verdict_vs_thresholds)
import calibration_runner as cr  # noqa: E402

CORPUS = json.loads((CAL / "r412_attacker_calibration_corpus.json")
                    .read_text())
SEAL = json.loads((CAL / "r412_calibration_seal.json").read_text())
CASES = CORPUS["cases"]


# ---------------------------------------------------------------------------
# helpers: synthetic attack records
# ---------------------------------------------------------------------------

def _attack(final: str, kills=None, bases=None, status: str = "OK",
            objection: str = ""):
    """Synthetic attack_candidate()-shaped record. `objection` models
    the instrument's final_objection field (the text AFTER 'FINAL:');
    empty -> bare 'KILLED'/'SURVIVED' (the R411 recorded defect
    shape)."""
    kills = kills or []
    final_objection = (
        f"{final} — {objection}" if objection else final)
    return {
        "status": status,
        "verdict": "KILLED" if final == "KILLED" else (
            "SURVIVED" if final == "SURVIVED" else final),
        "kill_surfaces": list(kills),
        "wound_surfaces": [],
        "final_objection": final_objection,
        "surfaces": {
            s: {"basis": (bases or {}).get(s, f"basis for {s}")}
            for s in kills},
        "prompt_hash": "ph" * 8,
        "output_hash": "oh" * 8,
        "attacker_provider": "test",
        "attacker_model": "test-model",
        "independence_mode": "SEPARATE_CONTEXT",
    }


def _attack_for(final, kills=None, objection=""):
    """Map an outcome spec to an attack record, with INCOMPLETE as a
    genuine transport failure (status != OK — Art. LXI)."""
    if final == "INCOMPLETE":
        return {"status": "RATE_LIMITED_RETRY", "verdict": "INCOMPLETE"}
    return _attack(final, kills=kills or [], objection=objection)


def _results(outcomes: dict):
    """outcomes: case_id -> 'KILLED' | 'SURVIVED' | 'INCOMPLETE' |
    ('KILLED', [kill_surfaces], objection_text). Missing case ids are
    'not attacked'."""
    res = []
    for case in CASES:
        spec = outcomes.get(case["case_id"])
        if spec is None:
            continue
        if isinstance(spec, tuple):
            final, kills, obj = (spec + (None, None))[:3]
        else:
            final, kills, obj = spec, None, None
        res.append({
            "case_id": case["case_id"],
            "label": case["ground_truth"]["label"],
            "expected_final": case["ground_truth"]["expected_final"],
            "attack": _attack_for(final, kills, obj or ""),
        })
    return res


def _ids(label: str):
    return [c["case_id"] for c in CASES
            if c["ground_truth"]["label"] == label]


KG, KB, NM, PA = (_ids("KNOWN_GOOD"), _ids("KNOWN_BAD"),
                  _ids("NEAR_MISS"), _ids("PRIOR_ART_COLLISION"))


# ---------------------------------------------------------------------------
# preflight
# ---------------------------------------------------------------------------

class TestPreflight:
    def test_sealed_corpus_passes_preflight(self, tmp_path, monkeypatch):
        pre = preflight(CAL / "r412_attacker_calibration_corpus.json",
                        CAL / "r412_calibration_seal.json")
        assert pre["ok"] is True
        assert pre["corpus_sha256"] == SEAL["corpus_sha256"]

    def test_mutated_corpus_fails_preflight(self, tmp_path):
        mutated = json.loads(json.dumps(CORPUS))
        mutated["cases"][0]["ground_truth"]["label"] = "KNOWN_BAD"
        p = tmp_path / "corpus.json"
        p.write_text(json.dumps(mutated))
        s = tmp_path / "seal.json"
        s.write_text(json.dumps(SEAL))
        pre = preflight(p, s)
        assert pre["ok"] is False
        assert any("sha256" in prob for prob in pre["problems"])

    def test_runner_refuses_mutated_corpus(self, tmp_path, monkeypatch):
        # point the runner at a mutated corpus via monkeypatched paths
        mutated = json.loads(json.dumps(CORPUS))
        mutated["cases"][0]["ground_truth"]["ground_truth_basis"] = "x"
        cpath = tmp_path / "c.json"
        cpath.write_text(json.dumps(mutated))
        monkeypatch.setattr(cr, "CORPUS_PATH", cpath)
        monkeypatch.setattr(cr, "SEAL_PATH", CAL /
                            "r412_calibration_seal.json")
        monkeypatch.setattr(cr, "RUNS_DIR", tmp_path / "runs")
        called = []
        summary = cr.run_pass("minimax-m3", attack_fn=lambda case: (
            called.append(1) or _attack("SURVIVED")))
        assert summary["status"] == "PREFLIGHT_FAILED"
        assert called == []  # no attack ran


# ---------------------------------------------------------------------------
# metric math on fixed synthetic outcomes
# ---------------------------------------------------------------------------

class TestPassMetrics:
    def test_exact_confusion_counts(self):
        # 24 killed positives, 4 survived, 2 INCOMPLETE (still misses:
        # TPR denominator stays 30); 2/10 known-good falsely killed
        outcomes = {}
        for cid in KB + NM + PA:
            outcomes[cid] = "SURVIVED"
        for cid in KB[:8] + NM[:8] + PA[:8]:
            outcomes[cid] = "KILLED"
        outcomes[NM[8]] = "INCOMPLETE"
        outcomes[NM[9]] = "INCOMPLETE"
        outcomes[KG[0]] = "KILLED"
        outcomes[KG[1]] = "KILLED"
        for cid in KG[2:10]:
            outcomes[cid] = "SURVIVED"
        res = _results(outcomes)
        m = pass_metrics(res, CASES)
        assert m["n"] == 40
        pos, neg = m["confusion"]["positives"], m["confusion"]["negatives"]
        assert pos["n"] == 30 and pos["killed"] == 24
        assert pos["TPR"] == 0.8
        assert pos["FNR"] == 0.2
        assert pos["TPR_conditional"] == round(24 / 28, 4)
        assert neg["n"] == 10 and neg["killed"] == 2
        assert neg["FPR"] == 0.2
        assert neg["TNR"] == 0.8
        assert m["false_kills"] == [KG[0], KG[1]]
        assert m["coverage"] == 0.95
        assert m["parse_completeness"] == 0.95

    def test_incomplete_positives_are_misses_conservatively(self):
        # a positive with NO decisive outcome counts as a miss (TPR
        # denominator stays 30) but never as a verdict in either
        # direction
        outcomes = {}
        for cid in KB + NM + PA:
            outcomes[cid] = "KILLED"
        outcomes[KB[0]] = "INCOMPLETE"
        outcomes[KG[0]] = "INCOMPLETE"
        for cid in KG[1:10]:
            outcomes[cid] = "SURVIVED"
        m = pass_metrics(_results(outcomes), CASES)
        pos, neg = m["confusion"]["positives"], m["confusion"]["negatives"]
        assert pos["TPR"] == round(29 / 30, 4)
        assert pos["non_decisive"] == 1
        assert neg["FPR"] == 0.0  # incomplete is NOT a false kill
        assert m["coverage"] == 0.95
        assert m["parse_completeness"] == 0.95

    def test_full_score_scenario_matches_seal_semantics(self):
        # the exact pre-registered threshold semantics: TPR=killed/30,
        # FPR=false-killed/10 over the FULL corpus
        outcomes = {cid: "KILLED" for cid in KB + NM + PA}
        for cid in KG:
            outcomes[cid] = "SURVIVED"
        m = pass_metrics(_results(outcomes), CASES)
        assert m["confusion"]["positives"]["TPR"] == 1.0
        assert m["confusion"]["negatives"]["FPR"] == 0.0
        assert m["false_kill_rate_on_known_good"] == 0.0
        assert m["by_cohort"]["KNOWN_BAD"]["KILLED"] == 10
        assert m["by_cohort"]["NEAR_MISS"]["KILLED"] == 10
        assert m["by_cohort"]["PRIOR_ART_COLLISION"]["KILLED"] == 10

    def test_expected_surface_specificity(self):
        outcomes = {}
        for cid in KB + NM + PA:
            eks = next(c["ground_truth"]["expected_kill_surface"]
                       for c in CASES if c["case_id"] == cid)
            outcomes[cid] = ("KILLED", [eks], "")
        for cid in KG:
            outcomes[cid] = "SURVIVED"
        m = pass_metrics(_results(outcomes), CASES)
        assert m["specificity"][
            "expected_surface_citation_rate"] == 1.0
        assert m["specificity"][
            "killed_positives_expected_surface_cited"] == 30

    def test_outcome_of_transport_failure_is_incomplete(self):
        assert outcome_of({"status": "RATE_LIMITED_RETRY"}) == "INCOMPLETE"
        assert outcome_of({"status": "OK", "verdict": "CONDITIONAL"}) \
            == "CONDITIONAL"
        assert outcome_of({"status": "OK", "verdict": "KILLED"}) == "KILLED"


# ---------------------------------------------------------------------------
# threshold verdict
# ---------------------------------------------------------------------------

class TestThresholdVerdict:
    def test_verdict_uses_sealed_thresholds(self):
        thresholds = SEAL["pre_registered_thresholds"]
        good = {
            "coverage": 0.95, "parse_completeness": 0.95,
            "confusion": {"positives": {"TPR": 0.9},
                          "negatives": {"FPR": 0.1}}}
        bad = {
            "coverage": 0.95, "parse_completeness": 0.95,
            "confusion": {"positives": {"TPR": 0.9},
                          "negatives": {"FPR": 0.5}}}
        assert verdict_vs_thresholds(good, thresholds)["calibrated"] is True
        v = verdict_vs_thresholds(bad, thresholds)
        assert v["calibrated"] is False
        assert v["verdict"] == "NOT_CALIBRATED"
        assert v["checks"]["fpr_max"] is False

    def test_missing_metrics_fail_closed(self):
        thresholds = SEAL["pre_registered_thresholds"]
        v = verdict_vs_thresholds({}, thresholds)
        assert v["calibrated"] is False  # None metrics never pass


# ---------------------------------------------------------------------------
# agreement
# ---------------------------------------------------------------------------

class TestAgreement:
    def test_agreement_and_disagreement_listing(self):
        a_out, b_out = {}, {}
        for cid in KB + NM + PA:
            a_out[cid] = "KILLED"
            b_out[cid] = "KILLED"
        for cid in KG:
            a_out[cid] = "SURVIVED"
            b_out[cid] = "SURVIVED"
        # one disagreement + one case only decisive in pass a
        a_out[KG[0]] = "KILLED"
        b_out[KG[1]] = "INCOMPLETE"
        a_out[NM[0]] = "INCOMPLETE"
        ag = agreement(_results(a_out), _results(b_out))
        assert ag["n_cases_both_decisive"] == 38
        assert ag["n_agree"] == 37
        assert ag["agreement_rate"] == round(37 / 38, 4)
        assert len(ag["disagreements"]) == 1
        assert ag["disagreements"][0]["case_id"] == KG[0]
        assert ag["disagreements"][0]["expected_final"] == "SURVIVED"

    def test_no_ensemble_note_present(self):
        ag = agreement([], [])
        assert "no majority-vote ensemble" in ag["note"]


# ---------------------------------------------------------------------------
# structured death records (ban "KILLED: KILLED")
# ---------------------------------------------------------------------------

class TestStructuredDeathRecords:
    def test_normal_kill_is_fully_structured(self):
        case = next(c for c in CASES if c["case_id"] == KB[0])
        attack = _attack(
            "KILLED", kills=["physics"],
            objection="violates the second law: the claimed 900 W/m2 "
                      "static output exceeds the radiative budget")
        rec = structured_death_record(case, attack)
        for f in ("death_stage", "death_category", "specific_reason",
                  "evidence_refs", "attacker_basis"):
            assert rec.get(f) is not None
        assert rec["death_stage"] == "ATTACK"
        assert rec["death_category"] == "physics"
        assert rec["bare_killed_defect"] is False
        assert rec["fallback_used"] is False
        assert "second law" in rec["specific_reason"]

    def test_bare_killed_falls_back_with_disclosure(self):
        case = next(c for c in CASES if c["case_id"] == KB[0])
        attack = _attack("KILLED", kills=["physics"], objection="")
        rec = structured_death_record(case, attack)
        assert rec["bare_killed_defect"] is True
        assert rec["fallback_used"] is True
        assert "[fallback" in rec["specific_reason"]
        assert "basis for physics" in rec["specific_reason"]

    def test_kill_with_no_reason_at_all_is_a_violation(self):
        case = next(c for c in CASES if c["case_id"] == KB[0])
        attack = _attack("KILLED", kills=[], objection="")
        rec = structured_death_record(case, attack)
        assert rec["bare_killed_defect"] is True
        assert rec["fallback_used"] is False
        assert "[UNSTRUCTURED" in rec["specific_reason"]

    def test_all_deaths_guard_surfaces_violations(self):
        # kills WITH kill-surface bases + bare objection -> the
        # fallback supplies the reason; no violation, disclosed
        outcomes = {cid: ("KILLED", ["physics"], "") for cid in KB[:3]}
        for cid in KB[3:] + NM + PA + KG:
            outcomes[cid] = "SURVIVED"
        res = _results(outcomes)
        m = pass_metrics(res, CASES)
        guard = all_deaths_structured(m["per_case"], CASES, res)
        assert guard["n_killed"] == 3
        assert guard["unstructured_violations"] == []
        assert all(r["fallback_used"] for r in guard["records"])
        # kills with NEITHER objection NOR kill-surface basis:
        # unstructured violations
        outcomes_v = {cid: ("KILLED", [], "") for cid in KB[:2]}
        outcomes_v.update({cid: "SURVIVED"
                           for cid in KB[2:] + NM + PA + KG})
        res_v = _results(outcomes_v)
        m_v = pass_metrics(res_v, CASES)
        guard_v = all_deaths_structured(m_v["per_case"], CASES, res_v)
        assert sorted(guard_v["unstructured_violations"]) == \
            sorted(KB[:2])


# ---------------------------------------------------------------------------
# runner resume semantics
# ---------------------------------------------------------------------------

class TestRunnerResume:
    def test_decisive_cases_never_rerun_incomplete_requeued(self,
                                                            tmp_path,
                                                            monkeypatch):
        monkeypatch.setattr(cr, "RUNS_DIR", tmp_path)
        monkeypatch.setattr(cr, "CORPUS_PATH",
                            CAL / "r412_attacker_calibration_corpus.json")
        # first invocation: kill everything, 2 INCOMPLETE
        outcomes = {cid: "KILLED" for cid in KB + NM + PA}
        for cid in KG:
            outcomes[cid] = "SURVIVED"
        outcomes[KB[0]] = "INCOMPLETE"
        outcomes[KG[0]] = "INCOMPLETE"
        calls = []

        def fake_attack(case):
            calls.append(case["case_id"])
            return _attack_for(outcomes.get(case["case_id"], "SURVIVED"))

        cr.run_pass("minimax-m3", pace_seconds=0, attack_fn=fake_attack)
        assert len(calls) == 40
        # second invocation: only the 2 INCOMPLETE cases are retried
        calls.clear()
        outcomes[KB[0]] = "KILLED"
        cr.run_pass("minimax-m3", pace_seconds=0, attack_fn=fake_attack)
        assert sorted(calls) == [KB[0], KG[0]]
        # third invocation: budget exhausted (attempt 2 was INCOMPLETE
        # for KG[0]) -> nothing pending
        calls.clear()
        cr.run_pass("minimax-m3", pace_seconds=0, attack_fn=fake_attack)
        assert calls == []
        summary = cr._pass_summary("minimax-m3", cr._load_corpus())
        m = summary["metrics"]
        assert m["n"] == 40
        assert m["confusion"]["positives"]["TPR"] == 1.0
        assert m["outcome_counts"]["INCOMPLETE"] == 1

    def test_env_pins_set_during_run_and_restored_after(self, tmp_path,
                                                        monkeypatch):
        monkeypatch.setattr(cr, "RUNS_DIR", tmp_path)
        monkeypatch.setattr(cr, "CORPUS_PATH",
                            CAL / "r412_attacker_calibration_corpus.json")
        for k in ("ENGINE_LLM_PROVIDER", "OPENROUTER_MODEL"):
            monkeypatch.delenv(k, raising=False)
        seen = {}

        def fake_attack(case):
            seen["ENGINE_LLM_PROVIDER"] = os.environ.get(
                "ENGINE_LLM_PROVIDER")
            seen["OPENROUTER_MODEL"] = os.environ.get("OPENROUTER_MODEL")
            return _attack("SURVIVED")

        cr.run_pass("minimax-m3", limit=1, pace_seconds=0,
                    attack_fn=fake_attack)
        assert seen["ENGINE_LLM_PROVIDER"] == "openrouter"
        assert seen["OPENROUTER_MODEL"] == "minimax/minimax-m3:free"
        assert "ENGINE_LLM_PROVIDER" not in os.environ
        assert "OPENROUTER_MODEL" not in os.environ

    def test_report_marks_missing_passes(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cr, "MEASUREMENT_PATH",
                            tmp_path / "measurement.json")
        monkeypatch.setattr(cr, "RUNS_DIR", tmp_path)
        report = cr.build_report(["minimax-m3", "glm-5.3-free"])
        assert report["passes"][0]["status"] == "MISSING"
        assert report["passes"][1]["status"] == "MISSING"
        assert report["calibrated"] is None
        assert "NOT_MEASURED" in report["calibration_verdict"]
        assert report["reviewer_provenance"] == "AI_REVIEW"


# ---------------------------------------------------------------------------
# anti-gaming: the instrument is measured as-deployed
# ---------------------------------------------------------------------------

class TestInstrumentIntegrity:
    def test_instrument_declaration_in_report(self, tmp_path, monkeypatch):
        monkeypatch.setattr(cr, "MEASUREMENT_PATH",
                            tmp_path / "measurement.json")
        monkeypatch.setattr(cr, "RUNS_DIR", tmp_path)
        report = cr.build_report(["minimax-m3"])
        assert report["instrument"][
            "instrument_modified_for_measurement"] is False
        assert report["instrument"]["attack_version"] == "R411-ATTACK-V1"

    def test_no_ensemble_in_any_pass_config(self):
        for pid, pins in cr.PASS_REGISTRY.items():
            assert "vote" not in json.dumps(pins).lower()
