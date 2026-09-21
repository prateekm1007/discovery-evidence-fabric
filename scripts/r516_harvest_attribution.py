#!/usr/bin/env python3
"""
R516 ATTRIBUTION HARVEST — offline derivation of the two-level
MECHANISM_SPACE decomposition from durable run bytes (auditor
directive R516B-E sections 5-6).

For one run directory (local path; durable-branch bytes are
materialized first via `git archive <ref> runs/<slug>`):

  INTERNAL (OBSERVED_IN_STAGE — the R516 Part A record):
    runtime_attribution.subphases + funnel + llm detail, read from
    envelope_MECHANISM_SPACE.json $.mechanism_space.runtime_attribution.

  OUTER (OBSERVED_IN_STAGE — the conductor's own measurement):
    stage_log MECHANISM_SPACE duration_monotonic_s, read from the
    work envelope (longest stage_log).

  WRAPPER (DERIVED — never inferred, never a scientific state):
    wrapper_protocol_overhead_s = outer - internal_total.
    Covers Candidate.run_stage envelope application (apply_to merge,
    deep-copy), before/after envelope hashing, and entry bookkeeping.
    A negative value is recorded AS-IS with a rounding note (never
    clamped to a cleaner zero — Art. XXIV).

  LEDGER JOIN (OFFLINE_DERIVED where matched, UNKNOWN where absent):
    model_routing/ledger.jsonl lines for this session at
    engine_stage MECHANISM_SPACE -> provider execution sum vs
    routing/fallback overhead (llm wall - provider sum). No match =
    UNKNOWN (typed, Art. XXV — never zero).

  FUNNEL ROW: shelled out to scripts/r515_discovery_yield.py
  (v1.1.0, frozen semantics; the R506 harvest precedent — shell out,
  never import).

Output: R516/MS_ATTRIBUTION_HARVEST.json (per-run rows + aggregate)
plus per-run YIELD_ROW files via the instrument.

Vocabulary discipline: every number carries exactly one of
OBSERVED_IN_STAGE / OFFLINE_DERIVED / UNKNOWN.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
INSTRUMENT = REPO / "scripts" / "r515_discovery_yield.py"


def _read_json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _envelopes(run_dir: Path):
    envs = {}
    for f in sorted(run_dir.glob("envelope_*.json")):
        d = _read_json(f)
        if isinstance(d, dict):
            envs[f.stem[len("envelope_"):]] = d
    return envs


def _work_envelope(envs):
    best, best_key = None, (-1,)
    for stage, doc in envs.items():
        log = doc.get("stage_log") or []
        key = (len(log),)
        if key > best_key:
            best, best_key = doc, key
    return best


def _stage_entry(doc, stage):
    for e in (doc or {}).get("stage_log") or []:
        if e.get("stage") == stage:
            return e
    return None


def measure_run(run_dir: Path, ledger_lines: list):
    """Full two-level measurement for one local run dir."""
    run_dir = Path(run_dir)
    slug = run_dir.name
    row = {"run_slug": slug}
    envs = _envelopes(run_dir)
    work = _work_envelope(envs)

    # ---- internal attribution (OBSERVED_IN_STAGE) ----
    ms_env = envs.get("MECHANISM_SPACE") or {}
    ms = ms_env.get("mechanism_space") or {}
    attr = ms.get("runtime_attribution")
    if isinstance(attr, dict):
        internal = {
            "class": "OBSERVED_IN_STAGE",
            "present": True,
            "attribution_version": attr.get("attribution_version"),
            "subphases": attr.get("subphases"),
            "total_s": attr.get("total_s"),
            "funnel": attr.get("funnel"),
            "llm": attr.get("llm"),
            "terminal_state": attr.get("terminal_state"),
            "evidence": "envelope_MECHANISM_SPACE.json"
                        "$.mechanism_space.runtime_attribution",
        }
        internal_total = attr.get("total_s")
    else:
        internal = {
            "class": "OBSERVED_IN_STAGE",
            "present": False,
            "note": ("no runtime_attribution on the mechanism-space "
                     "envelope — pre-instrument build or skipped stage; "
                     "unmeasured stays unmeasured (Art. XXV)"),
            "evidence": "envelope_MECHANISM_SPACE.json (absent key)",
        }
        internal_total = None

    # ---- outer stage wall (OBSERVED_IN_STAGE) ----
    entry = _stage_entry(work, "MECHANISM_SPACE") if work else None
    outer = (entry or {}).get("duration_monotonic_s")
    outer_rec = {
        "class": "OBSERVED_IN_STAGE",
        "duration_monotonic_s": outer,
        "entry_status": (entry or {}).get("status"),
        "evidence": "work-envelope stage_log[MECHANISM_SPACE]"
                    ".duration_monotonic_s",
    }

    # ---- wrapper derivation (DERIVED) ----
    if isinstance(outer, (int, float)) and \
            isinstance(internal_total, (int, float)):
        wrapper = round(outer - internal_total, 3)
        wclass = "OFFLINE_DERIVED"
        wnote = ("Candidate.run_stage envelope application "
                 "(apply_to merge, deep-copy), before/after envelope "
                 "hashing, entry bookkeeping. Recorded as measured; "
                 "a negative value would be kept as-is with a "
                 "rounding note, never clamped.")
    else:
        wrapper, wclass = None, "UNKNOWN"
        wnote = ("outer wall or internal total absent — the wrapper "
                 "cannot be derived (Art. XXV)")
    row["internal_attribution"] = internal
    row["outer_stage_wall"] = outer_rec
    row["wrapper_protocol_overhead"] = {
        "class": wclass,
        "wrapper_protocol_overhead_s": wrapper,
        "derivation": ("stage_log duration_monotonic_s minus "
                       "runtime_attribution.total_s"),
        "note": wnote,
    }

    # ---- funnel row via the frozen-behavior instrument ----
    r = subprocess.run(
        [sys.executable, str(INSTRUMENT), "--run-dir", str(run_dir)],
        capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        row["funnel_row"] = {
            "class": "UNKNOWN",
            "note": f"instrument error: {r.stderr[-200:]}"}
    else:
        try:
            payload = json.loads(r.stdout)
            frow = (payload.get("rows") or [{}])[0]
            row["funnel_row"] = {
                "class": "OBSERVED_IN_STAGE",
                "instrument": frow.get("instrument"),
                "lost_at": frow.get("lost_at"),
                "typed_drop_reason":
                    frow.get("typed_drop_reason"),
                "starvation_terminal":
                    frow.get("starvation_terminal"),
                "mechanisms_found": {
                    "reached": (frow.get("mechanisms_found") or {})
                    .get("reached")},
                "distinct": ((frow.get(
                    "candidates_generated_distinct") or {})
                    .get("count")),
            }
        except Exception as exc:  # noqa: BLE001
            row["funnel_row"] = {"class": "UNKNOWN",
                                 "note": f"row parse: {exc}"[:160]}

    # ---- ledger join (OFFLINE_DERIVED / UNKNOWN) ----
    sid = _session_of(run_dir)
    matched = [ln for ln in ledger_lines
               if ln.get("session_id") == sid
               and ln.get("engine_stage") == "MECHANISM_SPACE"] \
        if sid else []
    if matched:
        ok_lat = sum(float(ln.get("latency_ms") or 0)
                     for ln in matched if ln.get("ok")) / 1000.0
        all_lat = sum(float(ln.get("latency_ms") or 0)
                      for ln in matched) / 1000.0
        row["ledger_join"] = {
            "class": "OFFLINE_DERIVED",
            "n_lines": len(matched),
            "providers": sorted({ln.get("provider") for ln in
                                 matched}),
            "models": sorted({ln.get("model") for ln in matched}),
            "provider_execution_s": round(all_lat, 3),
            "ok_latency_s": round(ok_lat, 3),
            "failures": sorted({str(ln.get("failure_class"))
                                for ln in matched if not ln.get("ok")}),
            "note": ("per-hop latencies from the routing ledger; "
                     "routing/fallback overhead = llm wall minus "
                     "provider sum (computed by the analyst, never "
                     "written back in-stage)"),
        }
    else:
        row["ledger_join"] = {
            "class": "UNKNOWN",
            "note": ("no MECHANISM_SPACE ledger lines for this "
                     "session — unmeasured stays unmeasured "
                     "(Art. XXV)"),
        }
    return row


def _session_of(run_dir: Path):
    for name in ("run_manifest.json", "final_state.json"):
        d = _read_json(run_dir / name)
        if isinstance(d, dict) and d.get("session_id"):
            return d["session_id"]
    return None


def load_ledger(path: Path):
    lines = []
    try:
        for raw in path.read_text(encoding="utf-8",
                                  errors="replace").splitlines():
            raw = raw.strip()
            if not raw.startswith("{"):
                continue
            try:
                lines.append(json.loads(raw))
            except Exception:
                continue
    except Exception:
        pass
    return lines


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run-dir", required=True)
    ap.add_argument("--ledger", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    ledger = load_ledger(Path(args.ledger)) if args.ledger else []
    row = measure_run(Path(args.run_dir), ledger)
    payload = json.dumps(row, indent=1, sort_keys=True,
                         ensure_ascii=False)
    if args.out:
        outp = Path(args.out)
        outp.parent.mkdir(parents=True, exist_ok=True)
        outp.write_text(payload + "\n", encoding="utf-8")
        print(f"wrote {outp}")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
