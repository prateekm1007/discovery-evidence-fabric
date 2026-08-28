# Gold Semantic Set — Human Engineer Labeling Sheet

You are the independent human engineer calibrating the audit
layer of an AI invention-engine. For each item below, judge the
engineering content and assign exactly one label:

* **CORRECT** — the engineering statement/reasoning is right.
* **QUESTIONABLE** — you cannot decide from the provided
  materials, or the statement is partly right / unproven.
* **INCORRECT** — the engineering is wrong (wrong physics,
  wrong causal direction, wrong quantity, contradiction,
  unsupported by the source).

Rules:

1. Judge ONLY from the provided materials (dossier artifacts at
   the given path, readable in this repository).
2. You are NOT shown any automated verdict — do not look for
   one; the comparison is only valid if your labels are blind.
3. A claim that is generic boilerplate rather than engineered
   content for THIS device is INCORRECT.
4. Return your labels as JSON:
   `{"reviewer": "<name/role>", "labels":
    {"<item_id>": "CORRECT|QUESTIONABLE|INCORRECT", ...}}`

---

## GOLD-BENCH_01-mechanism_correctness

* type: AXIS_JUDGMENT
* dossier: BENCH_01 (/home/z/my-project/discovery-evidence-fabric/artifacts/benchmark/generated/runs/BENCH_01)
* question: Is the invention's mechanism claim physically correct engineering for this device (right physics family, right control architecture, causal direction as stated)?

**Mechanism claim:** graded-porosity outlet diffuser spreads flow to reduce stagnant zones where tissue ingrowth starts

**Source span:** graded-porosity outlet diffuser spreads flow to reduce stagnant zones where tissue ingrowth starts

**Expected effect:** lower ingrowth-driven obstruction rate at equal drainage

**Falsification test:** (none)

**Architecture:** {'description': 'PROPOSED architecture (no physical system exists): flow path / lumen architecture; pressure regulation element; sensing / feedback element (if closed-loop); termination interfaces (patient / reservoir) — realizing: porous polymeric diffuser sleeve over the distal outlet', 'subsystems': [{'name': 'flow path / lumen architecture', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['diffuser', 'distal', 'lumen', 'outlet', 'polymeric', 'porous', 'sleeve']}}, {'name': 'pressure regulation element', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['diffuser', 'distal', 'outlet', 'polymeric', 'porous', 'sleeve']}}, {'name': 'sensing / feedback element (if closed-loop)', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['diffuser', 'distal', 'outlet', 'polymeric', 'porous', 'sleeve']}}, {'name': 'termination interfaces (patient / reservoir)', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['diffuser', 'distal', 'outlet', 'polymeric', 'porous', 'sleeve']}}]}

**Your label:** CORRECT / QUESTIONABLE / INCORRECT

## GOLD-BENCH_01-engineering_reasoning_correctness

* type: AXIS_JUDGMENT
* dossier: BENCH_01 (/home/z/my-project/discovery-evidence-fabric/artifacts/benchmark/generated/runs/BENCH_01)
* question: Does the engineering reasoning (claim -> principle -> model -> input -> assumption -> output -> failure -> verification) hold together as correct engineering?

**Mechanism claim:** graded-porosity outlet diffuser spreads flow to reduce stagnant zones where tissue ingrowth starts

**Source span:** graded-porosity outlet diffuser spreads flow to reduce stagnant zones where tissue ingrowth starts

**Expected effect:** lower ingrowth-driven obstruction rate at equal drainage

**Falsification test:** (none)

**Architecture:** {'description': 'PROPOSED architecture (no physical system exists): flow path / lumen architecture; pressure regulation element; sensing / feedback element (if closed-loop); termination interfaces (patient / reservoir) — realizing: porous polymeric diffuser sleeve over the distal outlet', 'subsystems': [{'name': 'flow path / lumen architecture', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['diffuser', 'distal', 'lumen', 'outlet', 'polymeric', 'porous', 'sleeve']}}, {'name': 'pressure regulation element', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['diffuser', 'distal', 'outlet', 'polymeric', 'porous', 'sleeve']}}, {'name': 'sensing / feedback element (if closed-loop)', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['diffuser', 'distal', 'outlet', 'polymeric', 'porous', 'sleeve']}}, {'name': 'termination interfaces (patient / reservoir)', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['diffuser', 'distal', 'outlet', 'polymeric', 'porous', 'sleeve']}}]}

**Your label:** CORRECT / QUESTIONABLE / INCORRECT

## GOLD-BENCH_01-equation_applicability

* type: AXIS_JUDGMENT
* dossier: BENCH_01 (/home/z/my-project/discovery-evidence-fabric/artifacts/benchmark/generated/runs/BENCH_01)
* question: Is each governing equation applied only where its validity regime holds (and honestly rejected/conditional elsewhere)?

**Mechanism claim:** graded-porosity outlet diffuser spreads flow to reduce stagnant zones where tissue ingrowth starts

**Source span:** graded-porosity outlet diffuser spreads flow to reduce stagnant zones where tissue ingrowth starts

**Expected effect:** lower ingrowth-driven obstruction rate at equal drainage

**Falsification test:** (none)

**Architecture:** {'description': 'PROPOSED architecture (no physical system exists): flow path / lumen architecture; pressure regulation element; sensing / feedback element (if closed-loop); termination interfaces (patient / reservoir) — realizing: porous polymeric diffuser sleeve over the distal outlet', 'subsystems': [{'name': 'flow path / lumen architecture', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['diffuser', 'distal', 'lumen', 'outlet', 'polymeric', 'porous', 'sleeve']}}, {'name': 'pressure regulation element', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['diffuser', 'distal', 'outlet', 'polymeric', 'porous', 'sleeve']}}, {'name': 'sensing / feedback element (if closed-loop)', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['diffuser', 'distal', 'outlet', 'polymeric', 'porous', 'sleeve']}}, {'name': 'termination interfaces (patient / reservoir)', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['diffuser', 'distal', 'outlet', 'polymeric', 'porous', 'sleeve']}}]}

**Your label:** CORRECT / QUESTIONABLE / INCORRECT

## GOLD-BENCH_01-failure_mode_correctness

* type: AXIS_JUDGMENT
* dossier: BENCH_01 (/home/z/my-project/discovery-evidence-fabric/artifacts/benchmark/generated/runs/BENCH_01)
* question: Is the failure analysis physically correct for this device family (right failure physics, real mechanisms)?

**Mechanism claim:** graded-porosity outlet diffuser spreads flow to reduce stagnant zones where tissue ingrowth starts

**Source span:** graded-porosity outlet diffuser spreads flow to reduce stagnant zones where tissue ingrowth starts

**Expected effect:** lower ingrowth-driven obstruction rate at equal drainage

**Falsification test:** (none)

**Architecture:** {'description': 'PROPOSED architecture (no physical system exists): flow path / lumen architecture; pressure regulation element; sensing / feedback element (if closed-loop); termination interfaces (patient / reservoir) — realizing: porous polymeric diffuser sleeve over the distal outlet', 'subsystems': [{'name': 'flow path / lumen architecture', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['diffuser', 'distal', 'lumen', 'outlet', 'polymeric', 'porous', 'sleeve']}}, {'name': 'pressure regulation element', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['diffuser', 'distal', 'outlet', 'polymeric', 'porous', 'sleeve']}}, {'name': 'sensing / feedback element (if closed-loop)', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['diffuser', 'distal', 'outlet', 'polymeric', 'porous', 'sleeve']}}, {'name': 'termination interfaces (patient / reservoir)', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['diffuser', 'distal', 'outlet', 'polymeric', 'porous', 'sleeve']}}]}

**Your label:** CORRECT / QUESTIONABLE / INCORRECT

## GOLD-BENCH_01-verification_appropriateness

* type: AXIS_JUDGMENT
* dossier: BENCH_01 (/home/z/my-project/discovery-evidence-fabric/artifacts/benchmark/generated/runs/BENCH_01)
* question: Does each verification measure the quantity its failure mode actually depends on, with an acceptance criterion that can detect failure?

**Mechanism claim:** graded-porosity outlet diffuser spreads flow to reduce stagnant zones where tissue ingrowth starts

**Source span:** graded-porosity outlet diffuser spreads flow to reduce stagnant zones where tissue ingrowth starts

**Expected effect:** lower ingrowth-driven obstruction rate at equal drainage

**Falsification test:** (none)

**Architecture:** {'description': 'PROPOSED architecture (no physical system exists): flow path / lumen architecture; pressure regulation element; sensing / feedback element (if closed-loop); termination interfaces (patient / reservoir) — realizing: porous polymeric diffuser sleeve over the distal outlet', 'subsystems': [{'name': 'flow path / lumen architecture', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['diffuser', 'distal', 'lumen', 'outlet', 'polymeric', 'porous', 'sleeve']}}, {'name': 'pressure regulation element', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['diffuser', 'distal', 'outlet', 'polymeric', 'porous', 'sleeve']}}, {'name': 'sensing / feedback element (if closed-loop)', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['diffuser', 'distal', 'outlet', 'polymeric', 'porous', 'sleeve']}}, {'name': 'termination interfaces (patient / reservoir)', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['diffuser', 'distal', 'outlet', 'polymeric', 'porous', 'sleeve']}}]}

**Your label:** CORRECT / QUESTIONABLE / INCORRECT

## GOLD-BENCH_01-CLAIM

* type: MECHANISM_CLAIM
* dossier: BENCH_01 (/home/z/my-project/discovery-evidence-fabric/artifacts/benchmark/generated/runs/BENCH_01)
* question: Is this mechanism claim, as an engineering statement about this device, CORRECT / QUESTIONABLE / INCORRECT? Judge the physics, the causal direction, and whether the source span supports the claim.

**Mechanism claim:** graded-porosity outlet diffuser spreads flow to reduce stagnant zones where tissue ingrowth starts

**Source span:** graded-porosity outlet diffuser spreads flow to reduce stagnant zones where tissue ingrowth starts

**Expected effect:** lower ingrowth-driven obstruction rate at equal drainage

**Falsification test:** (none)

**Architecture:** {'description': 'PROPOSED architecture (no physical system exists): flow path / lumen architecture; pressure regulation element; sensing / feedback element (if closed-loop); termination interfaces (patient / reservoir) — realizing: porous polymeric diffuser sleeve over the distal outlet', 'subsystems': [{'name': 'flow path / lumen architecture', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['diffuser', 'distal', 'lumen', 'outlet', 'polymeric', 'porous', 'sleeve']}}, {'name': 'pressure regulation element', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['diffuser', 'distal', 'outlet', 'polymeric', 'porous', 'sleeve']}}, {'name': 'sensing / feedback element (if closed-loop)', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['diffuser', 'distal', 'outlet', 'polymeric', 'porous', 'sleeve']}}, {'name': 'termination interfaces (patient / reservoir)', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['diffuser', 'distal', 'outlet', 'polymeric', 'porous', 'sleeve']}}]}

**Your label:** CORRECT / QUESTIONABLE / INCORRECT

## GOLD-BENCH_04-mechanism_correctness

* type: AXIS_JUDGMENT
* dossier: BENCH_04 (/home/z/my-project/discovery-evidence-fabric/artifacts/benchmark/generated/runs/BENCH_04)
* question: Is the invention's mechanism claim physically correct engineering for this device (right physics family, right control architecture, causal direction as stated)?

**Mechanism claim:** exposure-aware link-budget scheduler adapts transmit power to hold link margin

**Source span:** exposure-aware link-budget scheduler adapts transmit power to hold link margin

**Expected effect:** reliable data link at maximum implant depth within SAR limits

**Falsification test:** (none)

**Architecture:** {'description': 'PROPOSED architecture (no physical system exists): transmit chain + power limits; channel / tissue path (path loss model); receive chain + detection; regulatory exposure constraint (SAR) — realizing: adaptive-power telemetry firmware with antenna tuning network', 'subsystems': [{'name': 'transmit chain + power limits', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['antenna', 'firmware', 'limits', 'network', 'power', 'telemetry', 'transmit', 'tuning']}}, {'name': 'channel / tissue path (path loss model)', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['antenna', 'firmware', 'network', 'power', 'telemetry', 'tuning']}}, {'name': 'receive chain + detection', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['antenna', 'firmware', 'network', 'power', 'telemetry', 'tuning']}}, {'name': 'regulatory exposure constraint (SAR)', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['antenna', 'exposure', 'firmware', 'network', 'power', 'telemetry', 'tuning']}}]}

**Your label:** CORRECT / QUESTIONABLE / INCORRECT

## GOLD-BENCH_04-engineering_reasoning_correctness

* type: AXIS_JUDGMENT
* dossier: BENCH_04 (/home/z/my-project/discovery-evidence-fabric/artifacts/benchmark/generated/runs/BENCH_04)
* question: Does the engineering reasoning (claim -> principle -> model -> input -> assumption -> output -> failure -> verification) hold together as correct engineering?

**Mechanism claim:** exposure-aware link-budget scheduler adapts transmit power to hold link margin

**Source span:** exposure-aware link-budget scheduler adapts transmit power to hold link margin

**Expected effect:** reliable data link at maximum implant depth within SAR limits

**Falsification test:** (none)

**Architecture:** {'description': 'PROPOSED architecture (no physical system exists): transmit chain + power limits; channel / tissue path (path loss model); receive chain + detection; regulatory exposure constraint (SAR) — realizing: adaptive-power telemetry firmware with antenna tuning network', 'subsystems': [{'name': 'transmit chain + power limits', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['antenna', 'firmware', 'limits', 'network', 'power', 'telemetry', 'transmit', 'tuning']}}, {'name': 'channel / tissue path (path loss model)', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['antenna', 'firmware', 'network', 'power', 'telemetry', 'tuning']}}, {'name': 'receive chain + detection', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['antenna', 'firmware', 'network', 'power', 'telemetry', 'tuning']}}, {'name': 'regulatory exposure constraint (SAR)', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['antenna', 'exposure', 'firmware', 'network', 'power', 'telemetry', 'tuning']}}]}

**Your label:** CORRECT / QUESTIONABLE / INCORRECT

## GOLD-BENCH_04-equation_applicability

* type: AXIS_JUDGMENT
* dossier: BENCH_04 (/home/z/my-project/discovery-evidence-fabric/artifacts/benchmark/generated/runs/BENCH_04)
* question: Is each governing equation applied only where its validity regime holds (and honestly rejected/conditional elsewhere)?

**Mechanism claim:** exposure-aware link-budget scheduler adapts transmit power to hold link margin

**Source span:** exposure-aware link-budget scheduler adapts transmit power to hold link margin

**Expected effect:** reliable data link at maximum implant depth within SAR limits

**Falsification test:** (none)

**Architecture:** {'description': 'PROPOSED architecture (no physical system exists): transmit chain + power limits; channel / tissue path (path loss model); receive chain + detection; regulatory exposure constraint (SAR) — realizing: adaptive-power telemetry firmware with antenna tuning network', 'subsystems': [{'name': 'transmit chain + power limits', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['antenna', 'firmware', 'limits', 'network', 'power', 'telemetry', 'transmit', 'tuning']}}, {'name': 'channel / tissue path (path loss model)', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['antenna', 'firmware', 'network', 'power', 'telemetry', 'tuning']}}, {'name': 'receive chain + detection', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['antenna', 'firmware', 'network', 'power', 'telemetry', 'tuning']}}, {'name': 'regulatory exposure constraint (SAR)', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['antenna', 'exposure', 'firmware', 'network', 'power', 'telemetry', 'tuning']}}]}

**Your label:** CORRECT / QUESTIONABLE / INCORRECT

## GOLD-BENCH_04-failure_mode_correctness

* type: AXIS_JUDGMENT
* dossier: BENCH_04 (/home/z/my-project/discovery-evidence-fabric/artifacts/benchmark/generated/runs/BENCH_04)
* question: Is the failure analysis physically correct for this device family (right failure physics, real mechanisms)?

**Mechanism claim:** exposure-aware link-budget scheduler adapts transmit power to hold link margin

**Source span:** exposure-aware link-budget scheduler adapts transmit power to hold link margin

**Expected effect:** reliable data link at maximum implant depth within SAR limits

**Falsification test:** (none)

**Architecture:** {'description': 'PROPOSED architecture (no physical system exists): transmit chain + power limits; channel / tissue path (path loss model); receive chain + detection; regulatory exposure constraint (SAR) — realizing: adaptive-power telemetry firmware with antenna tuning network', 'subsystems': [{'name': 'transmit chain + power limits', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['antenna', 'firmware', 'limits', 'network', 'power', 'telemetry', 'transmit', 'tuning']}}, {'name': 'channel / tissue path (path loss model)', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['antenna', 'firmware', 'network', 'power', 'telemetry', 'tuning']}}, {'name': 'receive chain + detection', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['antenna', 'firmware', 'network', 'power', 'telemetry', 'tuning']}}, {'name': 'regulatory exposure constraint (SAR)', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['antenna', 'exposure', 'firmware', 'network', 'power', 'telemetry', 'tuning']}}]}

**Your label:** CORRECT / QUESTIONABLE / INCORRECT

## GOLD-BENCH_04-verification_appropriateness

* type: AXIS_JUDGMENT
* dossier: BENCH_04 (/home/z/my-project/discovery-evidence-fabric/artifacts/benchmark/generated/runs/BENCH_04)
* question: Does each verification measure the quantity its failure mode actually depends on, with an acceptance criterion that can detect failure?

**Mechanism claim:** exposure-aware link-budget scheduler adapts transmit power to hold link margin

**Source span:** exposure-aware link-budget scheduler adapts transmit power to hold link margin

**Expected effect:** reliable data link at maximum implant depth within SAR limits

**Falsification test:** (none)

**Architecture:** {'description': 'PROPOSED architecture (no physical system exists): transmit chain + power limits; channel / tissue path (path loss model); receive chain + detection; regulatory exposure constraint (SAR) — realizing: adaptive-power telemetry firmware with antenna tuning network', 'subsystems': [{'name': 'transmit chain + power limits', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['antenna', 'firmware', 'limits', 'network', 'power', 'telemetry', 'transmit', 'tuning']}}, {'name': 'channel / tissue path (path loss model)', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['antenna', 'firmware', 'network', 'power', 'telemetry', 'tuning']}}, {'name': 'receive chain + detection', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['antenna', 'firmware', 'network', 'power', 'telemetry', 'tuning']}}, {'name': 'regulatory exposure constraint (SAR)', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['antenna', 'exposure', 'firmware', 'network', 'power', 'telemetry', 'tuning']}}]}

**Your label:** CORRECT / QUESTIONABLE / INCORRECT

## GOLD-BENCH_04-CLAIM

* type: MECHANISM_CLAIM
* dossier: BENCH_04 (/home/z/my-project/discovery-evidence-fabric/artifacts/benchmark/generated/runs/BENCH_04)
* question: Is this mechanism claim, as an engineering statement about this device, CORRECT / QUESTIONABLE / INCORRECT? Judge the physics, the causal direction, and whether the source span supports the claim.

**Mechanism claim:** exposure-aware link-budget scheduler adapts transmit power to hold link margin

**Source span:** exposure-aware link-budget scheduler adapts transmit power to hold link margin

**Expected effect:** reliable data link at maximum implant depth within SAR limits

**Falsification test:** (none)

**Architecture:** {'description': 'PROPOSED architecture (no physical system exists): transmit chain + power limits; channel / tissue path (path loss model); receive chain + detection; regulatory exposure constraint (SAR) — realizing: adaptive-power telemetry firmware with antenna tuning network', 'subsystems': [{'name': 'transmit chain + power limits', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['antenna', 'firmware', 'limits', 'network', 'power', 'telemetry', 'transmit', 'tuning']}}, {'name': 'channel / tissue path (path loss model)', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['antenna', 'firmware', 'network', 'power', 'telemetry', 'tuning']}}, {'name': 'receive chain + detection', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['antenna', 'firmware', 'network', 'power', 'telemetry', 'tuning']}}, {'name': 'regulatory exposure constraint (SAR)', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['antenna', 'exposure', 'firmware', 'network', 'power', 'telemetry', 'tuning']}}]}

**Your label:** CORRECT / QUESTIONABLE / INCORRECT

## GOLD-BENCH_09-mechanism_correctness

* type: AXIS_JUDGMENT
* dossier: BENCH_09 (/home/z/my-project/discovery-evidence-fabric/artifacts/benchmark/generated/runs/BENCH_09)
* question: Is the invention's mechanism claim physically correct engineering for this device (right physics family, right control architecture, causal direction as stated)?

**Mechanism claim:** on-device temporal model learns the patient baseline and flags deviation earlier than fixed thresholds

**Source span:** on-device temporal model learns the patient baseline and flags deviation earlier than fixed thresholds

**Expected effect:** earlier true alarms with fewer false positives

**Falsification test:** (none)

**Architecture:** {'description': 'PROPOSED architecture (no physical system exists): data ingestion and labeling pipeline; feature / representation layer; model + uncertainty quantification; deployment target + monitoring loop — realizing: patient-adaptive anomaly detector on the sensor node', 'subsystems': [{'name': 'data ingestion and labeling pipeline', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['anomaly', 'detector', 'patient', 'sensor']}}, {'name': 'feature / representation layer', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['anomaly', 'detector', 'patient', 'sensor']}}, {'name': 'model + uncertainty quantification', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['anomaly', 'detector', 'model', 'patient', 'sensor']}}, {'name': 'deployment target + monitoring loop', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['anomaly', 'detector', 'patient', 'sensor']}}]}

**Your label:** CORRECT / QUESTIONABLE / INCORRECT

## GOLD-BENCH_09-engineering_reasoning_correctness

* type: AXIS_JUDGMENT
* dossier: BENCH_09 (/home/z/my-project/discovery-evidence-fabric/artifacts/benchmark/generated/runs/BENCH_09)
* question: Does the engineering reasoning (claim -> principle -> model -> input -> assumption -> output -> failure -> verification) hold together as correct engineering?

**Mechanism claim:** on-device temporal model learns the patient baseline and flags deviation earlier than fixed thresholds

**Source span:** on-device temporal model learns the patient baseline and flags deviation earlier than fixed thresholds

**Expected effect:** earlier true alarms with fewer false positives

**Falsification test:** (none)

**Architecture:** {'description': 'PROPOSED architecture (no physical system exists): data ingestion and labeling pipeline; feature / representation layer; model + uncertainty quantification; deployment target + monitoring loop — realizing: patient-adaptive anomaly detector on the sensor node', 'subsystems': [{'name': 'data ingestion and labeling pipeline', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['anomaly', 'detector', 'patient', 'sensor']}}, {'name': 'feature / representation layer', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['anomaly', 'detector', 'patient', 'sensor']}}, {'name': 'model + uncertainty quantification', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['anomaly', 'detector', 'model', 'patient', 'sensor']}}, {'name': 'deployment target + monitoring loop', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['anomaly', 'detector', 'patient', 'sensor']}}]}

**Your label:** CORRECT / QUESTIONABLE / INCORRECT

## GOLD-BENCH_09-equation_applicability

* type: AXIS_JUDGMENT
* dossier: BENCH_09 (/home/z/my-project/discovery-evidence-fabric/artifacts/benchmark/generated/runs/BENCH_09)
* question: Is each governing equation applied only where its validity regime holds (and honestly rejected/conditional elsewhere)?

**Mechanism claim:** on-device temporal model learns the patient baseline and flags deviation earlier than fixed thresholds

**Source span:** on-device temporal model learns the patient baseline and flags deviation earlier than fixed thresholds

**Expected effect:** earlier true alarms with fewer false positives

**Falsification test:** (none)

**Architecture:** {'description': 'PROPOSED architecture (no physical system exists): data ingestion and labeling pipeline; feature / representation layer; model + uncertainty quantification; deployment target + monitoring loop — realizing: patient-adaptive anomaly detector on the sensor node', 'subsystems': [{'name': 'data ingestion and labeling pipeline', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['anomaly', 'detector', 'patient', 'sensor']}}, {'name': 'feature / representation layer', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['anomaly', 'detector', 'patient', 'sensor']}}, {'name': 'model + uncertainty quantification', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['anomaly', 'detector', 'model', 'patient', 'sensor']}}, {'name': 'deployment target + monitoring loop', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['anomaly', 'detector', 'patient', 'sensor']}}]}

**Your label:** CORRECT / QUESTIONABLE / INCORRECT

## GOLD-BENCH_09-failure_mode_correctness

* type: AXIS_JUDGMENT
* dossier: BENCH_09 (/home/z/my-project/discovery-evidence-fabric/artifacts/benchmark/generated/runs/BENCH_09)
* question: Is the failure analysis physically correct for this device family (right failure physics, real mechanisms)?

**Mechanism claim:** on-device temporal model learns the patient baseline and flags deviation earlier than fixed thresholds

**Source span:** on-device temporal model learns the patient baseline and flags deviation earlier than fixed thresholds

**Expected effect:** earlier true alarms with fewer false positives

**Falsification test:** (none)

**Architecture:** {'description': 'PROPOSED architecture (no physical system exists): data ingestion and labeling pipeline; feature / representation layer; model + uncertainty quantification; deployment target + monitoring loop — realizing: patient-adaptive anomaly detector on the sensor node', 'subsystems': [{'name': 'data ingestion and labeling pipeline', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['anomaly', 'detector', 'patient', 'sensor']}}, {'name': 'feature / representation layer', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['anomaly', 'detector', 'patient', 'sensor']}}, {'name': 'model + uncertainty quantification', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['anomaly', 'detector', 'model', 'patient', 'sensor']}}, {'name': 'deployment target + monitoring loop', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['anomaly', 'detector', 'patient', 'sensor']}}]}

**Your label:** CORRECT / QUESTIONABLE / INCORRECT

## GOLD-BENCH_09-verification_appropriateness

* type: AXIS_JUDGMENT
* dossier: BENCH_09 (/home/z/my-project/discovery-evidence-fabric/artifacts/benchmark/generated/runs/BENCH_09)
* question: Does each verification measure the quantity its failure mode actually depends on, with an acceptance criterion that can detect failure?

**Mechanism claim:** on-device temporal model learns the patient baseline and flags deviation earlier than fixed thresholds

**Source span:** on-device temporal model learns the patient baseline and flags deviation earlier than fixed thresholds

**Expected effect:** earlier true alarms with fewer false positives

**Falsification test:** (none)

**Architecture:** {'description': 'PROPOSED architecture (no physical system exists): data ingestion and labeling pipeline; feature / representation layer; model + uncertainty quantification; deployment target + monitoring loop — realizing: patient-adaptive anomaly detector on the sensor node', 'subsystems': [{'name': 'data ingestion and labeling pipeline', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['anomaly', 'detector', 'patient', 'sensor']}}, {'name': 'feature / representation layer', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['anomaly', 'detector', 'patient', 'sensor']}}, {'name': 'model + uncertainty quantification', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['anomaly', 'detector', 'model', 'patient', 'sensor']}}, {'name': 'deployment target + monitoring loop', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['anomaly', 'detector', 'patient', 'sensor']}}]}

**Your label:** CORRECT / QUESTIONABLE / INCORRECT

## GOLD-BENCH_09-CLAIM

* type: MECHANISM_CLAIM
* dossier: BENCH_09 (/home/z/my-project/discovery-evidence-fabric/artifacts/benchmark/generated/runs/BENCH_09)
* question: Is this mechanism claim, as an engineering statement about this device, CORRECT / QUESTIONABLE / INCORRECT? Judge the physics, the causal direction, and whether the source span supports the claim.

**Mechanism claim:** on-device temporal model learns the patient baseline and flags deviation earlier than fixed thresholds

**Source span:** on-device temporal model learns the patient baseline and flags deviation earlier than fixed thresholds

**Expected effect:** earlier true alarms with fewer false positives

**Falsification test:** (none)

**Architecture:** {'description': 'PROPOSED architecture (no physical system exists): data ingestion and labeling pipeline; feature / representation layer; model + uncertainty quantification; deployment target + monitoring loop — realizing: patient-adaptive anomaly detector on the sensor node', 'subsystems': [{'name': 'data ingestion and labeling pipeline', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['anomaly', 'detector', 'patient', 'sensor']}}, {'name': 'feature / representation layer', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['anomaly', 'detector', 'patient', 'sensor']}}, {'name': 'model + uncertainty quantification', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['anomaly', 'detector', 'model', 'patient', 'sensor']}}, {'name': 'deployment target + monitoring loop', 'status': 'ENGINEERING_PROPOSED', 'detail': 'NOT ESTABLISHED (requires design work)', 'invention_tie': {'invention_tied': True, 'matched_tokens': ['anomaly', 'detector', 'patient', 'sensor']}}]}

**Your label:** CORRECT / QUESTIONABLE / INCORRECT
