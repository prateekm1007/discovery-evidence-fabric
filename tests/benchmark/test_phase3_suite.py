"""tests/benchmark — Coder 2 Phase 3 (B7-B12) adversarial suite.

Every new control must:
  * CATCH the defect class it exists to catch (adversarial mutations on
    COPIES or crafted fixtures — Art. IX: never mutate production runs);
  * NOT fire on clean content (Art. V: no universal rejector);
  * keep the B7 freeze immutable (double-hash pinned), the unseen
    content out of the repository (B10), the disagreements preserved
    (B9), and human review un-automatable (B11).
"""
import json
import shutil
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.benchmark import (  # noqa: E402
    blind_adjudication as ba)
from discovery_fabric.benchmark import failure_taxonomy as ft
from discovery_fabric.benchmark import human_spot_check as hsc
from discovery_fabric.benchmark import independent_freeze as ifz
from discovery_fabric.benchmark import rejection_decomposition as rd
from discovery_fabric.benchmark import unseen_problem_test as upt

BASELINE_DIR = REPO_ROOT / "artifacts/benchmark/baseline"


# ===========================================================================
# B7 — independent baseline freeze
# ===========================================================================
def test_b7_freeze_exists_with_pinned_numbers():
    v = ifz.verify_independent_baseline()
    assert v["verdict"] == "INTEGRITY_OK", v
    assert v["baseline_release_yield"] == {"released": 3, "total": 15}
    assert v["quality_rejections"] == {"rejected": 12, "total": 15}


def test_b7_freeze_is_hash_chained_to_b1():
    v = ifz.verify_independent_baseline()
    assert v["chain_to_b1"] == "db161312c5c50140aa89c7a00525fe87a161335" \
                               "a043b0592b1b7abe0957042ea", v


def test_b7_freeze_refuses_overwrite(tmp_path):
    dst = tmp_path / "freeze.json"
    pin = tmp_path / "freeze.json.bytehash"
    result = ifz.freeze_independent_baseline(out_path=dst)
    assert result["action"] == "FROZEN"
    first_bytes = dst.read_bytes()
    again = ifz.freeze_independent_baseline(out_path=dst)
    assert again["action"] == "REFUSED"
    assert dst.read_bytes() == first_bytes  # untouched


def test_b7_detects_content_mutation(tmp_path):
    dst = tmp_path / "freeze.json"
    ifz.freeze_independent_baseline(out_path=dst)
    data = json.loads(dst.read_text())
    data["baseline_release_yield"] = {"released": 15, "total": 15}
    dst.write_text(json.dumps(data, indent=1))
    v = ifz.verify_independent_baseline(dst)
    assert v["verdict"] == "BASELINE_MUTATED"


def test_b7_detects_byte_mutation_with_valid_content_hash(tmp_path):
    # an attacker who recomputes the content hash but changes the bytes
    # is still caught by the external byte-hash pin
    dst = tmp_path / "freeze.json"
    ifz.freeze_independent_baseline(out_path=dst)
    data = json.loads(dst.read_text())
    data["note_added_by_attacker"] = "the baseline is now great"
    import hashlib
    data["content_sha256"] = ifz.sha256_obj(
        {k: v for k, v in data.items() if k != "content_sha256"})
    dst.write_text(json.dumps(data, indent=1, ensure_ascii=False))
    v = ifz.verify_independent_baseline(dst)
    assert v["verdict"] == "BASELINE_MUTATED"
    assert "byte hash mismatch" in v["reason"]


def test_b7_external_sha256sum_reproduces_pin():
    import hashlib
    pin = BASELINE_DIR / "INDEPENDENT_BASELINE_FREEZE.bytehash"
    assert pin.exists(), "byte-hash pin file missing"
    actual = hashlib.sha256(
        (BASELINE_DIR / "INDEPENDENT_BASELINE_FREEZE.json")
        .read_bytes()).hexdigest()
    assert actual == pin.read_text(encoding="utf-8").strip()


# ===========================================================================
# B8 — rejection decomposition
# ===========================================================================
def test_b8_all_twelve_rejections_decomposed():
    art = json.loads(
        (BASELINE_DIR / "REJECTION_DECOMPOSITION.json").read_text())
    assert art["rejections_decomposed"] == 12
    assert art["expected_rejections"] == 12
    for r in art["rejections"]:
        assert r["PRIMARY_BLOCKER"] in rd.BLOCKER_TAXONOMY
        assert r["PRIMARY_BLOCKER"] != "OTHER" or not r["SECONDARY_BLOCKERS"]
        for s in r["SECONDARY_BLOCKERS"]:
            assert s in rd.BLOCKER_TAXONOMY
        # every blocker row names its evidence source
        for row in r["blocker_ladder"]:
            for ev in row["evidence"]:
                assert ev["source"] in ("ENGINE_GATE_RE_DERIVED",
                                        "INDEPENDENT_CODER2")


def test_b8_no_shallow_label_left():
    # the point of B8: no rejection may be left as merely "shallow"
    art = json.loads(
        (BASELINE_DIR / "REJECTION_DECOMPOSITION.json").read_text())
    for r in art["rejections"]:
        assert r["PRIMARY_BLOCKER"] in rd.BLOCKER_TAXONOMY
        assert "shallow" not in r["PRIMARY_BLOCKER"].lower()


def test_b8_ranking_gate_fail_outranks_independent_severity3():
    evidence = [
        {"category": "CAUSAL_REASONING", "severity": 3,
         "source": "INDEPENDENT_CODER2", "detail": {"x": 1}},
        {"category": "DOMAIN_REASONING", "severity": 4,
         "source": "ENGINE_GATE_RE_DERIVED", "detail": {"x": 2}},
    ]
    primary, secondary, ladder = rd.rank_blockers(evidence)
    assert primary == "DOMAIN_REASONING"  # direct gate cause first
    assert "CAUSAL_REASONING" in secondary


def test_b8_ranking_other_never_outranks_named_category():
    evidence = [
        {"category": "OTHER", "severity": 4,
         "source": "INDEPENDENT_CODER2", "detail": {}},
        {"category": "FAILURE_ANALYSIS", "severity": 2,
         "source": "INDEPENDENT_CODER2", "detail": {}},
    ]
    primary, secondary, _ = rd.rank_blockers(evidence)
    assert primary == "FAILURE_ANALYSIS"
    assert "OTHER" in secondary


def test_b8_ranking_correctness_precedence_within_tier():
    evidence = [
        {"category": "TRANSFER_SPECIFICITY", "severity": 3,
         "source": "INDEPENDENT_CODER2", "detail": {}},
        {"category": "CAUSAL_REASONING", "severity": 3,
         "source": "INDEPENDENT_CODER2", "detail": {}},
    ]
    primary, _, _ = rd.rank_blockers(evidence)
    assert primary == "CAUSAL_REASONING"


def test_b8_primary_matches_frozen_baseline_count():
    art = json.loads(
        (BASELINE_DIR / "REJECTION_DECOMPOSITION.json").read_text())
    total = sum(art["primary_blocker_counts"].values())
    assert total == 12


# ===========================================================================
# B9 — blind semantic adjudication
# ===========================================================================
def test_b9_module_independence_no_b3_b4_reuse():
    # the adjudication layer must not IMPORT the benchmark author's
    # semantic detectors (structural check via AST, not text: the
    # docstring legitimately names them in the independence contract)
    import ast
    src = Path(ba.__file__).read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert node.module is None or not (
                node.module.startswith("discovery_fabric.benchmark."
                                       "semantic")), \
                f"adjudicator imports benchmark detector: {node.module}"
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.startswith(
                    "discovery_fabric.benchmark.semantic"), \
                    f"adjudicator imports benchmark detector: " \
                    f"{alias.name}"
    # and the runtime namespace holds no detector modules
    assert not any(hasattr(ba, n) for n in ("sc_mod", "sg_mod",
                                            "semantic_causal",
                                            "semantic_genericness"))


def _mk_run(tmp_path, eng, inv, problem=None, envelope=None):
    d = tmp_path / "RUN"
    d.mkdir()
    (d / "ENGINEERING_SPECIFICATION.json").write_text(json.dumps(eng))
    (d / "INVENTION_SPECIFICATION.json").write_text(json.dumps(inv))
    (d / "problem.json").write_text(json.dumps(
        problem or {"problem_id": "t:1", "device": "x",
                    "failure_mode": "THERMAL_INJURY", "failure": "f",
                    "constraint": "c"}))
    (d / "candidate_envelope.json").write_text(json.dumps(
        envelope or {"mechanism_map": {}}))
    (d / "DISCOVERY_RELEASE.json").write_text(json.dumps(
        {"status": "RELEASED"}))
    return d


def _base_inv(mechanism, intervention="the intervention", effect="the "
             "effect", span=None):
    return {"mechanism": {"value": {
        "mechanism": mechanism, "intervention": intervention,
        "expected_effect": effect,
        "mechanism_source_span": span if span is not None else mechanism,
    }}}


def _base_eng(fms=None, vms=None, equations=None, chains=None,
              arch="passive mechanical architecture", validation=None):
    return {
        "mechanism_architecture": arch,
        "system_architecture": arch,
        "design_outputs": [],
        "design_inputs": [],
        "failure_analysis": fms or [],
        "verification_matrix": vms or [],
        "validation_matrix": validation or [],
        "engineering_core": {"governing_model": {
            "equations": equations or []}},
        "engineering_reasoning_chains": {"chains": chains or []},
        "design_graph": {"counts": {}, "linkage_maps": {
            "fm_parent_do": {}, "do_parent_di": {}}},
        "kill_condition": "",
    }


def test_b9_adjudicator_a_catches_control_contradiction():
    inv = _base_inv("adaptive scheduler adjusts transmit power to hold "
                    "the link margin under exposure limits")
    eng = _base_eng(
        arch="adaptive control architecture with feedback")
    eng["design_outputs"] = [{
        "id": "DO-016", "kind": "architecture_block", "parent_ids": [],
        "description": "No closed-loop control is proposed: the "
                       "invention operates passively/open-loop as "
                       "specified", "status": "CONCEPTUAL",
        "missing_inputs": [], "basis": "ENGINEERING_PROPOSED"}]
    a = ba.adjudicate_a(eng, inv, ["implant telemetry node",
                                   "adaptive transmit power"])
    assert a["classified_family"] == "rf"
    classes = [f["class"] for f in
               a["axes"]["mechanism_correctness"]["findings"]]
    assert "CONTROL_ARCHITECTURE_CONTRADICTION" in classes
    assert a["axes"]["mechanism_correctness"]["verdict"] == "INCORRECT"


def test_b9_adjudicator_a_consistent_passive_mechanism_passes():
    inv = _base_inv("graded porosity diffuser spreads flow to reduce "
                    "stagnant zones where tissue ingrowth starts")
    eng = _base_eng(arch="passive flow-path architecture")
    eng["design_outputs"] = [{
        "id": "DO-016", "kind": "architecture_block", "parent_ids": [],
        "description": "No closed-loop control is proposed: the "
                       "invention operates passively/open-loop as "
                       "specified", "status": "CONCEPTUAL",
        "missing_inputs": [], "basis": "ENGINEERING_PROPOSED"}]
    a = ba.adjudicate_a(eng, inv, ["CSF shunt system", "graded porosity "
                                   "diffuser reduces tissue ingrowth"])
    classes = [f["class"] for f in
               a["axes"]["mechanism_correctness"]["findings"]]
    assert "CONTROL_ARCHITECTURE_CONTRADICTION" not in classes


def test_b9_adjudicator_a_catches_wrong_quantity_verification():
    inv = _base_inv("distributed current steering spreads dissipation "
                    "across multiple electrode contact sites")
    fms = [{
        "graph_id": "FM-001", "failure_mode": "electrode heating",
        "mode": "TISSUE_INJURY",
        "physical_mechanism": "current density raises local tissue "
                              "temperature above the safety margin",
        "verification_test": "bit error rate sweep across implant depth",
        "design_control": "current steering pattern",
        "kill_condition": "if temperature exceeds margin, kill"}]
    eng = _base_eng(fms=fms, vms=[{
        "id": "VF-001", "requirement": "r", "method": "m",
        "result": "NOT_TESTED", "invention_tie": "tie",
        "acceptance": "temperature rise below 2 C", "acceptance_status":
            "ESTABLISHED"}])
    a = ba.adjudicate_a(eng, inv, ["implantable neuromodulation lead",
                                   "current steering reduces tissue "
                                   "heating"])
    classes = [f["class"] for f in
               a["axes"]["verification_appropriateness"]["findings"]]
    assert "VERIFICATION_MEASURES_WRONG_QUANTITY" in classes
    assert a["axes"]["verification_appropriateness"]["verdict"] == \
        "INCORRECT"


def test_b9_adjudicator_b_catches_unclosed_chains():
    inv = _base_inv("mechanism text long enough to pass the substance "
                    "floor with physical quantities like pressure and "
                    "flow words present")
    chain = {"chain_id": "RC-1", "subject": "equation:E-1", "nodes": [
        {"node_type": "CLAIM", "content": "claim", "parent_ids": [],
         "provenance": {"refs": {}, "evidence_ids": []}},
        {"node_type": "FAILURE_MODE", "content": "x", "parent_ids": [],
         "provenance": {"refs": {"failure_mode_ids": []}}},
        {"node_type": "VERIFICATION", "content": "x", "parent_ids": [],
         "provenance": {"refs": {"verification_ids": []}}},
    ]}
    eng = _base_eng(chains=[chain])
    b = ba.adjudicate_b(eng, inv, ["device"])
    classes = [f["class"] for f in
               b["axes"]["engineering_reasoning_correctness"]["findings"]]
    assert "NO_CHAIN_CLOSED_TO_FAILURE_AND_VERIFICATION" in classes


def test_b9_disagreement_preserved_not_resolved(tmp_path):
    # A flags the control contradiction (INCORRECT); B sees traceable
    # mechanism + substance (CORRECT) -> DISAGREMENT recorded with BOTH
    inv = _base_inv("adaptive scheduler adjusts transmit power to hold "
                    "the link margin under exposure limits while reducing "
                    "local power density")
    eng = _base_eng(arch="adaptive control architecture with feedback")
    eng["design_outputs"] = [{
        "id": "DO-016", "kind": "architecture_block", "parent_ids": [],
        "description": "No closed-loop control is proposed: the "
                       "invention operates passively/open-loop as "
                       "specified", "status": "CONCEPTUAL",
        "missing_inputs": [], "basis": "ENGINEERING_PROPOSED"}]
    d = _mk_run(
        tmp_path, eng, inv,
        problem={"problem_id": "t:1", "device": "implant telemetry node",
                 "failure_mode": "LINK_LOSS", "failure": "telemetry "
                 "dropout at implant depth", "constraint": "SAR limits"},
        envelope={"mechanism_map": {
            "mechanism": "adaptive scheduler adjusts transmit power to "
                         "hold the link margin",
            "intervention": "adaptive-power telemetry firmware",
            "expected_effect": "reliable link within SAR limits"}})
    record = {"run_dir": str(d), "set": "COMMITTED", "name": "TEST_01"}
    row = ba.adjudicate_sample(record)
    mc = row["axes"]["mechanism_correctness"]
    assert row["adjudicator_a_family"] == "rf"
    va = mc[ba.ADJUDICATOR_A]["verdict"]
    vb = mc[ba.ADJUDICATOR_B]["verdict"]
    if va != vb:
        assert mc["recorded_verdict"] == "DISAGREEMENT"
        assert mc["agreement"] is False
        assert any(x["axis"] == "mechanism_correctness"
                   for x in row["disagreements"])
        # both verdicts preserved verbatim
        dg = [x for x in row["disagreements"]
              if x["axis"] == "mechanism_correctness"][0]
        assert dg[ba.ADJUDICATOR_A] == va
        assert dg[ba.ADJUDICATOR_B] == vb
        assert dg["resolution"] == "NONE — preserved as disagreement " \
                                   "(CEO B9)"


def test_b9_artifact_disagreements_survive():
    art = json.loads(
        (BASELINE_DIR / "BLIND_SEMANTIC_ADJUDICATION.json").read_text())
    assert art["population"]["released_dossiers_total"] == 8
    assert art["sampling"]["seed"] == 20260828
    assert art["disagreement_count"] > 0  # real disagreements exist
    for row in art["samples"]:
        if row["publication"]["set"] == "BLIND_RELEASED":
            # blind-safe: hash-keyed id, no content fields
            assert row["publication"]["sample_id"].startswith("BLIND_")
            assert row["sample"].get("run_dir") is None


def test_b9_adjudicators_never_read_coder1_labels():
    # neither adjudicator's signature accepts an E15-B verdict argument
    import inspect
    for fn in (ba.adjudicate_a, ba.adjudicate_b):
        params = list(inspect.signature(fn).parameters)
        assert "quality" not in " ".join(params)
        assert "e15" not in " ".join(params).lower()


# ===========================================================================
# B10 — unseen-problem test
# ===========================================================================
def test_b10_manifest_hashes_only_no_content():
    art = json.loads(
        (BASELINE_DIR / "UNSEEN_PROBLEM_MANIFEST.json").read_text())
    assert art["unseen_input_count"] == 4
    assert len(art["unseen_input_hashes"]) == 4
    # no expected-answer VALUES exist anywhere in the manifest: the only
    # expected-answer field is the disclosure whose value starts NONE
    assert art["evaluation_blindness"]["expected_answer_key"].startswith(
        "NONE")

    def walk_for_expected(o):
        hits = []
        if isinstance(o, dict):
            for k, v in o.items():
                if "expected" in str(k).lower() and k != \
                        "expected_answer_key":
                    hits.append(k)
                hits += walk_for_expected(v)
        elif isinstance(o, list):
            for v in o:
                hits += walk_for_expected(v)
        return hits
    assert walk_for_expected(art) == []


def test_b10_unseen_content_absent_from_tracked_files():
    specs = upt.load_unseen_set()
    import re
    import subprocess
    tracked = subprocess.run(["git", "ls-files"], cwd=REPO_ROOT,
                             capture_output=True,
                             text=True).stdout.splitlines()
    blob_parts = []
    for rel in tracked:
        p = REPO_ROOT / rel
        if p.suffix in (".py", ".json", ".md", ".txt", ".yml", ".yaml"):
            try:
                blob_parts.append(p.read_text(encoding="utf-8",
                                              errors="replace").lower())
            except Exception:
                pass
    blob = "\n".join(blob_parts)
    for s in specs:
        words = [w for w in re.findall(r"[a-z]+",
                                       s["mechanism"].lower())
                 if len(w) > 3]
        for i in range(len(words) - 2):
            gram = " ".join(words[i:i + 3])
            assert gram not in blob, (
                f"UNSEEN CONTENT LEAK: '{gram}' is tracked in the repo")


def test_b10_unseen_runs_are_gitignored():
    gi = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "artifacts/benchmark/unseen/" in gi


def test_b10_distinctness_rejects_near_duplicate():
    # a spec whose mechanism copies a committed input must FAIL
    from discovery_fabric.benchmark.corpus_runner import BENCHMARK_INPUTS
    c = BENCHMARK_INPUTS[0]
    fake = dict(domain=c["domain"], device=c["device"],
                failure_mode=c["failure_mode"], failure=c["failure"],
                constraint=c["constraint"], mechanism=c["mechanism"],
                intervention=c["intervention"], effect=c["effect"],
                fals=c["fals"])
    v = upt.verify_unseen_inputs([fake, fake, fake, fake])
    assert v["verdict"] == "FAIL"
    assert not v["distinct_from_committed_and_blind"]


def test_b10_real_mode_failure_attributed_to_evidence():
    art = json.loads(
        (BASELINE_DIR / "UNSEEN_PROBLEM_MANIFEST.json").read_text())
    real = art["UNSEEN_PROBLEM_RELEASE"]["real_mode"]
    assert real["runs"] == 4
    for r in art["real_mode_runs"]:
        assert "EVIDENCE_FAILURE" in r["failure_attribution"] or \
            r["release_status"] == "RELEASED"
        assert "GENERATION_FAILURE" not in r["failure_attribution"]


# ===========================================================================
# B11 — human spot-check
# ===========================================================================
def test_b11_queue_schema_and_pending_status():
    q = json.loads(
        (BASELINE_DIR / "HUMAN_SPOT_CHECK_QUEUE.json").read_text())
    assert q["status"] == "PENDING_HUMAN_REVIEW"
    assert len(q["items"]) >= 6
    for it in q["items"]:
        for field in ("claim", "source", "engineering_interpretation",
                      "design_implication"):
            assert it[field], f"item {it['item_id']} missing {field}"
        assert it["reviewer_verdict"] is None  # never fabricated


def test_b11_ingest_valid_verdict_counts_only(tmp_path):
    queue_path = tmp_path / "q.json"
    results_path = tmp_path / "r.json"
    q = {"artifact": "HUMAN_SPOT_CHECK_QUEUE", "items": [
        {"item_id": "HSC-001", "claim": "c", "source": {},
         "engineering_interpretation": "i", "design_implication": "d"}]}
    queue_path.write_text(json.dumps(q))
    before = queue_path.read_bytes()
    out = hsc.ingest_verdicts(
        [{"item_id": "HSC-001", "reviewer_verdict": "HUMAN_DISPUTED",
          "reviewer_id": "reviewer-1", "reviewer_rationale": "does not "
          "follow"}],
        results_path=results_path, queue_path=queue_path)
    assert out["accepted"] == 1
    assert out["counts_only_aggregate"]["HUMAN_DISPUTED"] == 1
    assert out["queue_mutated"] is False
    assert queue_path.read_bytes() == before  # queue untouched
    # no score conversion in the results file: no score-like KEYS
    r = json.loads(results_path.read_text())

    def walk_keys(o):
        keys = []
        if isinstance(o, dict):
            for k, v in o.items():
                keys.append(k)
                keys += walk_keys(v)
        elif isinstance(o, list):
            for v in o:
                keys += walk_keys(v)
        return keys
    for k in walk_keys(r):
        assert not any(banned in k.lower() for banned in
                       ("score", "grade", "rating", "numeric", "points")), \
            f"score-like key '{k}' present in human review results"


def test_b11_ingest_rejects_bad_verdict_and_duplicates(tmp_path):
    queue_path = tmp_path / "q.json"
    results_path = tmp_path / "r.json"
    q = {"items": [{"item_id": "HSC-001"}, {"item_id": "HSC-002"}]}
    queue_path.write_text(json.dumps(q))
    out = hsc.ingest_verdicts(
        [{"item_id": "HSC-001", "reviewer_verdict": "HUMAN_GREAT"},
         {"item_id": "HSC-999", "reviewer_verdict": "HUMAN_CONFIRMED"},
         {"item_id": "HSC-002", "reviewer_verdict": "HUMAN_UNCERTAIN"}],
        results_path=results_path, queue_path=queue_path)
    assert out["accepted"] == 1
    assert len(out["rejected"]) == 2
    # duplicate now rejected
    out2 = hsc.ingest_verdicts(
        [{"item_id": "HSC-002", "reviewer_verdict": "HUMAN_CONFIRMED"}],
        results_path=results_path, queue_path=queue_path)
    assert out2["accepted"] == 0
    assert len(out2["rejected"]) == 1


def test_b11_protocol_exists_with_verdict_vocabulary():
    p = BASELINE_DIR / "HUMAN_SPOT_CHECK_PROTOCOL.md"
    assert p.exists()
    text = " ".join(p.read_text(encoding="utf-8").lower().split())
    for v in hsc.VERDICTS:
        assert v.lower() in text
    assert "never converted into an automated score" in text


# ===========================================================================
# B12 — failure taxonomy + final report
# ===========================================================================
def test_b12_exactly_five_categories():
    assert ft.FAILURE_CATEGORIES == (
        "GENERATION_FAILURE", "AUDIT_FAILURE", "BENCHMARK_FAILURE",
        "EVIDENCE_FAILURE", "ENGINEERING_REASONING_FAILURE")


def test_b12_register_entries_carry_evidence():
    reg = ft.build_failure_register()
    assert set(reg["category_counts"]) == set(ft.FAILURE_CATEGORIES)
    for e in reg["entries"]:
        assert e["category"] in ft.FAILURE_CATEGORIES
        assert e["evidence"], f"{e['id']} has no evidence pointer"
        assert e["owner"] in ("CODER1", "CODER2", "CODER1_TEST_SUITE",
                              "ENVIRONMENT")
        assert e["status"] in ("OPEN", "FIXED", "CLOSED")


def test_b12_evidence_failure_not_generation_failure():
    # the missing-credential blockage must be EVIDENCE_FAILURE — Coder 1
    # must not chase it as a generation bug
    reg = ft.build_failure_register()
    v1 = [e for e in reg["entries"] if e["id"] == "V1"]
    assert v1 and v1[0]["category"] == "EVIDENCE_FAILURE"
    assert "NOT a generation failure" in v1[0]["description"]


def test_b12_final_report_sections_present():
    report = json.loads(
        (BASELINE_DIR / "FINAL_AUDIT_REPORT.json").read_text())
    for key in ("frozen_baselines", "rejection_decomposition_b8",
                "blind_semantic_adjudication_b9", "unseen_problem_test_b10",
                "human_spot_check_b11", "failure_register_b12",
                "ceo_checklist_phase3", "bottom_line"):
        assert key in report, f"final report missing {key}"
    b7 = report["frozen_baselines"]["B7_INDEPENDENT_FREEZE"]
    assert b7["BASELINE_RELEASE_YIELD"] == {"released": 3, "total": 15}
    assert b7["integrity"] == "INTEGRITY_OK"


def test_b12_checklist_marks_pending_items_honestly():
    report = json.loads(
        (BASELINE_DIR / "FINAL_AUDIT_REPORT.json").read_text())
    cl = report["ceo_checklist_phase3"]
    assert cl["Human technical spot-check"].startswith("BUILT, PENDING")
    assert "PARTIAL" in cl["Genuine unseen-problem validation"]
    assert cl["Real-world validation"].startswith("NOT STARTED")
