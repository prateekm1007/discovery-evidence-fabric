# Production Adversarial Call Graph

## Single Production Entry Point

All production adversarial evaluation flows through ONE module:

```
discovery_fabric/a2/adversarial.py
  └── adversarial_challenge(candidate, evidence_verified, prior_art_state)
        ├── V4 Correction 11: skip_if_evidence_failed()
        │     └── if evidence fails → NOT_RUN, no LLM call
        ├── LLM adversarial challenge (llm_chat)
        ├── V4 Correction 10: enforce_prior_art_firewall()
        │     └── non-kill states → PRIOR_ART=KILL overridden to SURVIVE
        ├── V4 Correction 5+9: evaluate_boundary_condition()
        │     └── no external evidence → INSUFFICIENT_EVIDENCE, not KILL
        ├── V4 Correction 6: check_adversarial_invalid()
        │     └── verdict/reason conflict → ADVERSARIAL_INVALID, not KILL
        └── corrected dimension verdicts → AIC gate
```

## V4 Corrections (Authoritative Implementation)

All corrections are imported from ONE module:

```
discovery_fabric/v4_corrections.py
  ├── skip_if_evidence_failed()          → wraps check_evidence_gate_before_adversarial()
  ├── evaluate_boundary_condition()       → wraps validate_boundary_evidence() + boundary_prefilter()
  ├── enforce_prior_art_firewall()
  ├── check_adversarial_invalid()
  ├── NON_KILL_PRIOR_ART_STATES           → {TOPICAL_RELATED, POSSIBLE_RELEVANCE, NO_MATCH_FOUND, UNRESOLVED}
  └── KILL_PRIOR_ART_STATES               → {SPECIFIC_DISCLOSURE, IDENTICAL_OR_NEAR_IDENTICAL_DISCLOSURE}
```

## Callers (Production Paths)

All production callers import from `discovery_fabric.a2.adversarial`:

| Caller | Import | Status |
|--------|--------|--------|
| `discovery_fabric/a2/run.py` | `from discovery_fabric.a2.adversarial import adversarial_challenge` | ✅ Production (A2 pipeline) |
| `corpus_v2.py` | `from discovery_fabric.a2.adversarial import adversarial_challenge` | ✅ Production (corpus v2) |
| `corpus_v3.py` | `from discovery_fabric.a2.adversarial import adversarial_challenge` | ✅ Production (corpus v3) |
| `corpus_generator.py` | `from discovery_fabric.a2.adversarial import adversarial_challenge` | ✅ Production (corpus gen) |
| `postfix_validation.py` | `from discovery_fabric.a2.adversarial import adversarial_challenge` | ✅ Production (validation) |
| `a2_diagnostic.py` | `from discovery_fabric.a2.adversarial import adversarial_challenge` | ✅ Production (diagnostic) |
| `tests/test_e2e_adversarial_v4.py` | `from discovery_fabric.a2.adversarial import adversarial_challenge` | ✅ Test (E2E) |

**No bypass path exists.** All callers use the same `adversarial_challenge()` function, which internally calls the V4 corrections from `discovery_fabric.v4_corrections`.

## Historical/Invalidated Paths (NOT Production)

These paths have their own internal adversarial prompts but are **invalidated** or **historical** — they are NOT production paths:

| Path | Status | Reason |
|------|--------|--------|
| `engine/invention_synthesis_v2.py` (PASS4_ADVERSARIAL) | ❌ INVALIDATED | `INVENTION_ENGINE_V2_STATUS = INVALID_UNCORRECTED_ADVERSARIAL_GATE`. Scientific result invalid. Preserved as historical artifact. |
| `scripts/tournament_v3_runner.py` (gate_adversarial) | ⚠️ Historical | V3 tournament is `HISTORICAL_PILOT_NOT_PRODUCT_SELECTION`. Tournament used its own inline adversarial prompt, NOT the production path. Preserved as historical artifact. |
| `scripts/v3_corrected_replay.py` | ⚠️ Historical | V3 replay applies V4 corrections to existing V3 data (reclassification only, no LLM calls). Does not call production `adversarial_challenge()`. |

## Verification

The production import test (`test_production_adversarial_imports_v4_corrections`) verifies that `adversarial.py` imports and uses the SAME function objects from `v4_corrections` — not duplicated logic.

```python
# From tests/test_e2e_adversarial_v4.py
def test_adversarial_calls_v4_corrections_not_own_logic():
    from discovery_fabric.v4_corrections import (
        skip_if_evidence_failed as v4_skip,
        evaluate_boundary_condition as v4_eval_bc,
        enforce_prior_art_firewall as v4_firewall,
        check_adversarial_invalid as v4_invalid,
    )
    import discovery_fabric.a2.adversarial as adv
    assert adv.skip_if_evidence_failed is v4_skip
    assert adv.evaluate_boundary_condition is v4_eval_bc
    assert adv.enforce_prior_art_firewall is v4_firewall
    assert adv.check_adversarial_invalid is v4_invalid
```

This test confirms there is ONE authoritative implementation — `adversarial.py` delegates to `v4_corrections`, it does not duplicate the logic.
