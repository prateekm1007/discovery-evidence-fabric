#!/usr/bin/env python3
"""R147S1: register the DIR-2 claim (claim-before-work, Art. 29(b)) —
the cent-ai judge path: the auditor's r147 qualification gate, then
the P4 panel completion with the qualified judges (the owner-funded
fallback; the HF Providers credits remain exhausted — HTTP 402
measured this window at e344a6dc7 preflight; api-inference
DNS-fails from the sandbox).

Claim-before-work: c-0254 (counter c-0254 -> c-0255). The panel lane
c-0252 stays OPEN (its lease covers the byte-resume panel; THIS claim
covers the qualification + the cent-ai transport legs).
"""
import json

REG = "/home/z/my-project/discovery-evidence-fabric/eval/work_claims.json"
COUNTER = "/home/z/my-project/discovery-evidence-fabric/eval/claim_next_id.txt"

with open(REG) as f:
    reg = json.load(f)
by_id = {c["claim_id"]: c for c in reg["claims"]}

assert by_id["c-0252"]["status"] == "OPEN"
assert by_id["c-0253"]["status"] == "DONE"

TS = "2026-11-24 (sandbox clock)"
SESSION = "builder-r147s1-b"
reg.setdefault("sessions", {})[SESSION] = {
    "claimed_at": TS,
    "role": "builder",
    "note": (
        "R147 window: the owner funded the cent-ai judge path "
        "(CENT_AI_API_KEY in the gitignored vault; measured working "
        "— hy4-flash:free answered OK); the auditor pre-built the "
        "r147 qualification corpus (12 balanced pairs, "
        "AUDITOR_RCAL_CORPUS_R147/1.0.0 @ audit tip f0941fc30). This "
        "lane: qualify the cent-ai judges via r147, then complete the "
        "P4 panel on the v17 strengthened set with the qualified "
        "judges (the c-0252 lane's instrument, byte-resume). "
        "Constitutions full-read verified at the DIR-1 pins."
    ),
}
reg["claims"].append({
    "work_id": "r147-centai-judge-path",
    "claim_id": "c-0254",
    "role": "EXECUTOR",
    "session_id": SESSION,
    "kind": "task",
    "status": "OPEN",
    "base_sha": "e344a6dc7",
    "lease_expiry": "2026-12-01T23:59:00Z",
    "claimed_at": TS,
    "registered_at": TS,
    "artifact_paths": [
        "eval/r147_rcal_centai/",
        "eval/r148_p4_panel_centai/",
        "scripts/r147_rcal_centai.py",
        "scripts/r148_p4_panel_centai.py",
        "scripts/r147s1b_register_claim.py",
    ],
    "title": (
        "R147S1 EXECUTOR (claim c-0254, base e344a6dc7): DIR-2 (TOP) — "
        "the owner-funded cent-ai judge path. (1) THE r147 "
        "QUALIFICATION: the auditor's fresh corpus (12 balanced "
        "pairs, 6 prefer-more-novel a1 / 6 prefer-less-novel a1, "
        "AM47 viability-necessity sealed suffix) run blind + "
        "sha-parity swap (det vote + mir stability) on the 4 "
        "cent-ai candidates (deepseek-v4-flash / qwen3.8-flash / "
        "hy4-flash:free / glm-5.3-flash, 2+ non-agnes families); "
        "gate per the corpus protocol: acc>=0.8 AND answered>=0.9 "
        "AND miss-based |over_novel-over_cons|<=1, >=3 qualified, "
        "inter-judge alpha>=0.6 (the V109 machinery: "
        "panel_agreement.rcal_qualification). (2) THE PANEL: with "
        "the qualified judges, the P4 ruling on the FULL v17 "
        "strengthened 30-candidate set (the c-0252 lane's packs — "
        "EPO problem-solution vs external prior art, blind + "
        "rotation), majority rule, >=50% bar; the pre-exhaustion "
        "dsr1 legs (10/10) stand committed as the old-instrument "
        "evidence, never merged into the new panel's tally. One "
        "generation per leg; byte-resume; no re-roll (Art. 7). "
        "HF 402 typed this window (preflight); api-inference "
        "DNS-fails; the cent-ai path is the owner-designated "
        "fallback with the auditor's qualification corpus."
    ),
    "notes": (
        "Judge identities change by owner designation (the old four "
        "are transport-dead; the auditor built r147 FOR the cent-ai "
        "candidates). The qualification record + the panel tally "
        "carry the full disclosure; the auditor verifies the gate "
        "from the raw legs."
    ),
})

with open(COUNTER) as f:
    cur = f.read().strip()
assert cur == "c-0254", f"counter unexpectedly {cur!r}"
with open(COUNTER, "w") as f:
    f.write("c-0255\n")

with open(REG, "w") as f:
    json.dump(reg, f, ensure_ascii=True, indent=2)
    f.write("\n")

print("c-0254 registered OPEN (r147-centai-judge-path); counter -> c-0255")
