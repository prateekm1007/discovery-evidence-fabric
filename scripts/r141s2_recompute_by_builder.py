#!/usr/bin/env python3
"""r141s2_recompute_by_builder — the EXECUTOR-side independent recompute
of the r141s1 accepted candidate's identity, run against the COMMITTED
raw run bytes (the repair of the b25d6788e close's omitted raw bytes).

Independence: this script re-derives the identity verdict from the
envelope bytes with its OWN record collection + span check, then runs
the engine's FIXED resolver (_resolve_binding_identity) as the
cross-check, and diffs the result against the committed acceptance row
(eval/r141s1_fresh_grounded_run/r141-fresh-04-...json). diff=0 is the
acceptance (the claims become recomputable from committed bytes —
Art. 1/18).
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

# the EXECUTOR-ORIGINAL raw bytes (the verifier's re-execution at the
# canonical eval/r141s1_fresh_grounded_run/ path is a DIFFERENT live
# run — its grounded candidate is on fresh-03; the executor's
# execution-of-record bytes, which this recompute re-derives, live here)
RUN_DIR = REPO / "eval" / "r141s1_fresh_grounded_run_executor_originals"
PID = "r141-fresh-04-chiller-fouling-capacity-droop"
TARGET = "cand:MS:DIRECT_TRANSFER:41c5f98f44ba"


def _collect_frozen(obj, seen, out):
    if isinstance(obj, dict):
        rid = obj.get("id")
        if rid and (obj.get("content_hash") or obj.get("title")):
            if rid not in seen:
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

    rec = json.loads((RUN_DIR / f"{PID}.json").read_text())
    acc = rec["acceptance"]
    row = [d for d in acc["detail"] if d.get("candidate_id") == TARGET][0]
    env = json.loads(
        (RUN_DIR / PID / "envelope_MECHANISM_SPACE.json").read_text())
    ms = env.get("mechanism_space") or {}
    cand = [c for c in ms.get("candidates") or []
            if c.get("candidate_id") == TARGET][0]
    binding = (cand["mechanism_support"] or {})["evidence_binding"]

    frozen, seen = [], set()
    freeze = json.loads((RUN_DIR / PID / "envelope_FREEZE.json").read_text())
    _collect_frozen(freeze, seen, frozen)

    # --- independent derivation (own span check) ---
    matches = [r for r in frozen if r["id"] == binding["evidence_id"]]
    n_exact = len(matches)
    rec0 = matches[0] if matches else {}
    # the SAME normalized-token form + field set the engine contract
    # uses (adapters.py _resolve_binding_identity rule 4) — normalized
    # whitespace/punctuation-insensitive token sequence match
    import re as _re
    blob = " ".join(str(rec0.get(k) or "") for k in
                    ("title", "abstract", "text", "content",
                     "summary", "_record_text"))
    span_norm = " ".join(_re.findall(r"[a-z0-9]+",
                                     binding["span"].lower()))
    blob_norm = " ".join(_re.findall(r"[a-z0-9]+", blob.lower()))
    span_in_record = bool(span_norm) and span_norm in blob_norm
    hash_equal = (rec0.get("content_hash") == binding["content_hash"])

    # --- engine resolver cross-check ---
    ok, reason, resolved = _resolve_binding_identity(binding, frozen)
    resolver_ok = bool(ok)

    independent = {
        "target": TARGET,
        "binding_evidence_id": binding["evidence_id"],
        "n_records_with_that_id": n_exact,
        "span": binding["span"],
        "span_in_record": span_in_record,
        "binding_hash": binding["content_hash"],
        "record_hash": rec0.get("content_hash"),
        "hash_equal": hash_equal,
        "resolver_ok": resolver_ok,
        "resolver_reason": reason,
        "n_frozen_records": len(frozen),
    }
    committed_claims = {
        "binding_evidence_id": row.get("binding_evidence_id"),
        "resolves": bool(row.get("resolves")),
        "admitted": bool(row.get("admitted")),
        "lifecycle": row.get("lifecycle"),
    }
    diff = []
    if independent["binding_evidence_id"] != committed_claims[
            "binding_evidence_id"]:
        diff.append("evidence_id")
    if not (independent["resolver_ok"] == committed_claims["resolves"]
            == committed_claims["admitted"]):
        diff.append("verdict")
    if not (independent["span_in_record"] and independent["hash_equal"]
            and independent["n_records_with_that_id"] == 1):
        diff.append("identity-triplet")

    out = {
        "record": "R141S2_RECOMPUTE_BY_BUILDER/1.0.0",
        "work_id": "r141s2-verify-fresh-run (executor-side repair)",
        "provenance_note": ("the source bytes are the executor's "
                            "execution-of-record raw run bytes (the "
                            "b25d6788e omission), preserved at "
                            "eval/r141s1_fresh_grounded_run_executor_"
                            "originals/ after the rebase — the "
                            "verifier's canonical re-execution at the "
                            "canonical path crosses the same bar on "
                            "fresh-03 (live retrieval variance, typed "
                            "by the verifier); BOTH sets are committed"),
        "session": "builder-r141s1",
        "at": "2026-11-23 (sandbox clock)",
        "source_bytes": [
            f"eval/r141s1_fresh_grounded_run_executor_originals/{PID}.json",
            f"eval/r141s1_fresh_grounded_run_executor_originals/{PID}/envelope_MECHANISM_SPACE.json",
            f"eval/r141s1_fresh_grounded_run_executor_originals/{PID}/envelope_FREEZE.json"],
        "independent_derivation": independent,
        "committed_acceptance_row": committed_claims,
        "diff": diff,
        "diff_zero": diff == [],
        "note": ("run 0 bad admissions re-checked across all 4 "
                 "committed per-problem records: "
                 + json.dumps([json.loads((RUN_DIR / f"{p}.json")
                                .read_text())["acceptance"]
                               ["n_bad_admissions"]
                               for p in ("r141-fresh-01-desal-membrane-fouling",
                                         "r141-fresh-02-wind-blade-leading-edge-erosion",
                                         "r141-fresh-03-cathodic-protection-depletion",
                                         PID)])),
    }
    (REPO / "eval" / "r141s2_recompute_by_builder.json").write_text(
        json.dumps(out, indent=1) + "\n")
    print(json.dumps({"diff": diff, "diff_zero": diff == [],
                      "independent": independent}, indent=1))
    return 0 if diff == [] else 1


if __name__ == "__main__":
    raise SystemExit(main())
