"""Constitution v3.0.0, Article 28 — Owner-dependency timeout (CI).

"An instrument that waits on an owner action for 3 or more rounds is
retired or replaced, and the builder lists offline work meanwhile.
Owner-gated decisions escalate, never idle."

CI check on the owner-action register (eval/owner_action_register.json):
  - the register exists and parses;
  - every tracked action carries an integer rounds_pending (>=1) and
    an escalation threshold;
  - no action may sit PENDING at >= threshold rounds without an
    ESCALATED/RESOLVED status or a retirement record (Art. 28: at 3
    rounds the instrument is retired or replaced — idling is
    forbidden);
  - RESOLVED entries keep their final round count (history is
    evidence, Art. 4).

The register's round-over-round truthfulness is report-side (the
builder updates rounds_pending each round); CI enforces the
structure and the escalation bound.
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

REGISTER = REPO / "eval" / "owner_action_register.json"


def test_article28_owner_actions_escalate_never_idle():
    reg = json.loads(REGISTER.read_text())
    actions = reg.get("actions") or []
    assert actions, "owner-action register carries no tracked actions"
    for a in actions:
        name = str(a.get("action") or "?")
        rp = a.get("rounds_pending")
        assert isinstance(rp, int) and rp >= 1, (
            f"{name}: rounds_pending must be an int >= 1, got {rp!r}")
        thr = a.get("escalate_at")
        assert thr == 3, f"{name}: escalate_at must be 3 (Art. 28)"
        status = str(a.get("status") or "")
        assert status in ("PENDING", "ESCALATED", "RESOLVED",
                          "RETIRED"), f"{name}: bad status {status!r}"
        if status == "PENDING" and rp >= thr:
            assert False, (
                f"{name}: PENDING at {rp} rounds — Art. 28 requires "
                f"retire/replace at 3, not idle")
        if status == "ESCALATED":
            assert str(a.get("escalation") or "").strip(), (
                f"{name}: ESCALATED without an escalation record")
        if status == "RETIRED":
            assert str(a.get("replacement") or "").strip(), (
                f"{name}: RETIRED without a replacement note")
    # offline work list present while actions are pending
    pending = [a for a in actions if a.get("status") == "PENDING"]
    if pending:
        assert reg.get("offline_work"), (
            "pending owner actions require an offline-work list "
            "(Art. 28)")
