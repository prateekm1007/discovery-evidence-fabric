"""tests/test_r390_reality_loop.py — adversarial tests for the R390
reality-loop closure (CEO directive #6: CLOSE THE ACTUAL REALITY LOOP).

Constitutional anchors exercised:
- Art. XVII/XXX: every control is attacked, not just exercised.
- Art. XXXVIII: MEASURED has ONE door; rehearsal can never flip state.
- Art. IX: canonical production state stays byte-identical.
- Art. VI: raw-byte custody (hash of the fetched bytes pins the event).
- Art. II: exact row binding (phase/parse refusals).
- Art. XXV: within-uncertainty observations change nothing.

All tests are hermetic: ledger_path redirects + the conftest autouse
guard. No network. The canonical portfolio and the canonical R370G
ledgers are hash-checked before/after the whole module (see the last
test) — the e11 contamination class is structurally closed.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine import reality_loop  # noqa: E402
from discovery_fabric.engine import reality_provider  # noqa: E402

CANON_LEDGERS = [
    REPO / "premium_package_factory" / "output" / "reality_loop" /
    "REALITY_EVENT_LEDGER.jsonl",
    REPO / "premium_package_factory" / "output" / "reality_loop" /
    "CAUSAL_MUTATION_LEDGER.jsonl",
]

FIXTURE_TSV = (
    b"Temperature (K)\tPressure (kPa)\tDensity (mol/l)\tVolume (l/mol)\t"
    b"Internal Energy (J/mol)\tEnthalpy (J/mol)\tEntropy (J/mol*K)\t"
    b"Cv (J/mol*K)\tCp (J/mol*K)\tSound Spd. (m/s)\tJoule-Thomson "
    b"(K/MPa)\tViscosity (uPa*s)\tTherm. Cond. (W/m*K)\tPhase\n"
    b"310.1500\t101.3250\t55.13822\t0.01813624\t2791.940\t2793.778\t"
    b"9.586539\t73.62747\t75.29020\t1523.658\t-0.2138357\t691.3036\t"
    b"0.6244750\tliquid\n")

PORTFOLIO_ROOT = REPO.parent / "portfolio"


def _file_hash(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() \
        else "ABSENT"


def _ledger_hashes() -> dict:
    return {str(p): _file_hash(p) for p in CANON_LEDGERS}


def _fixture_observation(tmp_path, rehearsal=True, eta=None,
                         tsv=FIXTURE_TSV):
    ledger = tmp_path / "REALITY_EVENT_LEDGER.jsonl"
    obs = reality_loop.acquire_nist_water_viscosity(
        tmp_path / "observation", package_id="P-07",
        ledger_path=ledger, rehearsal=rehearsal,
        http_get=lambda url: tsv)
    if eta is not None:
        obs["value_mPa_s"] = eta
    return obs, ledger


# ---------------------------------------------------------------------------
# A. The happy-path machinery (positive cases — Art. V second half)
# ---------------------------------------------------------------------------

def test_rehearsal_closes_loop_without_flipping_state(tmp_path):
    obs, ledger = _fixture_observation(tmp_path)
    record = reality_loop.close_reality_loop(
        "04", obs, portfolio_root=PORTFOLIO_ROOT,
        out_root=tmp_path / "out", ledger_path=ledger)
    assert record["status"] == "LOOP_CLOSED"
    assert record["observation_origin"] == "RECONSTRUCTED"
    # the decision-change proof the CEO demanded
    proof = record["re_evaluation"]["decision_change_proof"]
    assert proof["answer"] is True
    assert "floor_lumen_diameter_mm = 0.6" in proof["decision_before"]
    assert "0.5471" in proof["decision_after"]
    # conductance restoration (computed independently in the next test)
    assert record["re_evaluation"]["conductance_restored_ratio"] == \
        pytest.approx(1.0, abs=1e-3)
    # rehearsal NEVER flips loop state (Art. XXXVII/XXXVIII)
    assert record["loop_verification_state"] == "UNTOUCHED"
    assert record["causal_chain"]["synthetic"] is True
    assert record["causal_chain"]["recorded_in_canonical_ledger"] is False
    # canonical bytes never touched
    assert record["mutation"]["applied_to_canonical_package"] is False


def test_conductance_math_pinned_by_hand_computation():
    """Art. II: the pinned value is hand-derived, not self-referential.
    G = pi*d^4/(128*eta*L); d=0.6mm, eta=1.0 mPa*s, L=100mm
      = 3.178e-11 m^3/(s*Pa).

    R405 CORRECTION: the pre-R405 pin (1.4315e-5 mL/(min*mmHg)) and its
    "hand computation" BOTH divided by 133.322 — the test re-derived
    with the code's own unit convention, so it verified nothing about
    the conversion direction (Art. XXXI lesson: a hand computation that
    repeats the implementation's convention is not independent
    verification). The independent derivation below derives the flow
    at a known pressure through PURE SI and converts once, so a
    direction error cannot cancel: at dP = 1333.22 Pa (= 10 mmHg),
    Q = G*Pa -> m^3/s -> mL/min; G = Q/10.
    """
    g = reality_loop._conductance_ml_per_min_mmhg(0.6, 1.0, 100.0)
    d_m, eta, L = 0.6e-3, 1.0e-3, 100.0e-3
    # independent path: flow at 10 mmHg expressed in Pa, converted to
    # mL/min once, then divided by 10 mmHg
    q_m3_s = (math.pi * d_m ** 4 / (128.0 * eta * L)) * 1333.22
    q_ml_min = q_m3_s * 1e6 * 60.0
    expected = q_ml_min / 10.0
    assert g == pytest.approx(expected, rel=1e-12)
    assert g == pytest.approx(0.2544473751, rel=1e-9)
    # ADVERSARIAL MAGNITUDE GUARD (Art. XVII): a 0.6 mm ID x 100 mm
    # water column passes mL/min at mmHg heads — a unit-direction bug
    # (pre-R405: 1.43e-5) is 4-5 orders below physical reality and must
    # fail this bound
    assert 0.05 <= g <= 5.0, (
        f"conductance {g} mL/(min*mmHg) outside the physical magnitude "
        "band for a 0.6 mm x 100 mm water column — unit conversion "
        "defect (R405 disclosure)")
    # the +44.65% over-drainage discrepancy at the measured viscosity
    # (ratio: unaffected by the R405 correction — constants cancel)
    g2 = reality_loop._conductance_ml_per_min_mmhg(0.6, 0.6913036, 100.0)
    assert g2 / g == pytest.approx(1.0 / 0.6913036, rel=1e-9)
    assert g2 == pytest.approx(0.3680689281, rel=1e-6)
    # pre-R405 recorded values were 133.322^2 = 17,774.7x too small
    assert g / 1.4315098311274948e-05 == pytest.approx(
        133.322 ** 2, rel=1e-6)


def test_compensation_restores_declared_conductance():
    rule = reality_loop.CAUSAL_RULES["viscosity"]
    d_new = rule["compensation_fn"](0.6, 0.6913036 / 1.0)
    g_before = reality_loop._conductance_ml_per_min_mmhg(0.6, 1.0, 100.0)
    g_after = reality_loop._conductance_ml_per_min_mmhg(
        d_new, 0.6913036, 100.0)
    assert g_after / g_before == pytest.approx(1.0, rel=1e-6)


# ---------------------------------------------------------------------------
# B. The REALITY BOUNDARY attacks (Art. XVII: attempt the bypass)
# ---------------------------------------------------------------------------

def test_attack_measured_smuggling_via_direct_add():
    """A provider-grade datum with MEASURED origin cannot be added
    directly — the one door is add_measured with R370G validation."""
    model = reality_provider.RealityModel(package_id="P-07")
    with pytest.raises(ValueError, match="REALITY BOUNDARY VIOLATION"):
        model.add("measurements", reality_provider.RealityDatum(
            name="smuggled", value=0.69,
            origin=reality_provider.EvidenceOrigin.MEASURED))


def test_attack_rehearsal_event_cannot_supply_measured(tmp_path):
    """A CONTROLLED_REHEARSAL event is refused by add_measured — the
    MEASURED door rejects synthetic events (R370G rule, re-verified)."""
    obs, ledger = _fixture_observation(tmp_path, rehearsal=True)
    model = reality_provider.RealityModel(package_id="P-07")
    adm = model.add_measured(
        "measurements", "x", 0.69, obs["event_id"], ledger_path=ledger)
    assert adm["admitted"] is False
    assert any("CONTROLLED_REHEARSAL" in e or "not found" in e.lower()
               for e in adm["errors"])


def test_attack_unknown_event_id_cannot_supply_measured(tmp_path):
    """An event id that does not exist anywhere is INVALID — never
    silently accepted (Art. IV: no fallback path)."""
    model = reality_provider.RealityModel(package_id="P-07")
    adm = model.add_measured(
        "measurements", "x", 0.69, "EVT-DOES-NOT-EXIST",
        ledger_path=tmp_path / "nothing.jsonl")
    assert adm["admitted"] is False


def test_attack_fake_event_fails_frozen_gate(tmp_path):
    """An event missing attestation/custody cannot be recorded — the
    R370G gate raises, the acquisition refuses (Art. VI)."""
    bad = reality_loop.acquire_nist_water_viscosity(
        tmp_path / "bad", package_id="P-07",
        ledger_path=tmp_path / "bad_ledger.jsonl",
        http_get=lambda url: FIXTURE_TSV)
    # strip the attestation -> gate must reject on record
    import importlib.util
    p = REPO / "premium_package_factory" / "gates" / \
        "r370g_reality_event_schema.py"
    spec = importlib.util.spec_from_file_location("atk_r370g", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    stripped = dict(bad["event"])
    stripped.pop("attestation")
    with pytest.raises(ValueError):
        mod.record_reality_event(stripped)


# ---------------------------------------------------------------------------
# C. Decision-discipline attacks (Art. XXV/XXVII)
# ---------------------------------------------------------------------------

def test_within_uncertainty_observation_changes_nothing(tmp_path):
    """An observation INSIDE the design's declared +/-20% band must NOT
    change any decision — no mutation is justified (Art. XXVII: the
    design's own declared band is the threshold)."""
    obs, ledger = _fixture_observation(tmp_path, eta=0.9)  # -10%, inside
    record = reality_loop.close_reality_loop(
        "04", obs, portfolio_root=PORTFOLIO_ROOT,
        out_root=tmp_path / "out", ledger_path=ledger)
    assert record["status"] == "NO_DECISION_CHANGE"
    assert "mutation" not in record
    assert record["comparison"]["status"] == "WITHIN_UNCERTAINTY"


def test_out_of_envelope_compensation_refuses_rebuild(tmp_path):
    """If the compensating value falls outside the declared envelope,
    the loop REFUSES (never clamps silently — R389 Phase 5 rule)."""
    obs, ledger = _fixture_observation(tmp_path, eta=0.05)
    # eta=0.05 -> ratio 0.05^(1/4)=0.472 -> d=0.283 < envelope min 0.3
    record = reality_loop.close_reality_loop(
        "04", obs, portfolio_root=PORTFOLIO_ROOT,
        out_root=tmp_path / "out", ledger_path=ledger)
    assert record["status"] == "ENVELOPE_BLOCKS_COMPENSATION"
    assert record["mutation"]["applied"] is False
    assert record["mutation"]["computed_value"] < 0.3


def test_wrong_phase_row_refuses_parse(tmp_path):
    """Art. II: a gas-phase row must be refused — the proposition binds
    to the exact liquid row at 310.15 K."""
    tsv = FIXTURE_TSV.replace(b"liquid", b"gas")
    with pytest.raises(ValueError, match="phase"):
        reality_loop.acquire_nist_water_viscosity(
            tmp_path / "obs", ledger_path=tmp_path / "l.jsonl",
            http_get=lambda url: tsv)


def test_malformed_payload_refuses_parse(tmp_path):
    with pytest.raises(ValueError, match="viscosity table"):
        reality_loop.acquire_nist_water_viscosity(
            tmp_path / "obs", ledger_path=tmp_path / "l.jsonl",
            http_get=lambda url: b"<html>error page</html>")


# ---------------------------------------------------------------------------
# D. Custody and determinism attacks (Art. VI/XVI)
# ---------------------------------------------------------------------------

def test_raw_byte_custody_hash_pins_event(tmp_path):
    """The recorded event's raw_data_sha256 equals the hash of the saved
    bytes — re-hashing the raw file reproduces the ledger's custody."""
    obs, ledger = _fixture_observation(tmp_path)
    raw = Path(obs["raw_path"]).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == obs["raw_sha256"]
    ev = obs["event"]
    assert ev["raw_data_sha256"] == obs["raw_sha256"]
    # tampering the raw file breaks the recorded custody
    Path(obs["raw_path"]).write_bytes(raw + b"x")
    assert hashlib.sha256(
        Path(obs["raw_path"]).read_bytes()).hexdigest() != obs["raw_sha256"]


def test_metamorphic_event_value_changes_decision(tmp_path):
    """Different measured values must produce different decisions (a
    metamorphic property: the machinery actually responds to the input)."""
    obs1, l1 = _fixture_observation(tmp_path / "a", eta=0.6913036)
    obs2, l2 = _fixture_observation(tmp_path / "b", eta=0.75)
    r1 = reality_loop.close_reality_loop(
        "04", obs1, portfolio_root=PORTFOLIO_ROOT,
        out_root=tmp_path / "oa", ledger_path=l1)
    r2 = reality_loop.close_reality_loop(
        "04", obs2, portfolio_root=PORTFOLIO_ROOT,
        out_root=tmp_path / "ob", ledger_path=l2)
    assert r1["mutation"]["to_value"] != r2["mutation"]["to_value"]
    assert r1["mutation"]["to_value"] == pytest.approx(
        0.6 * 0.6913036 ** 0.25, abs=1e-3)
    assert r2["mutation"]["to_value"] == pytest.approx(
        0.6 * 0.75 ** 0.25, abs=1e-3)


def test_loop_closure_is_deterministic(tmp_path):
    """Same inputs -> byte-identical comparison + mutation decision."""
    outs = []
    for sub in ("run1", "run2"):
        obs, ledger = _fixture_observation(tmp_path / sub)
        r = reality_loop.close_reality_loop(
            "04", obs, portfolio_root=PORTFOLIO_ROOT,
            out_root=tmp_path / f"out_{sub}", ledger_path=ledger)
        outs.append((r["comparison"], r["mutation"]["to_value"],
                     r["re_evaluation"]["conductance_restored_ratio"]))
    assert outs[0] == outs[1]


# ---------------------------------------------------------------------------
# E. Canonical-state isolation (Art. IX — the e11 class, closed)
# ---------------------------------------------------------------------------

def test_canonical_ledgers_and_portfolio_byte_identical(tmp_path):
    """A battery of hermetic closures leaves the canonical R370G ledgers
    and the portfolio DOWNLOAD tree byte-identical."""
    before = _ledger_hashes()
    portfolio_before = _tree_hash(PORTFOLIO_ROOT / "DOWNLOAD")
    for i in range(3):
        obs, ledger = _fixture_observation(tmp_path / f"iso{i}")
        reality_loop.close_reality_loop(
            "04", obs, portfolio_root=PORTFOLIO_ROOT,
            out_root=tmp_path / f"iso_out{i}", ledger_path=ledger)
    assert _ledger_hashes() == before
    assert _tree_hash(PORTFOLIO_ROOT / "DOWNLOAD") == portfolio_before


def _tree_hash(root: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(root.rglob("*")):
        if p.is_file():
            h.update(str(p.relative_to(root)).encode())
            h.update(p.read_bytes())
    return h.hexdigest()


# ---------------------------------------------------------------------------
# F. The real-event path end-to-end (redirected ledger, real semantics)
# ---------------------------------------------------------------------------

def test_real_event_completes_causal_chain_and_derives_state(tmp_path):
    """A REAL (non-rehearsal) event with a redirected ledger completes
    the 9-stage chain and derive-real-loop-verified returns TRUE — the
    same code path as the live run (Art. XXXVII same-path rule)."""
    ledger = tmp_path / "REALITY_EVENT_LEDGER.jsonl"
    obs = reality_loop.acquire_nist_water_viscosity(
        tmp_path / "observation", package_id="P-07",
        ledger_path=ledger, rehearsal=False,
        http_get=lambda url: FIXTURE_TSV)
    record = reality_loop.close_reality_loop(
        "04", obs, portfolio_root=PORTFOLIO_ROOT,
        out_root=tmp_path / "out", ledger_path=ledger)
    assert record["status"] == "LOOP_CLOSED"
    assert record["observation_origin"] == "MEASURED"
    chain = record["causal_chain"]
    assert chain["recorded_in_canonical_ledger"] is True
    assert [s["stage"] for s in chain["stages"]] == [
        "EVENT", "EVIDENCE", "BELIEF_UPDATE", "KNOWLEDGE_ATOM",
        "EIG_CHANGE", "EXPERIMENT_CHANGE", "PACKAGE_MUTATION",
        "DISCOVERY_CONSTRAINT", "FUTURE_CANDIDATE_CHANGE"]
    assert chain["loop_state"] == "REAL_LOOP_VERIFIED"
    # every mutation entry carries the full Art. XXXVIII provenance
    muts = [json.loads(ln) for ln in
            (tmp_path / "CAUSAL_MUTATION_LEDGER.jsonl").read_text()
            .splitlines() if ln.strip()]
    assert len(muts) == 9
    for m in muts:
        assert m["trigger_event_id"] == obs["event_id"]
        assert m["before_hash"] and m["after_hash"]
        assert m["reason"]
        assert m["timestamp"]


def test_rebuild_uses_measured_geometry_not_request(tmp_path):
    """The re-evaluation must use the MEASURED rebuilt radius (from the
    CAD kernel's cylinder faces), not merely the requested parameter."""
    obs, ledger = _fixture_observation(tmp_path)
    record = reality_loop.close_reality_loop(
        "04", obs, portfolio_root=PORTFOLIO_ROOT,
        out_root=tmp_path / "out", ledger_path=ledger)
    nd = record["new_design"]
    assert nd["measured_geometry_value"] is not None
    assert nd["measured_geometry_value"] == pytest.approx(
        record["mutation"]["to_value"], abs=0.02)
    assert nd["geometry_validation"]["valid"] is True
    assert record["re_evaluation"]["after"]["d_mm"] == pytest.approx(
        nd["measured_geometry_value"], abs=1e-9)
