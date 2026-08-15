# MICRO-2 Forensic QC — 10 Deterministic + All Inconsistent

Deterministic sample size: 10

Inconsistent records audited: 0

Total audited in this QC pass: 10

**No manual improvement performed.** Audit only.

## Per-Seed Audit

### micro_082 — Ventilator (Mistral/mistral-medium-latest)

- stored: MICRO_MECHANISM_SUPPORTED_HYPOTHESIS → canonical: MICRO_MECHANISM_SUPPORTED_HYPOTHESIS → derived: MICRO_MECHANISM_SUPPORTED_HYPOTHESIS (consistent=True)
- in_deterministic_sample: True | in_inconsistent_set: False
- reason: All four gates PASS: problem + mechanism + hypothesis + falsification.
  - **problem_evidence**: {'verdict': 'PASS', 'has_registry_evidence': True, 'device_in_sources': True, 'failure_in_sources': True, 'candidate_mentions_device': True, 'candidate_mentions_failure': True, 'level': 'PROBLEM_FROM_REGISTRY'}
  - **mechanism_evidence**: {'verdict': 'PASS', 'has': True, 'level': 'DIRECT', 'supporting_spans_count': 1}
  - **transfer_level**: {'level': 'MECHANISTIC_INFERENCE', 'supported': True, 'concepts_count': 2, 'spans_count': 0}
  - **hypothesis_boundary**: {'verdict': 'PASS', 'is_hypothesis': True, 'has_falsification': True, 'modification_length': 113}
  - **falsification_test**: {'verdict': 'PASS', 'length': 280, 'has_test_indicator': True, 'excerpt': 'Culture swabs from the inner surface of the modified circuit after 72 hours of clinical use, comparing CFU (colony-forming units) counts to the baseline (uncoated) circuit. A statistically significant'}
  - **provenance**: {'verdict': 'PASS', 'provider': 'Mistral', 'model': 'mistral-medium-latest', 'prompt_hash': 'bdad7f76c4ebeaaa', 'prompt_hash_matches': True, 'response_hash': 'ad09a0c134c25110', 'source_ids_count': 1, 'source_hashes_count': 3}

### micro_015 — Intraocular Lens (NVIDIA/deepseek-ai/deepseek-v4-flash-0731)

- stored: MICRO_UNSUPPORTED → canonical: MICRO_UNSUPPORTED → derived: MICRO_UNSUPPORTED (consistent=True)
- in_deterministic_sample: True | in_inconsistent_set: False
- reason: Problem or mechanism evidence insufficient (pe=PASS, me=FAIL).
  - **problem_evidence**: {'verdict': 'PASS', 'has_registry_evidence': True, 'device_in_sources': False, 'failure_in_sources': True, 'candidate_mentions_device': False, 'candidate_mentions_failure': True, 'level': 'INDIRECT'}
  - **mechanism_evidence**: {'verdict': 'FAIL', 'has': False, 'level': 'UNSUPPORTED', 'supporting_spans_count': 0}
  - **transfer_level**: {'level': 'NOT_APPLICABLE', 'supported': False, 'concepts_count': 3, 'spans_count': 0}
  - **hypothesis_boundary**: {'verdict': 'PASS', 'is_hypothesis': True, 'has_falsification': True, 'modification_length': 200}
  - **falsification_test**: {'verdict': 'PASS', 'length': 449, 'has_test_indicator': True, 'excerpt': 'In an in vitro assay, inoculate the modified IOL and a standard AcrySof IOL (control) with Staphylococcus epidermidis (common endophthalmitis pathogen) at 10^5 CFU/mL. Incubate in balanced salt soluti'}
  - **provenance**: {'verdict': 'PASS', 'provider': 'NVIDIA', 'model': 'deepseek-ai/deepseek-v4-flash-0731', 'prompt_hash': 'bdad7f76c4ebeaaa', 'prompt_hash_matches': True, 'response_hash': 'dbb9a8a16b8b342e', 'source_ids_count': 1, 'source_hashes_count': 3}

### micro_004 — Hip Implant (NVIDIA/deepseek-ai/deepseek-v4-flash-0731)

- stored: MICRO_MECHANISM_SUPPORTED_HYPOTHESIS → canonical: MICRO_MECHANISM_SUPPORTED_HYPOTHESIS → derived: MICRO_MECHANISM_SUPPORTED_HYPOTHESIS (consistent=True)
- in_deterministic_sample: True | in_inconsistent_set: False
- reason: All four gates PASS: problem + mechanism + hypothesis + falsification.
  - **problem_evidence**: {'verdict': 'PASS', 'has_registry_evidence': True, 'device_in_sources': True, 'failure_in_sources': True, 'candidate_mentions_device': False, 'candidate_mentions_failure': True, 'level': 'DIRECT'}
  - **mechanism_evidence**: {'verdict': 'PASS', 'has': True, 'level': 'DIRECT', 'supporting_spans_count': 1}
  - **transfer_level**: {'level': 'NOT_APPLICABLE', 'supported': False, 'concepts_count': 1, 'spans_count': 0}
  - **hypothesis_boundary**: {'verdict': 'PASS', 'is_hypothesis': True, 'has_falsification': True, 'modification_length': 200}
  - **falsification_test**: {'verdict': 'PASS', 'length': 628, 'has_test_indicator': True, 'excerpt': 'Conduct a hip simulator wear test per ISO 14242-1 (or ASTM F1714) using the modified femoral head (with microtextured dimples) paired with the same highly cross-linked polyethylene liner, run for 10 m'}
  - **provenance**: {'verdict': 'PASS', 'provider': 'NVIDIA', 'model': 'deepseek-ai/deepseek-v4-flash-0731', 'prompt_hash': 'bdad7f76c4ebeaaa', 'prompt_hash_matches': True, 'response_hash': '48f230fcb7150b47', 'source_ids_count': 1, 'source_hashes_count': 3}

### micro_095 — Peritoneal Dialysis Catheter (Mistral/mistral-medium-latest)

- stored: MICRO_UNSUPPORTED → canonical: MICRO_UNSUPPORTED → derived: MICRO_UNSUPPORTED (consistent=True)
- in_deterministic_sample: True | in_inconsistent_set: False
- reason: Transfer is UNSUPPORTED_TRANSFER under V2 rule.
  - **problem_evidence**: {'verdict': 'PASS', 'has_registry_evidence': True, 'device_in_sources': True, 'failure_in_sources': True, 'candidate_mentions_device': True, 'candidate_mentions_failure': True, 'level': 'PROBLEM_FROM_REGISTRY'}
  - **mechanism_evidence**: {'verdict': 'PARTIAL', 'has': False, 'level': 'INDIRECT', 'supporting_spans_count': 0}
  - **transfer_level**: {'level': 'UNSUPPORTED_TRANSFER', 'supported': False, 'concepts_count': 2, 'spans_count': 0}
  - **hypothesis_boundary**: {'verdict': 'PASS', 'is_hypothesis': True, 'has_falsification': True, 'modification_length': 117}
  - **falsification_test**: {'verdict': 'PASS', 'length': 221, 'has_test_indicator': True, 'excerpt': 'In vitro bacterial challenge test (e.g., *Staphylococcus epidermidis* biofilm formation assay) comparing silver-impregnated cuff vs. standard cuff, measuring bacterial viability and migration through '}
  - **provenance**: {'verdict': 'PASS', 'provider': 'Mistral', 'model': 'mistral-medium-latest', 'prompt_hash': 'bdad7f76c4ebeaaa', 'prompt_hash_matches': True, 'response_hash': '67e05a2a853b1151', 'source_ids_count': 1, 'source_hashes_count': 3}

### micro_036 — Glaucoma Shunt (Mistral/mistral-medium-latest)

- stored: MICRO_UNSUPPORTED → canonical: MICRO_UNSUPPORTED → derived: MICRO_UNSUPPORTED (consistent=True)
- in_deterministic_sample: True | in_inconsistent_set: False
- reason: Transfer is UNSUPPORTED_TRANSFER under V2 rule.
  - **problem_evidence**: {'verdict': 'PASS', 'has_registry_evidence': True, 'device_in_sources': True, 'failure_in_sources': True, 'candidate_mentions_device': True, 'candidate_mentions_failure': True, 'level': 'PROBLEM_FROM_REGISTRY'}
  - **mechanism_evidence**: {'verdict': 'PARTIAL', 'has': False, 'level': 'INDIRECT', 'supporting_spans_count': 0}
  - **transfer_level**: {'level': 'UNSUPPORTED_TRANSFER', 'supported': False, 'concepts_count': 3, 'spans_count': 0}
  - **hypothesis_boundary**: {'verdict': 'PASS', 'is_hypothesis': True, 'has_falsification': True, 'modification_length': 143}
  - **falsification_test**: {'verdict': 'PASS', 'length': 227, 'has_test_indicator': True, 'excerpt': 'Compare infection rates in a controlled study between coated and uncoated shunts over a 12-month postoperative period, with infection defined as positive bacterial culture from conjunctival swabs or c'}
  - **provenance**: {'verdict': 'PASS', 'provider': 'Mistral', 'model': 'mistral-medium-latest', 'prompt_hash': 'bdad7f76c4ebeaaa', 'prompt_hash_matches': True, 'response_hash': '887bfb2b7bc672bc', 'source_ids_count': 1, 'source_hashes_count': 3}

### micro_032 — Sacral Nerve Stimulator (Mistral/mistral-medium-latest)

- stored: MICRO_UNSUPPORTED → canonical: MICRO_UNSUPPORTED → derived: MICRO_UNSUPPORTED (consistent=True)
- in_deterministic_sample: True | in_inconsistent_set: False
- reason: Transfer is UNSUPPORTED_TRANSFER under V2 rule.
  - **problem_evidence**: {'verdict': 'PASS', 'has_registry_evidence': True, 'device_in_sources': True, 'failure_in_sources': True, 'candidate_mentions_device': False, 'candidate_mentions_failure': True, 'level': 'PROBLEM_FROM_REGISTRY'}
  - **mechanism_evidence**: {'verdict': 'PARTIAL', 'has': False, 'level': 'INDIRECT', 'supporting_spans_count': 0}
  - **transfer_level**: {'level': 'UNSUPPORTED_TRANSFER', 'supported': False, 'concepts_count': 3, 'spans_count': 0}
  - **hypothesis_boundary**: {'verdict': 'PASS', 'is_hypothesis': True, 'has_falsification': True, 'modification_length': 148}
  - **falsification_test**: {'verdict': 'PASS', 'length': 236, 'has_test_indicator': True, 'excerpt': 'Compare infection rates in a randomized controlled trial (RCT) between devices with and without the antimicrobial coating over a 12-month follow-up period, with the primary endpoint being the rate of '}
  - **provenance**: {'verdict': 'PASS', 'provider': 'Mistral', 'model': 'mistral-medium-latest', 'prompt_hash': 'bdad7f76c4ebeaaa', 'prompt_hash_matches': True, 'response_hash': '419321bccc7c14fc', 'source_ids_count': 1, 'source_hashes_count': 3}

### micro_029 — Spinal Cord Stimulator (Mistral/mistral-medium-latest)

- stored: MICRO_UNSUPPORTED → canonical: MICRO_UNSUPPORTED → derived: MICRO_UNSUPPORTED (consistent=True)
- in_deterministic_sample: True | in_inconsistent_set: False
- reason: Transfer is UNSUPPORTED_TRANSFER under V2 rule.
  - **problem_evidence**: {'verdict': 'PASS', 'has_registry_evidence': True, 'device_in_sources': True, 'failure_in_sources': True, 'candidate_mentions_device': True, 'candidate_mentions_failure': True, 'level': 'PROBLEM_FROM_REGISTRY'}
  - **mechanism_evidence**: {'verdict': 'PARTIAL', 'has': False, 'level': 'INDIRECT', 'supporting_spans_count': 0}
  - **transfer_level**: {'level': 'UNSUPPORTED_TRANSFER', 'supported': False, 'concepts_count': 1, 'spans_count': 0}
  - **hypothesis_boundary**: {'verdict': 'PASS', 'is_hypothesis': True, 'has_falsification': True, 'modification_length': 194}
  - **falsification_test**: {'verdict': 'PASS', 'length': 220, 'has_test_indicator': True, 'excerpt': 'Accelerated fatigue testing (e.g., cyclic bending at physiological spinal motion ranges) of modified leads vs. baseline leads, measuring the rate of complete electrical failure (open circuit) under eq'}
  - **provenance**: {'verdict': 'PASS', 'provider': 'Mistral', 'model': 'mistral-medium-latest', 'prompt_hash': 'bdad7f76c4ebeaaa', 'prompt_hash_matches': True, 'response_hash': '7dd8780e3797b56b', 'source_ids_count': 1, 'source_hashes_count': 3}

### micro_018 — Heart Valve (Mistral/mistral-medium-latest)

- stored: MICRO_UNSUPPORTED → canonical: MICRO_UNSUPPORTED → derived: MICRO_UNSUPPORTED (consistent=True)
- in_deterministic_sample: True | in_inconsistent_set: False
- reason: Transfer is UNSUPPORTED_TRANSFER under V2 rule.
  - **problem_evidence**: {'verdict': 'PASS', 'has_registry_evidence': True, 'device_in_sources': True, 'failure_in_sources': True, 'candidate_mentions_device': False, 'candidate_mentions_failure': True, 'level': 'PROBLEM_FROM_REGISTRY'}
  - **mechanism_evidence**: {'verdict': 'PARTIAL', 'has': False, 'level': 'INDIRECT', 'supporting_spans_count': 0}
  - **transfer_level**: {'level': 'UNSUPPORTED_TRANSFER', 'supported': False, 'concepts_count': 2, 'spans_count': 0}
  - **hypothesis_boundary**: {'verdict': 'PASS', 'is_hypothesis': True, 'has_falsification': True, 'modification_length': 150}
  - **falsification_test**: {'verdict': 'PASS', 'length': 295, 'has_test_indicator': True, 'excerpt': 'Conduct accelerated fatigue testing (e.g., ISO 5840-3) on coated vs. uncoated leaflets under physiological pressure cycles (e.g., 600 mmHg, 5 Hz) and compare the number of cycles to failure. If coated'}
  - **provenance**: {'verdict': 'PASS', 'provider': 'Mistral', 'model': 'mistral-medium-latest', 'prompt_hash': 'bdad7f76c4ebeaaa', 'prompt_hash_matches': True, 'response_hash': '5b1b10b9b1bba930', 'source_ids_count': 1, 'source_hashes_count': 3}

### micro_014 — Dental Implant (NVIDIA/deepseek-ai/deepseek-v4-flash-0731)

- stored: MICRO_MECHANISM_SUPPORTED_HYPOTHESIS → canonical: MICRO_MECHANISM_SUPPORTED_HYPOTHESIS → derived: MICRO_MECHANISM_SUPPORTED_HYPOTHESIS (consistent=True)
- in_deterministic_sample: True | in_inconsistent_set: False
- reason: All four gates PASS: problem + mechanism + hypothesis + falsification.
  - **problem_evidence**: {'verdict': 'PASS', 'has_registry_evidence': True, 'device_in_sources': True, 'failure_in_sources': True, 'candidate_mentions_device': True, 'candidate_mentions_failure': True, 'level': 'DIRECT'}
  - **mechanism_evidence**: {'verdict': 'PASS', 'has': True, 'level': 'DIRECT', 'supporting_spans_count': 2}
  - **transfer_level**: {'level': 'NOT_APPLICABLE', 'supported': False, 'concepts_count': 0, 'spans_count': 0}
  - **hypothesis_boundary**: {'verdict': 'PASS', 'is_hypothesis': True, 'has_falsification': True, 'modification_length': 200}
  - **falsification_test**: {'verdict': 'PASS', 'length': 523, 'has_test_indicator': True, 'excerpt': 'In an in vitro biofilm assay (e.g., using *Porphyromonas gingivalis* or *Streptococcus mutans*), compare the modified implant-abutment assembly against the unmodified baseline (same geometry, same mat'}
  - **provenance**: {'verdict': 'PASS', 'provider': 'NVIDIA', 'model': 'deepseek-ai/deepseek-v4-flash-0731', 'prompt_hash': 'bdad7f76c4ebeaaa', 'prompt_hash_matches': True, 'response_hash': '4fb9a200dfc20d85', 'source_ids_count': 1, 'source_hashes_count': 3}

### micro_087 — Infusion Pump (Mistral/mistral-medium-latest)

- stored: MICRO_MECHANISM_SUPPORTED_HYPOTHESIS → canonical: MICRO_MECHANISM_SUPPORTED_HYPOTHESIS → derived: MICRO_MECHANISM_SUPPORTED_HYPOTHESIS (consistent=True)
- in_deterministic_sample: True | in_inconsistent_set: False
- reason: All four gates PASS: problem + mechanism + hypothesis + falsification.
  - **problem_evidence**: {'verdict': 'PASS', 'has_registry_evidence': True, 'device_in_sources': True, 'failure_in_sources': True, 'candidate_mentions_device': True, 'candidate_mentions_failure': True, 'level': 'PROBLEM_FROM_REGISTRY'}
  - **mechanism_evidence**: {'verdict': 'PASS', 'has': True, 'level': 'DIRECT', 'supporting_spans_count': 1}
  - **transfer_level**: {'level': 'MECHANISTIC_INFERENCE', 'supported': True, 'concepts_count': 3, 'spans_count': 0}
  - **hypothesis_boundary**: {'verdict': 'PASS', 'is_hypothesis': True, 'has_falsification': True, 'modification_length': 132}
  - **falsification_test**: {'verdict': 'PASS', 'length': 329, 'has_test_indicator': True, 'excerpt': 'In vitro challenge test: Inoculate the coated and uncoated connectors with a standardized bacterial load (e.g., *Staphylococcus epidermidis*), then measure bacterial viability (CFU/mL) after 24 hours.'}
  - **provenance**: {'verdict': 'PASS', 'provider': 'Mistral', 'model': 'mistral-medium-latest', 'prompt_hash': 'bdad7f76c4ebeaaa', 'prompt_hash_matches': True, 'response_hash': 'cca99c410694d1d4', 'source_ids_count': 1, 'source_hashes_count': 3}
