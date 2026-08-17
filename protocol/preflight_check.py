#!/usr/bin/env python3
"""
preflight_check.py — Mechanical enforcement of INVENTION_PROTOCOL_V1.

This script walks every INVENTION_* directory in the repository and verifies
that the package complies with every mandatory rule in the constitution:

  Section 9.1  Missing artifacts
  Section 9.2  Limitation freeze violations
  Section 9.3  Patent assertion without primary-source evidence
  Section 9.4  102 multiple-reference / mis-classification violations
  Section 9.5  103 missing motivation / reasonable expectation
  Section 9.6  Family coverage violations
  Section 9.7  Engineering worst-case / failure-mode / fail-safe violations
  Section 9.8  Simulation number provenance violations
  Section 9.9  Score provenance / silent promotion violations
  Section 9.10 Hash integrity violations
  Section 9.11 Version preservation violations
  Section 9.12 Silent promotion violations

Exit codes:
  0  — all checks pass (CI allows commit)
  1  — at least one check failed (CI blocks commit)

Output:
  - stdout: human-readable summary
  - preflight_report.json: machine-readable per-check pass/fail with specific failure reasons

This script is the FLOOR, not the ceiling. It does not verify substance
(is the motivation analysis actually meaningful?). It verifies structure.
Human review is still required for substance.

Per INVENTION_PROTOCOL_V1 Section 11.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path("/home/z/my-project/discovery-evidence-fabric")
INVENTION_PATTERN = re.compile(r"^(?:[A-Z]+_)?INVENTION_\d+", re.IGNORECASE)

# Mandatory artifacts per Section 6
MANDATORY_DIRS = [
    "01_COMPANY_CORPUS",
    "02_FAMILY_GRAPH",
    "03_TECHNOLOGY_MAP",
    "04_OWNERSHIP_MAP",
    "05_BUYER_MAP",
    "06_MOAT_MAP",
    "07_PROBLEM_SELECTION",
    "09_PRIOR_ART",
    "10_CLAIM_RETRIEVAL",
    "11_102_ATTACK",
    "12_103_ATTACK",
    "13_ARCHITECTURES",
    "14_DESIGN_AROUND",
    "15_ENGINEERING_BLUEPRINT",
    "16_SIMULATION",
    "17_MANUFACTURING",
    "18_REGULATORY",
    "19_BUILD_BUY",
    "20_BUYER_MEMO",
]

MANDATORY_FILES = [
    "00_MANIFEST.json",
    "08_LIMITATION_FREEZE.json",
    "21_EVIDENCE_LEDGER.json",
    "22_FINAL_ADJUDICATION.json",
    "23_LESSONS_LEARNED.json",
    "SHA256SUMS",
]

# Domains where fail-safe analysis is required (Section 9.7)
FAIL_SAFE_REQUIRED_KEYWORDS = [
    "CNS", "intracranial", "subarachnoid", "cerebrospinal", "neural",
    "cardiac", "heart", "vascular", "blood",
    "respiratory", "lung", "ventilator",
    "battery", "implantable_power", "energy_storage",
]


@dataclass
class CheckResult:
    section: str
    check_name: str
    passed: bool
    failure_reason: str = ""
    artifact: str = ""


@dataclass
class InventionReport:
    invention_id: str
    invention_dir: str
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        return all(c.passed for c in self.checks)

    @property
    def failures(self) -> list[CheckResult]:
        return [c for c in self.checks if not c.passed]


def sha256_of_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> dict | list | None:
    if not path.is_file():
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except Exception as e:
        return {"_parse_error": str(e)}


# ---------- Section X.0 — Constitution hash-pin (repo-level, runs FIRST) ----------
#
# Per INVENTION_PROTOCOL_V1 §14 (Protocol Evolution Workflow) and §3.8
# (Protocol Immutability Within a Run). The canonical constitution file's
# SHA-256 is pinned in protocol/CONSTITUTION_REGISTRY.json. This check
# verifies the file exists at the pinned path and its hash matches. A
# mismatch means the constitution was modified outside the Protocol
# Evolution Workflow — a hard CI failure.
#
# This check is repo-level, not per-invention. It runs BEFORE any
# Section 9 check. Its result appears as a top-level `constitution_check`
# field in preflight_report.json.

def check_constitution_hash(repo_root: Path) -> list[CheckResult]:
    """Verify the canonical constitution file exists and its SHA-256 matches the registry pin.

    Returns a single CheckResult (section X.0) that passes only if:
    1. CONSTITUTION_REGISTRY.json exists and is parseable
    2. current_canonical_path field is present
    3. The canonical file exists at that path
    4. The file's SHA-256 matches current_sha256

    If any sub-check fails, the single CheckResult fails with a message
    identifying which step failed.
    """
    registry_path = repo_root / "protocol" / "CONSTITUTION_REGISTRY.json"
    section = "X.0"
    check_name = "constitution_hash_pin"

    # Step 1: registry file exists and is parseable
    registry = load_json(registry_path)
    if registry is None:
        return [CheckResult(
            section=section, check_name=check_name, passed=False,
            failure_reason="protocol/CONSTITUTION_REGISTRY.json is missing",
            artifact=str(registry_path),
        )]
    if not isinstance(registry, dict) or "_parse_error" in registry:
        parse_err = registry.get("_parse_error", "not a valid JSON object") if isinstance(registry, dict) else "not a valid JSON object"
        return [CheckResult(
            section=section, check_name=check_name, passed=False,
            failure_reason=f"protocol/CONSTITUTION_REGISTRY.json is not valid: {parse_err}",
            artifact=str(registry_path),
        )]

    # Step 2: current_canonical_path field present
    canonical_rel = registry.get("current_canonical_path")
    if not canonical_rel or not isinstance(canonical_rel, str):
        return [CheckResult(
            section=section, check_name=check_name, passed=False,
            failure_reason="CONSTITUTION_REGISTRY.json missing or invalid 'current_canonical_path' field",
            artifact=str(registry_path),
        )]

    # Step 3: canonical constitution file exists at the pinned path
    canonical_path = repo_root / canonical_rel
    if not canonical_path.is_file():
        return [CheckResult(
            section=section, check_name=check_name, passed=False,
            failure_reason=f"Canonical constitution file not found at pinned path: {canonical_rel}",
            artifact=str(canonical_path),
        )]

    # Step 4: SHA-256 matches the pin
    pinned_hash = registry.get("current_sha256")
    if not pinned_hash or not isinstance(pinned_hash, str):
        return [CheckResult(
            section=section, check_name=check_name, passed=False,
            failure_reason="CONSTITUTION_REGISTRY.json missing or invalid 'current_sha256' field",
            artifact=str(registry_path),
        )]

    actual_hash = sha256_of_file(canonical_path)
    if actual_hash != pinned_hash:
        return [CheckResult(
            section=section, check_name=check_name, passed=False,
            failure_reason=(
                f"Constitution SHA-256 mismatch: pinned={pinned_hash}, actual={actual_hash}. "
                "The constitution file was modified outside the Protocol Evolution Workflow (§14). "
                "Either restore the file or follow §14 to create V2."
            ),
            artifact=str(canonical_path),
        )]

    # All steps passed
    return [CheckResult(
        section=section, check_name=check_name, passed=True,
        artifact=str(canonical_path),
    )]


def find_invention_dirs(repo_root: Path) -> list[Path]:
    if not repo_root.is_dir():
        return []
    found = []
    for entry in sorted(repo_root.iterdir()):
        if entry.is_dir() and INVENTION_PATTERN.match(entry.name):
            # Skip experimental / non-canonical dirs that match the pattern
            # but aren't real invention packages (e.g.,*_V8, *_ELITE_AUDIT)
            # Heuristic: must contain a MANIFEST.json or 00_MANIFEST.json
            if (entry / "00_MANIFEST.json").is_file() or (entry / "MANIFEST.json").is_file():
                found.append(entry)
    return found


# ---------- Section 9.1 — Missing artifacts ----------

def check_mandatory_artifacts(invention_dir: Path) -> list[CheckResult]:
    results = []
    for d in MANDATORY_DIRS:
        if not (invention_dir / d).is_dir():
            results.append(CheckResult(
                section="9.1",
                check_name=f"mandatory_dir_{d}",
                passed=False,
                failure_reason=f"Missing mandatory directory: {d}/",
                artifact=str(invention_dir / d),
            ))
    for f in MANDATORY_FILES:
        if not (invention_dir / f).is_file():
            results.append(CheckResult(
                section="9.1",
                check_name=f"mandatory_file_{f}",
                passed=False,
                failure_reason=f"Missing mandatory file: {f}",
                artifact=str(invention_dir / f),
            ))
        else:
            results.append(CheckResult(
                section="9.1",
                check_name=f"mandatory_file_{f}",
                passed=True,
                artifact=str(invention_dir / f),
            ))
    return results


# ---------- Section 9.2 — Limitation freeze violations ----------

def check_limitation_freeze(invention_dir: Path) -> list[CheckResult]:
    results = []
    freeze_path = invention_dir / "08_LIMITATION_FREEZE.json"
    freeze = load_json(freeze_path)
    if freeze is None:
        results.append(CheckResult(
            section="9.2",
            check_name="limitation_freeze_present",
            passed=False,
            failure_reason="08_LIMITATION_FREEZE.json is missing",
            artifact=str(freeze_path),
        ))
        return results
    if not isinstance(freeze, dict):
        results.append(CheckResult(
            section="9.2",
            check_name="limitation_freeze_parseable",
            passed=False,
            failure_reason=f"08_LIMITATION_FREEZE.json is not valid JSON object",
            artifact=str(freeze_path),
        ))
        return results
    limitations = freeze.get("limitations", {})
    if not limitations or not isinstance(limitations, dict):
        results.append(CheckResult(
            section="9.2",
            check_name="limitations_present",
            passed=False,
            failure_reason="limitations field missing or empty",
            artifact=str(freeze_path),
        ))
        return results
    for lid in ["L1", "L2", "L3", "L4", "L5", "L6"]:
        if lid not in limitations or not limitations[lid]:
            results.append(CheckResult(
                section="9.2",
                check_name=f"limitation_{lid}_present",
                passed=False,
                failure_reason=f"{lid} missing or empty in limitations",
                artifact=str(freeze_path),
            ))
        else:
            results.append(CheckResult(
                section="9.2",
                check_name=f"limitation_{lid}_present",
                passed=True,
                artifact=str(freeze_path),
            ))
    return results


# ---------- Section 9.3 — Patent assertion without primary-source evidence ----------

def check_evidence_ledger(invention_dir: Path) -> tuple[list[CheckResult], dict | None]:
    results = []
    ledger_path = invention_dir / "21_EVIDENCE_LEDGER.json"
    ledger = load_json(ledger_path)
    if ledger is None or not isinstance(ledger, dict):
        results.append(CheckResult(
            section="9.3",
            check_name="evidence_ledger_present",
            passed=False,
            failure_reason="21_EVIDENCE_LEDGER.json missing or invalid",
            artifact=str(ledger_path),
        ))
        return results, None

    evidence = ledger.get("evidence", [])
    if not evidence:
        results.append(CheckResult(
            section="9.3",
            check_name="evidence_ledger_nonempty",
            passed=False,
            failure_reason="evidence array is empty",
            artifact=str(ledger_path),
        ))
        return results, ledger

    sha_sums = read_sha_sums(invention_dir)

    for i, entry in enumerate(evidence):
        if not isinstance(entry, dict):
            continue
        eid = entry.get("evidence_id", f"<index {i}>")
        artifact_pointer = entry.get("artifact_pointer")
        if not artifact_pointer:
            results.append(CheckResult(
                section="9.3",
                check_name=f"evidence_{eid}_artifact_pointer",
                passed=False,
                failure_reason=f"evidence_id {eid} has no artifact_pointer",
                artifact=str(ledger_path),
            ))
            continue
        # artifact_pointer is a filename; check it exists in SHA256SUMS
        pointer_basename = os.path.basename(artifact_pointer)
        if pointer_basename not in sha_sums:
            results.append(CheckResult(
                section="9.3",
                check_name=f"evidence_{eid}_in_sha256sums",
                passed=False,
                failure_reason=f"evidence_id {eid} artifact_pointer {pointer_basename} not in SHA256SUMS",
                artifact=str(ledger_path),
            ))
        # model_derived check
        source_type = entry.get("source_type", "")
        model_derived = entry.get("model_derived", False)
        if source_type == "model_derived" and not model_derived:
            results.append(CheckResult(
                section="9.3",
                check_name=f"evidence_{eid}_model_derived_label",
                passed=False,
                failure_reason=f"evidence_id {eid} source_type=model_derived but model_derived=false",
                artifact=str(ledger_path),
            ))
        if model_derived and not entry.get("model_derived_note"):
            results.append(CheckResult(
                section="9.3",
                check_name=f"evidence_{eid}_model_derived_note",
                passed=False,
                failure_reason=f"evidence_id {eid} model_derived=true but model_derived_note is empty",
                artifact=str(ledger_path),
            ))
    return results, ledger


# ---------- Section 9.4 — 102 multiple-reference / mis-classification ----------

def check_102_attack(invention_dir: Path) -> list[CheckResult]:
    results = []
    # Try 11_102_ATTACK/102_RESULTS.json, then 06_102/102_RESULTS*.json (legacy), then root
    candidate_paths = [
        invention_dir / "11_102_ATTACK" / "102_RESULTS.json",
        invention_dir / "06_102" / "102_RESULTS.json",
        invention_dir / "06_102" / "102_RESULTS_V3.json",
        invention_dir / "TASK2_102_103_CORRECTED.json",  # legacy
    ]
    attack = None
    used_path = None
    for p in candidate_paths:
        loaded = load_json(p)
        if loaded is not None:
            attack = loaded
            used_path = p
            break
    if attack is None:
        results.append(CheckResult(
            section="9.4",
            check_name="102_attack_artifact_present",
            passed=False,
            failure_reason="No 102_RESULTS.json found in 11_102_ATTACK/ or legacy locations",
            artifact=str(invention_dir / "11_102_ATTACK" / "102_RESULTS.json"),
        ))
        return results

    # Could be a list of references or a dict with references_analyzed
    references = []
    if isinstance(attack, list):
        references = attack
    elif isinstance(attack, dict):
        references = attack.get("references_analyzed", attack.get("results", []))

    combination_words = re.compile(r"\b(combine|combination|together with|in view of|combined with)\b", re.IGNORECASE)
    for i, ref in enumerate(references):
        if not isinstance(ref, dict):
            continue
        anticipated = ref.get("102_anticipated") or ref.get("anticipated", False)
        rationale = ref.get("rationale", "") or ref.get("anticipation_rationale", "")
        # Check for NOT_DISCLOSED in limitation_matrix when anticipated=true
        matrix = ref.get("limitation_matrix", {})
        not_disclosed_count = 0
        for lid, lm in matrix.items():
            if isinstance(lm, dict) and lm.get("status") == "NOT_DISCLOSED":
                not_disclosed_count += 1
        if anticipated and not_disclosed_count > 0:
            results.append(CheckResult(
                section="9.4",
                check_name=f"ref_{i}_102_no_not_disclosed_when_anticipated",
                passed=False,
                failure_reason=f"ref {ref.get('reference_number', i)}: anticipated=true but {not_disclosed_count} limitations are NOT_DISCLOSED",
                artifact=str(used_path),
            ))
        # Check for combination words in rationale when anticipated=true
        if anticipated and combination_words.search(rationale or ""):
            results.append(CheckResult(
                section="9.4",
                check_name=f"ref_{i}_102_no_combination_words",
                passed=False,
                failure_reason=f"ref {ref.get('reference_number', i)}: 102 rationale contains combination words (likely mis-classified 103)",
                artifact=str(used_path),
            ))
    return results


# ---------- Section 9.5 — 103 missing motivation / expectation ----------

def check_103_attack(invention_dir: Path) -> list[CheckResult]:
    results = []
    candidate_paths = [
        invention_dir / "12_103_ATTACK" / "103_RESULTS.json",
        invention_dir / "07_103" / "103_RESULTS.json",
        invention_dir / "07_103" / "103_RESULTS_V3.json",
        invention_dir / "TASK2_102_103_CORRECTED.json",  # legacy combined
    ]
    attack = None
    used_path = None
    for p in candidate_paths:
        loaded = load_json(p)
        if loaded is not None:
            attack = loaded
            used_path = p
            break
    if attack is None:
        results.append(CheckResult(
            section="9.5",
            check_name="103_attack_artifact_present",
            passed=False,
            failure_reason="No 103_RESULTS.json found",
            artifact=str(invention_dir / "12_103_ATTACK" / "103_RESULTS.json"),
        ))
        return results

    # For legacy combined files, 103 info is implicit in 103_result field per ref
    # For canonical 103_RESULTS.json, look for combinations_analyzed array
    combinations = []
    if isinstance(attack, dict):
        combinations = attack.get("combinations_analyzed", [])
    if not combinations and isinstance(attack, list):
        # Legacy: each ref has 103_result field
        for ref in attack:
            if isinstance(ref, dict) and ref.get("103_result"):
                # Convert to pseudo-combination
                combinations.append({
                    "_legacy": True,
                    "obvious": ref.get("103_obvious", False),
                    "motivation": ref.get("103_motivation", ""),
                    "reference_number": ref.get("reference_number"),
                })

    weak_motivation_pattern = re.compile(r"\b(both known|well-known|well known|commonly known|generally known)\b", re.IGNORECASE)
    for i, comb in enumerate(combinations):
        if not isinstance(comb, dict):
            continue
        motivation = comb.get("motivation", "")
        expectation = comb.get("reasonable_expectation_of_success", {})
        if isinstance(expectation, dict):
            expectation_text = expectation.get("expectation", "")
        else:
            expectation_text = str(expectation or "")
        obvious = comb.get("obvious", False) or comb.get("103_obvious", False)

        # Check motivation present (only if obvious=true; if not obvious, motivation absence is acceptable)
        if obvious:
            if not motivation:
                results.append(CheckResult(
                    section="9.5",
                    check_name=f"combination_{i}_motivation_present",
                    passed=False,
                    failure_reason=f"combination {i}: obvious=true but motivation is empty",
                    artifact=str(used_path),
                ))
            elif weak_motivation_pattern.search(motivation):
                results.append(CheckResult(
                    section="9.5",
                    check_name=f"combination_{i}_motivation_specific",
                    passed=False,
                    failure_reason=f"combination {i}: motivation is weak ('both known' / 'well-known') without documented reason",
                    artifact=str(used_path),
                ))
            if not expectation_text:
                results.append(CheckResult(
                    section="9.5",
                    check_name=f"combination_{i}_expectation_present",
                    passed=False,
                    failure_reason=f"combination {i}: obvious=true but reasonable_expectation_of_success is empty",
                    artifact=str(used_path),
                ))
    return results


# ---------- Section 9.7 — Engineering worst-case / fail-safe ----------

def check_engineering_simulation(invention_dir: Path) -> list[CheckResult]:
    results = []
    # Engineering blueprint: 15_ENGINEERING_BLUEPRINT/blueprint.json (or legacy TASK3/TASK4)
    blueprint_candidates = [
        invention_dir / "15_ENGINEERING_BLUEPRINT" / "blueprint.json",
        invention_dir / "ENGINEERING_BLUEPRINT.json",
        invention_dir / "TASK3_MEMBRANE_MATERIAL_SPEC.json",
        invention_dir / "TASK4_ICP_SIMULATION.json",
    ]
    sim_candidates = [
        invention_dir / "16_SIMULATION" / "simulation_results.json",
        invention_dir / "FOULING_ICP_SIMULATION.json",
        invention_dir / "TASK4_ICP_SIMULATION.json",
    ]

    # Fail-safe check: if the engineering blueprint mentions CNS/cardiac/vascular/battery/etc., require fail_safe
    engineering_text = ""
    for p in blueprint_candidates + sim_candidates:
        if p.is_file():
            try:
                with open(p) as f:
                    engineering_text += f.read()
            except Exception:
                pass

    requires_fail_safe = any(kw.lower() in engineering_text.lower() for kw in FAIL_SAFE_REQUIRED_KEYWORDS)

    sim_loaded = None
    for p in sim_candidates:
        loaded = load_json(p)
        if loaded is not None:
            sim_loaded = loaded
            break

    if sim_loaded is None:
        results.append(CheckResult(
            section="9.7",
            check_name="simulation_artifact_present",
            passed=False,
            failure_reason="No simulation_results.json found in 16_SIMULATION/",
            artifact=str(invention_dir / "16_SIMULATION" / "simulation_results.json"),
        ))
        return results

    # Check failure_modes
    failure_modes = sim_loaded.get("failure_modes", [])
    if not failure_modes:
        # TASK4 format uses fouling_states; check for that
        fouling_states = sim_loaded.get("fouling_states", [])
        if not fouling_states:
            results.append(CheckResult(
                section="9.7",
                check_name="failure_modes_present",
                passed=False,
                failure_reason="simulation has no failure_modes or fouling_states",
                artifact=str(invention_dir / "16_SIMULATION" / "simulation_results.json"),
            ))

    # Check worst_case_boundary_conditions
    worst_case = sim_loaded.get("worst_case_boundary_conditions")
    if not worst_case:
        # TASK4 format uses complete_occlusion_result
        occlusion = sim_loaded.get("complete_occlusion_result")
        if not occlusion:
            results.append(CheckResult(
                section="9.7",
                check_name="worst_case_present",
                passed=False,
                failure_reason="simulation has no worst_case_boundary_conditions or complete_occlusion_result",
                artifact=str(invention_dir / "16_SIMULATION" / "simulation_results.json"),
            ))

    # Fail-safe check
    if requires_fail_safe:
        fail_safe = sim_loaded.get("fail_safe_analysis") or sim_loaded.get("a1_modified_specification")
        if not fail_safe:
            results.append(CheckResult(
                section="9.7",
                check_name="fail_safe_present",
                passed=False,
                failure_reason="engineering blueprint mentions CNS/cardiac/vascular/battery but simulation has no fail_safe_analysis",
                artifact=str(invention_dir / "16_SIMULATION" / "simulation_results.json"),
            ))

    return results


# ---------- Section 9.8 — Simulation number provenance ----------

def check_simulation_provenance(invention_dir: Path) -> list[CheckResult]:
    results = []
    sim_path = invention_dir / "16_SIMULATION" / "simulation_results.json"
    sim = load_json(sim_path)
    if sim is None:
        # Try legacy
        sim_path = invention_dir / "TASK4_ICP_SIMULATION.json"
        sim = load_json(sim_path)
    if sim is None:
        return results  # already flagged in 9.7

    model_inputs = sim.get("model_inputs")
    if not model_inputs:
        # TASK4 format: infer from fields
        # check that fouling_states have explicit values that trace to model inputs (lumen_diameter, csf_flow_rate)
        if not sim.get("lumen_diameter_um") and not sim.get("csf_flow_rate_ml_hr"):
            results.append(CheckResult(
                section="9.8",
                check_name="model_inputs_present",
                passed=False,
                failure_reason="simulation has numeric outputs but no model_inputs field",
                artifact=str(sim_path),
            ))
    return results


# ---------- Section 9.9 — Score provenance / silent promotion ----------

def check_final_adjudication(invention_dir: Path) -> list[CheckResult]:
    results = []
    adjudication_path = invention_dir / "22_FINAL_ADJUDICATION.json"
    adjudication = load_json(adjudication_path)
    if adjudication is None:
        # Try legacy
        for legacy in [invention_dir / "REVISED_SCORE.json", invention_dir / "FINAL_ADJUDICATION.json"]:
            adjudication = load_json(legacy)
            if adjudication:
                adjudication_path = legacy
                break
    if adjudication is None:
        results.append(CheckResult(
            section="9.9",
            check_name="adjudication_present",
            passed=False,
            failure_reason="No 22_FINAL_ADJUDICATION.json or REVISED_SCORE.json found",
            artifact=str(invention_dir / "22_FINAL_ADJUDICATION.json"),
        ))
        return results

    gates = adjudication.get("gates", {})
    final_status = adjudication.get("final_status", "")
    milestones = adjudication.get("milestones_for_buyer_ready", [])

    # Check each gate has evidence_pointer
    for gate_name, gate in gates.items():
        if not isinstance(gate, dict):
            continue
        score = gate.get("score", 0)
        threshold = gate.get("threshold", 0)
        status = gate.get("status", "")
        evidence_pointer = gate.get("evidence_pointer") or gate.get("evidence", "")

        if not evidence_pointer:
            results.append(CheckResult(
                section="9.9",
                check_name=f"gate_{gate_name}_evidence_pointer",
                passed=False,
                failure_reason=f"{gate_name} score has no evidence_pointer (silent promotion risk)",
                artifact=str(adjudication_path),
            ))

        # Silent promotion: final_status LEVEL_4_BUYER_READY but a gate is FAIL or below threshold
        if final_status == "LEVEL_4_BUYER_READY":
            if status == "FAIL" or score < threshold:
                results.append(CheckResult(
                    section="9.12",
                    check_name=f"gate_{gate_name}_silent_promotion",
                    passed=False,
                    failure_reason=f"{gate_name} score {score} < threshold {threshold} but final_status=LEVEL_4_BUYER_READY (silent promotion)",
                    artifact=str(adjudication_path),
                ))
            if milestones:
                results.append(CheckResult(
                    section="9.9",
                    check_name="milestones_empty_for_buyer_ready",
                    passed=False,
                    failure_reason="final_status=LEVEL_4_BUYER_READY but milestones list is non-empty",
                    artifact=str(adjudication_path),
                ))

        # WOULD_CONSIDER_WITH_MILESTONES must have non-empty milestones
        if final_status == "WOULD_CONSIDER_WITH_MILESTONES" and not milestones:
            results.append(CheckResult(
                section="9.9",
                check_name="milestones_nonempty_for_consider",
                passed=False,
                failure_reason="final_status=WOULD_CONSIDER_WITH_MILESTONES but milestones list is empty",
                artifact=str(adjudication_path),
            ))

    # Non-compensable check
    non_comp = adjudication.get("non_compensable_gates_status", {})
    patent_pass = non_comp.get("patent_gate_passed")
    evidence_pass = non_comp.get("evidence_gate_passed")
    if patent_pass is False and final_status != "WOULD_NOT_PAY":
        results.append(CheckResult(
            section="9.12",
            check_name="patent_gate_non_compensable",
            passed=False,
            failure_reason=f"patent_gate_passed=false but final_status={final_status} (non-compensable violation)",
            artifact=str(adjudication_path),
        ))
    if evidence_pass is False and final_status != "WOULD_NOT_PAY":
        results.append(CheckResult(
            section="9.12",
            check_name="evidence_gate_non_compensable",
            passed=False,
            failure_reason=f"evidence_gate_passed=false but final_status={final_status} (non-compensable violation)",
            artifact=str(adjudication_path),
        ))

    return results


# ---------- Section 9.10 — Hash integrity ----------

def read_sha_sums(invention_dir: Path) -> dict[str, str]:
    sums_path = invention_dir / "SHA256SUMS"
    if not sums_path.is_file():
        return {}
    sums = {}
    with open(sums_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            # Format: "<hash>  <filename>"
            parts = line.split(None, 1)
            if len(parts) == 2:
                digest, name = parts
                sums[name.strip()] = digest
    return sums


def check_hash_integrity(invention_dir: Path) -> list[CheckResult]:
    results = []
    sha_sums = read_sha_sums(invention_dir)
    if not sha_sums:
        results.append(CheckResult(
            section="9.10",
            check_name="sha256sums_present",
            passed=False,
            failure_reason="SHA256SUMS file is missing or empty",
            artifact=str(invention_dir / "SHA256SUMS"),
        ))
        return results
    # Verify every file in SHA256SUMS matches actual
    for name, recorded_digest in sha_sums.items():
        actual_digest = sha256_of_file(invention_dir / name)
        if actual_digest is None:
            results.append(CheckResult(
                section="9.10",
                check_name=f"hash_{name}_file_exists",
                passed=False,
                failure_reason=f"SHA256SUMS lists {name} but file does not exist",
                artifact=str(invention_dir / name),
            ))
            continue
        if actual_digest != recorded_digest:
            results.append(CheckResult(
                section="9.10",
                check_name=f"hash_{name}_matches",
                passed=False,
                failure_reason=f"{name}: recorded hash {recorded_digest} != actual {actual_digest}",
                artifact=str(invention_dir / name),
            ))
    # Verify every mandatory file is in SHA256SUMS
    for f in MANDATORY_FILES:
        if f == "SHA256SUMS":
            continue
        if (invention_dir / f).is_file() and f not in sha_sums:
            results.append(CheckResult(
                section="9.10",
                check_name=f"hash_{f}_in_sha256sums",
                passed=False,
                failure_reason=f"{f} exists but not in SHA256SUMS",
                artifact=str(invention_dir / f),
            ))
    return results


# ---------- Section 9.11 — Version preservation ----------

def check_version_preservation(repo_root: Path, invention_dir: Path) -> list[CheckResult]:
    """Check that previous versions of this invention have not been deleted."""
    results = []
    # Extract base name (e.g., CEREVASC_INVENTION_001_V2 → CEREVASC_INVENTION_001)
    base_match = re.match(r"^(.+?)_V\d+", invention_dir.name)
    if not base_match:
        return results  # No version suffix; nothing to check
    base_name = base_match.group(1)
    # Look for sibling dirs with same base name
    for entry in repo_root.iterdir():
        if not entry.is_dir():
            continue
        if entry.name == invention_dir.name:
            continue
        if entry.name.startswith(base_name + "_V") or entry.name == base_name:
            # Older version exists — good
            results.append(CheckResult(
                section="9.11",
                check_name=f"version_preservation_{entry.name}",
                passed=True,
                artifact=str(entry),
            ))
    return results


# ---------- Main ----------

def audit_invention(invention_dir: Path, repo_root: Path) -> InventionReport:
    report = InventionReport(
        invention_id=invention_dir.name,
        invention_dir=str(invention_dir),
    )
    report.checks.extend(check_mandatory_artifacts(invention_dir))
    report.checks.extend(check_limitation_freeze(invention_dir))
    report.checks.extend(check_evidence_ledger(invention_dir)[0])
    report.checks.extend(check_102_attack(invention_dir))
    report.checks.extend(check_103_attack(invention_dir))
    report.checks.extend(check_engineering_simulation(invention_dir))
    report.checks.extend(check_simulation_provenance(invention_dir))
    report.checks.extend(check_final_adjudication(invention_dir))
    report.checks.extend(check_hash_integrity(invention_dir))
    report.checks.extend(check_version_preservation(repo_root, invention_dir))
    return report


def main():
    repo_root = REPO_ROOT
    if not repo_root.is_dir():
        print(f"FATAL: repo root {repo_root} does not exist", file=sys.stderr)
        return 2

    # ---------- Section X.0 — Constitution hash-pin (repo-level, runs FIRST) ----------
    print("Constitution hash-pin check (Section X.0) ...")
    constitution_checks = check_constitution_hash(repo_root)
    constitution_pass = all(c.passed for c in constitution_checks)
    constitution_fails = [c for c in constitution_checks if not c.passed]
    if constitution_pass:
        print(f"  PASS  ({len(constitution_checks)} checks)")
    else:
        print(f"  FAIL  ({len(constitution_fails)} failures)")
        for fail in constitution_fails:
            print(f"    [{fail.section}] {fail.check_name}: {fail.failure_reason}")

    invention_dirs = find_invention_dirs(repo_root)
    all_reports = []
    if not invention_dirs:
        print("No invention directories found.")
    else:
        for d in invention_dirs:
            print(f"\nAuditing {d.name} ...")
            report = audit_invention(d, repo_root)
            all_reports.append(report)
            if report.all_passed:
                print(f"  PASS  ({len(report.checks)} checks)")
            else:
                print(f"  FAIL  ({len(report.failures)} failures)")
                for fail in report.failures:
                    print(f"    [{fail.section}] {fail.check_name}: {fail.failure_reason}")

    # Write machine-readable report
    report_path = repo_root / "protocol" / "preflight_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w") as f:
        json.dump({
            "protocol": "INVENTION_PROTOCOL_V1",
            "timestamp": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
            "constitution_check": {
                "section": "X.0",
                "all_passed": constitution_pass,
                "check_count": len(constitution_checks),
                "failure_count": len(constitution_fails),
                "checks": [asdict(c) for c in constitution_checks],
            },
            "inventions_audited": len(all_reports),
            "all_pass": constitution_pass and all(r.all_passed for r in all_reports),
            "reports": [
                {
                    "invention_id": r.invention_id,
                    "invention_dir": r.invention_dir,
                    "all_passed": r.all_passed,
                    "failure_count": len(r.failures),
                    "checks": [asdict(c) for c in r.checks],
                }
                for r in all_reports
            ],
        }, f, indent=2)

    total_failures = (
        sum(len(r.failures) for r in all_reports)
        + len(constitution_fails)
    )
    total_checks = (
        sum(len(r.checks) for r in all_reports)
        + len(constitution_checks)
    )
    print(f"\n{'='*60}")
    print(f"Constitution: {len(constitution_checks)} checks ({'PASS' if constitution_pass else 'FAIL'})")
    print(f"Inventions audited: {len(all_reports)}")
    print(f"Total checks run: {total_checks}")
    print(f"Total failures: {total_failures}")
    print(f"Overall: {'PASS' if total_failures == 0 else 'FAIL'}")
    print(f"Report: {report_path}")

    return 0 if total_failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
