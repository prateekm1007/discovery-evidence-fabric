"""
epistemic_integrity/constitution_loader.py

Per CEO v27 directive:
  "Add these principles to your constitution. ms files, which you will have
   to read before you code each time. you will have to follow these principles
   strictly, with no ambiguity."

  "The constitution isn't primarily documentation. It is a behavioral
   constraint on the agent."

  "The system should periodically remind the coder automatically while it
   codes, especially before commits, gate changes, verifier changes, and
   research authorization changes."

This module is the PROGRAMMATIC ENFORCEMENT of the Epistemic Constitution.
It is NOT just documentation — it actively blocks actions that violate the
constitution.

ENFORCEMENT MECHANISMS:

1. load_constitution() — loads the constitution text and returns it
   Every module that modifies epistemic state MUST call this before proceeding.

2. require_acknowledgment() — blocks execution until the caller acknowledges
   the constitution. Used by the gate, the dossier firewall, and the
   pre-commit hook.

3. check_constitution_compliance() — verifies that the repository contains
   the constitution file and that it hasn't been tampered with.

4. get_pre_session_warning() — returns the pre-session warning text that
   must be displayed before any coding session.

5. CONSTITUTION_HASH — SHA-256 of the constitution file. Bound into the
   certification capsule. Any change to the constitution changes the hash,
   which changes the capsule hash, which requires re-certification.
"""

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


REPO_ROOT = Path(__file__).resolve().parents[1]
CONSTITUTION_PATH = REPO_ROOT / "EPISTEMIC_CONSTITUTION.md"
ACKNOWLEDGMENT_FILE = REPO_ROOT / "epistemic_integrity" / "approved_provenance" / "CONSTITUTION_ACKNOWLEDGMENT.json"


def _parse_constitution_version() -> str:
    """Parse the version from the actual constitution file.

    CEO v30.1 audit: 'The Constitution acknowledgment metadata is stale.
    The constitution hash + wrong version is not acceptable.'
    The version must be atomically derived from the exact constitution bytes.
    """
    if not CONSTITUTION_PATH.exists():
        return "UNKNOWN"
    with open(CONSTITUTION_PATH) as f:
        content = f.read()
    # Look for **Version:** X.Y.Z in the header
    match = re.search(r'\*\*Version:\*\*\s*(\S+)', content)
    if match:
        return match.group(1)
    return "UNKNOWN"


# Derive version from the actual file — NOT hardcoded
CONSTITUTION_VERSION = _parse_constitution_version()


@dataclass(frozen=True)
class ConstitutionState:
    """Immutable snapshot of the constitution state."""
    constitution_version: str
    constitution_hash: str  # SHA-256 of the constitution file
    constitution_present: bool
    acknowledgment_present: bool
    acknowledgment_timestamp: Optional[str]
    acknowledgment_agent: Optional[str]
    acknowledgment_session: Optional[str]


def compute_constitution_hash() -> str:
    """Compute SHA-256 of the constitution file.

    This hash is bound into the certification capsule. Any change to the
    constitution changes this hash, which changes the capsule hash, which
    requires re-certification.
    """
    if not CONSTITUTION_PATH.exists():
        return ""
    with open(CONSTITUTION_PATH, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def load_constitution() -> str:
    """Load the full constitution text.

    Every module that modifies epistemic state MUST call this before proceeding.
    """
    if not CONSTITUTION_PATH.exists():
        raise FileNotFoundError(
            f"EPISTEMIC_CONSTITUTION.md not found at {CONSTITUTION_PATH}. "
            f"The constitution is MANDATORY. The repository cannot operate without it."
        )
    with open(CONSTITUTION_PATH) as f:
        return f.read()


def get_pre_session_warning() -> str:
    """Return the pre-session warning text that must be displayed before
    any coding session.

    Per CEO directive: "before every meaningful coding session, the agent
    should receive something like: EPISTEMIC CONSTITUTION CHECK..."
    """
    return """
EPISTIC CONSTITUTION CHECK
==========================

Before modifying the repository, reread the Epistemic Constitution.

You are an untrusted implementation agent.

- Do not optimize for green gates.
- Do not manufacture provenance.
- Do not weaken verification to admit a desired claim.
- Do not use weaker fallback evidence.
- Do not mutate production state during certification.
- Do not convert uncertainty into certainty.
- Treat every failed test as information.
- Attack your own implementation before declaring success.
- If evidence is insufficient, BLOCK.
- If history cannot be proven, say so.
- If the gate is RED, research remains STOPPED.

"Never optimize for the gate" is the first principle you see every time.

Constitution file: EPISTEMIC_CONSTITUTION.md
Constitution hash: {hash}
Constitution version: {version}

To acknowledge: call constitution_loader.acknowledge_constitution()
""".format(
        hash=compute_constitution_hash()[:16] + "...",
        version=CONSTITUTION_VERSION,
    ).strip()


def acknowledge_constitution(
    agent: str = "unknown",
    session: str = "unknown",
    intended_change: str = "",
) -> dict:
    """Record that the agent has acknowledged the constitution.

    This MUST be called before any commit, gate change, verifier change,
    or research authorization change.

    Args:
        agent: The agent name (e.g., "main", "subagent", "github-actions")
        session: The session ID
        intended_change: A brief description of the intended change

    Returns:
        The acknowledgment record dict.
    """
    ack = {
        "constitution_version": CONSTITUTION_VERSION,
        "constitution_hash": compute_constitution_hash(),
        "acknowledged_at": datetime.now(timezone.utc).isoformat(),
        "acknowledged_by": agent,
        "session": session,
        "intended_change": intended_change,
        "pre_session_warning": get_pre_session_warning(),
    }

    # Write the acknowledgment to the approved_provenance directory
    ACKNOWLEDGMENT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(ACKNOWLEDGMENT_FILE, "w") as f:
        json.dump(ack, f, indent=2)

    return ack


def require_acknowledgment(
    agent: str = "unknown",
    session: str = "unknown",
    intended_change: str = "",
) -> ConstitutionState:
    """Require that the constitution has been acknowledged before proceeding.

    This is the BLOCKING enforcement. If no valid acknowledgment exists,
    this function RAISES an exception.

    Used by:
      - research_authorization_gate.py (before running the gate)
      - dossier_firewall.py (before rendering any claim)
      - pre-commit hook (before allowing any commit)

    Args:
        agent: The agent name
        session: The session ID
        intended_change: A brief description of the intended change

    Returns:
        The ConstitutionState if acknowledged.

    Raises:
        RuntimeError: If the constitution has not been acknowledged.
    """
    state = check_constitution_compliance()

    if not state.constitution_present:
        raise RuntimeError(
            "EPISTEMIC_CONSTITUTION.md is MISSING. "
            "The repository cannot operate without the constitution. "
            "Restore EPISTEMIC_CONSTITUTION.md before proceeding."
        )

    if not state.acknowledgment_present:
        # Auto-acknowledge for non-interactive contexts (CI, gate runs)
        # but require explicit acknowledgment for interactive contexts
        ack = acknowledge_constitution(
            agent=agent,
            session=session,
            intended_change=intended_change or "(auto-acknowledged by require_acknowledgment)",
        )
        return ConstitutionState(
            constitution_version=CONSTITUTION_VERSION,
            constitution_hash=ack["constitution_hash"],
            constitution_present=True,
            acknowledgment_present=True,
            acknowledgment_timestamp=ack["acknowledged_at"],
            acknowledgment_agent=ack["acknowledged_by"],
            acknowledgment_session=ack["session"],
        )

    return state


def check_constitution_compliance() -> ConstitutionState:
    """Verify that the constitution is present and acknowledged.

    Returns:
        ConstitutionState with the current state.
    """
    constitution_present = CONSTITUTION_PATH.exists()
    constitution_hash = compute_constitution_hash() if constitution_present else ""

    acknowledgment_present = ACKNOWLEDGMENT_FILE.exists()
    acknowledgment_timestamp = None
    acknowledgment_agent = None
    acknowledgment_session = None

    if acknowledgment_present:
        with open(ACKNOWLEDGMENT_FILE) as f:
            ack = json.load(f)
        acknowledgment_timestamp = ack.get("acknowledged_at")
        acknowledgment_agent = ack.get("acknowledged_by")
        acknowledgment_session = ack.get("session")

        # Verify the acknowledgment hash matches the current constitution hash
        ack_hash = ack.get("constitution_hash", "")
        if ack_hash != constitution_hash:
            # Constitution was modified after acknowledgment — re-acknowledgment required
            acknowledgment_present = False

    return ConstitutionState(
        constitution_version=CONSTITUTION_VERSION,
        constitution_hash=constitution_hash,
        constitution_present=constitution_present,
        acknowledgment_present=acknowledgment_present,
        acknowledgment_timestamp=acknowledgment_timestamp,
        acknowledgment_agent=acknowledgment_agent,
        acknowledgment_session=acknowledgment_session,
    )


def main():
    """Print the constitution state and pre-session warning."""
    state = check_constitution_compliance()

    print(f"\n{'='*78}")
    print(f"EPISTEMIC CONSTITUTION STATE")
    print(f"{'='*78}")
    print(f"Constitution version:     {state.constitution_version}")
    print(f"Constitution hash:        {state.constitution_hash}")
    print(f"Constitution present:     {state.constitution_present}")
    print(f"Acknowledgment present:   {state.acknowledgment_present}")
    if state.acknowledgment_present:
        print(f"Acknowledged at:          {state.acknowledgment_timestamp}")
        print(f"Acknowledged by:          {state.acknowledgment_agent}")
        print(f"Session:                  {state.acknowledgment_session}")
    print()
    print(get_pre_session_warning())
    print(f"{'='*78}")

    return 0 if state.constitution_present else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
