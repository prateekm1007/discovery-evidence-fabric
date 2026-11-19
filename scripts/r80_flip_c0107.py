#!/usr/bin/env python3
"""R80: flip c-0107 OPEN->DONE on completion (module + CI-wired tests +
workflow wiring + NOTICE attribution all landed)."""
import json, datetime

NOW = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

with open("eval/work_claims.json") as f:
    reg = json.load(f)
claims = reg["claims"] if isinstance(reg, dict) and "claims" in reg else reg
c = next(x for x in claims if str(x.get("claim_id")) == "c-0107")
assert str(c.get("status")).upper() == "OPEN", "c-0107 not OPEN"
c["status"] = "DONE"
c["completed_at"] = f"{NOW} (sandbox clock, TRUE UTC)"
c["completion_note"] = (
    "DONE: the computed-equilibrium chemistry prototype is landed and green "
    "— (1) scripts/r80_chemistry_equilibrium.py: the computed-direction "
    "engine (equilibrate() at both levels, dilution-free X[target]/X[source] "
    "signal — the mole-fraction comparison was REJECTED on computed evidence "
    "(excess O2 lowers the CO2 mole fraction purely by dilution while "
    "conversion rises; scripts/r80_chem_sanity.py), the verdict engine "
    "CONSISTENT/INVERTED/UNVERIFIABLE fail-open, and the CONSERVATIVE prose "
    "extractor (excess-oxidant + explicit direction on the typed CO->CO2 "
    "pair only; anything ambiguous stays silent, the registry-scan "
    "contract); (2) tests/test_r80_chemistry_equilibrium.py: 12 CI-wired "
    "deterministic tests — every expected sign COMPUTED FIRST (sanity "
    "script) then baked in, never assumed: oxidant-excess leg (the "
    "STRUCTURE of the volatile-chloride inversion), T-up endothermic "
    "(SMR CO +45.8%), T-up exothermic dissociation (CO up ~1500x, CO2 down "
    "24%), flat threshold (H2O 1K step, -0.00006% -> UNVERIFIABLE), "
    "fail-open on bad claims, prose extraction consistent+inverted+silent "
    "cases, determinism, freeze parity (15 baselines), zero-network; (3) "
    "CI wiring additive: the suite joins the queue-surface invocation list "
    "+ cantera joins the Install test deps step (the c-0066 pint "
    "precedent); (4) NOTICE.md: Cantera BSD-3-Clause dependency row + "
    "ChemMCP Apache-2.0 / CACTUS BSD-2 planned-copies (AM81). Typed scope: "
    "the Ti-Cl species-level computed check needs a custody-verified Ti/Cl "
    "mechanism (no invented thermo data) — the registry scan keeps "
    "covering those legs (TI_CLASS_SCOPE_NOTE in the module). NO frozen "
    "bytes touched; adoption-gated like the convergence lane. Lane "
    "discipline: c-0106 (peer) untouched. 34/34 tests green across the "
    "three convergence+chemistry suites.")

if isinstance(reg, dict):
    reg["claims"] = claims
with open("eval/work_claims.json", "w") as f:
    json.dump(reg, f, indent=1, ensure_ascii=False)
print("c-0107 OPEN->DONE")
