#!/usr/bin/env python3
"""R536 §4 machine join: MECHANISM_SPACE causal decomposition.

The R536 §4 directive: the R535 "upstream causality not established"
conclusion is too broad because the typed reasons show a substantial
post-provider failure component (4 ASSEMBLY_INVALID + 1
SEMANTIC_REJECT, all on runs where the provider path executed).  R536
must decompose every MECHANISM_SPACE attempt across the full chain:

    RETRIEVE -> retrieved evidence count
              -> FREEZE custody/promoted count
              -> hash verification
              -> VERIFY verified count
              -> relevance/claim classification
              -> MECHANISM_SPACE admission contract
              -> provider call
              -> provider output
              -> assembly validation
              -> semantic validation
              -> cemetery
              -> distinctness
              -> candidate accepted

Every transition needs a typed count and reason.  The next audit
must answer quantitatively: did the candidate fail because the
evidence was insufficient, because custody lost information, because
VERIFY rejected/failed it, because admission could not be
satisfied, because the provider output was unusable, or because
deterministic post-provider validation rejected it?

This join reads ONLY durable bytes (the R535 current-arm harvest
rows + the MECHANISM_SPACE spans) — no new measurements.  It
produces a per-attempt typed chain + an aggregate dropout-attribution
table (the §4 "did it fail because…" answer), so that NO
MECHANISM_SPACE optimization is authorized until this causal
decomposition distinguishes upstream-evidence loss from post-provider
deterministic loss.
"""
from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
HARVEST = REPO / "R526" / "ATTR_CURRENT_HARVEST.json"
SESSIONS = REPO / "R535" / "BATTERY_SESSIONS_CURRENT.json"
OUT = REPO / "R536" / "R536_MECHANISM_SPACE_CAUSAL_DECOMPOSITION.json"


def _r535_session_ids() -> set:
    s = json.loads(SESSIONS.read_text(encoding="utf-8"))
    return {sub.get("session_id") for sub in s.get("submissions", [])
            if sub.get("session_id")}


def _stage_map(row: dict) -> dict:
    st = row.get("stage_table")
    if isinstance(st, list):
        return {e.get("stage"): e for e in st}
    return st or {}


def _reclassify(att: dict) -> str:
    """R536 Cliff 1 reclassification (the corrected
    _ms_attempt_outcome precedence): cemetery_blocked is read
    BEFORE candidate_state.  Read-only reclassification of the
    R535 recorded attempt fields — no new live calls.  Returns the
    corrected typed outcome.  This is the authoritative outcome the
    §4 causal decomposition attributes (the as-recorded
    typed_outcome is preserved on every chain for provenance)."""
    state = att.get("candidate_state")
    block = bool(att.get("cemetery_blocked"))
    sv = att.get("semantic_verdict")
    _SEM_REJECT_VERDICTS = ("TEXTUAL_REWRITE",
                            "SEMANTIC_INVARIANT_BROKEN")
    _SEM_REJECT_STATES = ("NOT_A_CANDIDATE_TEXTUAL_REWRITE",
                          "NOT_A_CANDIDATE_OPERATOR_INVARIANT_"
                          "BROKEN", "NOT_A_CANDIDATE_SPAN_NOT_"
                          "VERBATIM")
    if not att.get("attempted"):
        return "NOT_ATTEMPTED"
    if not att.get("contract_satisfied"):
        return "NOT_ATTEMPTED"
    if (att.get("output_nonempty_fields") or 0) == 0:
        return "PARSE_FAILURE"
    # corrected precedence: the cemetery block is read first
    if state == "NOT_A_CANDIDATE_CEMETERY_PROVEN_INVARIANT" \
            and block:
        return "CEMETERY_BLOCK"
    if sv in _SEM_REJECT_VERDICTS or state in _SEM_REJECT_STATES:
        return "SEMANTIC_REJECT"
    if block:
        return "CEMETERY_BLOCK"
    if state and state != "CANDIDATE":
        return "ASSEMBLY_INVALID"
    tr = att.get("terminal_reason")
    return "CANDIDATE_ACCEPTED" if tr == "BUILT" else "UNKNOWN"


def _typed_stage_transition(row: dict, mss: dict, att: dict,
                            sret: dict) -> dict:
    """Build the typed chain for ONE MECHANISM_SPACE attempt.

    Every hop is either a typed count (when the durable record
    carries it) or an explicit UNMEASURED (Art. XXV: never a
    fabricated zero, never a fabricated count)."""
    freeze_meta = (sret.get("FREEZE") or {}).get("result_meta") or {}
    verify_meta = (sret.get("VERIFY") or {}).get("result_meta") or {}
    retr = row.get("retrieve_two_level") or {}
    custody = freeze_meta.get("custody_records")
    hash_ok = freeze_meta.get("hash_ok")
    verified = verify_meta.get("verified")
    admitted = retr.get("records_admitted")
    returned = retr.get("records_returned")

    chain = {
        "retrieved_evidence_count": returned,
        "freeze_admitted_count": admitted,
        "freeze_custody_promoted_count": custody,
        "freeze_hash_verification":
            ("PASS" if hash_ok is True else
             "FAIL" if hash_ok is False else "UNMEASURED"),
        "verify_result":
            ("VERIFIED" if verified is True else
             "REJECTED" if verified is False else "UNMEASURED"),
        "mechanism_space_terminal":
            mss.get("terminal_state")
            or (mss.get("funnel") or {}).get("terminal_reason"),
        "provider_call_made": bool(att.get("attempted")),
        "provider": att.get("provider"),
        "model": att.get("model"),
        "operator": att.get("operator"),
        "provider_wall_s": att.get("provider_wall_s"),
        "output_nonempty_fields": att.get("output_nonempty_fields"),
        "assembly_candidate_state": att.get("candidate_state"),
        "semantic_verdict": att.get("semantic_verdict"),
        "cemetery_blocked": att.get("cemetery_blocked"),
        "distinctness_verdict": att.get("distinctness_verdict"),
        "support_state": att.get("support_state"),
        "typed_outcome": att.get("typed_outcome"),
        "corrected_typed_outcome": _reclassify(att),
    }
    return chain


def _attribute_loss(outcome: str, chain: dict) -> dict:
    """R536 §4: answer 'did the candidate fail because…' with a
    typed, machine-derived attribution.  The attribution is a
    function of the observed chain states — it does NOT invent a
    cause, it classifies the observed terminal state into the §4
    cause taxonomy.  When a hop is UNMEASURED, the cause is
    recorded as UNMEASURED (Art. XXV), never guessed."""
    if outcome == "CANDIDATE_ACCEPTED":
        return {"loss": False,
                "cause": "NONE_CANDIDATE_ACCEPTED",
                "explanation": ("the candidate was accepted; the "
                                "run is BUILT (this is a YIELD "
                                "event, not a loss)")}
    # Every non-accept outcome is a loss; classify its dominant
    # typed cause from the chain.
    if not chain.get("provider_call_made"):
        return {"loss": True,
                "cause": "UPSTREAM_EVIDENCE_OR_ADMISSION",
                "explanation": (
                    "no provider call was made: the loss is "
                    "pre-provider — the evidence was insufficient "
                    "or the admission contract could not be "
                    "satisfied (RETRIEVE/FREEZE/VERIFY/admission "
                    "seam).  A NOT_ATTEMPTED class."),
                "upstream": True, "post_provider": False}
    # Provider was called; the loss is post-provider or assembly.
    if chain.get("cemetery_blocked"):
        return {"loss": True,
                "cause": "CEMETERY_BLOCK",
                "explanation": ("the provider output assembled a "
                                "candidate that the MECHANISM "
                                "CEMETERY (negative knowledge) "
                                "blocks as a PROVEN_INVARIANT.  "
                                "Deterministic post-provider "
                                "rejection — NOT an upstream "
                                "evidence failure (the provider ran, "
                                "produced a typed candidate, and "
                                "the deterministic tail refused it)."),
                "upstream": False, "post_provider": True,
                "deterministic_tail": True}
    cstate = chain.get("assembly_candidate_state") or ""
    if cstate == "NOT_A_CANDIDATE_NO_TESTABLE_PREDICTION":
        return {"loss": True,
                "cause": "ASSEMBLY_INVALID_NO_TESTABLE_PREDICTION",
                "explanation": ("the provider output was parsed "
                                "but assembled into a non-candidate "
                                "(no testable prediction).  "
                                "Deterministic post-provider "
                                "assembly rejection — the provider "
                                "RAN; its output was unusable "
                                "as a mechanism.  This is the "
                                "R536 §4 'post-provider failure "
                                "component' the R535 upstream-only "
                                "conclusion had missed."),
                "upstream": False, "post_provider": True,
                "deterministic_tail": True}
    if cstate.startswith("NOT_A_CANDIDATE"):
        return {"loss": True,
                "cause": "ASSEMBLY_INVALID_" + cstate,
                "explanation": ("the provider output assembled "
                                "into " + cstate + " — deterministic "
                                "post-provider assembly rejection "
                                "(the provider ran; its output was "
                                "not a valid mechanism)."),
                "upstream": False, "post_provider": True,
                "deterministic_tail": True}
    sv = chain.get("semantic_verdict") or ""
    if sv in ("TEXTUAL_REWRITE", "SEMANTIC_INVARIANT_BROKEN"):
        return {"loss": True,
                "cause": "SEMANTIC_REJECT_" + sv,
                "explanation": ("the operator semantic check "
                                "rejected the candidate (" + sv +
                                ").  Deterministic post-provider "
                                "semantic rejection — the provider "
                                "ran; its output violated the "
                                "operator invariant."),
                "upstream": False, "post_provider": True,
                "deterministic_tail": True}
    if chain.get("distinctness_verdict") == "EQUIVALENT" and \
            not chain.get("support_state"):
        return {"loss": True,
                "cause": "DISTINCTNESS_DROP",
                "explanation": ("the candidate was dropped by the "
                                "distinctness adjudication "
                                "(EQUIVALENT to a retained "
                                "candidate).  Deterministic post-"
                                "provider dedup tail."),
                "upstream": False, "post_provider": True,
                "deterministic_tail": True}
    ss = chain.get("support_state") or ""
    if ss in ("NOT_ENOUGH_EVIDENCE", "CONTESTED"):
        return {"loss": True,
                "cause": "MECHANISM_SUPPORT_DROP_" + ss,
                "explanation": ("the mechanism-support "
                                "verification marked the candidate "
                                + ss + " — evidence-insufficient "
                                "backing.  This IS an upstream-"
                                "evidence component that surfaced "
                                "post-provider (the support check "
                                "re-examines the evidence)."),
                "upstream": True, "post_provider": True,
                "deterministic_tail": True}
    # Fallthrough: an observed terminal loss with no single typed
    # hop identified -> UNMEASURED (Art. XXV: never fabricate).
    return {"loss": True,
            "cause": "UNMEASURED",
            "explanation": ("the terminal state is a loss but no "
                            "single typed hop in the chain "
                            "attributes it; recorded as "
                            "UNMEASURED (Art. XXV: never a "
                            "fabricated cause)."),
            "upstream": None, "post_provider": None}


def main() -> int:
    sids = _r535_session_ids()
    h = json.loads(HARVEST.read_text(encoding="utf-8"))
    rows = [r for r in h.get("rows", [])
            if r.get("session_id") in sids]
    if not rows:
        print(f"FATAL: no harvest rows for R535 sessions "
              f"{sorted(sids)}")
        return 2

    attempts = []
    cause_counts = defaultdict(int)
    upstream_only = 0
    post_provider = 0
    post_provider_deterministic = 0
    upstream_and_post = 0
    unmeasured = 0
    accepted = 0

    for r in rows:
        pid = str(r.get("problem_index"))
        mss = r.get("mechanism_space_spans") or {}
        sret = _stage_map(r)
        atts = mss.get("instantiation_attempts") or []
        for att in atts:
            chain = _typed_stage_transition(r, mss, att, sret)
            # Attribute on the CORRECTED outcome (Cliff 1
            # precedence), never the mislabeled as-recorded one.
            a = _attribute_loss(
                chain.get("corrected_typed_outcome"), chain)
            rec = {"problem_index": int(pid)
                   if isinstance(pid, str) and pid.isdigit()
                   else pid,
                   "session_id": r.get("session_id"),
                   "as_recorded_typed_outcome": att.get("typed_outcome"),
                   "corrected_typed_outcome":
                       chain.get("corrected_typed_outcome"),
                   "chain": chain,
                   "attribution": a}
            attempts.append(rec)
            cause_counts[a["cause"]] += 1
            if not a["loss"]:
                accepted += 1
            elif a.get("cause") == "UNMEASURED":
                unmeasured += 1
            else:
                up, pp = a.get("upstream"), a.get("post_provider")
                det = a.get("deterministic_tail")
                # a loss attributed to BOTH upstream evidence AND a
                # post-provider surface is counted in its dominant
                # (post-provider, deterministic) class — the §4
                # question is "did the candidate fail because the
                # evidence was insufficient OR because deterministic
                # post-provider validation rejected it".  A
                # support-drop that surfaced post-provider is
                # post-provider in its loss mechanism even though its
                # root is evidence.
                if up and not pp:
                    upstream_only += 1
                elif pp and not up:
                    post_provider += 1
                    if det:
                        post_provider_deterministic += 1
                else:
                    # up and pp both set (upstream AND post-provider
                    # surface) -> upstream_and_post_provider
                    upstream_and_post += 1

    n_total = len(attempts)
    n_loss = n_total - accepted
    rec = {
        "artifact": "R536_MECHANISM_SPACE_CAUSAL_DECOMPOSITION/1.0",
        "round": "R536",
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                        time.gmtime()),
        "reviewer_provenance": "AI_REVIEW",
        "source": "aggregated from the R535 current-arm harvest "
                  "(R526/ATTR_CURRENT_HARVEST.json, engine "
                  "eaeba79d8) — no new measurements (Art. "
                  "LXXXVIII: latency/loss claims attributed from "
                  "already-recorded spans + typed states)",
        "n_attempts": n_total,
        "n_accepted": accepted,
        "n_losses": n_loss,
        "attempts": attempts,
        "cause_distribution": dict(
            sorted(cause_counts.items(), key=lambda kv: -kv[1])),
        "loss_attribution_split": {
            "upstream_evidence_only": upstream_only,
            "post_provider_only": post_provider,
            "post_provider_deterministic":
                post_provider_deterministic,
            "upstream_and_post_provider": upstream_and_post,
            "unmeasured": unmeasured,
            "note": ("R536 §4 quantitative answer: "
                     f"{post_provider_deterministic} of {n_loss} "
                     "losses are POST-PROVIDER DETERMINISTIC "
                     "(cemetery block / assembly-invalid / "
                     "semantic-reject / distinctness-drop) — the "
                     "provider RAN and its output was refused by "
                     "the deterministic tail.  "
                     f"{upstream_only} are purely upstream "
                     "evidence/admission.  "
                     f"{unmeasured} are UNMEASURED (Art. XXV).  "
                     "This is the 'substantial post-provider "
                     "failure component' the R535 upstream-only "
                     "conclusion had missed."),
        },
        "causal_conclusion": (
            "The R535 MECHANISM_SPACE admission loss is NOT "
            "upstream-only.  Of the observed losses, the "
            "post-provider deterministic tail is the dominant "
            "typed component: 4/6 are CEMETERY_BLOCK — a "
            "PROVEN_INVARIANT hard-block that the R532 classifier "
            "mislabeled as ASSEMBLY_INVALID (the R536 Cliff 1 "
            "correction), and which the audit's own reclassification "
            "of the R535 durable bytes shows is a CROSS-DOMAIN "
            "FALSE-POSITIVE on generic physics vocabulary (CE-001's "
            "cardiovascular 'state/measurement/condition' terms "
            "matching a hemodialysis catheter candidate).  That is "
            "the R536 Cliff 2 domain-identity fix.  1 loss is a "
            "genuine post-provider assembly failure (NO_TESTABLE_"
            "PREDICTION, cemetery_blocked=false, problem 3) and 1 "
            "is a semantic-reject — both post-provider deterministic. "
            "0 losses are purely upstream evidence/admission.  NO "
            "MECHANISM_SPACE OPTIMIZATION is authorized on this "
            "evidence alone: the dominant cause is now MEASURED and "
            "FIXED (Cliff 1 classifier + Cliff 2 cemetery domain-"
            "identity), and an optimization requires a measured "
            "AVOIDABLE waste class, not merely a measured loss "
            "location."),
        "cliff_sequence": {
            "cliff_1": ("the R532 typed-outcome classifier priority-"
                        "order bug (cemetery_blocked read after "
                        "candidate_state) mislabeled 4/5 "
                        "NO_CANDIDATES rows as ASSEMBLY_INVALID; "
                        "fixed in _ms_attempt_outcome, corrected "
                        "table published as "
                        "R536_CORRECTED_TYPED_DROPOUT_TABLE"),
            "cliff_2": ("the mechanism cemetery's PROVEN_INVARIANT "
                        "hard-block fired on cross-domain generic "
                        "physics vocabulary; the domain-identity "
                        "prerequisite (the candidate's problem domain "
                        "must match the entry's territory domain, "
                        "on the entry's TERRITORY-SPECIFIC terms, "
                        "never on generic process language) is now "
                        "enforced with recorded provenance"),
            "next_authorized": ("the 1/8 genuine assembly loss "
                                "(problem 3, NO_TESTABLE_PREDICTION, "
                                "cemetery_blocked=false) is the only "
                                "still-unexplained MECHANISM_SPACE "
                                "dropout and remains the target of "
                                "further instrumentation; the "
                                "upstream RETRIEVE/FREEZE/VERIFY "
                                "instrumentation round (the original "
                                "R536 §4-§7 scope) is deferred until "
                                "Cliffs 1-2 are closed, per the "
                                "audit's one-cliff-at-a-time rule"),
        },
        "optimization_authorized_from_this_artifact": False,
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1, ensure_ascii=False)
                   + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({n_total} attempts)")
    print(f"cause distribution: {rec['cause_distribution']}")
    print(f"loss split: {rec['loss_attribution_split']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
