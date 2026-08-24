# Round 274 Audit — Kill False Causal Paradigm Claims + Gate Q Upgrade

**Task ID:** R274-GATE-Q-UPGRADE-KILLS
**Agent:** main (CTO, Super Z)
**Date:** 2026-08-24

---

## P0 — Both "New Causal Paradigm" Claims Are False

### CM-01: Osmotic-Pressure Valve → DOWNGRADED to WATCH

**CEO found:** US20020087111 (implantable shunt device with osmotic pressure controlling valve opening pressure — glaucoma drainage implant). Also US20040267187A1 (self-adjusting hydrocephalus valve).

**The functional equivalence that killed the claim:**
- Original: "CSF osmolarity → water flux → valve displacement → hydraulic resistance"
- Functional equivalent: "Osmotic pressure → chamber pressure → mechanical displacement → valve opening → hydraulic control"
- **FOUND in US20020087111.** The "new causal paradigm" is a novel DESCRIPTION of a known mechanism.

### CM-03: Feed-Forward Production-Matched Drainage → PRIOR_ART_THREATENED / LIKELY KILL

**CEO found:** US12636471 (May 2026 — programmable CSF metering shunt that measures/estimates CSF production rate and uses it to adjust shunt performance). Also US20220265974 (2022 application for same).

**The functional equivalence that killed the claim:**
- Original: "CSF production rate → flow signature → drainage matched to production → ICP stability"
- Functional equivalent: "Production measurement/estimation → control parameter → drainage adjustment"
- **FOUND in US12636471.** The "new control paradigm" is directly claimed in a 2026 patent.

**Critical lesson:** The most dangerous prior art was VERY RECENT (May 2026). The old-art shock test (search back 20-30 years) missed it because it was looking for old art, not recent art.

---

## P1 — Gate Q Upgraded to Functional Equivalence

| Old Gate Q | New Gate Q |
|---|---|
| "Has this exact causal chain been demonstrated in ANY field?" | "Has any system demonstrated a FUNCTIONALLY EQUIVALENT causal transformation that produces SUBSTANTIALLY THE SAME technical effect?" |

**The expansion rule:**
1. Write the candidate's causal chain in SPECIFIC terminology
2. Replace each specific term with its FUNCTIONAL EQUIVALENT (what does it DO, not what is it CALLED?)
3. Search for the functional-equivalent chain across ALL fields
4. If ANY functionally equivalent chain is found → NOT novel → default WATCH
5. Only if NO functionally equivalent chain exists → novel → proceed

This brings Gate Q into alignment with the functional-equivalence principle already used in Gates D and M.

---

## P2 — Recent-Art Shock Test

Mandatory 2024-2026 search before Level 1. CM-03 was killed by a May 2026 patent that old-art shock missed.

**Both shock tests are now mandatory:**
- Old-art shock (R258): search back 20-30 years for underlying physical principle
- Recent-art shock (R274): search last 24 months for direct competitors

---

## P3 — Negative-Search Provenance

For every "NOT FOUND" claim, the engine MUST record:
1. Query (exact search terms)
2. Database (where searched)
3. Date of search
4. Documents returned (count)
5. Documents excluded (count)
6. Documents retained (count)
7. Reason for exclusion

Without this, "0/10 domains found" is not auditable. The CEO repeatedly found prior art the engine missed because the searches were too narrow. Negative-search provenance makes the search verifiable.

---

## The Repeated Pattern (R268 → R274)

| Round | What happened | Root cause |
|---|---|---|
| R268 | SC-05 killed (concept not mechanism) | Assessed at concept level, not element level |
| R269 | SC-05 killed (3 prior-art sources) | Searched medical terms, missed functional equivalents |
| R272 | 5 INVEST all downgraded | CEO found prior art for all 5 using different terminology |
| R274 | CM-01, CM-03 killed | "New causal paradigm" was novel DESCRIPTION of known mechanism |

**Root cause:** The engine searches for the candidate's SPECIFIC TERMINOLOGY, not its FUNCTIONAL EQUIVALENT. "Osmolarity valve" ≠ "osmotic pressure valve" in the engine's search, but they are functionally identical. "Feed-forward production matching" ≠ "production estimation drainage control" in the engine's search, but they are functionally identical.

**The fix:** Gate Q now uses functional equivalence (P1). Recent-art shock catches 2024-2026 patents (P2). Negative-search provenance makes searches auditable (P3).

---

## Updated Portfolio

| Status | Count |
|---|---|
| INVEST | **0** |
| WATCH | 16 |
| PRIOR_ART_THREATENED | 2 (CM-01, CM-03) |
| BLOCKED | 1 (SC-F) |
| Cemetery | 23 |
| Level 2 | **0** |
| Sellable | **0** |
| Transactions | **$0** |

---

## Artifacts Produced

| Artifact | Path | Size |
|---|---|---|
| Gate Q upgrade + kills | `CANONICAL_STATE/R274_GATE_Q_UPGRADE_AND_KILLS.json` | 14,887 bytes |
| This Audit | `CANONICAL_STATE/ROUND_274_AUDIT.md` | (this file) |
| Script | `scripts/r274_gate_q_upgrade_kills.py` | (in /home/z/my-project/scripts/) |
