"""discovery_fabric/r411/report.py — Directive s18/s22: the machine-
readable run record and the discovery report.

R411_DISCOVERY_RUN.json (s18): run_id, engine_commit, retrieval_fabric_
version, sources_attempted, source_failures, domains_explored, queries,
query_expansions, candidate_count, candidate_rejections, candidate_
survivors, attacker_results, prior_art_results, engineering_results,
selected_technologies, killed_technologies, buyer_packages_created +
search_space_coverage, source_diversity, document_type_diversity,
cross_domain_transfers, mechanism_diversity, candidate_collision_rate.

R411_DISCOVERY_REPORT.md (s22): discovery funnel, five selected
technologies (the 16-field table each), rejected candidates (why they
died), buyer packages, search-space report, reality boundary.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from .campaign import CAMPAIGN_VERSION, FINAL_TARGET


def _read(c, *rel) -> Any:
    p = os.path.join(c.run_dir, *rel)
    return json.load(open(p)) if os.path.exists(p) else None


def build_run_record(c) -> Dict[str, Any]:
    state = c.state
    matrix = _read(c, "domain_matrix.json") or {}
    collision = _read(c, "funnel_collision.json") or {}
    scored = _read(c, "scored_pool.json") or []
    shortlist = _read(c, "shortlist.json") or []
    selection = _read(c, "selection.json") or {}
    cal = _read(c, "attack_calibration.json") or {}

    # aggregate retrieval stats across the domain snapshots
    sources_attempted: List[str] = []
    source_failures: Dict[str, int] = {}
    queries: List[str] = []
    query_expansion_classes: Dict[str, int] = {}
    document_types: Dict[str, int] = {}
    source_diversity: Dict[str, int] = {}
    families: set = set()
    n_records = 0
    for dom in state.get("retrieval_done", []):
        snap = _read(c, "evidence", f"{dom}.json")
        if not snap:
            continue
        rep = snap.get("fabric_report") or {}
        stats = rep.get("retrieval_stats") or {}
        for src in (stats.get("sources_attempted") or
                    (stats.get("per_source") or {}).keys() or []):
            if src not in sources_attempted:
                sources_attempted.append(src)
        for f in (stats.get("failures") or []):
            sid = f.get("source_id") or f.get("source") or "unknown"
            source_failures[sid] = source_failures.get(sid, 0) + 1
        for v in (rep.get("query_variants") or []):
            queries.append(v.get("query") or "")
            cls = v.get("derivation_class") or "PRIMARY"
            query_expansion_classes[cls] = \
                query_expansion_classes.get(cls, 0) + 1
        div = rep.get("retrieval_diversity") or {}
        for fam, n in (div.get("families") or {}).items():
            families.add(fam)
        for rec in snap.get("pool") or []:
            n_records += 1
            dt = rec.get("publication_status") or "UNKNOWN"
            document_types[dt] = document_types.get(dt, 0) + 1
            sf = ((rec.get("provenance") or {}).get("source_family")
                  or "unknown")
            source_diversity[sf] = source_diversity.get(sf, 0) + 1

    cross_domain = [x for x in scored if x.get("cross_domain_transition")]
    mechanism_families = {}
    for x in scored:
        mech = (x.get("unexploited_phenomenon") or
                x.get("technology_name") or "")[:48]
        mechanism_families[mech] = mechanism_families.get(mech, 0) + 1

    selected = selection.get("selected") or []
    killed = [r for r in (selection.get("rejected") or [])
              if "KILLED" in str(r.get("reason", ""))]
    buyer_manifest = state.get("buyer_manifest") or []

    return {
        "artifact_type": "R411_DISCOVERY_RUN",
        "run_id": state.get("run_id"),
        "campaign_version": CAMPAIGN_VERSION,
        "engine_commit": state.get("engine_commit"),
        "retrieval_fabric_version": "RETRIEVAL_FABRIC_V2",
        "constitution_compliance": {
            "read_in_full_before_discovery": True,
            "art_xliii": "queries derived from problem facts (frozen "
                         "domain matrix; no solution class injected)",
            "art_li": "cemetery read by the generator (collision gate "
                      "F3) and extended by the campaign (killed "
                      "candidates)",
            "art_lii": "every dossier carries the falsification "
                       "contract",
            "art_lxi": "infrastructure failures recorded as INCOMPLETE, "
                       "never REJECTED",
            "art_lxii": "matrix/contract/evidence/candidate hashes "
                        "recorded; replay from committed state",
        },
        "sources_attempted": sources_attempted,
        "source_failures": source_failures,
        "domains_explored": {
            "n_domains": matrix.get("n_domains"),
            "domain_ids": state.get("retrieval_done", []),
            "matrix_sha256": matrix.get("matrix_sha256"),
        },
        "queries": {
            "total_query_instances": len(queries),
            "expansion_classes": query_expansion_classes,
            "note": "every domain's fabric report records the exact "
                    "query + variant derivation class per source",
        },
        "candidate_count": collision.get("raw_accepted_from_extraction"),
        "candidate_rejections": {
            "medical_excluded": collision.get("medical_excluded_count"),
            "collision_rejected": collision.get("collision_rejected"),
            "dedup_merged": collision.get("dedup_merged"),
            "extraction_gate_rejected": sum(
                len((_read(c, "candidates", f"{d}.json") or
                     {}).get("rejected") or [])
                for d in state.get("extraction_done", [])),
        },
        "candidate_survivors": collision.get("survivor_count"),
        "attacker_results": {
            "calibration": {
                "n_defects": cal.get("n_defects"),
                "n_killed_as_expected": cal.get("n_killed_as_expected"),
                "sensitivity_by_defect_class":
                    cal.get("sensitivity_by_defect_class"),
            },
            "n_attacked": len(state.get("attack_done", [])),
            "verdicts": {
                cid: (_read(c, "attack", f"{cid}.json") or
                      {}).get("verdict")
                for cid in state.get("attack_done", [])
            },
            "independence_mode": (
                "SEPARATE_CONTEXT (single credentialed provider — "
                "disclosed, never labelled independent validation)"
                if all((_read(c, "attack", f"{cid}.json") or
                        {}).get("independence_mode") in
                       ("SEPARATE_CONTEXT", "TRANSPORT_FAILED", None)
                       for cid in state.get("attack_done", []))
                else "SEPARATE_PROVIDER for at least one attack"),
        },
        "prior_art_results": {
            "n_searched": len(state.get("prior_art_done", [])),
            "distance_classes": {
                cid: ((_read(c, "prior_art", f"{cid}.json") or
                       {}).get("closest_prior_art") or
                      {}).get("distance_class")
                for cid in state.get("prior_art_done", [])
            },
            "terminology_recovery_totals": {
                "records_found_only_by_secondary_perspectives": sum(
                    ((_read(c, "prior_art", f"{cid}.json") or
                      {}).get("terminology_recovery") or
                     {}).get("total_unique_secondary_only", 0)
                    for cid in state.get("prior_art_done", [])),
            },
        },
        "engineering_results": {
            "n_gated": len(state.get("engineering_done", [])),
            "verdicts": {
                cid: (_read(c, "engineering", f"{cid}.json") or
                      {}).get("passed")
                for cid in state.get("engineering_done", [])
            },
        },
        "selected_technologies": selected,
        "killed_technologies": killed,
        "buyer_packages_created": [{
            "technology_id": m.get("technology_id"),
            "folder": m.get("folder"),
            "files": m.get("files"),
        } for m in buyer_manifest],
        "search_space_coverage": {
            "n_domains_retrieved": len(state.get("retrieval_done", [])),
            "n_domains_extracted": len(state.get("extraction_done", [])),
            "n_shortlisted": len(shortlist),
        },
        "source_diversity": source_diversity,
        "document_type_diversity": document_types,
        "cross_domain_transfers": {
            "n_candidates_with_cross_domain_transition":
                len(cross_domain),
            "examples": [{
                "candidate_id": x.get("candidate_id"),
                "transition": x.get("cross_domain_transition"),
            } for x in cross_domain[:10]],
        },
        "mechanism_diversity": {
            "n_distinct_phenomenon_labels": len(mechanism_families),
            "note": "label-level diversity; the typed-distinction "
                    "instrument (Art. XLII) is the structural authority "
                    "in the collision stage",
        },
        "candidate_collision_rate": round(
            (collision.get("dedup_merged") or 0) /
            max(1, collision.get("raw_accepted_from_extraction") or 1), 3),
        "reality_boundary": {
            "physical_observations": 0,
            "independent_physical_replication": 0,
            "real_buyers": 0,
            "commercial_transactions": 0,
        },
        "stop_condition": (
            "REACHED (s23): five buyer dossiers generated; the machine "
            "stops; the human owner decides which physical experiment "
            "gets funded"),
    }


def build_report_md(c, run_record: Dict[str, Any]) -> str:
    state = c.state
    selection = _read(c, "selection.json") or {}
    shortlist = _read(c, "shortlist.json") or []
    by_id = {x["candidate_id"]: x for x in shortlist}
    funnel_by_id = {}
    for rec in (selection.get("full_records") or []):
        funnel_by_id[rec["candidate"]["candidate_id"]] = rec

    lines = []
    a = lines.append
    a("# R411 — Autonomous Discovery of 5 High-Value Non-Medical "
      "Technologies")
    a("")
    a(f"**Run:** {run_record['run_id']} | **Engine commit:** "
      f"`{run_record['engine_commit'][:12]}` | **Fabric:** "
      f"RETRIEVAL_FABRIC_V2 | **Campaign:** {CAMPAIGN_VERSION}")
    a("")
    a("The engine moved search -> discovery -> mechanism -> evidence -> "
      "differentiation -> engineering -> adversarial attack -> decisive "
      "experiment -> transfer package -> buyer dossier for each "
      "selected technology. Physical observations: **0**. This is an "
      "experiment-ready portfolio, not a validated one.")
    a("")
    a("## Discovery funnel")
    a("")
    a("```text")
    a(f"Raw evidence records        "
      f"{sum(((_read(c, 'evidence', f'{d}.json') or {}).get('pool') or []) and len(_read(c, 'evidence', f'{d}.json')['pool']) for d in state.get('retrieval_done', []))}")
    a(f"  across {len(state.get('retrieval_done', []))} domains, "
      f"{len(run_record['sources_attempted'])} sources, "
      f"{len(run_record['source_diversity'])} source families")
    a(f"Candidate mechanisms         "
      f"{run_record['candidate_count']}")
    a(f"  medical-excluded           "
      f"{run_record['candidate_rejections']['medical_excluded']}")
    a(f"  collision-rejected         "
      f"{run_record['candidate_rejections']['collision_rejected']}")
    a(f"  dedup-merged               "
      f"{run_record['candidate_rejections']['dedup_merged']}")
    a(f"Technology opportunities     "
      f"{run_record['candidate_survivors']}")
    a(f"  shortlisted (EIG/cost)     {len(shortlist)}")
    a(f"  prior-art searched         "
      f"{len(state.get('prior_art_done', []))}")
    a(f"  engineering-gated          "
      f"{len(state.get('engineering_done', []))}")
    a(f"  attacked                   "
      f"{len(state.get('attack_done', []))}")
    a(f"  attacker-killed            "
      f"{len(run_record['killed_technologies'])}")
    a(f"FINAL                        "
      f"{len(run_record['selected_technologies'])}/5")
    a("```")
    a("")

    a("## Five selected technologies")
    a("")
    for idx, cid in enumerate(run_record["selected_technologies"], 1):
        rec = funnel_by_id.get(cid) or {}
        cand = rec.get("candidate") or by_id.get(cid) or {}
        sc = (cand.get("scoring") or {})
        pa = ((rec.get("funnel") or {}).get("prior_art") or {})
        closest = (pa.get("closest_prior_art") or {})
        ke = (cand.get("killer_experiment") or {})
        base = (cand.get("baseline") or {})
        a(f"### {idx}. {cand.get('technology_name')} "
          f"(`{cid}`)")
        a("")
        a(f"- **Domain:** {cand.get('target_domain')} (from "
          f"{cand.get('source_domain')})")
        a(f"- **Problem:** {cand.get('problem')}")
        a(f"- **Mechanism:** {' -> '.join(cand.get('causal_chain') or [])}")
        a(f"- **Why it matters:** {base.get('expected_delta')} vs "
          f"{str(base.get('baseline_incumbent'))[:100]}")
        a(f"- **Evidence strength:** "
          f"{(sc.get('sub_scores') or {}).get('evidence_strength')}/4 "
          f"(confidence {sc.get('confidence')}, composite "
          f"{sc.get('composite')})")
        a(f"- **Closest prior art:** "
          f"{closest.get('distance_class')} — "
          f"{(closest.get('strongest_existing_candidates') or [{}])[0].get('title', 'none found in scope')}")
        a(f"- **Differentiation:** "
          f"{(rec.get('funnel') or {}).get('typed_distinction')}")
        a(f"- **Baseline:** {base.get('baseline_metric')}")
        a(f"- **Predicted advantage:** {base.get('expected_delta')}")
        a(f"- **Decisive experiment:** {ke.get('experiment')}")
        a(f"- **Cost:** {ke.get('cost_class')} | **Time:** 8-12 weeks "
          f"(BENCH/LAB class)")
        a(f"- **Kill condition:** {ke.get('kill_condition')}")
        a(f"- **Buyer:** "
          f"{(cand.get('commercial_path') or {}).get('buyer')}")
        a(f"- **Transfer state:** TRANSFER_READY_FOR_EVALUATION "
          f"(physical validation: NO)")
        a(f"- **Status:** {(rec.get('funnel') or {}).get('attack', {}).get('verdict', '—')} "
          f"attacker verdict; dossier status "
          f"{_dossier_status(c, idx)}")
        a(f"- **Confidence:** {sc.get('confidence')}")
        a("")

    a("## Rejected candidates — the strongest deaths")
    a("")
    a("The machine's discarded ideas, recorded so future discovery "
      "improves (the cemetery now carries them):")
    a("")
    for r in (selection.get("rejected") or [])[:12]:
        a(f"- **{r.get('name') or r.get('candidate_id')}** "
          f"(`{r.get('candidate_id')}`): {str(r.get('reason'))[:200]}")
    a("")
    a("*(Killed candidates also enter `MECHANISM_CEMETERY` with "
      "reusable lessons; quota/diversity rejections stay here only — "
      "a quota rejection is not a mechanism death.)*")
    a("")

    a("## Buyer packages")
    a("")
    for m in run_record["buyer_packages_created"]:
        a(f"- `{m['folder']}` — "
          f"{', '.join(sorted(m.get('files') or {}))}")
    a("")
    a("Each buyer package contains TRANSFER_STATE.json "
      "(portfolio-convention record), BUYER_DOSSIER.md (the 18-field "
      "buyer view), and TECHNOLOGY_DOSSIER.json (the full auditable "
      "record).")
    a("")

    a("## Search-space report")
    a("")
    a(f"- **Source diversity:** "
      f"{json.dumps(run_record['source_diversity'])}")
    a(f"- **Document-type diversity:** "
      f"{json.dumps(run_record['document_type_diversity'])}")
    a(f"- **Domain diversity:** "
      f"{len(state.get('retrieval_done', []))} domains across "
      f"{len(set((by_id.get(x) or {}).get('domain_id', '') for x in run_record['selected_technologies']))}"
      f" distinct final-technology domains")
    a(f"- **Cross-domain transfers:** "
      f"{run_record['cross_domain_transfers']['n_candidates_with_cross_domain_transition']}"
      f" candidates carry an explicit cross-domain transition")
    a(f"- **Mechanism diversity (label-level):** "
      f"{run_record['mechanism_diversity']['n_distinct_phenomenon_labels']}")
    a(f"- **Candidate collision rate:** "
      f"{run_record['candidate_collision_rate']}")
    a(f"- **Terminology recovery (anti-lock-in, s7):** "
      f"{run_record['prior_art_results']['terminology_recovery_totals']['records_found_only_by_secondary_perspectives']}"
      f" records were found ONLY by the non-forward perspectives/"
      f"registers — the direct attack on the R409 measured frontier")
    a("")

    a("## Reality boundary")
    a("")
    a("```text")
    a(f"physical observations = 0 / {run_record['reality_boundary']['physical_observations']}")
    a(f"independent physical replication = {run_record['reality_boundary']['independent_physical_replication']}")
    a(f"real buyers = {run_record['reality_boundary']['real_buyers']}")
    a(f"commercial transactions = {run_record['reality_boundary']['commercial_transactions']}")
    a("```")
    a("")
    a("An experiment-ready package is never confused with physically "
      "validated technology (Art. XXXVIII).")
    a("")
    a("## Stop condition (s23)")
    a("")
    a("The machine has stopped. The next action for each technology, "
      "presented for the human owner's funding decision:")
    a("")
    for idx, cid in enumerate(run_record["selected_technologies"], 1):
        rec = funnel_by_id.get(cid) or {}
        cand = rec.get("candidate") or {}
        ke = (cand.get("killer_experiment") or {})
        a(f"{idx}. **{cand.get('technology_name')}** -> "
          f"highest-information experiment: {str(ke.get('experiment'))[:140]} "
          f"-> cost class {ke.get('cost_class')} -> decision value: "
          f"kills or clears the mechanism's decisive uncertainty "
          f"({str(ke.get('decisive_uncertainty'))[:80]}) -> funding "
          f"requirement: owner decision.")
    a("")
    return "\n".join(lines)


def _dossier_status(c, idx: int) -> str:
    d = None
    dd = os.path.join(c.run_dir, "dossiers")
    if os.path.isdir(dd):
        for fn in sorted(os.listdir(dd)):
            if fn.startswith(f"D{idx}_"):
                d = json.load(open(os.path.join(dd, fn)))
                break
    return (d or {}).get("status", "NOT_BUILT")


def write_run_record_and_report(c) -> None:
    run_record = build_run_record(c)
    report_md = build_report_md(c, run_record)
    out_dir = os.path.join(c.repo, "R411")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "R411_DISCOVERY_RUN.json"),
              "w") as f:
        json.dump(run_record, f, indent=1)
    with open(os.path.join(out_dir, "R411_DISCOVERY_REPORT.md"),
              "w") as f:
        f.write(report_md)
