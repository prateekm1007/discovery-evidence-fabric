#!/usr/bin/env python
"""The L8 discovery campaign — 15 territories across the directive's
problem-space targets (CEO lifecycle directive 2026-08-29, point 8):

    01-05 Orthopedics
    06-09 Cardiovascular / Vascular
    10-12 Neurovascular
    13-14 Limb / Osseointegration
    15 Ophthalmology

"These are problem-space targets, not predetermined inventions. The
engine must decide which candidates deserve dossiers. Let the engine
kill weak spaces."

For every territory the universal FAILURE->GAP->OPPORTUNITY operator
runs the full 9-step chain. Kill decisions are the ENGINE's:

  BLOCKED (provider failure)             -> territory result BLOCKED
                                            (not the territory's fault;
                                            rerunnable)
  PROBLEM_NOT_DOCUMENTED                 -> KILLED (PROBLEM_EXISTENCE_FAIL)
  SIGNAL_BELOW_TRIAGE_THRESHOLD          -> KILLED (PROBLEM_EXISTENCE_UNDETERMINED)
  candidate with NO alternative
    physical principles                  -> KILLED (NO_MECHANISM_DIRECTION)
  candidate with NO cross-domain
    transfer evidence                    -> KILLED (NO_TRANSFER_SUPPORT)
  otherwise                              -> SURVIVOR (ranked)

Every killed candidate goes to the cemetery — the existing
MECHANISM_CEMETERY (compatible schema, engine-consultable) AND the
campaign report (the directive's exact 7 fields: candidate_id,
failure_reason, evidence, attacks, kill_condition, date,
reusable_constraints). "A failed candidate is not deleted. It becomes
future search knowledge."

Survivors are ranked DOSSIER_CANDIDATES — ranked, NOT dossiered: the
acceptance chain (prior art -> adversarial attack -> killer experiment
-> surviving invention) is a separate, later stage (Art. XXVIII: no
silent semantic promotion from candidate to invention).

Art. XXVI disclosure: BUILDER-MEASURED. Reproduction:

    python scripts/l8_campaign.py [--timeout 30] [--only 01,02]

Usage:
    python scripts/l8_campaign.py                # all 15 territories
    python scripts/l8_campaign.py --only 01,06   # subset
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.discovery_modes.opportunity import (  # noqa: E402
    discover_opportunity,
)
from orchestrator.mechanism_cemetery import (  # noqa: E402
    CemeteryEntry, append_entries_to_cemetery_file, load_cemetery,
)

OUT_DIR = REPO_ROOT / "discovery_campaigns" / "CAMPAIGN_L8_2026-08-29"

#: The 15 territories: problem-space targets (device + domain).
TERRITORIES = [
    {"id": "01", "campaign_slot": "Orthopedics", "domain": "ORTHOPEDICS",
     "device_query": "hip prosthesis"},
    {"id": "02", "campaign_slot": "Orthopedics", "domain": "ORTHOPEDICS",
     "device_query": "knee prosthesis"},
    {"id": "03", "campaign_slot": "Orthopedics", "domain": "ORTHOPEDICS",
     "device_query": "pedicle screw"},
    {"id": "04", "campaign_slot": "Orthopedics", "domain": "ORTHOPEDICS",
     "device_query": "shoulder prosthesis"},
    {"id": "05", "campaign_slot": "Orthopedics", "domain": "ORTHOPEDICS",
     "device_query": "spinal fusion interbody cage"},
    {"id": "06", "campaign_slot": "Cardiovascular/Vascular", "domain": "CARDIOVASCULAR",
     "device_query": "coronary stent"},
    {"id": "07", "campaign_slot": "Cardiovascular/Vascular", "domain": "CARDIOVASCULAR",
     "device_query": "heart valve prosthesis"},
    {"id": "08", "campaign_slot": "Cardiovascular/Vascular", "domain": "CARDIOVASCULAR",
     "device_query": "pacemaker lead"},
    {"id": "09", "campaign_slot": "Cardiovascular/Vascular", "domain": "CARDIOVASCULAR",
     "device_query": "venous filter"},
    {"id": "10", "campaign_slot": "Neurovascular", "domain": "NEUROVASCULAR",
     "device_query": "aneurysm clip"},
    {"id": "11", "campaign_slot": "Neurovascular", "domain": "NEUROVASCULAR",
     "device_query": "flow diverter"},
    {"id": "12", "campaign_slot": "Neurovascular", "domain": "NEUROVASCULAR",
     "device_query": "intracranial stent"},
    {"id": "13", "campaign_slot": "Limb/Osseointegration", "domain": "ORTHOPEDICS",
     "device_query": "osseointegration implant"},
    {"id": "14", "campaign_slot": "Limb/Osseointegration", "domain": "ORTHOPEDICS",
     "device_query": "limb prosthesis"},
    {"id": "15", "campaign_slot": "Ophthalmology", "domain": "OPHTHALMOLOGY",
     "device_query": "intraocular lens"},
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _campaign_cemetery_entry(territory, cand: dict, kill: dict) -> dict:
    """The directive's exact 7 fields for a killed campaign candidate.

    ``territory`` may be the territory spec (id/...) or a run outcome
    (territory_id/...) — both carry the needed fields."""
    return {
        "candidate_id": cand.get("candidate_id"),
        "failure_reason": kill["failure_reason"],
        "evidence": {
            "operator_run": OUT_DIR.name,
            "territory": territory.get("id") or territory.get("territory_id"),
            "device_query": territory.get("device_query"),
            "chain_steps": cand.get("_chain_step_summary", []),
            "problem_epistemic_class": cand.get("problem", {}).get("epistemic_class"),
            "why_they_fail_epistemic_class": (
                (cand.get("chain_detail", {}).get("why_they_fail", {})
                 or {}).get("epistemic_class")),
            "provenance": {
                "maude_query": (cand.get("chain_detail", {})
                                .get("attempted_solutions", {})
                                .get("query")),
            },
        },
        "attacks": kill["attacks"],
        "kill_condition": kill["kill_condition"],
        "date": _now(),
        "reusable_constraints": kill["reusable_constraints"],
    }


def _canonical_cemetery_entry(territory, cand: dict, kill: dict) -> CemeteryEntry:
    """The same kill in the existing cemetery's schema so the engine
    consults it before any future candidate (compatible fields only —
    load_cemetery() constructs CemeteryEntry(**entry))."""
    tid = territory.get("id") or territory.get("territory_id")
    return CemeteryEntry(
        entry_id=kill["entry_id"],
        territory_id=f"L8-{tid}",
        mechanism_name=(cand.get("mechanism_hypothesis", {})
                        .get("physical_principle", "unresolved")
                        + f" for {territory.get('device_query', '')}"),
        proposed_version="L8-campaign",
        killed_at_version=f"L8-{_now()[:10]}",
        kill_reason=kill["canonical_kill_reason"],
        what_was_proposed=(
            f"Universal-operator candidate for {territory.get('device_query', '')}: "
            + str((cand.get("problem", {}) or {}).get("constraint", ""))[:300]),
        why_it_failed=kill["failure_reason"],
        reusable_lesson=kill["reusable_constraints"][0] if kill["reusable_constraints"] else "",
        what_to_avoid=kill["what_to_avoid"],
        physical_constraint=None,
        evidence_sources=[OUT_DIR.name + "/CAMPAIGN_REPORT.json"],
        epistemic_class="FAILURE_LESSON",  # informational: discovery-gate
        # kills, not physics proofs — never hard-block future work
    )


def run_territory(territory: dict, timeout: int) -> dict:
    """Run the 9-step operator for one territory and let the ENGINE
    decide: kill or survive."""
    result = discover_opportunity(territory["device_query"],
                                  territory["domain"], timeout=timeout)
    outcome = {
        "territory_id": territory["id"],
        "campaign_slot": territory["campaign_slot"],
        "domain": territory["domain"],
        "device_query": territory["device_query"],
        "blocked": result["blocked"],
        "chain_steps": result["chain_steps"],
        "engine_decision": None,
        "candidates": [],
        "kills": [],
        "raw": result,
    }

    if result["blocked"]:
        outcome["engine_decision"] = "BLOCKED_PROVIDER_FAILURE"
        outcome["note"] = ("Transport-level provider failure — territory "
                           "NOT killed (Art. XXI.3: provider failure is not "
                           "absence). Rerunnable.")
        return outcome

    gate_steps = [s for s in result["chain_steps"]
                  if s["step"] == "problem_existence_gate"]
    if gate_steps:
        status = gate_steps[0]["status"]
        if status == "PROBLEM_NOT_DOCUMENTED":
            outcome["engine_decision"] = "KILLED"
            outcome["kills"].append({
                "candidate_id": f"territory:{territory['id']}:{territory['device_query']}",
                "failure_reason": "PROBLEM_NOT_DOCUMENTED: both failure "
                                  "providers answered definitively with "
                                  "zero records (Art. XX problem-existence "
                                  "gate).",
                "evidence": {"chain_steps": result["chain_steps"]},
                "attacks": [
                    "Re-phrased retrieval (synonyms) returned no failure "
                    "documentation either",
                    "Problem-existence gate refuses to invent a failure "
                    "mode to work on",
                ],
                "kill_condition": "No documented real-world failure for "
                                  "this device class in MAUDE/recall",
                "kill_condition_class": "PROBLEM_EXISTENCE_FAIL",
                "reusable_constraints": [
                    "Do not pursue invention work in this territory until "
                    "failure documentation exists",
                    "A territory without documented failures is a "
                    "signal-free space, not an opportunity",
                ],
                "what_to_avoid": "Inventing hypothetical failure modes to "
                                 "justify mechanism work (Art. XX)",
            })
            return outcome
        if status == "SIGNAL_BELOW_TRIAGE_THRESHOLD":
            outcome["engine_decision"] = "KILLED"
            outcome["kills"].append({
                "candidate_id": f"territory:{territory['id']}:{territory['device_query']}",
                "failure_reason": "SIGNAL_BELOW_TRIAGE_THRESHOLD: reports "
                                  "exist but no mechanism cluster meets the "
                                  "declared recurrence triage threshold.",
                "evidence": {"chain_steps": result["chain_steps"]},
                "attacks": [
                    "Recurrence triage is MODEL_DERIVED and declared "
                    "(S5 RECURRENCE_THRESHOLD_BASIS)",
                    "Lowering the threshold would admit noise, not signal",
                ],
                "kill_condition": "No recurring mechanism cluster at the "
                                  "declared triage threshold",
                "kill_condition_class": "PROBLEM_EXISTENCE_UNDETERMINED",
                "reusable_constraints": [
                    "Weak single-report signals are not a basis for "
                    "constraint derivation",
                    "Revisit only if independent failure evidence "
                    "accumulates",
                ],
                "what_to_avoid": "Treating isolated reports as recurring "
                                 "mechanisms",
            })
            return outcome

    # per-candidate engine decisions
    survivors = []
    for cand in result["candidates"]:
        detail = cand.get("chain_detail", {})
        principles = detail.get("alternative_physical_principles", [])
        transfer = (detail.get("cross_domain_transfer", {})
                    .get("per_domain", {}))
        transfer_domains = [d for d, v in transfer.items()
                            if v.get("status") == "TRANSFER_EVIDENCE"]
        if not principles:
            outcome["kills"].append({
                "candidate_id": cand["candidate_id"],
                "failure_reason": "NO_MECHANISM_DIRECTION: the constraint "
                                  "engages no un-attempted physical "
                                  "principle in the taxonomy.",
                "evidence": {
                    "constraint": (detail.get("constraint", {})
                                   .get("constraint_statement")),
                    "attempted_solutions_retrieved": (
                        detail.get("attempted_solutions", {})
                        .get("literature", {}).get("retrieved")),
                },
                "attacks": [
                    "Every principle capable of addressing the constraint "
                    "is already engaged by retrieved attempts",
                    "The taxonomy may lack an exotic principle — kill is "
                    "bounded by taxonomy coverage (declared limitation)",
                ],
                "kill_condition": "No alternative physical principle "
                                  "available for this constraint",
                "kill_condition_class": "PROBLEM_EXISTENCE_UNDETERMINED",
                "reusable_constraints": [
                    "Constraint is heavily worked: novelty requires "
                    "principles outside the current taxonomy",
                ],
                "what_to_avoid": "Proposing recombination of already-"
                                 "attempted principles as novelty",
            })
            continue
        if not transfer_domains:
            outcome["kills"].append({
                "candidate_id": cand["candidate_id"],
                "failure_reason": "NO_TRANSFER_SUPPORT: no other directive "
                                  "domain shows measurable evidence of the "
                                  "same constraint class.",
                "evidence": {
                    "constraint_terms": (detail.get("cross_domain_transfer", {})
                                         .get("constraint_terms")),
                    "per_domain": {d: v.get("status")
                                   for d, v in transfer.items()},
                },
                "attacks": [
                    "All four other directive domains queried; zero "
                    "title-level constraint overlap",
                    "Cross-domain evidence is a supporting signal — its "
                    "absence weakens, not kills, physics; the engine "
                    "still kills for dossier-priority purposes",
                ],
                "kill_condition": "No cross-domain transfer evidence for "
                                  "the constraint class",
                "kill_condition_class": "PROBLEM_EXISTENCE_UNDETERMINED",
                "reusable_constraints": [
                    "Domain-isolated constraints need stronger in-domain "
                    "evidence before dossier work",
                ],
                "what_to_avoid": "Assuming cross-domain transfer without "
                                 "measured evidence",
            })
            continue
        # SURVIVOR: rank by evidence strength
        why = detail.get("why_they_fail", {}) or {}
        problem_signal = 0
        for s in result["chain_steps"]:
            if s.get("step") == "real_world_failure":
                problem_signal = s.get("maude_records", 0) + s.get("recall_records", 0)
        survivors.append({
            **cand,
            "survivor_score": {
                "problem_signal_records": problem_signal,
                "root_cause_evidence": len(why.get("root_causes", [])),
                "narrative_evidence": len(why.get("narratives", [])),
                "transfer_domains": len(transfer_domains),
                "principles": len(principles),
            },
        })
    outcome["candidates"] = [
        {k: v for k, v in c.items() if k != "chain_detail"}
        for c in survivors]
    # keep detail for the report payload
    outcome["survivor_details"] = [
        {"candidate_id": c["candidate_id"], "chain_detail": c["chain_detail"]}
        for c in survivors]
    if survivors or outcome["kills"]:
        outcome["engine_decision"] = (
            "SURVIVORS" if survivors else
            ("KILLED" if outcome["kills"] else "NO_RECURRING_SIGNAL"))
    else:
        outcome["engine_decision"] = "NO_RECURRING_SIGNAL"
    return outcome


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--only", type=str, default=None,
                        help="comma-separated territory ids, e.g. 01,06")
    args = parser.parse_args()

    only = set(args.only.split(",")) if args.only else None
    territories = [t for t in TERRITORIES if only is None or t["id"] in only]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    for t in territories:
        print(f"[{t['id']}] {t['device_query']} ({t['domain']}) ...",
              flush=True)
        try:
            outcome = run_territory(t, args.timeout)
        except Exception as e:  # noqa: BLE001 — surfaced, never swallowed
            outcome = {
                "territory_id": t["id"], "device_query": t["device_query"],
                "engine_decision": "ERROR", "error": f"{type(e).__name__}: {e}",
                "kills": [], "candidates": [], "chain_steps": [],
            }
        n_kills = len(outcome.get("kills", []))
        n_surv = len(outcome.get("candidates", []))
        print(f"    -> {outcome['engine_decision']} "
              f"(kills={n_kills}, survivors={n_surv})", flush=True)
        results.append(outcome)

    # ---- assemble the campaign report ------------------------------------
    kills_flat = []
    for r in results:
        for k in r.get("kills", []):
            k["territory_id"] = r["territory_id"]
            k["campaign_slot"] = r["campaign_slot"]
            k["device_query"] = r["device_query"]
            kills_flat.append(k)

    survivors_flat = []
    for r in results:
        for c in r.get("candidates", []):
            survivors_flat.append({
                "territory_id": r["territory_id"],
                "campaign_slot": r["campaign_slot"],
                "device_query": r["device_query"],
                "candidate_id": c["candidate_id"],
                "principle": c["mechanism_hypothesis"]["physical_principle"],
                "principle_class": c["mechanism_hypothesis"]["epistemic_class"],
                "transfer_domains": c["cross_domain_evidence"]["transfer_domains"],
                "kill_conditions": [k["condition"] for k in c["kill_conditions"]],
                "survivor_score": c["survivor_score"],
                "strongest_alternative_explanation":
                    c["strongest_alternative_explanation"],
                "not_a_novelty_determination": True,
            })
    # rank: transfer domains, then evidence, then problem signal
    survivors_flat.sort(key=lambda s: (
        -s["survivor_score"]["transfer_domains"],
        -(s["survivor_score"]["root_cause_evidence"]
          + s["survivor_score"]["narrative_evidence"]),
        -s["survivor_score"]["problem_signal_records"]))

    # ---- write the directive-format cemetery entries ---------------------
    cemetery_directive_format = []
    canonical_new_entries = []
    existing = load_cemetery()
    existing_ids = {e.entry_id for e in existing}
    seq = 800  # L8 campaign namespace: CE-8xx
    for r in results:
        for k in r.get("kills", []):
            seq += 1
            entry_id = f"CE-{seq}"
            while entry_id in existing_ids:
                seq += 1
                entry_id = f"CE-{seq}"
            kill = {
                **k,
                "entry_id": entry_id,
                "failure_reason": k["failure_reason"],
                "attacks": k["attacks"],
                "kill_condition": k["kill_condition"],
                "reusable_constraints": k["reusable_constraints"],
                "canonical_kill_reason": k.get("kill_condition_class",
                                               "PROBLEM_EXISTENCE_UNDETERMINED"),
                "what_to_avoid": k.get("what_to_avoid", ""),
                "candidate": {"candidate_id": k.get("candidate_id"),
                              "mechanism_hypothesis": {},
                              "problem": {},
                              "chain_detail": k.get("evidence", {})},
                "_chain_step_summary": [
                    {"step": s.get("step"), "status": s.get("status")}
                    for s in (k.get("evidence", {}).get("chain_steps") or [])
                    if isinstance(s, dict)
                ][:8],
            }
            cemetery_directive_format.append(
                _campaign_cemetery_entry(r, kill, kill))
            canonical_new_entries.append(
                _canonical_cemetery_entry(r, kill, kill))

    # persist the canonical cemetery (history-preserving append: the
    # file's existing entries keep their append-only history fields)
    if canonical_new_entries:
        append_entries_to_cemetery_file(canonical_new_entries)

    report = {
        "artifact": "L8_DISCOVERY_CAMPAIGN_REPORT",
        "campaign": "15-territory medical-device campaign (CEO lifecycle "
                    "directive 2026-08-29)",
        "run_timestamp": _now(),
        "territories": [
            {"id": t["id"], "slot": t["campaign_slot"],
             "domain": t["domain"], "query": t["device_query"]}
            for t in territories],
        "engine_decisions": [
            {"territory_id": r["territory_id"],
             "device_query": r["device_query"],
             "decision": r["engine_decision"],
             "kills": len(r.get("kills", [])),
             "survivors": len(r.get("candidates", []))}
            for r in results],
        "summary": {
            "territories_run": len(results),
            "blocked": sum(1 for r in results if r["engine_decision"]
                           == "BLOCKED_PROVIDER_FAILURE"),
            "killed_territories": sum(1 for r in results
                                      if r["engine_decision"] == "KILLED"),
            "candidates_killed": len(kills_flat),
            "survivors": len(survivors_flat),
        },
        "cemetery_entries_directive_format": cemetery_directive_format,
        "dossier_candidates_ranked": survivors_flat,
        "dossier_promotion_note": (
            "Survivors are RANKED DOSSIER CANDIDATES only. Promotion to a "
            "dossier requires the full acceptance chain (prior art -> "
            "adversarial attack -> killer experiment -> surviving "
            "invention -> engineering specification -> dossier -> buyer "
            "zip -> portfolio repository). No candidate here has passed "
            "that chain (Art. XXVIII — no silent semantic promotion)."
        ),
        "builder_measured_disclosure": {
            "art_xxvi": "BUILDER-MEASURED. Reproduction: "
                        "python scripts/l8_campaign.py",
            "reproduction": "python scripts/l8_campaign.py",
        },
        "results": results,
    }
    out = OUT_DIR / "CAMPAIGN_REPORT.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)

    print("\n" + "=" * 70)
    print(f"CAMPAIGN SUMMARY: {len(results)} territories | "
          f"{len(kills_flat)} candidates killed | "
          f"{len(survivors_flat)} survivors")
    for r in results:
        print(f"  [{r['territory_id']}] {r['device_query']:32s} "
              f"{r['engine_decision']}")
    if survivors_flat:
        print("\nTOP DOSSIER CANDIDATES (ranked, NOT dossiered):")
        for s in survivors_flat[:5]:
            print(f"  {s['territory_id']} {s['device_query']:30s} "
                  f"{s['principle']:28s} transfer={len(s['transfer_domains'])}")
    print(f"\nreport: {out}")
    print(f"cemetery: +{len(canonical_new_entries)} entries appended")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
