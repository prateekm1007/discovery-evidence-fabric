"""R472 — the FOURTEEN-SLOT atria key ring + the keys-11..15 admission
+ the key-8 re-probe + the audit-response fixes this round ships.

Operator directive (2026-09-16 session 2, verbatim structure, values
redacted BS-021): fifteen keys supplied at the console URL — keys 1-10
identical to the R467-R470 registrations, keys 11-15 NEW this round.
The R472 probe measured (R472/PROBE_ATRIA_KEYS11TO15.json): keys 11-15
catalog 200 (sole model Atria-Dawn-Preview); ATRIA_API_KEY_8 re-probed
DETERMINISTIC 401 x3 (the R470 exclusion STANDS — the operator's
re-supply re-measured, never assumed); one 200 non-empty tiny
completion on key 11 (4.06 s, attempts=1); all fifteen pairwise
distinct; keys 1-10 identity-confirmed vs the R470 record.

These contracts pin:
  1. the R472 probe artifact's measured facts (fingerprints only);
  2. the FOURTEEN-slot registration (keys 11-15 appended in operator
     order; key 8 absent; slot numbers not compressed);
  3. the ring walk into the NEW tail (_10 -> _11 -> ... -> _15) and
     the tail-exhaustion reset;
  4. the key-8 re-probe honesty: the verdict is re-measured and the
     exclusion stands, recorded as such;
  5. the HF Space secret surface record (15/15 ring names PRESENT);
  6. the vault discipline: no key VALUE appears in any in-repo target.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
from discovery_fabric.engine import llm_registry as lr  # noqa: E402

PROBE = REPO / "R472" / "PROBE_ATRIA_KEYS11TO15.json"
PROBE_SCRIPT = REPO / "scripts" / "r472_probe_atria_keys11to15.py"
SECRETS_SCRIPT = REPO / "scripts" / "r472_hf_secrets_atria_ring15.py"
SURFACE = REPO / "R472" / "HF_SPACE_SECRETS_ATRIA_RING15.json"

RING = ["ATRIA_API_KEY", "ATRIA_API_KEY_2", "ATRIA_API_KEY_3",
        "ATRIA_API_KEY_4", "ATRIA_API_KEY_5", "ATRIA_API_KEY_6",
        "ATRIA_API_KEY_7", "ATRIA_API_KEY_9", "ATRIA_API_KEY_10",
        "ATRIA_API_KEY_11", "ATRIA_API_KEY_12", "ATRIA_API_KEY_13",
        "ATRIA_API_KEY_14", "ATRIA_API_KEY_15"]
NEW_SLOTS = ["ATRIA_API_KEY_11", "ATRIA_API_KEY_12", "ATRIA_API_KEY_13",
             "ATRIA_API_KEY_14", "ATRIA_API_KEY_15"]

# fake credential bodies — SHORT, non-matching to the BS-021 marker regex
K1 = "atr_local_k1"
K10, K11, K13, K15 = ("atr_local_k10", "atr_local_k11",
                      "atr_local_k13", "atr_local_k15")

BS021_TARGETS = [PROBE, PROBE_SCRIPT, SECRETS_SCRIPT, SURFACE,
                 REPO / "discovery_fabric/engine/llm_registry.py"]


# ---------------------------------------------------------------------------
# 1. the R472 probe artifact's measured facts
# ---------------------------------------------------------------------------

def _artifact() -> dict:
    assert PROBE.exists(), "R472/PROBE_ATRIA_KEYS11TO15.json missing"
    return json.loads(PROBE.read_text())


def test_probe_records_all_five_new_fingerprints():
    art = _artifact()
    fps = art["new_key_fingerprints"]
    assert set(fps) == set(NEW_SLOTS)
    # fingerprints, never values (BS-021)
    for v in fps.values():
        assert "..." in v and "(len 36)" in v


def test_probe_identity_continuity_and_distinctness():
    art = _artifact()
    ident = art["identity_checks"]
    assert ident["all_present_pairwise_distinct"] is True
    assert ident["n_present"] == 15
    assert ident["n_distinct"] == 15
    # keys 1-10 continuity vs the R470 record
    for name in RING[:9]:
        assert ident.get(f"{name}_same_as_r470") is True, name


def test_probe_new_keys_200_and_completion():
    art = _artifact()
    ring = art["ring_catalog_view"]
    for name in NEW_SLOTS:
        entry = next(r for r in ring if r["env_var"] == name)
        assert entry["status"] == 200, name
        assert entry["model_ids"] == ["Atria-Dawn-Preview"], name
    assert art["verdict"]["ring_size_measured"] == 14
    comp = next(p for p in art["probes"]
                if p["probe"] == "completion_new_key_sample")
    assert comp["env_var"] == "ATRIA_API_KEY_11"
    assert comp["status"] == 200 and comp["content_nonempty"] is True
    assert art["verdict"]["all_new_keys_valid"] is True


def test_probe_key8_reprobe_exclusion_stands():
    """The operator re-supplied key 8 in the same list — the verdict is
    RE-MEASURED (never carried forward, never assumed recovered), and
    the honest answer is recorded: still 401, exclusion stands."""
    art = _artifact()
    ring = art["ring_catalog_view"]
    k8 = next(r for r in ring if r["env_var"] == "ATRIA_API_KEY_8")
    assert k8["status"] == 401
    confirms = k8.get("non200_confirmations", [])
    assert [c["status"] for c in confirms] == [401, 401]
    verdict = art["key8_reprobe_verdict"]
    assert verdict["r472_verdict"].startswith("STILL non-200")
    assert verdict["r470_verdict"].startswith("deterministic 401")
    assert art["verdict"]["key8_revalidated"] is False


def test_probe_bogus_differential_control():
    art = _artifact()
    bogus = next(p for p in art["probes"]
                 if p["probe"] == "models_bogus_key")
    assert bogus["status"] in (401, 403)


# ---------------------------------------------------------------------------
# 2. the fourteen-slot registration
# ---------------------------------------------------------------------------

def test_ring_is_fourteen_slots_in_operator_order():
    spec = lr._SPEC_BY_ID["atria"]
    slots = lr.key_ring_slots(spec)
    assert slots == RING
    assert len(slots) == 14


def test_key8_still_not_registered_and_no_values_in_repo():
    spec = lr._SPEC_BY_ID["atria"]
    assert "ATRIA_API_KEY_8" not in lr.key_ring_slots(spec)
    # the vault discipline: no key VALUE appears in any in-repo target
    marker = re.compile(r"atr_[A-Za-z0-9_-]{20,}")
    for target in BS021_TARGETS:
        assert not marker.search(target.read_text()), str(target)


def test_registry_comment_records_the_r472_growth():
    src = (REPO / "discovery_fabric/engine/llm_registry.py").read_text()
    # the reconciled R472 record: both lines' probes, the flapping
    # disclosure, and the latest-verdict exclusion
    assert "R472 (2026-09-16, the PARALLEL-LINE RECONCILIATION" in src
    assert "FLAPPED" in src
    assert "CLEARED and REINSTATED" in src
    assert "current typed verdict is" in src
    assert "FOURTEEN-KEY ring" in src


# ---------------------------------------------------------------------------
# 3. the ring walk into the new tail
# ---------------------------------------------------------------------------

def _clear_all(monkeypatch):
    for v in RING:
        monkeypatch.delenv(v, raising=False)
    lr._reset_key_ring("atria")


def test_rotation_walks_the_new_tail(monkeypatch):
    """_10 (idx 8) -> _11 (idx 9) -> _13 (idx 11, _12 unset) -> _15
    (idx 13, _14 unset) -> exhausted -> reset to the first present."""
    _clear_all(monkeypatch)
    spec = lr._SPEC_BY_ID["atria"]
    monkeypatch.setenv("ATRIA_API_KEY_10", K10)
    monkeypatch.setenv("ATRIA_API_KEY_11", K11)
    monkeypatch.setenv("ATRIA_API_KEY_13", K13)
    monkeypatch.setenv("ATRIA_API_KEY_15", K15)
    assert lr.active_key_slot(spec) == 8
    assert lr.active_key_value(spec) == K10
    assert lr.rotate_key(spec) == 9               # -> _11
    assert lr.active_key_value(spec) == K11
    assert lr.rotate_key(spec) == 11              # skips _12 (unset)
    assert lr.active_key_value(spec) == K13
    assert lr.rotate_key(spec) == 13              # skips _14 (unset)
    assert lr.active_key_value(spec) == K15
    # exhausted from the tail: reset to first present, typed None
    assert lr.rotate_key(spec) is None
    assert lr.active_key_slot(spec) == 8


def test_new_tail_only_ring_walks_and_resets(monkeypatch):
    """A ring holding ONLY new-tail slots still walks them all."""
    _clear_all(monkeypatch)
    spec = lr._SPEC_BY_ID["atria"]
    monkeypatch.setenv("ATRIA_API_KEY_11", K11)
    monkeypatch.setenv("ATRIA_API_KEY_15", K15)
    assert lr.active_key_slot(spec) == 9
    assert lr.rotate_key(spec) == 13
    assert lr.rotate_key(spec) is None            # exhausted -> reset
    assert lr.active_key_slot(spec) == 9          # first PRESENT slot


def test_attempt_budget_extends_by_thirteen():
    spec = lr._SPEC_BY_ID["atria"]
    ring_extra = max(0, len(lr.key_ring_slots(spec)) - 1)
    assert ring_extra == 13


# ---------------------------------------------------------------------------
# 4. the probe script discipline (structure only)
# ---------------------------------------------------------------------------

def test_probe_script_uses_bogus_differential_and_reprobes():
    src = PROBE_SCRIPT.read_text()
    assert 'BOGUS = "atr_bogus differential key' in src
    assert "/v1/models" in src
    assert "def fp(val: str) -> str:" in src     # fingerprints only
    assert "DETERMINISTIC non-200" in src        # re-probe before typing
    assert "time.sleep(8)" in src
    # the key-8 re-probe is a first-class measurement, not an assumption
    assert "REPROBE_SLOTS" in src
    assert "key8_reprobe_verdict" in src


# ---------------------------------------------------------------------------
# 5. the HF Space secret surface record
# ---------------------------------------------------------------------------

def test_surface_record_fifteen_names_present():
    assert SURFACE.exists(), "R472/HF_SPACE_SECRETS_ATRIA_RING15.json missing"
    art = json.loads(SURFACE.read_text())
    ring_order = art["ring_order_declared"]
    assert len(ring_order) == 15
    assert ring_order[-5:] == NEW_SLOTS
    # all fifteen ring names verified PRESENT on the Space surface
    assert all(v == "PRESENT" for v in art["verified_names"].values())
    assert art["verified_summary"]["n_names_present"] == 15
    # the five new secrets were set this round (fingerprints only)
    for var in NEW_SLOTS:
        row = art["set_this_round"][var]
        assert row["set"] is True, var
        assert row["value"] == "<never recorded>"


def test_surface_record_discloses_key8_inert_carriage():
    art = json.loads(SURFACE.read_text())
    assert any("key 8" in n and "exclusion STANDS" in n
               for n in art.get("notes", []))


# ---------------------------------------------------------------------------
# 6. the secrets script discipline (structure only)
# ---------------------------------------------------------------------------

def test_secrets_script_never_records_values():
    src = SECRETS_SCRIPT.read_text()
    assert '"value": "<never recorded>"' in src
    assert "def fp(val: str) -> str:" in src
    # the R470-measured DIRECT secrets endpoint (dict keyed by name)
    assert "/api/spaces/" in src and "/secrets" in src
