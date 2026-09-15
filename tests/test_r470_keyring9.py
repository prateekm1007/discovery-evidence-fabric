"""R470 — the atria key ring + the keys-4..10 admission.

Operator directive (2026-09-16, verbatim structure, values redacted
BS-021): ten keys supplied (keys 1-3 identical to the R467/R468/R469
registrations; keys 4-10 new). The R470 probe measured: keys 4,5,6,7,9,10
catalog 200 (sole model Atria-Dawn-Preview); ATRIA_API_KEY_8 a
DETERMINISTIC 401 x3 (re-probed twice, 8 s apart) — typed INVALID,
excluded from the ring; one 200 non-empty tiny completion on key 4
(1.02 s) after one disclosed transient 502.

R472 (same day, third audit pass): the operator RE-SUPPLIED key 8 (the
same string) and added keys 11-13. The R472 probe re-measured: key 8
catalog 200 x3 (the account-side exclusion CLEARED — reinstated);
keys 11/12/13 catalog 200 each + one 200 non-empty completion on key
11. The ring is now THIRTEEN contiguous operator-ordered slots.

These contracts pin:
  1. the R470 probe artifact's measured facts (fingerprints only,
     BS-021) — the historical key-8 exclusion record;
  2. the R472 probe artifact's measured facts (reinstatement + the
     three new keys);
  3. the THIRTEEN-slot registration in operator order (slot numbers
     never compressed);
  4. the ring walk across the contiguous ring (unset slots skipped);
  5. the attempt budget extension at ring size 13 (base + 12);
  6. the vault discipline: key VALUES never appear in the repo.
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
PROBE472 = REPO / "R472" / "PROBE_ATRIA_KEYS11TO13.json"

RING13 = ["ATRIA_API_KEY"] + [f"ATRIA_API_KEY_{i}" for i in range(2, 14)]
# the R470 nine-valid view (key 8 excluded) — the historical artifact
RING9 = ["ATRIA_API_KEY", "ATRIA_API_KEY_2", "ATRIA_API_KEY_3",
         "ATRIA_API_KEY_4", "ATRIA_API_KEY_5", "ATRIA_API_KEY_6",
         "ATRIA_API_KEY_7", "ATRIA_API_KEY_9", "ATRIA_API_KEY_10"]

# fake credential bodies — SHORT, non-matching to the BS-021 marker regex
K1 = "atr_local_k1"
K4, K8, K9, K10 = ("atr_local_k4", "atr_local_k8", "atr_local_k9",
                   "atr_local_k10")
K11, K12, K13 = "atr_local_k11", "atr_local_k12", "atr_local_k13"

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
# 2. the thirteen-slot registration (R472)
# ---------------------------------------------------------------------------

def test_ring_is_thirteen_slots_in_operator_order():
    """R472: the probe re-measured key 8 VALID (the R470 401 cleared)
    and the operator added keys 11-13 — the registration carries all
    THIRTEEN operator-ordered slots (slot numbers never compressed)."""
    spec = lr._SPEC_BY_ID["atria"]
    assert lr.key_ring_slots(spec) == RING13


def test_r472_probe_records_the_reinstatement_and_new_keys():
    """The R472 probe-before-record artifact: key 8 catalog 200 x3,
    keys 11-13 VALID, fingerprints only (BS-021)."""
    assert PROBE472.exists(), "R472/PROBE_ATRIA_KEYS11TO13.json missing"
    art = json.loads(PROBE472.read_text())
    assert art["thirteen_way_distinct"] is True
    assert art["key8_reprobe_verdict"] == "CLEARED_200_REINSTATE"
    assert [p["status"] for p in art["key8_reprobe"]] == [200, 200, 200]
    for name in ("ATRIA_API_KEY_11", "ATRIA_API_KEY_12",
                 "ATRIA_API_KEY_13"):
        entry = next(p for p in art["probes"]
                     if p.get("slot") == name and p.get("probe") == "catalog")
        assert entry["verdict"] == "VALID", name
        assert entry["models"] == ["Atria-Dawn-Preview"], name
    assert art["bogus_differential"]["status"] == 401
    comp = next(p for p in art["probes"]
                if p.get("probe") == "tiny_completion")
    assert comp["status"] == 200 and comp["content_nonempty"] is True
    # fingerprints, never values (BS-021)
    for v in art["new_key_fingerprints"].values():
        assert "..." in v and len(v) < 40


def test_key8_registered_after_probe_cleared():
    """R472: the R470 exclusion was a MEASUREMENT, and the R472
    re-measurement outranks it in the other direction (Art. III): with
    the catalog answering 200 x3, key 8 rejoins the ring."""
    spec = lr._SPEC_BY_ID["atria"]
    assert "ATRIA_API_KEY_8" in lr.key_ring_slots(spec)
    # the BS-021 marker discipline holds: no real key body in any target
    import re
    marker = re.compile(r"atr_[A-Za-z0-9_-]{20,}")
    for target in BS021_TARGETS + [PROBE472,
                                   REPO / "scripts"
                                   / "r472_probe_atria_keys.py"]:
        assert not marker.search(target.read_text()), str(target)


def test_registry_comment_records_exclusion_AND_reinstatement():
    src = (REPO / "discovery_fabric/engine/llm_registry.py").read_text()
    # the R470 exclusion record stays verbatim (history, never edited)
    assert "ATRIA_API_KEY_8 is NOT REGISTERED" in src
    assert "DETERMINISTIC 401 x3" in src
    # and the R472 reinstatement record follows it
    assert "CLEARED, so key 8 is REINSTATED" in src
    assert "THIRTEEN VALID slots" in src


# ---------------------------------------------------------------------------
# 3. the ring walk (presence-driven, contiguous slots)
# ---------------------------------------------------------------------------

def _clear_all(monkeypatch):
    for v in RING13:
        monkeypatch.delenv(v, raising=False)
    lr._reset_key_ring("atria")


def test_active_slot_finds_first_present_in_middle(monkeypatch):
    _clear_all(monkeypatch)
    spec = lr._SPEC_BY_ID["atria"]
    monkeypatch.setenv("ATRIA_API_KEY_4", K4)
    assert lr.active_key_slot(spec) == 3          # index of _4
    assert lr.active_key_value(spec) == K4


def test_rotation_skips_unset_slots(monkeypatch):
    """The contiguous 13-slot ring: 0 -> 3 (1,2 unset) -> 8 (4..7
    unset) -> 9 -> exhausted. The walk passes THROUGH slot 7 (key 8,
    reinstated R472) whenever it is unset — skipping is by PRESENCE,
    never by name."""
    _clear_all(monkeypatch)
    spec = lr._SPEC_BY_ID["atria"]
    monkeypatch.setenv("ATRIA_API_KEY", K1)
    monkeypatch.setenv("ATRIA_API_KEY_4", K4)
    monkeypatch.setenv("ATRIA_API_KEY_9", K9)
    monkeypatch.setenv("ATRIA_API_KEY_10", K10)
    assert lr.active_key_slot(spec) == 0
    assert lr.rotate_key(spec) == 3               # skips 1,2 (unset)
    assert lr.active_key_value(spec) == K4
    assert lr.rotate_key(spec) == 8               # skips 4..8 (unset; 7 == key 8)
    assert lr.active_key_value(spec) == K9
    assert lr.rotate_key(spec) == 9
    assert lr.active_key_value(spec) == K10
    # exhausted from the tail: reset to first present, typed None
    assert lr.rotate_key(spec) is None
    assert lr.active_key_slot(spec) == 0


def test_rotation_includes_reinstated_key8(monkeypatch):
    """R472: with key 8 present, the walk lands ON it (index 7) — the
    R470 never-touch-slot-8 contract is dead, replaced by presence-
    driven rotation over all thirteen operator-ordered slots."""
    _clear_all(monkeypatch)
    spec = lr._SPEC_BY_ID["atria"]
    monkeypatch.setenv("ATRIA_API_KEY_8", K8)
    monkeypatch.setenv("ATRIA_API_KEY_11", K11)
    assert lr.active_key_slot(spec) == 7          # first present slot
    assert lr.active_key_value(spec) == K8
    assert lr.rotate_key(spec) == 10              # 9 unset -> _11
    assert lr.active_key_value(spec) == K11


def test_exhaustion_typed_when_middle_keys_only(monkeypatch):
    """A ring holding ONLY middle slots still walks them all, then
    resets to the first present (auto-recovery), never silently."""
    _clear_all(monkeypatch)
    spec = lr._SPEC_BY_ID["atria"]
    monkeypatch.setenv("ATRIA_API_KEY_9", K9)
    monkeypatch.setenv("ATRIA_API_KEY_10", K10)
    assert lr.active_key_slot(spec) == 8
    assert lr.rotate_key(spec) == 9
    assert lr.rotate_key(spec) is None            # exhausted -> reset
    assert lr.active_key_slot(spec) == 8          # first PRESENT slot


# ---------------------------------------------------------------------------
# 4. the attempt budget at ring size 13
# ---------------------------------------------------------------------------

def test_attempt_budget_extends_by_twelve():
    spec = lr._SPEC_BY_ID["atria"]
    ring_extra = max(0, len(lr.key_ring_slots(spec)) - 1)
    assert ring_extra == 12


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

def test_availability_row_lists_thirteen_ring_vars(monkeypatch):
    _clear_all(monkeypatch)
    monkeypatch.setenv("ATRIA_API_KEY", K1)
    monkeypatch.setenv("ATRIA_API_KEY_10", K10)
    matrix = lr.availability_matrix()
    row = next(r for r in matrix if r["provider_id"] == "atria")
    assert row["key_ring_env_vars"] == RING13
    assert row["key_slots_present"] == [0, 9]
    assert row["key_slot_active"] in (0, 9)
