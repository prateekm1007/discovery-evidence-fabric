"""Populate state transition ledger for all in-scope territories."""
import json, sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from epistemic_integrity.state_transition_ledger import StateTransitionLedger

EPISTEMIC_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[1]

# Load canonical portfolio to get territory states
with open(REPO_ROOT / "CANONICAL_STATE" / "PORTFOLIO.json") as f:
    portfolio = json.load(f)

ledger = StateTransitionLedger(EPISTEMIC_DIR / "approved_provenance")

# Record transitions for each territory
for t in portfolio.get("territories", []):
    tid = t["id"]
    state = t.get("current_state", "")
    version = t.get("frozen_at_version", t.get("current_state", "").split("_")[-1] if "_" in t.get("current_state", "") else "V1")
    commit = t.get("git_commit", "7c68f32")

    # Map common state names to versions — use frozen_at_version from PORTFOLIO.json
    frozen_version = t.get("frozen_at_version", "")
    if frozen_version:
        version = frozen_version
    elif "V6" in state:
        version = "V6"
    elif "V25" in state:
        version = "V25"
    elif "V8.8" in state or "V88" in state or "VALIDATION" in state:
        version = "V8.8"
    elif "V4" in state and "ARCHITECTURE" in state:
        version = "V4"
    elif "V3" in state and "PARTIAL" in state:
        version = "V3"
    elif "V1" in state or "DISCOVERY" in state:
        version = "V1"
    else:
        version = "V1"

    # Check if territory is in certification scope
    # CV-T02L is a narrow branch, not yet developed — mark as NOT_IN_CERTIFICATION_SCOPE
    in_scope = tid != "CV-T02L"

    if not in_scope:
        # Record as NOT_IN_CERTIFICATION_SCOPE
        ledger.record_transition(
            territory_id=tid,
            to_state="NOT_IN_CERTIFICATION_SCOPE",
            artifact_id=f"{tid}-branch",
            artifact_version="V1",
            commit_sha=commit,
            reason="Narrow branch, not yet developed. Excluded from certification scope.",
        )
    else:
        ledger.record_transition(
            territory_id=tid,
            to_state=state,
            artifact_id=f"{tid}-{version}",
            artifact_version=version,
            commit_sha=commit,
            reason=f"Initial ledger population from canonical portfolio state",
        )

# Save
ledger._save()
print(f"Ledger populated with {len(ledger.transitions)} transitions")
for tid in sorted(set(t.territory_id for t in ledger.transitions.values())):
    current = ledger.get_current_transition(tid)
    print(f"  {tid}: {current.to_state} (version={current.artifact_version})")
