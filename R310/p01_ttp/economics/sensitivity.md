# Sensitivity Analysis — P-01

**Candidate:** P-01 — Predictive Occlusion-Isolation Controller
**Authority:** Article XXXVI §2 C14 (uncertainty/sensitivity analysis)

---

## 1. Tornado chart inputs

| Input | Low | Base | High | Evidence tier | Effect on annual value |
|-------|----:|-----:|-----:|---------------|------------------------|
| Revision rate reduction | 15% | 30% | 45% | MODELLED | **Dominant driver** — ±15% swing causes ±$50M swing in annual value |
| Units deployed per year | 15K | 30K | 45K | MODELLED | Linear scaling — ±15K swing causes ±$60M swing |
| Revision surgery cost | $35K | $42.5K | $50K | PUBLICLY_VERIFIED | Linear scaling — ±$7.5K swing causes ±$20M swing |
| Manufacturing cost premium | $2K | $1.5K | $1K | MODELLED | Inverse linear — ±$500 swing causes ±$15M swing |
| Addressable market capture | 5% | 15% | 30% | MODELLED | ±10% swing causes ±$50M swing |

## 2. Output range

| Scenario | Annual value (per year) |
|----------|------------------------:|
| Low (all inputs at low) | $16M |
| Base (all inputs at base) | $124M |
| High (all inputs at high) | $335M |

## 3. Break-even analysis

- Development cost to market: $22-53M
- Annual value at base case: $124M
- **Break-even: < 1 year at base case**
- Break-even at low case: 1.4 years
- Break-even at high case: 0.07 years (3 months)

## 4. Key uncertainties

### 4.1 The 30% revision rate reduction is MODELLED
This is the single largest uncertainty. The simulator shows partial improvement (peak 22 vs 59 mmHg), but neither design achieves 24h survival. The 30% reduction assumes that lower peak ICP translates to fewer clinical revisions — this is plausible but not measured.

**Resolution path:** V0 bench testing → V1 implantable → pre-clinical → clinical trial.

### 4.2 The market capture assumption is MODELLED
10-30% capture of the addressable programmable valve market assumes competitive positioning that has not been tested with actual buyers.

**Resolution path:** Buyer outreach (CEO-owned). Buyer questionnaire (see `transfer/buyer_protocol.md`).

### 4.3 The manufacturing cost premium is MODELLED
The $1,000-$2,000 premium over standard programmable valves assumes MEMS valve cost reductions at scale. If MEMS valves remain expensive, the premium could be higher.

**Resolution path:** V1 implantable prototype cost analysis.

## 5. Worst-case scenario

If all uncertainties resolve unfavorably:
- Revision rate reduction: 15% (not 30%)
- Market capture: 5% (not 15%)
- Manufacturing premium: $2K (not $1.5K)

Annual value: ~$5M (still positive, but break-even stretches to 4-5 years).

**Implication:** Even in the worst case, P-01 is economically viable. The risk is not "does it work economically" but "how big is the opportunity."

## 6. Best-case scenario

If all uncertainties resolve favorably:
- Revision rate reduction: 45%
- Market capture: 30%
- Manufacturing premium: $1K

Annual value: ~$400M. This would make P-01 a flagship asset.

## 7. Recommended buyer disclosures

When presenting this model to a buyer:
1. Disclose that the 30% revision rate reduction is MODELLED, not measured
2. Disclose that the simulator honestly reports that P-01 does NOT achieve 24h survival (the partial improvement is real but not a complete solution)
3. Disclose that the path to PUBLICLY_VERIFIED requires clinical data (4-8 years, $20-50M)
4. Offer the buyer-specific value range calculation (see `value_model.md` §7) based on the buyer's actual revision rate data under NDA

## 8. Provenance

- Source: `TTP_PACKAGES/COMMERCIAL_EVIDENCE_LEDGER.json`, internal cost model
