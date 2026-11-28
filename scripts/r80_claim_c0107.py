#!/usr/bin/env python3
"""R80: stake claim c-0107 (Art. 29(b) claim-before-work, correctly FIRST
this time) — the generation-side COMPUTED-equilibrium chemistry check lane
(AM80 direction 3 / AM81 ChemMCP+CACTUS complement): Cantera equilibrate()
verifies claimed chemistry directions against COMPUTED equilibrium instead
of guessed prose. Non-frozen, adoption-gated, zero LLM."""
import json, datetime

HEAD = "835760c08"
NOW = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

claim = {
    "claim_id": "c-0107",
    "claimed_at": f"{NOW} (sandbox clock, TRUE UTC)",
    "registered_at": f"{NOW} (sandbox clock, TRUE UTC)",
    "work_id": "chemistry-computed-equilibrium-dev",
    "title": "AM80 direction 3 DEV prototype (builder-r80s1): the "
             "generation-side COMPUTED-equilibrium direction check — Cantera "
             "(BSD-3-Clause, NOTICE row added) equilibrate() computes the "
             "equilibrium composition and the claimed direction of a "
             "stated chemistry effect is verified AGAINST THE COMPUTED "
             " SIGN (kill the inversion class at the source, the "
             "registry-scan HO10-03 legs get a computed complement; "
             "ChemMCP Apache-2.0 + CACTUS BSD-2 attributed as planned "
             "pattern copies per AM81). Deliverables: scripts/"
             "r80_chemistry_equilibrium.py (the computed-direction engine "
             "+ a CONSERVATIVE prose-claim extractor, fail-open to "
             "silence on ambiguity exactly like the committed "
             "scan_equilibrium_direction contract), CI-wired deterministic "
             "tests tests/test_r80_chemistry_equilibrium.py on "
             "CANTERA-SHIPPED mechanisms (gri30 legs: oxidant-excess, "
             "T-up endothermic forward, T-up exothermic dissociation, "
             "flat/ambiguous typed UNVERIFIABLE, determinism, zero-network, "
             "freeze parity). NO frozen bytes touched (adoption-gated, the "
             "c-0106 lane owns the frozen-machine convergence wiring); "
             "NO invented thermo data (only cantera-shipped mechanisms in "
             "CI; the Ti-class species-level computed check needs a "
             "custody-verified Ti/Cl mechanism — typed follow-up, the "
             "registry scan keeps covering Ti legs until then).",
    "status": "OPEN",
    "session_id": "builder-r80s1",
    "role": "EXECUTOR",
    "kind": "task",
    "base_sha": "835760c08",
    "lease_expiry": "2026-11-20T23:59:00Z",
    "takes_over": None,
    "artifact_paths": [
        "scripts/r80_chemistry_equilibrium.py",
        "tests/test_r80_chemistry_equilibrium.py",
        "NOTICE.md",
    ],
    "notes": "Art. 29(b): claimed BEFORE any work byte. Lane division "
             "typed: c-0106 (builder-r93s1, OPEN, in flight) owns the "
             "convergence live-ablation + frozen-machine wiring lane; this "
             "claim does NOT touch the convergence layer, the frozen "
             "machine, or the c-0106 artifacts. Collision check: c-0107 "
             "free; no competing claim on the chemistry lane; the "
             "registry scan module (scripts/r70_stated_formula_scan.py) is "
             "read-only referenced, not edited.",
    "no_problem_read_before_claim": True,
}

with open("eval/work_claims.json") as f:
    reg = json.load(f)
claims = reg["claims"] if isinstance(reg, dict) and "claims" in reg else reg
ids = [str(c.get("claim_id")) for c in claims]
assert "c-0107" not in ids, "c-0107 already staked — race!"
claims.append(claim)
if isinstance(reg, dict):
    reg["claims"] = claims
with open("eval/work_claims.json", "w") as f:
    json.dump(reg, f, indent=1, ensure_ascii=False)
print(f"c-0107 staked OPEN at base {HEAD} — claims now {len(claims)}")
