#!/usr/bin/env python3
"""R405 — manifest v3: enumerate the R405 round's artifacts and record
the round's honest state (external-audit response, unit-conversion defect
fix, executed $0 roadmap items, owner-gated items).
"""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
p = REPO / "LEAD_PORTFOLIO_4_MANIFEST.json"
m = json.loads(p.read_text())
m["manifest_version"] = "3.0"
m["r405_external_audit_response_round"] = {
    "date": "2026-09-04",
    "directive": "CEO one-word directive 'audit' + the external audit "
                 "document ('Lead Portfolio 4 — External Audit & Elite "
                 "Package Roadmap', Claude Sonnet 4.6, audited SHA "
                 "135fd74f): verify the external audit against the "
                 "repository, execute its $0 roadmap items that are not "
                 "owner-gated, and record the rest with executable paths",
    "audit_response": "R405/EXTERNAL_AUDIT_RESPONSE.md (every material "
                      "claim classified CONFIRMED / ADDRESSED_BY_R404 / "
                      "DISPUTED / EXECUTED_THIS_ROUND / OWNER_GATED; two "
                      "audit errors verified — the P08 "
                      "artifacts-never-existed claim and the Q_min "
                      "mL/hr-vs-mL/min unit error; one repo defect found "
                      "and fixed — see the unit-conversion disclosure)",
    "new_artifacts": [
        "R405/EXTERNAL_AUDIT_RESPONSE.md",
        "R405/UNIT_CONVERSION_DEFECT_DISCLOSURE.json (the 133.322^2 "
        "conductance inversion in reality_loop + physics_core: affected "
        "artifact inventory, unaffected ratio-verdicts, Art. XXXI memory "
        "artifact)",
        "LEAD_PORTFOLIO_4/P04/QMIN_FLOOR_FLOW_CALCULATION.json (Q_min "
        "0.2-0.4 mL/min physiological declaration + corrected floor "
        "flows + ~47% common-cause tolerance margin)",
        "LEAD_PORTFOLIO_4/P11/INSTRUMENT_MDD_CALCULATION.json (MDD "
        "0.0253 s vs the claimed 0.1 s settling difference)",
        "LEAD_PORTFOLIO_4/P{04,08,11,13}/ENGINEERING_TRACEABILITY.json "
        "(3 R394-identifier-bound DI->DO->V->experiment chains per "
        "package, engine-side)",
        "scripts/r405_p04_qmin_and_conductance.py (computation log)",
        "scripts/r405_extend_records.py + scripts/r405_traceability.py "
        "(deterministic generators)",
        "tests/test_r405_external_audit_response.py (adversarial pins)",
    ],
    "extended_artifacts": [
        "P04: DECISIVE_EXPERIMENT (Q_min + common-cause arm + cost), "
        "NOVELTY_ASSESSMENT (US20240207499A1 claim map), BUYER_SEQUENCE "
        "(commercial anchor), TECHNOLOGY_MATURITY (conductance note), "
        "GEOMETRY_SEPARATION (NIST disposition + auditor conflict)",
        "P08: ENERGY_BUDGET (D2 arithmetic, thermal boundary, GaAs "
        "sourcing, power framing), DECISIVE_EXPERIMENT (thermal kill + "
        "cost), BUYER_SEQUENCE (anchor)",
        "P11: DECISIVE_EXPERIMENT (quantified kill conditions + MDD + "
        "cost context), NOVELTY_ASSESSMENT (US20250242099A1 claim map), "
        "BUYER_SEQUENCE (anchor), DIFFERENTIATION (materiality "
        "literature)",
        "P13: NOVELTY_ASSESSMENT (2-query plan), DECISIVE_EXPERIMENT "
        "(KA-014 prominence + BSA fouling protocol + cost), "
        "BUYER_SEQUENCE (anchor)",
    ],
    "code_fixes": [
        "discovery_fabric/engine/reality_loop.py::"
        "_conductance_ml_per_min_mmhg — per-mmHg conversion inverted "
        "(divided where multiply is required); fixed with independent "
        "derivation + adversarial magnitude guard",
        "discovery_fabric/engine/physics_core.py::"
        "poiseuille_conductance — same defect, same fix",
        "tests/test_r390_reality_loop.py — pin re-derived through an "
        "independent unit path + magnitude guard 0.05 <= G <= 5.0",
        "tests/test_r394_benchmark.py — zero-denominator improvement "
        "case accepted as the strongest improvement form",
    ],
    "final_classification": "UNCHANGED from R404 (P04 "
        "READY_FOR_TECHNICAL_EVALUATION, P08 REQUIRES_ENGINEERING_REPAIR "
        "[D2 owner decision], P11 READY_FOR_SPONSORED_VALIDATION, P13 "
        "REQUIRES_EVIDENCE_REPAIR [novelty search owner-gated], P14 "
        "NOT_IN_FOUR_LEAD_PORTFOLIO) — nothing changed this round is a "
        "classification-deciding fact; see EXTERNAL_AUDIT_RESPONSE Part 5",
    "owner_gated_items_recorded": [
        "NIST canonical application (auditor conflict recorded; release "
        "protocol requires both repos pushed — the PAT is an operator "
        "input; executable path in GEOMETRY_SEPARATION)",
        "P08 D2 engineering decision",
        "P13 PatentBear 2-query execution (meter 2/20)",
        "P13 drift-target EXTERNAL_PRECEDENT sourcing",
        "ANSI/IEC thermal numbers (paywalled standards)",
        "P14 KILL-record execution (CEO disposition)",
        "single-value pre-registrations (Q_min, kill margins, fouling "
        "criterion)",
        "buyer-surface propagation of every engine-side record (Art. "
        "XXXIX release chain)",
    ],
    "p14_records": "BYTE-UNCHANGED (the R404 sha pin is re-verified by "
                   "tests)",
}
p.write_text(json.dumps(m, sort_keys=True, ensure_ascii=False,
                        indent=1) + "\n")
print("manifest v3.0 written")
