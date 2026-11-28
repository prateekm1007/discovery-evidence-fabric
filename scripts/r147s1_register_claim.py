#!/usr/bin/env python3
"""r147s1 claim-before-work: register the fallback-transport panel
lane (the R147 DIR-2 order) with the honest session note."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
REG = REPO / "eval" / "work_claims.json"
CNT = REPO / "eval" / "claim_next_id.txt"
BASE = "e344a6dc7"
SESSION = "builder-r147s1"

d = json.loads(REG.read_text())
assert d.get("schema") == "work-claims/v1"
sess = d.setdefault("sessions", {})
if SESSION not in sess:
    sess[SESSION] = {
        "role": "builder",
        "note": ("R147 session-1 (the fallback-transport panel "
                 "lane): FULL-read both constitutions (EPISTEMIC @ "
                 "c3a9a6ac4, 153ac62efca36c2d; AUDITOR, "
                 "3775f869a1c19a96) + V112 before acting; vault "
                 "env-only (the owner-supplied cent key stored in "
                 "the gitignored .env.keys, never committed/printed); "
                 "secret-grep 0 live; CI on the tip SUCCESS from the "
                 "API. Lane: the R147 DIR-2 fallback — the HF free "
                 "tier DNS-blocked from the sandbox (typed transport "
                 "finding), the owner-designated cent-ai judges "
                 "probed and serving the ruling contract; the panel "
                 "resumes byte-exactly (only VALID legs skip), the "
                 "calibration caveat typed on every leg."),
        "registered_at": "2026-11-24 (sandbox clock)"}
claims = d.setdefault("claims", [])
counter_val = CNT.read_text().strip()
if any(c.get("claim_id") == counter_val
       and c.get("work_id") == "r147-panel-cent-resume"
       for c in claims):
    print("already registered:", counter_val)
    raise SystemExit(0)
lease = (datetime.now(timezone.utc)
         + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:00Z")
claims.append({
    "work_id": "r147-panel-cent-resume",
    "claim_id": counter_val,
    "role": "EXECUTOR",
    "session_id": SESSION,
    "kind": "task",
    "status": "OPEN",
    "base_sha": BASE,
    "lease_expiry": lease,
    "claimed_at": "2026-11-24 (sandbox clock)",
    "registered_at": "2026-11-24 (sandbox clock)",
    "artifact_paths": [
        "scripts/r147_panel_cent_resume.py",
        "eval/r146_p4_panel/",
        "eval/r147_transport_probe.json"],
    "one_shot": True,
    "title": (
        "R147S1 EXECUTOR (claim " + counter_val + ", base " + BASE
        + "): the R147 DIR-2 fallback — the P4 panel completion on "
        "the OWNER-DESIGNATED cent-ai judges after the HF 402 "
        "exhaustion and the free-tier DNS block. Probes: "
        "api-inference.huggingface.co unreachable from the sandbox "
        "(DNS, a network-policy block — typed, NOT a "
        "model-availability answer); cent-ai serves hy4-flash:free + "
        "deepseek-v4.1-flash + qwen3.8-flash with clean 7-key JSON "
        "rulings under the byte-identical instrument (the "
        "V112-validated prompt/parse/packs, one generation per "
        "(judge, candidate), budget escalation + 429/503 backoffs). "
        "CALIBRATION CAVEAT typed on every leg + the tally: the cent "
        "judges are NOT V109-qualified (acc/kappa UNKNOWN); the 10 "
        "dsr1 legs stand unmodified as the qualified signal; the 20 "
        "failed dsr1 legs are NOT substituted (Art. 7 — the identity "
        "awaits credit restore). Byte-resume: only VALID legs skip "
        "(the c-0252 typed fix). Acceptance: >=3 judges x 30, >=50% "
        "viable+non-obvious on the FULL set, recompute diff=0."),
})
d["claims"] = claims
CNT.write_text(f"c-{int(counter_val[2:]) + 1:04d}\n")
REG.write_text(json.dumps(d, indent=2, ensure_ascii=True) + "\n")
print(f"registered {SESSION} + claim {counter_val} "
      f"(r147-panel-cent-resume, base {BASE})")
