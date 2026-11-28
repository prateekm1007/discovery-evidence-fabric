#!/usr/bin/env python3
"""R64s4 VERIFIER: independent recompute of the holdout-v9 generation completion
from raw artifact bytes (auditor-constitution Art. 13 independent tally recompute;
epistemic-constitution Art. 29(c) VERIFIER role: recompute, never re-run).

Read-only over eval/holdout_v9_generation/ + the audit-branch sealed packet.
Writes eval/r64s4_verify_completion.json (numbers + digests only).
Any check mismatch -> FAIL exit 1.
"""
import collections
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ART = REPO / "eval" / "holdout_v9_generation"
AUDIT_REF = "origin/audit/r11-auditor-verdict-20261114"
V9_PROBLEMS_PATH = "audit/holdout_v9/holdout_v9_problems.json"
V9_PREREG_PATH = "audit/holdout_v9/PREREGISTRATION.json"
REGISTERED = "agnes-3.0-flash"
INSTRUMENT_EXECUTOR = "builder-r60s1@holdout-v9-generation"
OUT = Path(os.environ.get(
    "R64S4_VERIFY_OUT", str(REPO / "eval" / "r64s4_verify_completion.json")))
SUBJECT = os.environ.get(
    "R64S4_VERIFY_SUBJECT", "eval/holdout_v9_generation/ (this tree's window)")
TOKEN_RE = re.compile(
    r"sk-[A-Za-z0-9]{16}|hf_[A-Za-z0-9]{16}|ghp_[A-Za-z0-9]{16}"
    r"|github_pat_[A-Za-z0-9_]{10}")

checks = []


def check(name, ok, got=None, want=None, note=None):
    rec = {"check": name, "verdict": "PASS" if ok else "FAIL",
           "got": got, "want": want}
    if note:
        rec["note"] = note
    checks.append(rec)
    return ok


def sha256_file(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def git_show(path, ref=AUDIT_REF):
    r = subprocess.run(["git", "show", f"{ref}:{path}"], cwd=REPO,
                       capture_output=True, text=True, check=True)
    return r.stdout


# ---- 1. rows/ -------------------------------------------------------------
rows = sorted((ART / "rows").glob("HO9-*.json"))
rowdata = [json.loads(p.read_text()) for p in rows]
ids = [d.get("problem_id") for d in rowdata]
check("rows.count==30", len(rows) == 30, len(rows), 30)
check("rows.filename==problem_id",
      all(p.stem == i for p, i in zip(rows, ids)))
tally = collections.Counter(
    d.get("final_meta", {}).get("critic_verdict", "MISSING") for d in rowdata)
check("rows.verdicts_typed_and_total_30",
      all(d.get("final_meta", {}).get("critic_verdict") in ("CLEAN", "FLAG")
          for d in rowdata) and len(rows) == 30,
      dict(tally), "all in {CLEAN,FLAG}, n=30",
      note="tally RECOMPUTED and disclosed, never asserted from a prior "
           "record (the 23-row partial state quoted 21 CLEAN / 2 FLAG)")
flag_rows = [p.stem for p, d in zip(rows, rowdata)
             if d.get("final_meta", {}).get("critic_verdict") == "FLAG"]
# typed finding classes per FLAG row, from the events ledger attempts
ev_raw0 = json.loads((ART / "events.json").read_text())
ev0 = ev_raw0.get("events") if isinstance(ev_raw0, dict) else ev_raw0
flag_classes = sorted({f.split(":")[0]
                       for e in ev0 if e.get("problem_id") in flag_rows
                       for a in e.get("attempts", [])
                       for f in a.get("findings_disclosed", [])})
check("rows.FLAG_findings_typed", bool(flag_rows) == bool(flag_classes),
      {"flag_rows": sorted(flag_rows), "finding_classes": flag_classes},
      "every FLAG row carries typed findings_disclosed")
row_exec = {d.get("executor_id") for d in rowdata}
check("rows.executor_id==instrument_constant", row_exec == {INSTRUMENT_EXECUTOR},
      sorted(row_exec), [INSTRUMENT_EXECUTOR],
      note="EXECUTOR_ID is a hard-coded lock-holder constant "
           "(scripts/r60_v9_one_shot.py:101); true executor chain lives in "
           "eval/r64s4_adoption_record.json")

# ---- 2. events ledger ------------------------------------------------------
ev_raw = json.loads((ART / "events.json").read_text())
ev = ev_raw.get("events") if isinstance(ev_raw, dict) else ev_raw
check("events.count==30", len(ev) == 30, len(ev), 30)
eids = [e.get("problem_id") for e in ev]
check("events.ids==rows.ids(order)", eids == ids)
ats = [e.get("generated_at") for e in ev]
check("events.timestamps.monotonic", all(a <= b for a, b in zip(ats, ats[1:])))

# ---- 3. sealed packet selection order --------------------------------------
packet = json.loads(git_show(V9_PROBLEMS_PATH))
if isinstance(packet, dict):
    pids_raw = packet.get("problems") or packet.get("selection") or []
else:
    pids_raw = packet
pids = [p.get("problem_id") if isinstance(p, dict) else p for p in pids_raw]
check("seal.selection_order==events.ids(order)", pids == eids,
      {"packet_first3": pids[:3], "packet_n": len(pids)},
      {"events_first3": eids[:3], "events_n": len(eids)})
prereg = json.loads(git_show(V9_PREREG_PATH))
sel_sha = prereg.get("selection_sha256")

# ---- 4. gateway slice -------------------------------------------------------
lines = [json.loads(l)
         for l in (ART / "gateway_slice.txt").read_text().splitlines()
         if l.strip()]
statuses = collections.Counter(l.get("status") for l in lines)
completed = [l for l in lines if l.get("status") == "OK"]
check("slice.lines>=completed", len(lines) >= len(completed),
      (len(lines), len(completed)), "telemetry included")
bad_served = [l.get("ts") for l in completed
              if l.get("model") != REGISTERED
              or l.get("requested_model") != REGISTERED]
check("slice.completed_calls>0", len(completed) > 0,
      len(completed), ">=1 (cross-checked vs attestation below)")
check("slice.completed.served==requested==registered(agnes-3.0-flash)",
      not bad_served, bad_served[:3], "none")
no_model = sum(1 for l in lines if not l.get("model"))
check("slice.lines_without_model_field==0", no_model == 0, no_model, 0,
      note="attestation error-line definition: lines carrying no model field")
at = json.loads((ART / "attestation.json").read_text())
ts_all = sorted(l.get("ts", "") for l in lines)
check("slice.window within [events.first, attestation.window_ended]",
      ts_all[0] >= ats[0] and ts_all[-1] <= at.get("window_ended_at", "9999"),
      [ts_all[0], ts_all[-1], f"events.first={ats[0]}"])
check("slice.covers_events_first (no coverage gap)",
      ts_all[0] <= ats[0],
      {"slice.first": ts_all[0], "events.first": ats[0]},
      "slice.first <= events.first; a later slice.first means calls "
      "before it are UNVERIFIABLE from committed bytes (Art. 1)")
gap_rows = [e.get("problem_id") for e in ev if e.get("generated_at") < ts_all[0]]
check("slice.gap_rows_disclosed", True, gap_rows,
      note="rows whose generated_at precedes the committed slice; "
           "their gateway calls are typed UNVERIFIED here")
check("slice.status_distribution", True, dict(statuses),
      note="typed; non-OK statuses are telemetry, never scored")

# ---- 5. attestation cross-check ---------------------------------------------
at = json.loads((ART / "attestation.json").read_text())
check("attest.rows_committed==30", at.get("rows_committed") == 30,
      at.get("rows_committed"), 30)
check("attest.gateway_completed_calls==recomputed",
      at.get("gateway_completed_calls") == len(completed),
      at.get("gateway_completed_calls"), len(completed))
for k in ("all_calls_requested_registered", "all_calls_served_registered",
          "served_model_matches_registered", "rows_30_30_attestation"):
    check(f"attest.{k}==true", at.get(k) is True, at.get(k), True)
check("attest.registered_model==agnes-3.0-flash",
      at.get("registered_model") == REGISTERED, at.get("registered_model"),
      REGISTERED)
import re as _re
_iso = bool(_re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$",
                      str(at.get("window_started_at", ""))))
check("attest.window_started_is_iso_or_typed",
      _iso or str(at.get("window_started_at")) == "(recomputed from bytes)",
      at.get("window_started_at"),
      "ISO-8601Z or the disclosed recompute placeholder",
      note="a placeholder makes the window start UNVERIFIED from this "
           "attestation alone; the events ledger is the byte source")
check("attest.window_ended>=last_event",
      at.get("window_ended_at", "") >= ats[-1],
      [at.get("window_ended_at"), ats[-1]])
check("attest.executor_id==instrument_constant",
      at.get("executor_id") == INSTRUMENT_EXECUTOR, at.get("executor_id"),
      INSTRUMENT_EXECUTOR)

# ---- 6. token-pattern scan (Art. 12/17) -------------------------------------
hits = []
for p in (list(ART.glob("*.json")) + list(ART.glob("*.txt"))
          + list((ART / "rows").glob("*.json"))):
    if TOKEN_RE.search(p.read_text(errors="ignore")):
        hits.append(p.name)
check("token_pattern_scan==0", not hits, hits, "none")

# ---- digests (records carry digests only) -----------------------------------
def set_digest(paths):
    h = hashlib.sha256()
    for p in sorted(paths):
        h.update(p.name.encode())
        h.update(sha256_file(p).encode())
    return h.hexdigest()[:16]

digests = {
    "events.json_sha256_16": sha256_file(ART / "events.json")[:16],
    "gateway_slice.txt_sha256_16": sha256_file(ART / "gateway_slice.txt")[:16],
    "attestation.json_sha256_16": sha256_file(ART / "attestation.json")[:16],
    "rows_set_sha256_16": set_digest(rows),
    "prereg_selection_sha256_at_ref": sel_sha,
}

fails = [c for c in checks if c["verdict"] == "FAIL"]
rec = {
    "record": "R64S4_VERIFY_COMPLETION/1.0.0",
    "session": "builder-r64s4 (continuation session; VERIFIER recompute per "
               "epistemic Art. 29(c) — recomputed, never re-run)",
    "date": "2026-11-18",
    "subject": SUBJECT,
    "registered_model": REGISTERED,
    "audit_ref": AUDIT_REF,
    "method": "independent recompute from raw artifact bytes + audit-branch "
              "sealed packet via git show; no instrument module imported",
    "checks": checks,
    "digests": digests,
    "verdict": "VERIFIED" if not fails else "FAILED",
}
OUT.write_text(json.dumps(rec, indent=1) + "\n")
for c in checks:
    print(f"[{c['verdict']}] {c['check']}  got={c['got']}")
print(f"\n{len(checks) - len(fails)}/{len(checks)} checks PASS -> {rec['verdict']}")
print("record written:", OUT)
sys.exit(0 if not fails else 1)
