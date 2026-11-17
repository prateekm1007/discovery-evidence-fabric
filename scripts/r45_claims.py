#!/usr/bin/env python3
"""r45_claims.py — R45 claims (session builder-r45s2), filed BEFORE
any build or problem byte:
  c-0065  v81-capability-adoption  (D1 computed-physics layer + D2
          population tree search + TRIZ seeding — the AM42 delete-list
          replacements; kind task)
  c-0066  holdout-v8-generation-v81 (the FRESH one-shot execution of
          the sealed v8 packet under the V8.1 machine; kind one_shot;
          filed OPEN now, executed only after D1+D2 land)
The disposition decision recorded here (for the auditor's burn-
custody ruling at scoring time): the partial 23/30 V8.0 run is
VOIDED-SUPERSEDED (owner AM42 deletes single-chain repair); its rows
are retained as F54/F58 frontier evidence and are EXCLUDED from any
prompt compilation (Art. 13 — compile on eval/r43_scan_labels.json +
BURNED v7 rows only); the sealed packet is used ONCE for scoring by
the machine that will be scored (V8.1); the packet's prior 23-row
exposure (zero scores, zero per-problem adaptation, model has no
cross-call memory) is disclosed prominently for the auditor to rule
packet-valid vs v9-reauthor."""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
NOW = "2026-11-17T05:40:00Z (sandbox clock)"

p = REPO / "eval" / "work_claims.json"
d = json.loads(p.read_text(encoding="utf-8"))
d.setdefault("sessions", {})["builder-r45s2"] = {
    "registered_at": NOW, "role": "builder",
    "note": "R45 session (the AM42 D1+D2 adoption lane + the fresh "
            "v8-v81 one-shot executor). Registered before the claim "
            "push per Art. 29(a)."}

claims = d.setdefault("claims", [])
have = {c.get("claim_id") for c in claims}
new = []
if "c-0065" not in have:
    new.append({
        "claim_id": "c-0065",
        "work_id": "v81-capability-adoption",
        "title": "the AM42 D1+D2 adoption: (D1) a computed-physics "
                 "layer (CoolProp/ht/fluids/thermo/chemicals/tespy "
                 "with typed scipy fallbacks) binding "
                 "direction+magnitude+cost in code — Arrhenius scorch "
                 "integral, NPSH, LSI scaling, frost psychrometrics, "
                 "Larson-Miller, COP/fouling; (D2) the V8.1 machine "
                 "(scripts/r45_machine_v81.py): >=3 mechanistically "
                 "distinct candidates per intervention mapped to "
                 "distinct TRIZ principles, best-first selection by "
                 "the deterministic bind battery + computed physics; "
                 "the frozen V8.0 machine byte-untouched (retired "
                 "with Art. 16 accounting).",
        "status": "OPEN",
        "registered_at": NOW, "session_id": "builder-r45s2",
        "role": "EXECUTOR", "kind": "task",
        "base_sha": "c1b1414ca",
        "claimed_at": NOW,
        "lease_expiry": "2026-11-17T17:40:00Z",
        "takes_over": None,
        "artifact_paths": ["scripts/v81_physics.py",
                           "scripts/r45_machine_v81.py",
                           "scripts/triz_principles.py",
                           "tests/test_v81_binds.py",
                           "eval/retirement_ledger.json"],
        "notes": "The V8.0 partial run (23/30) is typed "
                 "VOIDED-SUPERSEDED by owner AM42's delete-list; "
                 "zero v8-row bytes enter prompt compilation "
                 "(Art. 13)."})
if "c-0066" not in have:
    new.append({
        "claim_id": "c-0066",
        "work_id": "holdout-v8-generation-v81",
        "title": "the FRESH one-shot execution of the sealed v8 "
                 "packet (audit/holdout_v8/holdout_v8_problems.json "
                 "@ af6b5b311-lineage audit tip, seal f65b9d8b… "
                 "recomputed EXACT before any generation) under the "
                 "V8.1 machine (glm-4-plus): 30/30 rows, serving "
                 "attestation PRE-SCORING, durable events, run "
                 "ledger; one executor; zero re-generation of THIS "
                 "run.",
        "status": "OPEN",
        "registered_at": NOW, "session_id": "builder-r45s2",
        "role": "EXECUTOR", "kind": "one_shot",
        "base_sha": "c1b1414ca",
        "claimed_at": NOW,
        "lease_expiry": "2026-11-17T17:40:00Z",
        "takes_over": None,
        "artifact_paths": ["eval/v81_run/rows/",
                           "eval/v81_run/v81_events_ledger.json",
                           "eval/v81_run/v81_serving_attestation.json",
                           "eval/v81_run/v81_run_ledger.json",
                           "eval/v81_run/gateway_log_slice.txt",
                           "scripts/r45_v81_one_shot.py"],
        "notes": "PACKET EXPOSURE DISCLOSED (for the auditor's "
                 "ruling): the same sealed packet served a 23/30 "
                 "generation under the now-VOIDED V8.0 machine "
                 "(claim c-0062, pushed durably at c1b1414ca); zero "
                 "scores existed, no per-problem adaptation occurred, "
                 "and no v8 row enters the V8.1 prompt compilation "
                 "(compiled on the labelled bind corpus + burned v7 "
                 "rows only) — the fresh run is epistemically clean "
                 "under Art. 13; the auditor owns burn custody and "
                 "may rule the packet spent and author v9 instead "
                 "(Art. 28: the loop escalates and acts, never "
                 "idles)."})
d["at"] = NOW
p.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n",
             encoding="utf-8")
print("claims filed:",
      [(c["claim_id"], c["work_id"], c["status"]) for c in new])
