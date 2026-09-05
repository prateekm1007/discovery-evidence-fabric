#!/usr/bin/env python3
"""scripts/r412_seal_verify.py — verify the R412 gradient v2 seal.

Checks (Constitution Articles XIV, XXVI; operator directive Step 7):
  1. Every artifact hash recorded in R412_GRADIENT_V2_PREREGISTRATION.json
     matches the file on disk (tamper detection).
  2. The instrument finding carries the three exact required conclusions
     (NOT_DETERMINED / TVM_PROPOSER_SCHEMA_FAILURE / NOT_PERMITTED).
  3. The calibration corpus hash matches the corpus on disk AND the hash
     pinned in the test suite (double pin).
  4. The parser method registry equals the frozen ruleset registry.
  5. The capability-family map validates.
  6. The run gate is BLOCKED with the three unresolved fields; zero
     gradient/discovery model calls recorded; the transport probe verdict
     is recorded honestly.
  7. Reports git HEAD + working-tree state for context (the seal of record
     is the COMMIT, verified from the committed bytes).

Exit 0 = SEAL_VERIFIED (with the run gate state, which is BLOCKED until
the operator resolves the population/seed/TVM inputs).
Exit 1 = SEAL_BROKEN (printed reason; research stays stopped).
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path("/home/z/my-project/audit_ws/repo")
V2DIR = REPO / "R412" / "GRADIENT_V2"
sys.path.insert(0, str(V2DIR))

PREREG_PATH = V2DIR / "R412_GRADIENT_V2_PREREGISTRATION.json"
FINDING_PATH = REPO / "R412" / "R412_GRADIENT_V1_INSTRUMENT_FINDING.json"
CORPUS_PATH = V2DIR / "TVM_V2_PARSER_CALIBRATION_CORPUS.json"
RULES_PATH = V2DIR / "NORMALIZATION_RULES.json"
TEST_PATH = REPO / "tests" / "test_r412_tvm_v2.py"

REQUIRED_CONCLUSIONS = {
    "scientific_conclusion": "NOT_DETERMINED",
    "instrument_conclusion": "TVM_PROPOSER_SCHEMA_FAILURE",
    "frontier_absence_conclusion": "NOT_PERMITTED",
}

REQUIRED_BLOCKED_FIELDS = {"population_hash", "seed_allocation",
                           "tvm_snapshot_hash"}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_state() -> dict:
    def run(args):
        try:
            return subprocess.run(
                ["git", "-C", str(REPO)] + args,
                capture_output=True, text=True, timeout=30,
            ).stdout.strip()
        except Exception as exc:  # pragma: no cover
            return f"ERROR: {exc}"
    return {
        "head": run(["rev-parse", "HEAD"]),
        "branch": run(["rev-parse", "--abbrev-ref", "HEAD"]),
        "status_r412": run(["status", "--porcelain", "--", "R412",
                            "scripts/r412_generate_artifacts.py",
                            "scripts/r412_seal_verify.py",
                            "scripts/r412_corpus_check.py",
                            "tests/test_r412_tvm_v2.py"]),
    }


def main() -> int:
    failures = []
    checks = []

    prereg = json.loads(PREREG_PATH.read_text(encoding="utf-8"))

    # --- 1. Artifact hash pinning -----------------------------------------
    hash_checks = [
        ("parser module",
         prereg["v2_parser_specification"]["sha256"],
         V2DIR / "tvm_v2" / "value_parser.py"),
        ("calibration corpus",
         prereg["parser_calibration_corpus"]["sha256"], CORPUS_PATH),
        ("normalization rules",
         prereg["normalization_rules"]["sha256"], RULES_PATH),
        ("capability family map",
         prereg["capability_family_layer"]["sha256"],
         V2DIR / "CAPABILITY_FAMILY_MAP.json"),
        ("capability family module",
         prereg["capability_family_layer"]["module_sha256"],
         V2DIR / "tvm_v2" / "capability_family.py"),
        ("signal policy module",
         prereg["signal_policy"]["module_sha256"],
         V2DIR / "tvm_v2" / "signal_policy.py"),
        ("evidence contract module",
         prereg["evidence_contract"]["module_sha256"],
         V2DIR / "tvm_v2" / "evidence_contract.py"),
        ("v1 instrument finding",
         prereg["v1_provenance"]["v1_instrument_finding"]["sha256"],
         FINDING_PATH),
        ("v1 output reparse measurement",
         prereg["v1_output_reparse_measurement"]["sha256"],
         V2DIR / "V1_OUTPUT_REPARSE_MEASUREMENT.json"),
        ("transport probe",
         prereg["transport_probe"]["sha256"],
         V2DIR / "TRANSPORT_PROBE.json"),
        ("generator script",
         prereg["generator"]["sha256"],
         REPO / "scripts" / "r412_generate_artifacts.py"),
        ("gateway script",
         prereg["model_pin"]["gateway_script_sha256"],
         REPO / "scripts" / "zai_gateway.mjs"),
    ]
    for prompt_id, ph in prereg["prompt_hashes"]["files"].items():
        hash_checks.append(
            (f"prompt {prompt_id}", ph, V2DIR / "PROMPTS" / f"{prompt_id}.json"))

    for label, expected, path in hash_checks:
        actual = sha256_file(path)
        ok = actual == expected
        checks.append((f"hash:{label}", ok))
        if not ok:
            failures.append(f"hash_mismatch:{label}")

    # --- 2. Instrument finding conclusions --------------------------------
    finding = json.loads(FINDING_PATH.read_text(encoding="utf-8"))
    for key, expected in REQUIRED_CONCLUSIONS.items():
        ok = finding.get(key) == expected
        checks.append((f"finding:{key}", ok))
        if not ok:
            failures.append(f"finding_conclusion_wrong:{key}")

    # --- 3. Corpus double pin (prereg + test suite) -----------------------
    corpus_hash = sha256_file(CORPUS_PATH)
    test_src = TEST_PATH.read_text(encoding="utf-8") \
        if TEST_PATH.exists() else ""
    test_pins = (corpus_hash in test_src)
    checks.append(("corpus pinned in tests", test_pins))
    if not test_pins:
        failures.append("corpus_hash_not_pinned_in_tests")

    # --- 4. Method registry vs ruleset ------------------------------------
    rules = json.loads(RULES_PATH.read_text(encoding="utf-8"))
    from tvm_v2.value_parser import METHOD_REGISTRY  # noqa: E402
    registry_ok = (sorted(METHOD_REGISTRY) ==
                   sorted(rules["method_registry_must_equal"]))
    checks.append(("method registry == ruleset", registry_ok))
    if not registry_ok:
        failures.append("method_registry_disagrees_with_ruleset")

    # --- 5. Capability family map valid ------------------------------------
    from tvm_v2.capability_family import validate_family_map  # noqa: E402
    fam_ok, fam_issues = validate_family_map()
    checks.append(("capability family map valid", fam_ok))
    if not fam_ok:
        failures.append(f"family_map_invalid:{fam_issues}")

    # --- 6. Run gate honesty ------------------------------------------------
    gate = prereg["run_gate"]
    gate_blocked = gate["state"] == "BLOCKED_PENDING_OPERATOR_INPUT"
    gate_fields = set(gate["blocking_fields"])
    gate_fields_ok = gate_fields == REQUIRED_BLOCKED_FIELDS
    budget = prereg["cost_budget"]
    zero_calls = budget["gradient_calls_spent_before_seal"] == 0
    probe = json.loads((V2DIR / "TRANSPORT_PROBE.json").read_text(
        encoding="utf-8"))
    probe_honest = (probe["gradient_model_calls_made"] == 0
                    and probe["discovery_model_calls_made"] == 0)
    checks.append(("run gate BLOCKED", gate_blocked))
    checks.append(("run gate fields exact", gate_fields_ok))
    checks.append(("zero gradient calls before seal", zero_calls))
    checks.append(("probe records zero discovery calls", probe_honest))
    if not gate_blocked:
        failures.append("run_gate_not_blocked")
    if not gate_fields_ok:
        failures.append("run_gate_fields_wrong")
    if not zero_calls:
        failures.append("gradient_calls_before_seal")
    if not probe_honest:
        failures.append("probe_claims_zero_but_budget_does_not")

    # --- Report -------------------------------------------------------------
    state = git_state()
    print("R412 GRADIENT V2 SEAL VERIFICATION")
    print(f"  git HEAD: {state['head']}")
    print(f"  branch:   {state['branch']}")
    print(f"  working-tree (R412 surface): "
          f"{state['status_r412'] or 'clean'}")
    for label, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}")
    if failures:
        print("SEAL_BROKEN: " + "; ".join(failures))
        return 1
    print(f"SEAL_VERIFIED with RUN_GATE={gate['state']}")
    print("  blocking fields: " + ", ".join(sorted(gate_fields)))
    print("  gradient/discovery model calls made: 0 (liveness probe only)")
    print("  research remains STOPPED until the operator resolves the "
          "blocking fields (Constitution Article XIV).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
