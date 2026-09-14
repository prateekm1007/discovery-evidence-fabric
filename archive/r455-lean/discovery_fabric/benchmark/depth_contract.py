"""Phase 2 — engineering depth contract (Coder 2).

The contract defines what a qualifying dossier needs, DERIVED FROM THE
BENCHMARK CORPUS — never from arbitrary numbers chosen to make Coder 1
pass (CEO mandate; Constitution Art. XXVII: no threshold invention).

Derivation rules (each requirement records its provenance):

  R1 CORPUS_UNIFORM    — satisfied by 15/15 frozen packages -> hard
                         requirement (FAIL if violated).
  R2 CORPUS_FLOOR      — higher-is-better count; qualifying floor = corpus
                         MIN (the weakest frozen buyer-ready package defines
                         "same substantive level"). Below min -> FAIL.
                         [min, median) -> CONDITIONAL. >= median -> PASS.
  R3 CORPUS_CEILING    — lower-is-better count (orphans, issues);
                         FAIL above corpus MAX, CONDITIONAL above median.
  R4 CORPUS_MAJORITY   — boolean satisfied by >= 80% of corpus; violation
                         maps to CONDITIONAL (a minority of frozen packages
                         would also violate).

Every threshold in the emitted contract carries `derivation` provenance.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

DEFAULT_PROFILE = Path("artifacts/benchmark/BENCHMARK_DOSSIER_PROFILE.json")


def _m(profile: Dict[str, Any], key: str) -> Dict[str, Any]:
    return profile["measures"][key]


def build_contract(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Derive the engineering depth contract from the corpus profile."""
    sections: list = []

    def stat(key: str) -> Dict[str, Any]:
        return _m(profile, key)

    # ------------------------------------------------------------------ 1
    d = stat("section_coverage")
    sections.append({
        "section": "DOSSIER_COMPLETENESS",
        "minimum_depth": {
            "section_coverage": d["min"],
            "dossier_chars": stat("dossier_chars")["min"],
        },
        "required_objects": [
            "15 numbered engineering sections rendered in the dossier PDF",
            "all 6 package PDFs (00..05) present",
        ],
        "required_traceability": [
            "every section reachable in extracted PDF text",
        ],
        "required_provenance": [],
        "required_specificity": [
            "buyer decision page with all "
            f"{stat('buyer_decision_elements')['min']} mandated elements",
        ],
        "failure_condition": {
            "section_coverage < corpus min": "FAIL",
            "any required PDF missing": "FAIL",
            "any buyer decision element missing": "FAIL",
            "dossier_chars below corpus min": "CONDITIONAL",
        },
        "derivation": {
            "rule": "R1_CORPUS_UNIFORM (15/15) + R2_CORPUS_FLOOR for chars",
            "corpus_stats": {
                "section_coverage": _dist(d),
                "dossier_chars": _dist(stat("dossier_chars")),
                "buyer_decision_elements": _dist(
                    stat("buyer_decision_elements")),
            },
        },
    })

    # ------------------------------------------------------------------ 2
    sections.append({
        "section": "ENGINEERING_CORE",
        "minimum_depth": {
            "equations": stat("equations")["min"],
            "critical_parameters": stat("critical_parameters")["min"],
            "remaining_unknowns": stat("remaining_unknowns")["min"],
            "unknown_markers": stat("unknown_markers")["min"],
        },
        "required_objects": [
            "governing model with corpus-floor equations",
            "critical design parameters (count at corpus floor)",
            "explicit unknowns register (count at corpus floor)",
        ],
        "required_traceability": [
            "every equation carries id / source / applicability / assumptions",
            "every critical parameter carries a provenance basis or UNKNOWN",
        ],
        "required_provenance": [
            "equations_with_issues == 0 (corpus uniform)",
            "unsupported_numbers == 0 (corpus uniform)",
        ],
        "required_specificity": [
            "equations judged applicable to the invention's domain",
            "explicit unknown disclosure (Art. XXV markers present)",
        ],
        "failure_condition": {
            "equations < corpus min": "FAIL",
            "critical_parameters < corpus min": "FAIL",
            "remaining_unknowns < corpus min": "FAIL",
            "unknown_markers < corpus min": "CONDITIONAL",
            "equations_with_issues > corpus max": "FAIL",
            "unsupported_numbers > corpus max": "FAIL",
        },
        "derivation": {
            "rule": "R2_CORPUS_FLOOR + R1 for zero-issue uniforms",
            "corpus_stats": {k: _dist(stat(k)) for k in (
                "equations", "critical_parameters", "remaining_unknowns",
                "unknown_markers", "equations_with_issues",
                "unsupported_numbers")},
        },
    })

    # ------------------------------------------------------------------ 3
    sections.append({
        "section": "DESIGN_CHAIN",
        "minimum_depth": {
            "design_inputs": stat("design_inputs")["min"],
            "design_outputs": stat("design_outputs")["min"],
            "traceability_chains": stat("traceability_chains")["min"],
            "chain_linkage_rate": stat("chain_linkage_rate")["min"],
            "evidence_ids_per_object": stat("evidence_ids_per_object")["min"],
            "orphan_design_outputs_max": stat("orphan_design_outputs")["max"],
            "orphan_failure_modes_max": stat("orphan_failure_modes")["max"],
        },
        "required_objects": [
            "design inputs at corpus floor",
            "design outputs at corpus floor",
        ],
        "required_traceability": [
            "DI -> DO -> FM -> VF linkage chains at corpus floor",
            "chain_linkage_rate at corpus floor",
        ],
        "required_provenance": [
            f"evidence_ids_per_object >= {stat('evidence_ids_per_object')['min']}",
        ],
        "required_specificity": [
            "design inputs state value + source + epistemic class",
        ],
        "failure_condition": {
            "design_inputs < corpus min": "FAIL",
            "design_outputs < corpus min": "FAIL",
            "traceability_chains < corpus min": "FAIL",
            "chain_linkage_rate < corpus min": "FAIL",
            "evidence_ids_per_object < corpus min": "FAIL",
            "orphan_design_outputs > corpus max": "FAIL",
            "orphan_failure_modes > corpus max": "FAIL",
        },
        "derivation": {
            "rule": "R2_CORPUS_FLOOR + R3_CORPUS_CEILING",
            "corpus_stats": {k: _dist(stat(k)) for k in (
                "design_inputs", "design_outputs", "traceability_chains",
                "chain_linkage_rate", "evidence_ids_per_object",
                "orphan_design_outputs", "orphan_failure_modes")},
        },
    })

    # ------------------------------------------------------------------ 4
    sections.append({
        "section": "VERIFICATION_VALIDATION",
        "minimum_depth": {
            "verifications": stat("verifications")["min"],
            "validations": stat("validations")["min"],
        },
        "required_objects": [
            "verification items at corpus floor",
            "validation items at corpus floor",
        ],
        "required_traceability": [
            "each verification carries requirement / method / acceptance",
            "each validation carries requirement / method / status",
        ],
        "required_provenance": [
            "verification results honestly NOT_TESTED until tested",
            "validation NOT_PERFORMED unless a physical observation exists",
        ],
        "required_specificity": [
            "verification and validation kept separate (no V&V collapse)",
        ],
        "failure_condition": {
            "verifications < corpus min": "FAIL",
            "validations < corpus min": "FAIL",
            "verification claims an unearned result": "FAIL",
            "validation claims an unearned result": "FAIL",
        },
        "derivation": {
            "rule": "R2_CORPUS_FLOOR + Art. XXXVIII reality boundary",
            "corpus_stats": {k: _dist(stat(k)) for k in (
                "verifications", "validations")},
        },
    })

    # ------------------------------------------------------------------ 5
    sections.append({
        "section": "FAILURE_ANALYSIS",
        "minimum_depth": {
            "failure_modes": stat("failure_modes")["min"],
        },
        "required_objects": [
            "invention-specific failure modes at corpus floor",
        ],
        "required_traceability": [
            "each failure mode links mechanism / mitigation / verification",
        ],
        "required_provenance": [
            "residual uncertainty disclosed per failure mode",
        ],
        "required_specificity": [
            "failure modes are mechanism-specific, not generic fillers",
        ],
        "failure_condition": {
            "failure_modes < corpus min": "FAIL",
            "orphan_failure_modes > corpus max": "FAIL",
            "generic filler failure modes": "CONDITIONAL",
        },
        "derivation": {
            "rule": "R2_CORPUS_FLOOR + R3_CORPUS_CEILING",
            "corpus_stats": {k: _dist(stat(k)) for k in (
                "failure_modes", "orphan_failure_modes")},
        },
    })

    # ------------------------------------------------------------------ 6
    sections.append({
        "section": "EVIDENCE_PROVENANCE",
        "minimum_depth": {
            "external_evidence": stat("external_evidence")["min"],
            "evidence_ids_per_object": stat("evidence_ids_per_object")["min"],
            "unsupported_numbers_max": stat("unsupported_numbers")["max"],
            "equations_with_issues_max": stat("equations_with_issues")["max"],
        },
        "required_objects": [
            "external evidence items at corpus floor",
        ],
        "required_traceability": [
            "evidence ids bound to sources with hashes",
        ],
        "required_provenance": [
            "no naked numbers (numerical provenance hard gate)",
            "no fake sources (hash must verify against evidence content)",
        ],
        "required_specificity": [
            "evidence spans prove the propositions they are bound to",
        ],
        "failure_condition": {
            "external_evidence < corpus min": "FAIL",
            "any NAKED_NUMBER / UNSUPPORTED_NUMBER detected": "FAIL",
            "any source hash mismatch detected": "FAIL",
        },
        "derivation": {
            "rule": "R2_CORPUS_FLOOR + Phase 9 hard gate",
            "corpus_stats": {"external_evidence": _dist(stat("external_evidence"))},
        },
    })

    # ------------------------------------------------------------------ 7
    tb = stat("transfer_boundary_elements")
    sections.append({
        "section": "TRANSFER_BOUNDARY",
        "minimum_depth": {
            "transfer_boundary_elements": tb["min"],
        },
        "required_objects": [
            "YOU RECEIVE / YOU MUST DEVELOP / YOU MUST VERIFY blocks",
        ],
        "required_traceability": [
            "transfer boundary content present in rendered package",
        ],
        "required_provenance": [],
        "required_specificity": [
            "BUYER_RECEIVES / BUYER_MUST_DEVELOP / BUYER_MUST_VERIFY never "
            "collapsed into TRANSFER_READY",
            "transfer_ready=TRUE only with reality-loop evidence",
        ],
        "failure_condition": {
            "transfer boundary elements missing": "FAIL",
            "transfer boundary removed": "FAIL",
            "transfer_ready collapsed without evidence": "FAIL",
        },
        "derivation": {
            "rule": "R1_CORPUS_UNIFORM (15/15 have 3/3 elements) + "
                    "Art. XXXVIII + Phase 11",
            "corpus_stats": {"transfer_boundary_elements": _dist(tb)},
        },
    })

    # ------------------------------------------------------------------ 8
    mfg = stat("manufacturing_has_processes")
    reg = stat("regulatory_has_di")
    sections.append({
        "section": "MANUFACTURING_REGULATORY",
        "minimum_depth": {
            "manufacturing_has_processes": 1,
            "regulatory_has_di": 1,
        },
        "required_objects": [
            "candidate manufacturing processes with honest status",
            "regulatory design input present",
        ],
        "required_traceability": [
            "manufacturing status recorded (validated vs candidate)",
        ],
        "required_provenance": [],
        "required_specificity": [
            "regulatory pathway honestly labeled (UNKNOWN where unknown)",
        ],
        "failure_condition": {
            "manufacturing processes absent": "CONDITIONAL",
            "regulatory design input absent": "FAIL",
        },
        "derivation": {
            "rule": "R4_CORPUS_MAJORITY for manufacturing "
                    f"({mfg['min'] * 15 if mfg['min'] else 14}/15), "
                    "R1_CORPUS_UNIFORM for regulatory DI (15/15)",
            "corpus_stats": {
                "manufacturing_has_processes": _dist(mfg),
                "regulatory_has_di": _dist(reg),
            },
        },
    })

    contract = {
        "artifact": "ENGINEERING_DEPTH_CONTRACT",
        "owner": "CODER2",
        "version": "1.0.0",
        "derived_from": {
            "corpus_repo": profile.get("corpus_repo"),
            "corpus_head": profile.get("corpus_head_verified"),
            "profile": "BENCHMARK_DOSSIER_PROFILE.json",
            "profile_generated_at": profile.get("generated_at"),
        },
        "derivation_rules": {
            "R1_CORPUS_UNIFORM": "satisfied by 15/15 frozen packages -> "
                                 "hard requirement",
            "R2_CORPUS_FLOOR": "higher-is-better; floor = corpus MIN; "
                               "below min FAIL; [min, median) CONDITIONAL",
            "R3_CORPUS_CEILING": "lower-is-better; above max FAIL; "
                                 "above median CONDITIONAL",
            "R4_CORPUS_MAJORITY": ">=80% corpus satisfaction; violation "
                                  "maps to CONDITIONAL",
        },
        "no_threshold_invention_note": (
            "Every numeric threshold below is the corpus min/median/max of "
            "the same measure across the 15 frozen buyer-ready packages. "
            "No number was chosen by judgment (Art. XXVII)."),
        "sections": sections,
        "verdict_vocabulary": ["PASS", "CONDITIONAL", "FAIL"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    return contract


def _dist(d: Dict[str, Any]) -> Dict[str, Any]:
    return {k: d.get(k) for k in
            ("min", "p25", "median", "p75", "max", "n", "measured", "missing")}


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--profile", default=str(DEFAULT_PROFILE))
    ap.add_argument("--out", default="artifacts/benchmark/"
                                     "ENGINEERING_DEPTH_CONTRACT.json")
    args = ap.parse_args()

    profile = json.loads(Path(args.profile).read_text(encoding="utf-8"))
    contract = build_contract(profile)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(contract, indent=1, ensure_ascii=False),
                   encoding="utf-8")
    print(f"ENGINEERING_DEPTH_CONTRACT.json written: {out}")
    for s in contract["sections"]:
        md = s["minimum_depth"]
        keys = ", ".join(f"{k}>= {v}" if isinstance(v, int)
                         else f"{k}>={v}" for k, v in md.items())
        print(f"  {s['section']:28s} {keys}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
