#!/usr/bin/env python3
"""Reclassify the 2026-09-06 empty-content LLM calls as
INCOMPLETE_TRANSPORT (Art. LXI) — they were misrecorded as parse
failures (MALFORMED_NO_JSON_ARRAY with EMPTY raw output) because the
runner did not check the call status before parsing.

Evidence: the three entries carry model=None, output_hash=None, and
an EMPTY raw_llm_output — the LLM calls returned no content (the
transient zai shared-quota failure the R411 campaign also measured),
so nothing was parsed at all. A transport failure is INCOMPLETE,
never a parse verdict, and never a completed construction attempt.

The original bytes are preserved here (Art. XI). The entries are
marked INCOMPLETE_TRANSPORT (bounded re-attemptable), their
llm_status recorded as recorded_empty_content, and the fix (status
check before parse) is disclosed. Zero proposals existed to reject,
so no scientific record changes.
"""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RUN = REPO / "R412" / "GRADIENT_V2" / "RUN"
TVM = RUN / "TVM_V2_CONSTRUCTED.json"
INC = RUN / "incidents" / "2026-09-06_transport_misclassification.json"

tvm = json.loads(TVM.read_text())
log = tvm["construction_log"]
bad = [e for e in log
       if (e.get("raw_llm_output") or "") == ""
       and e.get("n_proposed") == 0
       and e.get("model") is None
       and e.get("output_hash") is None
       and e.get("status") is None]
assert len(bad) == 3, f"expected 3, got {len(bad)}"

inc = {
    "incident_id": "2026-09-06-transport-misclassification-01",
    "class": "TRANSPORT_FAILURE_MISRECORDED_AS_PARSE_FAILURE "
             "(Art. LXI: infrastructure failure was recorded as a "
             "stage outcome; corrected to INCOMPLETE)",
    "affected_rungs": [e["rung"] for e in bad],
    "evidence": "model=None, output_hash=None, raw_llm_output empty "
                "on all three entries — the calls produced no "
                "content (transient zai shared-quota transport "
                "failure); nothing was parsed",
    "original_entries": [dict(e) for e in bad],
    "fix": "the runner now checks meta.ok + non-empty content "
           "BEFORE parsing; failed calls are recorded "
           "INCOMPLETE_TRANSPORT with llm_status/error, bounded "
           "re-attempt, and are disclosed incident overhead (the v1 "
           "orphan-calls precedent — they do not consume the sealed "
           "12-call budget)",
    "no_prompt_change": True,
    "no_threshold_change": True,
    "no_proposals_existed_to_reject": True,
    "reviewer_provenance": "AI_REVIEW",
}
INC.parent.mkdir(parents=True, exist_ok=True)
INC.write_text(json.dumps(inc, indent=1) + "\n")

for e in log:
    if e in bad:
        e["status"] = "INCOMPLETE_TRANSPORT"
        e["llm_status"] = "recorded_empty_content"
        e["incident_ref"] = ("R412/GRADIENT_V2/RUN/incidents/"
                             "2026-09-06_transport_misclassification"
                             ".json")
TVM.write_text(json.dumps(tvm, indent=1) + "\n")
print("incident recorded:", INC)
print("3 entries reclassified INCOMPLETE_TRANSPORT "
      "(bounded re-attemptable)")
