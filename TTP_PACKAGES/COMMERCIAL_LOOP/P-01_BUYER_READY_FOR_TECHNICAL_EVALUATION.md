# P-01 — Buyer-Ready for Technical Evaluation

## Status

**P-01 is BUYER_READY_FOR_TECHNICAL_EVALUATION** as of R277 (2026-08-25).

This is a sub-state of PROTOTYPE_READY. It means: a serious OEM engineer can today download the package, run the simulator on their own machine, audit the code, attack the design, and decide whether to request the V0 bench prototype spec.

## What "buyer-ready for technical evaluation" means

1. **The simulator runs on any machine with Python 3.8+.** No external dependencies. No installation friction.
2. **The simulator falsifies the original claim.** This is a feature, not a bug. The buyer sees an honest engineering finding (strict dual-invariant fails, graceful degradation succeeds) — not a sales pitch.
3. **The external validation handoff folder is ready.** Frozen design, frozen protocol, pre-registered expected metrics, blinding protocol, result submission schema, reproducibility checks. A lab can run validation without trusting us.
4. **The buyer economic questionnaire is ready.** Every modelled economic claim has a structured question waiting for the buyer's verified number.
5. **The buyer feedback intake schema is ready.** Any feedback (technical question, economic challenge, design suggestion, prototype request, rejection) becomes a machine-actionable task that enters the evidence loop.

## What "buyer-ready for technical evaluation" does NOT mean

1. It does NOT mean the package is transaction-ready. Buyer cannot pay $500K and receive a working implant. They would receive a technology package (control law spec + simulator + test protocol + IP dossier) that they would then integrate into their own R&D program.
2. It does NOT mean the strict dual-invariant claim is true. The simulator falsified it. The honest claim is graceful degradation.
3. It does NOT mean the economics are proven. They are modelled, with explicit BUYER_UNVERIFIED labels.
4. It does NOT mean IP is cleared. The buyer's IP counsel must perform independent FTO analysis.

## The outreach goal

Per CEO directive R277: "The purpose of outreach is to discover: What evidence would make a real OEM engineer say 'send me the prototype.' That feedback must enter the loop."

We are NOT trying to close a transaction in R278. We are trying to start a conversation that produces feedback. The conversation can take many forms:

- "Your simulator's prediction of 22 mmHg peak ICP is interesting. What happens if you increase F_MAX to 0.5?"
- "We don't believe the predictor is realistic. Have you tested with real occlusion timecourses?"
- "The dual-invariant claim is too strong. Can you reframe it?"
- "Send us the V0 bench prototype spec — we'll build it in our lab."
- "Too early for us. Come back when you have V1 implantable data."

Each of these is valuable. Each enters the BUYER_FEEDBACK_INTAKE_SCHEMA. Each shapes the next iteration.

## What we send to a buyer who says "send me more"

1. Link to the GitHub repository (specific commit hash)
2. P-01_FULL_TTP.json (the 15-element dossier)
3. P-01_PROTOTYPE/ folder (9 artifacts + EXTERNAL_VALIDATION_HANDOFF/)
4. COMMERCIAL_LOOP/BUYER_ECONOMIC_QUESTIONNAIRE_TEMPLATE.json
5. COMMERCIAL_LOOP/BUYER_FEEDBACK_INTAKE_SCHEMA.json (so they know how their feedback will be used)
6. This memo (BUYER_READY_FOR_TECHNICAL_EVALUATION.md)

## What we ask of the buyer

1. Read the simulator code. (~30 minutes)
2. Run the simulator on their machine. (~5 minutes)
3. Attack the design. (open-ended — try scenarios we didn't include)
4. Respond to the buyer economic questionnaire. (partial response is fine)
5. Tell us what evidence would change their evaluation. (the most important question)

## What we do NOT ask of the buyer

1. We do not ask them to sign an NDA before seeing the simulator. The simulator is published openly.
2. We do not ask them to commit to a transaction. The first conversation is exploratory.
3. We do not ask them to validate our claims. We ask them to challenge them.
4. We do not ask them to share confidential information. The economic questionnaire asks for numbers they are willing to share.

## Timeline expectation

- R278 (this round + 1): Send 10 outreach emails. Receive 2+ responses.
- R279-R280: Convert 1+ response into technical evaluation conversation.
- R281-R282: Convert 1+ technical evaluation into V0 bench prototype request.
- R283-R284: V0 bench prototype built by buyer lab. Results returned.
- R285+: Based on bench results, decide whether to engage on V1 implantable prototype (the $200-500K decision).

This is a multi-year process. We are at the very beginning.
