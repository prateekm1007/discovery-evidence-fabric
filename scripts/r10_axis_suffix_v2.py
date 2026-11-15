"""r10_axis_suffix_v2.py — AM10 D3 (F28) calibrated per-axis scoring
suffix. The anchors target the MEASURED defect classes from the stage-2
reproduction (bench-p02 novelty reversal; feasibility harshness 1 vs
auditor 3) — they sharpen the DEFINITION of each axis; they do not tune
scores toward a desired verdict. The adversarial gold-set check
(good/bad pairs must still separate) guards the Art. XXX failure mode
('what would make this test pass while the system is still wrong': a
flattened judge that ties everything would also 'fix' kappa — the gold
gate refuses that outcome)."""

PER_AXIS_SUFFIX_V2 = """

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
Your response is ONE JSON object with the rubric keys AND the eight
axis keys AND "prefer". No other text."""
