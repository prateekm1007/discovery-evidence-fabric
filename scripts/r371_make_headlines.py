#!/usr/bin/env python3
"""
r371_make_headlines.py — Build the R371 headline registry input.

Provenance: headline fields (technology_name, problem, mechanism, kill_if)
originate from the R370 portfolio v4 PACKAGE_MAP (the identity-frozen release
map). V2 mutation addenda are applied where a recorded mutation changes a
headline field (P-13 technology name; P-01/P-07 problem statement).

buyer_type is intentionally NOT carried over: v4 buyer_type strings name
specific companies without a source basis. V5 derives capability-based buyer
profiles instead; company names may appear only inside cited, hashed
external-precedent snippets (COMPETITOR_EVIDENCE).

Output: premium_package_factory/input/headlines_r371.json
"""

import json
import os
import sys

ENGINE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)
sys.path.insert(0, os.path.join(ENGINE, "premium_package_factory"))
sys.path.insert(0, ENGINE)

# v4 PACKAGE_MAP headline fields (verbatim from build_portfolio_v4.py —
# the identity-frozen release map; includes buyer_type for traceability
# but V5 will not render it as target-buyer claims).
V4_MAP = [
    {"num": "01", "pkg_id": "P-01", "name": "Multi-Segment Flow Control with Bayesian Occlusion Prediction", "problem": "Catheter obstruction causes 30-50% of shunt failures", "mechanism": "Multi-segment parallel catheter with Bayesian occlusion prediction and alpha-distribution controller", "kill_if": "Multi-segment shows no advantage over single-segment in >=80% of computational scenarios"},
    {"num": "02", "pkg_id": "P-02", "name": "Adaptive Valve Profile for Postural ICP Regulation", "problem": "ICP excursions during postural changes cause patient symptoms", "mechanism": "Valve whose opening pressure profile adapts to ICP trend via trend-feedback control", "kill_if": "Adaptive response time exceeds postural transient duration (cannot respond within seconds)"},
    {"num": "03", "pkg_id": "P-04", "name": "Catalytic Contact Time Lock for Amyloid Beta Clearance", "problem": "Amyloid beta accumulation in CSF of Alzheimer's/NPH patients with shunts", "mechanism": "NEP enzyme immobilized on catheter wall cleaves A-beta-42 via mass-transport-limited contact time", "kill_if": "Enzyme half-life in CSF environment is less than 30 days (insufficient for chronic implant)"},
    {"num": "04", "pkg_id": "P-07", "name": "Passive Drainage Priority Safety Floor", "problem": "Obstruction causes 30-50% of shunt failures with no passive safety floor", "mechanism": "Multi-lumen parallel catheter with differential conductance maintaining minimum drainage when primary path obstructs", "kill_if": "Common-cause obstruction affects both primary and floor lumens equally (no differential immunity)"},
    {"num": "05", "pkg_id": "P-11", "name": "Phage Anti-Biofilm Coating for Shunt Infection Prevention", "problem": "Infection causes 8-12% of shunt failures at $40-80K per case", "mechanism": "S. aureus phage K immobilized on electrospun titanium-coated catheter surface prevents biofilm establishment", "kill_if": "Phage K cannot retain infectivity when immobilized on Ti surface for >24h"},
    {"num": "06", "pkg_id": "P-13", "name": "Neuromorphic Shunt Failure Predictor", "problem": "Shunt failure prediction is reactive (symptoms then surgery)", "mechanism": "ML-based predictor using ICP and flow trends to forecast failure >=12h before symptoms", "kill_if": "No real failure dataset exists to train the model (CRITICAL BLOCKER per Article XXXVII)"},
    {"num": "07", "pkg_id": "P-15-R1", "name": "Self-Powered Sensing via Piezoelectric Energy Harvesting", "problem": "Chronic ICP monitoring requires battery or percutaneous leads", "mechanism": "Piezoelectric transducer harvests energy from CSF pulsation; duty-cycled sensing matches harvested power budget (R1 fix)", "kill_if": "Harvested power at in-vivo strain levels is insufficient for any duty cycle (model shows <0.1 uW average)"},
    {"num": "08", "pkg_id": "P-16", "name": "NIR Photovoltaic Power Delivery for Implantable Devices", "problem": "Implantable sensors need power without batteries or leads", "mechanism": "External 940nm NIR source penetrates tissue; implanted GaAs PV cell converts to electrical energy", "kill_if": "Tissue attenuation at 5cm depth prevents sufficient power delivery (>1mW/cm2 required at PV surface)"},
    {"num": "09", "pkg_id": "P-21-R1", "name": "UWB Catheter Position Mapping with SAR-Bounded Accuracy", "problem": "Catheter position verification requires CT/MRI (expensive, ionizing for CT)", "mechanism": "UWB transmitter in catheter; external receiver array localizes via TOA with SAR-bounded accuracy (R1 fix)", "kill_if": "SAR limit (1.6 W/kg) constrains transmit power below useful SNR at >5cm tissue depth"},
    {"num": "10", "pkg_id": "P-22-R1", "name": "Autonomous Catheter Navigation with Human-in-the-Loop", "problem": "Catheter placement is operator-dependent; malposition causes complications", "mechanism": "Hydraulic steering with closed-loop navigation; human-in-the-loop fallback (R1 fix); buckling analysis", "kill_if": "Buckling threshold is below typical insertion forces (catheter cannot navigate without buckling)"},
    {"num": "11", "pkg_id": "P-24", "name": "Gravity Compensation Hydraulic Damper for Postural Transients", "problem": "Postural ICP excursions cause over-drainage and under-drainage", "mechanism": "Proportional hydraulic damper attenuates postural pressure transients continuously (vs ASD on/off switching)", "kill_if": "Damper coefficient cannot be tuned to both attenuate transients AND maintain minimum drainage floor"},
    {"num": "12", "pkg_id": "P-26", "name": "Osmotic Pressure Regulating Drainage Valve", "problem": "Fixed-pressure valves cannot adapt to changing CSF conditions", "mechanism": "Semipermeable membrane with osmotic reservoir provides self-regulating drainage based on combined hydrostatic and osmotic pressure", "kill_if": "Membrane fouling rate in CSF reduces Lp by >50% within 30 days (insufficient for chronic implant)"},
    {"num": "13", "pkg_id": "P-27-R1", "name": "Self-Referencing Piezoresistive Pressure Sensor", "problem": "Chronic ICP monitoring sensors suffer from drift", "mechanism": "Piezoresistive MEMS sensor with self-referencing Wheatstone bridge for drift compensation (R1 fix)", "kill_if": "Self-referencing cannot reduce drift below 1 mmHg/month (insufficient for clinical utility)"},
    {"num": "14", "pkg_id": "P-28", "name": "Acoustic Obstruction Detection for CSF Shunts", "problem": "Shunt obstruction is detected late (symptoms then imaging)", "mechanism": "Catheter-integrated acoustic transducer detects obstruction via pulse-echo impedance contrast", "kill_if": "Tissue obstruction acoustic impedance is too similar to CSF for reliable detection (Z ratio < 1.1)"},
    {"num": "15", "pkg_id": "P-29", "name": "MR Flow Quantification Sensor at Catheter Scale", "problem": "CSF flow measurement requires clinical MRI (expensive, not continuous)", "mechanism": "Miniaturized permanent magnet + RF coil + gradient coil enables phase-contrast MRI flow measurement at catheter scale", "kill_if": "Miniaturization to catheter scale cannot achieve SNR > 10:1 at any B0 field (physically blocked)"},
]


def main():
    from r371.canonical_source import load_v2_addendum, apply_mutations, normalize_units

    out = []
    for row in V4_MAP:
        addendum = load_v2_addendum(row["pkg_id"])
        rec = {
            "portfolio_number": row["num"],
            "package_id": row["pkg_id"],
            "technology_name": apply_mutations(row["name"], addendum),
            "problem": apply_mutations(row["problem"], addendum),
            "mechanism": row["mechanism"],
            "kill_if": normalize_units(apply_mutations(row["kill_if"], addendum)),
            "has_v2_addendum": bool(addendum),
        }
        out.append(rec)

    dest = os.path.join(
        ENGINE, "premium_package_factory", "input", "headlines_r371.json"
    )
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(
            {
                "registry": "R371_HEADLINES",
                "provenance": (
                    "Headline fields from R370 portfolio v4 PACKAGE_MAP (identity-frozen); "
                    "V2 mutation addenda applied at generation time (script: "
                    "scripts/r371_make_headlines.py); buyer_type deliberately excluded "
                    "(unsourced company names retired per CEO audit directive Phase 3)."
                ),
                "packages": out,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )
    print(f"wrote {dest} ({len(out)} packages)")
    # sanity: P-13 name should carry the V2 mutation
    p13 = [r for r in out if r["package_id"] == "P-13"][0]
    print("P-13 name ->", p13["technology_name"][:80])
    p01 = [r for r in out if r["package_id"] == "P-01"][0]
    print("P-01 problem ->", p01["problem"][:120])


if __name__ == "__main__":
    main()
