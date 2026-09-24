#!/usr/bin/env python3
"""R526 automated clean-replay verification artifact.

Emits R526/CLEAN_REPLAY.json. Layers:

  A. Attribution-instrument integrity (runnable before AND after a
     cliff intervention): manifest identity, arm-label consistency,
     stage-table discipline (no zero for unexecuted, skip reasons
     carried), ledger consistency, source tagging (LIVE_API rows never
     carry derived span rates), funnel typed, secret scan over
     committable R526 artifacts.

  B. Measurement-shape proof:
     - every durable current-arm row must carry the deployed-R523
       shape: sources_excluded ['openalex'] on the envelope (the
       battery ran on current production as configured, not a
       different build).
     - if an after arm exists (one named intervention authorized by
       the completed ranking): the delta shape is recorded, never
       inferred.
     - the per-source job-wall table must be present on durable rows
       (the ranking input Art. LXXXIII requires).

Art. X: one instrument, one artifact. No hand-edited claims.
No provider credentials required for this replay.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
R526 = REPO / "R526"


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(name):
    p = R526 / name
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> int:
    checks: list[dict] = []
    failures: list[str] = []

    def check(name, ok, detail):
        checks.append({"name": name, "ok": (None if ok is None
                                            else bool(ok)),
                       "detail": detail})
        if ok is False:
            failures.append(name)

    def note(name, detail):
        checks.append({"name": name, "ok": None, "detail": detail})

    manifest = _load("BATTERY_PROBLEMS.json")
    check("manifest_present_and_ok",
          bool(manifest) and manifest.get("selection_status") == "OK",
          {"n": (manifest or {}).get("n_problems"),
           "families": (manifest or {}).get("declared_families")})
    man_sha = hashlib.sha256(
        (R526 / "BATTERY_PROBLEMS.json").read_bytes()).hexdigest() \
        if manifest else None

    for arm_file, arm in (("ATTR_CURRENT_HARVEST.json", "current"),
                          ("ATTR_AFTER_HARVEST.json", "after")):
        h = _load(arm_file)
        if h is None:
            note(f"{arm}_harvest_present", "harvest not run yet")
            continue
        check(f"{arm}_harvest_present", True, {"rows": h.get("n_rows")})
        check(f"{arm}_manifest_sha_matches",
              h.get("manifest_sha256") == man_sha,
              {"harvest": (h.get("manifest_sha256") or "")[:12],
               "manifest": (man_sha or "")[:12]})
        check(f"{arm}_arm_label_consistent",
              h.get("arm") == arm and all(
                  r.get("arm") == arm for r in h.get("rows", [])), {})
        rows = [r for r in h.get("rows", []) if "stage_table" in r]
        bad = []
        for r in rows:
            for e in r.get("stage_table", []):
                ec = e.get("entry_class")
                if ec == "EXECUTED" and e.get("wall_s") == 0:
                    bad.append((r.get("problem_index"), e.get("stage"),
                                "zero-wall-executed"))
                if ec in ("SKIPPED_ADMISSION", "SKIPPED_UPSTREAM_FAILURE"):
                    if e.get("wall_s") == 0:
                        bad.append((r.get("problem_index"), e.get("stage"),
                                    "zero-wall-skipped"))
                    if not e.get("skip_reason"):
                        bad.append((r.get("problem_index"), e.get("stage"),
                                    "skip-without-reason"))
        check(f"{arm}_stage_table_discipline", not bad,
              {"violations": bad})
        bad_l = []
        for r in rows:
            for role, b in (r.get("ledger_per_role") or {}).items():
                if b.get("class") == "OFFLINE_DERIVED":
                    if (b.get("provider_call_wall_s") or 0) < 0:
                        bad_l.append((r.get("problem_index"), role))
        check(f"{arm}_ledger_consistency", not bad_l, {"violations": bad_l})
        live_span = [r.get("problem_index") for r in rows
                     if r.get("observation_source") == "LIVE_API"
                     and (r.get("synthesize_validity") or {}).get(
                         "span_verbatim_rate") is not None]
        check(f"{arm}_live_span_discipline", not live_span,
              {"violations": live_span})
        no_funnel = [r.get("problem_index") for r in rows
                     if r.get("funnel_row_class") not in (
                         "OBSERVED_IN_STAGE", "UNKNOWN")]
        check(f"{arm}_funnel_typed", not no_funnel,
              {"violations": no_funnel})
        # job-wall table present on durable rows (ranking input)
        dur = [r for r in rows
               if r.get("observation_source") == "DURABLE_BRANCH"]
        have_jw = [r for r in dur
                   if (r.get("source_job_walls") or {}).get("jobs")]
        check(f"{arm}_job_wall_table_present",
              dur and len(have_jw) == len(dur),
              {"durable_rows": len(dur), "with_table": len(have_jw)})

    # Layer B: the current arm must carry the deployed-R523 shape
    hc = _load("ATTR_CURRENT_HARVEST.json")
    if hc is not None:
        excl = {}
        n = 0
        for r in hc.get("rows", []):
            if "stage_table" not in r or r.get(
                    "observation_source") != "DURABLE_BRANCH":
                continue
            n += 1
            e = (r.get("openalex") or {}).get("sources_excluded_envelope")
            key = json.dumps(e, sort_keys=True)
            excl[key] = excl.get(key, 0) + 1
        check("current_arm_is_deployed_r523_shape",
              n > 0 and excl.get('["openalex"]') == n,
              {"durable_rows": n, "excluded_shapes": excl})
    if _load("ATTR_AFTER_HARVEST.json") is None:
        note("after_arm_shape",
             "no after arm yet: either the round is measurement-only "
             "(no cliff named) or the after battery has not run — "
             "record honestly in the round record either way")

    # secret scan over committable R526 artifacts
    dirty = []
    for f in sorted(R526.glob("*.json")):
        if "BATTERY_SESSIONS" in f.name and "REDACTED" not in f.name:
            continue
        try:
            s = f.read_text(encoding="utf-8")
        except Exception:
            continue
        hits = re.findall(r"ghp_[A-Za-z0-9]{8}|sk-[A-Za-z0-9]{8}", s)
        if "owner_key" in s.lower():
            hits.append("owner_key-present")
        if hits:
            dirty.append({"file": f.name, "hits": hits})
    check("secret_scan_clean", not dirty, {"dirty": dirty})

    out = {"artifact": "R526_CLEAN_REPLAY/1.0",
           "ran_at_utc": _utcnow(),
           "checks": checks,
           "failures": failures,
           "result": "FAIL" if failures else "PASS",
           "reviewer_provenance": "AI_REVIEW"}
    R526.mkdir(parents=True, exist_ok=True)
    (R526 / "CLEAN_REPLAY.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8")
    print(f"{out['result']}: {sum(1 for c in checks if c['ok'])}/"
          f"{len(checks)} -> R526/CLEAN_REPLAY.json")
    return 0 if out["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
