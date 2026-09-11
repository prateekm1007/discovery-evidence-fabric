#!/usr/bin/env python3
"""scripts/r446_owner_decision_package.py — R446-C1 Task 5: the
smallest owner decision package for the production visual memory floor.

Everything in this package is DERIVED from measured artifacts (no new
measurement, no new threshold — Art. XXVII; the R445-C2 lower bound and
the R441 threshold provenance are the authorities):

  - R445/MEMORY_BUDGET.json — the measured render-tree floor
    (final verified peak 496.2 MB, window 496-521, irreducible
    decomposition ~503 MB, the 450 MB target verdict)
  - discovery_fabric/engine/visual_compiler/visual_compiler_thresholds.json
    — the memory guard thresholds with their own provenance
    (in-worker 800 / async 650 MB, ENGINEERING class, MEASURED basis)

The package answers exactly the five questions (the directive's list):
  1. measured minimum
  2. expected server baseline
  3. safe production headroom
  4. recommended minimum memory plan
  5. exact behavior on insufficient capacity

No threshold is lowered. No silent fallback to Blender. No quality
degradation. (Article LXV: this is an owner-gated decision — the
package ESCALATES it with exact numbers; the machine does not decide.)
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "R446" / "VISUAL_MEMORY_OWNER_DECISION.json"


def main() -> int:
    mb = json.loads((REPO / "R445" / "MEMORY_BUDGET.json").read_text())
    thr = json.loads(
        (REPO / "discovery_fabric" / "engine" / "visual_compiler" /
         "visual_compiler_thresholds.json").read_text())

    floor = mb["final_verified_peak_mb"]
    irreducible = mb["acceptance_target_outcome"]["irreducible_footprint_mb"]
    guard = thr["memory_guard_mb"]

    package = {
        "artifact_type": "VISUAL_MEMORY_OWNER_DECISION_PACKAGE",
        "round": "R446-C1",
        "created_at": "2026-09-11",
        "reviewer_provenance": "AI_REVIEW",
        "decision_owner": "OPERATOR (Article LXV — owner-gated; the "
                           "machine does not pick a default and proceed)",
        "decision_opened_in": "R443 (billing-gated capacity decision; "
                              "escalation count 4 at R444-C2)",
        "escalation_count_this_package": 5,
        "cost_of_continued_inaction": (
            "every round this stays open, the production visual stage "
            "typed-skips (RENDER_SKIPPED_LOW_MEMORY): fresh production "
            "runs ship packages with zero hero images, zero PDF cover "
            "renders, and render routes 404 — the buyer surface stays "
            "text-and-geometry only while the SAME bytes prove "
            "COMPLETE_PASS in the sandbox at the SAME SHA"),
        "measured_sources": {
            "render_tree_floor": "R445/MEMORY_BUDGET.json (R445-C2, "
                                 "measured per-process PSS at 12.5 Hz)",
            "guard_thresholds": "visual_compiler_thresholds.json "
                                "(R441, MEASURED basis, ENGINEERING "
                                "class, rev history append-only)",
            "no_new_measurement_this_round": True,
            "no_threshold_changed_this_round": True,
        },

        "1_measured_minimum": {
            "render_tree_peak_mb": floor["value"],
            "measured_window_mb": "496-521 (run-to-run variance "
                                  "+/-5-25 MB across 8+ repeats)",
            "context": floor["context"],
            "irreducible_decomposition_mb": irreducible,
            "what_the_floor_is": (
                "the FULL Visual Compiler render tree (quality-locked: "
                "hero at 1536x1024 + 2048 shadow map + PMREM + the "
                "single-process Chromium/V8/Node floor) at the final "
                "committed render.js after the R445-C2 deadweight-only "
                "optimization"),
            "why_450_is_unachievable": (
                mb["acceptance_target_outcome"][
                    "why_450_is_physically_insufficient"]),
        },

        "2_expected_server_baseline": {
            "python_server_local_reference_mb": mb[
                "consumer_decomposition_measured"]["consumers"][
                "python_server_baseline"],
            "python_visual_worker_at_render_mb": mb[
                "consumer_decomposition_measured"]["consumers"][
                "python_visual_worker_at_render"],
            "cadquery_ocp_note": (
                "the engineering stack (458.7 MB isolated import) is "
                "STRUCTURALLY ABSENT from the visual worker — the two "
                "never co-reside by construction"),
            "production_baseline_honesty": (
                "the production container's own server baseline is NOT "
                "directly observable from outside Render — honest "
                "UNKNOWN, never guessed (Art. XXV); the local reference "
                "boot is 30.4 MB flat"),
        },

        "3_safe_production_headroom": {
            "async_memory_guard_mb": guard["async"],
            "in_worker_guard_mb": guard["in_worker"],
            "guard_basis": guard["basis"][:400],
            "headroom_rule": (
                "the async guard requires >= 650 MB FREE at render "
                "time; the render tree alone peaks at 496-521 MB, so a "
                "plan must cover tree + server + gateway + variance "
                "with the guard's own margin"),
        },

        "4_recommended_minimum_memory_plan": {
            "recommendation": ">= 1 GB plan (Render Starter upgrade)",
            "basis": (
                "1024 MB - ~35-60 MB server+gateway - variance "
                "(+/-25 MB) leaves ~940-965 MB free at render time — "
                "above the 650 MB async guard with margin; the guard's "
                "own consequence note states the visual compiler "
                "renders automatically on a >= 1 GB plan"),
            "comfortable_plan": (
                "2 GB if the async render queue may run concurrently "
                "with a live discovery run (the engine gauntlet itself "
                "peaks well below 1 GB, but concurrency doubles the "
                "uncertainty band)"),
            "not_a_threshold_invention": (
                "the recommendation derives from the MEASURED guard "
                "(650 MB) and the MEASURED tree floor (496-521 MB); "
                "no new number is invented (Art. XXVII)"),
        },

        "5_exact_behavior_on_insufficient_capacity": {
            "typed_skip": (
                "RENDER_SKIPPED_LOW_MEMORY — the cgroup-aware guard "
                "measures the container's REAL free memory before "
                "Chromium launches and typed-skips below the guard"),
            "fail_closed_consequences": [
                "the hero is suppressed in every medium (website, "
                "package PDFs, ZIP) — Article LXXII",
                "the visual release decision blocks the package from "
                "buyer-release posture",
                "the typed record (R443 schema) persists the skip with "
                "the plan-upgrade note — never a bare failure",
                "the run's epistemic state is UNTOUCHED (Art. LXI: "
                "presentation infrastructure, never a scientific "
                "verdict)",
            ],
            "what_never_happens": [
                "no threshold is lowered to force a render",
                "no silent fallback to the Blender legacy path",
                "no quality degradation (resolution, shadow map, view "
                "count all quality-locked)",
                "no fabricated visual-complete claim",
            ],
        },

        "explicit_non_goals": (
            "this package does NOT attempt another renderer-pruning "
            "round: R445-C2 already measured the lower bound (496.2 MB) "
            "and classified the 450 MB target as "
            "MEMORY_TARGET_UNACHIEVABLE_WITHOUT_PRODUCT_DEGRADATION with "
            "the irreducible decomposition; the remaining gap is a "
            "capacity decision, not an engineering one"),
        "art_lxxv_note": (
            "this package is the escalation artifact — the single most "
            "prominent unresolved item for this round; the machine "
            "correctly refuses to decide it (Art. XXXIII) and makes the "
            "cost of continued deferral explicit (Art. LXV)"),
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(package, indent=1, ensure_ascii=False))
    print(f"owner decision package -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
