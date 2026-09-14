"""tests/test_e16_series.py — CEO E16 directives (A through J).

E16-A  benchmark split: TRAINING_REFERENCE / DEVELOPMENT_HOLDOUT /
       BLIND_HOLDOUT; floors derive from TRAINING only; blind vectors
       sealed (tamper-evident); NO engine module reads the seal except
       the evaluation-time gate/evaluator
E16-B  blind protocol: anonymized subjects, origin-blind measurement,
       reveal-and-score
E16-C  substantive content instruments (densities/ratios, NOT counts)
       with the verdict policy fixed before use
E16-D  semantic causal correctness: CORRECT/QUESTIONABLE/INCORRECT per
       critical chain; one INCORRECT blocks release
E16-E  candidate diversity: 10-candidate grid via recorded exploration
       angles; rewrite detection
E16-G  N-ary ensemble comparison with 3-model support
E16-H  holdout release gate: six gates; CONDITIONAL = human review
       required, never an automatic PASS
E16-I  terminology: LIVE_AUTONOMOUS_SOFTWARE_CAPSTONE (no "REAL"
       inflation)
E16-F/J are proven in the live run + E16_ACCEPTANCE.json (a test suite
cannot fabricate a live run; the offline tests prove the machinery).
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from test_a_series_integration import (  # noqa: E402
    _a9_survivor, _drive, ensure_registry)

from archive.r455_retired.discovery_fabric.engine import blind_protocol as bp  # noqa: E402
from discovery_fabric.engine import causal_correctness as cc  # noqa: E402
from discovery_fabric.engine import ensemble as ens  # noqa: E402
from archive.r455_retired.discovery_fabric.engine.benchmark_dossiers import (  # noqa: E402
    load_contract, measure_generated_vector)
from archive.r455_retired.discovery_fabric.engine.benchmark_split import (  # noqa: E402
    SEALED_VECTORS, assign_strata, load_split, open_sealed_blind_vectors,
    stratum_of)
from discovery_fabric.engine.candidate_diversity import (  # noqa: E402
    EXPLORATION_ANGLES, evaluate_diversity, measure_diversity)
from discovery_fabric.engine.release_gate import (  # noqa: E402
    evaluate_release_gate)

# ---------------------------------------------------------------- E16-A
def test_e16a_split_is_deterministic_and_sealed():
    strata = assign_strata()
    assert len(strata["TRAINING_REFERENCE"]) == 10
    assert len(strata["DEVELOPMENT_HOLDOUT"]) == 3
    assert len(strata["BLIND_HOLDOUT"]) == 2
    # deterministic: a second assignment is identical
    assert assign_strata() == strata
    # the committed split artifact matches the rule
    split = load_split()
    assert split["strata"] == strata
    assert "i % 8 == 0" in split["split_rule"]
    # every package's provenance is recorded
    assert all(p["provenance_sha256"] for p in
               split["per_package"].values())


def test_e16a_blind_vectors_sealed_and_tamper_evident():
    sealed = open_sealed_blind_vectors()
    assert len(sealed["vectors"]) == 2
    for name, v in sealed["vectors"].items():
        assert stratum_of(name) == "BLIND_HOLDOUT"
        assert "content" in v and "structural" in v
    # tamper evidence: a modified seal refuses to open
    original = SEALED_VECTORS.read_bytes()
    try:
        SEALED_VECTORS.write_text(
            original.decode() + "tampered")
        with pytest.raises(RuntimeError, match="seal hash mismatch"):
            open_sealed_blind_vectors()
    finally:
        SEALED_VECTORS.write_bytes(original)
    open_sealed_blind_vectors()  # restores cleanly


def test_e16a_floors_derive_from_training_only():
    contract = load_contract()
    assert contract["floors_derived_from"].startswith(
        "TRAINING_REFERENCE")
    training = [p for p in contract["per_package"]
                if p["_stratum"] == "TRAINING_REFERENCE"]
    for dim in contract["dimensions"]:
        assert contract["floors"][dim] == min(p[dim] for p in training)


def test_e16a_no_generator_module_reads_the_seal():
    """Static guard: no module under discovery_fabric/engine may open the
    sealed blind vectors except the release gate and this benchmark
    module (evaluation-time only)."""
    engine_dir = Path(__file__).resolve().parents[1] / \
        "discovery_fabric" / "engine"
    allowed = {"release_gate.py", "benchmark_split.py"}
    offenders = []
    for f in engine_dir.glob("*.py"):
        if f.name in allowed:
            continue
        if "open_sealed_blind_vectors" in f.read_text() or \
                "SEALED_VECTORS" in f.read_text():
            offenders.append(f.name)
    assert not offenders, offenders


# ---------------------------------------------------------------- E16-C
def test_e16c_policy_fixed_before_use():
    """The verdict policy thresholds are recorded constants, fixed before
    any generated package was measured against them (Art. XXVII)."""
    from discovery_fabric.engine.substance_metrics import (
        FLOOR_GUARD, SUBSTANCE_CONDITIONAL_DIMS, SUBSTANCE_PASS_DIMS)
    assert SUBSTANCE_PASS_DIMS == 8
    assert SUBSTANCE_CONDITIONAL_DIMS == 6
    assert FLOOR_GUARD == 0.5


def test_e16c_instruments_are_densities_not_counts():
    from archive.r455_retired.discovery_fabric.engine.benchmark_split import (
        list_frozen_packages, load_split)
    from discovery_fabric.engine.substance_metrics import (
        CONTENT_DIMENSIONS, content_vector)
    strata = load_split()["strata"]
    train = [d for d in list_frozen_packages()
             if d.name in strata["TRAINING_REFERENCE"]]
    v = content_vector(train[0])
    for dim in CONTENT_DIMENSIONS:
        val = v[dim]
        assert isinstance(val, (int, float)) and 0.0 <= val, dim
    # the content basis records the measured sentence/row denominators
    assert v["_content_basis"]["sentences"] > 0


# ---------------------------------------------------------------- E16-B
def test_e16b_blind_protocol_hides_origin_and_scores_blind():
    with tempfile.TemporaryDirectory() as td:
        reg = str(Path(td) / "reg.json")
        ensure_registry(reg)
        run = _drive(_a9_survivor(0), Path(td) / "run01", "t:e16b",
                     registry_path=reg)
        from archive.r455_retired.discovery_fabric.engine.benchmark_split import (
            list_frozen_packages, load_split)
        strata = load_split()["strata"]
        # reference subjects come from the DEVELOPMENT_HOLDOUT stratum
        # (the training corpus stays the scoring distribution; the blind
        # holdout is never touched in development tests)
        refs = [d for d in list_frozen_packages()
                if d.name in strata["DEVELOPMENT_HOLDOUT"]][:2]
        protocol = bp.prepare_blind_set(
            [Path(run.package_report["folder"])], refs, Path(td) / "blind")
        # the subjects directory contains NO origin information
        subjects_manifest = json.loads(
            (Path(protocol["work_root"]) / "subjects" / "SUBJECTS.json")
            .read_text())
        assert len(subjects_manifest["subjects"]) == 3
        measurements = bp.measure_subjects(
            Path(protocol["work_root"]) / "subjects")
        assert len(measurements) == 3
        # measurement objects carry no origin field
        for m in measurements.values():
            assert "origin" not in json.dumps(m).lower()
        scored = bp.reveal_and_score(
            measurements, Path(protocol["key_path"]), refs)
        assert scored["n_generated"] == 1 and scored["n_reference"] == 2
        gen = [r for r in scored["results"] if r["origin"] == "GENERATED"]
        assert gen[0]["substance"]["verdict"] in (
            "PASS", "CONDITIONAL", "FAIL")


# ---------------------------------------------------------------- E16-D
def test_e16d_semantic_correctness_on_healthy_artifact():
    from test_f_series_integration import _survivor_env
    from discovery_fabric.engine.engineering_spec import (
        build_engineering_spec)
    from discovery_fabric.engine.invention_spec import build_invention_spec
    env = _survivor_env("fluidics_hydraulic")
    spec = build_invention_spec(env, {"run_id": "t:e16d"})
    eng = build_engineering_spec(spec, env, {"run_id": "t:e16d"})
    result = cc.evaluate_causal_correctness(eng)
    assert result["counts"]["INCORRECT"] == 0
    assert result["verdict"] in ("PASS", "CONDITIONAL")


def test_e16d_incorrect_chain_detected_and_blocks():
    from test_f_series_integration import _survivor_env
    from discovery_fabric.engine.engineering_spec import (
        build_engineering_spec)
    from discovery_fabric.engine.invention_spec import build_invention_spec
    env = _survivor_env("fluidics_hydraulic")
    spec = build_invention_spec(env, {"run_id": "t:e16d2"})
    eng = build_engineering_spec(spec, env, {"run_id": "t:e16d2"})
    # fabricate an unsupported measured value on a sourced parameter:
    # R6 must mark the chain INCORRECT
    params = eng["engineering_core"]["critical_parameters"]
    for p in params:
        p["value_status"] = "COMPUTED"
        p["value"] = 3.14
        p["source"] = None
    result = cc.evaluate_causal_correctness(eng)
    assert result["counts"]["INCORRECT"] >= 1
    assert result["verdict"] == "FAIL"
    # and the release gate FAILs with it
    gate = evaluate_release_gate(spec, eng, {"folder": str(
        Path(__file__).resolve().parents[1])})
    assert gate["verdicts"]["CAUSAL_CORRECTNESS"] == "FAIL"


def test_e16d_rejected_equation_chain_is_incorrect():
    from test_f_series_integration import _survivor_env
    from discovery_fabric.engine.engineering_spec import (
        build_engineering_spec)
    from discovery_fabric.engine.invention_spec import build_invention_spec
    env = _survivor_env("fluidics_hydraulic")
    spec = build_invention_spec(env, {"run_id": "t:e16d3"})
    eng = build_engineering_spec(spec, env, {"run_id": "t:e16d3"})
    # move an equation to rejected but keep its chain: the chain now
    # claims what the artifact rejects (R3)
    gm = eng["engineering_core"]["governing_model"]
    eq = gm["equations"][0]
    eq_id = eq["equation_id"]
    gm["rejected_equations"].append({
        "equation_id": eq_id, "name": eq["name"],
        "rejection_reason": "test"})
    gm["equations"] = gm["equations"][1:]
    # the whole chain population is evaluated (critical_only=False): a
    # chain whose subject left the critical set must still be audited
    result = cc.evaluate_causal_correctness(eng, critical_only=False)
    bad = [r for r in result["results"] if r["verdict"] == "INCORRECT"]
    assert any(r["subject"] == f"equation:{eq_id}" for r in bad)


# ---------------------------------------------------------------- E16-E
def test_e16e_diversity_metrics_detect_rewrites():
    usable = [
        {"candidate_id": f"c{i}", "fields": {
            "mechanism": "porous titanium microstructure resists tissue "
                         "ingrowth through smooth pore walls",
            "intervention": "porous titanium catheter tip in the shunt "
                            "lumen drains fluid"}}
        for i in range(6)]
    m = measure_diversity(usable)
    # six lexical rewrites of one concept -> 1 cluster, tiny distance
    assert m["distinct_mechanism_clusters"] == 1
    verdict = evaluate_diversity(m, min_candidates=10)
    assert verdict["verdict"] in ("FAIL", "CONDITIONAL")
    assert any("clusters" in f or "distance" in f or "candidate" in f
               for f in verdict["failed_checks"])


def test_e16e_diversity_metrics_reward_genuine_spread():
    usable = [
        {"candidate_id": "c0", "fields": {
            "mechanism": "piezoelectric transducer converts tissue "
                         "compression into electrical charge for the "
                         "battery",
            "intervention": "piezoelectric fiber layer on the lead "
                            "surface harvests motion energy"}},
        {"candidate_id": "c1", "fields": {
            "mechanism": "thermoelectric generator converts body heat "
                         "difference across a semiconductor junction "
                         "into power",
            "intervention": "thermoelectric pile bonded to the titanium "
                            "housing exterior harvests thermal gradient"}},
        {"candidate_id": "c2", "fields": {
            "mechanism": "inductive coupling transfers power across the "
                         "skin through a resonant magnetic field pair",
            "intervention": "external coil drives an implanted receiver "
                            "coil through the tissue"}},
        {"candidate_id": "c3", "fields": {
            "mechanism": "glucose fuel cell oxidizes the analyte to "
                         "generate current at the electrode catalyst",
            "intervention": "implantable biofuel cell membrane stack in "
                            "the interstitial fluid"}},
        {"candidate_id": "c4", "fields": {
            "mechanism": "optical fiber delivers near-infrared light to "
                         "a photovoltaic cell that converts it to "
                         "charge",
            "intervention": "subcutaneous photovoltaic receiver behind "
                            "the optical window"}},
        {"candidate_id": "c5", "fields": {
            "mechanism": "kinetic energy harvester converts cardiac "
                         "motion into stored charge through an "
                         "inertial mass",
            "intervention": "seismic mass cantilever inside the pulse "
                            "generator shell"}},
        {"candidate_id": "c6", "fields": {
            "mechanism": "acoustic transducer focuses ultrasound energy "
                         "onto a receiver diaphragm to recharge the "
                         "cell",
            "intervention": "external ultrasound array beams power to "
                            "the implanted receiver"}},
        {"candidate_id": "c7", "fields": {
            "mechanism": "magnetic gear transmits rotational energy "
                         "through tissue from an external driving "
                         "magnet to an internal generator",
            "intervention": "implanted magnetic rotor pairs with the "
                            "external rotating magnet"}},
        {"candidate_id": "c8", "fields": {
            "mechanism": "reverse electrowetting converts mechanical "
                         "droplet motion into electrical energy on "
                         "patterned electrodes",
            "intervention": "electrowetting channel array embedded in "
                            "the lead tip"}},
        {"candidate_id": "c9", "fields": {
            "mechanism": "betavoltaic cell converts isotope decay "
                         "electrons into steady current in the "
                         "semiconductor junction",
            "intervention": "encapsulated tritium betavoltaic stack in "
                            "the generator can"}},
    ]
    m = measure_diversity(usable)
    assert m["distinct_mechanism_clusters"] >= 5
    assert m["mean_pairwise_token_distance"] >= 0.6
    verdict = evaluate_diversity(m, min_candidates=10)
    assert verdict["verdict"] in ("PASS", "CONDITIONAL")


def test_e16e_exploration_angles_are_recorded_policy():
    names = [a[0] for a in EXPLORATION_ANGLES]
    assert len(names) == 5
    assert all(a[1] for a in EXPLORATION_ANGLES)


# ---------------------------------------------------------------- E16-G
def test_e16g_nary_comparison_three_models(monkeypatch):
    class FakeRes:
        def __init__(self, content, provider):
            self.status = "OK"
            self.content = content
            self.provider_id = provider
            self.model = f"fake-{provider}"
            self.prompt_hash = "0" * 16
            self.output_hash = "2" * 16
            self.latency_ms = 1
            self.error = None

        @property
        def ok(self):
            return self.status == "OK"

    responses = {
        "modelA": ("MECHANISM: porous titanium resists tissue ingrowth\n"
                   "INTERVENTION: porous titanium shunt tip drains "
                   "cerebrospinal fluid\nEXPECTED_EFFECT: stable flow\n"
                   "FALSIFICATION_TEST: bench flow loop 30 days\n"
                   "MECHANISM_SOURCE_SPAN: porous structure"),
        "modelB": ("MECHANISM: hydrogel coating repels cell adhesion\n"
                   "INTERVENTION: hydrogel valve coating prevents "
                   "protein fouling\nEXPECTED_EFFECT: stable pressure\n"
                   "FALSIFICATION_TEST: monthly pressure drift\n"
                   "MECHANISM_SOURCE_SPAN: hydration layer"),
        "modelC": ("MECHANISM: magnetic rotor clears obstruction\n"
                   "INTERVENTION: rotating magnetic microimpeller in "
                   "the valve chamber\nEXPECTED_EFFECT: active flow\n"
                   "FALSIFICATION_TEST: flow rate under load\n"
                   "MECHANISM_SOURCE_SPAN: magnetic actuation"),
    }

    def fake_generate(prompt, system="", schema=None, evidence=None,
                      policy=None, timeout=240, max_retries=2,
                      max_tokens=512):
        pid = policy.preferred_providers[0]
        return FakeRes(responses[pid], pid)

    monkeypatch.setattr(ens, "generate", fake_generate)
    monkeypatch.setattr(ens, "availability_matrix", lambda: [
        {"provider_id": p, "available": True}
        for p in ("modelA", "modelB", "modelC")])
    out = ens.ensemble_synthesize(
        {"problem_id": "p", "device": "d", "failure": "f",
         "constraint": "c"},
        [{"id": "e1", "title": "t", "abstract": "a", "content_hash": "h"}])
    assert len(out["members"]) == 3
    assert out["comparison"]["pairs_compared"] == 3
    assert out["adjudication"]["consensus_forced"] is False
    # with three divergent mechanisms, disagreements exist and stay
    # unresolved
    assert out["disagreements"]
    assert all(d["status"].startswith("UNRESOLVED")
               for d in out["disagreements"])


# ---------------------------------------------------------------- E16-H
def test_e16h_gate_holds_conditional_and_blocks_failure():
    from test_f_series_integration import _survivor_env
    from discovery_fabric.engine.engineering_spec import (
        build_engineering_spec)
    from discovery_fabric.engine.invention_spec import build_invention_spec
    env = _survivor_env("fluidics_hydraulic")
    spec = build_invention_spec(env, {"run_id": "t:e16h"})
    eng = build_engineering_spec(spec, env, {"run_id": "t:e16h"})
    # a healthy fixture artifact with a full package report is needed for
    # TRACEABILITY/PROVENANCE; run the pipeline once
    with tempfile.TemporaryDirectory() as td:
        reg = str(Path(td) / "reg.json")
        ensure_registry(reg)
        run = _drive(_a9_survivor(0), Path(td) / "run01", "t:e16h-full",
                     registry_path=reg)
        gate = evaluate_release_gate(run._spec, run._eng,
                                     run.package_report)
        assert set(gate["verdicts"]) == {
            "SUBSTANTIVE_DEPTH", "CAUSAL_CORRECTNESS", "TRACEABILITY",
            "PROVENANCE", "DOMAIN_REASONING", "HOLDOUT_TEST"}
        # the fixture's causal chains carry QUESTIONABLE verdicts (open
        # questions bound to the decisive experiment) -> the gate must
        # HOLD the package for human review, never auto-PASS it
        assert gate["decision"] in ("CONDITIONAL", "FAIL")
        assert gate["policy_detail"]["HELD_FOR_HUMAN_REVIEW"]
