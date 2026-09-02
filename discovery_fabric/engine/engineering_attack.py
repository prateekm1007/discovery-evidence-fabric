"""discovery_fabric/engine/engineering_attack.py — CEO E15-F/E15-G/E15-H.

E15-F — ADVERSARIAL ENGINEERING MODEL. The attacker challenges a generated
engineering artifact on TEN specific targets (the CEO list):

    mechanism_feasibility, equation_applicability, critical_assumptions,
    parameter_values, novelty, obviousness, failure_modes,
    manufacturing_feasibility, regulatory_assumption, buyer_value

Every attack item ends in exactly one verdict:

    KILL      — a defect that invalidates the candidate; the candidate gets
                NO dossier.
    REPAIR    — a defect the repair pass can fix by MUTATING the engineering
                artifact itself (E15-G).
    UNCERTAIN — a genuine open question; bound to the decisive experiment
                and the buyer-diligence register (never silently resolved).
    SURVIVE   — the artifact's content answers the challenge with recorded
                evidence.

E15-G — AUTOMATIC REPAIR WITH ARTIFACT MUTATION. A REPAIR verdict must
change the engineering artifact STRUCTURALLY (a new block entry, a changed
verdict, a new linkage) — the ledger records before/after content hashes
per mutated node. A cosmetic-only repair is recorded as repair_failed and
NEVER passes the gate ("the engineering artifact itself must mutate").

E15-H — RELEASE ONLY THE STRONGEST SURVIVOR. From a candidate set, all
candidates are attacked; killed candidates get no package; viable ones are
repaired (mutated to V2) and compared with the E15-B quality evaluator;
only the strongest survivor(s) reach full dossier generation. Discovery
quality comes before document production.

Everything here is DETERMINISTIC and reads only recorded artifacts (no LLM
call is needed to attack — an attack that depends on the same model that
produced the claim would share its blind spots, the exact failure E15-E
exists to remove).
"""
from __future__ import annotations

import copy
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

VERDICT_KILL = "KILL"
VERDICT_REPAIR = "REPAIR"
VERDICT_UNCERTAIN = "UNCERTAIN"
VERDICT_SURVIVE = "SURVIVE"
VERDICTS = (VERDICT_KILL, VERDICT_REPAIR, VERDICT_UNCERTAIN,
            VERDICT_SURVIVE)

# the ten CEO E15-F attack targets
ATTACK_TARGETS = ("mechanism_feasibility", "equation_applicability",
                  "critical_assumptions", "parameter_values", "novelty",
                  "obviousness", "failure_modes", "manufacturing_feasibility",
                  "regulatory_assumption", "buyer_value")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z"


def _sha(obj: Any) -> str:
    from .candidate import sha256_obj
    return sha256_obj(obj)


# --------------------------------------------------------------------------
# E15-F: the attack itself
# --------------------------------------------------------------------------
def attack_engineering(spec: Dict[str, Any], eng: Dict[str, Any],
                       env: Optional[Any] = None) -> Dict[str, Any]:
    """Run the ten-target adversarial engineering attack. Deterministic;
    every verdict carries its basis and the affected claim ids."""
    items: List[Dict[str, Any]] = []
    mech = ((spec.get("mechanism") or {}).get("value") or {})
    problem = ((spec.get("problem") or {}).get("value") or {})
    core = eng.get("engineering_core") or {}
    gm = core.get("governing_model") or {}
    equations = gm.get("equations", []) or []
    rejected = gm.get("rejected_equations", []) or []
    params = core.get("critical_parameters", []) or []
    fms = eng.get("failure_analysis", []) or []
    mfg = eng.get("manufacturing") or {}
    reg = eng.get("regulatory") or {}
    tb = eng.get("transfer_boundary") or {}
    kc = eng.get("kill_condition") or {}
    dist = ((spec.get("distinguishing_features") or {}).get("value") or {})
    novelty = ((spec.get("novelty_hypothesis") or {}).get("value") or {})

    def item(target: str, verdict: str, basis: str,
             affected: Optional[List[str]] = None,
             repair_hint: str = "") -> Dict[str, Any]:
        if verdict not in VERDICTS:
            raise ValueError(f"invalid attack verdict {verdict!r}")
        return {"target": target, "verdict": verdict, "basis": basis,
                "affected_claim_ids": list(affected or []),
                "repair_hint": repair_hint,
                "attacked_at": utc_now()}

    # 1. mechanism_feasibility ------------------------------------------------
    fals = str(kc.get("falsification_test") or
               mech.get("falsification_test") or "").strip()
    falsifiable = bool(fals) and not fals.upper().startswith(
        "NOT ESTABLISHED")
    has_model = bool(equations)
    if not falsifiable and not has_model:
        items.append(item(
            "mechanism_feasibility", VERDICT_KILL,
            "mechanism is neither falsifiable (no falsification test) nor "
            "modelled (no governing equation) — nothing to engineer",
            ["mechanism"]))
    elif not falsifiable:
        items.append(item(
            "mechanism_feasibility", VERDICT_REPAIR,
            "no falsification test is bound to the kill condition — the "
            "mechanism cannot be experimentally refuted as stated",
            ["kill_condition.falsification_test"],
            repair_hint="bind falsification_test into kill_condition"))
    elif not has_model:
        items.append(item(
            "mechanism_feasibility", VERDICT_UNCERTAIN,
            "mechanism is falsifiable but carries no governing engineering "
            "model — feasibility is unquantified",
            ["governing_model"]))
    else:
        items.append(item(
            "mechanism_feasibility", VERDICT_SURVIVE,
            f"falsifiable mechanism + {len(equations)} governing "
            "equation(s) with applicability verdicts", ["mechanism"]))

    # 2. equation_applicability ----------------------------------------------
    unjudged = [e.get("equation_id") for e in equations
                if not str(((e.get("selection_rationale") or {})
                            .get("verdict")) or "").strip()]
    conflicting = [e.get("equation_id") for e in equations
                   if ((e.get("selection_rationale") or {})
                       .get("assumption_check") or {}).get("violations")]
    if unjudged:
        items.append(item(
            "equation_applicability", VERDICT_REPAIR,
            f"equations without an applicability verdict: {unjudged}",
            unjudged, repair_hint="re-judge or exclude unjudged equations"))
    elif conflicting:
        items.append(item(
            "equation_applicability", VERDICT_UNCERTAIN,
            f"selected equations carry recorded assumption violations: "
            f"{conflicting} — applicability is CONDITIONAL until the "
            "violation is tested", conflicting))
    elif not equations and not rejected:
        items.append(item(
            "equation_applicability", VERDICT_REPAIR,
            "governing model is empty AND nothing was rejected — the "
            "domain equation pass did not run",
            ["governing_model.equations"],
            repair_hint="re-run domain equation selection"))
    else:
        items.append(item(
            "equation_applicability", VERDICT_SURVIVE,
            f"{len(equations)} selected with verdicts, "
            f"{len(rejected)} rejected with reasons (A4 proof)", []))

    # 3. critical_assumptions --------------------------------------------------
    assumptions = gm.get("assumptions", []) or []
    if not assumptions:
        items.append(item(
            "critical_assumptions", VERDICT_REPAIR,
            "governing model states NO assumptions — an unassumed model "
            "hides its failure conditions",
            ["governing_model.assumptions"],
            repair_hint="import domain model_assumptions"))
    else:
        untested = [a for a in assumptions
                    if not str(((a if isinstance(a, dict) else {})
                                .get("test")) or "").strip()]
        if len(untested) == len(assumptions):
            items.append(item(
                "critical_assumptions", VERDICT_UNCERTAIN,
                f"{len(assumptions)} assumptions recorded, none carries its "
                "own falsification path — all remain open",
                ["governing_model.assumptions"]))
        else:
            items.append(item(
                "critical_assumptions", VERDICT_SURVIVE,
                "assumptions recorded with falsification paths",
                ["governing_model.assumptions"]))

    # 4. parameter_values -------------------------------------------------------
    naked = []
    unknowns = []
    for p in params:
        status = str(p.get("value_status", "UNKNOWN")).upper()
        val = p.get("value")
        if status == "UNKNOWN":
            unknowns.append(p.get("parameter_id"))
            continue
        if isinstance(val, (int, float)) and not p.get("source"):
            naked.append(p.get("parameter_id"))
        if isinstance(val, str) and re.fullmatch(
                r"[-+]?\d*\.?\d+([eE][-+]?\d+)?", val.strip() or "x"):
            naked.append(p.get("parameter_id"))
    if naked:
        items.append(item(
            "parameter_values", VERDICT_KILL,
            f"NAKED NUMBERS without provenance: {naked} — a fabricated "
            "value invalidates the artifact (Art. VIII)",
            naked))
    elif params and len(unknowns) == len(params):
        items.append(item(
            "parameter_values", VERDICT_UNCERTAIN,
            f"all {len(params)} critical parameters are unsourced "
            "(UNKNOWN) — the design is parameterized but unmeasured; "
            "bound to the decisive experiment",
            unknowns))
    else:
        items.append(item(
            "parameter_values", VERDICT_SURVIVE,
            f"{len(params) - len(unknowns)}/{len(params)} parameters carry "
            f"status+provenance; {len(unknowns)} honestly UNKNOWN", []))

    # 5. novelty ------------------------------------------------------------------
    risk = str(novelty.get("collision_novelty_risk") or "").upper()
    prior = str(((spec.get("prior_art") or {}).get("value") or {})
                .get("status") or "")
    if "HIGH" in risk:
        items.append(item(
            "novelty", VERDICT_KILL,
            f"collision stage recorded novelty risk {risk} — the idea is "
            "likely not new", ["novelty_hypothesis"]))
    elif "UNRESOLVED" in prior.upper():
        items.append(item(
            "novelty", VERDICT_UNCERTAIN,
            "prior-art search left unresolved sources — novelty is "
            "unproven, not disproven", ["prior_art"]))
    else:
        items.append(item(
            "novelty", VERDICT_SURVIVE,
            f"novelty risk {risk or 'RECORDED'} bounded by searched "
            "sources (hypothesis, not proof)", ["novelty_hypothesis"]))

    # 6. obviousness ----------------------------------------------------------------
    vs = dist.get("vs_nearest_prior_art", []) or []
    if not vs:
        items.append(item(
            "obviousness", VERDICT_UNCERTAIN,
            "no nearest prior-art comparison recorded — non-obviousness "
            "cannot be argued from the artifact",
            ["distinguishing_features.vs_nearest_prior_art"]))
    else:
        items.append(item(
            "obviousness", VERDICT_SURVIVE,
            f"{len(vs)} nearest prior-art comparison(s) recorded; "
            "differences asserted pending claim audit",
            ["distinguishing_features.vs_nearest_prior_art"]))

    # 7. failure_modes -----------------------------------------------------------
    n_phys = sum(1 for f in fms
                 if f.get("content_class") == "PHYSICAL_MECHANISM")
    n_generic = len(fms) - n_phys
    unlinked = [f.get("graph_id") for f in fms
                if f.get("verification") in ("NOT_LINKED", None, "")]
    if not fms:
        items.append(item(
            "failure_modes", VERDICT_KILL,
            "failure analysis is EMPTY — nothing has been challenged",
            ["failure_analysis"]))
    elif n_phys == 0:
        items.append(item(
            "failure_modes", VERDICT_REPAIR,
            "no failure row carries a physical mechanism (all generic "
            "adversarial placeholders) — E15-D requires mechanism-tied "
            "analysis", [f.get("graph_id") for f in fms],
            repair_hint="cross-reference domain failure mechanisms"))
    elif unlinked:
        items.append(item(
            "failure_modes", VERDICT_REPAIR,
            f"failure modes without linked verification: {unlinked}",
            unlinked,
            repair_hint="link each failure mode to a planned verification"))
    else:
        items.append(item(
            "failure_modes", VERDICT_SURVIVE,
            f"{n_phys} physical mechanisms + {n_generic} honest generic "
            "placeholders, all linked to planned verifications", []))

    # 8. manufacturing_feasibility ---------------------------------------------------
    procs = mfg.get("candidate_processes", []) or []
    tied = [p for p in procs
            if ((p.get("invention_tie") or {}).get("invention_tied"))]
    if not procs or all(str(p.get("status", "")) == "UNKNOWN"
                        for p in procs):
        items.append(item(
            "manufacturing_feasibility", VERDICT_REPAIR,
            "no manufacturing process candidate recorded — transfer "
            "reasoning is absent", ["manufacturing.candidate_processes"],
            repair_hint="import domain manufacturing routes"))
    elif not tied:
        items.append(item(
            "manufacturing_feasibility", VERDICT_UNCERTAIN,
            f"{len(procs)} process candidates, none tied to THIS invention "
            "(generic routes) — applicability is an open question",
            ["manufacturing.candidate_processes"]))
    else:
        items.append(item(
            "manufacturing_feasibility", VERDICT_SURVIVE,
            f"{len(tied)}/{len(procs)} process candidates tied to this "
            "invention (candidates only; no qualification claimed)", []))

    # 9. regulatory_assumption --------------------------------------------------------
    pathway = str(reg.get("pathway", "UNKNOWN"))
    standards = reg.get("candidate_standards", []) or []
    if pathway.upper() != "UNKNOWN" and not reg.get("basis"):
        items.append(item(
            "regulatory_assumption", VERDICT_KILL,
            f"regulatory pathway '{pathway}' asserted WITHOUT recorded "
            "basis — a fabricated regulatory determination (R370C)",
            ["regulatory.pathway"]))
    elif standards:
        items.append(item(
            "regulatory_assumption", VERDICT_SURVIVE,
            f"pathway honestly UNKNOWN; {len(standards)} candidate "
            "standards recorded with applicability verification required",
            ["regulatory.candidate_standards"]))
    else:
        items.append(item(
            "regulatory_assumption", VERDICT_REPAIR,
            "no candidate standards and no pathway — the regulatory "
            "surface is not even enumerated",
            ["regulatory.candidate_standards"],
            repair_hint="import domain standards candidates"))

    # 10. buyer_value --------------------------------------------------------------------
    receives = tb.get("buyer_receives", []) or []
    builds = tb.get("buyer_must_create", []) or []
    if not receives or not builds:
        items.append(item(
            "buyer_value", VERDICT_REPAIR,
            f"transfer boundary incomplete: receives={len(receives)} "
            f"builds={len(builds)} — the buyer cannot price the offer",
            ["transfer_boundary"],
            repair_hint="enumerate buyer receives/builds"))
    else:
        items.append(item(
            "buyer_value", VERDICT_SURVIVE,
            f"buyer receives {len(receives)} deliverables, must create "
            f"{len(builds)} — the transfer is bidirectionally explicit",
            ["transfer_boundary"]))

    # coverage assertion: the attack must address ALL ten targets
    seen = {i["target"] for i in items}
    missing = [t for t in ATTACK_TARGETS if t not in seen]
    if missing:
        raise RuntimeError(
            f"E15-F attack coverage gap: targets never challenged: {missing}")

    return {
        "attack": "ENGINEERING_ATTACK (E15-F)",
        "version": "1.0.0",
        "targets": list(ATTACK_TARGETS),
        "items": items,
        "counts": {v: sum(1 for i in items if i["verdict"] == v)
                   for v in VERDICTS},
        "overall": ("KILLED" if any(i["verdict"] == VERDICT_KILL
                                    for i in items)
                    else "NEEDS_REPAIR" if any(i["verdict"] == VERDICT_REPAIR
                                               for i in items)
                    else "SURVIVED_WITH_UNCERTAINTIES"
                    if any(i["verdict"] == VERDICT_UNCERTAIN for i in items)
                    else "SURVIVED"),
        "attacked_at": utc_now(),
        "artifact_hash": _sha({"spec": spec, "eng": eng}),
    }


# --------------------------------------------------------------------------
# E15-G: repair pass — the engineering artifact itself must mutate
# --------------------------------------------------------------------------
def _structural_mutations(eng: Dict[str, Any], attack: Dict[str, Any],
                          spec: Dict[str, Any],
                          ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Apply the REPAIR verdicts as targeted structural mutations.
    Returns (repair_ledger, mutated_paths). Every mutation is recorded with
    before/after content hashes of the mutated node."""
    from .domains import get_domain_module, detect_domain, domain_label
    from .engineering_spec import _propose_acceptance
    ledger: List[Dict[str, Any]] = []
    mutated: List[str] = []
    eng2 = copy.deepcopy(eng)

    def node_hash(path: str, node: Any) -> str:
        return _sha(node)

    def record(rid: str, target: str, verdict_id: str, path: str,
               before: Any, after: Any, summary: str) -> None:
        entry = {
            "repair_id": rid, "attack_target": target,
            "attack_verdict_id": verdict_id, "mutated_path": path,
            "before_hash": node_hash(path, before),
            "after_hash": node_hash(path, after),
            "change_summary": summary,
            "mutation_kind": "STRUCTURAL",
        }
        if node_hash(path, before) == node_hash(path, after):
            entry["mutation_kind"] = "NO_CHANGE"
        ledger.append(entry)
        if entry["mutation_kind"] == "STRUCTURAL":
            mutated.append(path)

    core = eng2.setdefault("engineering_core", {})
    gm = core.setdefault("governing_model", {})
    mech = ((spec.get("mechanism") or {}).get("value") or {})
    domain = eng2.get("technology_domain", "UNKNOWN")
    if domain == "NOT ESTABLISHED":
        domain = "UNKNOWN"
    module = get_domain_module(domain)

    for it in attack.get("items", []):
        if it["verdict"] != VERDICT_REPAIR:
            continue
        target, hint = it["target"], it["repair_hint"]
        rid = f"RP-{target}"

        if target == "mechanism_feasibility" and "falsification" in hint:
            kc2 = eng2.setdefault("kill_condition", {})
            before = dict(kc2)
            fals = (mech.get("falsification_test", "")
                    or ((spec.get("killer_experiment") or {}).get("value")
                        or {}).get("definition", ""))
            if fals:
                kc2["falsification_test"] = fals
                kc2["repair_note"] = (
                    "E15-G repair: falsification test bound to the kill "
                    "condition by the adversarial engineering pass")
                record(rid, target, it["basis"],
                       "kill_condition", before, kc2,
                       "falsification test bound into kill_condition")

        elif target == "equation_applicability" and "re-judge" in hint:
            # unjudged equations are EXCLUDED from the governing model and
            # moved to rejected_equations with an explicit reason — a
            # structural removal, never a silent fix
            before = copy.deepcopy(gm.get("equations", []))
            keep, moved = [], []
            for e in gm.get("equations", []):
                if str(((e.get("selection_rationale") or {})
                        .get("verdict")) or "").strip():
                    keep.append(e)
                else:
                    moved.append({
                        "equation_id": e.get("equation_id"),
                        "name": e.get("name"),
                        "rejection_reason":
                            "E15-G repair: equation reached the governing "
                            "model without an applicability verdict; "
                            "excluded and recorded (was: selected)"})
            if moved:
                gm["equations"] = keep
                gm.setdefault("rejected_equations", []).extend(moved)
                record(rid, target, it["basis"],
                       "governing_model.equations", before, keep,
                       f"{len(moved)} unjudged equation(s) excluded with "
                       "reasons")

        elif target == "critical_assumptions":
            before = copy.deepcopy(gm.get("assumptions", []))
            # the domain registry stores model assumptions per governing
            # model ({model, assumptions[...]}); flatten them so the repair
            # imports the domain's actual assumption content (Art. VI:
            # recorded content, never invented)
            imported: List[Dict[str, Any]] = []
            for entry in (module.get("model_assumptions", []) or []):
                if isinstance(entry, dict):
                    model_name = str(entry.get("model", ""))
                    for a in entry.get("assumptions", []) or []:
                        imported.append({
                            "assumption": str(a),
                            "basis": f"ENGINEERING_PROPOSED (E15-G repair: "
                                     f"domain model assumption imported "
                                     f"from '{model_name}')",
                            "test": "falsification path to be defined by "
                                    "the first characterization"})
                elif isinstance(entry, str):
                    imported.append({
                        "assumption": entry,
                        "basis": "ENGINEERING_PROPOSED (E15-G repair: "
                                 "domain model assumption imported by the "
                                 "adversarial pass)",
                        "test": "falsification path to be defined by the "
                                "first characterization"})
            existing = {a.get("assumption") if isinstance(a, dict)
                        else str(a) for a in before}
            new = [a for a in imported
                   if a["assumption"] not in existing]
            if new:
                gm["assumptions"] = list(before) + new
                record(rid, target, it["basis"],
                       "governing_model.assumptions", before,
                       gm["assumptions"],
                       f"{len(new)} domain assumption(s) imported")

        elif target == "failure_modes" and "cross-reference" in hint:
            # re-run the domain mechanism cross-reference over generic rows
            from .engineering_spec import (_domain_mechanism_for_attack,
                                           _invention_tokens)
            tokens = _invention_tokens(spec)
            before_fms = copy.deepcopy(eng2.get("failure_analysis", []))
            changed = 0
            for row in eng2.get("failure_analysis", []):
                if row.get("content_class") != "GENERIC_ADVERSARIAL_PLACEHOLDER":
                    continue
                cross = _domain_mechanism_for_attack(
                    str(row.get("mode", "")) + " " +
                    str(row.get("physical_mechanism", "")), module, tokens)
                if cross:
                    row["physical_mechanism"] = cross["physical_mechanism"]
                    row["trigger"] = cross.get("trigger", "NOT ESTABLISHED")
                    row["detectability"] = cross.get(
                        "detectability", "NOT ESTABLISHED")
                    row["content_class"] = "PHYSICAL_MECHANISM"
                    row["mechanism_provenance"] = {
                        "source": "E15-G repair: domain-registry "
                                  "cross-reference",
                        "domain_mode": cross.get("mode", "")}
                    changed += 1
            if changed:
                record(rid, target, it["basis"],
                       "failure_analysis", before_fms,
                       eng2.get("failure_analysis"),
                       f"{changed} generic row(s) upgraded to physical "
                       "mechanisms via domain cross-reference")

        elif target == "failure_modes" and "link" in hint:
            before_vf = copy.deepcopy(eng2.get("verification_matrix", []))
            before_fms = copy.deepcopy(eng2.get("failure_analysis", []))
            vf_n = len(before_vf)
            linked = 0
            vf_ids = {v.get("id") for v in before_vf}
            for row in eng2.get("failure_analysis", []):
                if row.get("verification") in ("NOT_LINKED", None, ""):
                    vf_n += 1
                    vid = f"VF-{vf_n:03d}"
                    method = ("killer-experiment measurement (adversarial "
                              "probe exposure)")
                    before_vf.append({
                        "id": vid, "requirement": method, "method": method,
                        "acceptance": "pre-registered rule (E15-G repair)",
                        "acceptance_status": "ENGINEERING_PROPOSED",
                        "result": "NOT_TESTED",
                        "invention_tie": {"linkage_kind": "e15g_repair",
                                          "targets": [row.get("graph_id")]}})
                    row["verification"] = vid
                    row["verification_test"] = vid
                    linked += 1
                    vf_ids.add(vid)
            if linked:
                eng2["verification_matrix"] = before_vf
                record(rid + "-VF", target, it["basis"],
                       "verification_matrix", None, before_vf,
                       f"{linked} failure row(s) linked to new planned "
                       "verifications")
                record(rid + "-FM", target, it["basis"],
                       "failure_analysis.verification", before_fms,
                       eng2.get("failure_analysis"),
                       "verification links recorded on failure rows")

        elif target == "manufacturing_feasibility":
            before = copy.deepcopy(eng2.get("manufacturing", {}))
            routes = module.get("manufacturing_routes", []) or []
            procs = (eng2.get("manufacturing", {})
                     .setdefault("candidate_processes", []))
            had = {str(p.get("process", "")) for p in procs}
            added = 0
            for r in routes:
                proc = r.get("process", r) if isinstance(r, dict) else r
                if str(proc) in had:
                    continue
                procs.append({
                    "process": str(proc), "status": "ENGINEERING_PROPOSED",
                    "source": "E15-G repair: domain manufacturing route "
                              "imported by the adversarial pass",
                    "note": "candidate only; no process qualification exists",
                    "invention_tie": {"invention_tied": False,
                                      "note": "tie to be established by "
                                              "design work"}})
                added += 1
            if added:
                eng2["manufacturing"] = {**eng2.get("manufacturing", {})}
                record(rid, target, it["basis"],
                       "manufacturing.candidate_processes", before,
                       eng2["manufacturing"],
                       f"{added} domain manufacturing route(s) imported")

        elif target == "regulatory_assumption":
            before = copy.deepcopy(eng2.get("regulatory", {}))
            stds = (eng2.get("regulatory", {})
                    .setdefault("candidate_standards", []))
            had = {str(s.get("standard", "")) for s in stds
                   if isinstance(s, dict)}
            added = 0
            for s in module.get("standards_candidates", []):
                name = s.get("standard", "") if isinstance(s, dict) else str(s)
                if name and name not in had:
                    stds.append({"standard": name,
                                 "class": "EXTERNAL_PRECEDENT_CANDIDATE",
                                 "verify_applicability": True,
                                 "repair_note": "E15-G: imported by the "
                                                "adversarial pass"})
                    added += 1
            if added:
                eng2["regulatory"] = {**eng2.get("regulatory", {})}
                record(rid, target, it["basis"],
                       "regulatory.candidate_standards", before,
                       eng2["regulatory"],
                       f"{added} candidate standard(s) imported")

        elif target == "buyer_value":
            before = copy.deepcopy(eng2.get("transfer_boundary", {}))
            tb2 = eng2.setdefault("transfer_boundary", {})
            changed = False
            if not tb2.get("buyer_receives"):
                tb2["buyer_receives"] = [
                    "invention specification (classed)",
                    "engineering specification (classed)",
                    "evidence custody references"]
                changed = True
            if not tb2.get("buyer_must_create"):
                tb2["buyer_must_create"] = [
                    "detailed design and geometry",
                    "sourced parameters and acceptance thresholds",
                    "all verification and validation results"]
                changed = True
            if changed:
                tb2["repair_note"] = ("E15-G: transfer boundary completed "
                                      "by the adversarial pass")
                record(rid, target, it["basis"],
                       "transfer_boundary", before, tb2,
                       "buyer receives/builds enumerated")

    return eng2, ledger, mutated


def repair_engineering(spec: Dict[str, Any], eng: Dict[str, Any],
                       attack: Dict[str, Any]) -> Dict[str, Any]:
    """E15-G: apply repairs and produce ENGINEERING SPEC V2. The repair is
    valid ONLY if the artifact structurally mutated (hash change AND >= 1
    structural mutation); otherwise the repair is recorded as failed and
    the candidate keeps its V1 (honest, no cosmetic pass-off)."""
    eng_before_hash = _sha(eng)
    eng2, ledger, mutated = _structural_mutations(eng, attack, spec)
    eng_after_hash = _sha(eng2)
    structural = [e for e in ledger if e["mutation_kind"] == "STRUCTURAL"]
    mutated_artifact = (eng_after_hash != eng_before_hash
                        and bool(structural))
    repaired = dict(eng2)
    repaired["spec_version"] = 2
    repaired["repaired_from_hash"] = eng_before_hash
    repaired["repair_ledger"] = {
        "rule": ("E15-G: the engineering artifact itself must mutate; "
                 "cosmetic sentence changes do not pass. Every mutation "
                 "records before/after node hashes."),
        "mutations": ledger,
        "structural_mutation_count": len(structural),
        "mutated_paths": sorted(set(mutated)),
        "artifact_mutated": mutated_artifact,
        "before_artifact_hash": eng_before_hash,
        "after_artifact_hash": eng_after_hash,
        "repaired_at": utc_now(),
    }
    if not mutated_artifact:
        repaired["repair_ledger"]["outcome"] = (
            "REPAIR_FAILED — no structural mutation was possible; "
            "candidate keeps V1 honestly")
    else:
        # re-run the attack on the mutated artifact: the repair must be
        # visible to the attacker too (no self-congratulation)
        reattack = attack_engineering(spec, repaired)
        repaired["repair_ledger"]["post_repair_attack"] = {
            "overall": reattack["overall"],
            "counts": reattack["counts"],
            "remaining_repairs": [i["target"] for i in reattack["items"]
                                  if i["verdict"] == VERDICT_REPAIR],
        }
    return repaired


# --------------------------------------------------------------------------
# E15-H: strongest-survivor selection
# --------------------------------------------------------------------------
def select_survivors(candidates: List[Dict[str, Any]]
                     ) -> Dict[str, Any]:
    """E15-H selection over attacked (+repaired, +quality-evaluated)
    candidates. Each candidate dict carries:
        candidate_id, attack (post-repair), quality (E15-B result or None),
        repaired (bool), span_underived (bool, R377),
        physics_lifecycle (str, R397 Phase 2)
    Selection policy (recorded, deterministic, NOT a new numeric score):
      1. KILLed candidates are out (no dossier for the weak).
      2. R377: SPAN_UNDERIVED candidates are out — a mechanism whose
         quoted evidence span does not contain its vocabulary is a
         prior-knowledge proposal, not an evidence-derived candidate
         (CEO R377: "a higher kill rate is acceptable if the surviving
         inventions become materially better"). The flag and its
         measurement stay on the ranked record.
      3. R397 Phase 2: a candidate whose physics_lifecycle is
         DOES_NOT_BEAT_BASELINE or PLAUSIBILITY_BOUND_VIOLATED is
         INELIGIBLE for strongest-survivor selection — the release
         would claim an improvement the machine's own physics says the
         candidate does not deliver. MECHANISM_NOT_SIMULATABLE and
         INCONCLUSIVE candidates remain eligible (honest disclosure,
         never a fabricated kill — the domain refusal is not negative
         knowledge).
      4. Among the rest, prefer the better E15-B verdict
         (PASS > CONDITIONAL > FAIL); FAIL means the quality gate rejects
         the candidate. BEATS_BASELINE outranks within the same verdict
         tier (physics strength is a recorded tie-break, not a score).
      5. Tie-break: fewer deficient areas, then fewer UNCERTAIN verdicts.
      6. All comparisons and the final choice are recorded.
    """
    ranked: List[Dict[str, Any]] = []
    for c in candidates:
        attack = c.get("attack") or {}
        quality = c.get("quality") or {}
        verdict_rank = {"PASS": 0, "CONDITIONAL": 1, "FAIL": 2,
                        None: 3}.get(quality.get("verdict"), 3)
        killed = attack.get("overall") == "KILLED" \
            or bool(c.get("physics_kill"))
        underived = bool(c.get("span_underived"))
        physics_lifecycle = c.get("physics_lifecycle") \
            or "MECHANISM_NOT_SIMULATABLE"
        ranked.append({
            "candidate_id": c.get("candidate_id"),
            "killed": killed,
            "attack_overall": attack.get("overall"),
            "uncertain_count": (attack.get("counts") or {})
            .get(VERDICT_UNCERTAIN, 0),
            "quality_verdict": quality.get("verdict"),
            "quality_deficient_count": len(quality.get("deficient_areas", [])
                                           or []),
            "repaired": bool(c.get("repaired")),
            "span_underived": underived,
            "physics_lifecycle": physics_lifecycle,
            "_verdict_rank": verdict_rank,
            "_physics_rank": {"BEATS_BASELINE": 0,
                              "MECHANISM_NOT_SIMULATABLE": 1,
                              "INCONCLUSIVE": 1,
                              None: 1}.get(physics_lifecycle, 1),
        })
    eligible = [r for r in ranked if not r["killed"]
                and r["quality_verdict"] != "FAIL"
                and not r["span_underived"]
                and r["physics_lifecycle"] not in
                ("DOES_NOT_BEAT_BASELINE", "PLAUSIBILITY_BOUND_VIOLATED")]
    eligible.sort(key=lambda r: (r["_verdict_rank"], r["_physics_rank"],
                                 r["quality_deficient_count"],
                                 r["uncertain_count"]))
    selection = {
        "selection": "STRONGEST_SURVIVOR (E15-H + R397 physics gate)",
        "policy": ("kill first; SPAN_UNDERIVED candidates are ineligible "
                   "(R377 evidence-derivation requirement); R397 Phase 2: "
                   "DOES_NOT_BEAT_BASELINE and PLAUSIBILITY_BOUND_VIOLATED "
                   "candidates are ineligible for release (the machine's "
                   "own physics gates the claim); among survivors prefer "
                   "better E15-B verdict, then BEATS_BASELINE, then fewer "
                   "deficient areas, then fewer UNCERTAIN attack "
                   "outcomes; NO numeric score is computed (CEO standing "
                   "rule: no new scoring systems)"),
        "ranked": ranked,
        "selected": eligible[0]["candidate_id"] if eligible else None,
        "selection_basis": eligible[0] if eligible else None,
        "killed": [r["candidate_id"] for r in ranked if r["killed"]],
        "span_underived_excluded": [r["candidate_id"] for r in ranked
                                    if not r["killed"]
                                    and r["span_underived"]],
        "quality_rejected": [r["candidate_id"] for r in ranked
                             if not r["killed"]
                             and r["quality_verdict"] == "FAIL"],
        "physics_ineligible": [r["candidate_id"] for r in ranked
                               if not r["killed"]
                               and not r["span_underived"]
                               and r["physics_lifecycle"] in
                               ("DOES_NOT_BEAT_BASELINE",
                                "PLAUSIBILITY_BOUND_VIOLATED")],
        "physics_policy_note": (
            "R397 Phase 2: the physics verdicts are lifecycle-affecting, "
            "not report fields — DOES_NOT_BEAT_BASELINE blocks automatic "
            "release with the design-learning mutation recorded as the "
            "next candidate; PLAUSIBILITY_BOUND_VIOLATED candidates are "
            "killed before the engineering attack; MECHANISM_NOT_SIMULATABLE "
            "stays eligible with an honest disclosure (a domain refusal is "
            "not negative knowledge — Art. XXV/XXIX)"),
        "decided_at": utc_now(),
    }
    return selection
