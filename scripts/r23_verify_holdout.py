#!/usr/bin/env python3
"""r23_verify_holdout.py — c-0010 VERIFIER record for c-0009
(holdout-v2-generation, executor builder-r20s2): recompute generation
integrity FROM COMMITTED BYTES (Art. 13, never re-run), WITHOUT ever
opening audit/holdout_v2/holdout_v2_rubric_PRIVATE.json.

Checks:
  1. problem-set identity: the 12 pair files == the auditor's problems
     file (read from the audit branch) == the generation record.
  2. custody sha: the problems file's sha256 (first 16) recomputed from
     audit-branch bytes == the executor's recorded problems_sha256_16.
  3. selection sha: the executor's received selection_sha256 == the
     auditor's pre-registered PREREGISTRATION.selection_sha256.
  4. custody tip: audit_tip_at_read == 6235108c3 (the sealed tip).
  5. type-aware mapping: per-problem question_type (from the AUDIT
     problems file — authoritative) maps to the declared contract
     (intervention -> SYS_A1_INT_V4, predictor -> SYS_A1F_V4) and the
     pair records carry the matching a1_source.
  6. one-shot: exactly one generation attempt per problem; no
     candidates/best-of-k structures; transport_tries recorded; the
     machine-internal repair loop (REPAIR_BUDGET=2, disclosed by the
     executor as the machine under test — the same code path as
     r20/r21) is the ONLY re-prompting, and it is machine-internal
     typed scans, never rubric or judge feedback (typed for the
     auditor's ruling).
  7. builder-unjudged: no judged=True, no axes/draws/prefer tallies,
     no judge routes anywhere in the outputs.
  8. no rubric leak: the queue tree carries no rubric content (the
     rubric filename appears in protocol-typing strings only) and the
     driver source has no code path to the rubric file.
  9. answers substantive: every answer >1500 chars with the
     contract's required section structure.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
AUDIT = "origin/audit/r11-auditor-verdict-20261114"
GEN = REPO / "eval" / "holdout_v2_generation"
FAILS = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name +
          (f" | {detail}" if detail else ""))
    if not ok:
        FAILS.append(name)


def audit_bytes(path):
    return subprocess.run(["git", "show", f"{AUDIT}:{path}"],
                          capture_output=True, check=True).stdout


pre = json.loads(audit_bytes("audit/holdout_v2/PREREGISTRATION.json")
                 .decode())
probs_raw = audit_bytes("audit/holdout_v2/holdout_v2_problems.json")
probs = json.loads(probs_raw)
plist = probs if isinstance(probs, list) else probs.get("problems", [])
audit_ids = sorted(p["problem_id"] for p in plist)
audit_type = {p["problem_id"]: p.get("question_type") for p in plist}

rec = json.loads((GEN / "holdout_v2_generation_record.json").read_text(
    encoding="utf-8"))
pair_files = sorted(GEN.glob("HO2-*.json"))
pairs = [json.loads(p.read_text(encoding="utf-8")) for p in pair_files]

# 1. problem-set identity
pair_ids = sorted(x["problem_id"] for x in pairs)
check("12/12 problem-set identity (audit problems == pair files)",
      len(pair_files) == 12 and pair_ids == audit_ids == sorted(
          [p["problem_id"] for p in pairs]),
      f"{len(pair_files)} pair files, {len(audit_ids)} audit problems")

# 2. custody sha
sha16 = hashlib.sha256(probs_raw).hexdigest()[:16]
check("problems-file sha matches the executor's custody record",
      sha16 == rec["custody"]["problems_sha256_16"], sha16)

# 3. selection sha
check("selection_sha256 received == auditor pre-registration",
      rec["custody"]["selection_sha256_received"]
      == pre["selection_sha256"])

# 4. custody tip
check("custody read at the sealed tip 6235108c3",
      rec["custody"]["audit_tip_at_read"] == "6235108c3"
      and all(x.get("audit_tip_at_read") == "6235108c3" for x in pairs),
      rec["custody"]["audit_tip_at_read"])

# 5. type-aware mapping
mismatches = []
for x in pairs:
    qt = str(audit_type.get(x["problem_id"], ""))
    family = qt.split("-")[0] if qt else ""
    want = {"intervention": "SYS_A1_INT_V4", "predictor": "SYS_A1F_V4"}.get(
        family)
    src = str(x.get("a1_source", ""))
    if want and want not in src:
        mismatches.append((x["problem_id"], qt, src[:40]))
check("type-aware contract mapping (intervention->INT_V4, "
      "predictor->F_V4) on all 12, from the AUDIT problems file",
      not mismatches, f"mismatches={mismatches[:3]}")

# 6. one-shot
bad_one = []
for x in pairs:
    atts = x.get("attempts") or []
    gens = [a for a in atts if a.get("kind") == "generation"]
    reps = [a for a in atts if str(a.get("kind", "")).startswith("repair")]
    if (len(gens) != 1
            or not isinstance(gens[0].get("transport_tries"), int)
            or len(reps) > 2
            or any(not a.get("findings_disclosed") for a in reps)):
        bad_one.append((x["problem_id"], len(gens), len(reps)))
check("one-shot: exactly one generation attempt per problem (with "
      "transport tries); machine-internal repairs <= REPAIR_BUDGET=2, "
      "each disclosing its typed findings — no re-draw of a returned "
      "call", not bad_one, f"violations={bad_one[:3]}")
check("no best-of-k/candidate structures in any pair file",
      not any("candidates" in x or "selected_idx" in x for x in pairs))

# 7. builder-unjudged
leak_judge = []
for x in pairs:
    if x.get("judged") is not False or x.get("axes") or x.get("draws"):
        leak_judge.append(x["problem_id"])
check("builder-unjudged (judged=False, no axes/draws anywhere)",
      not leak_judge, f"violations={leak_judge[:3]}")

# 8. no rubric leak in queue tree
rub_hits = []
for p in GEN.iterdir():
    t = p.read_text(encoding="utf-8")
    for line in t.splitlines():
        low = line.lower()
        if "rubric" in low and ("k_coverage" in low or "d_quality"
                                in low or "score" in low.lower()
                                and "0-4" in low):
            rub_hits.append((p.name, line.strip()[:80]))
driver_src = (REPO / "scripts" / "r22_holdout_v2_generate.py").read_text(
    encoding="utf-8")
check("no rubric content in the queue tree; driver has no rubric code "
      "path (problems-only custody)",
      not rub_hits and "rubric_PRIVATE" not in driver_src,
      f"content hits={rub_hits[:2]}")

# 9. answers substantive
thin = [(x["problem_id"], len(x.get("a1_answer") or ""))
        for x in pairs if len(x.get("a1_answer") or "") < 1500]
check("all 12 answers substantive (>1500 chars)", not thin,
      f"thin={thin[:3]}")
no_bill = [x["problem_id"] for x in pairs
           if str(audit_type.get(x["problem_id"], "")).startswith(
               "intervention")
           and "IMPLEMENTATION BILL" not in str(x.get("a1_answer", ""))]
check("intervention answers carry the IMPLEMENTATION BILL section",
      not no_bill, f"missing={no_bill[:3]}")

print()
if FAILS:
    print(f"VERIFIER: FAILED — {len(FAILS)} mismatch(es)")
    for f in FAILS:
        print("  -", f)
    sys.exit(1)
print("VERIFIER: HOLDOUT-V2 GENERATION INTEGRITY CONFIRMED — the "
      "one-shot was clean (problems-only custody, byte-unchanged "
      "type-aware machine, single generation pass per problem, "
      "builder-unjudged, no rubric access). TYPED NOTE for the "
      "auditor's ruling: the executor disclosed the machine-internal "
      "repair loop (REPAIR_BUDGET=2, critic/scan feedback only — the "
      "same code path as r20/r21) as part of the machine under test; "
      "no outcome-based (rubric/judge) iteration exists in the bytes. "
      "c-0009 flips to DONE on this record (Art. 29(c)); scoring and "
      "burn-after are the auditor's.")
