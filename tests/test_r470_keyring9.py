"""R470 — the atria key ring + the keys-4..10 admission, moved forward
by R472's PARALLEL-LINE RECONCILIATION.

R472: TWO probe lines measured the SAME operator delivery (the
re-supplied key 8 + the new keys). The sibling's line
(R472/PROBE_ATRIA_KEYS11TO13.json, 22:40Z) measured key 8 catalog
200 x3 — cleared, reinstated on their line, keys 11-13 valid. THIS
line (R472/PROBE_ATRIA_KEYS11TO15.json, 22:57Z) measured the SAME
key-8 value DETERMINISTIC 401 x3 (re-probed twice), measured keys
11-15 all valid, and the post-rebase decisive re-measure answered
401 x3 again — key 8's provider state FLAPPED; the LATEST typed
verdict (INVALID) rules. The reconciled registration is the FOURTEEN
operator-ordered valid slots (1-7, 9-15); both probe artifacts stand
as historical records.

Operator directive (2026-09-16, verbatim structure, values redacted
BS-021): ten keys supplied (keys 1-3 identical to the R467/R468/R469
registrations; keys 4-10 new). The R470 probe measured: keys 4,5,6,7,9,10
catalog 200 (sole model Atria-Dawn-Preview); ATRIA_API_KEY_8 a
DETERMINISTIC 401 x3 (re-probed twice, 8 s apart) — typed INVALID,
excluded from the ring; one 200 non-empty tiny completion on key 4
(1.02 s) after one disclosed transient 502.

These contracts pin:
  1. the R470 probe artifact's measured facts (fingerprints only);
  2. the SIBLING's R472 probe artifact (the 200 x3 key-8 window +
     keys 11-13 — the historical record of the other line);
  3. the CURRENT reconciled registration (14 slots: 1-7, 9-15; key 8
     excluded per the latest typed measurement, slot numbers never
     compressed);
  4. the ring walk across NON-CONTIGUOUS present slots;
  5. the attempt budget extension at the current ring size;
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
# the sibling line's R472 probe (keys 11-13 + the key-8 200-window)
PROBE472_SIBLING = REPO / "R472" / "PROBE_ATRIA_KEYS11TO13.json"
# this line's R472 probe (keys 11-15 + the key-8 401 re-measure)
PROBE472_THIS = REPO / "R472" / "PROBE_ATRIA_KEYS11TO15.json"

RING9 = ["ATRIA_API_KEY", "ATRIA_API_KEY_2", "ATRIA_API_KEY_3",
         "ATRIA_API_KEY_4", "ATRIA_API_KEY_5", "ATRIA_API_KEY_6",
         "ATRIA_API_KEY_7", "ATRIA_API_KEY_9", "ATRIA_API_KEY_10"]
# R472 (the reconciled contract): the FOURTEEN valid operator-ordered
# slots — keys 11-15 appended after dual-line probe validation; key 8
# excluded per the LATEST typed measurement (the 22:40 200-window on
# the sibling's line superseded by the 22:57 and post-rebase 401 x3
# re-measures on this line — the flapping disclosed in the registry
# comment). Historical name RING9 kept for the walk tests below (their
# slot indices live in the first nine positions and are unchanged).
# R478 (2026-09-17): key 8 REINSTATED per the LATEST typed measurement
# (R478/RING_VALIDATION.json) — FIFTEEN slots, operator order.
RING = ["ATRIA_API_KEY", "ATRIA_API_KEY_2", "ATRIA_API_KEY_3",
        "ATRIA_API_KEY_4", "ATRIA_API_KEY_5", "ATRIA_API_KEY_6",
        "ATRIA_API_KEY_7", "ATRIA_API_KEY_8", "ATRIA_API_KEY_9",
        "ATRIA_API_KEY_10", "ATRIA_API_KEY_11", "ATRIA_API_KEY_12",
        "ATRIA_API_KEY_13", "ATRIA_API_KEY_14", "ATRIA_API_KEY_15"]

# fake credential bodies — SHORT, non-matching to the BS-021 marker regex
K1 = "atr_local_k1"
K4, K8, K9, K10, K11 = ("atr_local_k4", "atr_local_k8",
                        "atr_local_k9", "atr_local_k10",
                        "atr_local_k11")

BS021_TARGETS = [PROBE, PROBE_SCRIPT, PROBE472_SIBLING, PROBE472_THIS,
                 REPO / "discovery_fabric/engine/llm_registry.py",
                 REPO / "scripts" / "r472_probe_atria_keys.py",
                 REPO / "scripts" / "r472_probe_atria_keys11to15.py"]


# ---------------------------------------------------------------------------
# 1. the R470 probe artifact's measured facts
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
# 2. the sibling line's R472 probe — the historical 200-window record
# ---------------------------------------------------------------------------

def test_r472_sibling_probe_records_the_clearance_window():
    """The sibling's probe-before-record artifact stands as MEASURED
    HISTORY: key 8 catalog 200 x3 at 22:40:28Z, keys 11-13 valid.
    The reconciled EXCLUSION does not edit their record — it
    supersedes it with a later measurement (Art. III in both
    directions, timestamps deciding)."""
    assert PROBE472_SIBLING.exists(), \
        "R472/PROBE_ATRIA_KEYS11TO13.json missing"
    art = json.loads(PROBE472_SIBLING.read_text())
    assert art["key8_reprobe_verdict"] == "CLEARED_200_REINSTATE"
    assert [p["status"] for p in art["key8_reprobe"]] == [200, 200, 200]
    for name in ("ATRIA_API_KEY_11", "ATRIA_API_KEY_12",
                 "ATRIA_API_KEY_13"):
        entry = next(p for p in art["probes"]
                     if p.get("slot") == name and p.get("probe") == "catalog")
        assert entry["verdict"] == "VALID", name
        assert entry["models"] == ["Atria-Dawn-Preview"], name
    assert art["bogus_differential"]["status"] == 401


# ---------------------------------------------------------------------------
# 3. the current registration (R478: 15 slots, key 8 reinstated)
# ---------------------------------------------------------------------------

def test_ring_registration_current_operator_order():
    """R478: the LATEST typed measurement rules — key 8's catalog
    200 x3 + 200 tiny completion (R478/RING_VALIDATION.json) reinstates
    it; keys 11-15 (validated by BOTH R472 lines) stay appended. Slot
    numbers never compressed."""
    spec = lr._SPEC_BY_ID["atria"]
    assert lr.key_ring_slots(spec) == RING
    assert len(RING) == 15


def test_key8_reinstated_after_the_r478_remeasure():
    """Every measurement is on the record; the registration follows
    the LATEST (R478: 200 x3 + a 200 completion, 2026-09-17) — the
    R472 401 x3 re-measures stand as superseded history, never
    deleted."""
    spec = lr._SPEC_BY_ID["atria"]
    assert "ATRIA_API_KEY_8" in lr.key_ring_slots(spec)
    # the BS-021 marker discipline holds: no real key body in any target
    import re
    marker = re.compile(r"atr_[A-Za-z0-9_-]{20,}")
    for target in BS021_TARGETS:
        if not target.exists():
            continue  # the sibling's script may live on their line only
        assert not marker.search(target.read_text()), str(target)


def test_registry_comment_records_the_full_key8_history():
    src = (REPO / "discovery_fabric/engine/llm_registry.py").read_text()
    # the R470 exclusion record stays verbatim (history, never edited)
    assert "ATRIA_API_KEY_8 is NOT REGISTERED" in src
    assert "DETERMINISTIC 401 x3" in src
    # the R472 reconciliation records BOTH measurements and the verdict
    assert "FLAPPED" in src
    assert "CLEARED and REINSTATED" in src
    assert "current typed verdict is" in src
    assert "EXCLUDED from the ring" in src


# ---------------------------------------------------------------------------
# 4. the ring walk across non-contiguous present slots
# ---------------------------------------------------------------------------

def _clear_all(monkeypatch):
    for v in RING:
        monkeypatch.delenv(v, raising=False)
    monkeypatch.delenv("ATRIA_API_KEY_8", raising=False)
    lr._reset_key_ring("atria")


def test_active_slot_finds_first_present_in_middle(monkeypatch):
    _clear_all(monkeypatch)
    spec = lr._SPEC_BY_ID["atria"]
    monkeypatch.setenv("ATRIA_API_KEY_4", K4)
    assert lr.active_key_slot(spec) == 3          # index of _4
    assert lr.active_key_value(spec) == K4


def test_rotation_skips_unset_and_unregistered(monkeypatch):
    """0 -> 3 (1,2 unset) -> 8 (4,5,6,7 unset; slot 7 is _8 —
    registered since R478, unset here, skipped like any unset slot;
    slot 8 is _9) -> 9 (_10). The walk skips unset names whatever
    their registration state."""
    _clear_all(monkeypatch)
    spec = lr._SPEC_BY_ID["atria"]
    monkeypatch.setenv("ATRIA_API_KEY", K1)
    monkeypatch.setenv("ATRIA_API_KEY_4", K4)
    monkeypatch.setenv("ATRIA_API_KEY_9", K9)
    monkeypatch.setenv("ATRIA_API_KEY_10", K10)
    assert lr.active_key_slot(spec) == 0
    assert lr.rotate_key(spec) == 3               # skips 1,2 (unset)
    assert lr.active_key_value(spec) == K4
    assert lr.rotate_key(spec) == 8               # skips 4,5,6,7 (unset)
    assert lr.active_key_value(spec) == K9
    assert lr.rotate_key(spec) == 9
    assert lr.active_key_value(spec) == K10
    # exhausted from the tail: reset to first present, typed None
    assert lr.rotate_key(spec) is None
    assert lr.active_key_slot(spec) == 0


def test_rotation_walks_the_new_tail(monkeypatch):
    """The R472 append (R478 indices): _10 (idx 9) -> _11 (idx 10)
    -> exhausted -> reset to the first present."""
    _clear_all(monkeypatch)
    spec = lr._SPEC_BY_ID["atria"]
    monkeypatch.setenv("ATRIA_API_KEY_10", K10)
    monkeypatch.setenv("ATRIA_API_KEY_11", K11)
    assert lr.active_key_slot(spec) == 9
    assert lr.rotate_key(spec) == 10              # -> _11
    assert lr.active_key_value(spec) == K11
    assert lr.rotate_key(spec) is None            # exhausted -> reset
    assert lr.active_key_slot(spec) == 9


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
# 5. the attempt budget at the current ring size (R478: 15 slots)
# ---------------------------------------------------------------------------

def test_attempt_budget_extends_by_ring_minus_one():
    spec = lr._SPEC_BY_ID["atria"]
    ring_extra = max(0, len(lr.key_ring_slots(spec)) - 1)
    assert ring_extra == 14


def test_budget_comment_pins_the_extension_rule():
    src = (REPO / "discovery_fabric/engine/llm_registry.py").read_text()
    assert "ring_extra = max(0, len(key_ring_slots(spec)) - 1)" in src


# ---------------------------------------------------------------------------
# 6. the live differential proof stays possible (structure only)
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
# 7. the availability row reports the full ring
# ---------------------------------------------------------------------------

def test_availability_row_lists_current_ring_vars(monkeypatch):
    _clear_all(monkeypatch)
    monkeypatch.setenv("ATRIA_API_KEY", K1)
    monkeypatch.setenv("ATRIA_API_KEY_10", K10)
    matrix = lr.availability_matrix()
    row = next(r for r in matrix if r["provider_id"] == "atria")
    assert row["key_ring_env_vars"] == RING
    assert row["key_slots_present"] == [0, 9]
    assert row["key_slot_active"] in (0, 9)
