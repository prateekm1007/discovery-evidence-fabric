#!/usr/bin/env python3
"""r139s2_verify_c0219 — the INDEPENDENT VERIFIER record for the open
claims c-0218 (r137-panel-fixes-live-multi-mechanism) and c-0219
(r138-grounding-agnes-measurement). The twin (builder-r121s1-3e8a41d7)
holds c-0220 EXECUTOR over the R139 repair lane; THIS lane is the
verification the auditor's DIR 7 requires before those claims may
close: functional probes of the REAL engine path (the
MechanismSpaceAdapter admission chain with a stubbed LLM and crafted
mechanism_support verdicts), plus zero-LLM recomputes of the c-0219
measurement claims from committed bytes.

The functional probes drive the REAL admission rule (the inline R138
rule in adapters._lean_mechanism_space) with eight binding scenarios —
the auditor's negative/positive classes. Whatever the rule admits or
refuses is the measured fact; nothing here inspects source text as
evidence.

Output: eval/r139s2_verifier_c0218_c0219.json
"""
from __future__ import annotations
import json
import sys
import unittest.mock as mock
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine import adapters, mechanism_space as ms  # noqa: E402
from discovery_fabric.engine.candidate import Candidate  # noqa: E402

OUT = REPO / "eval" / "r139s2_verifier_c0218_c0219.json"

# the r453-lean-core fixture (the PROVEN working domain-anchor pair:
# the engine's domain check rejects off-domain probes, so the binding
# probe isolates the ADMISSION variable on a known-good domain)
PROBLEM = {
    "device": "arthroscopic irrigation system",
    "failure_mode": "pressure swings outside the target band",
    "constraint": "no pump hardware replacement",
}
FROZEN = {
    "id": "doi:10.1080/15567036.2023.2216170",
    "title": "Arthroscopic irrigation pressure control in ambulatory "
             "knee surgery",
    "abstract": ("Intra-articular pressure during arthroscopic surgery "
                 "of the knee stays inside the 40-60 mmHg band when the "
                 "inflow bag height and the shaver outflow resist are "
                 "matched; mismatched outflow collapses the capsule."),
    "content_hash": "hash_test_001",
    "retrieval_timestamp": "2026-09-14T00:00:00Z",
    "source": "europepmc",
}
SPAN_OK = ("the inflow bag height and the shaver outflow resist are "
           "matched")
CLASS_OK = {"n_items": 1, "items": [{
    "source_id": FROZEN["id"], "classification": "DIRECT_SUPPORT"}]}


def _env(evidence=None):
    env = Candidate(problem=PROBLEM, problem_id="r139s2_probe")
    env.evidence = list(evidence if evidence is not None else [FROZEN])
    env.evidence_classification = dict(CLASS_OK)
    env.provenance = {"synthesis": {
        "model": "agnes-3.0-flash", "provider": "agnes",
        "transport_status": "OK",
        "task_degradation": {
            "requested_task": "STRONG",
            "actual_task_capability": "STRONG",
            "task_capability_match": True}}}
    return env


def _binding(binding, support_state="SUPPORTED"):
    """A crafted canonical verifier verdict the REAL rule consumes."""
    return {"candidate_id": "probe", "mechanism_support_state":
            support_state, "evidence_binding": binding,
            "grounding_state": ("GROUNDED" if binding.get("grounded")
                                else "UNGROUNDED_SYNTHESIS"),
            "counts": {}, "n_items": 1, "verdicts": [],
            "contradictions_visible": [], "note": "crafted probe"}


def run_space(env, binding, support_state="SUPPORTED"):
    """Run the REAL adapter with a stubbed LLM and the crafted
    verifier verdict; return the retained candidates."""
    resp = {
        "ok": True, "status": "OK",
        "content": ("MECHANISM: matched inflow and outflow resist holds "
                    "the pressure in band; " + SPAN_OK + "\n"
                    "INTERVENTION: a passive outflow resist sleeve sized "
                    "to the shaver flow\n"
                    "EXPECTED_EFFECT: pressure stays inside the 40-60 "
                    "mmHg band\n"
                    "FALSIFICATION_TEST: measure pressure across the "
                    "commanded flow range\n"
                    "MECHANISM_SOURCE_SPAN: " + SPAN_OK + "\n"
                    "NOVEL_DESIGN_VARIABLE: the outflow resist sleeve's "
                    "flow-resistance value\n"
                    "TESTABLE_PREDICTION: doubling the inflow step keeps "
                    "the pressure within 5 mmHg of the band edge\n"),
        "provider": "agnes", "model": "agnes-3.0-flash",
        "prompt_hash": "h1", "output_hash": "h2", "latency_ms": 5,
        "task_degradation": {"requested_task": "STRONG",
                             "actual_task_capability": "STRONG",
                             "task_capability_match": True},
        "call_provenance": {}, "cost_provenance": {}}
    with mock.patch.object(ms, "llm_generate",
                           side_effect=lambda *a, **kw: dict(resp)), \
         mock.patch.object(ms, "verify_mechanism_support",
                           side_effect=lambda c, items, p:
                           _binding(binding, support_state)):
        res = adapters.MechanismSpaceAdapter().execute(
            env, {"run_id": "r139s2_probe"})
    space = res["apply_to"]["mechanism_space"]
    return space.get("candidates") or [], space


def probe_admission(name, binding, support_state="SUPPORTED",
                    evidence=None):
    cands, space = run_space(_env(evidence), binding, support_state)
    adm = [c for c in cands if c.get("discovery_admissible")]
    return {
        "probe": name,
        "binding": binding,
        "support_state": support_state,
        "n_retained": len(cands),
        "admitted": bool(adm),
        "lifecycle": (adm[0].get("candidate_lifecycle") if adm else
                      (cands[0].get("candidate_lifecycle")
                       if cands else None)),
        "n_admitted": len(adm)}


def main() -> int:
    rec = {"record": "R139S2_VERIFIER_C0218_C0219/1.0.0",
           "role": "VERIFIER (Art. 29(c)); executor = the twin's "
                   "c-0220 (r139-binding-identity-pool-gate)",
           "session": "builder-r134s2",
           "at": "2026-11-23 (sandbox clock)",
           "verified_sha": "2035f2945",
           "functional_probes": [], "data_probes": {},
           "claims_verified": {}}

    REAL = {"grounded": True, "evidence_id": FROZEN["id"],
            "span": SPAN_OK, "content_hash": FROZEN["hash"]
            if False else FROZEN["content_hash"], "word_count": 6}
    ALIAS = {"grounded": True,
             "evidence_id": "lean_" + FROZEN["id"],
             "span": SPAN_OK, "word_count": 6}
    NOHASH = {"grounded": True, "evidence_id": FROZEN["id"],
              "span": SPAN_OK, "word_count": 6}
    WRONGHASH = {"grounded": True, "evidence_id": FROZEN["id"],
                 "span": SPAN_OK, "content_hash": "hash_FORGED",
                 "word_count": 6}
    BADSPAN = {"grounded": True, "evidence_id": FROZEN["id"],
               "span": ("an eight word span that appears nowhere in "
                        "the frozen record"), "word_count": 8}

    # the auditor's negative/positive classes through the REAL rule
    rec["functional_probes"].append(probe_admission(
        "P1_synthetic_alias_admitted", ALIAS))
    rec["functional_probes"].append(probe_admission(
        "P2_hash_absent_admitted", NOHASH))
    rec["functional_probes"].append(probe_admission(
        "P3_hash_forged_admitted", WRONGHASH))
    rec["functional_probes"].append(probe_admission(
        "P4_span_not_in_record_admitted", BADSPAN))
    rec["functional_probes"].append(probe_admission(
        "P5_positive_valid_binding_admitted", REAL))
    rec["functional_probes"].append(probe_admission(
        "P6_positive_partial_support_admitted_distinct", REAL,
        "PARTIALLY_SUPPORTED"))
    rec["functional_probes"].append(probe_admission(
        "P7_contradiction_refused", REAL, "CONTESTED"))
    rec["functional_probes"].append(probe_admission(
        "P8_unknown_evidence_refused", REAL, "NOT_ENOUGH_EVIDENCE"))
    dup = dict(FROZEN)
    rec["functional_probes"].append(probe_admission(
        "P9_duplicate_id_ambiguity", REAL,
        evidence=[FROZEN, dup]))

    # the producer's alias emission (functional, the real instrument)
    lean_item = {"item_id": "lean_" + FROZEN["id"],
                 "fields": {"system": {"value": FROZEN["title"]},
                            "abstract": {"value": FROZEN["abstract"]}},
                 "_record_text": FROZEN["title"] + ". " +
                                 FROZEN["abstract"]}
    id_item = dict(lean_item)
    id_item["id"] = FROZEN["id"]
    MECH = "the coil stays clear when " + SPAN_OK + " the frost"
    rec["data_probes"]["producer_alias_emission"] = {
        "probe": "the REAL _verbatim_eight_word_binding on a lean "
                 "item WITHOUT the frozen id",
        "emitted_evidence_id": ms._verbatim_eight_word_binding(
            MECH, [lean_item]).get("evidence_id"),
        "grounded": bool(ms._verbatim_eight_word_binding(
            MECH, [lean_item]).get("grounded")),
        "with_frozen_id_emits": ms._verbatim_eight_word_binding(
            MECH, [id_item]).get("evidence_id"),
        "hash_in_binding": ("content_hash" in
                            (ms._verbatim_eight_word_binding(
                                MECH, [id_item]) or {}))}

    # the committed R138 HVAC bindings resolved against the frozen set
    base = REPO / "eval" / "r138_fresh_runs"
    run = json.loads((base / "r138-fresh-04-hvac-coil-freezing.json")
                     .read_text())
    env_ms = json.loads((base / "r138-fresh-04-hvac-coil-freezing" /
                         "envelope_MECHANISM_SPACE.json").read_text())
    cands = (env_ms.get("mechanism_space") or {}).get("candidates") or []
    adm = [c for c in cands if c.get("discovery_admissible")]
    freeze = json.loads((base / "r138-fresh-04-hvac-coil-freezing" /
                         "envelope_FREEZE.json").read_text())
    frozen_ids = [str(r.get("id")) for r in
                  (freeze.get("evidence") or freeze.get("items") or
                   (freeze.get("provenance") or {}).get("evidence") or [])]
    if not frozen_ids:
        # the freeze envelope shape varies; look one level deeper
        def _walk_ids(o, acc):
            if isinstance(o, dict):
                if o.get("id") and (o.get("content_hash") or
                                    o.get("title")):
                    acc.append(str(o["id"]))
                for v in o.values():
                    _walk_ids(v, acc)
            elif isinstance(o, list):
                for v in o:
                    _walk_ids(v, acc)
        _walk_ids(freeze, frozen_ids)
    frozen_ids = sorted(set(frozen_ids))
    binds = []
    for c in adm:
        b = ((c.get("mechanism_support") or {}).get("evidence_binding")
             or {})
        eid = str(b.get("evidence_id") or "")
        binds.append({
            "candidate_id": c.get("candidate_id"),
            "evidence_id": eid,
            "resolves_in_frozen_set": sum(1 for i in frozen_ids
                                          if i == eid),
            "is_synthetic_alias": eid.startswith("lean_"),
            "carries_content_hash": "content_hash" in b,
            "support_state":
                (c.get("mechanism_support") or {})
                .get("mechanism_support_state")})
    rec["data_probes"]["r138_hvac_admitted_bindings"] = {
        "n_admissible_in_mechanism_space": len(adm),
        "n_frozen_records_found": len(frozen_ids),
        "bindings": binds,
        "ranked_results_n_admissible": json.loads(
            (base / "r138-fresh-04-hvac-coil-freezing" /
             "RANKED_DISCOVERY_RESULTS.json").read_text()
        ).get("n_admissible"),
        "ranked_packages": json.loads(
            (base / "r138-fresh-04-hvac-coil-freezing" /
             "RANKED_PACKAGE_RECORDS.json").read_text()).get("packages")}

    # c-0219 Agnes 3/3 claim: recompute transport attribution per run
    agnes = {}
    for f in sorted(base.glob("r138-fresh-*.json")):
        d = json.loads(f.read_text())
        ta = d.get("transport_attribution") or {}
        provs, mods = ta.get("mechanism_space_providers") or [], \
            ta.get("mechanism_space_models") or []
        fs = d.get("final_status")
        blocks = ((d.get("generated_blocks") or {})
                  .get("value") if isinstance(
                      d.get("generated_blocks"), dict) else
                  d.get("generated_blocks"))
        starved = (not blocks)  # zero parsed hypothesis blocks = the
        # run starved BEFORE mechanism generation (the twin's typed
        # NO_EVIDENCE starvation class; final_status is NOT the marker
        # — all five runs end INVENTION_REQUIRES_EXPERIMENT)
        agnes[f.stem] = {
            "providers": provs, "models": mods,
            "final_status": fs,
            "starved_before_generation": starved,
            "agnes_served_generation": bool(
                provs == ["agnes"] and mods == ["agnes-3.0-flash"])}
    executed = [k for k, v in agnes.items()
                if not v["starved_before_generation"]]
    agnes_ok = all(agnes[k]["agnes_served_generation"]
                   for k in executed)
    rec["claims_verified"]["c0219_agnes_3_of_3_executed"] = {
        "per_run": agnes, "n_executed_generation": len(executed),
        "all_executed_served_by_agnes_3_0_flash": agnes_ok,
        "claim_holds": bool(agnes_ok and len(executed) == 3)}

    # c-0219 panel 120/119 claim: recount the committed legs
    v2 = REPO / "eval" / "r136_panel_v2"
    legs = list(v2.glob("*__*.json"))
    n_valid = sum(1 for f in legs
                  if json.loads(f.read_text()).get("outcome") == "VALID")
    rec["claims_verified"]["c0219_panel_recount"] = {
        "n_legs_committed": len(legs), "n_valid": n_valid,
        "claim_120_recorded_119_valid": bool(
            len(legs) == 120 and n_valid == 119)}

    # c-0218 R137 multi-mechanism: the R138 reconciliation corrected it
    recon = REPO / "eval" / "r138_reconcile" / "reconciliation.json"
    for cand_path in (REPO / "eval").glob("r138*reconcil*"):
        rec["data_probes"].setdefault("r137_reconciliation_files",
                                      []).append(cand_path.name)

    OUT.write_text(json.dumps(rec, indent=1) + "\n")
    brief = {
        "P1_alias_admitted": rec["functional_probes"][0]["admitted"],
        "P2_hash_absent_admitted":
            rec["functional_probes"][1]["admitted"],
        "P3_hash_forged_admitted":
            rec["functional_probes"][2]["admitted"],
        "P4_bad_span_admitted": rec["functional_probes"][3]["admitted"],
        "P5_valid_admitted": rec["functional_probes"][4]["admitted"],
        "P6_partial_admitted_distinct":
            rec["functional_probes"][5]["admitted"],
        "P7_contested_refused":
            not rec["functional_probes"][6]["admitted"],
        "P8_unknown_refused":
            not rec["functional_probes"][7]["admitted"],
        "P9_duplicate_id_admitted":
            rec["functional_probes"][8]["admitted"],
        "producer_emits_alias":
            rec["data_probes"]["producer_alias_emission"][
                "emitted_evidence_id"],
        "hvac_bindings": rec["data_probes"][
            "r138_hvac_admitted_bindings"]["bindings"],
        "agnes_claim_holds": rec["claims_verified"][
            "c0219_agnes_3_of_3_executed"]["claim_holds"],
        "panel_claim_holds": rec["claims_verified"][
            "c0219_panel_recount"]["claim_120_recorded_119_valid"]}
    print(json.dumps(brief, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
