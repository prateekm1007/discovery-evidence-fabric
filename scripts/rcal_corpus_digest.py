#!/usr/bin/env python3
"""rcal_corpus_digest.py — the R-CAL corpus digest canonicalization
(R142 DIR-8 / R142-F4): make a digest RECOMPUTABLE from the committed
corpus file alone.

Two digests, honestly distinguished (Art. 1: name what a hash proves):

1. FILE-INTEGRITY digest (this script's output):
   sha256 over the CANONICAL FORM of the corpus file: the `pairs` array
   re-serialized with sorted keys, compact separators, UTF-8 — every
   field EXCEPT the digest fields (`selection_sha256`) participates.
   Anyone with the committed file recomputes this byte-for-byte. It
   proves: the panel saw exactly these pairs.

2. SELECTION-PROCESS digest (`selection_sha256` in the file):
   the auditor's digest of HOW the pairs were selected (the pre-shadow
   pool, the balanced-domain draw). NOT recomputable from the corpus
   file alone — the process inputs are not in the file. The corpus
   file RECORDS the value; the auditor's own artifacts (the
   pre-registration on the audit branch) carry its evidence. This
   script does not re-derive it and never claims to (typed honest).

Method (stable contract — never change without a new record version):
  canonical = json.dumps(pairs, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False).encode("utf-8")
  file_digest = sha256(canonical).hexdigest()
"""
import hashlib
import json
import sys
from pathlib import Path


def canonical_file_digest(corpus: dict) -> str:
    pairs = corpus.get("pairs")
    if not isinstance(pairs, list):
        raise SystemExit("REFUSED: the corpus carries no pairs array")
    blob = json.dumps(pairs, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else \
        Path("eval/auditor_rcal_corpus_r142.json")
    corpus = json.loads(path.read_text(encoding="utf-8"))
    dig = canonical_file_digest(corpus)
    out = {
        "record": "RCAL_CORPUS_FILE_DIGEST/1.0.0",
        "source_file": str(path),
        "method": ("sha256 over json.dumps(pairs, sort_keys=True, "
                   "separators=(',',':'), ensure_ascii=False) — the "
                   "digest fields excluded from the canonical form"),
        "file_integrity_sha256": dig,
        "recorded_selection_sha256": corpus.get("selection_sha256"),
        "selection_digest_note": ("the selection-process digest is the "
                                  "auditor's; not recomputable from "
                                  "the corpus file alone (typed "
                                  "honest, R142-F4)"),
    }
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
