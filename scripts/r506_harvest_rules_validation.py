#!/usr/bin/env python3
"""Validation harness for scripts/r506_harvest_rules.py against REAL durable
bytes (measure-before-integration): contamination on the R484 terminal run,
clarification on a live battery session with its real problem.json, plus
synthetic positive probes for both rules."""
import importlib.util
import json
import os
import shutil
import sys
import tempfile

import os as _os
REPO = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
WORKTREE = "/home/z/my-project/r506_durable"  # the durability worktree (local, Art. LXXIV)

spec = importlib.util.spec_from_file_location(
    "hr", os.path.join(REPO, "scripts", "r506_harvest_rules.py"))
hr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hr)

rules = json.load(open(os.path.join(REPO, "R506", "HARVEST_RULES.json"),
                       encoding="utf-8"))
seeds = rules["seeds"]
seed_grams = {s["seed_record_id"]: hr.ngrams(
    hr.norm_tokens(s["narrative_text"]), hr.CONTENT_NGRAM_WORDS) for s in seeds}

fails = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + (f" | {detail}" if detail else ""))
    if not cond:
        fails.append(name)


# 1. contamination on the R484 terminal run (geothermal — no automotive seeds)
r484 = os.path.join(WORKTREE, "runs",
                    "toscanini_ui_ui_calcite_and_silica_gel_deposition_on_separ_602181")
c = hr.contamination_for_run(r484, seeds, seed_grams, ev_ok_measured=True,
                             ms_measured=True)
check("R484 verdict CLEAN", c["verdict"] == "CLEAN", c["verdict"])
check("R484 evidence set non-empty", c["evidence_set_size"] > 0,
      f"n={c['evidence_set_size']}")
check("R484 no seed tokens anywhere", c["seed_token_files_anywhere"] == {})
check("R484 credit stands", c["credit_adjustment"]["evidence_verified_credited"])

# 2. synthetic contamination probes (each in an isolated run dir)
def probe_dir(name, files):
    d = os.path.join(tempfile.mkdtemp(prefix="hr_probe_"), name)
    os.makedirs(d)
    for fname, doc in files.items():
        with open(os.path.join(d, fname), "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False)
    return d

# probe1: credited evidence collapses to the seed -> CONTAMINATED
p1 = probe_dir("p1", {"candidate_envelope.json": {
    "evidence": [{"id": "nhtsa_odi:11664780", "source_type": "adverse_event",
                  "summary": "seed probe"}]}})
c2 = hr.contamination_for_run(p1, seeds, seed_grams, ev_ok_measured=True,
                              ms_measured=True)
check("probe1 verdict CONTAMINATED (evidence collapses to seed)",
      c2["verdict"] == "CONTAMINATED", c2["verdict"])
check("probe1 credit withheld",
      c2["credit_adjustment"]["evidence_verified_credited"] is False
      and c2["credit_adjustment"]["mechanisms_found_credited"] is False)
# probe2: an independent DOI survives the exclusion -> SELF-EVIDENCE-EXCLUDED
p2 = probe_dir("p2", {"candidate_envelope.json": {
    "evidence": [{"id": "nhtsa_odi:11664780", "summary": "seed probe"},
                 {"id": "doi:10.2118/0615-0032-ogf",
                  "source_type": "scientific_paper", "summary": "x"}]}})
c3 = hr.contamination_for_run(p2, seeds, seed_grams, ev_ok_measured=True,
                              ms_measured=True)
check("probe2 verdict SELF-EVIDENCE-EXCLUDED (survives exclusion)",
      c3["verdict"] == "SELF-EVIDENCE-EXCLUDED", c3["verdict"])
check("probe2 remaining counted", c3["credited_ids_remaining_after_exclusion"] >= 1)
# probe3: seed only in metadata bytes, not in evidence set -> CLEAN + disclosure
p3 = probe_dir("p3", {"envelope_VERIFY.json": json.load(
    open(os.path.join(r484, "envelope_VERIFY.json"), encoding="utf-8"))})
with open(os.path.join(p3, "EVENT_JOURNAL.jsonl"), "a", encoding="utf-8") as f:
    f.write('\n{"retrieved": "nhtsa_odi:11664780"}\n')
c4 = hr.contamination_for_run(p3, seeds, seed_grams, ev_ok_measured=True,
                              ms_measured=True)
check("probe3 verdict CLEAN (token outside credited evidence set)",
      c4["verdict"] == "CLEAN", c4["verdict"])
check("probe3 disclosure net fired",
      c4["seed_token_files_anywhere"].get("nhtsa_odi:11664780")
      == ["EVENT_JOURNAL.jsonl"])
# probe4: CONTENT_OVERLAP — 12-word verbatim span of a seed narrative
narr = seeds[0]["narrative_text"]
span = " ".join(hr.norm_tokens(narr)[:14])
p4 = probe_dir("p4", {"candidate_envelope.json": {
    "evidence": [{"id": "doi:10.9999/fake",
                  "summary": f"prior art states {span}"}]}})
c5 = hr.contamination_for_run(p4, seeds, seed_grams, ev_ok_measured=True,
                              ms_measured=True)
check("probe4 content overlap detected as seed-like",
      c5["verdict"] == "CONTAMINATED"
      and c5["content_overlap_items"], c5["verdict"])

# 3. clarification audit on the live battery session ts_66e23c67b511 (real Q&A)
sess = {s.get("session_id"): s for s in
        json.load(open(os.path.join(WORKTREE, "sessions.json"),
                       encoding="utf-8"))["sessions"]}
sid = "ts_66e23c67b511"
run_dir = os.path.join(WORKTREE, "runs",
                       "toscanini_ui_ui_complete_power_loss_while_driving_690150")
baseline = json.load(open(os.path.join(run_dir, "problem.json"),
                          encoding="utf-8")).get("user_text")
cl = hr.clarification_for_run(run_dir, sess.get(sid), baseline, None)
check("battery clarification intact (verbatim subset)",
      cl["verdict"] == "BLINDNESS_INTACT_VERBATIM_SUBSET", cl["verdict"])
check("byte-proof subset flag true on every answered pair",
      all(p.get("answer_is_verbatim_subset_of_submitted_problem") is True
          for p in cl["pairs"] if not p.get("unanswered")))
check("pairs carried with hashes", all(p.get("answer_sha256") for p in cl["pairs"]))

# 4. downgraded probe: answer introduces new technical content
s2 = dict(sess.get(sid))
s2["clarification_answer"] = {"field": "desired_outcome",
                              "answer": "Use a titanium heat pipe at 40 W/mK "
                                        "and set the target to 99.97% removal",
                              "provenance": "USER_STATED"}
cl2 = hr.clarification_for_run(run_dir, s2, baseline, None)
check("downgraded probe flags NEW CONTENT",
      cl2["verdict"] == "BLINDNESS_DOWNGRADED_NEW_CONTENT", cl2["verdict"])
check("new-content preview typed",
      cl2["pairs"][0].get("new_content_chars", 0) > 0)

# 5. absent-bytes typing
cl3 = hr.clarification_for_run(run_dir, None, baseline, None)
check("absent Q&A typed honestly",
      cl3["verdict"] == "CLARIFICATION_BYTES_ABSENT_IN_DURABLE_RECORD")

print()
print("RESULT:", "ALL PASS" if not fails else f"{len(fails)} FAILURES: {fails}")
sys.exit(1 if fails else 0)
