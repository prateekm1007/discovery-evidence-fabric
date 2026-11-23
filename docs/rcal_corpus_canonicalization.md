# R-CAL corpus digest canonicalization (R142-F4, DIR 8)

The auditor's sealed R-CAL corpus (`eval/auditor_rcal_corpus_r142.json`,
audit branch, 12 balanced blind pairs) carries a `selection_sha256`
field that is the digest of the **selection process** (the pre-shadow
pool, the balanced-domain draw) — it is NOT recomputable from the
corpus file alone, because the process inputs are not in the file.
That was typed honest by the executor lane (c-0227).

This document defines the digest that IS recomputable from the
committed file, and the script that computes it.

## File-integrity digest (recomputable)

```
python3 scripts/rcal_corpus_digest.py eval/auditor_rcal_corpus_r142.json
```

Method (stable contract — a change requires a new record version):

```python
canonical = json.dumps(corpus["pairs"],
                       sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False).encode("utf-8")
file_integrity_sha256 = hashlib.sha256(canonical).hexdigest()
```

- Scope: the `pairs` array ONLY (every field of every pair
  participates — including the labels, which is exactly what makes the
  digest useful: the panel provably saw these bytes).
- The digest fields (`selection_sha256`) are excluded from the
  canonical form so the file can carry the value without
  self-reference.
- UTF-8, sorted keys, compact separators: no whitespace dependence.

## What each digest proves (Art. 1: name what a hash proves)

| digest | provenance | recomputable from the corpus file | proves |
| --- | --- | --- | --- |
| `file_integrity_sha256` | this script | YES | the panel ran against exactly these pair bytes |
| `selection_sha256` | the auditor's process | NO (process inputs live in the auditor's pre-registration) | HOW the pairs were selected from the pool |

## Values (R142S1)

- `file_integrity_sha256 = 3df491d57232825a6e29b42751fac9cef234c3498a666618f208e4fa0834056b`
- `selection_sha256 = 67764d0cb1d105bc6db58b9b2f96d1af5f707b29c17be4936de88e767330cdf9` (recorded, not re-derived)
- corpus file sha256 (whole file): `8bb9ec8c15c532d4` (first 16 hex)

The verifier recompute (`scripts/r142_panel_verifier.py`) pins
`EXPECTED_FILE_DIGEST` to the file-integrity value: a corpus whose
canonical digest differs from the one the executor recorded reds
before any judge output is read.

## Worldwide-lane watch (typed, no import claimed)

OpenScholar's retrieval-augmented scientific LM and Think&Cite's
self-guided attributed generation are monitored for the
grounded-generation lane (the quote-anchored re-generation, DIR 3).
No module from either is integrated in this window; the ledger stays
live (import ≠ integration).
