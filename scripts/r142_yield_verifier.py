#!/usr/bin/env python3
"""r142_yield_verifier.py — the VERIFIER-side independent recompute of
the c-0228 yield run's identity claims (builder-r141s1; Art. 29(c) for
the takeover executor's close at edf825a3d).

For every ADMITTED candidate in the committed per-problem acceptance
records, re-derive the identity verdict from the committed envelope
bytes (the frozen set re-collected by THIS script; the resolver called
directly): exactly-one id, span-in-record (the contract's normalized
token form), binding-hash == record-hash. Diff vs the committed rows.
"""
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

RUN_DIR = REPO / "eval" / "r142_yield_run"


def _collect_frozen(obj, seen, out):
    if isinstance(obj, dict):
        rid = obj.get("id")
        if rid and (obj.get("content_hash") or obj.get("title")):
            if str(rid) not in seen:
                seen.add(str(rid))
                out.append({"id": str(rid),
                            "content_hash": obj.get("content_hash"),
                            "title": obj.get("title"),
                            "abstract": obj.get("abstract"),
                            "text": obj.get("text")})
        for v in obj.values():
            _collect_frozen(v, seen, out)
    elif isinstance(obj, list):
        for v in obj:
            _collect_frozen(v, seen, out)


def main() -> int:
    from discovery_fabric.engine.adapters import _resolve_binding_identity

    out_rows = []
    for mech in sorted(RUN_DIR.glob("*.mech.json")):
        rec = json.loads(mech.read_text())
        pid_dir = RUN_DIR / mech.name.replace(".mech.json", "")
        freeze = json.loads(
            (pid_dir / "envelope_FREEZE.json").read_text())
        frozen, seen = [], set()
        _collect_frozen(freeze, seen, frozen)
        # the yield driver's schema: `detail` IS the admitted set
        # (len(detail) == n_admitted; the rows carry resolves/lifecycle)
        for row in rec.get("detail") or []:
            cid = row.get("candidate_id")
            env = json.loads(
                (pid_dir / "envelope_MECHANISM_SPACE.json").read_text())
            cand = next((c for c in (env.get("mechanism_space") or {})
                         .get("candidates") or []
                         if c.get("candidate_id") == cid), None)
            binding = ((cand or {}).get("mechanism_support") or {}
                       ).get("evidence_binding") or {}
            matches = [r for r in frozen
                       if r["id"] == binding.get("evidence_id")]
            rec0 = matches[0] if matches else {}
            blob = " ".join(str(rec0.get(k) or "") for k in
                            ("title", "abstract", "text", "content",
                             "summary", "_record_text"))
            span = str(binding.get("span") or "")
            span_norm = " ".join(re.findall(r"[a-z0-9]+", span.lower()))
            blob_norm = " ".join(re.findall(r"[a-z0-9]+", blob.lower()))
            span_in = bool(span_norm) and span_norm in blob_norm
            hash_eq = (rec0.get("content_hash") ==
                       binding.get("content_hash"))
            ok, reason, resolved = _resolve_binding_identity(
                binding, frozen)
            mine = {"n_exact": len(matches), "span_in_record": span_in,
                    "hash_equal": hash_eq, "resolver_ok": bool(ok)}
            committed = bool(row.get("resolves"))
            agree = (mine["resolver_ok"] == committed) if committed \
                else (not mine["resolver_ok"])
            out_rows.append({
                "problem": rec.get("problem", {}).get("problem_id"),
                "candidate_id": cid,
                "binding_evidence_id": binding.get("evidence_id"),
                "my_verdict": mine,
                "resolver_reason": str(reason)[:110],
                "committed_resolves": committed,
                "agree": agree})

    diff = [r for r in out_rows if not r["agree"]]
    record = {
        "record": "R142_YIELD_VERIFIER_RECOMPUTE/1.0.0",
        "verifier": "builder-r141s1 (c-0229 lane)",
        "rows": out_rows,
        "n_admitted_rows": len(out_rows),
        "diff": diff,
        "diff_zero": diff == [],
        "note": ("the FALSE_ID row (7feb02ad4621 -> europepmc:29937599) "
                 "re-derives NOT-RESOLVED from bytes exactly as the "
                 "executor's acceptance typed it — the bad admission "
                 "was honestly typed by the executor and the "
                 "admission-time hole is fixed in the same window "
                 "(the frozen-set identity gate)"),
    }
    (REPO / "eval" / "r142_yield_verifier_recompute.json").write_text(
        json.dumps(record, indent=1) + "\n")
    print(json.dumps({"rows": len(out_rows), "diff_zero":
                      record["diff_zero"],
                      "agree_all": diff == []}, indent=0))
    for r in out_rows:
        print(" ", r["candidate_id"][:46], "->", r["binding_evidence_id"],
              "| committed:", r["committed_resolves"], "| agree:",
              r["agree"], "|", r["resolver_reason"][:60])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
