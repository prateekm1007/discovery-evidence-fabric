#!/usr/bin/env python3
"""r70_v75_deliverable_bind.py — the DELIVERABLE-CLASS generation
directive (AM63 directive 1, F75). Appended to BOTH generation
contracts (SYS_A1_INT_V72 interventions and SYS_A1F_V5 predictors):
the generation side of the bind whose detection side lives in
scripts/r70_deliverable_class_scan.py. Neutrality preserved: the
clause constrains the ARTIFACT CLASS (identity/refusal/deliberation),
never the mechanism choice or outcome."""

V75_DELIVERABLE_BIND = """
M. DELIVERABLE-CLASS BIND (F75): the reply IS the deliverable
   artifact and nothing else.
   - Open DIRECTLY with the artifact's required heading. NEVER open
     with, or interject, a refusal ("I cannot fulfill ...", "I do not
     generate ..."): if a stated constraint looks impossible, deliver
     the best-conforming artifact within the constraints and mark the
     tension in the CONSTRAINT-BIND / RISK field instead of refusing.
   - NEVER state or hint an assistant identity, model name or vendor
     ("I am <model>", "an AI assistant", "developed by ..."): the
     deliverable is an engineering document with no author voice.
   - NEVER leak internal deliberation into the artifact: no "Wait,",
     "No—Correction", "Correction:", "Let me reconsider", "Hmm,".
     Resolve the reasoning silently and ship only the final position.
   A violation of this bind is a typed deliverable-class defect and
   the machine will repair it before recording the row.
"""
