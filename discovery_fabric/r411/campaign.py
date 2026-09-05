"""discovery_fabric/r411/campaign.py — the R411 campaign orchestrator.

A RESUMABLE state machine (the sandbox reaps long processes; every work
unit checkpoints to the run directory, and the driver re-invokes until
the STOP condition).

Stages:
  F0  init          — engine commit, frozen matrix + scoring contract,
                      evidence-snapshot registry
  F1  retrieval     — per domain: one live fabric call -> evidence pool
  F2  extraction    — per domain: LLM candidate extraction (no-fabrication
                      gate), medical-exclusion screen
  F3  collision     — cemetery + portfolio + intra-campaign dedup
  F4  scoring       — deterministic pre-registered composite + EIG/cost
  F4b shortlist     — ~14 finalists with domain-diversity pre-selection
  F5  prior_art     — per finalist: 4-perspective + terminology-register
                      adversarial retrieval
  F6  engineering   — structural engineering gate
  F7  attack        — attacker calibration + tournament
  F8  selection     — final five (diversity constraint; never fabricate)
  F9  dossiers      — P04/P11-level packages
  F10 buyer         — buyer packages -> LEAD_PORTFOLIO_4/R411_DISCOVERED/
                      + cemetery entries for killed candidates
  F11 records       — R411_DISCOVERY_RUN.json + R411_DISCOVERY_REPORT.md

Constitution: every stage transition is recorded with its inputs/outputs
hashes; provider failures are recorded as INCOMPLETE_* (Art. LXI), never
as scientific rejections; the STOP condition (s23) is terminal.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from typing import Any, Dict, List, Optional

from .domain_matrix import (DOMAIN_MATRIX_SPEC, build_domain_matrix,
                            primary_query_for_entry)
from .scoring import scoring_contract, score_candidate, \
    information_gain_per_cost
from .extract import (build_extraction_prompt, parse_candidates,
                      CANDIDATES_PER_CALL)
from .collision import collision_gate, intra_campaign_dedup
from .prior_art import (build_perspectives, assess_prior_art,
                        terminology_recovery, register_queries)
from .attack import attack_candidate, run_attacker_calibration
from .dossier import build_dossier
from .buyer_package import write_buyer_package

CAMPAIGN_VERSION = "R411-CAMPAIGN-V1"
DEFAULT_RUN_DIR = "R411/DISCOVERY_RUN"
SHORTLIST_SIZE = 14
FINAL_TARGET = 5
MAX_PER_DOMAIN_FAMILY = 1   # s4 diversity constraint for the FINAL five
MAX_PER_DOMAIN_FAMILY_SHORTLIST = 2

FABRIC_LANE_CAPS = {
    "SCHOLARLY": 8, "PREPRINT": 4, "THESIS": 4, "PATENT": 6,
    "TECHNICAL_REPORT": 3, "DATASET": 2, "REPOSITORY": 5,
}


def _sha(obj: Any) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True).encode()).hexdigest()


def _write_json(path: str, obj: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, indent=1)


def _read_json(path: str) -> Any:
    with open(path) as f:
        return json.load(f)


def engine_commit(repo_root: str) -> str:
    import subprocess
    return subprocess.run(
        ["git", "-C", repo_root, "rev-parse", "HEAD"],
        capture_output=True, text=True).stdout.strip()


def normalize_pool(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Fabric engine items -> the campaign pool record shape (record_id,
    title, abstract, year, lane, publication_status, provenance)."""
    out = []
    for it in items:
        prov = it.get("provenance") or {}
        out.append({
            "record_id": str(it.get("id")),
            "title": str(it.get("title") or ""),
            "abstract": str(it.get("abstract") or "")[:1200],
            "year": it.get("publication_year"),
            "lane": it.get("evidence_lane") or it.get("fabric_lane"),
            "publication_status": it.get("publication_status"),
            "source_type": it.get("source_type"),
            "provenance": {
                "source_id": it.get("source_id"),
                "source_family": prov.get("source_family"),
                "query": (prov.get("queries_by_source") or {}),
                "variant_class": prov.get("query_variant_derivation"),
                "raw_payload_sha256": prov.get("raw_payload_sha256"),
                "fabric_version": prov.get("fabric_version"),
            },
        })
    return out


class Campaign:
    """The resumable campaign state machine."""

    def __init__(self, repo_root: str, run_dir: Optional[str] = None):
        self.repo = repo_root
        self.run_dir = os.path.join(repo_root, run_dir or DEFAULT_RUN_DIR)
        self.state_path = os.path.join(self.run_dir, "STATE.json")
        os.makedirs(self.run_dir, exist_ok=True)
        self.state = self._load_or_init()

    # ---------------- state management --------------------------------
    def _load_or_init(self) -> Dict[str, Any]:
        if os.path.exists(self.state_path):
            return _read_json(self.state_path)
        matrix = build_domain_matrix()
        contract = scoring_contract()
        commit = engine_commit(self.repo)
        return {
            "campaign_version": CAMPAIGN_VERSION,
            "run_id": f"r411:{int(time.time())}",
            "engine_commit": commit,
            "stage": "F0_init",
            "domain_matrix": {
                "matrix_sha256": matrix["matrix_sha256"],
                "n_domains": matrix["n_domains"],
                "n_entries": matrix["n_entries"],
                "path": os.path.join(self.run_dir, "domain_matrix.json"),
            },
            "scoring_contract": {
                "contract_sha256": contract["contract_sha256"],
                "path": os.path.join(self.run_dir,
                                     "scoring_contract.json"),
            },
            "retrieval_done": [],
            "extraction_done": [],
            "collision_done": False,
            "scoring_done": False,
            "shortlist_done": False,
            "prior_art_done": [],
            "engineering_done": [],
            "attack_calibration_done": False,
            "attack_done": [],
            "selection_done": False,
            "dossiers_done": False,
            "buyer_done": False,
            "records_done": False,
            "stopped": False,
        }

    def save(self) -> None:
        _write_json(self.state_path, self.state)

    def materialize_frozen_inputs(self) -> None:
        """F0: write the frozen matrix + scoring contract (before any
        candidate exists — the pre-registration)."""
        matrix = build_domain_matrix()
        _write_json(self.state["domain_matrix"]["path"], matrix)
        _write_json(self.state["scoring_contract"]["path"],
                    scoring_contract())

    # ---------------- F1: retrieval ------------------------------------
    def retrieval_targets(self) -> List[Dict[str, Any]]:
        matrix = _read_json(self.state["domain_matrix"]["path"])
        seen = set()
        targets = []
        for entry in matrix["entries"]:
            if entry["domain_id"] not in seen:
                seen.add(entry["domain_id"])
                targets.append(entry)
        return targets

    def run_retrieval_for(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """One domain's live fabric call. LLM expansion OFF (deterministic
        terminology classes only) + reciprocal OFF for the sweep (S2
        budget discipline; the finalist prior-art stage re-enables
        retrieval depth). Provider failures are recorded per-lane by the
        fabric itself (Art. XXI.3)."""
        from discovery_fabric.retrieval_fabric.pipeline import retrieve_fabric
        problem = dict(entry["problem"])
        t0 = time.time()
        items, report = retrieve_fabric(
            problem, lane_caps=FABRIC_LANE_CAPS,
            enable_reciprocal=False, enable_unpaywall=False)
        pool = normalize_pool(items)
        snapshot = {
            "domain_id": entry["domain_id"],
            "entry_id": entry["entry_id"],
            "problem": problem,
            "fabric_report": {
                k: v for k, v in report.items()
                if k != "canonical_records"},
            "pool": pool,
            "pool_sha256": _sha(pool),
            "elapsed_s": round(time.time() - t0, 1),
        }
        path = os.path.join(self.run_dir, "evidence",
                            f"{entry['domain_id']}.json")
        _write_json(path, snapshot)
        # the full canonical records are large; store once per domain in
        # a sidecar for replayability (Art. LXII) without bloating the
        # working snapshot
        _write_json(
            os.path.join(self.run_dir, "evidence",
                         f"{entry['domain_id']}_canonical.json"),
            {"domain_id": entry["domain_id"],
             "canonical_records": report.get("canonical_records", [])})
        self.state["retrieval_done"].append(entry["domain_id"])
        self.save()
        return snapshot

    # ---------------- F2: extraction ------------------------------------
    def run_extraction_for(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """LLM extraction over the domain's frozen pool. Each call sees a
        batch of records; every result passes the no-fabrication gate.
        Transport failure => the domain is INCOMPLETE (recorded), never
        fabricated (Art. LXI)."""
        from discovery_fabric.engine.mechanism_space import llm_generate
        snap_path = os.path.join(self.run_dir, "evidence",
                                 f"{entry['domain_id']}.json")
        snapshot = _read_json(snap_path)
        pool = snapshot["pool"]
        if not pool:
            result = {
                "domain_id": entry["domain_id"],
                "status": "NO_EVIDENCE_POOL",
                "accepted": [], "rejected": [],
            }
            path = os.path.join(self.run_dir, "candidates",
                                f"{entry['domain_id']}.json")
            _write_json(path, result)
            self.state["extraction_done"].append(entry["domain_id"])
            self.save()
            return result
        domain_spec = DOMAIN_MATRIX_SPEC[entry["domain_id"]]
        accepted: List[Dict[str, Any]] = []
        rejected: List[Dict[str, Any]] = []
        transport_failures = 0
        n_batches = max(1, min(3, (len(pool) + 27) // 28))
        for batch in range(n_batches):
            prompt = build_extraction_prompt(entry, domain_spec, pool,
                                             batch_offset=batch * 28)
            meta = llm_generate(
                prompt,
                system="You are a mechanism-discovery instrument. "
                       "Ground every candidate in the evidence records. "
                       "Never invent record ids or findings.",
                purpose="r411_candidate_extraction", max_tokens=2400)
            if not meta.get("ok"):
                transport_failures += 1
                rejected.append({
                    "candidate_id": f"TRANSPORT-FAIL-{batch}",
                    "reasons": [f"LLM transport: {meta.get('status')}"],
                })
                continue
            parsed = parse_candidates(
                meta.get("content") or "", entry["domain_id"], pool,
                generation_meta={
                    "provider": meta.get("provider"),
                    "model": meta.get("model"),
                    "prompt_hash": meta.get("prompt_hash"),
                    "output_hash": meta.get("output_hash"),
                })
            accepted.extend(parsed["accepted"])
            rejected.extend(parsed["rejected"])
        result = {
            "domain_id": entry["domain_id"],
            "status": "OK" if transport_failures < n_batches else
                      "INCOMPLETE_LLM_TRANSPORT",
            "transport_failures": transport_failures,
            "n_batches": n_batches,
            "accepted": accepted,
            "rejected": rejected,
            "pool_sha256": snapshot["pool_sha256"],
        }
        path = os.path.join(self.run_dir, "candidates",
                            f"{entry['domain_id']}.json")
        _write_json(path, result)
        self.state["extraction_done"].append(entry["domain_id"])
        self.save()
        return result

    # ---------------- F3: collision -------------------------------------
    def run_collision(self) -> Dict[str, Any]:
        all_accepted = []
        for dom in self.state["extraction_done"]:
            path = os.path.join(self.run_dir, "candidates",
                                f"{dom}.json")
            if os.path.exists(path):
                all_accepted.extend(
                    _read_json(path).get("accepted") or [])
        # medical exclusion (s1) first
        from .medical_exclusion import medical_exclusion_screen
        medical_excluded = []
        screened = []
        for c in all_accepted:
            s = medical_exclusion_screen(c)
            c["medical_screen"] = s
            if s["excluded"]:
                medical_excluded.append(
                    {"candidate_id": c["candidate_id"],
                     "verdict": s["verdict"],
                     "matched": s["matched_medical_terms"][:6]})
            else:
                screened.append(c)
        # collision gate per candidate (cemetery + portfolio + typed)
        gate_results = []
        admitted = []
        for c in screened:
            gate = collision_gate(c)
            gate_results.append({
                "candidate_id": c["candidate_id"],
                "verdict": gate["verdict"],
                "typed_distinction": gate.get("typed_distinction"),
                "reasons": gate.get("reasons"),
            })
            if gate["admitted"]:
                c["collision_gate"] = gate
                admitted.append(c)
        # intra-campaign dedup (Art. XLVIII)
        dedup = intra_campaign_dedup(admitted)
        _write_json(os.path.join(self.run_dir, "funnel_collision.json"), {
            "raw_accepted_from_extraction": len(all_accepted),
            "medical_excluded": medical_excluded,
            "medical_excluded_count": len(medical_excluded),
            "collision_gate_results": gate_results,
            "collision_rejected_count": sum(
                1 for g in gate_results if not g.get("typed_distinction")
                or g["verdict"].startswith("REJECTED")),
            "dedup": {k: v for k, v in dedup.items() if k != "survivors"},
            "survivor_count": dedup["survivor_count"],
            "survivors_path": os.path.join(self.run_dir,
                                           "scored_pool.json"),
        })
        _write_json(os.path.join(self.run_dir, "scored_pool.json"),
                    dedup["survivors"])
        self.state["collision_done"] = True
        self.state["collision_counts"] = {
            "raw": len(all_accepted),
            "medical_excluded": len(medical_excluded),
            "collision_rejected": len(admitted) and (
                len(screened) - len(admitted)),
            "dedup_merged": len(dedup["merge_events"]),
            "pool": dedup["survivor_count"],
        }
        self.save()
        return dedup

    # ---------------- F4: scoring ----------------------------------------
    def run_scoring(self) -> Dict[str, Any]:
        pool_path = os.path.join(self.run_dir, "scored_pool.json")
        survivors = _read_json(pool_path)
        pools_by_domain = {}
        for dom in self.state["extraction_done"]:
            p = os.path.join(self.run_dir, "evidence", f"{dom}.json")
            if os.path.exists(p):
                pools_by_domain[dom] = _read_json(p)["pool"]
        scored = []
        for c in survivors:
            dom_pool = pools_by_domain.get(c["domain_id"], [])
            funnel_stub = {"typed_distinction":
                           (c.get("collision_gate") or {}).get(
                               "typed_distinction")}
            sc = score_candidate(c, dom_pool, funnel_stub)
            eig = information_gain_per_cost(c)
            c["scoring"] = sc
            c["eig_per_cost"] = eig
            scored.append(c)
        _write_json(os.path.join(self.run_dir, "scored_pool.json"), scored)
        self.state["scoring_done"] = True
        self.state["scoring_counts"] = {
            "n_scored": len(scored),
            "n_finalist_eligible": sum(
                1 for c in scored if c["scoring"]["finalist_eligible"]),
            "n_low_confidence": sum(
                1 for c in scored if c["scoring"]["confidence"] == "LOW"),
        }
        self.save()
        return {"n": len(scored)}

    # ---------------- F4b: shortlist --------------------------------------
    def run_shortlist(self) -> List[Dict[str, Any]]:
        scored = _read_json(os.path.join(self.run_dir, "scored_pool.json"))
        matrix = _read_json(self.state["domain_matrix"]["path"])
        family_of = {e["domain_id"]: e["domain_family"]
                     for e in matrix["entries"]}
        eligible = [c for c in scored if c["scoring"]["finalist_eligible"]]
        # rank: EIG/cost desc, composite desc, evidence asc-conflict
        eligible.sort(key=lambda c: (-c["eig_per_cost"],
                                     -c["scoring"]["composite"]))
        picked, family_count = [], {}
        for c in eligible:
            fam = family_of.get(c["domain_id"], "?")
            if family_count.get(fam, 0) >= \
                    MAX_PER_DOMAIN_FAMILY_SHORTLIST:
                continue
            family_count[fam] = family_count.get(fam, 0) + 1
            picked.append(c)
            if len(picked) >= SHORTLIST_SIZE:
                break
        _write_json(os.path.join(self.run_dir, "shortlist.json"), picked)
        self.state["shortlist_done"] = True
        self.state["shortlist_ids"] = [c["candidate_id"] for c in picked]
        self.save()
        return picked

    # ---------------- F5: prior art ----------------------------------------
    def run_prior_art_for(self, cand: Dict[str, Any]) -> Dict[str, Any]:
        """Four retrieval perspectives + terminology registers for one
        finalist. The fabric is called with the perspective problems;
        register queries run as plain variant-class queries through the
        fabric's lane fan-out (each perspective call = 1 fabric call)."""
        from discovery_fabric.retrieval_fabric.pipeline import retrieve_fabric
        perspectives = build_perspectives(cand)
        retrieved = {}
        forward_records = []
        for p in perspectives:
            items, report = retrieve_fabric(
                p["problem"], lane_caps=FABRIC_LANE_CAPS,
                enable_reciprocal=False, enable_unpaywall=False)
            norm = normalize_pool(items)
            retrieved[p["perspective"]] = norm
            if p["perspective"] == "FORWARD":
                forward_records = norm
        # terminology-register queries: run the MECHANISM problem with
        # register-substituted device text (a cheap deterministic
        # anti-lock-in expansion on top of the fabric's own variants)
        mech_problem = perspectives[1]["problem"]
        for reg_query in register_queries(cand):
            reg_problem = {
                "device": reg_query["query"][:120],
                "failure_mode": cand.get("pain_class") or "",
                "constraint": f"terminology register {reg_query['register']}",
            }
            items, report = retrieve_fabric(
                reg_problem, lane_caps={"SCHOLARLY": 4, "PATENT": 4,
                                        "THESIS": 2, "REPOSITORY": 3,
                                        "PREPRINT": 2,
                                        "TECHNICAL_REPORT": 2,
                                        "DATASET": 1},
                enable_reciprocal=False, enable_unpaywall=False)
            retrieved[f"REGISTER_{reg_query['register']}"] = \
                normalize_pool(items)
        pa = assess_prior_art(cand, retrieved,
                              generator_provider=(
                                  cand.get("generation") or {}).get(
                                  "provider"))
        pa["terminology_recovery"] = terminology_recovery(
            retrieved, forward_records)
        pa["retrieval_counts"] = {k: len(v) for k, v in retrieved.items()}
        path = os.path.join(self.run_dir, "prior_art",
                            f"{cand['candidate_id']}.json")
        _write_json(path, pa)
        self.state["prior_art_done"].append(cand["candidate_id"])
        self.save()
        return pa

    # ---------------- F6: engineering ---------------------------------------
    ENGINEERING_GATE_RULES = (
        "structural: causal chain >=3 steps, governing variables with "
        "units, >=1 equation, boundary conditions, design-realizable "
        "intervention, killer experiment with kill condition + cost "
        "class; each check deterministic")

    def engineering_gate(self, cand: Dict[str, Any]) -> Dict[str, Any]:
        checks = {
            "causal_chain_steps": len(cand.get("causal_chain") or []) >= 3,
            "governing_variables": bool(cand.get("governing_variables")),
            "equation_present": bool(cand.get("equations")),
            "boundary_conditions": bool(cand.get("boundary_conditions")),
            "intervention_realizable": bool(cand.get("intervention")),
            "kill_condition": bool(
                (cand.get("killer_experiment") or {}).get("kill_condition")),
            "cost_class_valid": (cand.get("killer_experiment") or {}).get(
                "cost_class") in ("BENCH", "LAB", "PILOT", "FIELD"),
            "baseline_metric": bool(
                (cand.get("baseline") or {}).get("baseline_metric")),
        }
        return {
            "gate_version": "R411-ENG-V1",
            "checks": checks,
            "passed": all(checks.values()),
            "failed_checks": [k for k, v in checks.items() if not v],
            "rules": self.ENGINEERING_GATE_RULES,
        }

    # ---------------- F7: attack ---------------------------------------------
    def run_attack_calibration(self) -> Dict[str, Any]:
        cal = run_attacker_calibration()
        _write_json(os.path.join(self.run_dir,
                                 "attack_calibration.json"), cal)
        self.state["attack_calibration_done"] = True
        self.state["attack_calibration"] = {
            "n_defects": cal["n_defects"],
            "n_killed_as_expected": cal["n_killed_as_expected"],
        }
        self.save()
        return cal

    def run_attack_for(self, cand: Dict[str, Any],
                       pa: Dict[str, Any]) -> Dict[str, Any]:
        dom_pool = []
        p = os.path.join(self.run_dir, "evidence",
                         f"{cand['domain_id']}.json")
        if os.path.exists(p):
            dom_pool = _read_json(p)["pool"]
        attack = attack_candidate(
            cand, dom_pool, pa,
            generator_provider=(cand.get("generation") or {}).get(
                "provider"))
        path = os.path.join(self.run_dir, "attack",
                            f"{cand['candidate_id']}.json")
        _write_json(path, attack)
        self.state["attack_done"].append(cand["candidate_id"])
        self.save()
        return attack

    # ---------------- F8: selection --------------------------------------------
    def run_selection(self) -> Dict[str, Any]:
        shortlist = _read_json(os.path.join(self.run_dir, "shortlist.json"))
        matrix = _read_json(self.state["domain_matrix"]["path"])
        family_of = {e["domain_id"]: e["domain_family"]
                     for e in matrix["entries"]}
        records = []
        for c in shortlist:
            cid = c["candidate_id"]
            pa_path = os.path.join(self.run_dir, "prior_art",
                                   f"{cid}.json")
            pa = _read_json(pa_path) if os.path.exists(pa_path) else {}
            eng = self.engineering_gate(c)
            eng_path = os.path.join(self.run_dir, "engineering",
                                    f"{cid}.json")
            _write_json(eng_path, eng)
            self.state["engineering_done"].append(cid)
            attack_path = os.path.join(self.run_dir, "attack",
                                       f"{cid}.json")
            attack = _read_json(attack_path) if os.path.exists(
                attack_path) else {"status": "NOT_RUN"}
            funnel = {
                "typed_distinction": (c.get("collision_gate") or {}).get(
                    "typed_distinction"),
                "prior_art": pa,
                "attack": attack,
                "engineering": eng,
                "scoring": c.get("scoring"),
            }
            killed = (attack.get("verdict") == "KILLED") or \
                     (not eng["passed"])
            incomplete = attack.get("status") not in ("OK",) or \
                not pa
            records.append({
                "candidate": c,
                "funnel": funnel,
                "killed": killed,
                "incomplete": incomplete,
                "selection_score": (
                    0 if killed else
                    (c.get("eig_per_cost", 0) +
                     c.get("scoring", {}).get("composite", 0) / 4.0) +
                     (0.5 if funnel["typed_distinction"] in (
                         "NEW_MECHANISM", "NEW_CAUSAL_CONFIGURATION",
                         "NEW_MEASUREMENT_METHOD") else 0)),
            })
        # diversity-constrained selection (s4/s14)
        records.sort(key=lambda r: -r["selection_score"])
        selected, family_count, rejected = [], {}, []
        for r in records:
            fam = family_of.get(r["candidate"]["domain_id"], "?")
            if r["killed"] or r["incomplete"]:
                r["rejection_reason"] = (
                    "KILLED: " + str(
                        (r["funnel"]["attack"] or {}).get(
                            "final_objection") or
                        (r["funnel"]["attack"] or {}).get("verdict"))
                    if r["killed"] else "INCOMPLETE (Art. LXI)")
                rejected.append(r)
                continue
            if len(selected) < FINAL_TARGET:
                if family_count.get(fam, 0) >= MAX_PER_DOMAIN_FAMILY:
                    r["rejection_reason"] = (
                        f"domain-family diversity constraint "
                        f"({fam} already at {family_count.get(fam)})")
                    rejected.append(r)
                    continue
                family_count[fam] = family_count.get(fam, 0) + 1
                selected.append(r)
            else:
                r["rejection_reason"] = "quota filled by higher-ranked " \
                                        "survivors"
                rejected.append(r)
        _write_json(os.path.join(self.run_dir, "selection.json"), {
            "selected": [r["candidate"]["candidate_id"]
                         for r in selected],
            "n_selected": len(selected),
            "target": FINAL_TARGET,
            "quota_honesty": (
                f"{len(selected)}/{FINAL_TARGET} qualified; "
                f"{FINAL_TARGET - len(selected)}/{FINAL_TARGET} "
                f"insufficient evidence" if len(selected) < FINAL_TARGET
                else f"{FINAL_TARGET}/{FINAL_TARGET} qualified — no "
                     f"threshold was lowered to force five winners"),
            "rejected": [{
                "candidate_id": r["candidate"]["candidate_id"],
                "name": r["candidate"].get("technology_name"),
                "reason": r.get("rejection_reason"),
                "selection_score": r.get("selection_score"),
            } for r in rejected],
            "full_records": records,
        })
        self.state["selection_done"] = True
        self.state["selected_ids"] = [r["candidate"]["candidate_id"]
                                      for r in selected]
        self.save()
        return {"selected": selected, "rejected": rejected}

    # ---------------- F9/F10/F11 in the driver (dossier/buyer/records) -------
