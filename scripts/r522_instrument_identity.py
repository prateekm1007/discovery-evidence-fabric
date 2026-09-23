#!/usr/bin/env python3
"""R522 instrument-identity proof (Art. XLVII / LXII / XVI).

The R522 baseline arm must be the exact current production retrieval
path (openalex enabled) even though it runs on the winner engine (which
carries the dormant centralized exclusion authority). An assertion is
not proof (Art. XVI). This instrument MEASURES that claim: it extracts
two committed trees via `git archive` (immune to worktree state), runs
the SAME hermetic planner in each as an isolated subprocess, and
requires the deterministic V2 fan-out plan to be byte-identical with
ENGINE_RETRIEVE_EXCLUDE_SOURCES unset.

If the dormant authority altered the unset-path plan at all, the two
fingerprints would differ and this exits nonzero. It is run for:
  - production winner 91c92371 (no authority, current prod), and
  - the R522 commit under test (authority present, dormant),
both with the switch unset -> identical plan -> the baseline arm IS the
current production retrieval path, and the only difference to the after
arm is the switch value.

Usage:
  python scripts/r522_instrument_identity.py \
      --commit-prod 91c92371... --commit-r522 2f3cde35...
Deterministic (no timestamps, sorted keys). No network. No Space creds.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# the hermetic planner, run inside each extracted tree: fixed variants,
# a deterministic sentinel connector per source, no network. Emits a
# canonical plan fingerprint (kind, lane, source_id, sorted queries)
# plus the resolved exclusion set.
PLANNER = r'''
import json, os, sys
sys.path.insert(0, ".")
from discovery_fabric.retrieval_fabric import pipeline as p
VARIANTS = [
    {"query": "clutch pressure plate engagement failure surge",
     "derivation_class": "PRIMARY"},
    {"query": "plate wear comparison target",
     "derivation_class": "COMPARISON_TARGETED"},
    {"query": "transmission hydraulic domain",
     "derivation_class": "DOMAIN_NARROW"},
    {"query": "automotive actuator cross domain",
     "derivation_class": "CROSS_DOMAIN_TERM"},
]
def stub(sid, scoped=None):
    return object()
p._connector_for = stub
plan = p._plan_fanout_jobs(VARIANTS)
rows = []
for u in plan:
    if u["kind"] == "job":
        j = u["job"]
        rows.append(["job", j["lane"], j["source_id"],
                     sorted(v["query"] for v in j["variants"])])
    else:
        s = u["state"]
        rows.append(["lane_state", s.lane, s.source_id,
                     s.status, sorted(s.queries)])
out = {
    "excluded": p.excluded_sources() if hasattr(p, "excluded_sources")
                else "NO_AUTHORITY",
    "plan": rows,
    "has_authority": hasattr(p, "excluded_sources"),
}
print(json.dumps(out, sort_keys=True))
'''


def run_planner(tree: Path, exclude=None):
    env = dict(__import__("os").environ)
    env["PYTHONPATH"] = str(tree)
    if exclude is not None:
        env["ENGINE_RETRIEVE_EXCLUDE_SOURCES"] = exclude
    else:
        env.pop("ENGINE_RETRIEVE_EXCLUDE_SOURCES", None)
    r = subprocess.run([sys.executable, "-c", PLANNER],
                       cwd=str(tree), capture_output=True, text=True,
                       timeout=180, env=env)
    if r.returncode != 0:
        raise RuntimeError(f"planner failed in {tree}: {r.stderr[-400:]}")
    return json.loads(r.stdout.strip().splitlines()[-1])


def extract(commit: str, dest: Path):
    r = subprocess.run(["git", "archive", "--format=tar", commit],
                       cwd=str(REPO), capture_output=True, timeout=600)
    if r.returncode != 0:
        raise RuntimeError(f"git archive {commit}: {r.stderr[-300:]}")
    with tarfile.open(fileobj=io.BytesIO(r.stdout)) as tf:
        tf.extractall(str(dest))  # noqa: S202 (trusted local tree)


def canon(obj) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True).encode("utf-8")).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--commit-prod", required=True,
                    help="current production winner SHA (no authority)")
    ap.add_argument("--commit-r522", required=True,
                    help="R522 commit under test (dormant authority)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    report = {"checks": [], "failures": []}

    def check(name, ok, detail):
        report["checks"].append({"name": name, "ok": bool(ok),
                                 "detail": detail})
        if not ok:
            report["failures"].append(name)

    with tempfile.TemporaryDirectory() as td:
        tprod = Path(td) / "prod"
        t522 = Path(td) / "r522"
        tprod.mkdir(); t522.mkdir()
        extract(args.commit_prod, tprod)
        extract(args.commit_r522, t522)

        # 1. production tree has NO authority (as expected)
        r_prod = run_planner(tprod, exclude=None)
        check("prod_tree_has_no_authority",
              r_prod["has_authority"] is False
              and r_prod["excluded"] == "NO_AUTHORITY",
              {"has_authority": r_prod["has_authority"]})

        # 2. R522 tree HAS the dormant authority, resolves empty unset
        r522_off = run_planner(t522, exclude=None)
        check("r522_tree_has_dormant_authority",
              r522_off["has_authority"] is True
              and r522_off["excluded"] == [],
              {"has_authority": r522_off["has_authority"],
               "excluded_unset": r522_off["excluded"]})

        # 3. CORE: unset-path plan byte-identical to production
        check("baseline_plan_identical_to_production",
              canon(r_prod["plan"]) == canon(r522_off["plan"]),
              {"prod_plan_sha": canon(r_prod["plan"])[:16],
               "r522_off_plan_sha": canon(r522_off["plan"])[:16]})

        # 4. openalex is a live job on BOTH unset paths (enabled)
        def oa_job(rec):
            return [x for x in rec["plan"]
                    if x[2] == "openalex" and x[0] == "job"]
        check("openalex_enabled_on_both_baseline_paths",
              len(oa_job(r_prod)) == 1 and len(oa_job(r522_off)) == 1,
              {"prod": len(oa_job(r_prod)),
               "r522_off": len(oa_job(r522_off))})

        # 5. flipping the switch yields EXCLUDED + no job, and does NOT
        #    change the OTHER sources' plan (blast radius = openalex)
        r522_on = run_planner(t522, exclude="openalex")
        oa_on = [x for x in r522_on["plan"] if x[2] == "openalex"]
        check("switch_makes_openalex_excluded_not_absent",
              len(oa_on) == 1 and oa_on[0][0] == "lane_state"
              and oa_on[0][3] == "EXCLUDED",
              {"openalex_unit": oa_on[0][:4]})
        prod_others = sorted(json.dumps(x) for x in r522_off["plan"]
                             if x[2] != "openalex")
        on_others = sorted(json.dumps(x) for x in r522_on["plan"]
                           if x[2] != "openalex")
        check("only_openalex_changes_when_switch_flips",
              prod_others == on_others,
              {"n_other_units": len(prod_others)})

    report["result"] = "PASS" if not report["failures"] else "FAIL"
    payload = json.dumps(report, indent=1, sort_keys=True)
    if args.out:
        Path(args.out).write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0 if report["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
