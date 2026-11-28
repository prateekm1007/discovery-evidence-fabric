"""discovery_fabric/engine/review_layer.py — the CHECK LAYER as
ENGINE code (the R131-F2 / R133 DIR-3 migration; the F63 rule:
capability logic lives in the engine, not scripts/).

Lineage (forward-only, Art. 16 accounting):
  - check_layer moved VERBATIM from scripts/r121_successor_run.py:55
    (the stripped machine's own scans over (prob, bill) — the
    successor machine's check leg). The script keeps a thin
    re-export shim importing from HERE (historical instruments stay
    importable; their committed bytes are never rewritten).
  - FIX_SCHEMA moved byte-identically from
    scripts/r127_phaseA_gate.py:47 (also mirrored in
    engine/prompts.py — the prompts module is the canonical pointer
    for prompt/schema constants; this module is the behavior surface).
  - the scanner surface is scripts/r40_machine_v77.py (m77) — the
    deterministic defect-detection layer (base_scan, deliverable
    class, formula direction, constraint fit, catalog, standard bill,
    operational loss, conversion, allowed-measures, physics
    direction, direction lexicon, input availability, duty-cycle
    pricing). The m77 module stays in scripts/ (its own committed
    lineage); THIS module binds the scanner set as engine behavior.

Determinism: pure over (prob, bill) bytes; zero network, zero LLM.
CI: tests/test_article22_measured_path.py extended to the F31e path
(check_layer resolves through discovery_fabric/engine/).
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

import r40_machine_v77 as m77  # noqa: E402


def check_layer(prob: dict, bill: str, gw_key: str | None) -> dict:
    """The stripped machine's own scans over (prob, bill) — the
    successor machine's check leg, minus the LLM direction check
    (which needs the gateway; the deterministic scans are the check
    layer's defect-detection surface and match the amendment-1
    detector set exactly). MOVED VERBATIM from
    scripts/r121_successor_run.py (R133 DIR-3); byte-identical
    behavior."""
    vio: dict = {}
    vio.update(m77.base_scan(bill))
    vio.update(m77.scan_deliverable_class(bill))
    vio.update(m77.scan_stated_formula_direction(bill))
    vio.update(m77.scan_constraint_fit(prob, bill))
    vio.update(m77.scan_catalog(prob, bill))
    sb = m77.scan_standard_bill(bill, "intervention-proposal")
    if sb:
        vio.update(sb)
    ol = m77.scan_operational_loss(bill, "intervention-proposal")
    if ol:
        vio.update(ol)
    cv = m77.scan_conversion(bill, "intervention-proposal", prob)
    if cv:
        vio.update(cv)
    vio.update(m77.scan_allowed_measures_class(prob, bill))
    vio.update(m77.scan_physics_direction(prob, bill))
    vio.update(m77.direction_lexicon_check(prob, bill))
    vio.update(m77.scan_input_availability(prob, bill))
    vio.update(m77.scan_duty_cycle_pricing(bill))
    return vio


# The reviewer fix schema (byte-identical to r127_phaseA_gate.FIX_SCHEMA
# and engine/prompts.REVIEWER_FIX_SCHEMA — one constant, two views).
from discovery_fabric.engine.prompts import REVIEWER_FIX_SCHEMA  # noqa: E402,F401
