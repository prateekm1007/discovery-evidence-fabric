#!/usr/bin/env python3
"""amend_ui_state_map.py — R453-C2 acceptance amendment to the §47
deliverable CODER2_UI_STATE_MAP.json.

The production acceptance round (fresh run ts_94d163221011 on the live
deploy at 8d019f3) observed three canonical wire tokens that the map
did not enumerate:

  1. evidence_state.state = GATHERED        (run_state.py::_evidence_state)
  2. mechanism_state.state = GENERATED      (run_state.py::_mechanism_state)
  3. result.final_status = INCOMPLETE_INFERENCE_FAILURE

The UI handles all three correctly (present.ts + presentationState.ts;
the adversarial battery 14/14) — the gap was in the §47 DOCUMENT. This
amendment is PURE ADDITION: no existing entry is altered or removed;
an amended provenance block records who/when/why. Art. XI: the map
must map EVERY canonical scientific state to its user-facing
representation — production just proved three were missing.
"""
import json
import time
from pathlib import Path

REPO = Path("/home/z/my-project/hf_space")
PATH = REPO / "CODER2_UI_STATE_MAP.json"

PROOF = ("production acceptance R453-C2: fresh run ts_94d163221011 "
         "on the live deploy at 8d019f3df7ef (Space revision 486bc0c7) "
         "observed this token on the wire; the UI rendered it honestly "
         "— the §47 document was missing it, not the interface")

doc = json.loads(PATH.read_text())
maps = doc["maps"]

# ---- 1. retrieval_state: the raw canonical token GATHERED --------------
maps["retrieval_state"]["GATHERED"] = {
    "user": "the RAW canonical token on the wire (run_state.py::"
            "_evidence_state). The presentation layer derives the user "
            "sentence from records_found: > 0 -> RETRIEVED_POSITIVE "
            "('I found N sources in the evidence base...'); == 0 -> "
            "RETRIEVED_ZERO ('the searches completed and returned no "
            "matching records' — a result about the searches, never "
            "about the problem).",
    "derives_to": ["RETRIEVED_POSITIVE", "RETRIEVED_ZERO"],
    "forbidden": ["no evidence exists", "not found"],
    "production_evidence": PROOF,
}

# ---- 2. mechanism_state: a WHOLE section the map lacked ----------------
maps["mechanism_state"] = {
    "source": "run_state.py::_mechanism_state (the wire token on "
              "run_state.mechanism_state.state)",
    "GENERATED": {
        "user": "A candidate mechanism emerged: <mechanism> — presented "
                "as a HYPOTHESIS at HYPOTHESIZED/INFERRED maturity, "
                "feeding the competing-hypotheses view; never an "
                "invention claim (Art. LXI: the candidate maturity is "
                "the ceiling).",
        "forbidden": ["new invention", "we invented"],
    },
    "FAILED": {
        "user": "The mechanism synthesis could not complete — an "
                "honest development outcome; nothing was concluded "
                "about the problem.",
        "forbidden": ["no mechanism exists"],
    },
    "PENDING": {
        "user": "I'm forming candidate mechanisms from the evidence "
                "now — in progress, not a finding.",
        "forbidden": [],
    },
    "NOT_REACHED": {
        "user": "The mechanism stage was not reached on this run — "
                "not a finding about the problem.",
        "forbidden": ["no mechanism possible"],
    },
    "production_evidence": PROOF,
}

# ---- 3. run_outcome: the final_status token INCOMPLETE_INFERENCE_FAILURE
maps["run_outcome"]["INCOMPLETE_INFERENCE_FAILURE"] = {
    "user": "the run result's final_status token. The engine's own "
            "user_state_view renders it as user_state COMPLETED_UNKNOWN "
            "('Completed — outcome unknown': the run reached a terminal "
            "state without a recorded verdict — the outcome could not "
            "be established from the run's own artifacts; decision: "
            "outcome not established; found_something=false, "
            "rejected=false) with outcome RUN_BLOCKED ('Run blocked — "
            "infrastructure, not a verdict'). The conversation renders "
            "the terminal-incomplete arc: 'Here is what the "
            "investigation found, and how far it got.' + 'I stopped "
            "partway — the infrastructure I need became unavailable.' + "
            "'Nothing was concluded about your problem — this is an "
            "infrastructure state, not a verdict on the idea.' with the "
            "next action 'Resume the investigation'.",
    "forbidden": ["failed", "rejected", "no invention possible"],
    "production_evidence": PROOF + "; the run carried evidence_state "
                           "GATHERED + mechanism_state GENERATED + "
                           "attack SKIPPED and concluded with NO "
                           "candidate — the honest partial arc",
}

# ---- 4. the amended provenance block ------------------------------------
doc["amended"] = {
    "round": "R453-C2-acceptance",
    "amended_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                    time.gmtime()),
    "reason": "the §44 STEP 15 production acceptance observed three "
              "canonical wire tokens (evidence_state GATHERED, "
              "mechanism_state GENERATED, final_status "
              "INCOMPLETE_INFERENCE_FAILURE) that this §47 document did "
              "not enumerate; the interface itself rendered all three "
              "honestly (the adversarial battery 14/14 + the live run) "
              "— the documentation gap is fixed here",
    "policy": "PURE ADDITION: no existing entry altered or removed; "
              "the three entries carry their production evidence",
    "fresh_run_session": "ts_94d163221011",
    "reviewer_provenance": "AI_REVIEW",
}

PATH.write_text(json.dumps(doc, indent=1))
n_maps = len([k for k, v in maps.items() if isinstance(v, dict)])
print(f"amended -> {PATH}")
print(f"sections now: {n_maps}; new keys: retrieval_state.GATHERED, "
      f"mechanism_state (4 tokens), run_outcome."
      f"INCOMPLETE_INFERENCE_FAILURE")
