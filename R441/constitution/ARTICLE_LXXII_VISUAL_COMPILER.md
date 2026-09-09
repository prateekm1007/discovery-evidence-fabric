# ARTICLE LXXII — No 3D Artifact Ships Without Passing the Visual Compiler

**Ratified:** 2026-09-10 (Round R441)
**Amends:** Constitution v2.2.0 → v2.3.0
**Sponsor:** Operator directive R441 ("World-Class 3D Pipeline Constitution"),
codified per the amendment process (Art. XXXI: every correction creates a
memory artifact; Art. X: one canonical authority).

## Full text

> **No 3D artifact ships without passing the Visual Compiler.**
>
> A 3D artifact is not complete because geometry exists. It is complete
> only after the canonical geometry has been transformed by the Visual
> Compiler into a deterministic presentation set (Hero, Turntable,
> Exploded, Section, Orthographic, Dimension, Poster), passed the Visual
> Quality Gate, and the exact same approved render has been embedded in
> both the website and the technology package PDF. If any visual gate
> fails, the Hero is suppressed and the package is blocked from release.

## What the article governs

1. **The pipeline, not prompts, guarantees quality.** Every technology
   package is forced through the same deterministic visual pipeline
   (`discovery_fabric/engine/visual_compiler/`); no render reaches a
   buyer surface by ad-hoc craft.
2. **The Visual Quality Gate is an anti-entropy verifier** in the
   Constitution's own sense: it re-measures the saved pixels with its
   own tools (Art. III — the verifier never trusts the claimant), and
   its rules carry operator-directive provenance (Art. XXVII — no
   threshold invention): hero occupancy 70–85% on the confining frame
   dimension, no clipping, contact shadow present, grounded base inside
   the 80–95% composition window, 100% semantic materials from
   component type, 100% node naming, geometry identity (the exported
   GLB re-exports the SAME vertices), poster parity with the hero, and
   exactly ONE primary viewer on the technology page.
3. **Fail closed** (Art. V): a gate that cannot run (renderer skipped,
   artifact missing) is `NOT_RUN` — which suppresses the hero and
   blocks release exactly like a FAIL. Unknown never passes as good
   (Art. XXV).
4. **One render, every surface.** The website hero, the package PDF
   cover (page 1 — the PDF Constitution), and the poster are the SAME
   approved render (identical scene spec sha256, identical source
   bytes, parity re-measured by the gate). A gate FAIL suppresses the
   hero in EVERY medium simultaneously — nothing ships a render the
   gate rejected.

## Constitutional ancestry

- **Art. XXXVI** (TECHNOLOGY_TRANSFER_READY): presentation completeness
  is part of the manufactured-asset completion standard; LXXII extends
  it to the visual layer.
- **Art. XLV** (generator/verifier separation): scene_builder /
  camera_solver / material_mapper / render_worker are the generator;
  visual_gate is the verifier and shares no state with it.
- **Art. LVIII** (no self-scored world-class claims): "world-class
  presentation" is MEASURED by the gate, never asserted.
- **Art. LXI** (infrastructure failure is never science): a render
  skip/failure changes no epistemic field of the run — it only
  suppresses the hero.
- **Art. XXVIII** (no silent semantic promotion): a passing render
  never promotes the geometry's engineering status; the honesty badge
  vocabulary is unchanged (conceptual stays conceptual).

## Enforcement

- `visual_gate.evaluate()` writes `visual_gate.json` with
  `verdict` / `hero_suppressed` / `release_blocked`; the package
  compiler refuses the hero and blocks the release on any non-PASS
  verdict (`MODEL/3D/HERO_RELEASE_STATE.json`).
- The technology PDF embeds cover pages ONLY from gate-approved
  renders; a FAIL/NOT_RUN dossier ships text-only (hero suppressed).
- The website surfaces the gate verdict beside the hero (the buyer
  sees the approval, not a hidden one).
- Adversarial regressions live in `tests/test_r441_visual_compiler.py`
  (gate tampering, env allowlist, retirement integrity, dispatcher
  default) — every control has an attempted bypass (Art. XVII).

## Reviewer provenance

`AI_REVIEW` (Art. LXVII) — coder-implemented, gate-measured; the first
independent human review is still owed by the system as a whole.
