#!/usr/bin/env python3
"""Adjust the TVM v2 FRONTIER_ENTRY_PROPOSAL prompt from the v2.0
per-record call pattern to the per-RUNG batch pattern — BEFORE the
v2.1 seal (Art. LIX forbids only POST-unseal changes; this is a
pre-seal adjustment, disclosed, and the v2.1 preregistration pins
the adjusted template's hash).

Why: the v2.0 template was authored for one source record per call,
which conflicts with the sealed 12-call TVM construction budget
(v1 semantics: 12 rung constructions, each seeing its retrieval
pool). The operator's Phase L requires 'no expanded budget', so the
call unit must stay the RUNG; the prompt now lists the rung's
retrieved records and each proposal cites exactly one
source_record_id.

The serialization contract, failure states, and proposal-object
schema are UNCHANGED; only the input framing (record list instead
of single record) and explicit value/year field guidance change.
Version 1.0.0 -> 1.1.0.
"""
import json
from pathlib import Path

P = Path(__file__).resolve().parents[1] / "R412" / "GRADIENT_V2" / \
    "PROMPTS" / "TVM_V2_FRONTIER_ENTRY_PROPOSAL.json"

TEMPLATE = """You are proposing candidate entries for a Technology Velocity Map (TVM). You see one capability-family search brief (family, measurement dimension, required regime, search vocabulary) and the retrieved source records for one capability rung (each with record_id, title, abstract).

STRICT SERIALIZATION CONTRACT — a proposal that violates any term is discarded by the deterministic verifier, with no retry:
1. quoted_span MUST be an EXACT contiguous substring of the cited record's title+abstract text. Copy it character-for-character. Do not paraphrase, do not fix typography, do not merge sentences.
2. The value field must quote the measured value exactly as the cited record states it, and that value text MUST appear inside your quoted_span. Accepted canonical forms: a point (0.42), a value with uncertainty (0.42 ± 0.03), a stated range (0.1–10, 10 to 20), an approximation (~50, approximately 50), an inequality (>100, ≤ 3.5, at least 12), scientific notation (3.2e-2, 1.2 × 10^3), or an explicit statement of non-numericity (varies, not reported).
3. DO NOT compute, convert, average, or round any number. If the record says 0.42 ± 0.03 you write exactly that; you never write 0.39–0.45 yourself (the deterministic normalizer derives the interval).
4. The year field must be the year text exactly as the cited record states it (bare year 2023, qualified year "2023 (study)", year range 2018–2024, or prepositional form "in 2021") AND that year text must appear in the cited record's title+abstract. Never compute or infer a year.
5. trajectory_dimension MUST be one of: performance, cost, efficiency, reliability, manufacturing, deployment. NEVER investment, talent, or experimental concentration — those cannot establish capability.
6. If the record does not state a measured value, do not propose an entry for it. Never estimate.
7. Each proposal cites exactly one source_record_id from the list. A record_id not in the list is discarded (RECORD_ID_NOT_IN_RETRIEVED_POOL).

Emit one JSON object per proposal with fields: domain, capability_rung, indicator, metric, quoted_span, value, unit, year, trajectory_dimension, source_record_id, citation, occurrence_index (0-based index of the quoted span within the cited record's title+abstract if it occurs more than once).

Emit a JSON array of these objects (possibly empty). No prose, no markdown fences, no commentary — the array alone.

FAILURE STATES you will be measured against (the deterministic verifier emits these, not you): RECORD_ID_NOT_IN_RETRIEVED_POOL, SPAN_NOT_FOUND, SPAN_AMBIGUOUS_REQUIRES_INDEX, VALUE_TEXT_NOT_IN_QUOTED_SPAN, YEAR_NOT_IN_RECORD_TEXT, FLAT_VALUE_DISAGREES_WITH_SPAN, NON_PRIMARY_SIGNAL_AS_CAPABILITY, canonical_value_not_numeric, flat_value_disagrees_with_canonical."""

doc = json.loads(P.read_text())
old_version = doc["version"]
doc["template"] = TEMPLATE
doc["version"] = "1.1.0"
doc["provenance_note"] = (
    "v2.0 (frozen 2026-09-06) was authored for a per-record call "
    "pattern, conflicting with the sealed 12-call TVM construction "
    "budget's per-rung semantics. Adjusted to the per-rung batch "
    "BEFORE the v2.1 seal (pre-seal change, disclosed; Art. LIX "
    "governs only post-unseal changes). The serialization contract, "
    "failure states, and deterministic verifier are unchanged. The "
    "value/year fields now carry the record's own text (span-bound, "
    "checked by VALUE_TEXT_NOT_IN_QUOTED_SPAN / "
    "YEAR_NOT_IN_RECORD_TEXT) in addition to quoted_span."
)
doc["batch_semantics"] = {
    "call_unit": "one capability rung per LLM call",
    "input": "the rung's retrieval pool (record_id/title/abstract)",
    "output": "JSON array of proposals, each citing one "
              "source_record_id",
    "budget_alignment": "tvm_construction_llm_calls_max = 12 "
                        "(sealed v1 budget, unchanged)",
}
P.write_text(json.dumps(doc, indent=1) + "\n")
import hashlib
print(f"template adjusted: {old_version} -> {doc['version']}")
print("new template sha256:",
      hashlib.sha256(P.read_bytes()).hexdigest())
