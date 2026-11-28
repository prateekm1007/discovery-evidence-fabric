"""tests/test_physics_guards_am91.py — the AM91 physics-guard CI
(claim c-0116): the ammonia-strip direction relation, the ride-along
van 't Hoff direction guard and the aqueous NaOH saturation bound,
each with the contract's CI controls + the Art. 3 degenerate-input
typed-refusal battery entries (the registry rows live in
tests/test_article3_degenerate_inputs.py::DEGENERATE_KWARGS)."""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine import physics_checks as pc  # noqa: E402


# ---- the ammonia-strip direction relation (the HO14-12 class) ----

def test_ammonia_raises_improve() -> None:
    """Contract control 1: raising pH AND the A/W ratio improves."""
    r = pc.ammonia_strip_direction(
        ph_initial=8.0, ph_proposed=10.8, temp_initial_degC=25.0,
        temp_proposed_degC=35.0, aw_initial=2.0, aw_proposed=3.5)
    assert r["verdict"] == "RUN" and r["direction_of_effect"] == \
        "improves", r
    assert r["value"] > 0


def test_ammonia_lower_aw_is_worsens() -> None:
    """Contract control 2: lowering the A/W ratio WORSENS the removal
    potential (the inverted mitigation; the scan kills the CLAIM via
    AMMONIA_STRIP_DIRECTION_INVERTED — the relation computes the
    truth)."""
    r = pc.ammonia_strip_direction(
        ph_initial=10.8, ph_proposed=10.8, temp_initial_degC=30.0,
        temp_proposed_degC=30.0, aw_initial=3.0, aw_proposed=1.5)
    assert r["verdict"] == "RUN" and r["direction_of_effect"] == \
        "worsens", r
    assert r["value"] < 0


def test_ammonia_degenerate_inputs_refused() -> None:
    """Contract control 4 (Art. 3): degenerate inputs are typed
    REFUSED, never uncaught."""
    r = pc.ammonia_strip_direction(10.8, 10.8, 30.0, 30.0, 3.0, 3.0)
    assert r["verdict"] == "REFUSED", r
    assert "no parameter change" in r["detail"]["error"]
    for bad in (dict(ph_initial=15.0, ph_proposed=10.0,
                     temp_initial_degC=25.0, temp_proposed_degC=30.0,
                     aw_initial=2.0, aw_proposed=3.0),
                dict(ph_initial=8.0, ph_proposed=10.0,
                     temp_initial_degC=25.0, temp_proposed_degC=30.0,
                     aw_initial=0.0, aw_proposed=3.0)):
        r = pc.ammonia_strip_direction(**bad)
        assert r["verdict"] == "REFUSED", r


# ---- the van 't Hoff direction guard (the HO14-04 class) ----

def test_vant_hoff_exothermic_cooling_desorption_refused_shape() -> None:
    """The EXACT HO14-04 claim shape: exothermic dH_ads, cooling
    proposed, desorption intent — the relation computes K2/K1 < 1 is
    FALSE (cooling RAISES K_ads) so the claimed intent WORSENS. The
    generator's claim was the opposite of the computed sign."""
    r = pc.vant_hoff_adsorption_direction(
        delta_h_ads_kj_mol=-40.0, t_initial_degC=25.0,
        t_proposed_degC=5.0, intent="PROMOTE_DESORPTION")
    assert r["verdict"] == "RUN", r
    assert r["value"] > 1.0  # cooling an exothermic adsorption RAISES K
    assert r["direction_of_effect"] == "worsens", r


def test_vant_hoff_heating_promotes_desorption() -> None:
    """Warm-caustic elution: heating an exothermic adsorption lowers
    K_ads and promotes desorption (improves)."""
    r = pc.vant_hoff_adsorption_direction(
        delta_h_ads_kj_mol=-40.0, t_initial_degC=25.0,
        t_proposed_degC=60.0, intent="PROMOTE_DESORPTION")
    assert r["verdict"] == "RUN" and r["value"] < 1.0
    assert r["direction_of_effect"] == "improves", r


def test_vant_hoff_degenerate_inputs_refused() -> None:
    for kwargs in (dict(delta_h_ads_kj_mol=0.0, t_initial_degC=25.0,
                        t_proposed_degC=65.0,
                        intent="PROMOTE_DESORPTION"),
                   dict(delta_h_ads_kj_mol=-40.0, t_initial_degC=25.0,
                        t_proposed_degC=25.0,
                        intent="PROMOTE_DESORPTION"),
                   dict(delta_h_ads_kj_mol=-40.0, t_initial_degC=25.0,
                        t_proposed_degC=65.0, intent="MAKE_IT_GO")):
        r = pc.vant_hoff_adsorption_direction(**kwargs)
        assert r["verdict"] == "REFUSED", r


# ---- the aqueous saturation bound (the HO14-04 "50 M NaOH" class) --

def test_naoh_50m_refused() -> None:
    r = pc.aqueous_molarity_saturation_bound("NaOH", 50.0)
    assert r["verdict"] == "REFUSED", r
    assert "saturation bound" in r["detail"]["error"]


def test_naoh_practical_molarities_run() -> None:
    r = pc.aqueous_molarity_saturation_bound("sodium hydroxide", 15.3)
    assert r["verdict"] == "RUN" and r["value"] == 15.3, r
    r2 = pc.aqueous_molarity_saturation_bound("caustic", 24.0)
    assert r2["verdict"] == "RUN" and \
        r2["detail"]["near_saturation"] is True, r2


def test_unknown_solute_fails_closed() -> None:
    r = pc.aqueous_molarity_saturation_bound("unobtainium", 2.0)
    assert r["verdict"] == "REFUSED", r
    assert "not in the aqueous saturation registry" in \
        r["detail"]["error"]


# ---- registry wiring ----

def test_new_checks_registered() -> None:
    for cid in ("ammonia_strip_direction",
                "vant_hoff_adsorption_direction",
                "aqueous_molarity_saturation_bound"):
        assert cid in pc.CHECKS
        assert cid in pc.CHECKS_BY_FAILURE_CLASS.values() or any(
            cid in v for v in pc.CHECKS_BY_FAILURE_CLASS.values())
