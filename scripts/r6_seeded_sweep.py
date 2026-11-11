#!/usr/bin/env python3
"""r6_seeded_sweep.py — the seeded-defect catch vs false-kill sweep on
OWNER-HELD specimens (owner directive 2026-11-11, item 2).

Why this file replaces scripts/r6_seeded_defects.py:
  The R6 circular sweep seeded three hand-written defects matched to the
  gate's own vocabulary and then reported the gate catching them. The
  instrument and its fixtures came from the same hand (Art. XIX: no
  optimizing the gate; Art. XXV: unknown stays unknown; Art. LXIV: retire,
  do not accumulate). That sweep is RETIRED, not repaired.

This runner consumes OWNER-HELD specimens:
  seeded_specimens_v1.json at an owner-held path, integrity-verified
  against the owner-declared selection_sha256 (the directive states the
  prefix c0aeb715; the full hash is supplied at run time — the code
  never invents it).

NEVER-READ RULE (binding): any field whose name suggests private scoring
  data — *key*, *rubric*, *answer*, *expected*, *gold*, *labels*,
  *verdict_truthy* — is never accessed, never printed, never committed,
  never used to select anything beyond the aggregate tally below. The
  per-class report shows catch/false-kill AGGREGATES only; individual
  rows are written only to gitignored ENGINE_RUNS scratch, never to
  tracked outputs, never pasted into the report.

Fail-closed: missing file, hash mismatch, unparseable spec, unknown
  prefix mode → typed blocker, exit 2, no scores emitted.
Deterministic: the gate functions are LLM-free; no network calls.

Classification used for aggregates (defect_class vocabulary is the
owner's, unfiltered): classes in CLEAN_CLASSES count as
negative controls (false-kill metric); everything else with a
defect_class counts as seeded (catch metric); absent defect_class →
NOT_MEASURED for both metrics (never fabricated).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

DECLARED_PREFIX = "c0aeb715"          # owner-declared, public in directive
CLEAN_CLASSES = {"control", "clean", "legit", "legitimate",
                 "legitimate_intervention", "none", "unknown", ""}
#: fields the runner will never access, print, or write
FORBIDDEN_FIELD_TOKENS = ("key", "rubric", "answer", "expected",
                          "gold", "label", "truthy", "verdict")

GATE_CHECKS = ("not_an_intervention", "function_removal",
               "restates_constraint", "anchor_domain")


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _specimen_text(s):
    for k in ("intervention", "candidate", "candidate_text", "text"):
        v = s.get(k)
        if isinstance(v, str) and v.strip():
            return v
    return None


def _specimen_class(s):
    for k in ("defect_class", "class", "defect"):
        v = s.get(k)
        if v is not None:
            return str(v).strip().lower()
    return None


def _load_specimens(path: Path):
    raw = path.read_bytes()
    sha = _sha256_bytes(raw)
    try:
        d = json.loads(raw.decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        return None, sha, f"specimens file is not valid JSON ({exc})"
    specs = None
    if isinstance(d, list):
        specs = d
    elif isinstance(d, dict):
        for k in ("specimens", "specimens_v1", "items", "candidates"):
            if isinstance(d.get(k), list):
                specs = d[k]
                break
    if specs is None:
        return None, sha, ("specimens file parsed but no known top-level "
                           "list found (specimens|items|candidates); "
                           "refusing to guess a schema")
    return specs, sha, None


def run_sweep(specimens_path: Path, expected_full: str | None,
              prefix_mode: bool, synthetic_fixture: bool) -> dict:
    blocker = None
    if not specimens_path.is_file():
        blocker = f"specimens file absent at owner-held path: {specimens_path}"
        return {"outcome": "BLOCKED_SPECIMENS_ABSENT",
                "detail": blocker,
                "catch": "NOT_MEASURED", "false_kill": "NOT_MEASURED"}

    specs, sha, load_err = _load_specimens(specimens_path)
    if load_err:
        return {"outcome": "BLOCKED_SPECIMENS_UNREADABLE",
                "detail": load_err, "specimens_sha256": sha,
                "catch": "NOT_MEASURED", "false_kill": "NOT_MEASURED"}

    # integrity check against the owner-declared selection
    integrity = {"specimens_sha256": sha}
    if expected_full:
        full = expected_full.strip().lower()
        ok = (sha == full) if not prefix_mode else sha.startswith(full)
        integrity.update({"expected_mode": ("prefix" if prefix_mode else "full"),
                          "expected_selection_sha256": full,
                          "match": bool(ok)})
        if not ok:
            return {"outcome": "BLOCKED_SELECTION_SHA_MISMATCH",
                    "integrity": integrity,
                    "catch": "NOT_MEASURED",
                    "false_kill": "NOT_MEASURED",
                    "detail": ("specimens bytes do not match the "
                               "owner-declared selection_sha256; refusing "
                               "to score a different selection")}
    elif not synthetic_fixture:
        return {"outcome": "BLOCKED_NO_EXPECTED_HASH",
                "integrity": integrity,
                "catch": "NOT_MEASURED", "false_kill": "NOT_MEASURED",
                "detail": ("--expected-selection-sha256 (full or declared "
                           "prefix) is required outside a synthetic "
                           "fixture run; the runner never substitutes a "
                           "hash it recalled from memory")}
    else:
        integrity["SYNTHETIC_FIXTURE"] = True

    # ---- scoring -----------------------------------------------------
    from discovery_fabric.engine.intervention_gate import (  # noqa: E402
        not_an_intervention_check, function_removal_check,
        restates_constraint_check, anchor_domain_check)

    probs = {}
    try:
        probs = {p["problem_id"]: p for p in json.loads(
            (REPO / "eval" / "problems.json").read_text(
                encoding="utf-8"))["problems"]}
    except Exception:  # noqa: BLE001 — context optional; fail-open scoped
        pass

    rows = []
    per_class = {}
    n_kills_total = 0
    for i, s in enumerate(specs):
        if not isinstance(s, dict):
            rows.append({"row": i, "outcome": "SKIP_UNPARSEABLE"})
            continue
        cls = _specimen_class(s)
        text = _specimen_text(s)
        if not text:
            rows.append({"row": i, "outcome": "SKIP_NO_CANDIDATE_TEXT",
                         "defect_class": cls})
            continue
        v = {}
        v["not_an_intervention"] = bool(
            not_an_intervention_check(text).get("rejected"))
        pid = s.get("problem_id")
        p = probs.get(pid) if pid else None
        constraint = (p or {}).get("constraint") or s.get("constraint") or ""
        if constraint:
            v["function_removal"] = bool(
                function_removal_check(constraint, text).get("killed"))
            v["restates_constraint"] = bool(
                restates_constraint_check(constraint, text,
                                          s.get("mechanism") or
                                          s.get("rationale")).get("killed"))
        else:
            v["function_removal"] = None  # not measured, never guessed
            v["restates_constraint"] = None
        try:
            v["anchor_domain"] = bool(
                anchor_domain_check(p or {}, s).get("killed"))
        except Exception:  # noqa: BLE001 — gate shape varies; measured, not fatal
            v["anchor_domain"] = None
        killed_by = [k for k, val in v.items() if val is True]
        killed = bool(killed_by)
        n_kills_total += int(killed)
        ckey = cls if cls is not None else "UNLABELED"
        a = per_class.setdefault(ckey, {"n": 0, "killed": 0})
        a["n"] += 1
        a["killed"] += int(killed)
        rows.append({"row": i, "defect_class": ckey, "killed": killed,
                     "killed_by": killed_by,
                     "checks_measured": {k: (x is not None)
                                         for k, x in v.items()}})

    seeded = {"n": 0, "killed": 0}
    control = {"n": 0, "killed": 0}
    for ckey, a in per_class.items():
        if ckey == "UNLABELED":
            continue
        if ckey in CLEAN_CLASSES:
            control["n"] += a["n"]
            control["killed"] += a["killed"]
        else:
            seeded["n"] += a["n"]
            seeded["killed"] += a["killed"]

    def _rate(b):
        return round(b["killed"] / b["n"], 3) if b["n"] else None

    per_class_out = {c: {"n": a["n"], "killed": a["killed"],
                         "kill_rate": _rate(a)}
                     for c, a in sorted(per_class.items())}

    catch = ("NOT_MEASURED" if seeded["n"] == 0 else
             {"n_seeded": seeded["n"], "n_caught": seeded["killed"],
              "catch_rate": _rate(seeded)})
    false_kill = ("NOT_MEASURED" if control["n"] == 0 else
                  {"n_controls": control["n"],
                   "n_false_kills": control["killed"],
                   "false_kill_rate": _rate(control)})

    return {"outcome": "SCORED",
            "integrity": integrity,
            "n_specimens": len(specs),
            "n_killed": n_kills_total,
            "per_class_aggregates": per_class_out,
            "catch": catch,
            "false_kill": false_kill,
            "gate_checks_applied": list(GATE_CHECKS),
            "rows_scratch_note": ("per-specimen rows are written only to "
                                  "gitignored ENGINE_RUNS scratch"),
            "_rows": rows}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--specimens",
                    default=None,
                    help="owner-held path to seeded_specimens_v1.json "
                         "(or env SEEDED_SPECIMENS_PATH)")
    ap.add_argument("--expected-selection-sha256", default=None,
                    help="full 64-hex sha256 of the specimens file, or "
                         "with --prefix-match the owner-declared prefix "
                         "(directive: c0aeb715)")
    ap.add_argument("--prefix-match", action="store_true")
    ap.add_argument("--synthetic-fixture", action="store_true",
                    help="dev/test only; marks output SYNTHETIC_FIXTURE")
    ap.add_argument("--output-dir", default=str(REPO / "ENGINE_RUNS"))
    args = ap.parse_args()

    import os
    sp = args.specimens or os.environ.get("SEEDED_SPECIMENS_PATH")
    if not sp:
        print("[sweep] BLOCKED_SPECIMENS_ABSENT: pass --specimens or set "
              "SEEDED_SPECIMENS_PATH to the owner-held path; the file "
              "is never supplied by this repository", flush=True)
        return 2

    prefix = args.expected_selection_sha256
    if prefix_mode_check := (args.prefix_match and prefix
                             and not prefix.lower().startswith(
                                 DECLARED_PREFIX)):
        print(f"[sweep] BLOCKED_BAD_PREFIX: prefix must start with the "
              f"owner-declared {DECLARED_PREFIX}; refusing", flush=True)
        return 2

    res = run_sweep(Path(sp), prefix, args.prefix_match,
                    args.synthetic_fixture)
    out_dir = Path(args.output_dir)
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"[sweep] BLOCKED_OUTPUT_DIR: {exc}", flush=True)
        return 2

    rows = res.pop("_rows", None)
    scratch = out_dir / "r6_seeded_sweep_rows.jsonl"
    if rows is not None:
        with scratch.open("w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r, default=str) + "\n")

    out_json = out_dir / "r6_seeded_sweep.json"
    out_json.write_text(json.dumps(res, indent=1, default=str) + "\n",
                        encoding="utf-8")

    lines = ["# R6 seeded-defect catch vs false kills (owner-held specimens)",
             "", f"- outcome: {res.get('outcome')}",
             f"- integrity: {json.dumps(res.get('integrity'), default=str)}",
             f"- specimens scored: {res.get('n_specimens')} | kills: "
             f"{res.get('n_killed')}",
             f"- catch: {json.dumps(res.get('catch'), default=str)}",
             f"- false-kill: {json.dumps(res.get('false_kill'), default=str)}",
             "", "## per-class aggregates (aggregates only)"]
    for c, a in (res.get("per_class_aggregates") or {}).items():
        lines.append(f"- {c}: n={a['n']} killed={a['killed']} "
                     f"kill_rate={a['kill_rate']}")
    (out_dir / "r6_seeded_sweep.md").write_text("\n".join(lines) + "\n",
                                                encoding="utf-8")
    print("\n".join(lines), flush=True)
    print(f"[sweep] -> {out_json.name}, r6_seeded_sweep.md, "
          f"{scratch.name} (gitignored scratch)", flush=True)
    if str(res.get("outcome", "")).startswith("BLOCKED"):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
