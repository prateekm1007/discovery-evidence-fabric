#!/usr/bin/env python3
"""scripts/r411_run_campaign.py — the R411 campaign driver.

Usage:
    python3 scripts/r411_run_campaign.py <stage> [limit]

Stages (resumable; each invocation processes work units and checkpoints):
    init            F0: freeze matrix + scoring contract
    retrieval [n]   F1: n domain fabric calls (default 4 per invocation)
    extraction [n]  F2: n domain LLM extractions (default 3)
    collision       F3
    scoring         F4
    shortlist       F4b
    priorart [n]    F5: n finalist prior-art searches (default 2)
    calibrate       F7a: attacker calibration
    attack [n]      F7: n finalist attacks (default 3)
    selection       F8
    dossiers        F9+F10: dossier + buyer packages + cemetery
    records         F11: run record + report
    status          print state

The gateway is started as a child process for LLM stages and terminated
on exit (the sandbox reaps background processes between invocations).
"""
from __future__ import annotations

import json
import os
import sys
import time

sys.path.insert(0, "/home/z/my-project/audit_ws/repo")
sys.path.insert(0, "/home/z/my-project/scripts")

REPO = "/home/z/my-project/audit_ws/repo"
os.chdir(REPO)

from discovery_fabric.engine.adapters import load_credentials  # noqa: E402

load_credentials()

from discovery_fabric.r411 import Campaign  # noqa: E402
from discovery_fabric.r411.campaign import (  # noqa: E402
    CAMPAIGN_VERSION, DEFAULT_RUN_DIR)


def _with_gateway(fn):
    """Run fn with the LLM gateway up (child process, torn down after)."""
    from r411_gateway_helper import start_gateway
    gw = start_gateway()
    try:
        return fn()
    finally:
        gw.terminate()
        try:
            gw.wait(timeout=10)
        except Exception:
            gw.kill()


def main() -> int:
    stage = sys.argv[1] if len(sys.argv) > 1 else "status"
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else None
    c = Campaign(REPO)

    if stage == "status":
        print(json.dumps(c.state, indent=1))
        return 0

    if stage == "init":
        c.materialize_frozen_inputs()
        c.state["stage"] = "F1_retrieval"
        c.save()
        print("F0 done: matrix + scoring contract frozen")
        return 0

    if stage == "retrieval":
        n = limit or 4
        targets = [t for t in c.retrieval_targets()
                   if t["domain_id"] not in c.state["retrieval_done"]]
        done = 0
        for entry in targets[:n]:
            snap = c.run_retrieval_for(entry)
            print(f"F1 {entry['domain_id']}: {len(snap['pool'])} records "
                  f"({snap['elapsed_s']}s) "
                  f"sources_ok="
                  f"{snap['fabric_report'].get('retrieval_stats', {}).get('sources_succeeded')}")
            done += 1
        print(f"F1 batch done: {done} domains "
              f"({len(c.state['retrieval_done'])}/"
              f"{len(c.retrieval_targets())})")
        return 0

    if stage == "extraction":
        n = limit or 3

        def work():
            targets = [t for t in c.retrieval_targets()
                       if t["domain_id"] not in
                       c.state["extraction_done"] and
                       t["domain_id"] in c.state["retrieval_done"]]
            done = 0
            for entry in targets[:n]:
                res = c.run_extraction_for(entry)
                print(f"F2 {entry['domain_id']}: "
                      f"{len(res.get('accepted') or [])} accepted, "
                      f"{len(res.get('rejected') or [])} rejected, "
                      f"status={res.get('status')}")
                done += 1
            print(f"F2 batch done: {done} domains "
                  f"({len(c.state['extraction_done'])}/"
                  f"{len(c.state['retrieval_done'])} retrieved)")
        return _with_gateway(work) or 0

    if stage == "collision":
        dedup = c.run_collision()
        print(f"F3 done: {dedup['survivor_count']} survive "
              f"(input {dedup['input_count']})")
        return 0

    if stage == "scoring":
        res = c.run_scoring()
        print(f"F4 done: {res['n']} scored; "
              f"{c.state['scoring_counts']}")
        return 0

    if stage == "shortlist":
        picked = c.run_shortlist()
        print(f"F4b done: {len(picked)} shortlisted: "
              f"{[p['candidate_id'] for p in picked]}")
        return 0

    if stage == "priorart":
        n = limit or 2
        shortlist = json.load(open(os.path.join(
            c.run_dir, "shortlist.json")))
        todo = [x for x in shortlist
                if x["candidate_id"] not in c.state["prior_art_done"]]
        for cand in todo[:n]:
            pa = c.run_prior_art_for(cand)
            print(f"F5 {cand['candidate_id']}: "
                  f"distance={pa['closest_prior_art']['distance_class']}, "
                  f"relevant={len(pa['relevant_records'])}, "
                  f"secondary-only={pa['terminology_recovery']['total_unique_secondary_only']}")
        print(f"F5 progress: {len(c.state['prior_art_done'])}/"
              f"{len(shortlist)}")
        return 0

    if stage == "calibrate":

        def work():
            cal = c.run_attack_calibration()
            print(f"F7a calibration: {cal['n_killed_as_expected']}/"
                  f"{cal['n_defects']} known defects killed as expected")
        return _with_gateway(work) or 0

    if stage == "attack":
        n = limit or 3

        def work():
            shortlist = json.load(open(os.path.join(
                c.run_dir, "shortlist.json")))
            todo = [x for x in shortlist
                    if x["candidate_id"] not in c.state["attack_done"] and
                    x["candidate_id"] in c.state["prior_art_done"]]
            for cand in todo[:n]:
                pa = json.load(open(os.path.join(
                    c.run_dir, "prior_art",
                    f"{cand['candidate_id']}.json")))
                atk = c.run_attack_for(cand, pa)
                print(f"F7 {cand['candidate_id']}: verdict="
                      f"{atk.get('verdict')} "
                      f"kills={atk.get('kill_surfaces')} "
                      f"wounds={atk.get('wound_surfaces')} "
                      f"independence={atk.get('independence_mode')}")
            print(f"F7 progress: {len(c.state['attack_done'])}/"
                  f"{len(shortlist)}")
        return _with_gateway(work) or 0

    if stage == "selection":
        res = c.run_selection()
        print(f"F8 done: {len(res['selected'])} selected, "
              f"{len(res['rejected'])} rejected")
        for r in res["rejected"][:8]:
            print(f"  rejected: {r['candidate'].get('technology_name', '')[:60]}"
                  f" — {r.get('rejection_reason', '')[:80]}")
        return 0

    if stage == "dossiers":
        return _do_dossiers(c)

    if stage == "records":
        return _do_records(c)

    print(f"unknown stage: {stage}")
    return 1


def _do_dossiers(c: Campaign) -> int:
    from discovery_fabric.r411.dossier import build_dossier
    from discovery_fabric.r411.buyer_package import write_buyer_package

    sel = json.load(open(os.path.join(c.run_dir, "selection.json")))
    full = sel["full_records"]
    matrix = json.load(open(c.state["domain_matrix"]["path"]))
    engine_commit = c.state["engine_commit"]

    pools_by_domain = {}
    for dom in c.state["extraction_done"]:
        p = os.path.join(c.run_dir, "evidence", f"{dom}.json")
        if os.path.exists(p):
            pools_by_domain[dom] = json.load(open(p))["pool"]

    buyer_manifest = []
    for idx, rec in enumerate([r for r in full
                               if r["candidate"]["candidate_id"]
                               in sel["selected"]], start=1):
        cand = rec["candidate"]
        pool = pools_by_domain.get(cand["domain_id"], [])
        # the evidence snapshot hash for this dossier = the domain pool
        # hash the candidate was extracted from (Art. XLIV)
        camp_meta = {
            "engine_commit": engine_commit,
            "fabric_version": "RETRIEVAL_FABRIC_V2",
            "evidence_snapshot_sha256": json.load(open(os.path.join(
                c.run_dir, "candidates", f"{cand['domain_id']}.json"))
            ).get("pool_sha256"),
            "domain_matrix_sha256": matrix["matrix_sha256"],
            "scoring_contract_sha256": json.load(open(
                c.state["scoring_contract"]["path"]))["contract_sha256"],
        }
        dossier = build_dossier(cand, pool, rec["funnel"], camp_meta,
                                dossier_index=idx)
        dp = os.path.join(c.run_dir, "dossiers",
                          f"D{idx}_{cand['candidate_id']}.json")
        os.makedirs(os.path.dirname(dp), exist_ok=True)
        json.dump(dossier, open(dp, "w"), indent=1)
        out = os.path.join(REPO, "LEAD_PORTFOLIO_4", "R411_DISCOVERED")
        manifest = write_buyer_package(out, dossier, camp_meta, idx)
        buyer_manifest.append(manifest)
        print(f"F9/F10 D{idx}: {dossier['technology_name']} -> "
              f"{manifest['folder']} status={dossier['status']}")

    # cemetery entries for the killed/rejected (s14 + Art. LI)
    _append_cemetery(c, sel)
    c.state["dossiers_done"] = True
    c.state["buyer_done"] = True
    c.state["buyer_manifest"] = buyer_manifest
    c.save()
    print("F9/F10 done: dossiers + buyer packages + cemetery entries")
    return 0


def _append_cemetery(c: Campaign, sel: dict) -> None:
    """Killed candidates -> MECHANISM_CEMETERY with rejection reasons
    (s14; the chain extension is the orchestrator's own machinery)."""
    from orchestrator.mechanism_cemetery import (
        append_entries_to_cemetery_file)
    entries = []
    for r in sel.get("rejected") or []:
        cand = None
        for rec in sel["full_records"]:
            if rec["candidate"]["candidate_id"] == r["candidate_id"]:
                cand = rec["candidate"]
                break
        if not cand:
            continue
        funnel = {}
        for rec in sel["full_records"]:
            if rec["candidate"]["candidate_id"] == r["candidate_id"]:
                funnel = rec["funnel"]
                break
        if not r.get("reason") or "KILLED" not in str(r.get("reason")):
            continue  # only true KILLS enter the cemetery; quota rejections
            # are recorded in the run record (a quota rejection is not a
            # mechanism-death — putting it in the cemetery would poison
            # future search with non-failures)
        entries.append({
            "territory_id": f"r411:{r['candidate_id']}",
            "mechanism_name": cand.get("technology_name") or
                              r["candidate_id"],
            "proposed_version": CAMPAIGN_VERSION,
            "killed_at_version": CAMPAIGN_VERSION,
            "kill_reason": str(r.get("reason"))[:300],
            "what_was_proposed": " -> ".join(
                cand.get("causal_chain") or [])[:500],
            "why_it_failed": str(
                (funnel.get("attack") or {}).get("final_objection") or
                r.get("reason"))[:500],
            "reusable_lesson": (
                "R411 attacker tournament: this causal configuration did "
                "not survive adversarial attack; future generation must "
                "address the recorded objection before re-proposing"),
            "what_to_avoid": str(
                (funnel.get("attack") or {}).get("kill_surfaces"))[:300],
            "physical_constraint": "",
            "evidence_sources": [str(x) for x in
                                 (cand.get("evidence_refs") or [])][:8],
            "epistemic_class": "FAILURE_LESSON",
        })
    if entries:
        append_entries_to_cemetery_file(entries)
    print(f"cemetery: {len(entries)} entries appended "
          f"(killed only; quota rejections stay in the run record)")


def _do_records(c: Campaign) -> int:
    """F11: R411_DISCOVERY_RUN.json + R411_DISCOVERY_REPORT.md."""
    from discovery_fabric.r411.report import write_run_record_and_report
    write_run_record_and_report(c)
    c.state["records_done"] = True
    c.state["stopped"] = True
    c.save()
    print("F11 done: R411_DISCOVERY_RUN.json + R411_DISCOVERY_REPORT.md")
    print("STOP CONDITION REACHED (s23): no spend, no hardware, no buyer "
          "contact, no physical validation")
    return 0


if __name__ == "__main__":
    sys.exit(main())
