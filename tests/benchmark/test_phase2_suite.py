"""tests/benchmark — Coder 2 Phase 2 (B1-B6) adversarial suite.

Every new semantic control must:
  * CATCH the defect class it exists to catch (adversarial mutations on
    artifact COPIES — Art. IX: never mutate production runs);
  * NOT fire on clean content (Art. V: no universal rejector);
  * keep the baseline immutable (B1), the thresholds hash-pinned (B6),
    and the blind content out of the repository (B2).
"""
import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.benchmark import baseline as bl  # noqa: E402
from discovery_fabric.benchmark import data_split as ds  # noqa: E402
from discovery_fabric.benchmark import reaudit as ra  # noqa: E402
from discovery_fabric.benchmark import semantic_causal as sc  # noqa: E402
from discovery_fabric.benchmark import semantic_genericness as sg  # noqa: E402
from discovery_fabric.benchmark import tri_measurement as tm  # noqa: E402

RUNS = REPO_ROOT / "artifacts/benchmark/generated/runs"

ACTIVE_SIGNATURE = [
    "implant telemetry node", "telemetry dropout at implant depth",
    "exposure-aware link-budget scheduler adapts transmit power to hold "
    "link margin",
    "adaptive-power telemetry firmware with antenna tuning network",
    "reliable data link at maximum implant depth within SAR limits",
]
PASSIVE_SIGNATURE = [
    "CSF shunt system", "postural overdrainage causes intracranial "
    "hypotension",
    "serial siphon-limiting segments raise hydrodynamic resistance only "
    "under gravitational head",
    "multi-stage gravity-compensating catheter segment",
    "upright drainage stays within the physiologic band",
]


# ---------------------------------------------------------------------------
# Minimal synthetic engineering specifications (B3 attack surface)
# ---------------------------------------------------------------------------
def _eq_chain(eq_id, name, source_text, condition, verdict, reason,
              model_str, fm_ids=None, vf_ids=None):
    fm_ids = fm_ids or []
    vf_ids = vf_ids or []
    nodes = [
        {"node_id": f"{eq_id}-00", "node_type": "CLAIM",
         "content": f"{name} governs the behavior of this invention's "
                    f"primary output within its stated applicability",
         "parent_ids": [],
         "provenance": {"refs": {"equation_id": eq_id, "verdict": verdict}}},
        {"node_id": f"{eq_id}-01", "node_type": "ENGINEERING_PRINCIPLE",
         "content": f"{name} (standard engineering relation)",
         "parent_ids": [f"{eq_id}-00"], "provenance": {"refs": {}}},
        {"node_id": f"{eq_id}-02", "node_type": "EQUATION_MODEL",
         "content": model_str, "parent_ids": [f"{eq_id}-01"],
         "provenance": {"refs": {
             "equation_id": eq_id, "verdict": verdict,
             "applicability_reason": reason}}},
        {"node_id": f"{eq_id}-03", "node_type": "INPUT",
         "content": "all input variables UNKNOWN (no sourced value)",
         "epistemic_class": "UNKNOWN",
         "parent_ids": [f"{eq_id}-02"], "provenance": {"refs": {}}},
        {"node_id": f"{eq_id}-04", "node_type": "ASSUMPTION",
         "content": "model assumptions checked; none violated",
         "parent_ids": [f"{eq_id}-03"], "provenance": {"refs": {}}},
        {"node_id": f"{eq_id}-05", "node_type": "OUTPUT",
         "content": "no computed value exists (no sourced inputs)",
         "epistemic_class": "UNKNOWN",
         "parent_ids": [f"{eq_id}-04"], "provenance": {"refs": {}}},
        {"node_id": f"{eq_id}-06", "node_type": "FAILURE_MODE",
         "content": f"failure modes linked: {fm_ids}",
         "parent_ids": [f"{eq_id}-05"],
         "provenance": {"refs": {"failure_mode_ids": fm_ids}}},
        {"node_id": f"{eq_id}-07", "node_type": "VERIFICATION",
         "content": f"verifications: {vf_ids}",
         "parent_ids": [f"{eq_id}-06"],
         "provenance": {"refs": {"verification_ids": vf_ids}}},
    ]
    return {"chain_id": f"RC-{eq_id}", "subject": f"equation:{eq_id}",
            "nodes": nodes}


def _eng_spec(chains, equations, failure_rows, vf_rows,
              design_inputs=None):
    return {
        "design_inputs": design_inputs or [],
        "design_outputs": [],
        "failure_analysis": failure_rows,
        "verification_matrix": vf_rows,
        "engineering_core": {"governing_model": {"equations": equations}},
        "engineering_reasoning_chains": {"chains": chains},
        "kill_condition": {"falsification_test": ""},
        "_epistemic_summary": {"UNKNOWN_fields": []},
    }


FLUIDICS_EQUATION = {
    "equation_id": "FLU-001", "name": "Hagen-Poiseuille",
    "source": {"text": "Hagen-Poiseuille relation"},
    "applicability": {"condition": "laminar, newtonian, steady flow"},
}
RF_EQUATION = {
    "equation_id": "RF-001", "name": "Friis link budget",
    "source": {"text": "Friis transmission equation"},
    "applicability": {"condition": "far field, line of sight"},
}
OBSTRUCTION_FM = {
    "graph_id": "FM-001", "failure_mode": "OBSTRUCTION",
    "physical_mechanism": "deposits narrow the lumen and progressively "
                          "obstruct drainage flow",
    "content_class": "PHYSICAL_MECHANISM", "verification": "VF-001",
}
FLOW_VF = {
    "id": "VF-001", "method": "flow-rate and time-to-occlusion bench loop",
    "requirement": "flow-rate and time-to-occlusion bench loop",
}
BER_VF = {
    "id": "VF-002", "method": "bit-error-rate vs distance/depth curve",
    "requirement": "bit-error-rate vs distance/depth curve",
}
FRACTURE_FM = {
    "graph_id": "FM-002", "failure_mode": "FRACTURE",
    "physical_mechanism": "cyclic micromotion initiates a fatigue crack "
                          "that propagates through the anchor",
    "content_class": "PHYSICAL_MECHANISM", "verification": "VF-002",
}


def _clean_fluidics_spec():
    chain = _eq_chain(
        "FLU-001", "Hagen-Poiseuille", "Hagen-Poiseuille relation",
        "laminar, newtonian, steady flow", "APPLICABLE",
        "invention mechanism engages the model variables: Q, dP",
        "Q = dP * pi * r^4 / (8 * mu * L)  [FLU-001]",
        fm_ids=["FM-001"], vf_ids=["VF-001"])
    return _eng_spec([chain], [FLUIDICS_EQUATION],
                     [OBSTRUCTION_FM], [FLOW_VF])


FLUIDICS_SIGNATURE = [
    "CSF shunt system", "proximal catheter obstruction by tissue ingrowth",
    "graded-porosity outlet diffuser spreads flow to reduce stagnant "
    "zones where tissue ingrowth starts",
    "porous polymeric diffuser sleeve over the distal outlet",
]


# ---------------------------------------------------------------------------
# B3 — semantic causal review: attacks must be caught
# ---------------------------------------------------------------------------
def test_b3_wrong_domain_equation_is_incorrect():
    """A governing relation from a foreign engineering family claimed for
    an invention it does not govern must be INCORRECT (release blocker)."""
    chain = _eq_chain(
        "RF-001", "Friis link budget", "Friis transmission equation",
        "far field, line of sight", "APPLICABLE",
        "invention mechanism engages the model variables: P_r, P_t",
        "P_r = P_t * G_t * G_r * (lambda / (4 * pi * d))^2  [RF-001]")
    spec = _eng_spec([chain], [RF_EQUATION], [OBSTRUCTION_FM], [FLOW_VF])
    audit = sc.audit_semantic_causality(spec, None, FLUIDICS_SIGNATURE)
    assert audit["incorrect_critical_count"] >= 1
    reasons = [l["reason"] for ic in
               audit["incorrect_critical_chains"] for l in
               ic["incorrect_links"]]
    assert "DOMAIN_FAMILY_MISMATCH" in reasons
    assert audit["release_blocker"] is True


def test_b3_control_contradiction_in_chain_node():
    """A chain node asserting passive operation for an ACTIVE-control
    invention is INCORRECT (the canonical defect class)."""
    spec = _clean_fluidics_spec()
    active_sig = list(ACTIVE_SIGNATURE)  # active rf invention...
    # ...whose chain claims a passive architecture
    spec["engineering_reasoning_chains"]["chains"][0]["nodes"][2][
        "content"] += (" — no closed-loop control is proposed: the "
                       "invention operates passively open-loop")
    audit = sc.audit_semantic_causality(spec, None, active_sig)
    node_findings = [nf for ic in audit["incorrect_critical_chains"]
                     for nf in ic.get("node_findings", [])]
    assert any(nf["reason"] == "CONTROL_ARCHITECTURE_CONTRADICTION"
               for nf in node_findings)
    assert audit["release_blocker"] is True


def test_b3_fabricated_output_with_unknown_inputs():
    spec = _clean_fluidics_spec()
    chain = spec["engineering_reasoning_chains"]["chains"][0]
    out = next(n for n in chain["nodes"] if n["node_type"] == "OUTPUT")
    out["content"] = "computed drainage improvement factor 3.2x"
    out["epistemic_class"] = "COMPUTED"
    audit = sc.audit_semantic_causality(spec, None, FLUIDICS_SIGNATURE)
    reasons = [l["reason"] for ic in audit["incorrect_critical_chains"]
               for l in ic["incorrect_links"]]
    assert "OUTPUT_WITHOUT_INPUTS" in reasons


def test_b3_applicable_despite_assumption_violation():
    """A laminar-flow equation judged APPLICABLE for a turbulent invention
    is INCORRECT — the applicability judgment is re-verified, not
    trusted (Art. III)."""
    chain = _eq_chain(
        "FLU-001", "Hagen-Poiseuille", "Hagen-Poiseuille relation",
        "laminar, newtonian, steady flow", "APPLICABLE",
        "invention mechanism engages the model variables: Q, dP",
        "Q = dP * pi * r^4 / (8 * mu * L)  [FLU-001]")
    spec = _eng_spec([chain], [FLUIDICS_EQUATION], [OBSTRUCTION_FM],
                     [FLOW_VF])
    turbulent_sig = list(FLUIDICS_SIGNATURE) + [
        "flow through the outlet is turbulent at physiologic flow rates"]
    audit = sc.audit_semantic_causality(spec, None, turbulent_sig)
    reasons = [l["reason"] for ic in audit["incorrect_critical_chains"]
               for l in ic["incorrect_links"]]
    assert "APPLICABLE_DESPITE_ASSUMPTION_VIOLATION" in reasons


def test_b3_rejected_for_assumption_violation_is_correct():
    """The same conflict with verdict REJECTED must be CORRECT (the
    engine's judgment matches the physics)."""
    chain = _eq_chain(
        "FLU-001", "Hagen-Poiseuille", "Hagen-Poiseuille relation",
        "laminar, newtonian, steady flow", "REJECTED",
        "invention mechanism engages the model variables: Q, dP",
        "Q = dP * pi * r^4 / (8 * mu * L)  [FLU-001]")
    spec = _eng_spec([chain], [], [OBSTRUCTION_FM], [FLOW_VF])
    # rejected equations live in rejected_equations (real schema)
    spec["engineering_core"]["governing_model"]["rejected_equations"] = [
        FLUIDICS_EQUATION]
    turbulent_sig = list(FLUIDICS_SIGNATURE) + [
        "flow through the outlet is turbulent at physiologic flow rates"]
    audit = sc.audit_semantic_causality(spec, None, turbulent_sig)
    reasons = [l["reason"] for ic in audit["incorrect_critical_chains"]
               for l in ic["incorrect_links"]]
    assert "APPLICABLE_DESPITE_ASSUMPTION_VIOLATION" not in reasons
    assert "REJECTED_FOR_ASSUMPTION_VIOLATION" in str(
        audit["chains"][0]["link_verdicts"])


def test_b3_verification_measuring_wrong_quantity():
    """A fatigue failure verified by a bit-error-rate curve cannot detect
    the failure — INCORRECT."""
    chain = _eq_chain(
        "FLU-001", "Hagen-Poiseuille", "Hagen-Poiseuille relation",
        "laminar, newtonian, steady flow", "APPLICABLE",
        "invention mechanism engages the model variables: Q, dP",
        "Q = dP * pi * r^4 / (8 * mu * L)  [FLU-001]",
        fm_ids=["FM-002"], vf_ids=["VF-002"])
    spec = _eng_spec([chain], [FLUIDICS_EQUATION], [FRACTURE_FM], [BER_VF])
    audit = sc.audit_semantic_causality(spec, None, FLUIDICS_SIGNATURE)
    reasons = [l["reason"] for ic in audit["incorrect_critical_chains"]
               for l in ic["incorrect_links"]]
    assert "VERIFICATION_WRONG_QUANTITY" in reasons


def test_b3_clean_chain_passes_no_false_incorrect():
    """Positive control (Art. V): a well-formed, family-consistent chain
    with matching verification produces NO INCORRECT verdict."""
    spec = _clean_fluidics_spec()
    audit = sc.audit_semantic_causality(spec, None, FLUIDICS_SIGNATURE)
    assert audit["chain_verdict_counts"]["INCORRECT"] == 0
    assert audit["verdict"] == "PASS"
    assert audit["release_blocker"] is False


def test_b3_fm_discipline_adjacent_is_questionable_not_incorrect():
    """A fluidics invention carrying a MECHANICAL failure mode is an
    adjacent-discipline question (QUESTIONABLE), not a falsehood —
    implantable catheters legitimately fail mechanically."""
    fm_chain = {
        "chain_id": "RC-FM002", "subject": "failure_mode:FM-002",
        "nodes": [
            {"node_id": "RC-FM002-00", "node_type": "CLAIM",
             "content": "Failure mode 'catheter anchor fatigue fracture' "
                        "is a candidate failure of this invention's design",
             "parent_ids": [],
             "provenance": {"refs": {"failure_mode_id": "FM-002"}}},
            {"node_id": "RC-FM002-01", "node_type": "ENGINEERING_PRINCIPLE",
             "content": "cyclic micromotion initiates a fatigue crack that "
                        "propagates through the anchor under bending stress",
             "parent_ids": ["RC-FM002-00"],
             "provenance": {"refs": {}}},
            {"node_id": "RC-FM002-02", "node_type": "EQUATION_MODEL",
             "content": "no quantitative model linked (NOT_ESTABLISHED)",
             "parent_ids": ["RC-FM002-01"],
             "provenance": {"refs": {"equation_id": None}}},
            {"node_id": "RC-FM002-07", "node_type": "VERIFICATION",
             "content": "verifications: VF-002",
             "parent_ids": ["RC-FM002-01"],
             "provenance": {"refs": {"verification_ids": ["VF-002"]}}},
        ],
    }
    spec = _eng_spec([fm_chain], [FLUIDICS_EQUATION],
                     [FRACTURE_FM],
                     [{"id": "VF-002",
                       "method": "cyclic bend-to-failure rig; cycles vs "
                                 "straight control"}])
    audit = sc.audit_semantic_causality(spec, None, FLUIDICS_SIGNATURE)
    incorrect = [l["reason"] for ic in
                 audit["incorrect_critical_chains"]
                 for l in ic["incorrect_links"]]
    assert incorrect == []
    # the adjacent-discipline link is recorded as QUESTIONABLE
    assert any(l["reason"] == "FM_DISCIPLINE_ADJACENT"
               for c in audit["chains"] for l in c["link_verdicts"])


def test_b3_equation_informing_unrelated_fm_is_incorrect():
    """A governing fluidics model claimed to INFORM a fatigue failure is
    causally unrelated — INCORRECT (positive detection of the
    FM_CAUSALLY_UNRELATED_TO_MODEL class)."""
    chain = _eq_chain(
        "FLU-001", "Hagen-Poiseuille", "Hagen-Poiseuille relation",
        "laminar, newtonian, steady flow", "APPLICABLE",
        "invention mechanism engages the model variables: Q, dP",
        "Q = dP * pi * r^4 / (8 * mu * L)  [FLU-001]",
        fm_ids=["FM-002"], vf_ids=["VF-002"])
    spec = _eng_spec([chain], [FLUIDICS_EQUATION], [FRACTURE_FM], [{
        "id": "VF-002", "method": "cyclic bend-to-failure rig"}])
    audit = sc.audit_semantic_causality(spec, None, FLUIDICS_SIGNATURE)
    reasons = [l["reason"] for ic in audit["incorrect_critical_chains"]
               for l in ic["incorrect_links"]]
    assert "FM_CAUSALLY_UNRELATED_TO_MODEL" in reasons


# ---------------------------------------------------------------------------
# B4 — semantic genericness: attacks must be caught
# ---------------------------------------------------------------------------
def _pkg(pid, signature, sentences):
    """run_dir-less package record: build a temp dir with an eng spec
    carrying the given sentences in design_outputs descriptions."""
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix=f"sg_{pid}_"))
    spec = {"design_outputs": [{"description": s} for s in sentences],
            "design_inputs": [], "failure_analysis": [],
            "verification_matrix": [], "engineering_core": {},
            "engineering_reasoning_chains": {"chains": []}}
    (tmp / "ENGINEERING_SPECIFICATION.json").write_text(
        json.dumps(spec), encoding="utf-8")
    return {"run_dir": str(tmp), "package_dir": None, "package_id": pid,
            "input_signature": signature}


PASSIVE_SENTENCE = ("No closed-loop control is proposed: the invention "
                    "operates passively/open-loop as specified; this record "
                    "exists so the omission is explicit and auditable")
CSF_SENTENCE = ("CSF shunt systems for hydrocephalus management: current "
                "alternative standard fixed-pressure or programmable CSF "
                "shunt valves mechanism difference")


def test_b4_canonical_passive_openloop_defect_caught():
    """THE CEO-cited case: passive/open-loop boilerplate shipped into an
    ACTIVE-control invention's dossier."""
    pkgs = [
        _pkg("ACTIVE_PKG", ACTIVE_SIGNATURE, [PASSIVE_SENTENCE]),
        _pkg("PASSIVE_PKG", PASSIVE_SIGNATURE, [PASSIVE_SENTENCE]),
    ]
    audit = sg.audit_semantic_genericness(pkgs)
    mismatches = audit["semantic_mismatches"]
    assert any(m["package_id"] == "ACTIVE_PKG" and
               m["classification"] == "CONTROL_ARCHITECTURE_MISMATCH"
               for m in mismatches)
    # the passive package carries the SAME sentence with no contradiction
    assert not any(m["package_id"] == "PASSIVE_PKG" for m in mismatches)
    assert audit["verdict"] == "FAIL"


def test_b4_domain_mismatch_boilerplate_caught():
    """CSF-shunt boilerplate in a non-CSF package is a domain mismatch;
    the same sentence in a CSF-shunt package is not."""
    energy_signature = [
        "implantable sensor", "primary cell exhausts before device end of "
        "life", "piezoelectric stack harvests arterial pulsation energy "
        "through a compliant coupling",
        "pulsation-coupled piezoelectric energy harvester",
    ]
    csf_signature = FLUIDICS_SIGNATURE
    pkgs = [
        _pkg("ENERGY_PKG", energy_signature, [CSF_SENTENCE]),
        _pkg("CSF_PKG", csf_signature, [CSF_SENTENCE]),
    ]
    audit = sg.audit_semantic_genericness(pkgs)
    mismatches = audit["semantic_mismatches"]
    assert any(m["package_id"] == "ENERGY_PKG" and
               m["classification"] == "DOMAIN_MISMATCH"
               for m in mismatches)
    assert not any(m["package_id"] == "CSF_PKG" for m in mismatches)


def test_b4_mechanism_negation_caught():
    """"No energy harvesting is proposed" in an energy-harvesting
    dossier is a mechanism mismatch."""
    energy_signature = [
        "implantable sensor", "piezoelectric stack harvests arterial "
        "pulsation energy through a compliant coupling",
        "net positive energy balance at physiologic pulse pressure",
    ]
    negation = "no energy harvesting is proposed for this revision of " \
               "the design"
    pkgs = [
        _pkg("E1", energy_signature, [negation]),
        _pkg("E2", PASSIVE_SIGNATURE, [negation]),
    ]
    audit = sg.audit_semantic_genericness(pkgs)
    assert any(m["package_id"] == "E1" and
               m["classification"] == "MECHANISM_MISMATCH"
               for m in audit["semantic_mismatches"])


def test_b4_no_false_positive_on_test_control_group():
    """'vs straight control' in a falsification test must NOT trigger the
    mechanism-negation detector (control-group vocabulary). Signature is
    the committed BENCH_10 input (strain-relief bellows)."""
    signature = [
        "CSF shunt system", "neck movement fatigues the catheter until it "
        "cracks",
        "strain-relief bellows redistribute bending strain away from the "
        "fixation point",
        "cyclic bend-to-failure rig; cycles vs straight control",
    ]
    sentence = ("no closed-loop control is proposed for this passive "
                "mechanical element")
    pkgs = [_pkg("P1", signature, [sentence]),
            _pkg("P2", PASSIVE_SIGNATURE, [sentence])]
    audit = sg.audit_semantic_genericness(pkgs)
    assert audit["semantic_mismatch_count"] == 0


def test_b4_true_boilerplate_is_load_not_mismatch():
    """Recurring-but-true sentences are genericness LOAD, never semantic
    mismatches (Art. V: no universal rejector)."""
    true_sentence = ("all validation remains NOT_PERFORMED until physical "
                     "observation exists per the reality boundary")
    pkgs = [_pkg("A", FLUIDICS_SIGNATURE, [true_sentence]),
            _pkg("B", ACTIVE_SIGNATURE, [true_sentence])]
    audit = sg.audit_semantic_genericness(pkgs)
    assert audit["semantic_mismatch_count"] == 0
    assert audit["recurring_template_sentences"]["count"] >= 1


def test_b4_operating_mode_mismatch():
    signature = [
        "implantable sensor", "thermoelectric gradient across the implant "
        "capsule trickle-charges the reservoir",
        "continuous sensing without sleep windows",
    ]
    sentence = ("the device sleeps between measurements to conserve the "
                "energy budget and runs intermittent operation only")
    pkgs = [_pkg("S1", signature, [sentence]),
            _pkg("S2", PASSIVE_SIGNATURE, [sentence])]
    audit = sg.audit_semantic_genericness(pkgs)
    assert any(m["package_id"] == "S1" and
               m["classification"] == "OPERATING_MODE_MISMATCH"
               for m in audit["semantic_mismatches"])


# ---------------------------------------------------------------------------
# B1 — baseline immutability
# ---------------------------------------------------------------------------
def test_b1_baseline_freeze_once_and_mutation_detected(tmp_path):
    measurement = {
        "measured_at": "2026-08-28T00:00:00Z", "engine_head": "test",
        "threshold_integrity": {"depth_contract_sha256": "x"},
        "baseline_summary": {"CURRENT_BASELINE": "3/15 RELEASED"},
        "seven_deficiencies": {"RELEASE_YIELD": {"summary": "3/15"}},
        "tri_measurement": {},
    }
    path = tmp_path / "CURRENT_BASELINE.json"
    first = bl.freeze_baseline(measurement, path)
    assert first["action"] == "FROZEN"
    # second freeze REFUSES (immutable)
    second = bl.freeze_baseline(measurement, path)
    assert second["action"] == "REFUSED"
    # integrity OK on the untouched file
    assert bl.verify_baseline(path)["verdict"] == "INTEGRITY_OK"
    # mutation is detected
    data = json.loads(path.read_text(encoding="utf-8"))
    data["baseline_summary"]["CURRENT_BASELINE"] = "15/15 RELEASED"
    path.write_text(json.dumps(data), encoding="utf-8")
    verdict = bl.verify_baseline(path)
    assert verdict["verdict"] == "BASELINE_MUTATED"
    with pytest.raises(RuntimeError):
        bl.load_baseline(path)


def test_b1_committed_baseline_is_intact():
    path = REPO_ROOT / "artifacts/benchmark/baseline/CURRENT_BASELINE.json"
    if not path.exists():
        pytest.skip("baseline not frozen yet")
    verdict = bl.verify_baseline(path)
    assert verdict["verdict"] == "INTEGRITY_OK"
    summary = verdict["baseline_summary"]["CURRENT_BASELINE"]
    assert "3/15 RELEASED" in summary and "12/15 QUALITY_REJECTED" in summary


# ---------------------------------------------------------------------------
# B6 — threshold drift detection
# ---------------------------------------------------------------------------
def test_b6_threshold_drift_detected(tmp_path):
    recorded = {
        "depth_contract_sha256": bl.sha256_file(
            REPO_ROOT / "artifacts/benchmark/ENGINEERING_DEPTH_CONTRACT.json"),
        "dossier_profile_sha256": bl.sha256_file(
            REPO_ROOT / "artifacts/benchmark/BENCHMARK_DOSSIER_PROFILE.json"),
    }
    ok = ra.verify_threshold_integrity(recorded)
    assert ok["verdict"] == "OK"
    drifted = dict(recorded, depth_contract_sha256="0" * 64)
    alarm = ra.verify_threshold_integrity(drifted)
    assert alarm["verdict"] == "THRESHOLD_DRIFT"
    assert "depth_contract_sha256" in alarm["drifted"]


def test_b6_reaudit_blocks_comparison_on_drift(tmp_path):
    """A drifted threshold must block the before/after comparison."""
    measurement = {"seven_deficiencies": {k: {"summary": k}
                                          for k in ra.DEFICIENCY_KEYS}}
    result = ra.run_reaudit(
        measurement, baseline_path=tmp_path / "missing.json")
    assert result["comparison_allowed"] is False
    assert result["baseline"]["integrity"]["verdict"] == "MISSING"


def test_b6_reaudit_before_after_table_on_frozen_baseline():
    baseline = REPO_ROOT / "artifacts/benchmark/baseline/CURRENT_BASELINE.json"
    if not baseline.exists():
        pytest.skip("baseline not frozen yet")
    baseline_data = bl.load_baseline(baseline)
    result = ra.run_reaudit(baseline_data)  # after == before (same state)
    assert result["comparison_allowed"] is True
    rows = {r["deficiency"]: r for r in result["table"]}
    assert set(rows) == set(ra.DEFICIENCY_KEYS)
    for key, row in rows.items():
        assert row["before"] is not None and row["after"] is not None


# ---------------------------------------------------------------------------
# B2 — blind holdout disclosure discipline
# ---------------------------------------------------------------------------
def test_b2_split_manifest_covers_all_15_exactly_once():
    manifest = ds.build_split_manifest()
    dev = manifest["development_set"]["bench_ids"]
    hold = manifest["holdout_set"]["bench_ids"]
    assert len(dev) == 8 and len(hold) == 7
    assert set(dev) | set(hold) == {f"BENCH_{i:02d}" for i in range(1, 16)}
    assert not set(dev) & set(hold)


@pytest.mark.skipif(not (ds.BLIND_SET_PATH.exists() or
                         ds.BLIND_CUSTODY_PATH.exists()),
                    reason="blind custody file not present in this sandbox")
def test_b2_blind_set_verified_and_distinct():
    specs = ds.load_blind_set()
    ver = ds.verify_blind_inputs(specs)
    assert ver["verdict"] == "PASS", ver["problems"]
    assert ver["distinct_from_committed"] is True


@pytest.mark.skipif(not (ds.BLIND_SET_PATH.exists() or
                         ds.BLIND_CUSTODY_PATH.exists()),
                    reason="blind custody file not present in this sandbox")
def test_b2_blind_content_absent_from_tracked_repo():
    """No blind mechanism 3-gram may appear in ANY git-tracked file."""
    specs = ds.load_blind_set()
    tracked = subprocess.run(
        ["git", "ls-files"], cwd=REPO_ROOT, capture_output=True,
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
    import re as _re
    for s in specs:
        words = [w for w in _re.findall(r"[a-z]+",
                                        s["mechanism"].lower())
                 if len(w) > 3]
        for i in range(len(words) - 2):
            gram = " ".join(words[i:i + 3])
            assert gram not in blob, (
                f"BLIND CONTENT LEAK: '{gram}' is tracked in the repo")


def test_b2_blind_runs_are_gitignored():
    gi = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "artifacts/benchmark/blind/" in gi


# ---------------------------------------------------------------------------
# B5 — attribution + separation
# ---------------------------------------------------------------------------
def _rejected_run(tmp_path, killed, quality_rejected, eng_counts):
    rd = tmp_path / f"run_{len(list(tmp_path.iterdir()))}"
    rd.mkdir()
    (rd / "DISCOVERY_RELEASE.json").write_text(json.dumps({
        "status": "PIPELINE_FAILED",
        "failure_reason": "E15-H selection: no viable survivor (all "
                          "candidates killed or quality-rejected; "
                          "ranked=1)"}), encoding="utf-8")
    (rd / "SURVIVOR_SELECTION.json").write_text(json.dumps({
        "ranked": [{"candidate_id": "c1"}],
        "killed": killed, "quality_rejected": quality_rejected,
    }), encoding="utf-8")
    if eng_counts is not None:
        spec = _clean_fluidics_spec()
        spec["design_inputs"] = [{"value": "x"}] * eng_counts.get(
            "design_inputs", 9)
        spec["failure_analysis"] = [OBSTRUCTION_FM] * eng_counts.get(
            "failure_modes", 3)
        spec["verification_matrix"] = [FLOW_VF] * eng_counts.get(
            "verifications", 3)
        n_eq = eng_counts.get("equations", 1)
        gm = spec["engineering_core"]["governing_model"]
        gm["equations"] = [dict(FLUIDICS_EQUATION,
                                equation_id=f"FLU-00{i}")
                           for i in range(1, n_eq + 1)]
        spec["_epistemic_summary"]["UNKNOWN_fields"] = [
            f"unknown #{i}" for i in
            range(eng_counts.get("remaining_unknowns", 0))]
        (rd / "ENGINEERING_SPECIFICATION.json").write_text(
            json.dumps(spec), encoding="utf-8")
    return rd


def test_b5_attribution_attack_kill(tmp_path):
    rd = _rejected_run(tmp_path, killed=["c1"], quality_rejected=[],
                       eng_counts=None)
    attribution = tm.classify_non_release(rd)
    assert attribution["cause"] == "ALL_CANDIDATES_KILLED_BY_ATTACK"


def test_b5_attribution_shallow_output(tmp_path):
    contract = json.loads(
        (REPO_ROOT / "artifacts/benchmark/ENGINEERING_DEPTH_CONTRACT.json")
        .read_text(encoding="utf-8"))
    rd = _rejected_run(tmp_path, killed=[], quality_rejected=["c1"],
                       eng_counts={"design_inputs": 2})  # below floor 9
    attribution = tm.classify_non_release(rd, contract)
    assert attribution["cause"] == "QUALITY_REJECTED_SHALLOW_OUTPUT"


def test_b5_attribution_over_strict_gate(tmp_path):
    """A quality-rejected run whose would-be dossier MEETS every
    measurable floor is flagged as an over-strict gate candidate."""
    contract = json.loads(
        (REPO_ROOT / "artifacts/benchmark/ENGINEERING_DEPTH_CONTRACT.json")
        .read_text(encoding="utf-8"))
    rd = _rejected_run(tmp_path, killed=[], quality_rejected=["c1"],
                       eng_counts={"design_inputs": 12,
                                   "failure_modes": 5,
                                   "verifications": 4,
                                   "equations": 3,
                                   "remaining_unknowns": 7})
    attribution = tm.classify_non_release(rd, contract)
    assert attribution["cause"] == "QUALITY_REJECTED_DESPITE_ADEQUATE_DEPTH"


def test_b5_attribution_no_candidates(tmp_path):
    rd = _rejected_run(tmp_path, killed=[], quality_rejected=[],
                       eng_counts=None)
    (rd / "SURVIVOR_SELECTION.json").write_text(json.dumps(
        {"ranked": [], "killed": [], "quality_rejected": []}),
        encoding="utf-8")
    attribution = tm.classify_non_release(rd)
    assert attribution["cause"] == "NO_VIABLE_CANDIDATE_SYNTHESIS"


@pytest.mark.skipif(not (RUNS / "BENCH_01").exists(),
                    reason="benchmark runs not generated in this sandbox")
def test_b5_tri_measurement_separates_axes():
    contract = json.loads(
        (REPO_ROOT / "artifacts/benchmark/ENGINEERING_DEPTH_CONTRACT.json")
        .read_text(encoding="utf-8"))
    run_dirs = [RUNS / f"BENCH_{i:02d}" for i in range(1, 16)]
    batch = json.loads(
        (REPO_ROOT / "artifacts/benchmark/generated/"
                     "AUTOMATED_DOSSIER_BENCHMARK.json")
        .read_text(encoding="utf-8"))
    tri = tm.measure_yield_depth_correctness(
        run_dirs, contract=contract, batch_audit=batch,
        split_manifest=ds.build_split_manifest())
    y = tri["engine_release_yield"]
    assert y["released"] == 3 and y["engine_rejected"] == 12
    assert y["per_split"]["development_set"]["released"] == 2
    assert y["per_split"]["holdout_set"]["released"] == 1
    assert tri["dossier_depth"]["released_packages"] == 3
    assert tri["dossier_correctness"]["correctness_fail_count"] == 3
    # attribution must be complete for all 12 rejections
    assert sum(y["attribution_counts"].values()) == 12
    assert y["attribution_counts"].get(
        "QUALITY_REJECTED_SHALLOW_OUTPUT") == 12


@pytest.mark.skipif(not (RUNS / "BENCH_04").exists(),
                    reason="benchmark runs not generated in this sandbox")
def test_b3_b4_fired_on_real_released_runs():
    """Regression: the canonical defects ARE present in the current
    released set and are caught (release blocker semantics)."""
    eng = json.loads((RUNS / "BENCH_04" / "ENGINEERING_SPECIFICATION.json")
                     .read_text(encoding="utf-8"))
    from discovery_fabric.benchmark.audit_runner import _input_signature
    audit = sc.audit_semantic_causality(
        eng, None, _input_signature(RUNS / "BENCH_04"))
    assert audit["release_blocker"] is True
    assert audit["invention_control_architecture"] == "ACTIVE"


def test_b5_probe_floors_parsed_from_contract():
    """The depth probe must read the corpus contract's minimum_depth
    (regression: earlier revision read a wrong key and everything was
    NOT_MEASURABLE)."""
    contract = json.loads(
        (REPO_ROOT / "artifacts/benchmark/ENGINEERING_DEPTH_CONTRACT.json")
        .read_text(encoding="utf-8"))
    probe = tm.eng_spec_depth_probe(_clean_fluidics_spec(), contract)
    assert probe["floors_measurable"] is True
    floors = {c["metric"]: c["floor"] for c in probe["checks"]}
    assert floors.get("design_inputs") == 9
    assert floors.get("equations") == 3
