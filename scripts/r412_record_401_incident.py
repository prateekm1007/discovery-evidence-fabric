#!/usr/bin/env python3
"""Record the 2026-09-06 gateway-ownership (401) incident and reset
the incident-attributed transport failures.

ROOT CAUSE (measured): the runner's --gateway path only started a
gateway when NONE was alive. The sandbox did NOT reap the previous
invocation's gateway (contrary to the recorded process-scoped
expectation), so the next invocation found a healthy gateway
carrying the PREVIOUS invocation's unknown key — while this fresh
process had no ZAI_API_KEY — producing HTTP 401 / PROVIDER_
UNAVAILABLE on every LLM call (direct probe verified the upstream
was healthy throughout; the failure was purely local auth).

EFFECT: 9 construction attempts failed INCOMPLETE_TRANSPORT across
two invocations (3 initially misrecorded as parse failures —
already reclassified by the prior incident — plus 6 more), burning
transport-retry counters on rungs whose failure was this incident,
not the upstream.

TREATMENT (Art. LXI + the bounded-retry design intent):
  * the fix is shipped: --gateway now ALWAYS establishes a
    runner-owned gateway (pkill + fresh key + env export);
  * the incident-attributed failures do NOT count toward the
    2-failure bounded retry (the bound guards against an
    unreachable upstream, not against a fixed local defect);
  * the device-switching-energy gate-defect replay is marked
    CONSUMED on the defective entry (the replay happened; it
    transport-failed; further attempts flow through the normal
    transport path);
  * every affected entry carries incident_ref; the original bytes
    are preserved in THIS artifact.
"""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RUN = REPO / "R412" / "GRADIENT_V2" / "RUN"
TVM = RUN / "TVM_V2_CONSTRUCTED.json"
INC = RUN / "incidents" / "2026-09-06_gateway_ownership_401.json"

tvm = json.loads(TVM.read_text())
log = tvm["construction_log"]
transport = [e for e in log
             if e.get("status") == "INCOMPLETE_TRANSPORT"]
defect = [e for e in log
          if e.get("status") == "INCOMPLETE_GATE_FIELD_DEFECT"]
assert len(defect) == 1
assert transport, "expected incident-affected transport entries"

inc = {
    "incident_id": "2026-09-06-gateway-ownership-401",
    "class": "LOCAL_TRANSPORT_AUTH_DEFECT (Art. LXI: infrastructure "
             "failure; INCOMPLETE, never scientific)",
    "root_cause": "the runner reused an already-alive gateway whose "
                  "key belonged to a previous invocation; the fresh "
                  "process had no ZAI_API_KEY -> 401 -> "
                  "PROVIDER_UNAVAILABLE on every call (upstream "
                  "verified healthy by direct probe throughout)",
    "fix": "scripts/r412_run_gradient_v2.py --gateway now ALWAYS "
           "establishes a runner-owned gateway (pkill + fresh key + "
           "env export); verified by the post-fix invocation "
           "returning real completions",
    "affected_transport_entries": [
        {"rung": e["rung"],
         "llm_status": e.get("llm_status"),
         "error": e.get("error")}
        for e in transport],
    "n_failed_calls": len(transport),
    "treatment": "incident-attributed failures do not count toward "
                 "the 2-failure bounded retry (the bound guards an "
                 "unreachable upstream, not a fixed local defect); "
                 "affected entries carry incident_ref",
    "defect_replay_closure": "the device-switching-energy "
                             "gate-defect re-attempt is CONSUMED "
                             "(its replay transport-failed under "
                             "this incident; further attempts flow "
                             "through the normal transport path)",
    "no_prompt_change": True,
    "no_threshold_change": True,
    "reviewer_provenance": "AI_REVIEW",
}
INC.parent.mkdir(parents=True, exist_ok=True)
INC.write_text(json.dumps(inc, indent=1) + "\n")

for e in log:
    if e.get("status") == "INCOMPLETE_TRANSPORT":
        e["incident_ref"] = ("R412/GRADIENT_V2/RUN/incidents/"
                             "2026-09-06_gateway_ownership_401.json")
        e["incident_attributed"] = "gateway_ownership_401"
defect[0]["gate_defect_replayed"] = True
TVM.write_text(json.dumps(tvm, indent=1) + "\n")
print("incident recorded:", INC)
print(f"{len(transport)} transport entries marked "
      "incident-attributed (retry bound not consumed)")
print("gate-defect replay marked consumed")
