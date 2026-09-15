#!/usr/bin/env python3
"""R471 (external audit P0-3): the release-identity STABILITY probe.

The audit measured the production surface exposing MORE THAN ONE engine
identity across repeated observations (/api/version returned
67323d1e... then e7397192... while the audited checkout was 3b2298...),
and could not stably join the deployed artifact to the repository. The
acceptance: `/api/version`, `/api/health`, and the repository commit
agree across N repeated samples over a time window; a mixed identity
fails the release gate.

This probe IS that gate. It samples the public identity endpoints N
times over the window and exits typed:
  PASS   — one engine_commit everywhere, equal to --expect (when given)
  FAIL   — any drift, mismatch, or unreachable endpoint

Fingerprints only are printed; no credential values are involved (the
endpoints are public health/identity surfaces).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from collections import Counter

DEFAULT_BASE = "https://prateekm1-toscanini-prod-validation.hf.space"


def _get_json(base: str, path: str, timeout: float) -> dict:
    url = base.rstrip("/") + path
    req = urllib.request.Request(url, headers={"User-Agent": "r471-identity-probe/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def main() -> int:
    ap = argparse.ArgumentParser(description="release-identity stability probe")
    ap.add_argument("--base", default=DEFAULT_BASE)
    ap.add_argument("--samples", type=int, default=10,
                    help="number of identity samples (default 10)")
    ap.add_argument("--interval", type=float, default=6.0,
                    help="seconds between samples (default 6 => ~1 min window)")
    ap.add_argument("--expect", default=None,
                    help="the engine commit the deployment MUST carry")
    ap.add_argument("--timeout", type=float, default=15.0)
    args = ap.parse_args()

    commits: Counter[str] = Counter()
    constitutions: Counter[str] = Counter()
    failures: list[str] = []
    samples = []

    for i in range(1, args.samples + 1):
        try:
            ver = _get_json(args.base, "/api/version", args.timeout)
            commit = str(ver.get("engine_commit") or "")
            constitution = str(ver.get("constitution_version") or "")
            commits[commit] += 1
            constitutions[constitution] += 1
            # /api/health must agree on the same identity
            health = _get_json(args.base, "/api/health", args.timeout)
            h_commit = str(health.get("engine_commit") or "")
            ok = health.get("ok")
            if h_commit and commit and h_commit != commit:
                failures.append(
                    f"sample {i}: /api/health {h_commit[:10]} != "
                    f"/api/version {commit[:10]}")
            if ok is not True:
                failures.append(f"sample {i}: /api/health ok={ok!r}")
            samples.append({"n": i, "engine_commit": commit,
                            "health_engine_commit": h_commit,
                            "ok": ok})
            print(f"[probe {i:>2}/{args.samples}] engine={commit[:10] or 'MISSING'} "
                  f"health_ok={ok} h_engine={h_commit[:10] or 'MISSING'}",
                  flush=True)
        except Exception as exc:  # noqa: BLE001 — a probe failure IS evidence
            failures.append(f"sample {i}: {type(exc).__name__}: {exc}")
            print(f"[probe {i:>2}/{args.samples}] FAILED: "
                  f"{type(exc).__name__}: {exc}", flush=True)
        if i < args.samples:
            time.sleep(args.interval)

    distinct = [c for c in commits if c]
    verdict = "PASS"
    reasons: list[str] = []

    if len(distinct) != 1:
        verdict = "FAIL"
        reasons.append(f"MIXED IDENTITY: {len(distinct)} distinct engine "
                       f"commits observed ({dict(commits)}) — the audit's "
                       "measured class; a rolling/incoherent deployment "
                       "must not pass the release gate")
    elif not distinct:
        verdict = "FAIL"
        reasons.append("no engine_commit was ever observed")
    elif args.expect and distinct[0] != args.expect:
        verdict = "FAIL"
        reasons.append(f"identity {distinct[0][:12]} != expected "
                       f"{args.expect[:12]}")
    if failures:
        verdict = "FAIL"
        reasons.extend(failures)

    report = {
        "probe": "r471_identity_stability",
        "base": args.base,
        "samples": args.samples,
        "interval_s": args.interval,
        "observed_commits": dict(commits),
        "constitution_versions": dict(constitutions),
        "distinct_identity_count": len(distinct),
        "expected": args.expect,
        "failures": failures,
        "verdict": verdict,
        "reasons": reasons,
        "window_s": round(args.interval * max(args.samples - 1, 0), 1),
    }
    print(json.dumps(report, indent=1))
    if verdict != "PASS":
        print("[r471-identity] FAIL — " + "; ".join(reasons), file=sys.stderr)
        return 1
    print(f"[r471-identity] PASS — one stable identity "
          f"{distinct[0][:12]} across {args.samples} samples "
          f"over ~{report['window_s']}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
