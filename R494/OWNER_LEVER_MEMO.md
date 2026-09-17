# R494 — The Owner-Gated Lever Call: HF Inference Credits
# (the second strong ring the ring-binding now makes valuable)

**Round:** R494 · **Author:** Coder 1 (main session, CTO line) ·
**Decision requested of:** the owner (the credits are owner-gated —
the R491 402 CREDIT_EXHAUSTED state on the HF inference router is an
owner-account property, not a code property)

---

## The call

**Fund the HF inference router.** It is the only lever that lights a
second STRONG, production-reachable ring this quarter, and the
ring-binding discipline (R491, extended to the A2 gauntlet this
round) is what converts that ring from "another endpoint" into
calibrated, deployable kill authority.

## Why NOW — the measured case (all numbers from this round's records)

1. **The calibration is (rules × ring), and the rings are the
   bottleneck.** The A2 gauntlet's DEV-corpus arc, measured this
   round:

   | instrument | ring | TPR | FPR | verdict |
   |---|---|---|---|---|
   | untuned 1.0.0 | xkiro | 0.0909 | 1.0 | universal killer |
   | untuned 1.0.0 | zai-gateway | 0.0909 | 1.0 | same number, second ring |
   | sibling v4.1 | xkiro | 0.6364 | 0.0 | seal refused (TPR < 0.75) |
   | union 2.0.0 | xkiro | 0.2727 | 0.0 | seal refused (TPR < 0.75) |
   | union 2.0.0 | zai-gateway | 0.3636 | 0.0 | seal refused (TPR < 0.75) |

   The false-kill class is SOLVED (FPR 1.0 → 0.0 on every ring, every
   post-burden instrument). What fails is detection — and the failure
   is typed: the free rings' models do not PERFORM the
   attacker-computes derivation (the arithmetic over the record's own
   numbers that turns "10 µm d50 at the stated flow with the stated
   pump limit" into a kill). xkiro kills on memory and hedges on
   computation; the zai gateway hedges on both. The v4.2 prompt
   standard (attacker-computes) is named — but a prompt cannot make a
   weak model do physics.

2. **The ring-binding makes a second strong ring VALUABLE, not
   redundant.** Terminal kill authority now binds to the measured
   ring (R491 for the engine attacker; the A2 gate this round — a
   kill served by a different ring escalates with a typed
   ring_mismatch). Consequences, measured this round:
   - A calibration on the **sandbox-only** zai gateway is
     operationally void in production (its ring never serves
     production attacks — every production kill would escalate as
     ring-mismatched). This is why the shipped operative record pins
     **xkiro** — today the only production-reachable measured ring.
   - xkiro is FREE and weak. A strong ring that is also
     production-reachable is the missing piece: it is where the v4.2
     standard can actually be met (TPR ≥ 0.75 with FPR held at 0),
     and once calibrated, its authority is SERVABLE — the deployed
     cascade can route production attacks to it.

3. **The HF inference router is that ring.** It serves the GLM-class
   strong models (the zai slot's re-point target — the R480/R483
   wiring is already in the registry; the transport work is DONE).
   The only blocker is the account state: 402 CREDIT_EXHAUSTED
   (measured at R491; the token itself is live with repo.write +
   inference scopes).

4. **The cost is bounded and small.** The spend is the calibration
   measurements (21 cases × ~10–60 s per attack — a few hundred
   thousand tokens per full DEV-corpus pass, re-run a handful of
   times per tuning iteration) plus the production attack leg (one
   attack per candidate, ~the same size). No synthesis-stage
   spend is requested; the discovery loop's other stages stay on the
   free/owner-keyed rings exactly as wired.

## What the lever buys, concretely

- **The v4.2 iteration measured where it can pass**: the
  attacker-computes standard on a ring whose model performs
  derivations — the named path to the first CALIBRATED attacker
  (Art. L's destination state).
- **A production-servable calibrated ring** — the ring-bound
  authority becomes executable, not theoretical.
- **Ring redundancy for the attack leg**: today atria is typed-broken
  (4 probe attempts this round, all CALL_FAILED — R494/ATRIA_WATCH.json)
  and xkiro is the single live option; a second strong ring removes
  the single-point-of-failure on the terminal-verification stage.
- **The (rules × ring) science**: two strong rings measured on the
  same frozen corpus would for the first time separate the
  instrument's rules-quality from the ring's model-quality — the
  question every number in the table above begs.

## The owner decision

| option | effect |
|---|---|
| **Fund the router (recommended)** | the second strong ring lights; v4.2 tuning + measurement proceeds on a ring that can pass; production kill authority becomes servable when calibrated |
| Do nothing | the A2 gauntlet stays measured-NOT_CALIBRATED (fail-closed, escalations continue); the attacker's terminal authority remains off; the path-7 item (calibrated attacker) blocks on ring quality indefinitely |
| Fix atria instead (owner-side) | viable IF the provider's reasoning-ceiling behavior is an account/model config — but 4 probes across two eras show the same empty-content class, and no owner surface to change it has been identified; the router is the lever we control |

The ring-binding was built so that a second strong ring would be
worth lighting. This round measured why it is now the bottleneck.
