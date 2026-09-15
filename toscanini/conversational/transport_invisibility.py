"""toscanini/conversational/transport_invisibility.py — R458-C1 §5:
provider failures invisible to the scientific state.

Directive (verbatim): "Make provider failures invisible to the
scientific state. Keep the provider routing layer exactly where it
belongs: TRANSPORT / CAPABILITY ↓ SCIENTIFIC ENGINE. The user should
never receive: 'Qwen provider 1 hit 403.' unless they open the
technical record. The scientific result must say: 'The requested test
could not be completed.' or: 'I continued using another verified
reasoning route.'"

This module is the ONE authority for that mapping. It is a VIEW over
canonical records (the run-owned routing ledger + the capability
gate): it holds no state, invents no fields, and derives everything
from persisted artifacts (Art. X). Two product sentences exist, and
only two:

  CASCADE_ADVANCED      a route failed AND another route then served
                        the run (the ledger's own failure→success
                        ordering) →
                        "I continued using another verified reasoning
                        route."

  ALL_ROUTES_EXHAUSTED  failures with no serving line →
                        "The requested test could not be completed."

The provider names, HTTP statuses, latency tails, and failure classes
stay in the TECHNICAL RECORD — the routing ledger, the capability
gate, the session's raw error field — surfaces the user can open
deliberately. They never appear in the product contract, the product
event stream, or any user-facing message composed through this module
(BS-009: raw machine state must not leak into the human UX; Art. LXI:
infrastructure failure is never a scientific verdict).

The scrub guard (`transport_detail_violations`) makes the boundary
mechanical: any product-surface text carrying transport plumbing
(provider ids, HTTP error codes, endpoint hosts) is a named violation,
not a style issue.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

TRANSPORT_INVISIBILITY_VERSION = "conversational/transport_invisibility/1.0.0"

#: the directive's two sentences, verbatim (the ONLY product-surface
#: transport language this module may emit)
SENTENCE_CONTINUED = ("I continued using another verified reasoning "
                      "route.")
SENTENCE_NOT_COMPLETED = "The requested test could not be completed."

#: the technical-record pointer (openable deliberately, never pushed)
TECHNICAL_RECORD_NOTE = (
    "The full technical record — providers contacted, HTTP statuses, "
    "failure classes, latencies — is preserved in the run's routing "
    "ledger and can be opened from the technical record view.")

#: transport plumbing vocabulary that must NEVER appear in
#: product-surface text (the §5 attack surface, made mechanical).
#: R462 (Art. XXXI correction, disclosed): bynara — a REGISTERED
#: provider since R461 — was missing from this vocabulary (its id
#: could leak undetected); tokenharbor joins it (the R462 probe
#: candidate; its name rides technical records and must never reach
#: the product surface either).
_PROVIDER_ID_RE = re.compile(
    r"\b(unorouter|xkiro|apinex|bai|bynara|tokenharbor|localqwen|"
    r"openrouter|nvidia|tokenrouter|anthropic|gemini|mistral|zai)\b",
    re.I)
_HTTP_ERROR_RE = re.compile(r"\bHTTP\s*(40[0-9]|41[0-9]|42[0-9]|5\d\d)"
                            r"\b|\b(40[0-9]|429|50[0-9])\s+from\b",
                            re.I)
_ENDPOINT_HOST_RE = re.compile(
    r"https?://[a-z0-9.-]+\.[a-z]{2,}", re.I)
#: R462: REGION_NOT_SERVED joins the class vocabulary (the measured
#: tokenharbor region-gate specimen — its name is technical-record
#: vocabulary, never product text); AUTH_FAILURE added alongside the
#: R458 typo AUTH_FAILED (the actual class name leaked undetected —
#: Art. XXXI correction, disclosed; assertIn-style tests unaffected).
_FAILURE_CLASS_RE = re.compile(
    r"\b(RATE_LIMITED|CREDIT_EXHAUSTED|AUTH_FAILURE|AUTH_FAILED|"
    r"PROBE_FAILED|NETWORK_FAILURE|INVALID_RESPONSE|MODEL_NOT_FOUND|"
    r"REGION_NOT_SERVED)\b")


def _read_json(p: Path) -> Optional[Dict[str, Any]]:
    try:
        if p.is_file():
            data = __import__("json").loads(p.read_text())
            return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None
    return None


def classify_transport_outcome(run_dir: Optional[Path],
                               session: Optional[Dict[str, Any]] = None
                               ) -> Dict[str, Any]:
    """Classify the transport outcome from the run's OWN records.

    NEVER a scientific verdict (Art. LXI): this classification says
    what the TRANSPORT layer did, nothing about the candidate.
    """
    rd = Path(run_dir) if run_dir else None
    ledger = _read_json(rd / "ROUTING_LEDGER_RUN.json") if rd else None
    lines = [l for l in ((ledger or {}).get("lines") or [])
             if isinstance(l, dict)]
    failed = [l for l in lines if l.get("status") != "OK"]
    succeeded = [l for l in lines if l.get("status") == "OK"]

    # cascade-advanced needs a FAILURE followed by a SUCCESS on a
    # DIFFERENT route (the rotation actually saved the run)
    cascade_advanced = False
    if failed and succeeded:
        for f_i, f in enumerate(failed):
            for s in succeeded:
                if (f.get("provider") != s.get("provider")
                        and str(f.get("recorded_at_epoch") or 0)
                        <= str(s.get("recorded_at_epoch") or 0)):
                    cascade_advanced = True
                    break
            if cascade_advanced:
                break

    n_failure_providers = sorted({l.get("provider") for l in failed
                                  if l.get("provider")})
    n_success_providers = sorted({l.get("provider") for l in succeeded
                                  if l.get("provider")})

    if cascade_advanced:
        outcome = "CASCADE_ADVANCED"
    elif failed and not succeeded:
        outcome = "ALL_ROUTES_EXHAUSTED"
    elif not lines:
        # no run-owned ledger: the capability gate / session status is
        # the authority (blocked before any call was run-owned)
        status = str((session or {}).get("status") or "")
        if status in ("RUN_BLOCKED_TRANSPORT", "RUN_BLOCKED_CAPABILITY",
                      "ERROR_TRANSPORT"):
            outcome = "ALL_ROUTES_EXHAUSTED"
        else:
            outcome = "NOT_APPLICABLE"
    else:
        outcome = "NOT_APPLICABLE"

    return {
        "outcome": outcome,
        "n_run_owned_lines": len(lines),
        "n_failed_lines": len(failed),
        "n_succeeded_lines": len(succeeded),
        # technical-record facts — NEVER for the product surface
        "technical": {
            "failing_providers": n_failure_providers,
            "serving_providers": n_success_providers,
            "failure_classes": sorted({l.get("failure_class")
                                       for l in failed
                                       if l.get("failure_class")}),
            "ledger": "ROUTING_LEDGER_RUN.json",
        },
    }


def scientific_state_message(run_dir: Optional[Path],
                             session: Optional[Dict[str, Any]] = None
                             ) -> Dict[str, Any]:
    """The product-surface transport message: one of the directive's
    two sentences + the resumability note + the technical-record
    pointer. Zero transport plumbing in the message body."""
    cls = classify_transport_outcome(run_dir, session)
    outcome = cls["outcome"]
    if outcome == "CASCADE_ADVANCED":
        message = SENTENCE_CONTINUED
    elif outcome == "ALL_ROUTES_EXHAUSTED":
        message = SENTENCE_NOT_COMPLETED
    else:
        return {"outcome": outcome, "message": None,
                "version": TRANSPORT_INVISIBILITY_VERSION}
    status = str((session or {}).get("status") or "")
    resumable = status in ("RUN_BLOCKED_TRANSPORT",
                           "RUN_BLOCKED_CAPABILITY", "INTERRUPTED")
    note = ""
    if outcome == "ALL_ROUTES_EXHAUSTED" and resumable:
        note = (" Your work is saved; the run resumes when a verified "
                "route is available.")
    return {
        "outcome": outcome,
        "message": message + note,
        "technical_record": TECHNICAL_RECORD_NOTE,
        "resumable": resumable,
        "version": TRANSPORT_INVISIBILITY_VERSION,
    }


def transport_detail_violations(text: str) -> List[str]:
    """The §5 scrub guard: name every transport-plumbing pattern found
    in product-surface text. Empty list = clean. Used by the tests as
    an adversarial attack surface and by run_contract as a runtime
    guard (a violation is a DEFECT, never silently passed through)."""
    violations: List[str] = []
    if not text:
        return violations
    if _PROVIDER_ID_RE.search(text):
        violations.append("provider-id-in-product-surface")
    if _HTTP_ERROR_RE.search(text):
        violations.append("http-error-code-in-product-surface")
    if _ENDPOINT_HOST_RE.search(text):
        violations.append("endpoint-host-in-product-surface")
    if _FAILURE_CLASS_RE.search(text):
        violations.append("failure-class-in-product-surface")
    return violations


def blocking_reason_view(session: Dict[str, Any],
                         run_dir: Optional[Path]) -> Optional[Dict[str, Any]]:
    """The product-contract INFRASTRUCTURE blocker, composed through
    this module: the scientific-state sentence in `detail`, the
    technical record as an explicit POINTER (never its content), the
    raw error retained ONLY in the session store (the technical
    surface the user opens deliberately)."""
    status = str(session.get("status") or "")
    if not (status.startswith("ERROR_") or status in (
            "RUN_BLOCKED_TRANSPORT", "RUN_BLOCKED_CAPABILITY",
            "INTERRUPTED")):
        return None
    view = scientific_state_message(run_dir, session)
    message = view.get("message")
    if message is None:
        # transport records absent (e.g. blocked before the ledger
        # existed): the directive's second sentence still applies —
        # the test could not be completed, nothing about providers
        message = SENTENCE_NOT_COMPLETED
        if status in ("RUN_BLOCKED_TRANSPORT", "RUN_BLOCKED_CAPABILITY",
                      "INTERRUPTED"):
            message += (" Your work is saved; the run resumes when a "
                        "verified route is available.")
    return {
        "kind": "INFRASTRUCTURE",
        "state": status,
        "detail": message,
        "technical_record": TECHNICAL_RECORD_NOTE,
        "resumable": status in ("RUN_BLOCKED_TRANSPORT",
                                "RUN_BLOCKED_CAPABILITY",
                                "INTERRUPTED"),
    }
