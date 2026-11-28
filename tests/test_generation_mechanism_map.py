"""tests/test_generation_mechanism_map.py — the R145 sealed-set
classifier battery (DIR-2/DIR-3 enabler).

The generation.mechanism_map classifier's keyword vocabulary was
v16-shaped: the sealed v17 problems (the owner's 10-failure-class set)
routed only 18/30 before the additive extension (the verb forms —
"corrosion" is not a substring of "corrodes" — plus the separation/
CTE/TBC/insulation vocabulary). The extension is typed additive; the
weighted-keyword semantics (longer phrases score higher) resolve the
cross-class rows the owner's grouping pins (resonance-caused cracking
stays vibration; CTE-mismatch cracking stays thermal).
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.generation.mechanism_map import (  # noqa: E402
    classify_failure)

# the sealed v17 rows that exercised the extension (the owner's
# failure-class grouping; public problem statements, the RUBRICS are
# the private custody)
CASES = [
    ("Centrifugal slurry pump impeller erodes from hard quartz "
     "particles in the slurry.", "abrasion_erosion"),
    ("Pneumatic conveying elbow wears through from particle "
     "impingement at the bend.", "abrasion_erosion"),
    ("Hydro-transport pipeline bottom erodes from sliding bed load.",
     "abrasion_erosion"),
    ("Dairy pasteurizer heat-transfer surface fouls with protein "
     "deposit, raising energy use.", "fouling_deposition"),
    ("Refinery crude preheat train fouls from asphaltene deposition.",
     "fouling_deposition"),
    ("Geothermal brine reinjection wells scale with silica, losing "
     "injectivity.", "fouling_deposition"),
    ("Freeze-concentration of juice forms uncontrolled ice, trapping "
     "solute.", "nucleation_phase_change"),
    ("Rare-earth leachate carries iron/thorium impurities needing "
     "separation.", "contamination_separation"),
    ("Lithium brine boron/magnesium impurities degrade battery-grade "
     "product.", "contamination_separation"),
    ("Recycled plastic melt carries metal/label contaminants.",
     "contamination_separation"),
    ("Offshore splash-zone steel corrodes from cyclic seawater "
     "wetting.", "corrosion_chemical"),
    ("Chlor-alkali anolyte corrodes titanium anode coating.",
     "corrosion_chemical"),
    ("Flue-gas desulfurization duct corrodes from acid condensate.",
     "corrosion_chemical"),
    ("Rail axle fatigue cracks initiate at the wheel-seat fillet.",
     "fatigue_crack"),
    ("Crankshaft fillet fatigue cracks from cyclic bending.",
     "fatigue_crack"),
    ("Pressure-vessel nozzle fatigue cracks from thermal cycling.",
     "fatigue_crack"),
    ("Centrifuge bowl resonates at operating speed, cracking welds.",
     "vibration_resonance"),
    ("Subsea pipeline vortex-induced vibration fatigues the span.",
     "vibration_resonance"),
    ("Machine-tool spindle chatter resonance degrades finish.",
     "vibration_resonance"),
    ("Ceramic-metal seal cracks from CTE mismatch on thermal cycling.",
     "thermal_mismatch"),
    ("PCB solder joints fatigue from CTE mismatch under power "
     "cycling.", "thermal_mismatch"),
    ("Turbine thermal-barrier coating spalls from bond-coat "
     "oxidation.", "thermal_mismatch"),
    ("Hydrogen valve seat leaks from embrittlement/permeation.",
     "leakage_sealing"),
    ("Vacuum chamber seal leaks from outgassing/permeation.",
     "leakage_sealing"),
    ("HVDC bushing insulation degrades from field "
     "grading/contamination.", "electrical_insulation"),
    ("Motor winding insulation fails from partial discharge at "
     "voltage.", "electrical_insulation"),
    ("Capacitor dielectric breaks down from defect/field "
     "concentration.", "electrical_insulation"),
]


def test_sealed_rows_route_to_the_owner_grouping():
    for text, want in CASES:
        got = classify_failure(text).failure_class
        assert got == want, f"{text[:60]!r}: {got} != {want}"


def test_extension_is_additive_not_subtractive():
    """The pre-existing vocabulary still routes (the v16 shapes)."""
    assert classify_failure(
        "Ship stern-tube bearing wears from seawater-lubricated "
        "abrasion.").failure_class == "abrasion_erosion"
    assert classify_failure(
        "Lyophilizer vial-to-vial ice nucleation variability causes "
        "cake collapse.").failure_class == "nucleation_phase_change"
    assert classify_failure(
        "Overland conveyor belt rips at transfer points from trapped "
        "tramp metal.").failure_class == "contamination_separation"
    assert classify_failure(
        "Membrane bioreactor fouling spikes from extracellular polymer "
        "release.").failure_class == "fouling_deposition"


def test_degenerate_text_typed():
    sel = classify_failure("")
    assert sel.failure_class == "unclassified"
    assert sel.notes and "typed" in sel.notes[0]
