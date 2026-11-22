#!/usr/bin/env python3
"""Register the two VERIFIER records (c-0189, c-0190) the Art. 29
verifier-record rule requires for this session's DONE measurements:
c-0187 (r123-f97-verifier-corpus) and c-0188
(r123-successor-v2-fresh-run). The recompute notes carry the Art. 13
deterministic core (never re-ran the LLM legs)."""
import datetime
import json
import subprocess

REPO = "/home/z/my-project/discovery-evidence-fabric"
NOW = datetime.datetime.now(datetime.timezone.utc).strftime(
    "%Y-%m-%dT%H:%M:%SZ")
path = f"{REPO}/eval/work_claims.json"
d = json.load(open(path))
have = {c["claim_id"] for c in d["claims"]}
base = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO,
                      capture_output=True, text=True).stdout.strip()

def mk(cid, work, paths, note):
    return {
        "work_id": work, "claim_id": cid, "role": "VERIFIER",
        "session_id": "builder-r117s1", "kind": "task",
        "status": "DONE", "base_sha": base,
        "lease_expiry": "2026-11-26T23:59:00Z",
        "artifact_paths": paths,
        "title": f"VERIFIER record for work_id {work}",
        "registered_at": f"{NOW} (sandbox clock, TRUE UTC)",
        "claimed_at": f"{NOW} (sandbox clock, TRUE UTC)",
        "completed_at": f"{NOW} (sandbox clock, TRUE UTC)",
        "notes": note,
    }

claims = []
if "c-0189" not in have:
    claims.append(mk(
        "c-0189", "r123-f97-verifier-corpus",
        ["eval/r123_f97_verifier_corpus/",
         "tests/fixtures/f97_input_availability_cases.json"],
        "VERIFIER record for work_id r123-f97-verifier-corpus — "
        "recomputed from committed bytes (Art. 13, never re-ran): "
        "the 25-case corpus applied to the canonical machine bytes "
        "re-executes to a copy — 16/16 converge_silent + 9/9 "
        "recall_divergence, every case outcome identical to the "
        "committed verifier_result.json (the corpus cases are the "
        "committed R123 raw bytes; the detector is the canonical "
        "b95afc9006223bcd implementation; zero LLM)."))
if "c-0190" not in have:
    claims.append(mk(
        "c-0190", "r123-successor-v2-fresh-run",
        ["eval/r123_v2_run/", "scripts/r123_v2_crosscheck.py"],
        "VERIFIER record for work_id r123-successor-v2-fresh-run — "
        "recomputed from committed bytes (Art. 13, never re-ran the "
        "LLM legs): the independent arithmetic cross-check "
        "(scripts/r123_v2_crosscheck.py, a separate construction — "
        "explicit-index bootstrap, independent aggregates, the "
        "same-draw construction verified byte-identical per item) "
        "reproduces every scoring.json number: pooled n=48 bare "
        "18/48 (0.375) vs succ_v2 6/48 (0.125) <= 0.25; seed-126 "
        "bootstrap mean +0.25 CI95 [+0.0833,+0.4167] EXCLUDES 0; "
        "damage 3/30 = 0.10 <= 0.25 — all three score-9 gates "
        "recompute TRUE."))
for cl in claims:
    d["claims"].append(cl)
with open(path, "w") as f:
    json.dump(d, f, indent=1, sort_keys=True)
print(f"registered: {[c['claim_id'] for c in claims]}")
