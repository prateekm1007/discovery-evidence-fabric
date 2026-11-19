#!/usr/bin/env python3
"""R95: stake claim c-0109 (Art. 29(b) claim-before-work) — the CRITIC
tool-grounding lane (AM80 direction 1 / AM82 worldwide update 3 / the
c-0106 root cause's named fix): a deterministic tool-grounded CORRECTOR
that fixes the prompt-refractory finding classes mechanically at
generation time instead of flagging them for another prompt round."""
import json, datetime

HEAD = "e660ae71b"
NOW = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

claim = {
    "claim_id": "c-0109",
    "claimed_at": f"{NOW} (sandbox clock, TRUE UTC)",
    "registered_at": f"{NOW} (sandbox clock, TRUE UTC)",
    "work_id": "critic-tool-grounding-dev",
    "title": "AM80 direction 1 DEV mechanics (builder-r95s1): the CRITIC "
             "tool-grounding corrector — engine-native module "
             "discovery_fabric/engine/tool_grounded_critic.py that "
             "mechanically CORRECTS the prompt-refractory finding classes "
             "at generation time instead of flagging for another prompt "
             "round (the c-0106 root cause: reflection improves the "
             "surface but cannot zero structural formatting defects at "
             "budget 3; the ablation's named next leverage is CRITIC "
             "tool-grounding). Legs: (1) the BILL tagger — the same "
             "detection as the frozen machine's base_scan "
             "(scripts/r22_a1w_v5_repair.py, called at "
             "r40_machine_v77.py:484 on every attempt) finds "
             "IMPLEMENTATION-BILL rows lacking the literal (a)/(b)/(c) "
             "procurement tag, classifies each row by TYPED keyword rules "
             "derived from the scan's own directive definitions ((a) "
             "already-present infrastructure, (b) procurable catalog "
             "item, (c) parameter/duty/procedure change), and appends the "
             "tag mechanically — CONSERVATIVE: rows matching multiple "
             "classes or no class stay untagged and flagged (never a "
             "guessed tag), rows tagged in the non-scannable '(Tag: x)' "
             "format are normalized to the scannable format; (2) the "
             "chemistry-direction corrector — on the c-0107 computed "
             "INVERTED verdict for a typed-pair claim, the direction word "
             "is rewritten mechanically on the matched span (typed pair "
             "CO->CO2 only, conservative). CI-wired deterministic battery "
             "with the REAL r22 scan as oracle (corrected answers must "
             "scan CLEAN on the BILL_UNTAGGED leg). Attribution: CRITIC "
             "(microsoft, ICLR23 pattern) + CriticEval (MIT) per AM82 "
             "worldwide update 3; ChemMCP/CACTUS already attributed. "
             "NO frozen bytes touched (adoption-gated; the machine-side "
             "wiring + its live ablation are the typed next steps, the "
             "c-0106 lane pattern: fixture mechanics -> CI-gated "
             "adoption).",
    "status": "OPEN",
    "session_id": "builder-r95s1",
    "role": "EXECUTOR",
    "kind": "task",
    "base_sha": HEAD,
    "lease_expiry": "2026-11-21T23:59:00Z",
    "takes_over": None,
    "artifact_paths": [
        "discovery_fabric/engine/tool_grounded_critic.py",
        "tests/test_r95_tool_grounded_critic.py",
        "NOTICE.md",
    ],
    "notes": "Art. 29(b): claimed BEFORE any work byte. Lane division: "
             "c-0106 (peer, executor-complete awaiting verifier) untouched; "
             "c-0107/c-0108 (mine, DONE+verified) are the read-only "
             "computation legs this module composes. Collision check: "
             "c-0109 free; no competing claim on the tool-grounding lane.",
    "no_problem_read_before_claim": True,
}

with open("eval/work_claims.json") as f:
    reg = json.load(f)
claims = reg["claims"] if isinstance(reg, dict) and "claims" in reg else reg
ids = [str(c.get("claim_id")) for c in claims]
assert "c-0109" not in ids, "c-0109 already staked — race!"
claims.append(claim)
if isinstance(reg, dict):
    reg["claims"] = claims
with open("eval/work_claims.json", "w") as f:
    json.dump(reg, f, indent=1, ensure_ascii=False)
print(f"c-0109 staked OPEN at base {HEAD} — claims now {len(claims)}")
