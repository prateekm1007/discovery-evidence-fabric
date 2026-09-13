#!/usr/bin/env node
// R451-C2 — DETERMINISTIC UI TEST BATTERY for the presentation-state
// mapping (lib/presentationState.ts).
//
// Runs the directive's regression matrix (§12) and the adversarial
// mutation tests (§13, Attacks A–E) against the COMPILED module — the
// same code the browser ships — with zero browser, zero network, zero
// nondeterminism. These are assertions about what the UI WILL render
// because every blocked-state surface renders FROM this mapping's
// output (TechStage.tsx / InfrastructureBlockedHero.tsx are
// source-pinned by tests/test_r451_c2_blocked_state.py).
//
// The single most important assertion (§12): the infrastructure rows
// NEVER resolve to TECHNOLOGY_NOT_ESTABLISHED — the state whose hero
// says "Not established on this run."

import { execFileSync } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { createRequire } from "node:module";
import { tmpdir } from "node:os";
import path from "node:path";
import process from "node:process";

const WEBAPP = path.resolve(path.dirname(new URL(import.meta.url).pathname),
  "..", "TOSCANINI_UI", "webapp");
const OUT = mkdtempSync(path.join(tmpdir(), "r451c2-ui-"));
const require = createRequire(import.meta.url);

let failures = 0;
function check(name, cond, detail) {
  if (cond) {
    console.log(`  PASS  ${name}`);
  } else {
    failures += 1;
    console.error(`  FAIL  ${name}${detail ? " — " + detail : ""}`);
  }
}

try {
  execFileSync(path.join(WEBAPP, "node_modules", ".bin", "tsc"), [
    path.join(WEBAPP, "lib", "presentationState.ts"),
    "--outDir", OUT,
    "--module", "commonjs",
    "--target", "es2020",
    "--skipLibCheck",
    "--noEmitOnError",
  ], { stdio: "pipe" });
  const ps = require(path.join(OUT, "presentationState.js"));
  const { resolvePresentationState, blockedInsightCards } = ps;

  const usv = (over = {}) => ({
    user_state: "COMPLETED_UNKNOWN", label: "", meaning: "",
    decision: "", finished: true, found_something: false,
    rejected: false, package_available: false, ...over,
  });
  const detail = (over = {}) => ({
    status: "COMPLETE", final_status: null,
    user_state_view: usv(), run_state: null, ...over,
  });
  const dossier = (over = {}) => ({ tabs: { design: null, evidence: null }, ...over });
  const designAvailable = (over = {}) => ({
    availability: "AVAILABLE", glb: "/api/run/x/model/engineering_model.glb",
    renders: { status: "OK", visual_gate: { verdict: "COMPLETE_PASS" } },
    ...over,
  });

  // ----------------------------------------------------------------
  console.log("\n== Regression matrix (directive §12 / C2.13) ==");
  // RUNNING
  let r = resolvePresentationState(
    detail({ status: "RUNNING", user_state_view: usv({ user_state: "RUNNING", finished: false }) }),
    dossier());
  check("RUNNING -> INVESTIGATING", r.state === "INVESTIGATING" && !r.infrastructurePaused);

  // SUCCESS + geometry (gate pass). R451-C2.4 SUPERSESSION: the typed
  // geometry_state + the recorded ENGINEERING authority now ride the
  // fixture — the untyped legacy shape resolves to explicitly
  // unverified historical state (the fallback below), never readiness.
  r = resolvePresentationState(detail(), dossier({ tabs: { design: designAvailable({
    geometry_state: "visual_complete",
    engineering_authority: "ENGINEERING" }), evidence: null } }));
  check("SUCCESS+geometry(gate PASS) -> VISUAL_READY", r.state === "VISUAL_READY");

  // SUCCESS + geometry, render skipped (case D). R451-C2.5: the
  // fixture is TYPED (a current backend payload carries the typed
  // state + cause + authority); the untyped raw-field shape no longer
  // derives any current state — see the LEGACY_STATE_UNAVAILABLE block.
  r = resolvePresentationState(detail(), dossier({ tabs: {
    design: designAvailable({ geometry_state: "geometry_available",
      presentation_cause: "infrastructure",
      engineering_authority: "ENGINEERING",
      renders: { status: "RENDER_SKIPPED_LOW_MEMORY",
        visual_gate: { verdict: "NOT_RUN" } } }), evidence: null } }));
  check("GLB present + renderer skipped -> GEOMETRY_READY_RENDER_BLOCKED",
    r.state === "GEOMETRY_READY_RENDER_BLOCKED" && r.glbReadyButRenderBlocked === true);

  // SUCCESS + no geometry + invention exists (software-type technology)
  r = resolvePresentationState(
    detail({ user_state_view: usv({ user_state: "COMPLETED_CANDIDATE", found_something: true }) }),
    dossier({ tabs: { design: { availability: "UNAVAILABLE" }, evidence: null } }));
  check("SUCCESS+invention, no geometry -> GEOMETRY_UNAVAILABLE",
    r.state === "GEOMETRY_UNAVAILABLE");

  // SUCCESS + no geometry + nothing established (honest scientific absence)
  r = resolvePresentationState(
    detail({ user_state_view: usv({ user_state: "COMPLETED_UNKNOWN" }) }),
    dossier({ tabs: { design: { availability: "UNAVAILABLE" }, evidence: null } }));
  check("SUCCESS+nothing -> TECHNOLOGY_NOT_ESTABLISHED",
    r.state === "TECHNOLOGY_NOT_ESTABLISHED");

  // SCIENTIFIC REJECTION (false premise — a real scientific verdict)
  r = resolvePresentationState(
    detail({ user_state_view: usv({ user_state: "COMPLETED_FALSE_PREMISE" }) }),
    dossier({ tabs: { design: { availability: "UNAVAILABLE" }, evidence: null } }));
  check("SCIENTIFIC REJECTION -> SCIENTIFIC_REJECTION", r.state === "SCIENTIFIC_REJECTION");

  // INFRASTRUCTURE BLOCKED / TRANSPORT FAILURE / INTERRUPTED / ENGINE ERROR
  for (const [st, status] of [
    ["BLOCKED_TRANSPORT", "RUN_BLOCKED_TRANSPORT"],
    ["FAILED_TRANSPORT", "ERROR_TRANSPORT"],
    ["INTERRUPTED", "INTERRUPTED"],
    ["FAILED_ENGINE", "ERROR_STUCK"],
  ]) {
    r = resolvePresentationState(
      detail({ status, user_state_view: usv({ user_state: st }) }),
      dossier({ tabs: { design: { availability: "UNAVAILABLE" }, evidence: null } }));
    check(`${status} -> INFRASTRUCTURE_PAUSED`,
      r.state === "INFRASTRUCTURE_PAUSED" && r.infrastructurePaused === true);
    check(`${status} NEVER resolves to TECHNOLOGY_NOT_ESTABLISHED`,
      r.state !== "TECHNOLOGY_NOT_ESTABLISHED");
  }

  // ----------------------------------------------------------------
  console.log("\n== Adversarial attacks (directive §13) ==");
  // Attack A: infrastructure blocked + fabricated found_something=false
  //           (and every scientific-looking field lying) — the state
  //           stays infrastructure, never scientific rejection.
  r = resolvePresentationState(
    detail({ status: "RUN_BLOCKED_TRANSPORT",
      user_state_view: usv({ user_state: "BLOCKED_TRANSPORT",
        found_something: false, rejected: false, package_available: false }) }),
    dossier({ tabs: { design: { availability: "UNAVAILABLE" }, evidence: null } }));
  check("Attack A: stays INFRASTRUCTURE_PAUSED", r.state === "INFRASTRUCTURE_PAUSED");
  check("Attack A: no scientific-rejection wording path",
    r.state !== "SCIENTIFIC_REJECTION" && r.state !== "TECHNOLOGY_NOT_ESTABLISHED");

  // Attack B: infrastructure blocked + zero retrieved evidence
  let cards = blockedInsightCards({ retrieval_state: "NOT_REACHED",
    retrieved_count: 0, used_count: 0 });
  const sup = cards.find((c) => c.title === "What supports it");
  check("Attack B: NOT_REACHED renders 'not reached', never a zero",
    /not reached/i.test(sup.headline) && !/^0\b/.test(sup.headline),
    sup.headline);
  check("Attack B: never claims absence of evidence exists",
    !/no supporting evidence exists/i.test(sup.headline + sup.body));
  // stale legacy shape (counts present, state missing) — still not a zero
  cards = blockedInsightCards({ retrieved_count: 0, used_count: 0 });
  check("Attack B (stale shape): counts ignored without RETRIEVED state",
    /not reached|failed/i.test(
      cards.find((c) => c.title === "What supports it").headline));
  // the one honest zero: retrieval executed and measured zero
  cards = blockedInsightCards({ retrieval_state: "RETRIEVED",
    retrieved_count: 0, used_count: 0 });
  check("Measured zero (RETRIEVED state) MAY show numeric zero",
    /^0 sources retrieved$/.test(
      cards.find((c) => c.title === "What supports it").headline));

  // Attack C: infrastructure blocked + rejected=true in an unrelated
  // stale field — the canonical user-state authority wins; no silent
  // frontend reconciliation.
  r = resolvePresentationState(
    detail({ status: "RUN_BLOCKED_TRANSPORT",
      user_state_view: usv({ user_state: "BLOCKED_TRANSPORT",
        rejected: true,
        outcome: "INVENTION_REQUIRES_EXPERIMENT",
        outcome_label: "stale scientific outcome label" }) }),
    dossier({ tabs: { design: designAvailable(), evidence: null } }));
  check("Attack C: infrastructure wins over stale rejected=true",
    r.state === "INFRASTRUCTURE_PAUSED");
  check("Attack C: geometry present does not flip a blocked run to VISUAL_READY",
    r.state !== "VISUAL_READY" && r.state !== "GEOMETRY_READY_RENDER_BLOCKED");

  // Attack D: scientific rejection gets scientific language, not
  // infrastructure language.
  r = resolvePresentationState(
    detail({ user_state_view: usv({ user_state: "COMPLETED_FALSE_PREMISE" }) }),
    dossier());
  check("Attack D: SCIENTIFIC_REJECTION (not infrastructure)",
    r.state === "SCIENTIFIC_REJECTION" && !r.infrastructurePaused);

  // Attack E: successful technology -> technology hero + normal cards.
  // R451-C2.4 SUPERSESSION: the fixture carries the typed state + the
  // recorded ENGINEERING authority (see the regression-matrix note).
  r = resolvePresentationState(detail(), dossier({ tabs: {
    design: designAvailable({ geometry_state: "visual_complete",
      engineering_authority: "ENGINEERING" }), evidence: { retrieval_state: "RETRIEVED",
      retrieved_count: 12, used_count: 4 } } }));
  check("Attack E: VISUAL_READY for a successful technology",
    r.state === "VISUAL_READY");
  const normalSupport = "12 sources retrieved · 4 shaped the design";
  check("Attack E: numeric counts render when retrieval measured them",
    evidenceSubFor({ retrieval_state: "RETRIEVED", retrieved_count: 12, used_count: 4 })
      === normalSupport);
  function evidenceSubFor(ec) {
    // mirrors TechStage's evidenceSub rule — kept in sync by this test
    return ec?.retrieval_state === "RETRIEVED" && ec.retrieved_count != null
      ? `${ec.retrieved_count} sources retrieved · ${ec.used_count ?? 0} shaped the design`
      : null;
  }

  // ----------------------------------------------------------------
  console.log("\n== Blocked insight cards, complete set (directive §3) ==");
  cards = blockedInsightCards({ retrieval_state: "NOT_REACHED" });
  check("WHAT CHANGED is 'Not evaluated'",
    cards[0].headline === "Not evaluated");
  check("WHY IT WORKS is 'Not evaluated' (mechanism not reached)",
    cards[1].headline === "Not evaluated" &&
    /did not reach mechanism evaluation/.test(cards[1].body));
  check("WHAT SUPPORTS IT says retrieval not reached",
    /not reached/i.test(cards[2].headline));
  check("WHAT COULD KILL IT is 'Not evaluated' (no candidate attacked)",
    cards[3].headline === "Not evaluated");
  check("No card uses scientific-absence wording",
    cards.every((c) =>
      !/not established|no invention|nothing found|investigation failed|no technology|no answer/i
        .test(c.headline + " " + c.body)),
    JSON.stringify(cards));

  // ----------------------------------------------------------------
  console.log("\n== isTerminal canonical definition ==");
  check("RUN_BLOCKED_TRANSPORT is terminal",
    ps.isTerminal("RUN_BLOCKED_TRANSPORT") === true);
  check("RUNNING is not terminal", ps.isTerminal("RUNNING") === false);
  check("ERROR_* is terminal", ps.isTerminal("ERROR_TRANSPORT") === true);

  // =================================================================
  // R451-C2.1 — the five states with their exact copy, and the
  // no-file-inference rule: the mapping consumes the backend-typed
  // geometry_state and NEVER infers state from a missing file.
  // =================================================================
  console.log("\n== R451-C2.1: the five states, exact copy ==");

  // State A — RUN_BLOCKED_TRANSPORT
  r = resolvePresentationState(
    detail({ status: "RUN_BLOCKED_TRANSPORT",
      user_state_view: usv({ user_state: "BLOCKED_TRANSPORT" }) }),
    dossier());
  check("State A: INFRASTRUCTURE_PAUSED with the directive copy",
    r.state === "INFRASTRUCTURE_PAUSED" &&
    r.blocked?.verdictLine === "No scientific conclusion was reached." &&
    r.blocked?.subline === "Infrastructure temporarily unavailable.");

  // State B — invention exists, geometry absent (typed backend state)
  r = resolvePresentationState(
    detail({ user_state_view: usv({ user_state: "COMPLETED_CANDIDATE",
      found_something: true }) }),
    dossier({ tabs: { design: {
      availability: "UNAVAILABLE",
      geometry_state: "geometry_not_applicable",
      geometry_state_detail:
        "the recorded bridge outcome is NOT_VISUALIZABLE",
    }, evidence: null } }));
  check("State B: GEOMETRY_UNAVAILABLE with the absent reason",
    r.state === "GEOMETRY_UNAVAILABLE" &&
    r.geometryAbsent?.reason === "not_applicable");
  check("State B: exact directive copy",
    ps.GEOMETRY_ABSENT_COPY.line ===
      "Engineering visualization not available on this invention.");

  // State B variant — the geometry BUILD failed (also State B copy)
  r = resolvePresentationState(
    detail({ user_state_view: usv({ user_state: "COMPLETED_CANDIDATE",
      found_something: true }) }),
    dossier({ tabs: { design: {
      availability: "UNAVAILABLE",
      geometry_state: "geometry_generation_failed",
      geometry_state_detail: "the recorded bridge outcome is GEOMETRY_FAILED",
    }, evidence: null } }));
  check("State B (generation failed): same state, failed reason",
    r.state === "GEOMETRY_UNAVAILABLE" &&
    r.geometryAbsent?.reason === "generation_failed" &&
    r.geometryAbsent?.detail ===
      "the recorded bridge outcome is GEOMETRY_FAILED");

  // State C — GLB exists, renderer unavailable (typed backend state)
  r = resolvePresentationState(detail(), dossier({ tabs: {
    design: { availability: "AVAILABLE", glb: "/api/run/x/model.glb",
      geometry_state: "visual_render_failed",
      presentation_cause: "renderer_unavailable",
      geometry_state_detail: "the presentation renderer recorded RENDER_FAILED",
      renders: { status: "RENDER_FAILED" } }, evidence: null } }));
  check("State C: GEOMETRY_READY_RENDER_BLOCKED + renderer cause",
    r.state === "GEOMETRY_READY_RENDER_BLOCKED" &&
    r.renderBlockCause === "renderer_unavailable");
  check("State C: exact directive copy",
    ps.renderBlockedCopy(r.renderBlockCause).line ===
      "Engineering model ready. Presentation renderer unavailable.");

  // State C variant — renderer skipped on infrastructure
  // (R451-C2.2 §1: infrastructure gets its OWN sentence, distinct from
  // renderer absence)
  r = resolvePresentationState(detail(), dossier({ tabs: {
    design: { availability: "AVAILABLE", glb: "/api/run/x/model.glb",
      geometry_state: "visual_render_failed",
      presentation_cause: "infrastructure",
      renders: { status: "RENDER_SKIPPED_LOW_MEMORY" } },
    evidence: null } }));
  check("State C (infra skip): distinct infrastructure copy",
    r.renderBlockCause === "infrastructure" &&
    ps.renderBlockedCopy(r.renderBlockCause).line ===
      "Engineering model ready. Presentation rendering paused by " +
      "infrastructure.");

  // R451-C2.2 §1 — the not_attempted sentence: a render that was never
  // started is NEVER worded as renderer unavailability
  r = resolvePresentationState(detail(), dossier({ tabs: {
    design: { availability: "AVAILABLE", glb: "/api/run/x/model.glb",
      geometry_state: "geometry_available",
      presentation_cause: "not_attempted",
      renders: { status: "" } }, evidence: null } }));
  check("not_attempted: exact new directive copy",
    r.renderBlockCause === "not_attempted" &&
    ps.renderBlockedCopy(r.renderBlockCause).line ===
      "Engineering model ready. Presentation render not yet started.");

  // R451-C2.2 §1 — the async render-in-progress sentence
  r = resolvePresentationState(detail(), dossier({ tabs: {
    design: { availability: "AVAILABLE", glb: "/api/run/x/model.glb",
      geometry_state: "geometry_available",
      presentation_cause: "rendering_in_progress",
      renders: { status: "RENDERING" } }, evidence: null } }));
  check("rendering_in_progress: distinct in-progress copy",
    r.renderBlockCause === "rendering_in_progress" &&
    ps.renderBlockedCopy(r.renderBlockCause).line ===
      "Engineering model ready. Presentation render in progress.");

  // R451-C2.2 §1 — the causes are DISTINCT sentences; R451-C2.4 closed
  // the vocabulary at nine; R451-C2.5 §2 closes it at TEN
  // (visual_authority_not_engineering — the contradiction-pair state)
  {
    const lines = new Set(ps.RENDER_BLOCK_CAUSES.map(
      (c) => ps.renderBlockedCopy(c).line));
    check("ten causes -> ten distinct sentences (R451-C2.5: the contradiction-pair cause)",
      ps.RENDER_BLOCK_CAUSES.length === 10 && lines.size === 10);
  }

  // R451-C2.5 §1 — SUPERSESSION of the R451-C2.4 §1 branch: a legacy
  // pre-C2.1 payload (raw availability/glb/renders fields, no typed
  // geometry state) now resolves ONLY to LEGACY_STATE_UNAVAILABLE —
  // the explicit NON-CURRENT compatibility state. A convincing render
  // PASS in the payload upgrades nothing: a legacy payload derives no
  // current presentation state at all.
  r = resolvePresentationState(detail(), dossier({ tabs: {
    design: { availability: "AVAILABLE", glb: "/api/run/x/model.glb",
      renders: { status: "OK",
        visual_gate: { verdict: "COMPLETE_PASS" } } }, evidence: null } }));
  check("R451-C2.5 §1: legacy payload + convincing render PASS -> LEGACY_STATE_UNAVAILABLE",
    r.state === "LEGACY_STATE_UNAVAILABLE");
  check("R451-C2.5 §1: the legacy payload NEVER produces a current state",
    r.state !== "VISUAL_READY" && r.state !== "GEOMETRY_READY_RENDER_BLOCKED" &&
    r.state !== "TECHNOLOGY_NOT_ESTABLISHED" && r.state !== "SCIENTIFIC_REJECTION");
  // every legacy shape — with or without the convincing PASS — lands
  // on the SAME explicit non-current state
  for (const legacyDesign of [
    { availability: "AVAILABLE", glb: "/api/run/x/model.glb" },
    { availability: "AVAILABLE", glb: "/api/run/x/model.glb",
      renders: { status: "RENDER_FAILED", note: "stale" } },
    { glb: "/api/run/x/model.glb",
      renders: { status: "OK", visual_gate: { verdict: "PASS" } } },
  ]) {
    r = resolvePresentationState(detail(),
      dossier({ tabs: { design: legacyDesign, evidence: null } }));
    check(`R451-C2.5 §1: legacy shape -> LEGACY_STATE_UNAVAILABLE`,
      r.state === "LEGACY_STATE_UNAVAILABLE");
  }

  // R451-C2.4 §2 — geometry_unverified: the artifact candidate's
  // mandatory certification is incomplete — its OWN cause + sentence
  r = resolvePresentationState(detail(), dossier({ tabs: {
    design: { availability: "UNAVAILABLE",
      geometry_state: "geometry_unverified",
      presentation_cause: "geometry_unverified",
      engineering_authority: "UNKNOWN",
      geometry_state_detail: "the certification is incomplete: no " +
        "recorded identity document names the canonical GLB" },
    evidence: null } }));
  check("R451-C2.4 §2: geometry_unverified -> render-blocked with its own cause",
    r.state === "GEOMETRY_READY_RENDER_BLOCKED" &&
    r.renderBlockCause === "geometry_unverified" &&
    r.engineeringAuthority === "UNKNOWN");
  check("R451-C2.4 §2: the unverified copy claims no authority",
    ps.renderBlockedCopy(r.renderBlockCause).title ===
      "GEOMETRY AUTHORITY UNVERIFIED");

  // R451-C2.5 §2 — SUPERSESSION of the R451-C2.4 §6 mapping: the
  // VISUAL_READY invariant is ABSOLUTE — the STATE exists only on
  // (visual_complete, ENGINEERING). The contradiction pairs fail
  // closed to the NON-READY typed state; "Technology ready" is
  // structurally unreachable for them (the badge lock is the SECOND
  // lock — the state itself is the first).
  r = resolvePresentationState(detail(), dossier({ tabs: {
    design: designAvailable({ geometry_state: "visual_complete",
      engineering_authority: "ENGINEERING" }), evidence: null } }));
  check("R451-C2.5 §2: VISUAL_READY requires (visual_complete, ENGINEERING)",
    r.state === "VISUAL_READY" &&
    r.engineeringAuthority === "ENGINEERING");
  r = resolvePresentationState(detail(), dossier({ tabs: {
    design: designAvailable({ geometry_state: "visual_complete",
      engineering_authority: "CONCEPTUAL" }), evidence: null } }));
  check("R451-C2.5 §2: visual_complete + CONCEPTUAL fails closed to the non-ready state",
    r.state === "GEOMETRY_READY_RENDER_BLOCKED" &&
    r.renderBlockCause === "visual_authority_not_engineering" &&
    r.state !== "VISUAL_READY");
  check("R451-C2.5 §2: the contradiction pair's copy claims no readiness",
    ps.renderBlockedCopy(r.renderBlockCause).line.includes(
      "visual readiness is not claimed"));
  r = resolvePresentationState(detail(), dossier({ tabs: {
    design: designAvailable({ geometry_state: "visual_complete",
      engineering_authority: "UNKNOWN" }), evidence: null } }));
  check("R451-C2.5 §2: visual_complete + UNKNOWN fails closed to the non-ready state",
    r.state === "GEOMETRY_READY_RENDER_BLOCKED" &&
    r.renderBlockCause === "visual_authority_not_engineering");
  r = resolvePresentationState(detail(), dossier({ tabs: {
    design: designAvailable({ geometry_state: "visual_complete" }),
    evidence: null } }));
  check("R451-C2.5 §2: visual_complete + ABSENT authority fails closed (defensive)",
    r.state === "GEOMETRY_READY_RENDER_BLOCKED" &&
    r.renderBlockCause === "visual_authority_not_engineering");

  // R451-C2.3 §2 — the visual-input boundary has its OWN sentence:
  // a missing canonical GLB is never worded as renderer absence
  r = resolvePresentationState(detail(), dossier({ tabs: {
    design: { availability: "AVAILABLE", glb: "/api/run/x/model.glb",
      geometry_state: "geometry_available",
      presentation_cause: "visual_input_missing",
      engineering_authority: "ENGINEERING",
      visual_input_ready: false,
      geometry_state_detail:
        "the engineering geometry is verified but no canonical GLB " +
        "resolves under the run directory" },
    evidence: null } }));
  check("visual_input_missing: own cause, own sentence",
    r.renderBlockCause === "visual_input_missing" &&
    ps.renderBlockedCopy(r.renderBlockCause).line ===
      "Engineering model ready. The canonical 3D model file " +
      "required for presentation rendering was not produced on " +
      "this run.");

  // R451-C2.3 §5 — the release chain failing closed has its OWN
  // sentence and is NEVER worded as visual readiness
  r = resolvePresentationState(detail(), dossier({ tabs: {
    design: { availability: "AVAILABLE", glb: "/api/run/x/model.glb",
      geometry_state: "visual_render_failed",
      presentation_cause: "release_unverified",
      engineering_authority: "ENGINEERING",
      geometry_state_detail:
        "the gate passed but the release chain fails closed at " +
        "'invocation_receipt_identity' — not visual ready" },
    evidence: null } }));
  check("release_unverified: own cause, own sentence, never VISUAL_READY",
    r.renderBlockCause === "release_unverified" &&
    r.state === "GEOMETRY_READY_RENDER_BLOCKED" &&
    ps.renderBlockedCopy(r.renderBlockCause).line ===
      "Engineering model ready. The presentation could not be " +
      "verified against the canonical geometry.");

  // R451-C2.3 §1 — the ribbon title is AUTHORITY-AWARE: the
  // ENGINEERING MODEL READY claim exists only on the contract's
  // recorded ENGINEERING authority
  check("authority-aware title: ENGINEERING authority keeps the claim",
    ps.renderBlockedTitle("ENGINEERING") === "ENGINEERING MODEL READY");
  check("authority-aware title: CONCEPTUAL never claims engineering",
    ps.renderBlockedTitle("CONCEPTUAL") === "CONCEPTUAL MODEL");
  check("authority-aware title: UNKNOWN (legacy boolean-only) never claims engineering",
    ps.renderBlockedTitle("UNKNOWN") === "GEOMETRY AUTHORITY UNVERIFIED");
  check("authority-aware title: absent authority defaults to unverified",
    ps.renderBlockedTitle(undefined) === "GEOMETRY AUTHORITY UNVERIFIED");
  {
    // the view carries the backend's authority verdict into the ribbon
    const view = resolvePresentationState(detail(), dossier({ tabs: {
      design: { availability: "AVAILABLE", glb: "/api/run/x/model.glb",
        geometry_state: "geometry_available",
        presentation_cause: "not_attempted",
        engineering_authority: "UNKNOWN" },
      evidence: null } }));
    check("the view projects engineering_authority for the ribbon",
      view.engineeringAuthority === "UNKNOWN" &&
      ps.renderBlockedTitle(view.engineeringAuthority) ===
        "GEOMETRY AUTHORITY UNVERIFIED");
  }

  // State D — GLB exists, renderer succeeded, gate FAILED
  r = resolvePresentationState(detail(), dossier({ tabs: {
    design: { availability: "AVAILABLE", glb: "/api/run/x/model.glb",
      geometry_state: "visual_render_failed",
      presentation_cause: "gate_not_passed",
      geometry_state_detail:
        "the render completed but the presentation integrity gate returned FAIL",
      renders: { status: "OK",
        visual_gate: { verdict: "FAIL" } } }, evidence: null } }));
  check("State D: gate_not_passed cause",
    r.state === "GEOMETRY_READY_RENDER_BLOCKED" &&
    r.renderBlockCause === "gate_not_passed");
  check("State D: exact directive copy",
    ps.renderBlockedCopy(r.renderBlockCause).line ===
      "Model rendered but did not pass the presentation integrity gate.");

  // State E — gate COMPLETE_PASS: show the model.
  // R451-C2.5 SUPERSESSION (was the C2.1-era State E fixture): the
  // typed payload carries the recorded ENGINEERING authority — the
  // authority field is part of the current-state contract now.
  r = resolvePresentationState(detail(), dossier({ tabs: {
    design: designAvailable({
      geometry_state: "visual_complete",
      engineering_authority: "ENGINEERING",
      renders: { status: "OK",
        visual_gate: { verdict: "COMPLETE_PASS" } } }), evidence: null } }));
  check("State E: VISUAL_READY (the model shows)",
    r.state === "VISUAL_READY" && r.glbReadyButRenderBlocked == null);

  // ----------------------------------------------------------------
  console.log("\n== R451-C2.1: no-file-inference attacks ==");
  // Attack F1: geom.present == false (no glb field anywhere) must NOT
  // collapse the state when the backend typed the real one. A missing
  // file is never the browser's evidence for WHY geometry is absent.
  r = resolvePresentationState(
    detail({ user_state_view: usv({ user_state: "COMPLETED_CANDIDATE",
      found_something: true }) }),
    dossier({ tabs: { design: {
      availability: "UNAVAILABLE", glb: null,
      geometry_state: "geometry_not_applicable" }, evidence: null } }));
  check("Attack F1: missing glb + typed not_applicable -> State B (never TECHNOLOGY_NOT_ESTABLISHED)",
    r.state === "GEOMETRY_UNAVAILABLE" &&
    r.state !== "TECHNOLOGY_NOT_ESTABLISHED");

  // Attack F2 (R451-C2.5 SUPERSESSION): a GLB URL alone (stale design
  // row) without the typed state is a LEGACY payload — it resolves to
  // LEGACY_STATE_UNAVAILABLE, never any current state (file existence
  // and render absence are both raw-field material the browser no
  // longer interprets; the never-VISUAL_READY property is preserved
  // and strengthened).
  r = resolvePresentationState(detail(), dossier({ tabs: {
    design: { availability: "AVAILABLE", glb: "/api/run/x/model.glb",
      renders: { status: "" } }, evidence: null } }));
  check("Attack F2: glb present + no render record -> LEGACY_STATE_UNAVAILABLE (never VISUAL_READY)",
    r.state === "LEGACY_STATE_UNAVAILABLE" && r.state !== "VISUAL_READY");
  check("Attack F2: the legacy payload derives no current state",
    r.state !== "GEOMETRY_READY_RENDER_BLOCKED");

  // Attack F3 (R451-C2.5 SUPERSESSION): a raw gate FAIL with no typed
  // state is legacy material — the browser derives no current state
  // from it at all (the gate is the backend evaluator's input, never
  // the browser's; the typed State D path still renders the gate copy
  // in the causes block above).
  r = resolvePresentationState(detail(), dossier({ tabs: {
    design: { availability: "AVAILABLE", glb: "/api/run/x/model.glb",
      renders: { status: "OK",
        visual_gate: { verdict: "FAIL" } } }, evidence: null } }));
  check("Attack F3: raw gate FAIL without the typed state -> LEGACY_STATE_UNAVAILABLE",
    r.state === "LEGACY_STATE_UNAVAILABLE");

  // Attack F4: upstream_not_reached on a terminal run with an invention
  // falls through to the honest absence resolution — never a fake
  // geometry state
  r = resolvePresentationState(
    detail({ user_state_view: usv({ user_state: "COMPLETED_CANDIDATE",
      found_something: true }) }),
    dossier({ tabs: { design: {
      availability: "PENDING",
      geometry_state: "upstream_not_reached" }, evidence: null } }));
  check("Attack F4: upstream_not_reached + invention -> GEOMETRY_UNAVAILABLE (honest)",
    r.state === "GEOMETRY_UNAVAILABLE");

  // Attack F5: an infrastructure-blocked run NEVER reaches a geometry
  // state at all — even a typed geometry row cannot un-block it
  r = resolvePresentationState(
    detail({ status: "RUN_BLOCKED_TRANSPORT",
      user_state_view: usv({ user_state: "BLOCKED_TRANSPORT" }) }),
    dossier({ tabs: { design: designAvailable({
      geometry_state: "visual_complete" }), evidence: null } }));
  check("Attack F5: typed visual_complete cannot override INFRASTRUCTURE_PAUSED",
    r.state === "INFRASTRUCTURE_PAUSED" &&
    r.state !== "VISUAL_READY");

  // unknown geometry_state values are never trusted into a geometry
  // branch (the vocabulary is closed; anything else falls through)
  r = resolvePresentationState(
    detail({ user_state_view: usv({ user_state: "COMPLETED_CANDIDATE",
      found_something: true }) }),
    dossier({ tabs: { design: {
      availability: "UNAVAILABLE", geometry_state: "SOMETHING_ELSE" },
    evidence: null } }));
  check("Closed vocabulary: unknown geometry_state falls through honestly",
    r.state === "GEOMETRY_UNAVAILABLE");
} finally {
  rmSync(OUT, { recursive: true, force: true });
}

console.log(failures === 0
  ? "\nUI TEST BATTERY: ALL PASS"
  : `\nUI TEST BATTERY: ${failures} FAILURE(S)`);
process.exit(failures === 0 ? 0 : 1);
