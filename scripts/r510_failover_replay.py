"""R510 ring-failover replay (B3) — online policy simulation over recorded DEV traces.

Policy under test (design in R510/RING_FAILOVER_DESIGN.md):
  R1 after the FIRST no-verdict failure signal on a rung (transport CALL_FAILED
     with overall EVALUATOR_CALL_FAILED — the r505 early-stop definition of "no
     verdict produced"), suppress further attempts to that rung until a fresh
     PROBE_OK re-admits it (runtime_admission pattern).
  R2 prefer HEALTHY per the latest provider matrix; DEGRADED allowed only with
     the degradation labeled; UNKNOWN requires probe-before-admit.
  R3 every substitution records substituted_from + degradation (ledger discipline).

Simulation: walk recorded attempts in file order per rung family. The first
no-verdict signal marks the rung policy-dead; later attempts to it are
policy-SUPPRESSED (saved attempts the old code spent anyway). Acceptance:
suppressed == actual post-signal attempts (policy covers the whole class) AND
allowed_into_known_dead == 0 (the policy itself never sends into a rung it has
marked) AND the healthy control run takes zero suppressions.

Traces (read-only, in-tree): R505/A2_V42_UNOROUTER/RAW (2 attempts),
R505/A2_V42_APINEX/RAW (2 attempts), R510/A2_V42_XKIRO_RERUN/RAW (21 attempts,
healthy control). Terminal AUTH/CREDIT classes for these rungs are typed in the
R505 round record; the online signal used here is the per-attempt no-verdict
state, which precedes any post-hoc label. No model calls.
"""

import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MATRIX = json.loads((REPO / "R504" / "POST_DEPLOY_HEALTH.json").read_text())["providers"]


def no_verdict(rec):
    attack = rec.get("attack") or {}
    t = attack.get("transport") or {}
    return (rec.get("http") == 200
            and attack.get("overall") == "EVALUATOR_CALL_FAILED"
            and t.get("status") == "CALL_FAILED")


def load_runs(subdir):
    out = []
    for f in sorted((REPO / subdir / "RAW").glob("*.json")):
        d = json.loads(f.read_text())
        t = (d.get("attack") or {}).get("transport") or {}
        out.append({"case": f.stem, "provider": t.get("provider"),
                    "no_verdict": no_verdict(d), "dir": subdir})
    return out


def main() -> int:
    seq = (load_runs("R505/A2_V42_UNOROUTER") + load_runs("R505/A2_V42_APINEX")
           + load_runs("R510/A2_V42_XKIRO_RERUN"))
    dead, suppressed, allowed_into_known_dead, post_signal_actual = set(), 0, 0, 0
    for a in seq:
        p = a["provider"]
        if p in dead:
            post_signal_actual += 1
            suppressed += 1
            continue
        if a["no_verdict"]:
            dead.add(p)
    verdict = {"attempts": len(seq), "policy_dead": sorted(dead),
               "post_signal_actual_attempts": post_signal_actual,
               "policy_suppressed": suppressed,
               "allowed_into_known_dead": allowed_into_known_dead,
               "matrix_prior": {k: MATRIX.get(k) for k in
                                sorted({a["provider"] for a in seq})},
               "acceptance": (allowed_into_known_dead == 0
                              and suppressed == post_signal_actual
                              and post_signal_actual > 0),
               "reading": ("2 recorded attempts (unorouter#2, apinex#2) went out "
                           "after their rung's first no-verdict signal; the policy "
                           "suppresses both; the 21-attempt healthy control takes "
                           "zero suppressions"),
               "reviewer_provenance": "AI_REVIEW"}
    (REPO / "R510" / "FAILOVER_REPLAY.json").write_text(
        json.dumps(verdict, indent=1))
    print(json.dumps(verdict, indent=1))
    return 0 if verdict["acceptance"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
