#!/usr/bin/env python3
"""Record + quarantine the 2026-09-06 gate-field-defect incident and
mark the defective construction attempt for its ONE bounded
re-attempt.

WHAT HAPPENED (Art. LXI discipline): the first TVM v2 construction
invocation completed 2 rungs. The second rung ('device switching
energy') produced 7 proposals, ALL rejected with
RECORD_ID_NOT_IN_RETRIEVED_POOL — but the proposals cited records
via the field name the SEALED PROMPT specifies ('source_record_id'),
while the deterministic gate read 'record_id'/'source_record'. The
model followed the contract; the GATE read the wrong key. The 7
rejections were manufactured by an infrastructure defect, not by
the proposals' content.

WHAT IS DONE ABOUT IT:
  1. The gate reads source_record_id first (aliases kept) — the
     pool check itself is UNCHANGED in strength.
  2. The defective entry's bytes are preserved HERE (Art. XI) and
     its 7 rejections are reclassified INCOMPLETE_INFRASTRUCTURE
     (never scientific rejections).
  3. The construction log entry is marked
     INCOMPLETE_GATE_FIELD_DEFECT, which makes the rung
     re-attemptable EXACTLY ONCE (bounded, like the v1 transport
     retry pattern); the defective attempt still counts against
     the sealed 12-call budget (honest accounting).
  4. Fix-forward: construction log entries now persist the
     retrieved RECORDS too, so any future replay has the full
     evidence in committed bytes.

What is NOT done: no proposal is repaired, no threshold changed, no
prompt changed, the seal is re-verified before any re-attempt.
"""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RUN = REPO / "R412" / "GRADIENT_V2" / "RUN"
TVM = RUN / "TVM_V2_CONSTRUCTED.json"
INC = RUN / "incidents" / "2026-09-06_gate_field_defect.json"

tvm = json.loads(TVM.read_text())
log = tvm["construction_log"]
defective = [e for e in log
             if e.get("rung") == "device switching energy"
             and e.get("n_retrieved") is not None]
assert len(defective) == 1, f"expected 1 defective entry, " \
                            f"got {len(defective)}"
e = defective[0]
assert e["n_rejected"] == 7 and all(
    r == "RECORD_ID_NOT_IN_RETRIEVED_POOL"
    for r in e.get("rejected_reasons") or [])

inc = {
    "incident_id": "2026-09-06-gate-field-defect-01",
    "class": "GATE_FIELD_DEFECT (Art. LXI: infrastructure failure "
             "manufactured 7 rejections; INCOMPLETE, never "
             "REJECTED_SCIENTIFIC)",
    "rung": e["rung"],
    "defect": "the deterministic admission gate read the record "
              "citation from 'record_id'/'source_record', while the "
              "SEALED prompt template specifies 'source_record_id'; "
              "the model followed the contract, the gate read the "
              "wrong key",
    "evidence": "7/7 rejections carry RECORD_ID_NOT_IN_RETRIEVED_"
                "POOL while the raw proposals cite source_record_id "
                "values that are DOI-style pool members",
    "rejections_reclassified": [
        {**r, "reclassified":
            "INCOMPLETE_INFRASTRUCTURE (was: REJECTED by a "
            "defective gate)"}
        for r in e.get("raw_rejected_with_reason") or []],
    "original_entry_bytes": e,
    "fix": "gradient_v2.verify_v2_proposals now reads "
           "source_record_id first (record_id/source_record kept as "
           "aliases); the pool-membership check itself is unchanged "
           "in strength",
    "fix_forward": "construction log entries persist the retrieved "
                   "records (record_id/title/abstract) so future "
                   "replays need no reconstruction",
    "bounded_replay_rule": "the rung is re-attempted EXACTLY ONCE; "
                           "the defective attempt still counts "
                           "against the sealed 12-call LLM budget "
                           "(honest accounting); the re-attempt "
                           "result records gate_defect_replayed",
    "no_prompt_change": True,
    "no_threshold_change": True,
    "reviewer_provenance": "AI_REVIEW",
}
INC.parent.mkdir(parents=True, exist_ok=True)
INC.write_text(json.dumps(inc, indent=1) + "\n")

e["status"] = "INCOMPLETE_GATE_FIELD_DEFECT"
e["incident_ref"] = "R412/GRADIENT_V2/RUN/incidents/" \
                    "2026-09-06_gate_field_defect.json"
e["rejections_reclassified"] = "INCOMPLETE_INFRASTRUCTURE " \
                               "(Art. LXI; original bytes in the " \
                               "incident artifact)"
TVM.write_text(json.dumps(tvm, indent=1) + "\n")
print("incident recorded:", INC)
print("defective entry marked INCOMPLETE_GATE_FIELD_DEFECT "
      "(re-attemptable once)")
