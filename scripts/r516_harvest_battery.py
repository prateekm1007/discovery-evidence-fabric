#!/usr/bin/env python3
"""
R516 BATTERY HARVEST — from the durable branch to the measurement
records (auditor directive R516B-E sections 5-6, 11, 14).

Reads (never writes) origin/runtime-state-hf:
  1. fetch the branch;
  2. map R516 session ids -> run slugs via run_manifest/final_state;
  3. per run: v1.1.0 funnel row (YIELD_ROW files) + two-level
     MECHANISM_SPACE attribution + routing-ledger join
     (MS_ATTRIBUTION_HARVEST.json);
  4. write the redacted custody mirror.

Run beats are OBSERVED (durable bytes), derivations OFFLINE_DERIVED,
gaps UNKNOWN. No tuning, no rewording, no selection: every scored
submission is harvested, zeros included.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO))

SESSIONS = REPO / os.environ.get("R516_SESSIONS",
                                 "R516/BATTERY_SESSIONS.json")
MANIFEST = REPO / "R516" / "BATTERY_PROBLEMS.json"
REDACTED = REPO / os.environ.get(
    "R516_REDACTED", "R516/BATTERY_SESSIONS_REDACTED.json")
OUT_HARVEST = REPO / os.environ.get(
    "R516_OUT_HARVEST", "R516/MS_ATTRIBUTION_HARVEST.json")
YIELD_ROW_PREFIX = os.environ.get("R516_YIELD_ROW_PREFIX", "YIELD_ROW_")
INSTRUMENT_ID = "r506_discovery_yield"
INSTRUMENT_VERSION = "1.1.0"

import r516_harvest_attribution as hv  # noqa: E402


def _git(*args, **kwargs):
    return subprocess.run(["git", *args], capture_output=True,
                          timeout=kwargs.get("timeout", 120),
                          cwd=str(REPO))


def _show(ref_path):
    r = _git("show", ref_path, timeout=120)
    return r.stdout if r.returncode == 0 else None


def main() -> int:
    branch = "origin/runtime-state-hf"
    print("fetching durable branch ...")
    fr = _git("fetch", "origin", "runtime-state-hf", timeout=300)
    print("fetch rc=", fr.returncode)
    sessions = json.loads(SESSIONS.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    by_idx = {p["selection_index"]: p for p in manifest["problems"]}

    # map session -> slug from durable bytes
    ls = _git("ls-tree", "--name-only", f"{branch}:runs", timeout=120)
    slugs = sorted(ls.stdout.decode("utf-8", "replace").split())
    print(f"{len(slugs)} run dirs on the durable branch")
    slug_of = {}
    for slug in slugs:
        for name in ("run_manifest.json", "final_state.json"):
            raw = _show(f"{branch}:runs/{slug}/{name}")
            if not raw:
                continue
            try:
                d = json.loads(raw.decode("utf-8"))
            except Exception:
                continue
            if d.get("session_id"):
                slug_of[d["session_id"]] = slug
                break
    print(f"mapped {len(slug_of)} sessions to slugs")

    # materialize the routing ledger once
    ledger_raw = _show(f"{branch}:model_routing/ledger.jsonl")
    ledger_lines = []
    if ledger_raw:
        for line in ledger_raw.decode("utf-8",
                                      errors="replace").splitlines():
            line = line.strip()
            if line.startswith("{"):
                try:
                    ledger_lines.append(json.loads(line))
                except Exception:
                    continue
    print(f"ledger lines: {len(ledger_lines)}")

    rows = []
    with tempfile.TemporaryDirectory() as td:
        for s in sessions["submissions"]:
            idx, sid = s["problem_index"], s.get("session_id")
            p = by_idx[idx]
            slug = slug_of.get(sid)
            if not slug:
                rows.append({
                    "problem_index": idx,
                    "source_id": p["source_id"],
                    "declared_family": p["declared_family"],
                    "session_id": sid,
                    "harvest": "NOT_YET_ON_DURABLE_BRANCH_OR_UNKNOWN"})
                print(f"#{idx} {sid}: not on durable branch yet")
                continue
            # materialize the run dir (instrument --run-dir
            # expects <root>/runs/<slug> layout)
            dest = Path(td) / "runs" / slug
            dest.mkdir(parents=True)
            lr = _git("ls-tree", "--name-only",
                      f"{branch}:runs/{slug}", timeout=120)
            for name in lr.stdout.decode("utf-8",
                                         errors="replace").split():
                if "/" in name:
                    continue
                raw = _show(f"{branch}:runs/{slug}/{name}")
                if raw:
                    (dest / name).write_bytes(raw)
            row = hv.measure_run(dest, ledger_lines)
            row.update({
                "problem_index": idx,
                "source_id": p["source_id"],
                "declared_family": p["declared_family"],
                "session_id": sid,
                "run_slug": slug,
            })
            # canonical YIELD_ROW bytes: the instrument's OWN --out
            # serialization (R506 pattern). Determinism self-check:
            # the --out bytes must equal what measure_run read (same
            # input bytes -> same output bytes, Art. LXII); a mismatch
            # is recorded loudly, never papered over.
            out = REPO / "R516" / \
                f"{YIELD_ROW_PREFIX}{idx}_{slug}.json"
            r2 = subprocess.run(
                [sys.executable, str(hv.INSTRUMENT), "--run-dir",
                 str(dest), "--out", str(out)],
                capture_output=True, text=True, timeout=300)
            if r2.returncode == 0:
                frow2 = json.loads(out.read_text(
                    encoding="utf-8"))["rows"][0]
                if frow2 != row.get("funnel_row"):
                    row["determinism_check"] = {
                        "status": "MISMATCH",
                        "note": ("instrument --out bytes differ from "
                                 "harvest-time read on identical input "
                                 "bytes (Art. LXII violation)"),
                    }
                else:
                    row["determinism_check"] = {"status": "MATCH"}
            else:
                row["determinism_check"] = {
                    "status": "INSTRUMENT_OUT_ERROR",
                    "note": r2.stderr[-200:]}
            row["row_file"] = str(out.relative_to(REPO))
            rows.append(row)
            ms = ((row.get("internal_attribution") or {}).get("funnel")
                  or {})
            frow = row.get("funnel_row") or {}
            print(f"#{idx} {slug}: lost_at={frow.get('lost_at')} "
                  f"ms_terminal={ms.get('terminal_reason') if isinstance(ms, dict) else ms}")

    harvest = {
        "artifact_type": "R516_MS_ATTRIBUTION_HARVEST",
        "battery": "R516-mechanism-attribution",
        "instrument": f"{INSTRUMENT_ID}/{INSTRUMENT_VERSION}",
        "instrument_script": "scripts/r515_discovery_yield.py",
        "manifest_sha256": hashlib.sha256(
            MANIFEST.read_bytes()).hexdigest(),
        "harvested_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                          time.gmtime()),
        "rows": rows,
        "reviewer_provenance": "AI_REVIEW",
    }
    OUT_HARVEST.write_text(json.dumps(harvest, indent=1, sort_keys=True,
                                      ensure_ascii=False) + "\n",
                           encoding="utf-8")
    print(f"wrote {OUT_HARVEST} ({len(rows)} rows)")

    redacted = {
        "battery": sessions.get("battery"),
        "manifest_sha256": sessions.get("manifest_sha256"),
        "note": ("REDACTED custody: session ids only; owner "
                 "capabilities are LOCAL-ONLY and never committed "
                 "(BS-021)"),
        "submissions": [
            {"problem_index": s.get("problem_index"),
             "source_id": s.get("source_id"),
             "declared_family": s.get("declared_family"),
             "session_id": s.get("session_id"),
             "submitted_at_utc": s.get("submitted_at_utc")}
            for s in sessions.get("submissions", [])]}
    REDACTED.write_text(json.dumps(redacted, indent=1),
                        encoding="utf-8")
    print(f"wrote {REDACTED}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
