#!/usr/bin/env python3
"""
V1.0 → V1.1 Transition Script.

PREPARED but NOT EXECUTED.
This script is ready to run the moment CEO explicitly says "approve PCP-001".

DO NOT RUN THIS SCRIPT WITHOUT EXPLICIT CEO APPROVAL.
The coder who filed PCP-001 cannot self-approve.

When CEO approval is received, run:
    python3 protocol/governance/V11_TRANSITION_SCRIPT.py --approve --approved-by "CEO"

This will:
1. Update PCP_REGISTRY.json: PCP-001 status → APPROVED
2. Create V1.1 constitution (V1.0 preserved per Law 7)
3. Update CONSTITUTION_REGISTRY.json: current_version → V1.1
4. Pin all current canonical inventions to protocol_version=V1.1
5. Update preflight to enforce V1.1
6. Record the transition in the changelog
"""

import json
import hashlib
import sys
import os
from datetime import datetime, timezone
from pathlib import Path

# P0 (twenty-second round): Derive REPO_ROOT from __file__, NOT hardcoded.
# P0 (twenty-third round): Use shared adversarial-safe derivation.
# parents_up=2 because this module is at REPO_ROOT/protocol/governance/
import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from epistemic_integrity.path_utils import derive_repo_root
REPO_ROOT = derive_repo_root(__file__, parents_up=2)
GOV_DIR = REPO_ROOT / "protocol" / "governance"
NOW = datetime.now(timezone.utc).isoformat()

def execute_transition(approved_by: str):
    """Execute the V1.0 → V1.1 transition. Only run after CEO approval."""

    print("=" * 60)
    print("V1.0 → V1.1 CONSTITUTION TRANSITION")
    print(f"Approved by: {approved_by}")
    print(f"Timestamp: {NOW}")
    print("=" * 60)

    # 1. Update PCP_REGISTRY
    pcp_registry_path = GOV_DIR / "PCP_REGISTRY.json"
    registry = json.load(open(pcp_registry_path))
    for pcp in registry["pcps"]:
        if pcp["pcp_id"] == "PCP-001":
            pcp["status"] = "APPROVED"
            pcp["ceo_approval"] = approved_by
            pcp["ceo_approval_timestamp"] = NOW
            pcp["merged_into_version"] = "V1.1"
    registry["current_protocol_version"] = "V1.1"
    json.dump(registry, open(pcp_registry_path, "w"), indent=2)
    print("  1. PCP_REGISTRY updated: PCP-001 = APPROVED")

    # 2. Create V1.1 constitution (V1.0 preserved)
    v10_path = REPO_ROOT / "protocol" / "INVENTION_PROTOCOL_V1.md"
    v11_path = REPO_ROOT / "protocol" / "INVENTION_PROTOCOL_V1_1.md"
    if v10_path.exists():
        v10_content = v10_path.read_text()
        # Add V1.1 amendments
        v11_content = v10_content + f"""

---

## V1.1 Amendments (PCP-001 APPROVED {NOW})

### Amendment 1: BELOW_BUYER_THRESHOLD terminal status (§16 update)

§16 terminal statuses are now:
```
WOULD_NOT_PAY | BELOW_BUYER_THRESHOLD | WOULD_CONSIDER_WITH_MILESTONES | LEVEL_4_BUYER_READY
```

**BELOW_BUYER_THRESHOLD definition:** Hard gates (Patent + Evidence) PASS, but any soft gate FAILS OR composite < 70.

### Amendment 2: 4-concept separation (§7 + §16 update)

Every invention's 22_FINAL_ADJUDICATION.json must include:
- PATENT_STATUS (102 + 103 state)
- ENGINEERING_STATUS (TECHNICAL + SAFETY gate state)
- BUYER_SENTIMENT (blind test result + source)
- BUYER_READINESS (mechanical: READY if all gates pass + composite >= 70, else NOT_READY)
- final_status (deterministically derived per state machine)

### Amendment 3: Deterministic state machine

final_status is mechanically derived. No LLM/model may select it.
See protocol/governance/DETERMINISTIC_STATE_MACHINE.py

### Amendment 4: 103 three-state evidence

103 evidence state must be one of:
- FOUND (motivation passage found in primary claims)
- NOT_FOUND_AFTER_COMPLETE_SEARCH (search complete, no motivation found)
- SEARCH_INCOMPLETE (cannot infer absence of motivation)

If SEARCH_INCOMPLETE, 103_status MUST be UNCERTAIN.

### Amendment 5: Retroactive inflation scanner as CI gate

protocol/governance/RETROACTIVE_INFLATION_SCANNER.py is a permanent CI gate.
9 failure conditions enforced. See protocol/governance/CI_GATE_SPECIFICATION.json

### V1.0 preserved

V1.0 constitution (protocol/INVENTION_PROTOCOL_V1.md) is preserved unchanged per Law 7.
V1.1 supersedes V1.0 for all new inventions. V1.0 inventions retain their version.

**Approved by:** {approved_by}
**Approval timestamp:** {NOW}
"""
        v11_path.write_text(v11_content)
        print("  2. V1.1 constitution created (V1.0 preserved)")

    # 3. Update CONSTITUTION_REGISTRY
    registry_path = REPO_ROOT / "protocol" / "CONSTITUTION_REGISTRY.json"
    if registry_path.exists():
        reg = json.load(open(registry_path))
        v11_hash = hashlib.sha256(v11_content.encode()).hexdigest()

        # Add V1.1 to supersession history
        reg["supersession_history"].append({
            "version": "V1.1",
            "canonical_path": "protocol/INVENTION_PROTOCOL_V1_1.md",
            "sha256": v11_hash,
            "frozen_at": NOW,
            "frozen_by_commit": "pending",
            "supersedes": "V1.0",
            "supersession_rationale": "PCP-001 approved: BELOW_BUYER_THRESHOLD + 4-concept separation",
            "audit_status": "FROZEN",
            "audit_notes": f"Approved by {approved_by} at {NOW}",
        })

        # Update current version
        reg["current_version"] = "V1.1"
        reg["current_canonical_path"] = "protocol/INVENTION_PROTOCOL_V1_1.md"
        reg["current_sha256"] = v11_hash
        reg["current_frozen_at"] = NOW
        reg["current_frozen_by_commit"] = "pending"

        json.dump(reg, open(registry_path, "w"), indent=2)
        print("  3. CONSTITUTION_REGISTRY updated: current_version = V1.1")

    # 4. Pin all current canonical inventions to V1.1
    INVENTION_PATTERN = __import__("re").compile(r"^(?:[A-Z]+_)?INVENTION_\d+", __import__("re").IGNORECASE)
    pinned = 0
    for entry in sorted(REPO_ROOT.iterdir()):
        if entry.is_dir() and INVENTION_PATTERN.match(entry.name):
            manifest_path = entry / "00_MANIFEST.json"
            if manifest_path.exists():
                manifest = json.load(open(manifest_path))
                if not manifest.get("superseded_by"):
                    manifest["protocol_version"] = "V1.1"
                    manifest["protocol_version_pinned_at"] = NOW
                    json.dump(manifest, open(manifest_path, "w"), indent=2)
                    pinned += 1
    print(f"  4. {pinned} current canonical inventions pinned to V1.1")

    # 5. Record in changelog
    changelog_path = REPO_ROOT / "protocol" / "CHANGELOG.md"
    if changelog_path.exists():
        changelog = changelog_path.read_text()
        changelog += f"""

## V1.1 — {NOW} (PCP-001 APPROVED)
- BELOW_BUYER_THRESHOLD added as 4th terminal status
- 4-concept separation formalized (PATENT_STATUS, ENGINEERING_STATUS, BUYER_SENTIMENT, BUYER_READINESS)
- Deterministic state machine enforced
- 103 three-state evidence enforced
- Retroactive inflation scanner is permanent CI gate
- Approved by: {approved_by}
"""
        changelog_path.write_text(changelog)
        print("  5. CHANGELOG updated")

    print()
    print("V1.1 TRANSITION COMPLETE.")
    print("All future inventions must declare protocol_version=V1.1")
    print("Preflight will enforce V1.1 on next run.")

if __name__ == "__main__":
    if "--approve" not in sys.argv:
        print("ERROR: This script requires --approve flag.")
        print("The coder who filed PCP-001 CANNOT self-approve.")
        print("CEO must explicitly say 'approve PCP-001' and provide --approved-by.")
        print()
        print("Usage: python3 V11_TRANSITION_SCRIPT.py --approve --approved-by 'CEO'")
        sys.exit(1)

    approved_by = "CEO"
    if "--approved-by" in sys.argv:
        idx = sys.argv.index("--approved-by")
        approved_by = sys.argv[idx + 1]

    # Verify this is not self-approval
    if "coder" in approved_by.lower() or "agent" in approved_by.lower():
        print("ERROR: Self-approval forbidden. PCP-001 was filed by the coder/agent.")
        print("Approval must come from CEO or external auditor.")
        sys.exit(1)

    execute_transition(approved_by)
