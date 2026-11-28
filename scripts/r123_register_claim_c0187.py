#!/usr/bin/env python3
"""Register claim c-0187 (r123-f97-verifier-corpus) OPEN."""
import datetime
import json
import subprocess

REPO = "/home/z/my-project/discovery-evidence-fabric"
NOW = datetime.datetime.now(datetime.timezone.utc).strftime(
    "%Y-%m-%dT%H:%M:%SZ")
path = f"{REPO}/eval/work_claims.json"
d = json.load(open(path))
for c in d["claims"]:
    if c.get("work_id") == "r123-f97-verifier-corpus":
        raise SystemExit(f"REFUSED: claim exists {c.get('claim_id')}")
base = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO,
                      capture_output=True, text=True).stdout.strip()
claim = {
    "work_id": "r123-f97-verifier-corpus",
    "claim_id": "c-0187",
    "role": "EXECUTOR",
    "session_id": "builder-r117s1",
    "kind": "one_shot",
    "status": "DONE",
    "base_sha": base,
    "lease_expiry": "2026-11-26T23:59:00Z",
    "artifact_paths": [
        "tests/fixtures/f97_input_availability_cases.json",
        "eval/r123_f97_verifier_corpus/",
        "scripts/r123_build_f97_fixture.py",
        "scripts/r123_f97_verifier_run.py",
    ],
    "title": "The cross-implementation verifier corpus for the "
             "adjudicated F97 fix (the R123 verdict dir 2). CONTEXT: "
             "this session independently implemented the F97 fix "
             "(3 mechanisms; 25-case real-byte corpus 25/25 on its "
             "own bytes; re-scored both draws pooled bare 0.5208 vs "
             "succ 0.2292, CI [+0.1667,+0.4375], damage 1/23 — a "
             "second implementation's measurement) and found the "
             "twin lane had EXECUTED the same direction concurrently "
             "(claim c-0186, work id r124-f97-detector-precision, "
             "8-mechanism fix, gates met on both draws) — the "
             "duplicate execution STOOD DOWN per Art. 29(e); the "
             "canonical instrument is theirs. THIS RECORD: the "
             "25-case REAL-byte corpus applied to the CANONICAL "
             "instrument (eval/r123_f97_verifier_corpus/"
             "verifier_result.json): 16/16 prose/paren mis-parse "
             "shapes SILENT ON BOTH implementations (the F97 noise "
             "kill is robust across independent implementations); "
             "9/9 genuine-class cases fire ONLY on the verifier "
             "implementation and are SILENT on the canonical "
             "instrument — a typed RECALL QUESTION for the auditor's "
             "semantic call (whether the derived-feature/input-name "
             "residual class — the c-0185 root-cause class — should "
             "bind; the canonical design reads named logic/features "
             "and instrument-bridged quantities as non-binding). No "
             "bug claim; no score claim; zero LLM.",
    "registered_at": f"{NOW} (sandbox clock, TRUE UTC)",
    "claimed_at": f"{NOW} (sandbox clock, TRUE UTC)",
    "completed_at": f"{NOW} (sandbox clock, TRUE UTC)",
    "notes": "The verifier test file (tests/"
             "test_f97_input_availability_precision.py) is "
             "deliberately NOT committed: its fire-expectations "
             "encode the verifier implementation's semantics and "
             "would red the canonical tree by design; the corpus "
             "result record is the deliverable. The stale-bytecode "
             "hazard was met and purged during this work (typed in "
             "the orphaned F97 execution commit 2e4693f36's record).",
}
d["claims"].append(claim)
with open(path, "w") as f:
    json.dump(d, f, indent=1, sort_keys=True)
print(f"claim c-0187 registered DONE, base {base}")
