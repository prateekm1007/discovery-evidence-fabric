"""discovery_fabric/engine/prompts.py — the CANONICAL PROMPT CONSTANTS
as ENGINE code (the R131-F2/DIR-3 migration; the F63 rule: capability
logic lives in the engine, not scripts/).

Lineage (forward-only, Art. 16 accounting):
  - the judge rubric head is eval/run.py's committed _rubric_prompt
    contract (criteria + the JSON output contract); the per-axis
    suffix is scripts/r10_axis_suffix_v2.py's committed
    PER_AXIS_SUFFIX_V2 (the F28 calibrated anchors). THIS module is
    the canonical POINTER — the historical script/eval bytes are
    never rewritten; every NEW instrument imports from here.
  - the R133 lever (b): the FORCED-CHOICE prefer contract. The
    original judge contract allowed "TIE" on prefer; the auditor's r5
    labels carry NO ties, so a tie-capable schema was miscalibrated
    against a never-tie ground truth (the R132 diagnosis). The
    pair-judging contract here REMOVES the lazy TIE out.

Determinism: pure constants, zero network, zero LLM. CI pins the
bytes (tests/test_engine_prompts.py).
"""
from __future__ import annotations

# The six rubric criteria (byte-faithful to eval/run.py CRITERIA —
# the committed instrument; the pointer is canonical from R133).
RUBRIC_CRITERIA = {
    "a_answered": "answers the asked question",
    "b_user_vars": "uses user-stated variables",
    "c_prediction": "gives a specific testable prediction",
    "d_evidence": "grounded in the provided evidence",
    "e_clarification": "uses the user's clarification answer correctly",
    "f_novelty": "gives a specific, non-obvious design (not the generic "
                 "default)",
}

# The calibrated per-axis scoring suffix (byte-faithful to
# scripts/r10_axis_suffix_v2.py PER_AXIS_SUFFIX_V2 — the F28 anchors).
PER_AXIS_SUFFIX = """

=== PER-AXIS SCORING CONTRACT (required) ===
After the rubric gates, also score EACH answer on four axes, 1 (poor)
to 5 (excellent), as integer keys in the SAME single JSON object:
  "N_A": <A novelty 1-5>,   "F_A": <A feasibility 1-5>,
  "T_A": <A testability 1-5>, "C_A": <A constraint-compliance 1-5>,
  "N_B": <B novelty 1-5>,   "F_B": <B feasibility 1-5>,
  "T_B": <B testability 1-5>, "C_B": <B constraint-compliance 1-5>
Axis definitions (CALIBRATED — read carefully):
  novelty: how far the answer's MECHANISM departs from the generic
    field-standard practice toward a specific, non-obvious one.
    CALIBRATION: an answer that states or applies the field-standard
    practice scores 1-2 on novelty BY DEFINITION — even when executed
    excellently, at length, or with polished numbers; execution
    quality belongs to the other axes, never to novelty. A genuine
    departure (new mechanism, new measured quantity, new test
    principle) scores 4-5; a standard practice with one specific
    twist scores 3. Compare MECHANISMS, not prose, length, or
    familiarity.
  feasibility: could the proposed change actually be implemented and
    serve as specified with existing engineering means WITHIN the
    stated constraints. CALIBRATION: rate workability, not elegance
    or cost-optimality — a sound physical mechanism with concrete
    parameters and a realistic data/test path scores 3 or higher;
    reserve 1-2 for designs that are physically impossible,
    unit-incoherent, violate a stated constraint, or depend on
    hardware/compute the answer never declares. Declared, justified
    dependencies (costed edge compute, standard test equipment) do
    NOT lower the score.
  testability: is the falsification test concrete and capable of
    killing the proposal (5 = specific pass/fail protocol with
    thresholds; 1 = vague or no test).
  constraint_compliance: does the answer respect every stated user
    constraint verbatim (5 = all constraints explicitly respected;
    1 = constraint violated or ignored).
Score each answer INDEPENDENTLY against these definitions; do not
drift toward the middle — two answers may both be high or both low on
an axis, and the standard-practice answer's novelty is 1-2 whatever
its other axes say.
"""

# The R133 lever (b) — the FORCED-CHOICE prefer contract (the TIE
# lazy-out REMOVED; the auditor's labels are never-tie).
FORCED_CHOICE_SUFFIX = """
Then state your overall preference. FORCED CHOICE: "prefer" MUST be
"A" or "B" — a tie is NOT available. If the two answers are genuinely
equal in quality, choose the one with fewer fabrication risks (fewer
numbers or citations that the evidence packet does not support).
Your response is ONE JSON object with the rubric keys AND the eight
axis keys AND "prefer" ("A" or "B" only). No other text."""

# The R134 lever (a) — the COMPARATIVE CHAIN-OF-THOUGHT contract
# (frozen in eval/r134_panel_prereg.json before any panel call; the
# expert weighting operationalizes the auditor's dev-fu-001 ruling:
# the baseline dominated a1 on novelty 2>1 AND testability 4>3).
COT_COMPARATIVE_SUFFIX = """
Before the JSON, REASON as a domain-expert judge comparing the two
answers (2-6 sentences):
- For each axis (novelty, feasibility, testability,
  constraint-compliance) state in one sentence why EACH answer earns
  its score — compare MECHANISMS, not prose, length, or polish.
- EXPERT WEIGHTING for the preference: novelty and testability
  DOMINATE. An answer that applies the field-standard practice
  excellently and at length is a WORSE answer than one with a
  genuinely novel mechanism and a concrete falsification test, even
  when the standard answer is more polished. Feasibility and
  constraint-compliance act as gates (an infeasible or
  constraint-violating answer cannot win), not as tiebreakers.
- Finish your reasoning, then output the JSON. FORCED CHOICE:
  "prefer" MUST be "A" or "B" — a tie is NOT available. If the two
  answers are genuinely equal, choose the one with fewer fabrication
  risks.
Your response: your reasoning FIRST, then ONE JSON object with the
eight axis keys AND "prefer" ("A" or "B" only). The JSON object must
be the LAST thing in your reply."""

# The reviewer fix schema (byte-faithful to scripts/r127_phaseA_gate.py
# FIX_SCHEMA — the structured-output contract the parse-first-try
# metric is based on).
REVIEWER_FIX_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "reviewer_fix",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {"corrected_proposal": {"type": "string"}},
            "required": ["corrected_proposal"],
            "additionalProperties": False,
        },
    },
}

AUTHORING_DIRECTIVE = (
    "You are an engineer. Propose ONE mitigation for the failure "
    "described in the problem, under the stated constraint. Answer "
    "with the mitigation proposal (mechanism, implementation, and the "
    "measures it relies on)."
)

# IMPROVED_DIRECTIVE = the r122_lever_prereg v1 bytes (567c, the
# frozen baseline reference) + the M5 minimal-diff clause (195c) —
# the r130s3 fold's 762c composite, byte-audited (R130S3). The v1
# bytes live in eval/r122_lever_prereg.json the_lever.
# improved_directive_bytes; the engine constant is the COMPOSITE,
# pinned by CI against those bytes.
M5_DIFFMIN_CLAUSE = (
    "\n\nMINIMAL-DIFF RULE: change ONLY the sentences the findings "
    "touch. Every other sentence of the ORIGINAL proposal is carried "
    "over verbatim. Do not restate, reorganize, or reword untouched "
    "content."
)


def improved_directive() -> str:
    """The composite reviewer directive (v1 + M5), assembled from the
    committed prereg bytes at call time — the engine never carries a
    second copy of the v1 text (single canonical source)."""
    import json
    from pathlib import Path
    repo = Path(__file__).resolve().parents[2]
    v1 = json.loads(
        (repo / "eval" / "r122_lever_prereg.json").read_text(
            encoding="utf-8"))["the_lever"]["improved_directive_bytes"]
    return v1 + M5_DIFFMIN_CLAUSE
