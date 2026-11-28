#!/usr/bin/env python3
"""R95: register the builder-r95s1 session (Art. 29(a) identity-on-first-push)
— the CI validator caught the miss on the c-0109 push (typed, forward-only)."""
import json, datetime

NOW = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

with open("eval/work_claims.json") as f:
    reg = json.load(f)
sess = reg["sessions"]
assert "builder-r95s1" not in sess, "already registered"
sess["builder-r95s1"] = {
    "registered_at": f"{NOW} (sandbox clock, TRUE UTC)",
    "role": "builder",
    "note": "R95 session-1: continuation of the r80s1 conversation lineage "
            "(same builder lane, new context window; the r80s1 session "
            "itself remains registered — c-0105/c-0107/c-0108 its work). "
            "This session's work: the CRITIC tool-grounding lane c-0109 "
            "(discovery_fabric/engine/tool_grounded_critic.py + the 13-test "
            "CI battery, the machine's own base_scan as oracle, computed "
            "42.8% corpus correction) + the custody re-check (the sandbox "
            "recycle reverted .env.keys to the pre-bootstrap state — "
            "re-ran scripts/r77_vault_restore.py, 6 keys + HF session-only, "
            "0600, digests COMMITTED_RECORD_MATCH). Registration typed "
            "FORWARD after the CI validator caught the Art. 29(a) miss on "
            "the c-0109 push (self-caught, never silent; the claims carry "
            "this session id).",
}

with open("eval/work_claims.json", "w") as f:
    json.dump(reg, f, indent=1, ensure_ascii=False)
print("builder-r95s1 registered (Art. 29(a))")
