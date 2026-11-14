#!/usr/bin/env python3
"""r11_build_frozen_ledger — P0-1 (Amendment 2): the frozen-candidate
ledger for the lead-preserving repair path.

  p09 / sofc / new01: the CREDIT-REGISTER LEADS are RESTORED as the
  frozen candidates (UV-crosslinked EVOH, ZrO2 glass-ceramic seal +
  graded cathode, ionic-liquid/polymer hybrid electrolyte) with the
  Amendment-1 salvage directives — the machine keeps its best novelty
  assets instead of resampling them.
  The other 9: the R2 incumbent candidates, frozen, each carrying the
  auditor's R2 findings as prior_findings (the in-place repair edits
  exactly these; nothing else changes — byte-stability).
Deterministic from the committed bytes + the authoritative auditor
records; zero LLM calls.
"""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
R1 = REPO / "eval" / "pairs" / "r11_a1"
R2 = REPO / "eval" / "pairs" / "r11_a1_r2"
OUT = REPO / "eval" / "repair_ledger_r11"
OUT.mkdir(parents=True, exist_ok=True)

LEADS = {
    "bench-p09-packaging-barrier": {
        "source": "credit-register lead (1.0.0; pair WINNER, "
                  "restored per Amendment 2 P0-1)",
        "repair_directives": [
            "Specify the photoinitiator/functionalization chemistry "
            "for the UV crosslink — bare UV will not crosslink EVOH "
            "(Amendment 1 salvage)",
            "Replace the 18-month real-time test with a Peck/"
            "Arrhenius-accelerated WVTR protocol with a stated "
            "acceleration model (Amendment 1 salvage)"],
    },
    "eval-sofc-thermal-cycling": {
        "source": "credit-register lead (1.0.0; owner-cited win, "
                  "restored per Amendment 2 P0-1)",
        "repair_directives": [
            "Run the rule-of-mixtures CTE SIGN CHECK on the ZrO2 "
            "dispersion (ZrO2 CTE ~10-11 ppm/K may RAISE the "
            "composite CTE) — anchor the mechanism on constrained "
            "sintering densification, not CTE reduction alone "
            "(Amendment 1 salvage)",
            "Fix the malformed DOI 10.1002/advs.77388 or cite the "
            "packet records only (Amendment 1 salvage)",
            "The falsification test MUST carry the constraint's own "
            "criteria: 500 thermal cycles 25->800 C at 5 C/min, OCV "
            ">1.0 V, seal leakage <1% of fuel flow, stack mass "
            "+<=2% (Amendment 1 salvage)",
            "The seal is a GLASS-CERAMIC IONIC INSULATOR — never an "
            "electronic conductor (the R2 LSM substitution is the "
            "audited defect)"],
    },
    "eval-new01-supercap-dryout": {
        "source": "credit-register lead (1.0.0; pair WINNER, "
                  "restored per Amendment 2 P0-1)",
        "repair_directives": [
            "State the ESR budget against the acetonitrile baseline "
            "(Amendment 1 salvage)",
            "Resolve the immobilization-vs-mobility tension: the "
            "polymer matrix must immobilize the ionic liquid "
            "against evaporation while the ions stay mobile enough "
            "to hold capacitance (Amendment 1 salvage)",
            "The mechanism must NOT claim osmosis drives vapor "
            "transport — osmosis is liquid-phase transport across "
            "a semipermeable membrane (the R2 category error)"],
    },
}

PRIOR_FINDINGS = {
    "bench-p02-leadacid-grid-corrosion": [
        "Cu/Cu2O is NOT stable at positive-plate potential in H2SO4: "
        "Cu dissolves and Cu ions poison Pb cells (auditor R2)",
        "Pourbaix stability must be cited at the electrode potential "
        "vs SHE, not the cell voltage 2.27 V (auditor R2)",
        "the 15-year real-time test carried an inconsistent "
        "'1000 cycles' clause (auditor R2)"],
    "dev-fu-003-motor-insulation": [
        "a predictor-design question was answered with a VPI "
        "maintenance rewind (offline, during outages) — no online "
        "leading indicator (auditor R2)",
        "'3x user-stated' improvement was fabricated — no such user "
        "statement exists (auditor R2)"],
    "dev-fu-004-fouling": [
        "a predictor-design question was answered with C70600 "
        "retubing — an intervention, not a predictor (auditor R2)",
        "the back-pressure indicator is outside the allowed signals "
        "(temperature and flow only) (auditor R2)",
        "C70600 is a self-declared industry standard yet was sold as "
        "NOVELTY_CLAIMED (auditor R2)"],
    "eval-new02-slipring-predictor": [
        "a 1-10 kHz indicator band is Nyquist-impossible from 1-minute "
        "historian samples (auditor R2)"],
    "eval-new04-chiller-fouling-predictor": [
        "condenser ΔP is NOT in the BMS point list the constraint "
        "enumerates (chilled/condenser water temps, compressor "
        "power, pump speed, outdoor wet-bulb) (auditor R2)",
        "'user-approved' was fabricated — no such user statement "
        "exists (auditor R2)"],
    "eval-new05-liion-balance-drift": [
        "1 A × 10 ms = 0.0028 mAh, NOT 10 mAh — the stated product "
        "is off by ×3600 (auditor R2)",
        "the balancing pulse direction was inverted relative to "
        "reducing the cell-to-cell spread (auditor R2)"],
    "eval-new07-transformer-dga-predictor": [
        "a 1.5-10 kHz indicator band from 15-minute averages is "
        "Nyquist-impossible (auditor R2)",
        "PD detection from 0.1%-of-load current harmonics is "
        "physically absurd (auditor R2)"],
}


def main() -> int:
    n = 0
    for r2f in sorted(R2.glob("*.json")):
        pid = r2f.stem
        if pid in LEADS:
            r1 = json.loads((R1 / f"{pid}.json").read_text())
            ch = r1.get("chosen") or {}
            entry = {
                "problem_id": pid, "lever": ch.get("lever"),
                "name": ch.get("name"),
                "mechanism": ch.get("mechanism"),
                "failure_link": ch.get("failure_link"),
                "source": LEADS[pid]["source"],
                "repair_directives": LEADS[pid]["repair_directives"],
                "prior_findings": []}
        else:
            r2 = json.loads(r2f.read_text())
            ch = r2.get("chosen") or {}
            entry = {
                "problem_id": pid, "lever": ch.get("lever"),
                "name": ch.get("name"),
                "mechanism": ch.get("mechanism"),
                "failure_link": ch.get("failure_link"),
                "source": "R2 incumbent (frozen; repaired in place "
                          "per Amendment 2 P0-1)",
                "repair_directives": [
                    "fix exactly the listed findings IN PLACE; every "
                    "aspect not named stays byte-stable"],
                "prior_findings": PRIOR_FINDINGS.get(pid, [])}
        (OUT / f"{pid}.json").write_text(
            json.dumps(entry, indent=1) + "\n", encoding="utf-8")
        n += 1
        print(f"[ledger] {pid[:44]:46s} <- {entry['source'][:52]}")
    print(f"[ledger] {n} frozen candidates -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
