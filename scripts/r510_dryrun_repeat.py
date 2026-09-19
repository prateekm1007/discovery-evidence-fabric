"""scripts/r510_dryrun_repeat.py — A-vs-B repeatability checker.

Compares two proof rounds of the SAME controlled problem run with the
EXACT same deterministic inputs. PASS requires:

  MUST MATCH EXACTLY:
    - portfolio counts (generated/distinct/ranked) + funnel counts
    - ordered scientific identities (by rank)
    - per-identity: rank, ranking basis, distinctness, attack
      overalls, evidence refs, span, testable prediction
    - ranking_stable_hash, deterministic_input_identity,
      bundle_identity
    - stage statuses, grid_state, mechanism_space_state, final_status
    - grid engine candidate_ids (output-hash-derived: deterministic)
  PERMITTED DIFFS (explicit, each classified):
    - wall-clock timestamps + durations (runtime metadata)
    - run_id / out_dir round tags (A vs B harness labels)
    - the MS engine candidate_id/hash suffix: PROVEN timestamp-
      derived by field-level record comparison excluding derived_at
      (the engine binds wall-clock derived_at into the id by design;
      the scientific identity carries repeatability instead)

Any other difference FAILS the check. Usage:
  python scripts/r510_dryrun_repeat.py dry-p1 C:/proof/dryrun
"""
from __future__ import annotations

import json
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)


def _load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _ms_record(run_dir):
    env = _load(os.path.join(run_dir, "envelope_MECHANISM_SPACE.json"))
    ms = env.get("mechanism_space", env) or {}
    cands = ms.get("candidates") or []
    return cands[0] if cands else None


def _norm_ids(obj):
    """Normalize timestamp-derived engine ids/hashes (classified
    permitted at the top level) so the proof compares everything
    else byte-for-byte."""
    if isinstance(obj, dict):
        return {k: ("ID" if k in ("candidate_id", "candidate_hash")
                    and isinstance(v, str) else _norm_ids(v))
                for k, v in obj.items()}
    if isinstance(obj, list):
        return [_norm_ids(v) for v in obj]
    return obj


def check(problem_id, root):
    failures = []
    permitted = []

    def _ok(cond, msg, allow=False):
        if cond:
            return
        (permitted if allow else failures).append(msg)

    da = os.path.join(root, "%s_A" % problem_id)
    db = os.path.join(root, "%s_B" % problem_id)
    ra = [d for d in os.listdir(da) if d.startswith("engrun_")][0]
    rb = [d for d in os.listdir(db) if d.startswith("engrun_")][0]
    pa = _load(os.path.join(da, ra, "CANDIDATE_PORTFOLIO.json"))
    pb = _load(os.path.join(db, rb, "CANDIDATE_PORTFOLIO.json"))
    fa = _load(os.path.join(da, ra, "DRY_RUN_FUNNEL.json"))
    fb = _load(os.path.join(db, rb, "DRY_RUN_FUNNEL.json"))

    for k in ("candidate_count_generated", "candidate_count_distinct",
              "candidate_count_ranked"):
        _ok(pa[k] == pb[k], "portfolio.%s %s != %s" % (k, pa[k], pb[k]))
    for k in ("submitted", "premise", "evidence", "mechanisms",
              "distinct", "ranked"):
        _ok(fa[k] == fb[k], "funnel.%s %s != %s" % (k, fa[k], fb[k]))
    # Attack-state classifications must match exactly across A/B
    # (Art. LXXXIII/LXI: measured, never assumed; transport /
    # independence / drop identical; ATTACK_INCOMPLETE stays distinct
    # from KILLED and SURVIVED).
    for k in ("attack_reached", "attack_naive_overall",
              "attack_candidates_reached", "attack_survived",
              "attack_state_aggregate", "attack_measurement",
              "attack_state"):
        _ok(fa.get(k) == fb.get(k),
            "funnel.attack.%s differs" % k)
    for k in ("ranking_stable_hash", "deterministic_input_identity",
              "bundle_identity", "grid_state",
              "mechanism_space_state"):
        _ok(pa[k] == pb[k], "portfolio.%s differs" % k)
    _ok(fa.get("final_status") == fb.get("final_status"),
        "final_status %s != %s" % (fa.get("final_status"),
                                   fb.get("final_status")))
    _ok(fa.get("stage_statuses") == fb.get("stage_statuses"),
        "stage_statuses differ: %s" % (
            {k for k in fa.get("stage_statuses", {})
             if fa["stage_statuses"].get(k) != fb.get(
                 "stage_statuses", {}).get(k)}))

    ia = [c["identity"] for c in pa["candidates"]]
    ib = [c["identity"] for c in pb["candidates"]]
    _ok(ia == ib, "identity order differs:\n%s\n%s" % (ia, ib))
    ba = {c["identity"]: c for c in pa["candidates"]}
    bb = {c["identity"]: c for c in pb["candidates"]}
    for ident in ia:
        ca, cb = ba[ident], bb[ident]
        for k in ("rank", "ranking_basis", "distinctness",
                  "distinctness_basis", "state", "evidence_refs",
                  "attack_status", "attack", "falsification_test",
                  "testable_prediction", "mechanism_source_span",
                  "origin", "exploration_angle",
                  "transformation_operator"):
            _ok(ca.get(k) == cb.get(k),
                "identity %s field %s differs" % (ident[:12], k))
        if (ca.get("origin") or "").startswith("EXPLORATION_GRID"):
            _ok(ca.get("candidate_id") == cb.get("candidate_id"),
                "grid engine id differs for %s" % ident[:12])
        else:
            if ca.get("candidate_id") != cb.get("candidate_id"):
                permitted.append(
                    "MS engine id differs (timestamp-derived, "
                    "proven below): %s vs %s" % (
                        ca.get("candidate_id"),
                        cb.get("candidate_id")))

    # MS timestamp-derivation proof: the two MS records must agree on
    # every byte except derivation_trace.derived_at (+ the round tag
    # inside call_provenance.run_id, a harness label).
    ma, mb = _ms_record(os.path.join(da, ra)), _ms_record(
        os.path.join(db, rb))
    if ma is None and mb is None:
        permitted.append(
            "MS produced no retained candidate in either round "
            "(instrument verdict, states compared above)")
    elif ma is None or mb is None:
        failures.append("MS record present in exactly one round")
    else:
        ta = dict(ma.get("derivation_trace") or {})
        tb = dict(mb.get("derivation_trace") or {})
        _ok(set(ta) == set(tb), "MS trace keys differ",
            )
        for k in ta:
            if k == "derived_at":
                if ta[k] != tb[k]:
                    permitted.append(
                        "MS derived_at differs (wall clock): %s vs %s"
                        % (ta[k], tb[k]))
                continue
            va, vb = ta[k], tb[k]
            if isinstance(va, dict):
                va = {kk: (vv if not (
                    isinstance(vv, str) and ("_A" in vv or "_B" in vv))
                    else vv.replace("_A", "_X").replace(
                        "_B", "_X")) for kk, vv in va.items()}
                vb = {kk: (vv if not (
                    isinstance(vv, str) and ("_A" in vv or "_B" in vv))
                    else vv.replace("_A", "_X").replace(
                        "_B", "_X")) for kk, vv in vb.items()}
            _ok(va == vb, "MS trace.%s differs" % k)
        rest_a = _norm_ids({k: v for k, v in ma.items()
                            if k != "derivation_trace"})
        rest_b = _norm_ids({k: v for k, v in mb.items()
                            if k != "derivation_trace"})
        # engine ids/hashes normalized (proven timestamp-derived);
        # everything else must match byte-for-byte.
        _ok(rest_a == rest_b,
            "MS record differs beyond ids/derived_at: %s" % (
                [k for k in rest_a
                 if rest_a.get(k) != rest_b.get(k)]))

    # Transition-ledger repeatability: operator counts identical,
    # drop-transition identities identical (id-free comparison —
    # drop classes + cemetery entries, never engine ids).
    def _ledger(run_dir):
        env = _load(os.path.join(
            run_dir, "envelope_MECHANISM_SPACE.json"))
        m = env.get("mechanism_space", env) or {}
        return m.get("candidate_transitions") or {}
    la, lb = (_ledger(os.path.join(da, ra)),
              _ledger(os.path.join(db, rb)))
    _ok((la.get("operator_counts") or {}) == (
        lb.get("operator_counts") or {}),
        "operator_transition_counts differ: %s vs %s" % (
            la.get("operator_counts"), lb.get("operator_counts")))
    da_drops = sorted(str(t.get("drop_transition")) for t in (
        la.get("candidate_traces") or []))
    db_drops = sorted(str(t.get("drop_transition")) for t in (
        lb.get("candidate_traces") or []))
    _ok(da_drops == db_drops,
        "drop-transition identities differ: %s vs %s" % (
            da_drops, db_drops))
    da_blocks = sorted(str(e) for t in (
        la.get("candidate_traces") or [])
        for e in (t.get("cemetery_entry_ids") or []))
    db_blocks = sorted(str(e) for t in (
        lb.get("candidate_traces") or [])
        for e in (t.get("cemetery_entry_ids") or []))
    _ok(da_blocks == db_blocks,
        "cemetery block entries differ: %s vs %s" % (
            da_blocks, db_blocks))

    result = {"problem_id": problem_id, "passed": not failures,
              "failures": failures, "permitted_diffs": permitted}
    print(json.dumps(result, indent=1))
    return result


if __name__ == "__main__":
    r = check(sys.argv[1], sys.argv[2])
    raise SystemExit(0 if r["passed"] else 1)
