# Auditor Package — Corpus V2

## Corpus Root Hash
549d1ba7cdb205a9b19f4205330ccbec32f1d3238798f775c2e9bd93cac85f2f

## Source Universe
- Connector: Europe PMC (LIVE)
- Relevance gate: ACTIVE

## Candidate Universe
- Total: 14
- Survivors: 0
- Rejected: 14
- Evidence verified: 13/14 (93%)

## Generation Protocol
- A2: retrieve → relevance gate → freeze → synthesize → verify → prior-art → adversarial → classify
- Model: deepseek/deepseek-v4-flash-0731, temp=0.0, max_tokens=8000
- A2 contract FROZEN — no threshold tuning

## Sampling
- Survivors: corpus_v2/candidates/
- Rejected: corpus_v2/rejected/
- Progress: corpus_v2/corpus_v2_progress.json

## Code Commit: bfcbbd0b1b74753d3680c6ef84321d873f3b072b
