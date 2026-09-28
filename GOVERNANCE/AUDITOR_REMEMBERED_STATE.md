# Auditor Remembered State / Anti-Entropy Checkpoint v1

**Purpose:** preserve continuity of the auditor's understanding of the project so that a long-running audit program does not create entropy by forgetting settled decisions, current direction, standing blockers, or the latest accepted next move.

**Authority:** continuity aid only. This file never overrides the Constitution, live repository state, deployment state, or other higher-authority evidence. Memory is not proof.

## Core principle

> **Remember the project as far as the available evidence permits, so the next audit starts from the current direction rather than from a blank slate.**

The auditor must actively maintain a remembered model of:

- why the project exists;
- what the current product is supposed to do;
- which architectures and decisions are settled;
- which approaches have already been rejected and why;
- which repositories and deployments are authoritative;
- what the last audit actually established;
- what remains unproven;
- what the coder is currently implementing;
- what the next decisive verification is.

## Anti-entropy rule

Before prescribing new work, the auditor must ask:

1. **What have we already decided?**
2. **What has already been built?**
3. **What has already been rejected, and for what reason?**
4. **What is the current authoritative state?**
5. **What is the current product direction?**
6. **What would my proposed change accidentally reopen, duplicate, or reverse?**
7. **What new evidence justifies changing direction?**

If there is no new evidence, do not casually reverse a settled decision.

## Remembering is not invention of history

The auditor must never fill gaps in memory with plausible detail.

When exact state cannot be recovered:

`UNKNOWN` → `RECONSTRUCT FROM AUTHORITATIVE SOURCES` → `PROCEED`

not:

`UNKNOWN` → `ASSUME` → `DIRECT CODER`

## Required refresh sources

At the start of each substantive audit, refresh this checkpoint against as many of the following as are relevant and available:

- current engine repository default branch and commit;
- current buyer/technology-transfer repository and commit;
- current deployed service identity;
- current Constitution version/hash;
- current auditor governance versions/hashes;
- latest relevant coder worklog and commit history;
- active branches and pull requests;
- current production path;
- current unresolved standing notes;
- latest fresh user-path evidence.

## State categories

Every remembered item should be mentally classified as one of:

`SETTLED` — intentionally established and not to be reopened without new evidence.

`ACTIVE` — currently being implemented or verified.

`BLOCKED` — known blocker awaiting evidence, owner action, or repair.

`REJECTED` — previously tested and rejected, with reason preserved.

`SUPERSEDED` — replaced by a later authoritative decision.

`UNPROVEN` — plausible or reported, but not yet independently demonstrated.

`UNKNOWN` — insufficient evidence to reconstruct accurately.

## Current project continuity template

This section is intentionally a compact checkpoint. It should be refreshed when the auditor performs a substantive state reconstruction. It must never be treated as a substitute for the authoritative sources.

### Mission

Build a world-class AI discovery and invention machine that turns difficult user problems into credible technology packages a real company can evaluate, license, build, acquire, or commission the decisive experiment for.

### Product principle

Toscanini is an invention/discovery system, not a patent court. The machine should continually investigate, invent, challenge, evolve, explain, visualize, and package. Formal patentability, claim drafting, infringement/FTO, and legal opinions remain downstream legal work.

### Product experience

The target public experience is a calm, high-quality, Claude-influenced research/invention workspace in which the invention is the artifact: a clear technical essay in the main workspace and an inspectable 3D/system artifact beside it, with evidence, causal explanation, engineering state, experiment path, and package export available without exposing raw machine state as the primary UX.

### Two-repository roles

Engine repository: `prateekm1007/discovery-evidence-fabric` — factory, epistemic machinery, discovery pipeline, engineering, 3D generation, provenance, tests, runtime.

Buyer repository: `prateekm1007/technology-transfer-portfolio-15` — buyer-distribution authority for released technology packages.

### Deployment

Canonical Hugging Face production target (R447-SPACE-OWNER, 2026-09-12): `https://huggingface.co/spaces/prateekm1/toscanini-prod-validation` (direct app: `https://prateekm1-toscanini-prod-validation.hf.space`, private). The machine-readable authority is `R447/CANONICAL_HF_SPACE_RECORD.json`. It is the ONLY HF production target — no additional Space may be created, and the directive's premise of a second Space was not verified by any live channel at selection time. Legacy Render host (unchanged, not an HF target): `https://toscanini-engine-docker.onrender.com/`

Always verify the current deployment identity before making a completion claim.

### Settled architectural decisions

- Evidence precedes assertion.
- Live state beats narrative.
- Built is not wired.
- Fresh production path is required for product claims.
- One canonical invention state should drive website, 3D, PDF, ZIP, experiment plan, and package metadata.
- CadQuery/OCP/OCCT is the engineering geometry authority.
- Blender is a visualization/rendering layer, never the engineering or physics authority.
- Three.js/React Three Fiber is the browser presentation layer for GLB/glTF.
- Conceptual 3D may represent an invention honestly when engineering geometry is not yet earned, but conceptual geometry must never be presented as validated engineering geometry.
- Model/provider availability is dynamic and must be measured.
- Retrieval/source failure is not evidence absence.
- Attacker verdict authority must be calibrated before it is allowed to act as a terminal judge.
- Challenge → diagnosis → causal evolution is part of the invention loop.
- The website should not expose raw internal JSON or audit machinery as the primary human experience.

### Standing blockers / unproven areas

Refresh these from live state; do not assume they are unchanged.

- Attacker calibration status.
- Retrieval adequacy and blind re-verification.
- Fresh-run provider compatibility.
- Fresh-run invention → 3D → package reliability.
- Real physical validation.
- Real buyer evaluation.
- R547 (2026-09-28): the discovery funnel's current measured cliff is
  MECHANISM_SPACE (mechanism-space distinctness yields <2 materially
  distinct mechanisms on ordinary single-synthesis production runs —
  the production lean path is structurally capped at ONE generated
  candidate, measured at `R547/R547_MECHANISM_SPACE_CEILING.json`).
  This is a DISCOVERY CAPABILITY deficit, NOT an infrastructure
  failure (Art. LXXXIII: it is the authorized next bottleneck target,
  but the corrective infrastructure/proof reconciliation round must
  close first). The end-to-end discovery/invention loop and the
  reality/causal-update loop remain unproven by a fresh production run
  that crosses the full ladder (mechanism diversity → attack →
  contradiction → experiment → adjudication → engineering → reality →
  causal update → technology-transfer package).

### Recent known lessons

- Historical P-04/P-11 package quality is a reference standard, not proof for newly generated packages.
- A separate bridge repository can be technically correct yet still fail to improve the production path if not integrated.
- A green HTTP probe does not prove a model can satisfy Toscanini's structured generation protocol.
- A model/provider can be reachable but operationally unsuitable.
- An honest `No 3D` message can still represent an unacceptable engineering defect when the system could recover.
- A generated invention can solve the wrong problem even when its internal narrative is coherent.

### Last verified behavior

Populate from the most recent authoritative audit. State precisely what was observed, what was inferred, and what remains unproven.

### Latest accepted coder directive

Populate from the authoritative worklog/commit. Include the remaining acceptance criteria so the auditor does not reissue completed instructions.

### Next decisive verification

Populate with the smallest fresh test that would most reduce uncertainty about the current dominant product bottleneck.

## Update discipline

This file may be updated only to improve continuity. It must not be used to rewrite history, change sealed experiment results, or make an unproven capability appear proven.

When a remembered item changes because of new evidence, preserve the distinction between the previous remembered state and the newly observed authoritative state.

## Auditor declaration

Before every substantive audit, the auditor should be able to state internally:

> **I have reconstructed what this project is trying to become, what has already been settled, what is currently being built, what is still blocked, and what remains unproven. I will not create entropy by repeating, reversing, or bypassing prior decisions without new evidence.**
