"""tests/benchmark — Coder 2 Phase 4 (B13-B18) adversarial suite.

Every control must:
  * CATCH the defect it exists to catch (adversarial mutations on
    COPIES or crafted fixtures — Art. IX: never mutate production
    artifacts);
  * NOT fire on clean content (Art. V);
  * keep the Phase-3 findings frozen (B13), the adjudicator calibration
    honest (B14: no consensus forcing, misses preserved), the gold set
    human-only (B15: no fabricated labels, blinded export), the unseen
    set permanently sealed with five separated metrics (B16: no
    collapse), the repair register machine-readable and correctly
    owned (B17), and the milestone gate machine-derived (B18).
"""
import copy
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.benchmark import (  # noqa: E402
    adjudicator_calibration as ac)
from discovery_fabric.benchmark import (  # noqa: E402
    auditor_milestone as am)
from discovery_fabric.benchmark import findings_freeze as fz  # noqa: E402
from discovery_fabric.benchmark import gold_semantic_set as gs  # noqa: E402
from discovery_fabric.benchmark import repair_register as rr  # noqa: E402
from discovery_fabric.benchmark import unseen_seal as us  # noqa: E402

BASELINE_DIR = REPO_ROOT / "artifacts/benchmark/baseline"


# ===========================================================================
# B13 — Phase-3 findings freeze
# ===========================================================================
def test_b13_freeze_exists_with_pinned_findings():
    v = fz.verify_phase3_findings_freeze()
    assert v["verdict"] == "INTEGRITY_OK", v
    assert v["baseline"] == {"released": 3, "total": 15, "rejected": 12}
    assert v["domain_reasoning_primary_defect"] == "CONFIRMED"
    assert v["unseen_semantic_failure"] == "CONFIRMED"
    assert v["adjudicator_disagreements"]["status"] == "PRESERVED"
    assert v["adjudicator_disagreements"]["disagreements"] == 26
    assert v["adjudicator_disagreements"]["total_verdicts"] == 30


def test_b13_freeze_chained_to_b7():
    v = fz.verify_phase3_findings_freeze()
    assert v["chain_to_b7"] == "ff537529a6a1fd6c7037a8d455043435" \
                               "4371cc9e2004b2f1178550932ddfce07", v


def test_b13_freeze_refuses_overwrite(tmp_path):
    dst = tmp_path / "findings.json"
    first = fz.freeze_phase3_findings(out_path=dst)
    assert first["action"] == "FROZEN"
    first_bytes = dst.read_bytes()
    again = fz.freeze_phase3_findings(out_path=dst)
    assert again["action"] == "REFUSED"
    assert dst.read_bytes() == first_bytes


def test_b13_detects_finding_mutation(tmp_path):
    dst = tmp_path / "findings.json"
    fz.freeze_phase3_findings(out_path=dst)
    data = json.loads(dst.read_text())
    data["findings"]["BASELINE"]["value"]["released"] = 15
    dst.write_text(json.dumps(data, indent=1))
    v = fz.verify_phase3_findings_freeze(dst)
    assert v["verdict"] == "FINDINGS_FREEZE_MUTATED"


def test_b13_detects_byte_mutation_with_recomputed_content_hash(tmp_path):
    dst = tmp_path / "findings.json"
    fz.freeze_phase3_findings(out_path=dst)
    data = json.loads(dst.read_text())
    data["findings"]["ADJUDICATOR_DISAGREEMENTS"]["value"][
        "disagreements"] = 0
    # attacker recomputes the internal content hash...
    import hashlib
    data["content_sha256"] = hashlib.sha256(json.dumps(
        {k: v for k, v in data.items() if k != "content_sha256"},
        sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    dst.write_text(json.dumps(data, indent=1))
    # ...but the external byte-hash pin still catches it
    v = fz.verify_phase3_findings_freeze(dst)
    assert v["verdict"] == "FINDINGS_FREEZE_MUTATED"


def test_b13_derivation_is_fail_closed_on_tampered_sources(tmp_path,
                                                           monkeypatch):
    # tamper the B8 decomposition COPY so it no longer supports the
    # DOMAIN_REASONING finding -> the freeze must refuse to freeze
    b8 = json.loads((BASELINE_DIR / "REJECTION_DECOMPOSITION.json")
                    .read_text())
    b8["primary_blocker_counts"] = {"GENERICNESS": 12}
    tampered = tmp_path / "REJECTION_DECOMPOSITION.json"
    tampered.write_text(json.dumps(b8))
    monkeypatch.setitem(fz.SOURCE_PATHS, "rejection_decomposition_b8",
                        tampered)
    with pytest.raises(RuntimeError, match="DOMAIN_REASONING"):
        fz._derive_domain_reasoning_defect()


def test_b13_derivation_refuses_wrong_disagreement_count(tmp_path,
                                                         monkeypatch):
    b9 = json.loads((BASELINE_DIR / "BLIND_SEMANTIC_ADJUDICATION.json")
                    .read_text())
    b9["disagreement_count"] = 3
    tampered = tmp_path / "BLIND_SEMANTIC_ADJUDICATION.json"
    tampered.write_text(json.dumps(b9))
    monkeypatch.setitem(fz.SOURCE_PATHS,
                        "blind_semantic_adjudication_b9", tampered)
    with pytest.raises(RuntimeError, match="26/30"):
        fz._derive_adjudicator_disagreements()


# ===========================================================================
# B14 — adjudicator calibration
# ===========================================================================
def _committed_calibration():
    return json.loads((BASELINE_DIR / "ADJUDICATOR_CALIBRATION.json")
                      .read_text())


def test_b14_artifact_has_ceo_metric_keys():
    c = _committed_calibration()
    for key in ("adjudicator_A", "adjudicator_B", "agreement",
                "disagreement", "false_positive", "false_negative",
                "unstable_classes", "instrument_observations"):
        assert key in c, key
    for adj in ("adjudicator_A", "adjudicator_B"):
        for key in ("scored", "agree_gt", "false_positive",
                    "false_negative", "uncertain_defect", "uncertain_clean"):
            assert key in c[adj], (adj, key)


def test_b14_calibration_set_is_independent_and_definite():
    cases = ac.build_calibration_cases()
    assert len(cases) == 12
    # every case's ground truth is justified by an engineering principle
    for case in cases:
        assert case["ground_truth_basis"].strip(), case["case_id"]
        for axis, gt in case["expected"].items():
            assert gt in ("CORRECT", "INCORRECT")
    gts = {gt for c in cases for gt in c["expected"].values()}
    assert gts == {"CORRECT", "INCORRECT"}  # definite cases only
    # clean (false-positive controls) and defective cases both present
    classes = {c["defect_class"] for c in cases}
    assert "CLEAN_CONTROL" in classes
    assert len(classes - {"CLEAN_CONTROL"}) >= 8


def test_b14_no_consensus_forcing_disagreements_preserved():
    c = _committed_calibration()
    rows = c["calibration_rows"]
    disagree_rows = [r for r in rows if r["A_vs_B"] == "DISAGREE"]
    assert disagree_rows, "inter-adjudicator disagreements must be " \
                          "preserved, never resolved"
    for r in disagree_rows:
        assert r["verdict_A"] != r["verdict_B"]
        assert r["verdict_A"] and r["verdict_B"]  # both verdicts kept


def test_b14_fp_fn_semantics_recomputable_from_rows():
    c = _committed_calibration()
    rows = c["calibration_rows"]
    for adj_key, verdict_key in (("adjudicator_A", "verdict_A"),
                                 ("adjudicator_B", "verdict_B")):
        fp = sum(1 for r in rows if r["ground_truth"] == "INCORRECT"
                 and r[verdict_key] == "CORRECT")
        fn = sum(1 for r in rows if r["ground_truth"] == "CORRECT"
                 and r[verdict_key] == "INCORRECT")
        assert c[adj_key]["false_positive"] == fp, adj_key
        assert c[adj_key]["false_negative"] == fn, adj_key


def test_b14_known_misses_are_preserved_not_hidden():
    c = _committed_calibration()
    rows = {r["case_id"]: r for r in c["calibration_rows"]}
    # the reversed-causal-direction case is a known false positive for
    # BOTH adjudicators — the calibration must record it, not bury it
    r = rows["CAL08_CAUSAL_DIRECTION_REVERSED"]
    assert r["ground_truth"] == "INCORRECT"
    assert r["verdict_A"] == "CORRECT" and r["verdict_B"] == "CORRECT"
    # the canonical contradiction is caught by A but missed by B
    r1 = rows["CAL01_ACTIVE_PASSIVE_CONTRADICTION"]
    assert r1["verdict_A"] == "INCORRECT"   # A catches it
    assert r1["verdict_B"] == "CORRECT"     # B misses it (recorded)
    # negation blindness: A blocks a clean passive anchor
    r7 = rows["CAL07_CLEAN_PASSIVE_ANCHOR"]
    assert r7["ground_truth"] == "CORRECT"
    assert r7["verdict_A"] == "INCORRECT"   # A's false negative recorded


def test_b14_rerun_is_deterministic_in_metrics():
    committed = _committed_calibration()
    fresh = ac.run_calibration(out_path=Path("/tmp/_b14_fresh.json"))
    for key in ("adjudicator_A", "adjudicator_B", "agreement",
                "disagreement", "false_positive", "false_negative",
                "unstable_classes", "per_axis"):
        assert fresh[key] == committed[key], key


def test_b14_unstable_rule_is_conservative():
    c = _committed_calibration()
    for axis, s in c["per_axis"].items():
        expected = (s["inter_adjudicator_disagreed"] > 0 or
                    s["false_positives_A_or_B"] > 0 or
                    s["false_negatives_A_or_B"] > 0)
        assert s["unstable"] == expected, axis
    # calibration itself measured instability -> unstable set non-empty
    assert c["unstable_classes"]


def test_b14_adjudicator_code_not_modified_by_calibration():
    # the calibration module must not import-and-patch the adjudicators:
    # structural check — blind_adjudication source has no calibration hook
    src = (REPO_ROOT / "discovery_fabric/benchmark/blind_adjudication.py"
           ).read_text()
    assert "calibrat" not in src.lower()


# ===========================================================================
# B15 — gold semantic set
# ===========================================================================
def test_b15_gold_set_exists_pending_human_review():
    d = json.loads((BASELINE_DIR / "GOLD_SEMANTIC_SET.json").read_text())
    assert d["status"] == "PENDING_HUMAN_REVIEW"
    items = d["items"]
    assert len(items) == 18  # 15 axis judgments + 3 mechanism claims
    for item in items:
        assert item["human_label"] is None
        assert item["label_status"] == "PENDING_HUMAN_REVIEW"
    assert d["label_schema"] == ["CORRECT", "QUESTIONABLE", "INCORRECT"]


def test_b15_human_export_is_blinded():
    export = (BASELINE_DIR /
              "GOLD_SEMANTIC_SET_HUMAN_EXPORT.md").read_text()
    for leak in ("ADJUDICATOR_A", "ADJUDICATOR_B", "FIRST_PRINCIPLES",
                 "SYSTEMS_TRACE"):
        assert leak not in export, leak
    # no verdict values leaked next to items
    assert "INCORRECT (adjudicator" not in export


def test_b15_preregistration_exists_and_precedes_results():
    p = json.loads(
        (BASELINE_DIR / "GOLD_SEMANTIC_PREREGISTRATION.json").read_text())
    assert len(p["verdicts"]) == 18
    assert p["ordering_proof"]
    # the results ledger must not exist yet (no human labels ingested)
    assert not (BASELINE_DIR /
                "GOLD_SEMANTIC_RESULTS.json").exists()


def test_b15_preregistration_refuses_overwrite(tmp_path):
    dst = tmp_path / "prereg.json"
    first = gs.preregister_verdicts(out_path=dst)
    assert first["action"] == "PREREGISTERED"
    again = gs.preregister_verdicts(out_path=dst)
    assert again["action"] == "REFUSED"


def test_b15_gold_set_queue_refuses_overwrite(tmp_path):
    dst = tmp_path / "gold.json"
    first = gs.build_gold_set(set_path=dst, prereg=False)
    assert first["action"] == "WRITTEN"
    again = gs.build_gold_set(set_path=dst, prereg=False)
    assert again["action"] == "REFUSED"


def test_b15_comparison_uses_b14_semantics():
    p = json.loads(
        (BASELINE_DIR / "GOLD_SEMANTIC_PREREGISTRATION.json").read_text())
    ids = [r["item_id"] for r in p["verdicts"]]
    # craft labels that force one FP and one FN against adjudicator A
    a_verdicts = {r["item_id"]: r["ADJUDICATOR_A_FIRST_PRINCIPLES"]
                  for r in p["verdicts"]}
    fp_id = next(i for i, v in a_verdicts.items() if v == "CORRECT")
    fn_id = next(i for i, v in a_verdicts.items() if v == "INCORRECT")
    labels = {i: "QUESTIONABLE" for i in ids}
    labels[fp_id] = "INCORRECT"   # A said CORRECT -> false positive
    labels[fn_id] = "CORRECT"     # A said INCORRECT -> false negative
    result = gs.compare_with_human(labels, rehearsal=True)
    assert result["mode"] == "CONTROLLED_REHEARSAL"
    a = result["adjudicator_A_vs_human"]
    assert a["false_positive"] == 1 and fp_id in a["false_positive_items"]
    assert a["false_negative"] == 1 and fn_id in a["false_negative_items"]
    assert result["rehearsal_disclosure"].startswith(
        "SYNTHETIC_REHEARSAL=TRUE")


def test_b15_ingestion_rejects_rehearsal_and_bad_labels(tmp_path):
    labels_file = tmp_path / "labels.json"
    labels_file.write_text(json.dumps(
        {"reviewer": "REHEARSAL- Synthetic", "labels": {}}))
    with pytest.raises(ValueError, match="rehearsal"):
        gs.ingest_human_labels(labels_file,
                               results_path=tmp_path / "results.json")
    labels_file.write_text(json.dumps(
        {"reviewer": "engineer", "labels": {"NOPE": "CORRECT"}}))
    with pytest.raises(ValueError, match="unknown"):
        gs.ingest_human_labels(labels_file,
                               results_path=tmp_path / "results.json")
    labels_file.write_text(json.dumps(
        {"reviewer": "engineer", "labels": {
            "GOLD-BENCH_01-mechanism_correctness": "MAYBE"}}))
    with pytest.raises(ValueError, match="invalid"):
        gs.ingest_human_labels(labels_file,
                               results_path=tmp_path / "results.json")


def test_b15_status_pending_until_human_labels():
    s = gs.gold_set_status()
    assert s["status"] == "PENDING_HUMAN_REVIEW"
    assert s["human_labeled"] == 0


# ===========================================================================
# B16 — unseen seal + separated metrics
# ===========================================================================
def test_b16_seal_integrity_and_hash_count():
    v = us.verify_seal_integrity()
    assert v["verdict"] == "INTEGRITY_OK"
    assert v["sealed_input_count"] == 4
    manifest = json.loads(
        (BASELINE_DIR / "UNSEEN_PROBLEM_MANIFEST.json").read_text())
    assert sorted(v["sealed_input_hashes"]) == \
        sorted(manifest["unseen_input_hashes"])


def test_b16_seal_acceptance_gate_rejects_tampered_sets():
    from discovery_fabric.benchmark.unseen_problem_test import load_unseen_set
    specs = load_unseen_set()
    assert us.verify_unseen_seal(specs)["verdict"] == "SEALED_SET_MATCH"
    tampered = copy.deepcopy(specs)
    tampered[0]["mechanism"] = "a completely different easier problem"
    r = us.verify_unseen_seal(tampered)
    assert r["verdict"] == "NOT_THE_SEALED_SET"
    assert r["hashes_match"] is False


def test_b16_seal_refuses_overwrite(tmp_path):
    dst = tmp_path / "seal.json"
    assert us.seal_unseen_set(out_path=dst)["action"] == "SEALED"
    assert us.seal_unseen_set(out_path=dst)["action"] == "REFUSED"


def test_b16_metrics_have_exactly_five_separated_keys():
    d = json.loads((BASELINE_DIR / "UNSEEN_RUN_METRICS.json").read_text())
    assert d["metric_keys"] == list(us.METRIC_KEYS)
    for problem in d["problems"]:
        for mode in ("real_mode", "rehearsal_mode_labeled"):
            block = problem.get(mode)
            if not block:
                continue
            metric_keys = {k for k in block
                           if k in tuple(us.METRIC_KEYS) +
                           ("mode", "mode_stamp")}
            assert set(us.METRIC_KEYS) <= set(block), \
                (problem["unseen_id"], mode)
            # exactly the five metrics + mode metadata — nothing else
            assert metric_keys == set(block), \
                (problem["unseen_id"], mode, block.keys())


def test_b16_metrics_match_frozen_b10_numbers():
    d = json.loads((BASELINE_DIR / "UNSEEN_RUN_METRICS.json").read_text())
    agg = d["aggregate"]
    # rehearsal: 4 runs, 3 released, 3 semantic fails, 1 not assessed
    assert agg["rehearsal_mode_labeled"]["runs"] == 4
    assert agg["rehearsal_mode_labeled"]["dossier_release"] == 3
    assert agg["rehearsal_mode_labeled"]["semantic_correctness_fail"] == 3
    assert agg["rehearsal_mode_labeled"]["semantic_correctness_pass"] == 0
    assert agg["rehearsal_mode_labeled"][
        "semantic_correctness_not_assessed"] == 1
    # real: 4 retrieval successes, 0 synthesis (credential block), 0 release
    assert agg["real_mode"]["retrieval_success"] == 4
    assert agg["real_mode"]["synthesis_success"] == 0
    assert agg["real_mode"]["synthesis_blocked_by_credentials"] == 4
    assert agg["real_mode"]["dossier_release"] == 0


def test_b16_credential_block_is_evidence_failure_not_generation():
    d = json.loads((BASELINE_DIR / "UNSEEN_RUN_METRICS.json").read_text())
    for problem in d["problems"]:
        real = problem.get("real_mode") or {}
        syn = real.get("synthesis_success") or {}
        if syn.get("value") is False:
            assert "EVIDENCE_FAILURE" in syn["evidence"]
            # explicit negation: the failure is classified as evidence,
            # NOT generation
            assert "not a generation failure" in syn["evidence"].lower()


def test_b16_collapse_prohibition_is_structural():
    d = json.loads((BASELINE_DIR / "UNSEEN_RUN_METRICS.json").read_text())
    us.assert_no_collapse(d)  # committed report is clean
    bad = copy.deepcopy(d)
    bad["overall_score"] = 0.42
    with pytest.raises(AssertionError, match="collapse violation"):
        us.assert_no_collapse(bad)
    bad2 = copy.deepcopy(d)
    bad2["problems"][0]["composite"] = 1
    with pytest.raises(AssertionError):
        us.assert_no_collapse(bad2)


def test_b16_metrics_refuse_to_report_with_broken_seal(tmp_path,
                                                       monkeypatch):
    seal = json.loads((BASELINE_DIR / "UNSEEN_SET_SEAL.json").read_text())
    seal["sealed_input_hashes"] = ["0" * 64] * 4
    broken = tmp_path / "seal.json"
    broken.write_text(json.dumps(seal))
    with pytest.raises(RuntimeError, match="seal"):
        us.unseen_run_metrics(out_path=tmp_path / "m.json",
                              seal_path=broken)


# ===========================================================================
# B17 — Coder 1 repair register
# ===========================================================================
def _committed_register():
    return json.loads((BASELINE_DIR / "CODER1_REPAIR_REGISTER.json")
                      .read_text())


def test_b17_every_entry_has_ceo_schema():
    d = _committed_register()
    assert d["entry_schema"] == ["problem", "evidence", "failure_class",
                                 "affected_artifact", "expected_change",
                                 "release_blocker"]
    assert len(d["register"]) == 10
    for e in d["register"]:
        for field in d["entry_schema"]:
            assert e[field] not in (None, "", []), (e["id"], field)


def test_b17_all_five_failure_classes_present():
    d = _committed_register()
    classes = {e["failure_class"] for e in d["register"]}
    assert classes == {"GENERATION_FAILURE", "AUDIT_FAILURE",
                       "BENCHMARK_FAILURE", "EVIDENCE_FAILURE",
                       "ENGINEERING_REASONING_FAILURE"}


def test_b17_ownership_prevents_chasing_wrong_problems():
    d = _committed_register()
    by_owner = d["counts"]["by_owner"]
    assert by_owner["CODER1"] == 7
    assert by_owner["CODER2"] == 1            # R-09 audit-layer defect
    assert by_owner["ENVIRONMENT (CEO action required)"] == 1  # R-08
    assert by_owner["CODER1_TEST_SUITE"] == 1  # R-10
    # the environment entry must explicitly tell Coder 1 NOT to chase it
    r08 = next(e for e in d["register"] if e["id"] == "R-08")
    assert "NOT an engine defect" in r08["problem"]
    # the audit entry must be marked as Coder 2's
    r09 = next(e for e in d["register"] if e["id"] == "R-09")
    assert r09["owner"] == "CODER2"
    assert "NOT chase" in r09["problem"]


def test_b17_evidence_counts_match_source_artifacts():
    d = _committed_register()
    b8 = json.loads((BASELINE_DIR / "REJECTION_DECOMPOSITION.json")
                    .read_text())
    r01 = next(e for e in d["register"] if e["id"] == "R-01")
    assert f"{b8['primary_blocker_counts']['DOMAIN_REASONING']}/" \
           f"{len(b8['rejections'])}" in r01["evidence"]["measurement"]
    b16 = json.loads((BASELINE_DIR / "UNSEEN_RUN_METRICS.json").read_text())
    r04 = next(e for e in d["register"] if e["id"] == "R-04")
    assert str(b16["aggregate"]["rehearsal_mode_labeled"]
               ["semantic_correctness_fail"]) in \
        r04["evidence"]["measurement"]


def test_b17_engine_references_are_read_only_pointers():
    d = _committed_register()
    for e in d["register"]:
        arts = e["affected_artifact"]
        for a in arts:
            if a.startswith("discovery_fabric/engine/"):
                assert "read-only" in " ".join(arts).lower(), e["id"]


def test_b17_register_regenerates_deterministically():
    committed = _committed_register()
    fresh = rr.build_repair_register()
    assert fresh["register"] == committed["register"]
    assert fresh["counts"] == committed["counts"]


# ===========================================================================
# B18 — auditor milestone
# ===========================================================================
def test_b18_milestone_defined_with_four_criteria():
    v = am.verify_milestone_definition()
    assert v["verdict"] == "INTEGRITY_OK"
    assert v["milestone_id"] == "B18_NEXT_SUCCESS_MILESTONE_V1"
    m = json.loads((BASELINE_DIR / "AUDITOR_MILESTONE.json").read_text())
    assert len(m["milestone"]["criteria"]) == 4
    assert m["milestone"]["all_criteria_required"] is True


def test_b18_negative_declaration_present():
    m = json.loads((BASELINE_DIR / "AUDITOR_MILESTONE.json").read_text())
    nd = m["negative_declaration"]
    assert nd["engine_world_class"].startswith("NO")
    assert nd["prohibited_substitutes"]


def test_b18_milestone_definition_refuses_overwrite(tmp_path):
    dst = tmp_path / "milestone.json"
    assert am.define_milestone(out_path=dst)["action"] == "DEFINED"
    assert am.define_milestone(out_path=dst)["action"] == "REFUSED"


def test_b18_milestone_definition_detects_mutation(tmp_path):
    dst = tmp_path / "milestone.json"
    am.define_milestone(out_path=dst)
    m = json.loads(dst.read_text())
    m["milestone"]["criteria"] = m["milestone"]["criteria"][:1]
    dst.write_text(json.dumps(m))
    assert am.verify_milestone_definition(
        dst)["verdict"] == "MILESTONE_MUTATED"


def test_b18_current_evaluation_is_not_met_on_c3():
    e = am.evaluate_milestone(write=False)
    assert e["verdict"] == "NOT_MET"
    cr = e["criteria_results"]
    assert cr["C1_SEALED_UNSEEN_RUN"]["met"] is True
    assert cr["C2_DOSSIER_RELEASED"]["met"] is True   # release happens
    assert cr["C3_SEMANTIC_CORRECTNESS"]["met"] is False  # correctness fails
    assert cr["C4_BENCHMARK_HELD_FIXED"]["met"] is True
    assert "NOT world-class" in e["declaration"]


def test_b18_evaluation_detects_instrument_tampering(tmp_path,
                                                     monkeypatch):
    # a milestone whose recorded instrument hash is wrong must fail C4
    am.define_milestone(out_path=tmp_path / "m.json")
    m = json.loads((tmp_path / "m.json").read_text())
    key = next(iter(m["benchmark_fixed_instrument_hashes"]))
    m["benchmark_fixed_instrument_hashes"][key] = "0" * 64
    # recompute content hash so ONLY the instrument table is wrong
    import hashlib
    m["content_sha256"] = hashlib.sha256(json.dumps(
        {k: v for k, v in m.items() if k != "content_sha256"},
        sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    (tmp_path / "m.json").write_text(json.dumps(m))
    monkeypatch.setattr(am, "MILESTONE_PATH", tmp_path / "m.json")
    e = am.evaluate_milestone(write=False)
    assert e["criteria_results"]["C4_BENCHMARK_HELD_FIXED"][
        "met"] is False
    assert e["verdict"] == "NOT_MET"


def test_b18_evaluation_would_flip_only_on_all_criteria(tmp_path):
    # craft metrics in which every released unseen dossier passes
    metrics = json.loads(
        (BASELINE_DIR / "UNSEEN_RUN_METRICS.json").read_text())
    crafted = copy.deepcopy(metrics)
    for p in crafted["problems"]:
        block = p.get("rehearsal_mode_labeled") or {}
        sem = block.get("semantic_correctness")
        if sem and sem.get("value") == "FAIL":
            sem["value"] = "PASS"
    agg = crafted["aggregate"]["rehearsal_mode_labeled"]
    agg["semantic_correctness_fail"] = 0
    agg["semantic_correctness_pass"] = 3
    crafted_path = tmp_path / "crafted_metrics.json"
    crafted_path.write_text(json.dumps(crafted))
    e = am.evaluate_milestone(metrics_path=crafted_path,
                              out_path=tmp_path / "x.json", write=False)
    assert e["verdict"] == "MILESTONE_MET"
    assert e["declaration"].startswith("the defined milestone is MET")


# ===========================================================================
# Cross-cutting: no engine file modified by Phase 4
# ===========================================================================
def test_phase4_touched_no_engine_file():
    # every new module lives in the Coder 2 namespace
    new_modules = [ac.__file__, gs.__file__, us.__file__,
                   rr.__file__, am.__file__, fz.__file__]
    for f in new_modules:
        assert "discovery_fabric/benchmark/" in str(Path(f)), f
        assert "/engine/" not in str(Path(f)), f
