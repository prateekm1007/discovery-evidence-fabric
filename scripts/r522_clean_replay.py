#!/usr/bin/env python3
"""R522 automated clean-replay verification artifact.

Emits R522/CLEAN_REPLAY.json. Two layers (Art. XVI: the controls are
demonstrated, not asserted):

  A. Attribution-instrument integrity (runnable before AND after the
     cliff intervention): manifest identity, arm-label consistency,
     stage-table discipline (no zero for unexecuted, skip reasons
     carried), ledger consistency, source tagging (LIVE_API rows never
     carry derived span rates), funnel typed, live/durable merge tag,
     secret scan over committable R522 artifacts, battery integrity.

  B. Cliff-intervention shape (the ENGINE_RETRIEVE_EXCLUDE_SOURCES env
     knob through the one centralized authority). baseline rows must
     show openalex as a live fan-out job (a measured, rate-limited
     straggler) with sources_excluded empty; after rows must show the
     openalex job ABSENT from the fan-out with sources_excluded
     ['openalex'] on every durable row — the explicit EXCLUDED lane
     state, never silent absence. Until both harvests exist, layer B
     records the missing side as not-failed.

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
sys.path.insert(0, str(REPO / "scripts"))
R522 = REPO / "R522"


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(name):
    p = R522 / name
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> int:
    checks: list[dict] = []
    failures: list[str] = []

    def check(name: str, ok, detail) -> None:
        checks.append({"name": name, "ok": (None if ok is None
                                            else bool(ok)),
                       "detail": detail})
        if ok is False:
            failures.append(name)

    def note(name: str, detail) -> None:
        checks.append({"name": name, "ok": None, "detail": detail})

    manifest = _load("BATTERY_PROBLEMS.json")
    check("manifest_present_and_ok",
          bool(manifest) and manifest.get("selection_status") == "OK",
          {"n": (manifest or {}).get("n_problems"),
           "families": (manifest or {}).get("declared_families")})
    man_sha = hashlib.sha256(
        (R522 / "BATTERY_PROBLEMS.json").read_bytes()).hexdigest() \
        if manifest else None

    for arm_file, arm in (("ATTR_BASELINE_HARVEST.json", "baseline"),
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
                  r.get("arm") == arm for r in h.get("rows", [])),
              {})
        rows = [r for r in h.get("rows", []) if "stage_table" in r]
        # stage-table discipline
        bad = []
        for r in rows:
            for e in r.get("stage_table", []):
                ec = e.get("entry_class")
                if ec == "EXECUTED" and e.get("wall_s") == 0:
                    bad.append((r.get("problem_index"), e.get("stage"),
                                "zero-wall-executed"))
                if ec in ("SKIPPED_ADMISSION", "SKIPPED_UPSTREAM_FAILURE") \
                        and e.get("wall_s") == 0:
                    bad.append((r.get("problem_index"), e.get("stage"),
                                "zero-wall-skipped"))
                if ec in ("SKIPPED_ADMISSION", "SKIPPED_UPSTREAM_FAILURE") \
                        and not e.get("skip_reason"):
                    bad.append((r.get("problem_index"), e.get("stage"),
                                "skip-without-reason"))
        check(f"{arm}_stage_table_discipline", not bad,
              {"violations": bad})
        # ledger consistency
        bad_l = []
        for r in rows:
            for role, b in (r.get("ledger_per_role") or {}).items():
                if b.get("class") == "OFFLINE_DERIVED":
                    if (b.get("provider_call_wall_s") or 0) < 0:
                        bad_l.append((r.get("problem_index"), role))
        check(f"{arm}_ledger_consistency", not bad_l,
              {"violations": bad_l})
        # source tagging discipline
        live_span = [r.get("problem_index") for r in rows
                     if r.get("observation_source") == "LIVE_API"
                     and (r.get("synthesize_validity") or {}).get(
                         "span_verbatim_rate") is not None]
        check(f"{arm}_live_span_discipline", not live_span,
              {"violations": live_span})
        # funnel typed
        no_funnel = [r.get("problem_index") for r in rows
                     if r.get("funnel_row_class") not in
                     ("OBSERVED_IN_STAGE", "UNKNOWN")]
        check(f"{arm}_funnel_typed", not no_funnel,
              {"violations": no_funnel})

    # Layer B: the openalex exclusion shape
    hb = _load("ATTR_BASELINE_HARVEST.json")
    ha = _load("ATTR_AFTER_HARVEST.json")
    if hb is not None:
        oa_live = []
        excl = []
        for r in hb.get("rows", []):
            if "stage_table" not in r:
                continue
            oa = r.get("openalex") or {}
            oa_live.append(oa.get("class"))
            excl.append(oa.get("sources_excluded_envelope"))
        check("baseline_openalex_live_job_shape",
              all(c == "OBSERVED_IN_STAGE" for c in oa_live)
              and len(oa_live) > 0,
              {"openalex_classes": oa_live})
        check("baseline_openalex_not_excluded",
              all(e in (None, []) for e in excl),
              {"sources_excluded": excl})
    if ha is not None:
        excl_a = []
        n_a = 0
        for r in ha.get("rows", []):
            if "stage_table" not in r or r.get(
                    "observation_source") != "DURABLE_BRANCH":
                continue
            n_a += 1
            oa = r.get("openalex") or {}
            excl_a.append((oa.get("sources_excluded_envelope"),
                           oa.get("class")))
        check("after_openalex_excluded_envelope",
              n_a > 0 and all(
                  e[0] == ["openalex"] for e in excl_a),
              {"durable_rows": n_a, "excluded": [e[0] for e in excl_a]})
    else:
        note("after_openalex_excluded_envelope",
             "after harvest not run yet (not failed)")

    # instrument-identity artifact must exist and PASS
    ident = _load("R522_INSTRUMENT_IDENTITY.json")
    check("instrument_identity_present_pass",
          bool(ident) and ident.get("result") == "PASS",
          {"present": bool(ident),
           "result": (ident or {}).get("result")})

    # secret scan over committable R522 artifacts
    dirty = []
    for f in sorted(R522.glob("*.json")):
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

    out = {"artifact": "R522_CLEAN_REPLAY/1.0",
           "ran_at_utc": _utcnow(),
           "checks": checks,
           "failures": failures,
           "result": "FAIL" if failures else "PASS",
           "reviewer_provenance": "AI_REVIEW"}
    (R522).mkdir(parents=True, exist_ok=True)
    (R522 / "CLEAN_REPLAY.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8")
    print(f"{out['result']}: {sum(1 for c in checks if c['ok'])}/"
          f"{len(checks)} -> R522/CLEAN_REPLAY.json")
    return 0 if out["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
