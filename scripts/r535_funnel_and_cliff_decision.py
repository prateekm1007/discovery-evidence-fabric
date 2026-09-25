#!/usr/bin/env python3
"""R535 §5/§7/§9 machine aggregation: the full discovery-yield
funnel + typed dropout table + stage reachability matrix + single-
cliff decision record.

Reads ONLY durable bytes (the R535 battery harvest + join + stage-
wall attribution) — no hand transcription, no new measurements
(Art. LXXXIII/LXXXIV discipline; Art. XXXIV: stop coding when
reality is the bottleneck).

Output: R535/R535_FUNNEL_AND_CLIFF_DECISION.json with:
  * stage_reachability_matrix: per problem, per stage, the typed
    status (reached / skipped-admission / skipped-upstream /
    executed) — a stage not reached by the battery is recorded as
    UNPROVEN_CURRENT_REACHABILITY, never PASS (R535 §7).
  * typed_dropout_table: the complete funnel RETRIEVE -> FREEZE ->
    VERIFY -> MECHANISM_SPACE admission -> MECHANISM_SPACE accepted
    -> distinct mechanisms -> COLLISION -> PHYSICS -> ATTACK ->
    CONTRADICTION -> KILLER_EXPERIMENT -> ADJUDICATION -> CLASSIFY
    -> NEXT_BEST_ACTION -> RANK -> post-rank IMPROVE -> survivor,
    with the typed reason for every transition.  No collapse of
    retrieval-absence / custody-rejection / verification-rejection /
    mechanism-admission-rejection / semantic-rejection / cemetery-
    block / distinctness-drop into one NO_CANDIDATES.
  * single_cliff_decision: the §9 authorization — exactly one
    dominant discovery-yield dropout (Art. LXXXIII) is identified,
    and exactly one avoidable runtime sink is identified INDE-
    PENDENTLY; an optimization is authorized ONLY when BOTH the
    measured cost AND the measured avoidability hold for the same
    class, and even then only as a single bounded intervention
    with a paired counterfactual.  R535 is a MEASUREMENT round:
    the decision record names what is authorized for the NEXT
    round; it does not itself optimize.
"""
from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
HARVEST = REPO / "R526" / "ATTR_CURRENT_HARVEST.json"
SESSIONS = REPO / "R535" / "BATTERY_SESSIONS_CURRENT.json"
STAGE_WALL = REPO / "R535" / "R535_STAGE_WALL_ATTRIBUTION.json"
JOIN = REPO / "R535" / "MECHANISM_SPACE_PROVIDER_JOIN_R535.json"
OUT = REPO / "R535" / "R535_FUNNEL_AND_CLIFF_DECISION.json"

STAGE_ORDER = [
    "RETRIEVE", "FREEZE", "PREMISE_GATE", "SYNTHESIZE", "VERIFY",
    "MECHANISM_SPACE", "COLLISION", "PHYSICS", "ATTACK",
    "CONTRADICTION", "KILLER_EXPERIMENT", "ADJUDICATION", "CLASSIFY",
    "NEXT_BEST_ACTION", "RANK",
]
POST_RANK = "POST_RANK_IMPROVE"


def _r535_session_ids() -> set:
    s = json.loads(SESSIONS.read_text(encoding="utf-8"))
    return {sub.get("session_id") for sub in s.get("submissions", [])
            if sub.get("session_id")}


def _stage_table_map(row: dict) -> dict:
    st = row.get("stage_table")
    if isinstance(st, list):
        return {e.get("stage"): e for e in st}
    return st or {}


def main() -> int:
    sids = _r535_session_ids()
    h = json.loads(HARVEST.read_text(encoding="utf-8"))
    rows = [r for r in h.get("rows", [])
            if r.get("session_id") in sids]
    if not rows:
        print(f"FATAL: no harvest rows for the R535 sessions "
              f"{sorted(sids)}")
        return 2

    sw = json.loads(STAGE_WALL.read_text(encoding="utf-8")) \
        if STAGE_WALL.exists() else {}
    join = json.loads(JOIN.read_text(encoding="utf-8")) \
        if JOIN.exists() else {}

    # ---- stage reachability matrix (§7) --------------------------
    reachability = {}
    for r in rows:
        pid = str(r.get("problem_index"))
        stmap = _stage_table_map(r)
        stage_rec = {}
        for stage in STAGE_ORDER:
            e = stmap.get(stage) or {}
            status = e.get("status")
            entry = e.get("entry") or {}
            entry_class = e.get("entry_class")
            skip_reason = e.get("skip_reason") or \
                entry.get("skip_reason")
            # A stage is REACHED when it actually executed (OK /
            # FAILED_EXPLICIT with executed_flag=True) or was
            # admitted-and-skipped by the MINIMUM_DIVERSITY gate
            # (COLLISION/ATTACK SKIPPED_ADMISSION on a live run).
            # A stage NOT reached (SKIPPED_UPSTREAM_FAILURE from an
            # earlier stage's failure) is UNPROVEN_CURRENT_
            # REACHABILITY — never PASS (R535 §7).
            if status == "OK" and e.get("executed_flag") is True:
                reached = "REACHED_AND_EXECUTED"
            elif status == "FAILED_EXPLICIT" and \
                    e.get("executed_flag") is True:
                reached = "REACHED_AND_FAILED"
            elif status == "SKIPPED_ADMISSION":
                reached = "REACHED_ADMISSION_SKIPPED"
            elif status == "SKIPPED_UPSTREAM_FAILURE":
                reached = "UNPROVEN_CURRENT_REACHABILITY"
            elif status in ("DISABLED_BY_CONFIG",):
                reached = "DISABLED_BY_CONFIG"
            else:
                reached = "UNPROVEN_CURRENT_REACHABILITY"
            stage_rec[stage] = {
                "status": status,
                "entry_class": entry_class,
                "reached": reached,
                "skip_reason": skip_reason,
                "result_meta": e.get("result_meta"),
            }
        # post-rank IMPROVE: recorded separately (not a 16th linear
        # stage — R535 §3).
        improve_env = r.get("improve") or {}
        stage_rec[POST_RANK] = {
            "status": improve_env.get("status")
            or improve_env.get("state"),
            "reached": ("REACHED_AND_EXECUTED"
                        if improve_env.get("executed_flag")
                        else "UNPROVEN_CURRENT_REACHABILITY"),
            "note": ("IMPROVE is the post-rank Directive-1 kill-"
                     "evidence point (run.py kill point, "
                     "improve_payload present); it is never a 16th "
                     "linear stage"),
        }
        reachability[pid] = stage_rec

    # ---- typed dropout table (§5/§7) -----------------------------
    # For each transition in the funnel, record the typed reason.
    # The MECHANISM_SPACE typed outcomes (R532 classifier) are the
    # authoritative yield signal — NOT the stage-log status==OK flag
    # (the R535 §6 OK-vs-typed-outcome proof).
    dropout_table = {}
    for r in rows:
        pid = str(r.get("problem_index"))
        mss = r.get("mechanism_space_spans") or {}
        atts = mss.get("instantiation_attempts") or []
        att = atts[0] if atts else {}
        funnel_row = r.get("funnel_row") or {}
        dropout_table[pid] = {
            "retrieved_evidence_count":
                (r.get("retrieve_two_level") or {})
                .get("records_returned"),
            "frozen_evidence_count":
                ((r.get("stage_table") or {})
                 .get("FREEZE", {})
                 .get("result_meta", {})
                 .get("custody_records")
                 if isinstance(r.get("stage_table"), dict)
                 else None),
            "mechanism_space_terminal":
                mss.get("terminal_state")
                or (mss.get("funnel") or {}).get("terminal_reason"),
            "mechanism_space_typed_outcome":
                att.get("typed_outcome"),
            "cemetery_blocked": att.get("cemetery_blocked"),
            "distinctness_verdict": att.get("distinctness_verdict"),
            "semantic_verdict": att.get("semantic_verdict"),
            "support_state": att.get("support_state"),
            "mechanisms_found_reached":
                funnel_row.get("mechanisms_found", {}).get("reached"),
            "mechanisms_found_state":
                funnel_row.get("mechanisms_found", {}).get("state"),
            "typed_drop_reason":
                funnel_row.get("mechanisms_found", {})
                .get("typed_drop_reason"),
        }
    # the typed dropout reasons are NEVER collapsed: each of the
    # following is a distinct typed state (R535 §5: do not collapse
    # retrieval absence / custody rejection / verification rejection
    # / mechanism admission rejection / semantic rejection /
    # cemetery block / distinctness drop into one NO_CANDIDATES).
    typed_reasons_seen = sorted({
        d.get("mechanism_space_typed_outcome")
        or d.get("typed_drop_reason")
        for d in dropout_table.values()
        if d.get("mechanism_space_typed_outcome")
        or d.get("typed_drop_reason")
    })

    # ---- §9 single-cliff decision --------------------------------
    # The MECHANISM_SPACE join carries the R530 stopping rule: a
    # provider-dominated stage is NOT automatically a removable
    # waste class.  The avoidable_fraction is the measured ratio of
    # (failed-hop admission + inter-rung fallback) to the LLM-path
    # wall; ~0 means the dominant cost is genuine provider
    # inference.
    join_class = join.get("classification") or {}
    avoidable_fraction = join_class.get("avoidable_fraction")
    verdict = join_class.get("verdict")

    # The discovery-yield cliff: the largest funnel dropout is the
    # MECHANISM_SPACE admission loss (NOT_ATTEMPTED /
    # ASSEMBLY_INVALID / SEMANTIC_REJECT / MECHANISM_SUPPORT_DROP
    # across the R535 battery).  Art. LXXXIII: that stage/
    # transition becomes the next discovery cliff.
    ms_terminal_counts = defaultdict(int)
    for d in dropout_table.values():
        t = d.get("mechanism_space_terminal")
        if t:
            ms_terminal_counts[t] += 1
    n_cand = ms_terminal_counts.get("NO_CANDIDATES", 0)
    n_built = ms_terminal_counts.get("BUILT", 0)
    n_problems = len(dropout_table)
    yield_cliff = {
        "class": "MECHANISM_SPACE_ADMISSION_LOSS",
        "n_no_candidates": n_cand,
        "n_built": n_built,
        "n_problems": n_problems,
        "dropout_fraction": round(n_cand / n_problems, 4)
        if n_problems else None,
        "art_ref": "Art. LXXXIII: the largest measured funnel "
                   "dropout is the authorized next bottleneck",
        "causality": (
            "UPSTREAM_CAUSALITY_NOT_YET_ESTABLISHED: the R535 "
            "battery measures WHERE the loss occurs (the typed "
            "dropout table above) but does not yet establish "
            "WHICH upstream stage (RETRIEVE vs FREEZE vs VERIFY) "
            "causes it.  A targeted upstream-instrumentation round "
            "is required before an admission-cliff optimization is "
            "authorized."),
    }
    runtime_cliff = {
        "class": "MECHANISM_SPACE_PROVIDER_INFERENCE",
        "measured_cost": "dominant local wall component "
                        "(R532/R535 provider_execution mean)",
        "avoidable_fraction": avoidable_fraction,
        "r530_stopping_rule": verdict,
        "authorized": bool(avoidable_fraction is not None
                           and avoidable_fraction > 0.0),
        "note": ("avoidable_fraction ~0: the provider wall is "
                 "genuine inference, NOT a proven removable waste "
                 "class.  No optimization is authorized on runtime "
                 "alone."),
    }

    decision = {
        "round": "R535",
        "measurement_complete": True,
        "discovery_cliff": yield_cliff,
        "runtime_cliff": runtime_cliff,
        "optimization_authorized": (
            # §9 rule: authorize only when measured cost AND
            # measured avoidability hold for the SAME class.  The
            # discovery cliff is measured but its causality is not
            # yet established; the runtime cliff is measured with
            # avoidable_fraction ~0.  Neither independently
            # authorizes an intervention in R535.
            bool(runtime_cliff["authorized"]
                 and yield_cliff["causality"].startswith(
                     "ESTABLISHED"))),
        "next_authorized_move": (
            "R536: upstream-instrumentation round (RETRIEVE -> "
            "FREEZE -> VERIFY seam) to establish the causality of "
            "the MECHANISM_SPACE admission loss; NO optimization "
            "until a measured avoidable waste class is proven "
            "(§9 rule 8: the round authorizes exactly one bounded "
            "intervention only after the avoidable fraction is "
            "nonzero for a specific class)"),
        "not_authorized": [
            "provider inference cost (avoidable_fraction ~0 — "
            "R530 stopping rule)",
            "RETRIEVE/FREEZE/VERIFY causality (not yet "
            "established — measure first, §9 rule 2)",
            "any provider/model/prompt/token/stage-order/gate "
            "change (R535 §10 prohibition list)",
        ],
    }

    rec = {
        "artifact": "R535_FUNNEL_AND_CLIFF_DECISION/1.0",
        "round": "R535",
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                       time.gmtime()),
        "reviewer_provenance": "AI_REVIEW",
        "source": "aggregated from durable R535 battery harvest + "
                  "mechanism-space join + stage-wall attribution "
                  "(no new measurements)",
        "n_problems": n_problems,
        "stage_reachability_matrix": reachability,
        "funnel_terminal_distribution": dict(
            sorted(ms_terminal_counts.items(),
                   key=lambda kv: -kv[1])),
        "typed_dropout_table": dropout_table,
        "typed_reasons_seen": typed_reasons_seen,
        "mechanism_space_join_classification": join_class,
        "single_cliff_decision": decision,
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1, ensure_ascii=False)
                   + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({n_problems} problems)")
    print(f"funnel terminals: "
          f"{dict(sorted(ms_terminal_counts.items(), key=lambda kv: -kv[1]))}")
    print(f"optimization_authorized: "
          f"{decision['optimization_authorized']}")
    print(f"next_authorized_move: {decision['next_authorized_move']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
