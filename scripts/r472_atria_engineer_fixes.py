#!/usr/bin/env python3
"""R472 — Atria ENGINEER sessions, split per task (the sandbox kills
long-lived background processes; each call stays small and fast).

Task A: the E2E driver Leg-D observation persistence (audit Top-10 #9).
Task B: the no-survivor learning card (audit Top-10 #4 / P0-4).

CTO spec -> Atria (Atria-Dawn-Preview) drafts -> CTO reviews,
integrates, tests. Artifacts: R472/ATRIA_ENGINEER_A.json,
R472/ATRIA_ENGINEER_B.json + the raw drafts. Tokens on the operator's
fourteen-key ring; keys rotate on persistent transport failure.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT_DIR = REPO / "R472"
RING_KEYS = ["ATRIA_API_KEY_11", "ATRIA_API_KEY_12", "ATRIA_API_KEY_13",
             "ATRIA_API_KEY_14", "ATRIA_API_KEY", "ATRIA_API_KEY_2"]

SYSTEM = """You are the delegated code/engineer for the Toscanini discovery
engine (round R472). The CTO has specified a fix; you implement it EXACTLY.
Constitutional constraints that are NON-NEGOTIABLE:
1. HONESTY OVER COMFORT: derive from RECORDED data only; if a fact is
   not recorded, say so — never fabricate.
2. TYPED STATES: machine-readable kinds, never free-prose blobs.
3. APPEND-ONLY: projections never mutate recorded fields.
4. NO new dependencies; stdlib only; keep existing public names and
   behaviors the standing tests pin.
5. Product language: user-facing strings are plain sentences, precisely
   honest about what happened.
Output EXACTLY one fenced python code block and nothing else."""

SPEC_A = """CTO SPEC — TASK A: scripts/r471_prod_e2e.py Leg D observation
persistence (the audit's Top-10 #9: "Fix the R471 E2E driver save/output
defect so future proof does not require record reconstruction").

THE MEASURED DEFECT: the driver builds this_obs from the retry POST,
then calls _save() BEFORE this_obs is written into
record["legs"]["D_retry"] — a kill during the multi-minute resume poll
loses the 202+retry_id body (the R471 disclosed reconstruction).

THE FIX (minimal, structural):
1. Immediately after `d: dict = {}`, assign `record["legs"]["D_retry"]
   = d` so every later mutation of d is visible to every _save.
2. Set `d["on_terminal"] = this_obs` BEFORE the first _save that
   follows the retry POST.
3. Keep the resume-aware elif branch working: when a prior invocation
   already measured a 202 (prior_on_terminal) and THIS invocation's
   retry answers a typed refusal on the NEW terminal, keep BOTH halves
   (prior stays on_terminal; this becomes refusal_after_verdict).
4. No other behavior change.

CURRENT Leg D region (replace it wholesale in your answer):

    _log("LEG D: retry contract, live")
    d: dict = {}
    # D1 may already have been measured by a prior (killed) invocation —
    # the state file carried the observation; never lose it
    prior_d = record["legs"].get("D_retry") or {}
    prior_on_terminal = prior_d.get("on_terminal") or (
        {"http": prior_d.get("http"), "body": prior_d.get("body")}
        if prior_d.get("http") else None)
    st, retry = _req("POST", f"/api/sessions/{sid}/retry")
    this_obs = {"http": st, "body": {
        k: retry.get(k) for k in ("retry_id", "status", "retry_attempts",
                                  "refusal", "session_status",
                                  "retryable") if k in retry}}
    _log(f"  retry on {terminal} -> HTTP {st} "
         f"retry_id={retry.get('retry_id')} refusal={retry.get('refusal')}")
    _save(record, state_path, sid, owner_key)

    if st == 202:
        d["on_terminal"] = this_obs
        # ... long resume poll (minutes) ...
    elif prior_on_terminal and prior_on_terminal.get("http") == 202:
        d["on_terminal"] = prior_on_terminal
        d["refusal_after_verdict"] = this_obs
        d["resumed_terminal"] = terminal
    else:
        d["on_terminal"] = this_obs
    record["legs"]["D_retry"] = d
"""

SPEC_B = """CTO SPEC — TASK B: toscanini/run_state.py the no-survivor
learning card (audit P0-4 acceptance: "A terminal no-mechanism card
shows searched territory, strongest failed hypothesis, key missing
evidence, and 2-3 ranked next actions"; "the ideal refusal surface:
what was tested; what failed or remained unknown; the smallest next
action that could change the result").

DATA AVAILABLE (recorded fields only — NEVER invent beyond these):
- run_dir/INVENTION_LINEAGE.json: {generations: [{gen, mechanism,
  challenge: {killed, kill_reason}, diagnosed_cause,
  evidence_verified}], survivor_reached, current_invention: {gen}}
- session["final_status"] (e.g. MECHANISM_GENERATION_FAILED,
  INVENTION_KILLED_BY_CHALLENGE, COMPLETED_UNDER_DEVELOPMENT)
- session["failed_stages"]: dict stage->reason; session["reason"]
- existing helpers (REUSE, do not re-derive): _read_json(path),
  _lineage_challenge_verdict(run_dir) -> {current_killed,
  any_kill_genuine, survivor_reached, n_kills, kill_reasons, ...} or
  None; _evidence_state(session, run_dir) -> {"n_sources": int,
  "verified": bool, ...}.

WRITE ONE NEW PUBLIC FUNCTION:

def learning_card(session, run_dir=None) -> Optional[Dict[str, Any]]:
  Returns None UNLESS terminal-scientific-no-survivor: status ==
  "COMPLETE" AND final_status in (MECHANISM_GENERATION_FAILED,
  INVENTION_KILLED_BY_CHALLENGE, EVOLVED_BUT_KILLED,
  COMPLETED_UNDER_DEVELOPMENT, UNKNOWN) AND no verified survivor
  (when a lineage exists, its survivor_reached must be False; when NO
  lineage exists, only MECHANISM_GENERATION_FAILED qualifies).
  NEVER for MALFORMED_OR_FALSE_PREMISE, never for RUN_BLOCKED_*
  (infrastructure), never when a package exists.

  Returns:
  {
    "kind": "no_survivor_learning_card",
    "what_was_tested": <1-2 sentences from the lineage: how many
       generations were explored and challenged; with NO lineage
       (MECHANISM_GENERATION_FAILED): the search reached evidence
       gathering and mechanism synthesis but produced no candidate —
       nothing was rejected>
    "strongest_failed_hypothesis": <the LAST genuine-kill generation's
       mechanism (one line) + its kill_reason; with no lineage: the
       SYNTHESIZE failure reason from failed_stages (labeled as the
       synthesis failure, never as a rejection)>
    "key_missing_evidence": <honestly derived: evidence unverified ->
       say so; n_sources == 0 -> no external evidence retrieved; else
       the recorded failure the reason field carries; if nothing is
       recorded: "the run's records do not name a specific missing
       input.">
    "ranked_next_actions": <2-3 actions, each {"rank": 1..n contiguous,
       "action_kind": "ADD_EVIDENCE" | "REFINE_PROBLEM" |
       "NEW_TERRITORY", "action": one imperative sentence, "why": one
       sentence tied to the recorded failure}; distinct kinds; ordered
       by how directly they address the recorded failure; NO outcome
       promises ("will survive"/"guarantee" forbidden)>
    "basis": <one sentence naming the records the card derives from>
  }

ALSO OUTPUT the one-line wiring for toscanini/user_state.py
user_state_view() — add "learning_card": learning_card(session,
_run_dir(session)) to its returned dict right after "outcome_label",
importing learning_card from .run_state in the existing import line
that already imports terminal_outcome. Give the exact edited return-
dict block only, as a comment after the main code block.

Style: match the module's existing comment discipline (round-tagged
comments explaining WHY, e.g. "# R472 (audit P0-4): ...").
"""


def call_atria(system: str, user: str, max_tokens: int) -> dict:
    rotations = []
    last_err = None
    for kenv in RING_KEYS:
        kval = os.environ.get(kenv, "").strip()
        if not kval:
            continue
        body = json.dumps({
            "model": "Atria-Dawn-Preview",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": max_tokens, "temperature": 0.1,
        }).encode()
        req = urllib.request.Request(
            "https://api.atria-asi.ai/v1/chat/completions", data=body,
            headers={"Authorization": f"Bearer {kval}",
                     "Content-Type": "application/json"})
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=280) as r:
                    out = json.load(r)
                ch = out["choices"][0]
                return {"finish_reason": ch.get("finish_reason"),
                        "content": ch["message"].get("content") or "",
                        "completion_tokens":
                            out.get("usage", {}).get("completion_tokens"),
                        "attempts": attempt + 1,
                        "served_by_key": kenv, "rotations": rotations}
            except Exception as exc:  # noqa: BLE001
                last_err = repr(exc)
                time.sleep(8)
        rotations.append({"key": kenv, "error": str(last_err)[:160]})
        print(f"[engineer] {kenv} failed x3 — rotating", flush=True)
    return {"finish_reason": "ERROR", "content": "",
            "completion_tokens": 0, "error": last_err,
            "rotations": rotations}


def run_task(tag: str, spec: str, context: str, max_tokens: int) -> int:
    user = ("CTO SPEC FOLLOWS.\n\n" + spec +
            "\n\nCONTEXT (current code):\n```python\n" + context +
            "\n```\n")
    print(f"[engineer {tag}] spec {len(spec)} chars, prompt {len(user)} "
          f"chars — drafting...", flush=True)
    t0 = time.time()
    res = call_atria(SYSTEM, user, max_tokens)
    # the R467 EmptyContentWithFinish remedy AND the truncated-draft
    # class: finish_reason=length means the budget ran out — escalate
    # the cap and re-draft (truncated code is unusable either way)
    if res.get("finish_reason") == "length":
        print(f"[engineer {tag}] finish=length — cap escalate",
              flush=True)
        res2 = call_atria(SYSTEM, user, max_tokens * 3)
        res2["cap_escalation"] = f"{max_tokens} -> {max_tokens * 3}"
        res2["first_attempt"] = {k: res[k] for k in
                                 ("finish_reason", "completion_tokens",
                                  "served_by_key")}
        res = res2
    dt = round(time.time() - t0, 1)
    print(f"[engineer {tag}] finish={res['finish_reason']} "
          f"tokens={res.get('completion_tokens')} key={res.get('served_by_key')} "
          f"{dt}s", flush=True)
    draft_path = OUT_DIR / f"atria_draft_{tag.lower()}.py.raw"
    draft_path.write_text(res.get("content") or "")
    rec = {"round": "R472", "session": f"engineer-{tag}",
           "task": spec.split("\n")[0].replace("CTO SPEC — ", ""),
           "spec_chars": len(spec), "prompt_chars": len(user),
           "seconds": dt, "response": res,
           "draft_saved": str(draft_path),
           "measured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                        time.gmtime())}
    with open(OUT_DIR / f"ATRIA_ENGINEER_{tag}.json", "w") as f:
        json.dump(rec, f, indent=1)
    print(f"[engineer {tag}] draft {len(res.get('content') or '')} chars "
          f"-> {draft_path.name}", flush=True)
    return 0 if res.get("content") else 1


def main() -> int:
    OUT_DIR.mkdir(exist_ok=True)
    task = sys.argv[1] if len(sys.argv) > 1 else "AB"
    rc = 0
    if "A" in task:
        driver_src = (REPO / "scripts" / "r471_prod_e2e.py").read_text()
        # only the leg-D region plus _save, keeps the prompt small
        src = driver_src[driver_src.index("_log(\"LEG D"):]
        src = src[:src.index("def _save") + 400]
        rc |= run_task("A", SPEC_A, src, 8000)
    if "B" in task:
        rs_src = (REPO / "toscanini" / "run_state.py").read_text()
        lv = rs_src[rs_src.index("def _lineage_challenge_verdict"):]
        lv = lv[:lv.index("def terminal_outcome")]
        ev = rs_src[rs_src.index("def _evidence_state"):]
        ev = ev[:ev.index("def _mechanism_state")]
        imports = "\n".join(l for l in rs_src.splitlines()[:40]
                            if l.startswith(("import ", "from ")))
        ctx = ("\n# --- _lineage_challenge_verdict (existing helper) ---\n"
               + lv
               + "\n# --- _evidence_state (existing helper, abridged) ---\n"
               + ev[:1200]
               + "\n# --- module imports ---\n" + imports)
        rc |= run_task("B", SPEC_B, "pass  # helpers per spec contracts", 12000)
    return rc


if __name__ == "__main__":
    sys.exit(main())
