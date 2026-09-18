#!/usr/bin/env python3
"""tests/test_r505_strong_ring_and_recovery.py — hermetic pins for the
R505 round artifacts (the R498 registry-pin lineage: records are the
artifacts; tests pin their invariants so any silent mutation fails CI).

Pinned facts:
  1. REGISTRY 1.4.0: patentbear carries the MEASURED_R505 pool state
     (the 401-retired first key, the preserved last debit, the CDN-UA
     transport lesson); MEASURED_R505 provenance class present.
  2. THE STRONG-RING MEASUREMENT (R505/A2_V42_XKIRO): the v4.2
     attacker-computes standard measured on xkiro (qwen3.5-plus:free,
     uniform composition) — TPR 0.5455 / FPR 0.0 / rule45 firings 3 /
     NOT_CALIBRATED (tpr_min unmet — honestly recorded); the corpus is
     the frozen R492 DEV corpus, byte-identical (reconstruction sha).
  3. THE ANTI-SHOPPING LEDGER SHAPE: 21 verdict-class records; the 2
     EVALUATION_FAILED cases (parse-defect measured attempts) are
     counted against strict coverage, never retried, never scored as
     survival.
  4. THE FAILED-RING ATTEMPTS PRESERVED: unorouter AUTH_FAILURE and
     apinex CREDIT_EXHAUSTED typed in their attempt records (the ring
     landscape is measured state, never narrative).
  5. BS-021: NO raw credential value appears in ANY R505 record or
     script (fingerprints only).
  6. The value-recovery record: the probe state, the pool conclusion,
     the active key NOT probed (the R504 last-debit decision pinned).
"""
import hashlib
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
R505 = REPO / "R505"
FROZEN_SHA = "1e4a593fe887e64e19559f003ac7c1d8553b74a84572c98b03d903d58ed6480e"

# the two operator-supplied PatentBear key values are NEVER inlined in
# tests either — the scan uses sha256 fingerprints only (BS-021)
REGISTERED_FINGERPRINTS = {"561b6e70f5b5ea7f", "50fe7b3d569bb1fa"}


def _load(p: Path):
    return json.loads(p.read_text())


# ---------- 1. registry 1.4.0 ----------

def test_registry_1_4_0_patentbear_r505_pool_state():
    reg = _load(REPO / "PATENT_SOURCE_REGISTRY.json")
    assert reg["version"] == "1.4.0"
    assert reg["updated_round"] == "R505"
    pb = reg["sources"]["patentbear"]["properties"]
    assert "POOL_EXHAUSTED_MEASURED" in pb["RATE-LIMITED"]
    assert "MEASURED_R505" in pb["RATE-LIMITED"]
    # the 401-retired first key
    assert "401 isError" in pb["ACCESSIBLE"]
    # the CDN-UA transport lesson (Art. XXXI)
    assert "Error 1010" in pb["ACCESSIBLE"]
    # custody correction
    assert "MEASURED_R505" in pb["AUTHENTICATED"]
    pc = reg["provenance_classes"]
    classes = pc.keys() if isinstance(pc, dict) else pc
    assert "MEASURED_R505" in classes
    ev = reg["sources"]["patentbear"]["evidence"]
    assert any("R505/PATENTBEAR_VALUE_RECOVERY.json" in e for e in ev)


# ---------- 2. the strong-ring measurement ----------

def test_xkiro_measurement_headline_pinned():
    r = _load(R505 / "A2_V42_XKIRO" / "MEASUREMENT_RESULTS.json")
    assert r["artifact_type"] == "A2_V42_RING_MEASUREMENT_RESULTS"
    assert r["round"] == "R505"
    assert r["deployed_commit"].startswith("d7520b9b")
    h = r["headline"]
    assert h["tpr_defect_cohorts"] == 0.5455
    assert h["detected_in_defect_cohorts"] == "6/11"
    assert h["fpr_known_good"] == 0.0
    assert h["false_kills_on_controls"] == "0/4"
    assert h["coverage_all_9_fields"] == 1.0
    assert h["parse_completeness"] == 1.0
    # the honest verdict: NOT calibrated, the exact failure named
    assert r["threshold_verdict"]["calibrated"] is False
    assert r["threshold_verdict"]["failures"] == ["tpr_min"]


def test_xkiro_measurement_rule45_fired():
    r = _load(R505 / "A2_V42_XKIRO" / "MEASUREMENT_RESULTS.json")
    r45 = r["rule45_attacker_computes"]
    # the v4.2 standard FIRED on a strong ring (zero on every prior ring)
    assert r45["total_firings"] == 3
    assert "a2dev-01-cavitation-radical-bulk-kill" in r45["cases_with_firings"]
    # and the firings are real in the per-case raw records
    for cid in r45["cases_with_firings"]:
        raw = _load(R505 / "A2_V42_XKIRO" / "RAW" / f"{cid}.json")
        corr = (raw.get("attack") or {}).get("v4_corrections_applied") or []
        assert "burden_of_proof:attacker_computed_derivation" in corr


def test_xkiro_measurement_ring_derived_not_asserted():
    r = _load(R505 / "A2_V42_XKIRO" / "MEASUREMENT_RESULTS.json")
    ring = r["ring"]
    # the pin is DERIVED from the per-case records (the R491 pattern)
    assert ring["pin"] == "xkiro"
    assert ring["served_providers"] == {"xkiro": 19}
    # the uniform model composition disclosed as measured
    assert ring["served_models"] == {"qwen/qwen3.5-plus:free": 19}
    assert "model_mix_disclosure" in ring


def test_corpus_frozen_unchanged():
    # the canonical reconstruction sha (the R492 freeze contract)
    corpus = _load(REPO / "R492" / "A2_DEV_CORPUS" / "CORPUS.json")
    body = {k: v for k, v in corpus.items() if k != "corpus_sha256"}
    blob = json.dumps(body, indent=2, ensure_ascii=False) + "\n"
    actual = hashlib.sha256(blob.encode("utf-8")).hexdigest()
    freeze = _load(REPO / "R492" / "A2_DEV_CORPUS" / "FREEZE.json")
    assert actual == freeze["corpus_sha256"] == FROZEN_SHA
    r = _load(R505 / "A2_V42_XKIRO" / "MEASUREMENT_RESULTS.json")
    assert r["corpus_sha256"] == FROZEN_SHA
    assert r["n_cases"] == 21


# ---------- 3. the anti-shopping ledger shape ----------

def test_ledger_shape_21_verdict_class_no_shopping():
    r = _load(R505 / "A2_V42_XKIRO" / "MEASUREMENT_RESULTS.json")
    raw_dir = R505 / "A2_V42_XKIRO" / "RAW"
    files = sorted(raw_dir.glob("*.json"))
    assert len(files) == 21, "every corpus case has exactly one record"
    states = {}
    for f in files:
        rec = _load(f)
        overall = (rec.get("attack") or {}).get("overall")
        states[overall] = states.get(overall, 0) + 1
    # 19 clean verdicts + 2 parse-defect measured attempts — and the
    # strict coverage counts the 2 against coverage (never survival)
    assert states.get("KILLED") == 7
    assert states.get("PASS") == 12
    assert states.get("EVALUATION_FAILED") == 2
    assert r["n_measured"] == 19
    assert r["n_attack_incomplete"] == 2
    assert r["headline"]["coverage_strict_incl_not_measured"] == \
        pytest.approx(19 / 21, abs=1e-4)
    assert r["headline"]["coverage_strict_incl_not_measured"] >= 0.875


def test_scope_and_malformed_disciplines_hold_on_strong_ring():
    r = _load(R505 / "A2_V42_XKIRO" / "MEASUREMENT_RESULTS.json")
    d = r["category_disciplines"]
    # the scope-conflict traps: no scope-mismatch false kills
    assert all(e["scope_mismatch_false_kill"] is False
               for e in d["scope_conflict"])
    # the malformed cohort: no absence-as-contradiction
    for e in d["malformed"]:
        if e["case_id"] == "a2dev-20-empty-evidence-absence":
            assert e["absence_as_contradiction"] is False


# ---------- 4. the failed-ring attempts preserved ----------

def test_unorouter_attempt_typed_auth_failure():
    r = _load(R505 / "A2_V42_UNOROUTER" / "MEASUREMENT_RESULTS.json")
    raw = _load(R505 / "A2_V42_UNOROUTER" / "RAW" /
                "a2dev-01-cavitation-radical-bulk-kill.json")
    route = (((raw.get("attack") or {}).get("transport") or {})
             .get("provider_route") or [])
    assert any(x.get("failure_type") == "AUTH_FAILURE" for x in route)
    assert r["n_measured"] == 0


def test_apinex_attempt_typed_credit_exhausted():
    raw = _load(R505 / "A2_V42_APINEX" / "RAW" /
                "a2dev-01-cavitation-radical-bulk-kill.json")
    route = (((raw.get("attack") or {}).get("transport") or {})
             .get("provider_route") or [])
    assert any(x.get("failure_type") == "CREDIT_EXHAUSTED" for x in route)


# ---------- 5. BS-021: no raw credential values anywhere ----------

def test_no_raw_key_values_in_r505_artifacts():
    # BS-021: RAW credential values never enter any artifact — the
    # sha256:16 FINGERPRINT is the compliant identity form (LXXIII/
    # LXXVI: "names + fingerprints only") and may appear where custody
    # facts are described; the raw pb_live_ values are structurally
    # absent EVERYWHERE (records AND scripts).
    targets = list(R505.rglob("*.json")) + [
        REPO / "scripts" / "r505_patentbear_recovery.py",
        REPO / "scripts" / "r505_update_registry.py",
        REPO / "scripts" / "r505_a2_strong_ring.py",
    ]
    assert len(targets) >= 30
    for p in targets:
        text = p.read_text(errors="replace")
        # the raw key prefix is structurally absent everywhere
        assert text.count("pb_live_") == 0, \
            f"raw key prefix leaked into {p}"
        # and no credential-shaped secret appears in the RECORDS
        # (records carry fingerprints; real HF tokens are ~37 chars —
        # prose keys like hf_credits_and_elsevier are 23 and excluded
        # by the >30 threshold)
        if p.suffix == ".json":
            for token in text.split('"'):
                if token.startswith(("pb_live_", "ghp_", "hf_")) and \
                        len(token) > 30:
                    raise AssertionError(
                        f"credential-shaped token in {p}: {token[:8]}...")


# ---------- 6. the value-recovery record ----------

def test_value_recovery_record_pinned():
    r = _load(R505 / "PATENTBEAR_VALUE_RECOVERY.json")
    assert r["probe"]["state_typed"] == "AUTH_FAILED_401"
    assert r["probe"]["key_fingerprint"] == "561b6e70f5b5ea7f"
    assert r["active_key_not_probed"]["fingerprint"] == \
        "50fe7b3d569bb1fa"
    assert "1 remaining" in r["active_key_not_probed"]["measured_state"]
    assert "POOL_EXHAUSTED_MEASURED" in \
        r["pool_state_measured"]["conclusion"]
    # the full-battery arithmetic is carried with its verdict
    assert "8" in r["full_battery_arithmetic"]["needed_debits"]
    assert "AUTH_FAILED_401" in r["full_battery_arithmetic"]["verdict"]
    # the LXV escalation menu is present with opened_at + count
    menu = r["operator_decision_menu"]
    assert menu["opened_at"] == "R505"
    assert menu["escalation_count"] == 1
    assert len(menu["options"]) == 4
    # the CDN-UA lesson survives in the record (Art. XXXI)
    assert "Error 1010" in r["probe"]["first_attempt_disclosure"]
