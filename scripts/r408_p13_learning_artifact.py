#!/usr/bin/env python3
"""scripts/r408_p13_learning_artifact.py — R408 external-audit
instruction 5: preserve P13 as a LEARNING ARTIFACT (not a zombie).

Actions (all machine-recordable, no owner decisions made):
 1. LEAD_PORTFOLIO_4/P13/LEARNING_ARTIFACT_R408.json — the repositioning
    record: the causal chain of the architecture-level novelty collapse,
    the PERMANENT fabrication-spend freeze, and the ONE remaining live
    item (the narrow patent-counsel question on the measurement-method
    claim).
 2. MECHANISM_CEMETERY/CEMETERY.json — the causal lesson appended as a
    FAILURE_LESSON entry via append_entries_to_cemetery_file() (the
    byte-preserving, chain-maintaining append path; Art. XXXI/LI).
 3. LEAD_PORTFOLIO_4/FINAL_CLASSIFICATION.json — r408_extensions wiring
    (P13 learning-artifact repositioning + the P08 D2 gate pointer).

Constitution basis: Art. XI (append-only cemetery), Art. XXXI (every
correction creates a memory artifact), Art. LI (learning must be able to
change future search), Art. XLVI (causal novelty, not claim-shape
novelty), Art. XXV (CONTESTED stays CONTESTED).

Usage:
  python scripts/r408_p13_learning_artifact.py            # apply
  python scripts/r408_p13_learning_artifact.py --check    # verify only
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ENGINE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ENGINE_ROOT))

from orchestrator import mechanism_cemetery as mc  # noqa: E402

LP13 = ENGINE_ROOT / "LEAD_PORTFOLIO_4" / "P13"
LEARNING_PATH = LP13 / "LEARNING_ARTIFACT_R408.json"
CLASSIFICATION_PATH = ENGINE_ROOT / "LEAD_PORTFOLIO_4" / \
    "FINAL_CLASSIFICATION.json"

CEM_ID = "cem:r408:p13-arch-novelty"


def build_learning_artifact():
    return {
        "artifact_type": "LEARNING_ARTIFACT_REPOSITIONING",
        "artifact_version": "1.0.0",
        "portfolio_number": "P13",
        "company_designation": "P-29",
        "historical_package_id": "P-29 (Paired-Die Differential "
                                 "Biopressure Sensor)",
        "created_round": "R408 (external-audit instruction 5: 'Preserve "
                         "P13 as a learning artifact, not a zombie; do "
                         "not spend the $95-265K fabrication budget; "
                         "only the narrow counsel question on the "
                         "measurement-method claim remains; feed the "
                         "causal lesson into the cemetery')",
        "constitutional_basis": [
            "Art. XXXI (every correction creates a committed memory "
            "artifact)",
            "Art. LI (negative knowledge must be able to change future "
            "search — the cemetery entry is the mechanism)",
            "Art. XLVI (the machine distinguishes known/recombined/"
            "adapted/transferred/distinct — the distinction candidates "
            "were tested and failed the mechanism-level test)",
            "Art. XXV (CONTESTED stays CONTESTED: located art contests "
            "the architecture; the record never converts this to "
            "KILLED-by-absence or to NOVEL)",
            "Art. XLVII/LIV (the kill condition was cheap and was "
            "executed: the novelty review path cost days, not dollars)"
        ],
        "artifact_class": "LEARNING ARTIFACT — not a transfer item, not "
                          "a zombie: the package's remaining VALUE is "
                          "(a) the causal lesson (now in the mechanism "
                          "cemetery, machine-readable by the generator) "
                          "and (b) the pre-registered paired-die "
                          "benchmark, spendable ONLY if the owner "
                          "independently wants the fouling-asymmetry "
                          "answer measured",
        "the_causal_chain": [
            "STAGE 1 (pre-R406, the original defect): the package was "
            "built and scored WITHOUT any committed prior-art search "
            "artifact for THIS technology — the novelty position rested "
            "on retrieval absence, which is not evidence (Art. XXI.2); "
            "the gap was recorded honestly as REPORTED_BUT_UNLOCATED",
            "STAGE 2 (R406 hard gate): the directive's rule — 'do not "
            "spend large engineering effort until the specific novelty "
            "assessment exists' — forced the search; 7 live queries "
            "located the architecture in exact-recorded prior art "
            "(Seaver 2018 dissertation: implantable low-drift dual "
            "matched-die biopressure sensor with common-mode error "
            "subtraction; US4320664 1982 dummy-element piezoresistive "
            "bridge; WO2014076620A2; US11701504B2; US11422051B2) with "
            "verbatim claim spans and hash custody",
            "STAGE 3 (R407 claim-level comparison): every distinction "
            "candidate failed the Art. XLVI mechanism-level test — the "
            "exposed-active + shielded-dummy pair in the same fouling "
            "medium is a MEASUREMENT-PROTOCOL distinction; the 0.07 mm "
            "MEMS diaphragm is an ENGINEERING REALIZATION; the < 0.5 "
            "mmHg/month drift target is a MODEL_DERIVED target with no "
            "evidence class behind it — none is a new causal mechanism "
            "over the located art",
            "STAGE 4 (R408, this record): the architecture-level "
            "novelty position is closed as a FAILURE_LESSON; the "
            "fabrication budget stays FROZEN; exactly ONE narrow live "
            "item remains"
        ],
        "fabrication_spend": {
            "status": "FROZEN — PERMANENT",
            "amount_class": "$95-265K fab-NRE (REPORTED, 5-10x the "
                            "other lead packages' decisive experiments, "
                            "disclosed)",
            "basis": "the R406 directive hard gate + the R407-H rule "
                     "(engineering spend frozen permanent) + this R408 "
                     "audit instruction; the 5-arm bench protocol is "
                     "REGISTERED (EXPERIMENT_PREREGISTRATION.json) but "
                     "never funded from this record"
        },
        "the_one_remaining_live_item": {
            "item": "the narrow patent-counsel question on the "
                    "measurement-method claim",
            "question": "whether the located art recites the DIFFERENCE "
                        "channel between an exposed active element and "
                        "a shielded dummy element in the same fouling "
                        "medium AS the measured indicator of asymmetric "
                        "biofouling drift",
            "status": "CONDITIONAL — the only claim shape the R407 "
                      "comparison found that the located art does not "
                      "recite; requires owner patent-counsel "
                      "claim-charting to confirm; does NOT rescue the "
                      "compensation mechanism claims (E1-E4 remain "
                      "located art)",
            "owner_action": "patent counsel claim-chart review "
                            "(days-class cost, the CHEAP kill path — "
                            "already recorded as the recommended first "
                            "action in KILLABILITY_ASSESSMENT.json)"
        },
        "zombie_prevention_rules": [
            "no further engineering work on P13 (no CAD, no simulation, "
            "no bench) — the spend freeze is permanent until an owner "
            "decision record says otherwise",
            "no buyer-surface presence as a transfer item (the R407 "
            "external audit's verdict: 'Remove from buyer surface as a "
            "transfer item: P-13 (data-conditional; repositioned; make "
            "it permanent)')",
            "no re-promotion without the owner's counsel outcome on "
            "the narrow claim recorded against this file",
            "the lesson is FED FORWARD through the mechanism cemetery "
            "(entry " + CEM_ID + "): future candidate generation reads "
            "the cemetery (Art. LI) — the generator must treat "
            "'architecture-level novelty asserted without located-art "
            "claim charts' as a known failure pattern"
        ],
        "evidence_links": [
            "LEAD_PORTFOLIO_4/P13/NOVELTY_SEARCH_R406/"
            "NOVELTY_SEARCH_RESULT.json (7 live queries, located art "
            "with verbatim spans, verdict CONTESTED, full custody)",
            "LEAD_PORTFOLIO_4/P13/CLAIM_LEVEL_NOVELTY_COMPARISON_R407"
            ".json (the distinction-candidate testing; disposition: "
            "engineering spend FROZEN permanent)",
            "LEAD_PORTFOLIO_4/P13/KILLABILITY_ASSESSMENT.json (the two "
            "kill paths: cheap novelty review first, expensive bench "
            "second)",
            "LEAD_PORTFOLIO_4/P13/EXPERIMENT_PREREGISTRATION.json (the "
            "pre-registered 5-arm benchmark — sanctioned spend ONLY if "
            "the owner independently wants the fouling answer)",
            "MECHANISM_CEMETERY/CEMETERY.json (entry " + CEM_ID +
            " — the causal lesson, machine-readable)"
        ],
        "classification_note": "the package classification (REQUIRES_"
                              "EVIDENCE_REPAIR per FINAL_CLASSIFICATION "
                              "classifications.P13 with the R406 basis "
                              "updates) is unchanged by this record — "
                              "this record repositions the PACKAGE'S "
                              "ROLE (learning artifact), not its "
                              "evidence state"
    }


def build_cemetery_entry():
    return mc.CemeteryEntry(
        entry_id=CEM_ID,
        territory_id="lead-portfolio:P13:P-29",
        mechanism_name="paired-die common-mode-subtraction biopressure "
                       "sensor architecture (exposed active element + "
                       "shielded dummy element)",
        proposed_version="lead-portfolio-4 (R403 admission)",
        killed_at_version="R408 (external-audit response)",
        kill_reason="novelty: the architecture-level claim elements are "
                    "disclosed by located prior art (Seaver 2018 dual "
                    "matched-die implantable ICP sensor dissertation; "
                    "US4320664 1982 dummy-element bridge) — the "
                    "differentiation space collapses at the architecture "
                    "level; every tested distinction candidate is a "
                    "protocol/realization/target distinction, not a new "
                    "causal mechanism (Art. XLVI)",
        what_was_proposed="an architecture-level novelty position: the "
                          "paired-die differential pressure-sensor "
                          "architecture with common-mode error "
                          "subtraction as a transferable, fabricable "
                          "asset ($95-265K fab-NRE class gated behind "
                          "it)",
        why_it_failed="the novelty position was asserted BEFORE any "
                      "committed prior-art search existed for this "
                      "technology (retrieval absence, Art. XXI.2); when "
                      "the R406 hard gate forced the search, the same "
                      "causal architecture was located in public "
                      "1982-2018 art with verbatim claim spans; the "
                      "R407 claim-level comparison then tested every "
                      "distinction candidate and each failed the "
                      "mechanism-level test",
        reusable_lesson="architecture-level novelty claims require "
                        "claim-element differentiation against LOCATED "
                        "art BEFORE package promotion and before any "
                        "fabrication-budget commitment; a measurement-"
                        "method distinction (the difference channel as "
                        "fouling indicator) is a claim-shape question "
                        "for patent counsel — never an architecture "
                        "novelty fact; absence of a search artifact is "
                        "a GAP to repair, not a novelty finding",
        what_to_avoid="promoting a package to the buyer surface without "
                      "a committed search artifact; committing fab-NRE "
                      "($95-265K class) on a CONTESTED novelty "
                      "position; treating a MODEL_DERIVED drift target "
                      "or an engineering realization (0.07 mm MEMS "
                      "diaphragm) as a differentiating claim element",
        physical_constraint=None,
        evidence_sources=[
            "LEAD_PORTFOLIO_4/P13/NOVELTY_SEARCH_R406/"
            "NOVELTY_SEARCH_RESULT.json",
            "LEAD_PORTFOLIO_4/P13/CLAIM_LEVEL_NOVELTY_COMPARISON_R407"
            ".json",
            "LEAD_PORTFOLIO_4/P13/KILLABILITY_ASSESSMENT.json",
        ],
        epistemic_class="FAILURE_LESSON",
    )


def build_classification_extensions():
    p13_updates = [
        "LEARNING_ARTIFACT_R408.json records the repositioning: the "
        "causal chain of the architecture-level novelty collapse, the "
        "PERMANENT $95-265K fabrication-spend freeze, and the ONE "
        "remaining live item (the narrow patent-counsel question on "
        "the measurement-method claim)",
        "the causal lesson is fed into the mechanism cemetery (entry "
        + CEM_ID + ", FAILURE_LESSON class, chain-appended) so the "
        "generator reads it (Art. LI) — 'architecture-level novelty "
        "asserted without located-art claim charts' is now a recorded "
        "failure pattern",
        "no zombie behavior: no further engineering work, no buyer-"
        "surface presence as a transfer item, no re-promotion without "
        "the owner's counsel outcome"
    ]
    p08_updates = [
        "D2 is now an explicit owner-decision gate: "
        "LEAD_PORTFOLIO_4/P08/D2_OWNER_DECISION_GATE.json (options "
        "A/B/C/D with canonical-basis arithmetic; the thermal ceiling "
        "is UNKNOWN pending owner-extracted ANSI/IEC MPE numbers; eta "
        "alone can never close the gap)"
    ]
    return {
        "P13": {
            "state": "REQUIRES_EVIDENCE_REPAIR (unchanged) — but the "
                     "PACKAGE ROLE is repositioned: LEARNING ARTIFACT, "
                     "not a transfer item (R408 audit instruction 5)",
            "basis_updates": p13_updates,
        },
        "P08": {
            "state": "REQUIRES_ENGINEERING_REPAIR (unchanged)",
            "basis_updates": p08_updates,
        },
    }


def apply() -> int:
    LEARNING_PATH.write_text(
        json.dumps(build_learning_artifact(), indent=1,
                   ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {LEARNING_PATH.relative_to(ENGINE_ROOT)}")
    existing = json.loads(mc.CEMETERY_PATH.read_text(encoding="utf-8"))
    already = any(e.get("entry_id") == CEM_ID
                  for e in existing.get("entries", []))
    if already:
        print(f"cemetery entry {CEM_ID} already present — append "
              f"skipped (idempotent, Art. XI append-only)")
    else:
        mc.append_entries_to_cemetery_file([build_cemetery_entry()])
        print(f"appended cemetery entry {CEM_ID} (chain-maintaining path)")
    d = json.loads(CLASSIFICATION_PATH.read_text(encoding="utf-8"))
    d.setdefault("r408_extensions", {}).update(
        build_classification_extensions())
    CLASSIFICATION_PATH.write_text(
        json.dumps(d, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8")
    print(f"wired r408_extensions in "
          f"{CLASSIFICATION_PATH.relative_to(ENGINE_ROOT)}")
    return 0


def check() -> int:
    la = json.loads(LEARNING_PATH.read_text(encoding="utf-8"))
    assert la["artifact_class"].startswith("LEARNING ARTIFACT")
    assert la["fabrication_spend"]["status"].startswith("FROZEN")
    assert "measurement-method claim" in \
        la["the_one_remaining_live_item"]["item"]
    assert len(la["the_causal_chain"]) == 4
    cem = json.loads(mc.CEMETERY_PATH.read_text(encoding="utf-8"))
    hit = [e for e in cem["entries"] if e.get("entry_id") == CEM_ID]
    assert len(hit) == 1, "cemetery entry missing"
    from premium_package_factory.r374 import pathway
    assert pathway._chain_verify(cem)["valid"] is True, \
        "cemetery chain invalid after append"
    fc = json.loads(CLASSIFICATION_PATH.read_text(encoding="utf-8"))
    assert "P13" in fc.get("r408_extensions", {})
    assert "P08" in fc.get("r408_extensions", {})
    print("check: learning artifact + cemetery entry + classification "
          "wiring all verified")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="verify the applied state only")
    args = ap.parse_args()
    return check() if args.check else apply()


if __name__ == "__main__":
    raise SystemExit(main())
