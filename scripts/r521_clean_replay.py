#!/usr/bin/env python3
"""R521 automated clean-replay verification artifact.

Emits R521/CLEAN_REPLAY.json. Two layers:
  A. Attribution-instrument integrity (runnable before AND after the
     cliff intervention): manifest identity, stage-table completeness,
     no-zero-for-unexecuted, ledger consistency, RETRIEVE two-level
     presence + connector verdict, source tagging, funnel presence,
     live-tag discipline, secret scan, battery integrity.
  B. Cliff-intervention checks: appended ONLY after the single R521
     behavioral change lands (same pattern as R520's change-specific
     checks 1-9). Until then, layer B records ABSENT (not failed).

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
sys.path.insert(0, str(REPO))

R521 = REPO / "R521"


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(name):
    p = R521 / name
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> int:
    checks: list[dict] = []
    failures: list[str] = []

    def check(name: str, ok: bool, detail) -> None:
        checks.append({"name": name, "ok": bool(ok), "detail": detail})
        if not ok:
            failures.append(name)

    manifest = _load("BATTERY_PROBLEMS.json")
    check("manifest_present_and_ok",
          bool(manifest) and manifest.get("selection_status") == "OK",
          {"n": (manifest or {}).get("n_problems")})
    man_sha = hashlib.sha256(
        (R521 / "BATTERY_PROBLEMS.json").read_bytes()).hexdigest() \
        if manifest else None

    for arm_file, arm in (("ATTR_BEFORE_HARVEST.json", "before"),
                          ("ATTR_AFTER_HARVEST.json", "after")):
        h = _load(arm_file)
        if h is None:
            checks.append({"name": f"{arm}_harvest_present", "ok": None,
                           "detail": "harvest not run yet (not failed)"})
            continue
        check(f"{arm}_harvest_present", True, {"rows": h.get("n_rows")})
        check(f"{arm}_manifest_sha_matches",
              h.get("manifest_sha256") == man_sha,
              {"harvest": (h.get("manifest_sha256") or "")[:12],
               "manifest": (man_sha or "")[:12]})
        check(f"{arm}_arm_label_consistent",
              h.get("arm") == arm and all(
                  r.get("arm") == arm for r in h.get("rows", [])),
              {})
        rows = [r for r in h.get("rows", []) if "stage_table" in r]
        # stage-table completeness + no-zero-for-unexecuted
        bad = []
        for r in rows:
            for e in r.get("stage_table", []):
                if e.get("entry_class") == "EXECUTED" and \
                        e.get("wall_s") == 0:
                    bad.append((r.get("problem_index"), e.get("stage"),
                                "zero-wall-executed"))
                if e.get("entry_class") in ("SKIPPED_ADMISSION",
                                            "SKIPPED_UPSTREAM_FAILURE") \
                        and e.get("wall_s") == 0:
                    bad.append((r.get("problem_index"), e.get("stage"),
                                "zero-wall-skipped"))
                if e.get("entry_class") in ("SKIPPED_ADMISSION",
                                            "SKIPPED_UPSTREAM_FAILURE") \
                        and not e.get("skip_reason"):
                    bad.append((r.get("problem_index"), e.get("stage"),
                                "skip-without-reason"))
        check(f"{arm}_stage_table_discipline", not bad, {"violations": bad})
        # ledger consistency
        bad_l = []
        for r in rows:
            for role, b in (r.get("ledger_per_role") or {}).items():
                if b.get("class") == "OFFLINE_DERIVED":
                    if (b.get("provider_call_wall_s") or 0) < 0:
                        bad_l.append((r.get("problem_index"), role))
                    atts = b.get("attempts_seen") or []
                    if any(not isinstance(a, int) for a in atts):
                        bad_l.append((r.get("problem_index"), role))
        check(f"{arm}_ledger_consistency", not bad_l, {"violations": bad_l})
        # RETRIEVE two-level + connector verdict on durable rows
        dur = [r for r in rows
               if r.get("observation_source") == "DURABLE_BRANCH"]
        two = [r for r in dur if "retrieve_two_level" in r
               and "connector_visibility_verdict" in
               r.get("retrieve_two_level", {})]
        check(f"{arm}_retrieve_two_level_present",
              len(two) == len(dur) and len(dur) > 0,
              {"durable_rows": len(dur), "with_two_level": len(two)})
        # source tagging: no live-sourced span rates
        live_span = [r.get("problem_index") for r in rows
                     if r.get("observation_source") == "LIVE_API"
                     and (r.get("synthesize_validity") or {}).get(
                         "span_verbatim_rate") is not None]
        check(f"{arm}_live_span_discipline", not live_span,
              {"violations": live_span})
        # funnel presence (or typed reason)
        no_funnel = [r.get("problem_index") for r in rows
                     if r.get("funnel_row_class") not in (
                         "OBSERVED_IN_STAGE", "UNKNOWN")]
        check(f"{arm}_funnel_typed", not no_funnel,
              {"violations": no_funnel})

    # secret scan over committable R521 artifacts
    dirty = []
    for f in sorted(R521.glob("*.json")):
        if "BATTERY_SESSIONS" in f.name and "REDACTED" not in f.name:
            continue
        if f.name.startswith("BATTERY_LIVE"):
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

    # Layer B: cliff-intervention checks (the ENGINE_EVIDENCE_FABRIC=0
    # env knob). Before-arm rows must show the burning shape
    # (CHANNEL_ERROR crash or SUMMARY_RAN with pool=0); after-arm rows
    # must show the disabled shape (ABSENT envelope state 6/6).
    hb = _load("ATTR_BEFORE_HARVEST.json")
    ha = _load("ATTR_AFTER_HARVEST.json")
    if hb is not None:
        states = {}
        pools = []
        for r in hb.get("rows", []):
            if "stage_table" not in r:
                continue
            ef = (r.get("retrieve_two_level") or {}).get(
                "evidence_fabric") or {}
            st = ef.get("envelope_state", "MISSING_KEY")
            states[st] = states.get(st, 0) + 1
            if st == "SUMMARY_RAN":
                pools.append(ef.get("pool_items"))
        burning = (states.get("CHANNEL_ERROR", 0)
                   + states.get("SUMMARY_RAN", 0) == len(
                       [r for r in hb.get("rows", [])
                        if "stage_table" in r]) and
                   all(p == 0 for p in pools))
        check("before_ef_burning_shape", burning,
              {"envelope_states": states, "summary_pools": pools,
               "note": "before arm must show the measured burn: "
                       "crashed or ran-dry channels, zero pool"})
    if ha is not None:
        states_a = {}
        for r in ha.get("rows", []):
            if "stage_table" not in r:
                continue
            ef = (r.get("retrieve_two_level") or {}).get(
                "evidence_fabric") or {}
            st = ef.get("envelope_state", "MISSING_KEY")
            states_a[st] = states_a.get(st, 0) + 1
        n_a = len([r for r in ha.get("rows", [])
                   if "stage_table" in r])
        check("after_ef_disabled_shape",
              states_a.get("ABSENT", 0) == n_a and n_a > 0,
              {"envelope_states": states_a,
               "note": "after arm must show the disabled shape: "
                       "ABSENT envelope state on every scored row"})
    else:
        checks.append({"name": "after_ef_disabled_shape", "ok": None,
                       "detail": "after harvest not run yet (not failed)"})

    out = {"artifact": "R521_CLEAN_REPLAY/1.0",
           "ran_at_utc": _utcnow(),
           "checks": checks,
           "failures": failures,
           "result": "FAIL" if failures else "PASS",
           "reviewer_provenance": "AI_REVIEW"}
    (R521).mkdir(parents=True, exist_ok=True)
    (R521 / "CLEAN_REPLAY.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8")
    print(f"{out['result']}: {sum(1 for c in checks if c['ok'])}/"
          f"{len(checks)} -> R521/CLEAN_REPLAY.json")
    return 0 if out["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
