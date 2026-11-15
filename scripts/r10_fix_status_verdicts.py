#!/usr/bin/env python3
"""r10_fix_status_verdicts.py — applies the verdict-claim corrections to
eval/r10_status_r11.json (the previous attempt died on a wrong key path
after the eval-new06 update had already landed; dcf75c839's message
therefore overclaims for the status file — this script + its commit
complete the correction honestly)."""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
f = REPO / "eval" / "r10_status_r11.json"
d = json.loads(f.read_text())
am = d["AM10_directions"]
am["D2_f29_30_answers"] = am["D2_f29_30_answers"].replace(
    "All 30 A1 answers committed as bytes",
    "All 30 A1 answers committed as bytes (per-record verdicts, "
    "corrected in verdict_corrections below)")
am["D4_feasibility_grounding"] = am["D4_feasibility_grounding"].replace(
    "critic CLEAN 12/12",
    "critic 10 CLEAN + 2 typed FLAG disclosures (see "
    "verdict_corrections)")
d["verdict_corrections"] = {
    "corrects": ("this record's own D2/D4 claims and the messages of "
                 "e634f8024/dcf75c839"),
    "grounded_12": ("10 CLEAN + 2 typed FLAG disclosures (bench-p02, "
                    "eval-new01 — TEST_DURATION_REALTIME, the SAME "
                    "pre-existing disclosed class carried since the R3 "
                    "corpus; not kills)"),
    "fresh_18": ("17 CLEAN + eval-new06: stored KILL written under the "
                 "pre-broadening regex, current-instrument recheck "
                 "CLEAN (typed instrument_recheck field in the record, "
                 "history preserved, Art. XI)"),
    "lesson": ("verdict claims must be read from the stored bytes, "
               "not from partial run logs — the disk-verification step "
               "caught this before the round ended (the 066f1aa3e "
               "lesson holding); also: a heredoc that dies mid-way "
               "must abort the follow-up commit — newline-separated "
               "statements do not inherit exit codes (dcf75c839 landed "
               "with the status correction missing; completed here)"),
}
f.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n",
             encoding="utf-8")
print("[fix] status corrections applied:",
      list(d["verdict_corrections"].keys()))
