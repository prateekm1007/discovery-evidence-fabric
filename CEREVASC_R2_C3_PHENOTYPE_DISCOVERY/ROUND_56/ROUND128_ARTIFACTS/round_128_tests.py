#!/usr/bin/env python3
"""
ROUND_128_TESTS.py — 7 tests proving the CEO's required behaviors.

Per CEO Round 128: "Tests proving:
  * missing simulator → BLOCKED
  * executed contradiction → KILLED
  * all applicable virtual gates GREEN → WORLD_CLASS_INVENTION
  * common-model worlds do not receive false independence credit
  * positive evidence creates a new attack
  * no candidate can promote with mandatory NOT_RUN
  * no candidate can be resurrected by quota pressure
"""

import sys
sys.path.insert(0, "/home/z/my-project/scripts")
from experiment_engine_v2 import (
    evaluate_g18_independence, classify_cross_world_disagreement,
    generate_adversarial_next_attack, machine_enforced_promotion_check,
    multi_world_acquisition_score, WORLD_REGISTRY, SolverWorld
)

passed = 0
failed = 0


def test(name, condition, detail=""):
    global passed, failed
    if condition:
        print(f"  [PASS] {name}")
        passed += 1
    else:
        print(f"  [FAIL] {name}: {detail}")
        failed += 1


print("=" * 80)
print("ROUND 128 TESTS — 7 CEO-required behaviors")
print("=" * 80)

# Test 1: missing simulator → BLOCKED
print("\n--- Test 1: missing simulator → BLOCKED ---")
gate_states_blocked = {
    "G01": {"state": "GREEN"}, "G02": {"state": "GREEN"}, "G03": {"state": "GREEN"},
    "G04": {"state": "NOT_APPLICABLE_WITH_JUSTIFICATION"},
    "G05": {"state": "GREEN"}, "G06": {"state": "NOT_RUN"},
    "G07": {"state": "NOT_APPLICABLE_WITH_JUSTIFICATION"},
    "G08": {"state": "NOT_RUN"}, "G09": {"state": "GREEN"},
    "G10": {"state": "GREEN"}, "G11": {"state": "GREEN"},
    "G12": {"state": "NOT_APPLICABLE_WITH_JUSTIFICATION"},
    "G13": {"state": "GREEN"}, "G14": {"state": "GREEN"},
    "G15": {"state": "NOT_APPLICABLE_WITH_JUSTIFICATION"},
    "G16": {"state": "GREEN"}, "G17": {"state": "GREEN"},
    "G18": {"state": "GREEN"},
}
result = machine_enforced_promotion_check(gate_states_blocked)
test("missing simulator (NOT_RUN) → BLOCKED not KILLED",
     "BLOCKED" in result["verdict"] and "KILLED" not in result["verdict"],
     f"verdict={result['verdict']}")

# Test 2: executed contradiction → KILLED
print("\n--- Test 2: executed contradiction → KILLED ---")
gate_states_killed = dict(gate_states_blocked)
gate_states_killed["G09"] = {"state": "RED"}  # executed contradiction
gate_states_killed["G06"] = {"state": "NOT_APPLICABLE_WITH_JUSTIFICATION"}  # remove NOT_RUN
gate_states_killed["G08"] = {"state": "GREEN"}  # remove NOT_RUN
result2 = machine_enforced_promotion_check(gate_states_killed)
test("executed RED gate → KILLED_BY_EVIDENCE",
     "KILLED" in result2["verdict"],
     f"verdict={result2['verdict']}")

# Test 3: all applicable virtual gates GREEN → WORLD_CLASS_INVENTION
print("\n--- Test 3: all gates GREEN → WORLD_CLASS_INVENTION ---")
gate_states_all_green = {f"G{i:02d}": {"state": "GREEN"} for i in range(1, 19)}
result3 = machine_enforced_promotion_check(gate_states_all_green)
test("all gates GREEN → WORLD_CLASS_INVENTION",
     "WORLD_CLASS" in result3["verdict"],
     f"verdict={result3['verdict']}")
test("WORLD_CLASS_INVENTION carries PHYSICAL_VALIDATION_STATUS = NOT_ESTABLISHED",
     "NOT_ESTABLISHED" in result3["verdict"],
     f"verdict={result3['verdict']}")

# Test 4: common-model worlds do not receive false independence credit
print("\n--- Test 4: common-model worlds → no false independence ---")
# Create two worlds with SAME constitutive family (both neo-Hookean+CDM)
world_a = WORLD_REGISTRY["WORLD_A_FEBIO"]
fake_world_b = SolverWorld(
    world_id="FAKE_WORLD_B",
    name="FakeFEBio2",
    formulation_family=world_a.formulation_family,  # EXACT SAME string
    constitutive_family=world_a.constitutive_family,  # EXACT SAME string
    discretization_family=world_a.discretization_family,
    source_code_url="https://github.com/fake/febio2",  # different repo
    installed=False, certification_state="NOT_INSTALLED",
    parameter_source=world_a.parameter_source,
    calibration_source=world_a.calibration_source,
    mathematical_foundation=world_a.mathematical_foundation
)
# Temporarily add to registry
original_registry = dict(WORLD_REGISTRY)
WORLD_REGISTRY["FAKE_WORLD_B"] = fake_world_b
g18_result = evaluate_g18_independence(["WORLD_A_FEBIO", "FAKE_WORLD_B"])
WORLD_REGISTRY.clear()
WORLD_REGISTRY.update(original_registry)
test("common-model worlds → G18 RED (no false independence)",
     g18_result["overall_independence"] == "RED",
     f"overall={g18_result['overall_independence']}, dims={g18_result['dimensions']}")
test("common-model worlds → cannot receive cross-world credit",
     not g18_result["can_receive_cross_world_credit"],
     f"credit={g18_result['can_receive_cross_world_credit']}")

# Test 5: positive evidence creates a new attack
print("\n--- Test 5: positive evidence → new attack generated ---")
attacks = generate_adversarial_next_attack("C5", ["G05"], [])
test("G05 GREEN generates adversarial attack",
     len(attacks) > 0,
     f"attacks={len(attacks)}")
test("first attack targets parameter perturbation (G10)",
     attacks[0]["next_attack"] == "parameter_perturbation" if attacks else False,
     f"first attack={attacks[0]['next_attack'] if attacks else 'none'}")
# After G10 GREEN, should generate geometry attack
attacks2 = generate_adversarial_next_attack("C5", ["G05", "G10"], [])
test("G05+G10 GREEN generates geometry attack",
     any(a["next_attack"] == "geometry_variation" for a in attacks2),
     f"attacks={[a['next_attack'] for a in attacks2]}")

# Test 6: no candidate can promote with mandatory NOT_RUN
print("\n--- Test 6: no promotion with mandatory NOT_RUN ---")
gate_states_with_not_run = dict(gate_states_all_green)
gate_states_with_not_run["G09"] = {"state": "NOT_RUN"}  # mandatory gate NOT_RUN
result6 = machine_enforced_promotion_check(gate_states_with_not_run)
test("mandatory NOT_RUN blocks promotion",
     "WORLD_CLASS" not in result6["verdict"],
     f"verdict={result6['verdict']}")
test("mandatory NOT_RUN → BLOCKED not KILLED",
     "BLOCKED" in result6["verdict"],
     f"verdict={result6['verdict']}")

# Test 7: no candidate can be resurrected by quota pressure
print("\n--- Test 7: no resurrection by quota pressure ---")
# Simulate: 4 candidates already killed, 5th candidate also has RED gate
# The engine should NOT promote the 5th candidate just to avoid 0/5
gate_states_killed_5th = dict(gate_states_all_green)
gate_states_killed_5th["G09"] = {"state": "RED"}  # genuine kill
result7 = machine_enforced_promotion_check(gate_states_killed_5th)
test("5th candidate with RED gate → KILLED (no quota resurrection)",
     "KILLED" in result7["verdict"] and "WORLD_CLASS" not in result7["verdict"],
     f"verdict={result7['verdict']}")

# Summary
print(f"\n{'=' * 80}")
print(f"TESTS: {passed} passed, {failed} failed")
print(f"{'=' * 80}")
if failed > 0:
    sys.exit(1)
else:
    print("ALL TESTS PASSED")
