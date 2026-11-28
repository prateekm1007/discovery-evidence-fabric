#!/usr/bin/env python3
"""r109_d3_agreement_design.py — the R108 direction-3 PRE-REGISTRATION
record: the three agreement levers for the score-8 inter-agent bar
(>=0.7), committed BEFORE any v16 corpus scoring exists (Art. 6
anti-gaming: the design is fixed first, then the corpus is scored —
a post-hoc change needs a typed amendment record).

Levers (the auditor's own menu, fixed here in test order):
  (a) rubric tightening — every 4-level axis re-anchored on a 7-point
      scale with per-level behavioral anchors (the level table lives
      in the record; the judge prompt embeds the anchors verbatim);
  (b) agent qualification — a FIXED calibration set scored BEFORE the
      v16 corpus; an agent qualifies iff (i) test-retest self-consistency
      at temperature 0.0 on the calibration set >= 5/6 identical
      verdicts, and (ii) calibration-set agreement with the
      adjudicated calibration gold >= 0.6. Qualification NEVER sees a
      v16 item verdict (the selection is blind to the target labels —
      no selection toward the gate outcome). >=3 qualified agents
      required or the panel types PANEL_UNDER_QUALIFIED.
  (c) disagreement rules — BOTH statistics are pre-registered and
      reported side by side: mean-pairwise proportion (the gate
      clause binds to >=0.7 on this) and Krippendorff's alpha
      (nominal, 3 classes, reported alongside as the chance-corrected
      view). No third rule may be introduced post hoc.
Power note (auditor Art. 14): n=30 (the corpus convention) at p=0.7
gives a 95% CI of ~+/-0.16 (Wilson) — the bar is resolvable only
against a wide margin; the pre-registered n is 30 and an under-powered
resolution is typed UNRESOLVED, never passed on a point estimate.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "eval" / "r109_d3_agreement_design.json"

# the 7-point re-anchoring table (the R107 rubric's 4 levels -> 7,
# anchors written so two raters reading the SAME row land within one
# level; the axis set is the v2.1.0 invention rubric's)
SEVEN_POINT = {
    "novelty": {
        "1": "the mechanism is a verbatim known design; no recombination",
        "2": "a known design with one substituted component, no new interaction",
        "3": "a known design recombined; the interaction is stated but not load-bearing",
        "4": "a recombination where the new interaction is load-bearing but precedented in an adjacent field",
        "5": "a new interaction, precedented only in a distant field, with a stated transfer argument",
        "6": "a new interaction with no field precedent, but the transfer argument has one unverified premise",
        "7": "a new interaction, no field precedent, transfer argument fully verified from the served material",
    },
    "direction_correctness": {
        "1": "the claim moves the problem's own failure quantity the WRONG way or targets a different quantity while asserting the failure axis",
        "2": "no direction attributable (typed neutral anchor; coverage disclosed)",
        "3": "direction stated for a proxy quantity, not the failure quantity",
        "4": "the failure quantity is targeted; the improving direction is asserted without a mechanism link",
        "5": "the failure quantity is targeted; improving direction carried by an explicit mechanism link",
        "6": "as 5, plus a quantified expected direction with a stated source",
        "7": "as 6, plus the mechanism link is verified against the served material (not merely asserted)",
    },
    "magnitude_plausibility": {
        "1": "a percent claim beyond 10x the problem's own stated headroom",
        "2": "no percent claim attributable (typed neutral anchor)",
        "3": "percent claims >200% of stated headroom",
        "4": "percent claims >80% and <=200% of stated headroom",
        "5": "percent claims >50% and <=80% of stated headroom, source stated",
        "6": "percent claims <=50% of stated headroom with a stated source",
        "7": "as 6, plus the source is verifiable from the served material",
    },
    "testability": {
        "1": "no falsification test, or a test that cannot fail",
        "2": "a test named but with no measurable quantity",
        "3": "a measurable test whose threshold is unstated",
        "4": "measurable test + threshold, but the measurement method is unstated",
        "5": "test + threshold + method all stated",
        "6": "as 5, plus the test discriminates against at least one named alternative",
        "7": "as 6, plus the alternative discrimination is quantified",
    },
}

CALIB = {
    "source": ("the calibration set is FIXED at registration: the 12 "
               "burned v15 rows the auditor's R108 spread analysis used "
               "(the per-row scores in eval/r105s2_rubric_spread_v15.json) "
               "+ their adjudicated gold from the committed verdict "
               "bytes; the set is frozen here and never extended with "
               "v16 material"),
    "criteria": {
        "self_consistency": ">=5/6 identical verdicts on the K=6 "
                            "sampled calibration rows, re-served at "
                            "temperature 0.0 (the retest prompt is "
                            "byte-identical to the first)",
        "calibration_agreement": "mean-pairwise agreement with the "
                                 "adjudicated calibration gold >= 0.6",
        "qualified_panel_min": 3,
    },
    "blindness": ("qualification consumes ONLY calibration-set bytes; "
                  "no v16 item verdict exists at qualification time and "
                  "none may be consulted — the selection must not "
                  "correlate with the gate outcome"),
}

RULES = {
    "gate_statistic": "mean-pairwise proportion >= 0.7 (the auditor's "
                      "clause binds HERE)",
    "reported_alongside": "Krippendorff's alpha (nominal, 3 classes), "
                          "computed from the same per-item judgment "
                          "matrix; reported every run, gate-binding "
                          "never (the two statistics answer different "
                          "questions: raw overlap vs chance-corrected "
                          "agreement)",
    "pre_registration_status": "FIXED before v16 scoring; amendments "
                               "typed, dated, and disclosed in the "
                               "round record",
}

POWER = {
    "pre_registered_n": 30,
    "basis": "the corpus convention (30 items) + auditor Art. 14",
    "ci_note": ("Wilson 95% CI at n=30, p=0.7 is ~[0.51, 0.85] — "
                "point-estimate passing at exactly 0.70 is typed "
                "UNRESOLVED unless the CI excludes 0.70 from below "
                "(i.e. the lower bound clears 0.70 requires n or "
                "agreement substantially above the bar)"),
}

rec = {
    "record": "R109_D3_AGREEMENT_DESIGN/1.0.0 (PRE-REGISTRATION)",
    "at": datetime.now(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ (sandbox clock, TRUE UTC)"),
    "executor": "builder-r109s1",
    "claim": "c-0135 (r109-lane-d2d3-score8; the R108 direction 3)",
    "status_anchored": ("the R108 measured agreement 0.5875 is "
                        "sub-chance-adjacent, not noise: the levers "
                        "target the three mechanisms that produce it "
                        "(coarse scales mask real disagreement; "
                        "unqualified raters inject variance; a single "
                        "rule hides chance agreement)"),
    "seven_point_anchors": SEVEN_POINT,
    "agent_qualification": CALIB,
    "disagreement_rules": RULES,
    "power": POWER,
    "anti_tuning": ("this record is the pre-registration: it lands on "
                    "the queue BEFORE any v16 corpus exists; the "
                    "auditor's v16 authoring (direction 4) and any "
                    "panel rerun execute against THIS design, and a "
                    "design change after scoring starts is a typed "
                    "finding, not a fix"),
    "typed_conclusion": ("the three levers are fixed and testable; "
                         "the acceptance test stays the auditor's: "
                         "inter-agent proportion >= 0.7 on the v16 "
                         "corpus under these pre-registered rules"),
}
OUT.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n",
               encoding="utf-8")
print("wrote", OUT, "| axes anchored:", len(SEVEN_POINT))
