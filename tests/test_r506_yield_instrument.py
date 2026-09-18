#!/usr/bin/env python3
"""tests/test_r506_yield_instrument.py — CI pin suite for the R506 DISCOVERY
YIELD instrument (the R498 registry-pin lineage: records are the artifacts;
tests pin their invariants so any silent mutation fails CI).

Pinned facts (repo bytes only — CI-safe, the durable worktree is NOT required):
  1. THE FREEZE: scripts/r506_discovery_yield.py sha256 ==
     R506/YIELD_INSTRUMENT.json script_sha256 == the pre-registered
     831f1a0e… hash. Any instrument edit = new version (the freeze rule);
     this pin makes a silent edit fail CI instead.
  2. THE FUNNEL: the 10 frozen transitions and the 14-reason typed
     vocabulary in the spec match the script's own constants exactly.
  3. THE HONESTY PINS: the four spec-level pins (novelty/cost/attacker/
     family) are present.
  4. HERMETIC ACCEPTANCE 3/3: the three sealed-terminal case records exist
     and carry the exact reproduced claims (R489 mid-flight divergence,
     R484 child-admitted, R487 terminal closure) — the audit-verified
     honesty calls (blocking_count=None -> STAGE_INCOMPLETE,
     grid-advanced exclusion) stay pinned.
  5. THE BATTERY MANIFEST CHAIN: sha256(BATTERY_PROBLEMS.json) ==
     BATTERY_SESSIONS.manifest_sha256; 6 problems / 3 declared families;
     the disjointness rule is present.
  6. THE HARVEST RULES PRE-REGISTRATION: R506/HARVEST_RULES.json
     self-attests the rules script sha; the 6 seed record ids
     (nhtsa_odi:{odi}) match the manifest; verdict vocabularies and the
     merge contract (adds sections only, rows/aggregate untouched) are
     pinned; the timing proof is recorded (pre-registered while runs were
     live, before any terminal harvest).
  7. THE HARVEST CONTRACT: once R506/YIELD_MEASUREMENT.json exists it MUST
     carry contamination_audit + clarification_audit + harvest_rules with a
     pre_merge_sha256 (audit corrections 2+3 attached to every harvest).
"""
import hashlib
import json
import os
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
R506 = REPO / "R506"
SPEC = R506 / "YIELD_INSTRUMENT.json"
INSTRUMENT = REPO / "scripts" / "r506_discovery_yield.py"
RULES = R506 / "HARVEST_RULES.json"
RULES_SCRIPT = REPO / "scripts" / "r506_harvest_rules.py"
MEASUREMENT = R506 / "YIELD_MEASUREMENT.json"

FROZEN_INSTRUMENT_SHA = "831f1a0e075cb9dd"

FUNNEL_FROZEN = [
    "fresh_submitted", "premise_coherent", "evidence_verified",
    "mechanisms_found", "candidates_generated_distinct", "attack_survivors",
    "contradiction_survivors", "experimentally_discriminated",
    "mutated_survivors", "buyer_ready",
]

REASONS_FROZEN = {
    "PREMISE_INCOHERENT", "EVIDENCE_UNVERIFIED", "NO_CANDIDATES",
    "NO_DISTINCT_CANDIDATES", "ALL_DISTINCTNESS_INDETERMINATE",
    "ATTACK_KILLED", "BLOCKING_CONTRADICTIONS", "NO_NON_VACUOUS_EXPERIMENT",
    "NO_MUTATED_SURVIVOR", "RELEASE_NOT_EMITTED", "RELEASE_HELD",
    "PACKAGE_NOT_EMITTED", "STAGE_INCOMPLETE", "MID_FLIGHT_PER_LXXIV",
}


def _load(p: Path):
    # utf-8 ALWAYS (the R505 harness lesson: locale-decoding runners
    # must reconstruct the same bytes, not a new hash)
    return json.loads(p.read_text(encoding="utf-8"))


def _sha(p: Path):
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ---------- 1. the freeze ----------

def test_instrument_script_sha_matches_preregistration():
    spec = _load(SPEC)
    actual = _sha(INSTRUMENT)
    assert actual == spec["script_sha256"]
    assert actual.startswith(FROZEN_INSTRUMENT_SHA)
    assert spec["freeze_rule"]  # the freeze rule is recorded, non-empty


def test_instrument_version_and_id_frozen():
    spec = _load(SPEC)
    assert spec["instrument_id"] == "r506_discovery_yield"
    assert spec["instrument_version"] == "1.0.0"


# ---------- 2. the funnel ----------

def test_funnel_transitions_frozen():
    spec = _load(SPEC)
    ft = spec["funnel_transitions"]
    assert [t["name"] for t in ft] == FUNNEL_FROZEN
    assert [t["index"] for t in ft] == list(range(1, 11))
    assert all(t.get("byte_source") for t in ft)
    # behavioral: the script's own aggregate order must equal the frozen list
    import importlib.util
    ispec = importlib.util.spec_from_file_location("yi", INSTRUMENT)
    mod = importlib.util.module_from_spec(ispec)
    ispec.loader.exec_module(mod)
    agg = mod.aggregate([])
    assert [f["transition"] for f in agg["funnel"]] == FUNNEL_FROZEN


def test_reason_vocabulary_frozen():
    spec = _load(SPEC)
    vocab = spec["reason_vocabulary_frozen"]
    names = set(vocab if isinstance(vocab, list) else vocab.keys())
    assert names == REASONS_FROZEN
    # and the script's REASONS set must equal the spec vocabulary
    import importlib.util
    ispec = importlib.util.spec_from_file_location("yi", INSTRUMENT)
    mod = importlib.util.module_from_spec(ispec)
    ispec.loader.exec_module(mod)
    assert mod.REASONS == REASONS_FROZEN


def test_honesty_pins_present():
    spec = _load(SPEC)
    pins = spec["honesty_pins"]
    assert len(pins) >= 4
    joined = " ".join(pins)
    assert "NOVELTY_LEFT_UNRESOLVED_BY_RING_FAILURES" in joined
    assert "UNKNOWN_PER_ART_XXV" in joined
    assert "attacker_provenance typed on every attack_survivors transition" in joined
    assert "ABSENT_IN_DURABLE_RECORD" in joined


def test_mid_flight_rule_frozen():
    spec = _load(SPEC)
    assert "MID_FLIGHT_OR_PARTIAL_PER_LXXIV" in spec["mid_flight_rule"]
    assert "never collapsed" in spec["mid_flight_rule"]


# ---------- 4. hermetic acceptance 3/3 ----------

def test_hermetic_case1_r489_mid_flight_divergence():
    r = _load(R506 / "HERMETIC_CASE1_R489_CHECKPOINT_96965e28.json")["rows"][0]
    assert r["terminal"] is False
    assert r["run_state"] == "MID_FLIGHT_OR_PARTIAL_PER_LXXIV"
    assert r["lost_at"] == "mechanisms_found"
    assert r["typed_drop_reason"] == "NO_CANDIDATES"
    atk = r["attack_survivors"]
    assert atk["reached"] is False
    assert atk["killed_dimensions"] == ["obvious_combination"]
    assert r["mutated_survivors"]["deferred_to_kill_point"] is True
    assert r["mutated_survivors"]["improve_statuses"] == ["DEFERRED_TO_KILL_POINT"]
    assert r["mutated_survivors"]["children"] == []


def test_hermetic_case2_r484_child_admitted():
    r = _load(R506 / "HERMETIC_CASE2_R484_TERMINAL.json")["rows"][0]
    assert r["terminal"] is True
    assert r["run_state"] == "TERMINAL_COMMIT_PER_LXXIV"
    atk = r["attack_survivors"]
    assert atk["killed_dimensions"] == ["engineering_infeasibility",
                                        "obvious_combination",
                                        "unsupported_mechanism",
                                        "weak_transfer"]
    ms = r["mutated_survivors"]
    assert ms["reached"] is True and ms["count"] == 1
    assert ms["delta_real"] is True
    br = r["buyer_ready"]
    assert br["reached"] is False and br["typed_drop_reason"] == "RELEASE_HELD"


def test_hermetic_case3_r487_terminal_closure():
    r = _load(R506 / "HERMETIC_CASE3_R487_TERMINAL_34d81fb9.json")["rows"][0]
    assert r["terminal"] is True
    assert r["manifest_final_status"] == "INVENTION_UNDER_DEVELOPMENT"
    assert r["mutated_survivors"]["reached"] is True
    br = r["buyer_ready"]
    assert br["reached"] is False and br["typed_drop_reason"] == "RELEASE_HELD"
    assert br["package_zip"] is None
    assert br["real_loop_verified"] is False
    assert r["lost_at"] is not None  # the R487/R489 divergence ruling target


def test_hermetic_cases_declared_reproduced_in_spec():
    spec = _load(SPEC)
    ha = spec["hermetic_acceptance"]
    for key in ("case_1", "case_2", "case_3"):
        assert ha[key]["reproduced"] is True
        rec = R506 / Path(ha[key]["record"]).name
        assert rec.exists(), f"hermetic record missing: {rec}"
        # the record was produced by the SAME frozen instrument version
        doc = _load(rec)
        assert doc["instrument_version"] == spec["instrument_version"]
        assert doc["instrument"] == spec["instrument_id"]


# ---------- 5. the battery manifest chain ----------

def test_battery_manifest_chain_and_families():
    manifest = _load(R506 / "BATTERY_PROBLEMS.json")
    sessions = _load(R506 / "BATTERY_SESSIONS.json")
    assert sessions["manifest_sha256"] == _sha(R506 / "BATTERY_PROBLEMS.json")
    assert manifest["n_problems"] == 6
    assert manifest["n_families"] == 3
    assert set(manifest["declared_families"]) == {"mechanical", "thermal",
                                                  "electrical"}
    assert manifest["disjointness_rule"]
    assert manifest["verbatim_policy"]


def test_battery_problems_are_verbatim_sha_pinned():
    manifest = _load(R506 / "BATTERY_PROBLEMS.json")
    for p in manifest["problems"]:
        body = p["summary_verbatim"].encode("utf-8")
        assert hashlib.sha256(body).hexdigest() == p["verbatim_summary_sha256"]
        assert p["source"] == "NHTSA_ODI"


# ---------- 6. the harvest rules pre-registration ----------

def test_harvest_rules_script_self_attestation():
    rules = _load(RULES)
    assert rules["script_sha256"] == _sha(RULES_SCRIPT)
    assert rules["rules_id"] == "r506_harvest_rules"
    assert rules["rules_version"] == "1.0.0"


def test_harvest_rules_rules_sha_self_excluded_hash():
    rules = _load(RULES)
    recorded = rules.pop("rules_sha256")
    blob = json.dumps(rules, sort_keys=True, ensure_ascii=False).encode("utf-8")
    assert hashlib.sha256(blob).hexdigest() == recorded


def test_harvest_rules_seeds_match_manifest():
    rules = _load(RULES)
    manifest = _load(R506 / "BATTERY_PROBLEMS.json")
    expected = {f"nhtsa_odi:{p['source_id'].split(':', 1)[1]}"
                for p in manifest["problems"]}
    got = {s["seed_record_id"] for s in rules["seeds"]}
    assert got == expected and len(got) == 6
    # every seed narrative is byte-identical to the manifest verbatim
    by_odi = {f"nhtsa_odi:{p['source_id'].split(':', 1)[1]}": p
              for p in manifest["problems"]}
    for s in rules["seeds"]:
        assert s["narrative_text"] == by_odi[s["seed_record_id"]]["summary_verbatim"]


def test_harvest_rules_verdict_vocabularies_and_merge_contract():
    rules = _load(RULES)
    cr = rules["contamination_rule"]
    assert set(cr["verdicts"]) == {"CLEAN", "SELF-EVIDENCE-EXCLUDED",
                                   "CONTAMINATED"}
    assert "cannot credit verification or mechanism grounding" in cr["statement"]
    assert "failure_universe.py:66-167" in cr["threat"]
    ar = rules["clarification_audit_rule"]
    assert set(ar["verdicts"]) == {
        "BLINDNESS_INTACT_VERBATIM_SUBSET",
        "BLINDNESS_DOWNGRADED_NEW_CONTENT",
        "CLARIFICATION_BYTES_ABSENT_IN_DURABLE_RECORD"}
    mc = rules["merge_contract"]
    assert mc["adds_sections_only"] == ["contamination_audit",
                                        "clarification_audit", "harvest_rules"]
    assert mc["never_mutates"] == ["rows", "aggregate"]
    assert mc["assert_funnel_untouched_before_write"] is True
    assert mc["pre_merge_sha256_recorded"] is True


def test_harvest_rules_timing_proof_recorded():
    rules = _load(RULES)
    tp = rules["timing_proof"]
    # recorded BYTES from commit time (never re-derived from live state)
    assert tp["yield_measurement_absent_at_commit"] is True
    assert tp["all_battery_sessions_non_terminal_at_commit"] is True
    assert len(tp["battery_sessions_at_commit"]) == 6
    assert "pre-registered BEFORE any battery terminal harvest" in tp["requirement"]


# ---------- 7. the harvest contract (once harvest lands) ----------

def test_measurement_must_carry_the_rule_sections():
    if not MEASUREMENT.exists():
        pytest.skip("harvest has not landed yet (pre-registration window)")
    m = _load(MEASUREMENT)
    for section in ("contamination_audit", "clarification_audit",
                    "harvest_rules"):
        assert section in m, (
            f"harvest landed without the {section} section — audit "
            "corrections 2+3 must attach to EVERY harvest")
    assert m["harvest_rules"]["pre_merge_sha256"]
    assert m["harvest_rules"]["script_sha256"] == _sha(RULES_SCRIPT)
    assert m["instrument_sha256"] == _sha(INSTRUMENT)
