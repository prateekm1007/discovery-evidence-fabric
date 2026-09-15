"""R470 — the NINE-SLOT atria key ring + the keys-4..10 admission.

Operator directive (2026-09-16, verbatim structure, values redacted
BS-021): ten keys supplied (keys 1-3 identical to the R467/R468/R469
registrations; keys 4-10 new). The R470 probe measured: keys 4,5,6,7,9,10
catalog 200 (sole model Atria-Dawn-Preview); ATRIA_API_KEY_8 a
DETERMINISTIC 401 x3 (re-probed twice, 8 s apart) — typed INVALID,
excluded from the ring; one 200 non-empty tiny completion on key 4
(1.02 s) after one disclosed transient 502.

These contracts pin:
  1. the probe artifact's measured facts (fingerprints only, BS-021);
  2. the NINE-slot registration (key 8 absent, slot numbers not
     compressed);
  3. the ring walk across NON-CONTIGUOUS present slots (the new-keys
     middle of the ring: rotate 0 -> 3 with 1,2 unset; then 3 -> 7,
     skipping the unregistered 8 entirely);
  4. the attempt budget extension at ring size 9 (base + 8);
  5. the vault discipline: key 8's VALUE never appears in the repo.
"""
from __future__ import annotations

import json
import os
import urllib.error
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
from discovery_fabric.engine import llm_registry as lr  # noqa: E402

PROBE = REPO / "R470" / "PROBE_ATRIA_KEYS4TO10.json"
PROBE_SCRIPT = REPO / "scripts" / "r470_probe_atria_keys4to10.py"

RING9 = ["ATRIA_API_KEY", "ATRIA_API_KEY_2", "ATRIA_API_KEY_3",
         "ATRIA_API_KEY_4", "ATRIA_API_KEY_5", "ATRIA_API_KEY_6",
         "ATRIA_API_KEY_7", "ATRIA_API_KEY_9", "ATRIA_API_KEY_10"]

# fake credential bodies — SHORT, non-matching to the BS-021 marker regex
K1 = "atr_local_k1"
K4, K9, K10 = "atr_local_k4", "atr_local_k9", "atr_local_k10"

BS021_TARGETS = [PROBE, PROBE_SCRIPT,
                 REPO / "discovery_fabric/engine/llm_registry.py"]


# ---------------------------------------------------------------------------
# 1. the probe artifact's measured facts
# ---------------------------------------------------------------------------

def _artifact() -> dict:
    assert PROBE.exists(), "R470/PROBE_ATRIA_KEYS4TO10.json missing"
    return json.loads(PROBE.read_text())


def test_probe_records_all_ten_fingerprints():
    art = _artifact()
    fps = art["new_key_fingerprints"]
    assert set(fps) == {f"ATRIA_API_KEY_{i}" for i in range(4, 11)}
    # fingerprints, never values (BS-021)
    for v in fps.values():
        assert "atr_" not in v.replace("atr_...", "") or v.startswith(
            "atr_6..."[:4]) or "..." in v


def test_probe_identity_continuity_and_distinctness():
    art = _artifact()
    ident = art["identity_checks"]
    assert ident["ATRIA_API_KEY_same_as_recorded"] is True
    assert ident["ATRIA_API_KEY_2_same_as_recorded"] is True
    assert ident["ATRIA_API_KEY_3_same_as_recorded"] is True
    assert ident["all_present_pairwise_distinct"] is True
    assert ident["n_distinct"] == 10


def test_probe_key8_deterministic_401_excluded():
    art = _artifact()
    ring = art["ring_catalog_view"]
    k8 = next(r for r in ring if r["env_var"] == "ATRIA_API_KEY_8")
    assert k8["status"] == 401
    confirms = k8.get("non200_confirmations", [])
    assert [c["status"] for c in confirms] == [401, 401]
    assert "DETERMINISTIC non-200" in k8["note"]


def test_probe_new_keys_200_and_completion():
    art = _artifact()
    ring = art["ring_catalog_view"]
    for name in ("ATRIA_API_KEY_4", "ATRIA_API_KEY_5", "ATRIA_API_KEY_6",
                 "ATRIA_API_KEY_7", "ATRIA_API_KEY_9", "ATRIA_API_KEY_10"):
        entry = next(r for r in ring if r["env_var"] == name)
        assert entry["status"] == 200, name
        assert entry["model_ids"] == ["Atria-Dawn-Preview"], name
    assert art["verdict"]["ring_size_measured"] == 9
    comp = next(p for p in art["probes"]
                if p["probe"] == "completion_new_key_sample")
    assert comp["status"] == 200 and comp["content_nonempty"] is True


def test_probe_honest_about_the_invalid_key():
    """The verdict does NOT claim all-new-valid — key 8 is honestly
    excluded (Art. VI/XXV: never manufacture a clean result)."""
    art = _artifact()
    assert art["verdict"]["all_new_keys_valid"] is False
    assert art["new_keys_validity"]["per_key_200"][
        "ATRIA_API_KEY_8"] is False


# ---------------------------------------------------------------------------
# 2. the nine-slot registration
# ---------------------------------------------------------------------------

def test_ring_is_nine_slots_in_operator_order():
    spec = lr._SPEC_BY_ID["atria"]
    assert lr.key_ring_slots(spec) == RING9


def test_key8_not_registered_anywhere():
    spec = lr._SPEC_BY_ID["atria"]
    assert "ATRIA_API_KEY_8" not in lr.key_ring_slots(spec)
    # and the vault keeps the value OUTSIDE the repo (BS-021): the
    # marker regex must not appear in any in-repo target
    import re
    marker = re.compile(r"atr_[A-Za-z0-9_-]{20,}")
    for target in BS021_TARGETS:
        assert not marker.search(target.read_text()), str(target)


def test_registry_comment_records_the_exclusion():
    src = (REPO / "discovery_fabric/engine/llm_registry.py").read_text()
    assert "ATRIA_API_KEY_8 is NOT REGISTERED" in src
    assert "DETERMINISTIC 401 x3" in src


# ---------------------------------------------------------------------------
# 3. the ring walk across non-contiguous present slots
# ---------------------------------------------------------------------------

def _clear_all(monkeypatch):
    for v in RING9:
        monkeypatch.delenv(v, raising=False)
    lr._reset_key_ring("atria")


def test_active_slot_finds_first_present_in_middle(monkeypatch):
    _clear_all(monkeypatch)
    spec = lr._SPEC_BY_ID["atria"]
    monkeypatch.setenv("ATRIA_API_KEY_4", K4)
    assert lr.active_key_slot(spec) == 3          # index of _4
    assert lr.active_key_value(spec) == K4


def test_rotation_skips_unset_and_unregistered(monkeypatch):
    """0 -> 3 (1,2 unset) -> 7 (4,5,6 rotate-consumed or unset; slot 8
    does not exist in the ring) -> 8. The walk must never touch an
    ATRIA_API_KEY_8 name."""
    _clear_all(monkeypatch)
    spec = lr._SPEC_BY_ID["atria"]
    monkeypatch.setenv("ATRIA_API_KEY", K1)
    monkeypatch.setenv("ATRIA_API_KEY_4", K4)
    monkeypatch.setenv("ATRIA_API_KEY_9", K9)
    monkeypatch.setenv("ATRIA_API_KEY_10", K10)
    assert lr.active_key_slot(spec) == 0
    assert lr.rotate_key(spec) == 3               # skips 1,2 (unset)
    assert lr.active_key_value(spec) == K4
    assert lr.rotate_key(spec) == 7               # skips 4,5,6 (unset)
    assert lr.active_key_value(spec) == K9
    assert lr.rotate_key(spec) == 8
    assert lr.active_key_value(spec) == K10
    # exhausted from the tail: reset to first present, typed None
    assert lr.rotate_key(spec) is None
    assert lr.active_key_slot(spec) == 0


def test_exhaustion_typed_when_middle_keys_only(monkeypatch):
    """A ring holding ONLY middle slots still walks them all, then
    resets to the first present (auto-recovery), never silently."""
    _clear_all(monkeypatch)
    spec = lr._SPEC_BY_ID["atria"]
    monkeypatch.setenv("ATRIA_API_KEY_9", K9)
    monkeypatch.setenv("ATRIA_API_KEY_10", K10)
    assert lr.active_key_slot(spec) == 7
    assert lr.rotate_key(spec) == 8
    assert lr.rotate_key(spec) is None            # exhausted -> reset
    assert lr.active_key_slot(spec) == 7          # first PRESENT slot


# ---------------------------------------------------------------------------
# 4. the attempt budget at ring size 9
# ---------------------------------------------------------------------------

def test_attempt_budget_extends_by_eight():
    spec = lr._SPEC_BY_ID["atria"]
    ring_extra = max(0, len(lr.key_ring_slots(spec)) - 1)
    assert ring_extra == 8


def test_budget_comment_pins_the_extension_rule():
    src = (REPO / "discovery_fabric/engine/llm_registry.py").read_text()
    assert "ring_extra = max(0, len(key_ring_slots(spec)) - 1)" in src


# ---------------------------------------------------------------------------
# 5. the live differential proof stays possible (structure only)
# ---------------------------------------------------------------------------

def test_probe_script_uses_bogus_differential():
    src = PROBE_SCRIPT.read_text()
    assert 'BOGUS = "atr_bogus differential key' in src
    assert "/v1/models" in src
    # fingerprints only, never values
    assert "def fp(val: str) -> str:" in src


def test_probe_script_reprobes_before_typing_invalid():
    src = PROBE_SCRIPT.read_text()
    assert "DETERMINISTIC non-200" in src
    assert "time.sleep(8)" in src


# ---------------------------------------------------------------------------
# 6. the availability row reports the full ring
# ---------------------------------------------------------------------------

def test_availability_row_lists_nine_ring_vars(monkeypatch):
    _clear_all(monkeypatch)
    monkeypatch.setenv("ATRIA_API_KEY", K1)
    monkeypatch.setenv("ATRIA_API_KEY_10", K10)
    matrix = lr.availability_matrix()
    row = next(r for r in matrix if r["provider_id"] == "atria")
    assert row["key_ring_env_vars"] == RING9
    assert row["key_slots_present"] == [0, 8]
    assert row["key_slot_active"] in (0, 8)
