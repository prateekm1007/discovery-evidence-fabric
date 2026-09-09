# FEEDBACK TO CODER 1 — from the R442-PREP production visual join

**From:** Coder 2 (presentation layer)
**To:** Coder 1 (engineering geometry authority — CadQuery/OCCT bridge)
**Round:** R442-PREP, 2026-09-10
**Status:** FEEDBACK — no visual-layer compensation was applied (R442 boundary: a presentation defect is never "fixed" in the renderer; the render stays faithful and the defect comes back here)

## Evidence basis

Two genuinely fresh production inventions, end to end through production
at commit 33e5d6d9:

| Case | Run | Problem | Canonical GLB sha256 (prefix) |
|------|-----|---------|-------------------------------|
| A | ts_ef8a3f281c94 | benchtop autosampler (multi-part architecture) | `5a1815ee…` |
| B | ts_4c86d5642e99 | countercurrent heat-recovery module (helical coil) | `22de99c0…` |

## DEFECT 1 — the generic chassis dominates every invention

Both GEOMETRY_SPECs declare the same generic chassis skeleton with
**byte-identical dimensions**:

```
housing   min [-1.55, 0.5, -1.55]   max [1.55, 3.1, 1.55]     (both cases)
load_path min [-2.3, -0.0, -1.7]    max [2.3, 3.75, 1.7]      (both cases)
```

Consequence (measured): the two DIFFERENT inventions produced
**byte-identical hero/poster/dimension/turntable/orthographic renders**.
A buyer comparing the two technologies' hero images sees the same
product. The camera solve and grounding are derived from the model
extents, so identical chassis extents give identical framing — the
compiler is faithful; the geometry is generic.

**Ask:** the engineering bridge should derive part dimensions from the
invention's actual mechanism parameters (the spec already carries
`technology_class` / component roles — the dims ignore them), so that
two different mechanisms produce two different architectures.

## DEFECT 2 — overlapping module placement (Case A)

Case A's four modules (`module_01..04`) all occupy the **same bounding
box** `[-2.83, 3.75, 0.72] -> [-1.88, 4.5, 1.57]`: four parts stacked at
one location. The hero shows ONE cube; three parts are invisible. The
explode view separates them (which is how the defect was found).

**Ask:** part placement should be non-overlapping (or intentionally
assembled with recorded mating interfaces). A same-cell stack of four
distinct named parts is an engineering-realization artifact, not an
architecture.

## DEFECT 3 — enclosed sub-parts with no visual access (Case B)

Case B's `bearing` and `spring` sit entirely INSIDE the `housing`
volume (bearing `[-0.62, 1.18, -0.62] -> [0.62, 2.46, 0.62]` inside
housing `[-1.55, 0.5, -1.55] -> [1.55, 3.1, 1.55]`). They are invisible
from every exterior view; only the section plane reveals them. If this
is a bore-seated assembly it needs a housing bore feature (visible
cutout/access) in the geometry; as-built it reads as interference.

**Ask:** either open the housing (bore/section feature) or place the
sub-assemblies so the architecture reads externally. The interface node
`link_spring__housing` exists — let the geometry express it.

## What Coder 2 did NOT do (boundary compliance)

- did not add, remove, move, or re-material any part in the renderer;
- did not tune the camera, lighting, or occupancy to hide the overlap;
- did not weaken any gate rule (the gate PASSes on both cases because
  presentation quality is genuinely acceptable — the defects are
  engineering defects, and Art. XXVIII forbids the visual layer from
  promoting or demoting engineering status);
- filed this document instead.

## Suggested verification for Coder 1 (not prescribed, offered)

A cheap engineering-side non-interference witness (e.g., per-pair bbox
intersection + volume check over named parts at build time) would have
caught DEFECT 2 and flagged DEFECT 3 at the geometry source, before any
render. The visual gate deliberately does not own this check.
