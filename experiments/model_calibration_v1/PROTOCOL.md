# MODEL CALIBRATION V1 — PROTOCOL

**Status**: `CALIBRATION_BLOCKED` (pre-registered)
**Protocol SHA-256**: `0330e2c95f66726d4b6b1d35b7e4916196d0df4c340ff04335c70d6deda2cbd6`

## Objective

Calibrate model routing. Test 3 conditions. Only variable is model routing.

## Frozen Engine
- Search: V3.9 (14 families, PatSnap)
- 102: V3.4 passage-grounded
- 103: V3.9 separated 4-question chain
- Hindsight: V3.7 fixed
- Thresholds: frozen
- Corpus: V2 20 cases

## Three Conditions

| Condition | Model | Role |
|---|---|---|
| A | google/gemma-4-31b-it | All stages |
| B | nvidia/nemotron-3.5-lightning-30b-a3b | All stages |
| C | Gemma + Nemotron | Gemma=evidence, Nemotron=challenge, Adjudicator=structured |

## Acceptance Gate
accuracy>=85%, false_elite<=10%, false_reject<=10%, 102>=85%, 103>=80%

## Stop Condition
No 50→5. STOP FOR CEO AUDIT.
