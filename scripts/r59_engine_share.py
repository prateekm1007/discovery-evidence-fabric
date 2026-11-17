#!/usr/bin/env python3
"""r59_engine_share.py — the Article 27 ENGINE-LINE SHARE instrument
(epistemic constitution v3.2.0 CI addition for F63; ratification claim
c-0080).

THE CONSTITUTION CLAUSE (Art. 27, v3.2.0): "ENGINE-LINE SHARE: every
round record declares its measured engine-line share over the round's
declared diff range (diff_base_sha..diff_head_sha); the CI recompute
must MATCH the declared figure; a share <30% requires a typed
below-rule disclosure (retirement/precision rounds) — capability logic
lives in discovery_fabric/engine/, not scripts/."

GROUND TRUTH (F63): rounds shipped 0%/6.6%/24.8% engine lines with the
capability logic script-housed, disclosed only under audit pressure.
The owner rule (auditor Art. 5 v1.3.0): >=30% of changed lines per
round live in engine code; sub-30% is a FINDING that must be declared,
never hidden.

Method: `git diff --numstat <base>..<head>` — the changed-line surface
of the declared range; engine lines = paths under
discovery_fabric/engine/; shares computed on BOTH insertions and
changed (insertions+deletions), matching the R55 declaration
convention ("7.7% insertions / 5.5% changed").

Zero LLM, zero network, deterministic from committed bytes.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ENGINE_PREFIX = "discovery_fabric/engine/"
REPORT = REPO / "eval" / "r59_engine_share.json"


def compute_share(base: str, head: str) -> dict:
    out = subprocess.run(
        ["git", "diff", "--numstat", f"{base}..{head}"],
        cwd=str(REPO), capture_output=True, text=True, timeout=120)
    if out.returncode != 0:
        raise RuntimeError(
            f"git diff --numstat failed (typed): {out.stderr[:300]}")
    engine_ins = engine_del = total_ins = total_del = 0
    for ln in out.stdout.splitlines():
        if not ln.strip():
            continue
        ins, dele, path = ln.split("\t", 2)
        # binary files record "-" — excluded (no line semantics)
        i = int(ins) if ins.isdigit() else 0
        dl = int(dele) if dele.isdigit() else 0
        total_ins += i
        total_del += dl
        if path.startswith(ENGINE_PREFIX):
            engine_ins += i
            engine_del += dl
    total_changed = total_ins + total_del
    engine_changed = engine_ins + engine_del
    return {
        "diff_range": f"{base}..{head}",
        "engine_insertions": engine_ins,
        "total_insertions": total_ins,
        "engine_deletions": engine_del,
        "total_deletions": total_del,
        "engine_changed": engine_changed,
        "total_changed": total_changed,
        "share_insertions_pct": round(
            100.0 * engine_ins / total_ins, 1) if total_ins else None,
        "share_changed_pct": round(
            100.0 * engine_changed / total_changed, 1)
            if total_changed else None,
    }


def verify_record(record_path: Path) -> dict:
    rec = json.loads(record_path.read_text(encoding="utf-8"))
    art = rec.get("art27_capability_budget") or {}
    decl = art.get("engine_share_declaration")
    if not decl:
        return {"record": record_path.name, "verdict":
                "NO_DECLARATION (rounds >= R58 must declare — the "
                "v3.2.0 Art. 27 clause)"}
    computed = compute_share(decl["diff_base_sha"], decl["diff_head_sha"])
    checks = []
    for declared_key, computed_key in (
            ("engine_insertions", "engine_insertions"),
            ("total_insertions", "total_insertions"),
            ("engine_changed", "engine_changed"),
            ("total_changed", "total_changed"),
            ("share_insertions_pct", "share_insertions_pct"),
            ("share_changed_pct", "share_changed_pct")):
        if declared_key in decl:
            ok = decl[declared_key] == computed[computed_key]
            checks.append({"field": declared_key,
                           "declared": decl[declared_key],
                           "computed": computed[computed_key],
                           "match": ok})
    mismatch = [c for c in checks if not c["match"]]
    share = computed["share_changed_pct"]
    below = share is not None and share < 30.0
    disclosure = art.get("below_rule_disclosure") or \
        decl.get("below_rule_disclosure")
    verdict = "MATCH"
    if mismatch:
        verdict = "DECLARATION_MISMATCH"
    elif below and not disclosure:
        verdict = "BELOW_RULE_WITHOUT_DISCLOSURE"
    return {"record": record_path.name, "verdict": verdict,
            "computed": computed, "checks": checks,
            "below_rule": below,
            "disclosure_present": bool(disclosure)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--head", required=True)
    ap.add_argument("--verify", type=Path, default=None,
                    help="also verify a round record's declared share")
    args = ap.parse_args()
    try:
        share = compute_share(args.base, args.head)
    except Exception as e:  # noqa: BLE001 - typed instrument failure
        print(json.dumps({"record": "R59_ENGINE_SHARE/1.0.0",
                          "verdict": "INSTRUMENT_FAILURE",
                          "error": str(e)}))
        return 2
    report = {"record": "R59_ENGINE_SHARE/1.0.0", "share": share,
              "rule": ">=30% engine lines per round (auditor Art. 5 "
                      "v1.3.0 / epistemic Art. 27 v3.2.0); sub-30% "
                      "requires a typed below-rule disclosure"}
    if args.verify:
        report["verification"] = verify_record(args.verify)
    REPORT.write_text(json.dumps(report, indent=1, ensure_ascii=False)
                      + "\n", encoding="utf-8")
    print(json.dumps(report, indent=1))
    v = report.get("verification", {})
    return 1 if v.get("verdict") not in ("MATCH", None) else 0


if __name__ == "__main__":
    raise SystemExit(main())
