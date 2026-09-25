#!/usr/bin/env python3
"""R527 round-record generator + closure reconciliation.

R527 is a distinct intervention round (the single authorized
intervention: remove the fixed 0.5 s post-success SYNTHESIZE sleep).
This generator produces the durable R527_ROUND_RECORD.json from the
existing evidence artifacts:

  - R526/ATTR_CURRENT_HARVEST.json   (baseline arm, build 03881b2b4)
  - R526/ATTR_AFTER_HARVEST.json     (after arm, build 9392c181b)
  - R526/ATTR_COMPARISON.json        (paired before/after)
  - R527/AFTER_DEPLOY_RECORD.json    (after-arm deploy identity)

The five round-states are recorded EXPLICITLY and NEVER collapsed:
  measurement_complete
  optimization_authorized
  optimization_executed
  optimization_measured
  optimization_deployed

R527 closure reconciliation (the directive section 2 requirement):
  - R527 intervention identity (the single authorized change)
  - after-arm build identity (9392c181b, measured via session
    expected_commit, not the manifest stamp)
  - paired comparison (ATTR_COMPARISON.json, n_paired_problems == 10)
  - measured sleep effect (baseline ~0.5 s -> after 0.0 s, 10/10)
  - discovery-funnel outcome (mechanisms_found: baseline 4/10,
    after 1/10 — recorded as an observed arm confound /
    provider-state difference, NOT attributed to the sleep
    intervention)
  - remaining confounds (provider-inference variance in the after
    window: SYNTHESIZE stage wall 9.8 s -> 68.6 s; free-tier
    flapping, not the sleep removal)
  - final classification

The record is machine-generated from the durable artifacts — no
manual JSON edit, no hand-modified production evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
R526 = REPO / "R526"
R527 = REPO / "R527"
OUT = R527 / "R527_ROUND_RECORD.json"

# the R527 intervention (the single authorized change, frozen at Q3)
R527_INTERVENTION = {
    "id": "SYNTHESIZE_POST_SUCCESS_SLEEP_REMOVAL",
    "description": ("remove the fixed 0.5 s post-success sleep in "
                    "a2/synthesize.llm_chat res.ok path"),
    "source": "discovery_fabric/a2/synthesize.py llm_chat()",
    "claimed_effect": "~0.5 s per successful SYNTHESIZE call "
                     "(10/10 baseline R526 S5 fresh battery)",
    "baseline_sleep_s": 0.5,
    "after_sleep_s": 0.0,
    "intervention_commit": "c2015dfb3b8d45012bfa01c5faa011fa01598e8d",
    "measurement_commit": "9392c181bbf6ea2e50964580ad95111d5b776e54",
}
# the baseline build (the R526 S5 fresh current-arm build)
BASELINE_SHA = "03881b2b48ff52bf5b79966dd15c63879ac3a55f"
# the after-arm build (the R527 Q5 corrected build, deployed + measured)
AFTER_SHA = "9392c181bbf6ea2e50964580ad95111d5b776e54"


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _load(name: str) -> dict:
    p = R526 / name
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _synth_sleep(h: dict, arm: str) -> dict:
    """Extract the post_success_sleep_s mean from a harvest's
    synthesize_spans block on each row."""
    vs = []
    for r in h.get("rows", []):
        if "stage_table" not in r:
            continue
        ss = (r.get("synthesize_spans") or {}).get("spans") or {}
        v = ss.get("post_success_sleep_s")
        if v is not None:
            vs.append(v)
    if not vs:
        return {"n": 0, "mean": None,
                "note": ("post_success_sleep_s not present on this "
                         "arm (pre-Q5 instrumentation build)"
                         if arm == "current" else None)}
    return {"n": len(vs), "mean": round(sum(vs) / len(vs), 6),
            "values": vs}


def _mechanisms_found(h: dict) -> dict:
    """The discovery-funnel mechanisms_found outcome per row.

    R529 §2.1 repair: the canonical harvested schema is a STRUCTURED
    object, not a numeric scalar:
      funnel_row["mechanisms_found"] = {
        "n_candidates_generated": int,
        "reached": bool,
        "state": "BUILT" | "NO_CANDIDATES" | ...,
        "typed_drop_reason": str | None,
        "evidence": {"file": ..., "pointer": ...},
      }
    (evidence file = envelope_MECHANISM_SPACE.json when the stage
    executed with a durable mechanism_space block, else
    envelope_RANK.json $.stage_log[MECHANISM_SPACE].result_meta.)

    A row counts as mechanisms-found when reached is True (the
    canonical boolean) OR n_candidates_generated > 0 (the canonical
    count). No invented or estimated values: a row whose block is
    absent or unparseable is recorded as UNKNOWN, never as zero.
    The per-row detail (problem_index, reached, n, state) is
    preserved so the arm difference is auditable row-by-row.
    """
    found = 0
    total = 0
    unknown = 0
    per_row = []
    for r in h.get("rows", []):
        if "stage_table" not in r:
            continue
        total += 1
        fr = r.get("funnel_row") or {}
        mf = fr.get("mechanisms_found")
        pi = r.get("problem_index")
        if not isinstance(mf, dict):
            # absent or non-canonical block: UNKNOWN, never zero
            unknown += 1
            per_row.append({"problem_index": pi, "reached": None,
                            "n_candidates_generated": None,
                            "state": "UNKNOWN",
                            "note": "mechanisms_found block absent or "
                                    "non-canonical (Art. XXV)"})
            continue
        reached = mf.get("reached") is True
        n = mf.get("n_candidates_generated")
        if reached or (isinstance(n, (int, float)) and n > 0):
            found += 1
        per_row.append({
            "problem_index": pi,
            "reached": bool(reached),
            "n_candidates_generated": n,
            "state": mf.get("state"),
            "typed_drop_reason": mf.get("typed_drop_reason"),
        })
    return {"mechanisms_found": found, "n_rows": total,
            "n_unknown": unknown,
            "rate": (round(found / total, 3) if total else None),
            "per_row": per_row}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--deploy-sha", default=AFTER_SHA,
                    help="the after-arm deployed build SHA (default: "
                         "the R527 Q5 corrected build)")
    ap.add_argument("--baseline-sha", default=BASELINE_SHA,
                    help="the baseline (current-arm) build SHA")
    args = ap.parse_args()

    cur = _load("ATTR_CURRENT_HARVEST.json")
    aft = _load("ATTR_AFTER_HARVEST.json")
    comp = _load("ATTR_COMPARISON.json")
    dep_path = R527 / "AFTER_DEPLOY_RECORD.json"
    dep = json.loads(dep_path.read_text(encoding="utf-8")) \
        if dep_path.exists() else {}

    assert comp.get("n_paired_problems") is not None, \
        "ATTR_COMPARISON.json absent or empty — the paired " \
        "comparison is not durable; R527 closure cannot proceed " \
        "(fail-closed)"

    # ---- the measured sleep effect (baseline vs after) ----
    cur_sleep = _synth_sleep(cur, "current")
    aft_sleep = _synth_sleep(aft, "after")
    sleep_effect_proven = (
        aft_sleep.get("n", 0) == 10
        and (aft_sleep.get("mean") or 1.0) < 0.05
        and R527_INTERVENTION["baseline_sleep_s"] >= 0.5)

    # ---- discovery-funnel outcome (the confound, not the effect) ----
    cur_mf = _mechanisms_found(cur)
    aft_mf = _mechanisms_found(aft)
    funnel_confounded = (cur_mf.get("mechanisms_found")
                         != aft_mf.get("mechanisms_found"))

    # ---- provider-inference variance (the remaining confound) ----
    def _stage_wall(h, stage):
        vs = []
        for r in h.get("rows", []):
            if "stage_table" not in r:
                continue
            for e in r.get("stage_table", []):
                if (e.get("stage") == stage
                        and e.get("entry_class") == "EXECUTED"):
                    vs.append(e.get("wall_s"))
        vs = [v for v in vs if v is not None]
        return (round(sum(vs) / len(vs), 3) if vs else None)
    cur_synth_wall = _stage_wall(cur, "SYNTHESIZE")
    aft_synth_wall = _stage_wall(aft, "SYNTHESIZE")
    provider_variance = (
        (cur_synth_wall is not None and aft_synth_wall is not None)
        and aft_synth_wall > cur_synth_wall * 3)

    # ---- production identity (LIVE, the directive §2.2 chain) ----
    # R529 §2.2 repair: the round may only become deployed/closed
    # when the constitutional identity chain is EXPLICIT:
    #   target_sha -> deployed_sha -> production deployment
    #   identity -> health -> drift
    # Do NOT infer deployment from the existence of a commit or from
    # a config read-back (ENGINE_EVIDENCE_FABRIC=="0" is a standing-
    # config check, not a drift check). Query the LIVE production
    # endpoints and record each link of the chain from durable
    # evidence: the deploy record's commit (deployed_sha claim), the
    # after-harvest's measured_engine_sha (build-identity custody),
    # and the live /api/version + /api/health read-back.
    import urllib.request as _urlreq
    _PROD_BASE = "https://prateekm1-toscanini-prod-validation.hf.space"

    def _live_get(path: str, timeout: int = 60) -> dict:
        try:
            with _urlreq.urlopen(_PROD_BASE + path,
                                 timeout=timeout) as _r:
                return json.loads(_r.read().decode())
        except Exception as _e:
            return {"probe_error": f"{type(_e).__name__}: "
                                   f"{str(_e)[:120]}"}

    _live_version = _live_get("/api/version")
    _live_health = _live_get("/api/health")
    _live_engine = _live_version.get("engine_commit") or ""
    _live_drift = ((_live_health.get("deployment_identity") or {})
                   .get("deployment_drift") or "UNKNOWN")
    _live_tamper = ((_live_health.get("deployment_identity") or {})
                    .get("identity_tamper"))
    _live_health_ok = _live_health.get("ok", _live_health.get(
        "status") in (None, "ok", "healthy", "GREEN"))
    _aft_measured = (aft.get("measured_engine_sha") or "")
    _deploy_commit = dep.get("commit") or ""
    # link 1: target_sha == the after-arm build the round intended
    # link 2: deployed_sha == the commit the deploy record claims
    # link 3: custody == the after-harvest's measured build identity
    # link 4: live == what production actually serves right now
    # link 5: drift == the deployment_drift read-back
    _chain = {
        "target_sha": args.deploy_sha,
        "deploy_record_commit": _deploy_commit,
        "harvest_measured_engine_sha": _aft_measured,
        "live_engine_commit": _live_engine,
        "live_drift": _live_drift,
        "live_tamper": _live_tamper,
    }
    _link_target_deploy = (_deploy_commit == args.deploy_sha)
    _link_deploy_custody = (_deploy_commit == _aft_measured)
    _link_live_deploy = (_live_engine == _deploy_commit)
    _link_drift_green = (_live_drift == "GREEN" and _live_tamper is False)
    _production_identity_chain_ok = (
        _link_target_deploy and _link_deploy_custody
        and _link_live_deploy and _link_drift_green)
    # legacy proxies (kept for record continuity, now each backed by
    # an explicit chain link rather than a config coincidence):
    drift_green = _link_drift_green
    deploy_sha_match = _link_target_deploy and _link_live_deploy

    # ---- round states (explicit, never collapsed) ----
    measurement_complete = (comp.get("n_paired_problems") is not None
                            and aft_sleep.get("n", 0) == 10)
    optimization_authorized = True  # the single authorized intervention
    optimization_executed = True     # the sleep was removed in the build
    optimization_measured = sleep_effect_proven
    optimization_deployed = (deploy_sha_match and drift_green)

    rec = {
        "artifact": "R527_ROUND_RECORD/1.0",
        "round": "R527",
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                       time.gmtime()),
        "reviewer_provenance": "AI_REVIEW",
        "parent_round": "R526",
        "intervention": R527_INTERVENTION,
        "arms": {
            "baseline": {
                "build_sha": args.baseline_sha,
                "harvest": "R526/ATTR_CURRENT_HARVEST.json",
                "harvest_sha256": (_sha(R526 / "ATTR_CURRENT_HARVEST.json")
                                   if (R526 / "ATTR_CURRENT_HARVEST.json")
                                   .exists() else None),
                "post_success_sleep_s": cur_sleep,
                "synth_stage_wall_s": cur_synth_wall,
                "mechanisms_found": cur_mf,
            },
            "after": {
                "build_sha": args.deploy_sha,
                "harvest": "R526/ATTR_AFTER_HARVEST.json",
                "harvest_sha256": (_sha(R526 / "ATTR_AFTER_HARVEST.json")
                                   if (R526 / "ATTR_AFTER_HARVEST.json")
                                   .exists() else None),
                "post_success_sleep_s": aft_sleep,
                "synth_stage_wall_s": aft_synth_wall,
                "mechanisms_found": aft_mf,
                "deploy_record": "R527/AFTER_DEPLOY_RECORD.json",
                "deploy_commit": dep.get("commit"),
                "harvest_measured_engine_sha": _aft_measured,
                "production_identity_chain": {
                    **_chain,
                    "link_target_deploy": _link_target_deploy,
                    "link_deploy_custody": _link_deploy_custody,
                    "link_live_deploy": _link_live_deploy,
                    "link_drift_green": _link_drift_green,
                    "chain_ok": _production_identity_chain_ok,
                    "rule": ("target_sha == deploy-record commit == "
                             "harvest measured_engine_sha == live "
                             "production engine_commit, AND live drift "
                             "GREEN AND tamper false. Deployment is "
                             "NOT inferred from a commit's existence."),
                },
            },
        },
        "paired_comparison": {
            "artifact": "R526/ATTR_COMPARISON.json",
            "n_paired_problems": comp.get("n_paired_problems"),
            "current_ref": comp.get("current_harvest"),
            "after_ref": comp.get("after_harvest"),
        },
        "measured_sleep_effect": {
            "proven": sleep_effect_proven,
            "baseline_mean_s": cur_sleep.get("mean"),
            "after_mean_s": aft_sleep.get("mean"),
            "n_after_rows": aft_sleep.get("n"),
            "rule": ("the sleep effect is proven when the after arm "
                     "carries post_success_sleep_s on all 10 rows "
                     "with a mean < 0.05 s (the fixed 0.5 s sleep is "
                     "removed); the baseline reference is the R526 "
                     "S5 fresh battery (~0.5 s on 10/10 calls)"),
        },
        "discovery_funnel_outcome": {
            "confounded": funnel_confounded,
            "baseline_mechanisms_found": cur_mf,
            "after_mechanisms_found": aft_mf,
            "note": ("mechanisms_found changed materially "
                     f"(baseline {cur_mf.get('mechanisms_found')} vs "
                     f"after {aft_mf.get('mechanisms_found')}) — this "
                     "is an OBSERVED ARM CONFOUND / provider-state "
                     "difference, NOT attributed to the sleep "
                     "intervention (the directive section 3 rule: "
                     "do not attribute that difference to the "
                     "sleep; record it as a confound)"),
        },
        "remaining_confounds": {
            "provider_inference_variance": provider_variance,
            "synth_stage_wall_baseline_s": cur_synth_wall,
            "synth_stage_wall_after_s": aft_synth_wall,
            "note": ("the after-arm SYNTHESIZE stage wall is "
                     f"{aft_synth_wall} s vs baseline {cur_synth_wall} s — "
                     "this is provider-inference variance "
                     "(free-tier flapping in the after window), "
                     "NOT the sleep-removal effect (the sleep was "
                     "~0.5 s, ~5% of the baseline stage wall). The "
                     "unattributed remainder is recorded as "
                     "UNATTRIBUTED; it is NOT distributed to the "
                     "intervention."),
        },
        "round_states": {
            "measurement_complete": measurement_complete,
            "optimization_authorized": optimization_authorized,
            "optimization_executed": optimization_executed,
            "optimization_measured": optimization_measured,
            "optimization_deployed": optimization_deployed,
            "note": ("these five states are distinct and never "
                     "collapsed. optimization_measured is TRUE only "
                     "when the measured before/after sleep effect is "
                     "durable (after post_success_sleep_s ~0 on "
                     "10/10 rows). The funnel confound + provider "
                     "variance are recorded as UNKNOWN remainders, "
                     "never forced into the intervention claim."),
        },
        "classification": (
            "SLEEP_REMOVAL_MEASURED__FUNNEL_CONFOUND_DISCLOSED"
            if optimization_measured else
            "MEASUREMENT_OPEN__SLEEP_EFFECT_UNPROVEN"),
        "classification_not": [
            "NOT claimed: end-to-end discovery runtime improvement "
            "(the provider-inference variance dominates the stage "
            "wall; the 0.5 s sleep was ~5% of baseline)",
            "NOT claimed: discovery-funnel equivalence (the "
            "mechanisms_found drop is an arm confound, not the "
            "intervention effect)",
            "NOT claimed: the 0.5 s removal made the engine faster "
            "overall (only the sleep component is measured; "
            "provider inference is the dominant cost)",
        ],
        "next_round": {
            "target": "MECHANISM_SPACE",
            "rule": ("the next substantive target is the "
                     "constitutional funnel bottleneck "
                     "(Art. LXXXIII): the largest dropout stage "
                     "on the frozen battery. The MECHANISM_SPACE "
                     "subphase decomposition (mechanism_attribution/"
                     "1.0.0) is the next measurement to surface "
                     "before any optimization is named."),
        },
    }
    OUT.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print(f"wrote {OUT} "
          f"(classification={rec['classification']}, "
          f"measured={optimization_measured}, "
          f"deployed={optimization_deployed})")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
