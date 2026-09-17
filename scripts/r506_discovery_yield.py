#!/usr/bin/env python3
"""
R506 DISCOVERY YIELD INSTRUMENT — v1.0.0 (frozen)

The cycle's main build (CEO directive, "Review of the external feedback +
directive to coder", section 2): stop proving the machine works; start
measuring whether it discovers.

Single authority for the discovery-yield funnel. One row per fresh problem,
counters read from the run's OWN DURABLE BYTES — never self-reported values,
never narratives, never summaries (Art. XXIV). The instrument is observational
(Art. IX): it never writes to the run directory it reads.

FUNNEL (one row per fresh problem):

    fresh_submitted
      -> premise_coherent
      -> evidence_verified
      -> mechanisms_found
      -> candidates_generated_distinct   (DISTINCT only, Art. XLII/XLVIII)
      -> attack_survivors
      -> contradiction_survivors         (blocking_count == 0)
      -> experimentally_discriminated    (killer selected + executed/ingested)
      -> mutated_survivors               (CHILDREN_ADMITTED + delta_real + re-eval)
      -> buyer_ready                     (ZIP + lineage + VERIFIED)

Every transition carries:
  - reached: bool (from bytes)
  - evidence: the file + JSON pointer the verdict was read from
  - typed_drop_reason when lost (from the run's own typed bytes)

MID-FLIGHT RULE (Art. LXXIV): a run directory WITHOUT run_manifest.json is
MID_FLIGHT_OR_PARTIAL_PER_LXXIV — an observation, never a terminal. Aggregate
rows are computed separately for terminal and mid-flight runs and never
collapsed.

HERMETIC ACCEPTANCE (frozen with v1.0.0): the instrument, run on bytes alone,
reproduces the three known sealed terminals:
  1. R489 REJECTED pre-loop   — durable branch checkpoint 96965e28 (09:44Z),
     run ts_f0880e025e60: funnel dies at attack_survivors (obvious_combination
     KILLED among the 4 kill dimensions), no mutated survivor.
  2. R484 child-admitted      — terminal run dir toscanini_ui_ui_calcite_and_
     silica_gel_deposition_on_separ_602181: mutated_survivors >= 1
     (CHILDREN_ADMITTED, delta_real true), buyer_ready 0 (release HELD,
     package_zip null).
  3. R487 terminal closure    — terminal commit 34d81fb9, same run as (1):
     loop closed (children admitted), release HELD_FOR_HUMAN_REVIEW,
     real_loop_verified false, package_zip null.

HONESTY PINS baked into the row:
  - attacker_provenance: the run-level A2 adversarial gauntlet is NOT the
    sealed-bar-calibrated engine independent_attack instrument (R489
    composition finding). attack_survivors always carries
    RUN_LEVEL_A2_GAUNTLET (NOT_SEALED_BAR_CALIBRATED).
  - collision completeness: collision.mandatory_searches.complete=false is
    carried as NOVELTY_LEFT_UNRESOLVED_BY_RING_FAILURES (Art. XXI.3 / LXXV.2)
    — never as novelty.
  - INDETERMINATE distinctness verdicts are counted separately and never as
    inventions (Art. XLII: INDETERMINATE is legitimate, not DISTINCT).
  - cost/debit fields read from transport records when present, else typed
    UNKNOWN (Art. XXV).

Usage:
  python3 scripts/r506_discovery_yield.py --run-dir <dir> [--out FILE]
  python3 scripts/r506_discovery_yield.py --root <durability>/runs [--out FILE]
  python3 scripts/r506_discovery_yield.py --git-ref 96965e28 \
      --durability-worktree <wt> --run <slug> [--out FILE]

Determinism: byte-identical inputs produce byte-identical output (sorted
keys; no wall-clock in the payload).
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys

INSTRUMENT_ID = "r506_discovery_yield"
INSTRUMENT_VERSION = "1.0.0"
SPEC_PATH_DEFAULT = "R506/YIELD_INSTRUMENT.json"

STAGE_ORDER = ["RETRIEVE", "FREEZE", "PREMISE_GATE", "SYNTHESIZE",
               "VERIFY", "MECHANISM_SPACE", "MULTI_SOURCE_DISCOVERY",
               "COLLISION", "PHYSICS", "ATTACK", "CONTRADICTION",
               "KILLER_EXPERIMENT", "IMPROVE", "ADJUDICATION",
               "CLASSIFY", "NEXT_BEST_ACTION", "RANK"]

# typed drop-reason vocabulary (frozen — any addition is a new instrument version)
REASONS = {
    "PREMISE_INCOHERENT",
    "EVIDENCE_UNVERIFIED",
    "NO_CANDIDATES",
    "NO_DISTINCT_CANDIDATES",
    "ALL_DISTINCTNESS_INDETERMINATE",
    "ATTACK_KILLED",
    "BLOCKING_CONTRADICTIONS",
    "NO_NON_VACUOUS_EXPERIMENT",
    "NO_MUTATED_SURVIVOR",
    "RELEASE_NOT_EMITTED",
    "RELEASE_HELD",
    "PACKAGE_NOT_EMITTED",
    "STAGE_INCOMPLETE",
    "MID_FLIGHT_PER_LXXIV",
}


class ByteSource:
    """Read-only byte access: filesystem or a git ref of the durability repo."""

    def __init__(self, mode, root=None, git_ref=None, worktree=None):
        self.mode = mode
        self.root = root
        self.git_ref = git_ref
        self.worktree = worktree

    def read_text(self, relpath):
        if self.mode == "fs":
            p = os.path.join(self.root, relpath)
            if not os.path.isfile(p):
                return None
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        else:  # git
            spec = f"{self.git_ref}:{relpath}"
            r = subprocess.run(
                ["git", "-C", self.worktree, "show", spec],
                capture_output=True, text=True, timeout=60)
            if r.returncode != 0:
                return None
            return r.stdout

    def read_json(self, relpath):
        t = self.read_text(relpath)
        if t is None:
            return None, None
        try:
            return json.loads(t), hashlib.sha256(t.encode("utf-8")).hexdigest()
        except json.JSONDecodeError:
            return None, None

    def list_runs(self):
        if self.mode == "fs":
            base = os.path.join(self.root, "runs")
            return sorted(
                d for d in os.listdir(base)
                if os.path.isdir(os.path.join(base, d)))
        r = subprocess.run(
            ["git", "-C", self.worktree, "ls-tree", "--name-only",
             f"{self.git_ref}:runs"],
            capture_output=True, text=True, timeout=120)
        return sorted(x for x in r.stdout.split() if x)


def _ptr(obj, *keys):
    """Walk a JSON pointer path; returns (value, path_exists)."""
    cur = obj
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return None, False
        cur = cur[k]
    return cur, True


def _sha_obj(obj):
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def load_envelopes(src, slug):
    """Load every envelope_<STAGE>.json; return {stage: (doc, sha)}."""
    envs = {}
    if src.mode == "fs":
        base = os.path.join(src.root, "runs", slug)
        names = [n for n in os.listdir(base)
                 if n.startswith("envelope_") and n.endswith(".json")]
    else:
        r = subprocess.run(
            ["git", "-C", src.worktree, "ls-tree", "--name-only",
             f"{src.git_ref}:runs/{slug}"],
            capture_output=True, text=True, timeout=120)
        names = [n for n in r.stdout.split()
                 if n.startswith("envelope_") and n.endswith(".json")]
    for n in names:
        stage = n[len("envelope_"):-len(".json")]
        doc, sha = src.read_json(f"runs/{slug}/{n}")
        if doc is not None:
            envs[stage] = (doc, sha)
    return envs


def pick_work_envelope(envs):
    """The envelope carrying the fullest cumulative state = longest stage_log."""
    best, best_key = None, (-1, -1)
    for stage, (doc, sha) in envs.items():
        log = doc.get("stage_log") or []
        idx = STAGE_ORDER.index(stage) if stage in STAGE_ORDER else -1
        key = (len(log), idx)
        if key > best_key:
            best, best_key = (stage, doc, sha), key
    return best  # (stage, doc, sha) or None


def stage_log_entry(doc, stage):
    """First stage_log entry whose .stage == stage."""
    for e in doc.get("stage_log") or []:
        if e.get("stage") == stage:
            return e
    return None


def build_funnel_row(src, slug):
    """Compute one funnel row from durable bytes alone."""
    row = {
        "run_slug": slug,
        "instrument": f"{INSTRUMENT_ID}/{INSTRUMENT_VERSION}",
    }
    ev = lambda f, ptr: {"file": f, "pointer": ptr}  # noqa: E731

    # ---- identity + terminal state (Art. LXXIV rule) ----
    manifest, msha = src.read_json(f"runs/{slug}/run_manifest.json")
    final_state, fsha = src.read_json(f"runs/{slug}/final_state.json")
    problem, psha = src.read_json(f"runs/{slug}/problem.json")
    session_id = (manifest or {}).get("session_id") if manifest else None
    if not session_id and final_state:
        _epi = final_state.get("epistemic_state")
        session_id = (final_state.get("session_id")
                      or (_epi.get("session_id")
                          if isinstance(_epi, dict) else None))
    row["session_id"] = session_id  # may be None -> typed UNKNOWN (Art. XXV)
    row["byte_hashes"] = {
        "run_manifest.json": msha, "final_state.json": fsha, "problem.json": psha}

    if manifest is None:
        row["run_state"] = "MID_FLIGHT_OR_PARTIAL_PER_LXXIV"
        row["terminal"] = False
    else:
        row["run_state"] = "TERMINAL_COMMIT_PER_LXXIV"
        row["terminal"] = True
        row["manifest_final_status"] = manifest.get("final_status")
        row["stage_order_served"] = manifest.get("stage_order")
        row["failed_stages"] = manifest.get("failed_stages") or {}

    # declared family (LXXIX: family must be declared at submission)
    fam = None
    if problem:
        fam = problem.get("canonical_family") or problem.get("family")
    row["declared_family"] = fam  # None -> ABSENT_IN_DURABLE_RECORD (R489 precedent)

    envs = load_envelopes(src, slug)
    work = pick_work_envelope(envs)
    row["work_envelope"] = work[0] if work else None

    # ---- the funnel ----
    # 1. fresh_submitted
    row["fresh_submitted"] = {
        "reached": problem is not None,
        "evidence": ev("problem.json", "$"),
        "problem_id": (problem or {}).get("problem_id"),
    }
    funnel = row  # keep naming short below

    def set_stage(name, reached, count=None, drop=None, evidence=None, extra=None):
        st = {"reached": bool(reached), "evidence": evidence}
        if count is not None:
            st["count"] = count
        if drop:
            st["typed_drop_reason"] = drop
            assert drop in REASONS, f"untyped reason {drop}"
        if extra:
            st.update(extra)
        row[name] = st

    # 2. premise_coherent
    pg_env = envs.get("PREMISE_GATE", (None, None))[0] or (work[1] if work else {})
    verdict, ok = _ptr(pg_env, "premise_gate", "verdict")
    if not ok and work:
        entry = stage_log_entry(work[1], "PREMISE_GATE")
        verdict = ((entry or {}).get("result_meta") or {}).get("premise_verdict")
        ok = verdict is not None
    premise_ok = (verdict == "PREMISE_COHERENT")
    set_stage("premise_coherent", ok if ok else False,
              drop=None if (ok and premise_ok) else
              (None if not ok else "PREMISE_INCOHERENT"),
              evidence=ev(f"envelope_PREMISE_GATE.json", "$.premise_gate.verdict"),
              extra={"verdict": verdict} if verdict else None)

    # 3. evidence_verified — the engine's own adjudication evidence check
    ev_ok, ev_src, ev_issues, ev_ran = False, None, None, False
    if work:
        att = work[1].get("attack_results") or {}
        adj = (work[1].get("adjudication") or {}).get("evidence_verification") or {}
        if "evidence_verified" in att and att["evidence_verified"] is not None:
            ev_ok = bool(att["evidence_verified"])
            ev_ran = True
            ev_src = ev(f"envelope_{work[0]}.json",
                        "$.attack_results.evidence_verified")
        elif adj.get("verified") is not None:
            ev_ok = bool(adj["verified"])
            ev_ran = True
            ev_issues = adj.get("issues")
            ev_src = ev(f"envelope_{work[0]}.json",
                        "$.adjudication.evidence_verification")
        else:
            entry = stage_log_entry(work[1], "VERIFY")
            meta = (entry or {}).get("result_meta") or {}
            if "verified" in meta:
                ev_ok = bool(meta["verified"])
                ev_ran = True
                ev_src = ev(f"envelope_{work[0]}.json",
                            f"$.stage_log[VERIFY].result_meta.verified")
    if ev_ran:
        ev_drop = None if ev_ok else "EVIDENCE_UNVERIFIED"
    else:
        ev_drop = "STAGE_INCOMPLETE"  # never ran: infrastructure class (Art. LXI)
    set_stage("evidence_verified", ev_ok,
              drop=ev_drop, evidence=ev_src,
              extra={"stage_ran": ev_ran,
                     "verification_issues": ev_issues})

    # 4. mechanisms_found (stage-time MECHANISM_SPACE, primary candidate)
    ms_found, n_gen, ms_state, ms_src = False, None, None, None
    ms_env = envs.get("MECHANISM_SPACE", (None, None))[0]
    if ms_env:
        ms = ms_env.get("mechanism_space") or {}
        n_gen = ms.get("n_candidates_generated")
        ms_state = ms.get("state")
        ms_found = ms_found or (ms_state not in (None, "NO_CANDIDATES")
                                and (n_gen or 0) > 0)
        ms_src = ev("envelope_MECHANISM_SPACE.json",
                    "$.mechanism_space.n_candidates_generated")
    if not ms_found and work:
        entry = stage_log_entry(work[1], "MECHANISM_SPACE")
        meta = (entry or {}).get("result_meta") or {}
        if meta:
            n_gen = meta.get("n_candidates", n_gen)
            ms_state = meta.get("state", ms_state)
            ms_found = (ms_state not in (None, "NO_CANDIDATES")
                        and (n_gen or 0) > 0)
            ms_src = ev(f"envelope_{work[0]}.json",
                        "$.stage_log[MECHANISM_SPACE].result_meta")
    set_stage("mechanisms_found", ms_found,
              drop=None if ms_found else
              ("NO_CANDIDATES" if ms_state == "NO_CANDIDATES"
               else "STAGE_INCOMPLETE"),
              evidence=ms_src,
              extra={"state": ms_state, "n_candidates_generated": n_gen})

    # 5. candidates_generated_distinct — DISTINCT only (Art. XLII/XLVIII)
    distinct = {"n_distinct": None, "n_indeterminate": None,
                "n_equivalent_merged": None, "n_input": None,
                "n_retained": None, "instrument_version": None}
    if ms_env:
        d = (ms_env.get("mechanism_space") or {}).get("distinctness") or {}
        distinct.update({k: d.get(k) for k in
                         ("n_distinct", "n_indeterminate", "n_equivalent_merged",
                          "n_input", "n_retained", "instrument_version")})
    n_distinct = distinct["n_distinct"]
    distinct_ok = (n_distinct or 0) > 0
    drop = None
    if not distinct_ok:
        if (distinct.get("n_indeterminate") or 0) > 0:
            drop = "ALL_DISTINCTNESS_INDETERMINATE"
        else:
            drop = "NO_DISTINCT_CANDIDATES"
    set_stage("candidates_generated_distinct", distinct_ok,
              count=n_distinct or 0, drop=drop,
              evidence=ev("envelope_MECHANISM_SPACE.json",
                          "$.mechanism_space.distinctness.n_distinct"),
              extra={"distinctness": distinct})

    # 6. attack_survivors — from the run's own selection bytes when present
    attack_doc = envs.get("ATTACK", (None, None))[0]
    if attack_doc is None and work:
        attack_doc = work[1]
    attack = (attack_doc or {}).get("attack_results") or {}
    attacks = attack.get("attacks") or {}
    overall = attack.get("overall")
    killed_dims = sorted(k for k, v in attacks.items()
                         if isinstance(v, str) and v.startswith("KILL"))
    sel, ssha = src.read_json(f"runs/{slug}/SURVIVOR_SELECTION.json")
    grid_advanced = []
    if sel:
        for c in sel.get("ranked") or []:
            if not c.get("killed"):
                grid_advanced.append(c.get("candidate_id"))
    attack_ok = overall is not None and overall != "KILLED"
    set_stage("attack_survivors", attack_ok,
              count=1 if attack_ok else 0,
              drop=None if attack_ok else "ATTACK_KILLED",
              evidence=ev(f"envelope_{work[0] if work else 'ATTACK'}.json",
                          "$.attack_results.overall"),
              extra={
                  "attack_overall": overall,
                  "killed_dimensions": killed_dims,
                  "attacker_provenance": "RUN_LEVEL_A2_GAUNTLET_NOT_SEALED_BAR_CALIBRATED",
                  "grid_advanced_not_counted": len(grid_advanced),
                  "grid_advanced_note": "SURVIVOR_SELECTION.ranked non-killed entries "
                                        "are exploration-grid advancements (the "
                                        "SURVIVOR_GATE resolution records that "
                                        "discovery-level verification is NOT re-run "
                                        "per grid candidate); Article LXXVIII: "
                                        "grid-advanced counts are never invention "
                                        "counts, so they are recorded but never "
                                        "counted as attack survivors",
                  "note": "the run-level A2 adversarial gauntlet is a different "
                          "attacker from the engine independent_attack instrument "
                          "whose R412/R446/R447/R487 sealed-bar calibration gates "
                          "the engine consumption sites (R489 composition finding)",
              })

    # 7. contradiction_survivors — blocking_count == 0 (the engine's own
    #    ADJUDICATION no_blocking_contradictions definition)
    ct_env = envs.get("CONTRADICTION", (None, None))[0]
    blocking = None
    ct_src = None
    if ct_env:
        ct = ct_env.get("contradictions") or {}
        blocking = ct.get("blocking_count")
        ct_src = ev("envelope_CONTRADICTION.json", "$.contradictions.blocking_count")
    if blocking is None and work:
        ct = work[1].get("contradictions") or {}
        blocking = ct.get("blocking_count")
        ct_src = ev(f"envelope_{work[0]}.json", "$.contradictions.blocking_count")
    ct_ok = blocking is not None and blocking == 0
    if blocking is None:
        ct_drop = "STAGE_INCOMPLETE"
    elif blocking > 0:
        ct_drop = "BLOCKING_CONTRADICTIONS"
    else:
        ct_drop = None
    set_stage("contradiction_survivors", ct_ok,
              count=0 if blocking else (1 if ct_ok else 0),
              drop=ct_drop,
              evidence=ct_src,
              extra={"blocking_count": blocking})

    # 8. experimentally_discriminated — killer selected AND (contract issued
    #    + executed or REAL packet ingested). Selection alone is not
    #    discrimination; executed means a REAL/DECISIVE execution record exists.
    ke = {}
    ke_env = envs.get("KILLER_EXPERIMENT", (None, None))[0]
    if ke_env:
        ke = ke_env.get("killer_experiment") or {}
    decisive, dsha = src.read_json(f"runs/{slug}/DECISIVE_EXPERIMENT.json")
    selected = bool(ke.get("selected")) or bool((decisive or {}).get("selected"))
    contract = bool((decisive or {}).get("falsification_contract"))
    # execution evidence: REAL_LOOP_VERIFIED state or a real-event ingest record
    release, rsha = src.read_json(f"runs/{slug}/DISCOVERY_RELEASE.json")
    rlv = bool((release or {}).get("real_loop_verified"))
    executed = rlv  # v1.0.0: the only byte-typed execution proof in the record
    exp_ok = selected and contract and executed
    exp_state = ("REAL_PACKET_INGESTED" if executed else
                 ("CONTRACT_ISSUED_NOT_EXECUTED" if selected and contract else
                  ("SELECTED_NO_CONTRACT" if selected else "NOT_SELECTED")))
    set_stage("experimentally_discriminated", exp_ok,
              drop=None if exp_ok else "NO_NON_VACUOUS_EXPERIMENT",
              evidence=ev("DECISIVE_EXPERIMENT.json",
                          "$.falsification_contract + $.selected"),
              extra={"state": exp_state,
                     "real_loop_verified": rlv,
                     "note": "v1.0.0 counts EXECUTED only via the Art. "
                             "XXXVIII REAL_LOOP_VERIFIED byte state; synthetic "
                             "executions never count (Art. XXXVII)"})

    # 9. mutated_survivors — IMPROVE entries: CHILDREN_ADMITTED + delta_real
    improve_entries = []
    if work:
        for e in work[1].get("stage_log") or []:
            if e.get("stage") == "IMPROVE":
                improve_entries.append(e)
    children, delta_real, ledger_bytes = [], False, None
    for e in improve_entries:
        meta = e.get("result_meta") or {}
        # delta_real is recorded at the stage_log ENTRY level (with the
        # before/after envelope hashes); fall back to result_meta for
        # older layouts (Art. XL-adjacent: read bytes as they are)
        d_real = bool(e.get("delta_real")) or bool(meta.get("delta_real"))
        if meta.get("status") == "CHILDREN_ADMITTED":
            for ch in meta.get("children") or []:
                re_eval = {k: ch.get(k) for k in
                           ("attack", "independent_attack", "quality",
                            "killed", "physics_lifecycle") if k in ch}
                children.append({"candidate_id": ch.get("candidate_id")
                                 or ch.get("key"),
                                 "re_evaluated_fields": sorted(re_eval),
                                 "killed_at_reeval": ch.get("killed")})
            delta_real = delta_real or d_real
            ledger_bytes = meta.get("ledger")
        delta_real = delta_real or d_real
    mut_ok = bool(children) and delta_real
    evolve, esha = src.read_json(f"runs/{slug}/EVOLUTION_GEN_1.json")
    set_stage("mutated_survivors", mut_ok,
              count=len(children), drop=None if mut_ok else "NO_MUTATED_SURVIVOR",
              evidence=ev(f"envelope_{work[0] if work else 'IMPROVE'}.json",
                          "$.stage_log[IMPROVE] delta_real + "
                          "result_meta.status==CHILDREN_ADMITTED"),
              extra={"children": children, "delta_real": delta_real,
                     "hash_transition": [
                        {"before": e.get("before_envelope_hash"),
                         "after": e.get("after_envelope_hash")}
                        for e in improve_entries
                        if (e.get("result_meta") or {}).get("status")
                        == "CHILDREN_ADMITTED"],
                     "ledger": {k: ledger_bytes.get(k) for k in
                                ("children_admitted", "children_rekilled",
                                 "dead_consumed", "loop_closure")}
                                if isinstance(ledger_bytes, dict) else None,
                     "improve_statuses": [((e.get("result_meta") or {}).get("status"))
                                          for e in improve_entries],
                     "deferred_to_kill_point": any(
                         ((e.get("result_meta") or {}).get("status")
                          == "DEFERRED_TO_KILL_POINT") for e in improve_entries),
                     "evolution_record": bool(evolve)})

    # 10. buyer_ready — ZIP emitted + lineage VERIFIED (+ honest status)
    lineage, lsha = src.read_json(f"runs/{slug}/INVENTION_LINEAGE.json")
    pkg_zip = (release or {}).get("package_zip")
    rel_status = (release or {}).get("status")
    lin_reached = bool((lineage or {}).get("survivor_reached")) if lineage else False
    buyer_ok = bool(pkg_zip) and bool(release) and rel_status in (
        "RELEASED", "SHIPPED", "TECHNOLOGY_TRANSFER_READY")
    drop = None
    if not buyer_ok:
        if release is None:
            drop = "RELEASE_NOT_EMITTED"
        elif rel_status == "HELD_FOR_HUMAN_REVIEW":
            drop = "RELEASE_HELD"
        else:
            drop = "PACKAGE_NOT_EMITTED"
    set_stage("buyer_ready", buyer_ok,
              drop=drop,
              evidence=ev("DISCOVERY_RELEASE.json",
                          "$.package_zip + $.status"),
              extra={"release_status": rel_status,
                     "failure_reason": (release or {}).get("failure_reason"),
                     "package_zip": pkg_zip,
                     "loop_verification_state": (release or {}).get(
                         "loop_verification_state"),
                     "real_loop_verified": rlv,
                     "lineage_survivor_reached": lin_reached,
                     "lineage_sha": lsha,
                     "release_sha": rsha})

    # collision completeness honesty pin (Art. XXI.3/LXXV.2)
    coll = {}
    if work:
        coll = work[1].get("collision_results") or {}
    mand, _ = _ptr(coll, "mandatory_searches", "complete")
    row["novelty_resolution"] = {
        "mandatory_complete": mand,
        "typed": "NOVELTY_RESOLVED_BYTES" if mand is True else
                 "NOVELTY_LEFT_UNRESOLVED_BY_RING_FAILURES",
        "novelty_risk": coll.get("novelty_risk"),
    }

    # first lost transition -> bottleneck attribution
    ORDER = ["fresh_submitted", "premise_coherent", "evidence_verified",
             "mechanisms_found", "candidates_generated_distinct",
             "attack_survivors", "contradiction_survivors",
             "experimentally_discriminated", "mutated_survivors", "buyer_ready"]
    lost_at, lost_reason = None, None
    for name in ORDER:
        st = row.get(name) or {}
        if not st.get("reached"):
            lost_at = name
            lost_reason = st.get("typed_drop_reason") or "STAGE_INCOMPLETE"
            break
    row["lost_at"] = lost_at
    row["typed_drop_reason"] = lost_reason
    row["survived_all"] = lost_at is None

    # cost/transport bytes present? (never invented — UNKNOWN when absent)
    transports = []
    if work:
        att = work[1].get("attack_results") or {}
        t = att.get("transport")
        if t:
            transports.append({"stage": "ATTACK", "transport": t})
    synth_entry = stage_log_entry(work[1], "SYNTHESIZE") if work else None
    if synth_entry:
        transports.append({"stage": "SYNTHESIZE",
                           "transport": (synth_entry.get("result_meta") or {})})
    row["transports_observed"] = transports
    row["cost_debits"] = "UNKNOWN_PER_ART_XXV_NO_METERED_COST_BYTES_IN_RUN_RECORDS"
    return row


def aggregate(rows):
    """Aggregate funnel over terminal rows + rank bottlenecks."""
    terminal = [r for r in rows if r.get("terminal")]
    midflight = [r for r in rows if not r.get("terminal")]
    ORDER = ["fresh_submitted", "premise_coherent", "evidence_verified",
             "mechanisms_found", "candidates_generated_distinct",
             "attack_survivors", "contradiction_survivors",
             "experimentally_discriminated", "mutated_survivors", "buyer_ready"]
    n = len(terminal)
    funnel = []
    for i, name in enumerate(ORDER):
        reached = sum(1 for r in terminal if (r.get(name) or {}).get("reached"))
        prev = sum(1 for r in terminal
                   if i == 0 or (r.get(ORDER[i - 1]) or {}).get("reached"))
        funnel.append({
            "transition": name,
            "reached": reached,
            "of_n": n,
            "rate_overall": round(reached / n, 4) if n else None,
            "rate_conditional": round(reached / prev, 4) if prev else None,
            "absolute_drop_from_previous": prev - reached,
        })
    drops = {}
    for r in terminal:
        if r.get("lost_at"):
            key = f"{r['lost_at']}::{r.get('typed_drop_reason')}"
            drops.setdefault(key, []).append(r["run_slug"])
    ranked = sorted(
        [{"lost_at::reason": k, "n_runs": len(v), "runs": v}
         for k, v in drops.items()],
        key=lambda d: -d["n_runs"])
    # per-family yield per 100 fresh problems
    fams = {}
    for r in terminal:
        f = r.get("declared_family") or "ABSENT_IN_DURABLE_RECORD"
        fams.setdefault(f, {"n_fresh": 0, "n_survived_all": 0})
        fams[f]["n_fresh"] += 1
        if r.get("survived_all"):
            fams[f]["n_survived_all"] += 1
    for f, v in fams.items():
        v["yield_per_100_fresh"] = round(
            100.0 * v["n_survived_all"] / v["n_fresh"], 2) if v["n_fresh"] else None
    return {
        "n_rows_total": len(rows),
        "n_terminal": n,
        "n_mid_flight": len(midflight),
        "mid_flight_never_collapsed": True,
        "funnel": funnel,
        "dropoff_attribution_ranked": ranked,
        "yield_per_100_fresh_by_family": fams,
        "cost_debits": "UNKNOWN_PER_ART_XXV_NO_METERED_COST_BYTES_IN_RUN_RECORDS",
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-dir", help="one run directory (filesystem mode)")
    ap.add_argument("--root", help="runs/ root to batch over (filesystem mode)")
    ap.add_argument("--git-ref", help="durable-branch ref to read bytes from")
    ap.add_argument("--durability-worktree", help="git worktree of the durability repo")
    ap.add_argument("--run", help="run slug under runs/ (with --git-ref)")
    ap.add_argument("--out", help="write the report JSON here")
    args = ap.parse_args()

    if args.git_ref:
        src = ByteSource("git", git_ref=args.git_ref,
                         worktree=args.durability_worktree)
        slugs = [args.run] if args.run else src.list_runs()
        rows = [build_funnel_row(src, s) for s in slugs]
    elif args.run_dir:
        rd = args.run_dir.rstrip("/")
        slug = os.path.basename(rd)
        parent = os.path.dirname(rd)
        # ByteSource root = the directory CONTAINING runs/ (reads are
        # "runs/<slug>/<file>"); accept both the worktree root and runs/ itself
        src = ByteSource("fs", root=os.path.dirname(parent)
                         if os.path.basename(parent) == "runs" else parent)
        rows = [build_funnel_row(src, slug)]
    elif args.root:
        # --root accepts the runs/ directory; the ByteSource root is its parent
        src = ByteSource("fs", root=os.path.dirname(args.root.rstrip("/")))
        rows = [build_funnel_row(src, s) for s in src.list_runs()]
    else:
        ap.error("one of --run-dir / --root / --git-ref is required")

    report = {
        "instrument": INSTRUMENT_ID,
        "instrument_version": INSTRUMENT_VERSION,
        "byte_source_mode": src.mode,
        "git_ref": src.git_ref,
        "rows": rows,
        "aggregate": aggregate(rows),
    }
    payload = json.dumps(report, indent=1, sort_keys=True, ensure_ascii=False)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(payload + "\n")
        print(f"wrote {args.out}")
    else:
        print(payload)
    # exit code 0 = instrument ran; measurement outcomes are not pass/fail
    return 0


if __name__ == "__main__":
    sys.exit(main())
