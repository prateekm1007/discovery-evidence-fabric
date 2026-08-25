# Buyer Protocol — P-01

**Candidate:** P-01 — Predictive Occlusion-Isolation Controller
**Authority:** Article XXXVI §2 C13

---

## 1. Buyer integration path

### 1.1 For a shunt OEM buyer (Medtronic, Integra, Sophysa, Miethke)

**Phase 1: Technical evaluation (1-3 months)**
1. Buyer's engineering team reproduces simulator results (per `transfer/reproduction.md`)
2. Buyer's clinical team reviews the dual-invariant control law and the honest falsification findings
3. Buyer's regulatory team assesses pathway (PMA vs 510(k) vs De Novo)
4. Buyer's IP team reviews `differentiation/counsel_questions.md`

**Phase 2: V0 bench prototype (3-6 months)**
1. Buyer builds V0 bench prototype per `technology/prototype_blueprint.md`
2. Buyer runs 30-run test program (720 bench-hours)
3. Buyer compares hardware results to simulator predictions
4. Decision point: proceed to V1 implantable or terminate

**Phase 3: V1 implantable development (12-18 months)**
1. Buyer leads V1 implantable development (custom flow sensor, MEMS valves, hermetic packaging)
2. We provide engineering consultation and the tuned parameters (know-how transfer per `differentiation/know_how.md`)
3. Decision point: proceed to pre-clinical or terminate

**Phase 4: Pre-clinical and clinical (4-8 years)**
1. Buyer leads pre-clinical animal studies
2. Buyer leads clinical trial
3. Buyer leads PMA filing
4. We provide ongoing consultation

### 1.2 For a CNS biotech buyer (acquisition target)

**Phase 1: Due diligence (1-2 months)**
1. Buyer's technical team reviews the full TTP
2. Buyer's counsel examines `differentiation/counsel_questions.md`
3. Buyer's business team assesses strategic fit

**Phase 2: Acquisition or license**
1. Transaction scope per `commercial/transaction_options.md`
2. Know-how transfer per `differentiation/know_how.md`

## 2. Buyer questionnaire (per R277 economic ledger)

To upgrade the economic model from MODELLED to BUYER_VERIFIED, the buyer should complete the BUYER_ECONOMIC_QUESTIONNAIRE (see `TTP_PACKAGES/COMMERCIAL_LOOP/BUYER_ECONOMIC_QUESTIONNAIRE_TEMPLATE.json`):

- Q-01: Current annual revision rate (buyer's installed base)
- Q-02: Current cost per revision (buyer's actual cost data)
- Q-03: Current intervention (what valve/system buyer uses now)
- Q-04: Proposed intervention deployment volume
- Q-05: Measured difference (after V0 bench validation)
- Q-06: Annual volume
- Q-07: Verified savings (after clinical data)
- Q-08: Buyer willingness-to-pay

## 3. What we provide vs. what the buyer provides

### 3.1 We provide
- Complete TTP (this folder)
- Simulator code and preserved raw results
- V0 bench prototype design
- Tuned parameters (know-how, under NDA)
- Engineering consultation during V0/V1 development

### 3.2 Buyer provides
- V0 bench prototype hardware (build per our design)
- V1 implantable development (buyer's engineering team)
- Pre-clinical and clinical studies (buyer's regulatory team)
- Buyer-specific economic data (under NDA)
- Regulatory filing fees

## 4. Handoff protocol

1. CEO introduces buyer to the package (CEO-owned, not machine blocker)
2. Buyer signs NDA
3. We provide full TTP access
4. Buyer's engineering team reproduces simulator (per `transfer/reproduction.md`)
5. If reproduction succeeds: proceed to Phase 2 (V0 bench)
6. If reproduction fails: package is defective, return for correction

## 5. Decision points

| Decision point | Criterion | Outcome if PASS | Outcome if FAIL |
|----------------|-----------|-----------------|-----------------|
| Simulator reproduction | Results match within 1e-6 | Proceed to V0 bench | Package defective |
| V0 bench reproduction | Multi-segment peak < single-segment peak | Proceed to V1 implantable | Simulator wrong or hardware flawed |
| V1 implantable | Flow sensor resolved, prototype passes | Proceed to pre-clinical | Engineering blocker |
| Pre-clinical | Animal studies pass | Proceed to clinical | Biology blocker |
| Clinical | Trial meets endpoints | PMA filing | Mechanism insufficient |

Each decision point is an opportunity for the buyer to terminate the engagement. We do not commit to guaranteed outcomes; we commit to honest disclosure at each step.
