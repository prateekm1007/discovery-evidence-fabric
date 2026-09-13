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

// R451-C2.6 §1 — read a webapp source file (the TechStage source pins)
import { readFileSync } from "node:fs";
function fsRead(...parts) {
  return readFileSync(path.join(WEBAPP, ...parts), "utf8");
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
  // branch. R451-C2-CLOSURE Direction B SUPERSEDES the C2.1-era
  // expectation (disclosed per Art. LXIV): "falls through honestly" to
  // the absence logic translated an unrecognized backend state into
  // GEOMETRY_UNAVAILABLE / TECHNOLOGY_NOT_ESTABLISHED — scientific
  // claims manufactured by a frontend parse failure. The fail-closed
  // contract now: unknown -> PRESENTATION_STATE_UNAVAILABLE (the full
  // Direction B attack matrix lives in its own section below).
  r = resolvePresentationState(
    detail({ user_state_view: usv({ user_state: "COMPLETED_CANDIDATE",
      found_something: true }) }),
    dossier({ tabs: { design: {
      availability: "UNAVAILABLE", geometry_state: "SOMETHING_ELSE" },
    evidence: null } }));
  check("Closed vocabulary: unknown geometry_state FAILS CLOSED to " +
      "PRESENTATION_STATE_UNAVAILABLE (supersedes the C2.1 fall-through)",
    r.state === "PRESENTATION_STATE_UNAVAILABLE" &&
      r.state !== "GEOMETRY_UNAVAILABLE" &&
      r.state !== "TECHNOLOGY_NOT_ESTABLISHED");

  // ----------------------------------------------------------------
  console.log("\n== R451-C2.6 §1: the legacy viewer is impossible ==");
  // THE mandatory adversarial shape: LEGACY_STATE_UNAVAILABLE plus a
  // convincing viewerUrl, convincing GLB metadata, and convincing
  // render metadata. The browser proof (a real headless Chrome against
  // the real component) lives in R451/C2_PRODUCT/E2E_C26; this battery
  // pins the mapping-level contract the component consumes.
  {
    const convincingLegacy = dossier({ tabs: { design: {
      availability: "AVAILABLE",
      glb: "/api/run/x/model/engineering_model.glb",
      geometry_class: "ENGINEERING_3D",
      generation_id: "gen-1",
      hero_eligibility: { eligible: true, reason: null },
      evolution: [{ generation: 1, current: true,
        glb: "/api/run/x/model/engineering_model.glb" }],
      renders: { status: "OK",
        visual_gate: { verdict: "COMPLETE_PASS" } },
    }, evidence: null } });
    r = resolvePresentationState(
      detail({ user_state_view: usv({ user_state: "COMPLETED_CANDIDATE",
        found_something: true, package_available: true }) }),
      convincingLegacy);
    check("Legacy+convincing viewerUrl: LEGACY_STATE_UNAVAILABLE only",
      r.state === "LEGACY_STATE_UNAVAILABLE");
    check("Legacy+convincing viewerUrl: VISUAL_READY impossible",
      r.state !== "VISUAL_READY");
    check("Legacy+convincing viewerUrl: current geometry state impossible",
      r.state !== "GEOMETRY_READY_RENDER_BLOCKED");
    check("Legacy+convincing viewerUrl: the view carries NO viewer-able " +
        "field the component could mount",
      ["glb", "viewerUrl", "modelUrl", "canonicalGlb"].every(
        (k) => !(k in r)));
    check("Legacy+convincing viewerUrl: not an infrastructure pause " +
        "(the legacy hero, not the blocked surface)",
      r.infrastructurePaused === false);
  }
  {
    // the source pin: the component's hero-viewport resolves the legacy
    // state FIRST (before the viewerUrl branch), viewerUrl computes null
    // under the legacy state, and the gate badge is legacy-guarded
    const stage = fsRead("components", "TechStage.tsx");
    const vp = stage.indexOf("data-hero-viewport");
    const legacyFirst = stage.indexOf(
      'view.state === "LEGACY_STATE_UNAVAILABLE" ?', vp);
    const viewerBranch = stage.indexOf(") : viewerUrl ? (", vp);
    check("TechStage rendering order: the legacy hero branch is FIRST",
      legacyFirst !== -1 && viewerBranch !== -1 && legacyFirst < viewerBranch);
    check("TechStage: viewerUrl computes null under LEGACY_STATE_UNAVAILABLE",
      stage.includes("const legacyUnavailable = view.state === " +
        '"LEGACY_STATE_UNAVAILABLE"') &&
      stage.indexOf("!legacyUnavailable && heroEligible") <
        stage.indexOf("const showingHistory"));
    check("TechStage: the R441 gate badge is legacy-guarded",
      stage.includes("gateVerdict && !legacyUnavailable"));
  }

  // ----------------------------------------------------------------
  console.log("\n== R451-C2.6 FINAL CLOSEOUT — the ONE evaluator/UI coupling ==");
  // The directive's coupling assertion: presentationState =
  // INFRASTRUCTURE_PAUSED AND TechStage => NO terminal scientific
  // verdict DOM. The mapping-level half runs here on the COMPILED
  // shipping module with the directive's EXACT attack payload (every
  // stale field populated — the attack does not pass by omission); the
  // DOM half is the real-browser proof in
  // R451/C2_PRODUCT/E2E_FINAL_CLOSEOUT/ (production build, real
  // headless Chrome). One coupling, no second state machine: both
  // halves read the SAME resolvePresentationState the component
  // consumes.
  {
    const finalCloseoutUsv = usv({
      user_state: "BLOCKED_TRANSPORT",
      finished: true,
      found_something: true,
      rejected: true,
      package_available: true,
      label: "AUTOMATED INVENTION CANDIDATE",
      decision: "Technology ready",
      meaning: "The candidate survived.",
      outcome: "INVENTION_SURVIVED",
      outcome_label: "AUTOMATED INVENTION CANDIDATE",
    });
    const convincing = dossier({ tabs: { design: {
      availability: "AVAILABLE",
      glb: "/api/run/x/model/engineering_model.glb",
      geometry_class: "ENGINEERING_3D",
      generation_id: "gen-1",
      hero_eligibility: { eligible: true, reason: null },
      evolution: [{ generation: 1, current: true,
        glb: "/api/run/x/model/engineering_model.glb" }],
      renders: { status: "OK",
        visual_gate: { verdict: "COMPLETE_PASS" } },
    }, evidence: null } });
    const coupled = resolvePresentationState(
      detail({ status: "RUN_BLOCKED_TRANSPORT",
        user_state_view: finalCloseoutUsv }),
      convincing);
    check("Coupling (mapping half): the directive's blocked-terminal " +
        "payload resolves to INFRASTRUCTURE_PAUSED",
      coupled.state === "INFRASTRUCTURE_PAUSED" &&
        coupled.infrastructurePaused === true);
    check("Coupling (mapping half): the stale scientific fields NEVER " +
        "reconcile the pause into a ready/rejection state",
      coupled.state !== "VISUAL_READY" &&
        coupled.state !== "SCIENTIFIC_REJECTION" &&
        coupled.state !== "TECHNOLOGY_NOT_ESTABLISHED");
    // the source pin: the component's terminal verdict line is gated on
    // the SAME blocked state the hero consumes — !blocked && done && usv
    const stage = fsRead("components", "TechStage.tsx");
    const verdictIdx = stage.indexOf("data-stage-verdict");
    const guardIdx = stage.indexOf("{!blocked && done && usv && (");
    check("Coupling (source pin): the terminal verdict line is guarded " +
        "by !blocked && done && usv (INFRASTRUCTURE_PAUSED => no " +
        "scientific terminal verdict surface)",
      verdictIdx !== -1 && guardIdx !== -1 && guardIdx < verdictIdx &&
        guardIdx > stage.indexOf("data-stage-journal-live"));
    check("Coupling (source pin): the unguarded done && usv condition " +
        "is gone",
      !stage.includes("{done && usv && ("));
  }

  // ----------------------------------------------------------------
  console.log("\n== R452-C2 — item 1a: the FIVE typed retrieval states ==");
  // blockedInsightCards consumes the BACKEND-decided five-state
  // vocabulary verbatim: NOT_REACHED / PENDING / FAILED /
  // RETRIEVED_ZERO / RETRIEVED_POSITIVE are mutually distinct; a
  // measured zero and a measured positive are DIFFERENT typed states;
  // the legacy RETRIEVED value normalizes through the measured count
  // and never regresses into "not reached".
  {
    const supportsOf = (ev) => {
      const cards = blockedInsightCards(ev);
      return cards.find((c) => c.title === "What supports it");
    };
    let card;
    // the five backend-decided states, each rendered distinctly
    card = supportsOf({ retrieval_state: "RETRIEVED_ZERO" });
    check("R452: RETRIEVED_ZERO -> the measured zero (typed, decided by " +
        "the backend ledger)",
      card.headline === "0 sources retrieved");
    card = supportsOf({ retrieval_state: "RETRIEVED_POSITIVE",
      retrieved_count: 12 });
    check("R452: RETRIEVED_POSITIVE + count 12 -> the ACTUAL measured " +
        "count is shown ('12 sources retrieved')",
      card.headline === "12 sources retrieved");
    check("R452: RETRIEVED_POSITIVE is NEVER worded as not-reached",
      card.headline !== "Evidence retrieval not reached" &&
        !card.body.includes("not reached"));
    check("R452: RETRIEVED_POSITIVE is never worded as a measured zero",
      !card.body.includes("measured zero records"));
    card = supportsOf({ retrieval_state: "RETRIEVED_POSITIVE" });
    check("R452: RETRIEVED_POSITIVE with no count in the projection -> " +
        "'Sources retrieved' (the count is not invented here)",
      card.headline === "Sources retrieved" &&
        !card.body.includes("measured 0"));
    // legacy RETRIEVED normalization: stale projections never regress
    card = supportsOf({ retrieval_state: "RETRIEVED", retrieved_count: 0 });
    check("R452: legacy RETRIEVED zero -> the measured zero (never a " +
        "failure, never an absence)",
      card.headline === "0 sources retrieved");
    card = supportsOf({ retrieval_state: "RETRIEVED", retrieved_count: 12 });
    check("R452: legacy RETRIEVED 12 -> the measured count (never " +
        "'not reached')",
      card.headline === "12 sources retrieved" &&
        !card.body.includes("not reached"));
    card = supportsOf({ retrieval_state: "RETRIEVED" });
    check("R452: legacy RETRIEVED, no count -> 'Retrieval executed' " +
        "(count unknown — never zero, never unreachable)",
      card.headline === "Retrieval executed");
    // the five states are mutually distinct
    const fiveHeadlines = new Set([
      supportsOf({ retrieval_state: "NOT_REACHED" }).headline,
      supportsOf({ retrieval_state: "PENDING" }).headline,
      supportsOf({ retrieval_state: "FAILED" }).headline,
      supportsOf({ retrieval_state: "RETRIEVED_ZERO" }).headline,
      supportsOf({ retrieval_state: "RETRIEVED_POSITIVE",
        retrieved_count: 7 }).headline,
    ]);
    check("R452: all FIVE typed states render FIVE DISTINCT headlines " +
        "(no collapse in any direction)",
      fiveHeadlines.size === 5);
    // the measured zero and the measured positive never share wording
    const zero = supportsOf({ retrieval_state: "RETRIEVED_ZERO" });
    const pos = supportsOf({ retrieval_state: "RETRIEVED_POSITIVE",
      retrieved_count: 1 });
    check("R452: RETRIEVED_ZERO and RETRIEVED_POSITIVE render different " +
        "headlines AND different bodies (distinct facts, distinct " +
        "surfaces)",
      zero.headline !== pos.headline && zero.body !== pos.body);
  }

  // ----------------------------------------------------------------
  console.log("\n== R451-C2-CLOSURE — Direction A: the four retrieval states ==");
  // blockedInsightCards must keep NOT_REACHED / PENDING / FAILED /
  // RETRIEVED mutually distinct; RETRIEVED shows the ACTUAL measured
  // count (zero or positive); PENDING is never collapsed into
  // not-reached; a positive measured count is never rendered as
  // "not reached". (The legacy 4-state-era checks — retained as the
  // era-normalization regression.)
  {
    const supportsOf = (ev) => {
      const cards = blockedInsightCards(ev);
      return cards.find((c) => c.title === "What supports it");
    };
    let card = supportsOf({ retrieval_state: "NOT_REACHED" });
    check("A: NOT_REACHED -> 'Evidence retrieval not reached'",
      card.headline === "Evidence retrieval not reached");
    card = supportsOf({ retrieval_state: "PENDING" });
    check("A: PENDING -> 'Evidence retrieval in progress' (pending is " +
        "NEVER collapsed into not-reached)",
      card.headline === "Evidence retrieval in progress" &&
        card.headline !== "Evidence retrieval not reached");
    check("A: PENDING body says pending, not unreachable",
      card.body.includes("pending"));
    card = supportsOf({ retrieval_state: "FAILED" });
    check("A: FAILED -> 'Evidence retrieval failed' (never a measured " +
        "zero, never not-reached)",
      card.headline === "Evidence retrieval failed");
    card = supportsOf({ retrieval_state: "RETRIEVED", retrieved_count: 0 });
    check("A: RETRIEVED zero -> the measured zero",
      card.headline === "0 sources retrieved");
    card = supportsOf({ retrieval_state: "RETRIEVED", retrieved_count: 12 });
    check("A: RETRIEVED 12 -> the ACTUAL measured count is shown " +
        "('12 sources retrieved')",
      card.headline === "12 sources retrieved");
    check("A: RETRIEVED 12 is NEVER worded as not-reached",
      card.headline !== "Evidence retrieval not reached" &&
        !card.body.includes("not reached"));
    check("A: RETRIEVED 12 is never worded as an absence",
      !card.body.includes("measured zero records"));
    card = supportsOf({ retrieval_state: "RETRIEVED" });
    check("A: RETRIEVED with no count in the projection -> 'Retrieval " +
        "executed' (count unknown — never zero, never unreachable)",
      card.headline === "Retrieval executed" &&
        card.headline !== "Evidence retrieval not reached");
    const fourHeadlines = new Set([
      supportsOf({ retrieval_state: "NOT_REACHED" }).headline,
      supportsOf({ retrieval_state: "PENDING" }).headline,
      supportsOf({ retrieval_state: "FAILED" }).headline,
      supportsOf({ retrieval_state: "RETRIEVED", retrieved_count: 7 }).headline,
    ]);
    check("A: all four typed states render four DISTINCT headlines",
      fourHeadlines.size === 4);
  }

  // ----------------------------------------------------------------
  console.log("\n== R451-C2-CLOSURE — Direction B: unknown geometry stays unknown ==");
  // An unrecognized typed geometry_state fails closed to
  // PRESENTATION_STATE_UNAVAILABLE — never GEOMETRY_UNAVAILABLE, never
  // TECHNOLOGY_NOT_ESTABLISHED, never VISUAL_READY — under BOTH
  // found_something attacks, and even with convincing raw fields.
  {
    const unknown = "quantum_lattice_render_v9";
    // attack 1: unknown + found_something=false
    let r = resolvePresentationState(
      detail({ user_state_view: usv({ user_state: "COMPLETED_UNKNOWN",
        finished: true, found_something: false }) }),
      dossier({ tabs: { design: { geometry_state: unknown,
        availability: "UNAVAILABLE" }, evidence: null } }));
    check("B: unknown geometry + found_something=false -> " +
        "PRESENTATION_STATE_UNAVAILABLE",
      r.state === "PRESENTATION_STATE_UNAVAILABLE");
    check("B: unknown + found_something=false NEVER becomes a scientific " +
        "absence (TECHNOLOGY_NOT_ESTABLISHED / SCIENTIFIC_REJECTION)",
      r.state !== "TECHNOLOGY_NOT_ESTABLISHED" &&
        r.state !== "SCIENTIFIC_REJECTION");
    // attack 2: unknown + found_something=true (+ package_available)
    r = resolvePresentationState(
      detail({ user_state_view: usv({ user_state: "COMPLETED_CANDIDATE",
        finished: true, found_something: true, package_available: true }) }),
      dossier({ tabs: { design: { geometry_state: unknown,
        availability: "UNAVAILABLE" }, evidence: null } }));
    check("B: unknown geometry + found_something=true -> " +
        "PRESENTATION_STATE_UNAVAILABLE",
      r.state === "PRESENTATION_STATE_UNAVAILABLE");
    check("B: unknown + found_something=true NEVER becomes " +
        "GEOMETRY_UNAVAILABLE (the backend never said it)",
      r.state !== "GEOMETRY_UNAVAILABLE");
    check("B: unknown + found_something=true NEVER becomes ready",
      r.state !== "VISUAL_READY");
    // attack 3: unknown state + CONVINCING raw fields (the raw fields
    // of a visual-complete payload must not rescue an unrecognized
    // typed state into any current state)
    r = resolvePresentationState(
      detail({ user_state_view: usv({ user_state: "COMPLETED_CANDIDATE",
        found_something: true, package_available: true }) }),
      dossier({ tabs: { design: {
        geometry_state: unknown,
        availability: "AVAILABLE",
        glb: "/api/run/x/model/engineering_model.glb",
        geometry_class: "ENGINEERING_3D",
        engineering_authority: "ENGINEERING",
        hero_eligibility: { eligible: true, reason: null },
        renders: { status: "OK",
          visual_gate: { verdict: "COMPLETE_PASS" } },
      }, evidence: null } }));
    check("B: unknown geometry + convincing raw fields STILL " +
        "PRESENTATION_STATE_UNAVAILABLE",
      r.state === "PRESENTATION_STATE_UNAVAILABLE");
    check("B: the unrecognized state carries NO mountable field and no " +
        "authority claim",
      ["glb", "viewerUrl", "modelUrl"].every((k) => !(k in r)) &&
        r.engineeringAuthority === null);
    check("B: the detail names the unrecognized state and disclaims " +
        "any scientific claim",
      (r.renderBlockDetail ?? "").includes("unrecognized") &&
        (r.renderBlockDetail ?? "").includes("No scientific claim"));
    // source pins: the component locks the unrecognized state out of
    // the viewer/history/gate-badge surfaces and renders its own hero
    const stage = fsRead("components", "TechStage.tsx");
    const vp = stage.indexOf("data-hero-viewport");
    const legacyBranch = stage.indexOf(
      'view.state === "LEGACY_STATE_UNAVAILABLE" ?', vp);
    const unknownBranch = stage.indexOf(
      'view.state === "PRESENTATION_STATE_UNAVAILABLE" ?', vp);
    const viewerBranch = stage.indexOf(") : viewerUrl ? (", vp);
    check("B: TechStage hero order — the unrecognized-state hero " +
        "resolves BEFORE the viewerUrl branch (legacy first, unknown second)",
      legacyBranch !== -1 && unknownBranch !== -1 &&
        viewerBranch !== -1 && legacyBranch < unknownBranch &&
        unknownBranch < viewerBranch);
    check("B: TechStage computes viewerUrl null under the unrecognized " +
        "state (heroGlb + showingHistory both gated)",
      stage.includes("!legacyUnavailable && !unrecognizedState && heroEligible") &&
        stage.includes("!legacyUnavailable && !unrecognizedState && heroEligible &&\n    Boolean(activeRow?.glb)"));
    check("B: TechStage suppresses the gate badge under the " +
        "unrecognized state",
      stage.includes("gateVerdict && !legacyUnavailable && !unrecognizedState"));
    check("B: TechStage has the fail-closed hero component " +
        "(data-hero-unrecognized-state)",
      stage.includes("data-hero-unrecognized-state"));
  }

  // ----------------------------------------------------------------
  console.log("\n== R451-C2-CLOSURE — Direction C: the ONE transport authority ==");
  // The directive's EXACT contradiction fixture: status
  // RUN_BLOCKED_TRANSPORT + a stale/malformed projection claiming
  // COMPLETED_CANDIDATE with every scientific-looking field populated.
  // THE AUTHORITY (singular, explicit, attacked): the run record's
  // canonical status is the transport authority — a transport-terminal
  // status can NEVER become a ready scientific surface, whatever the
  // projection says.
  {
    const contradictory = detail({
      status: "RUN_BLOCKED_TRANSPORT",
      user_state_view: usv({
        user_state: "COMPLETED_CANDIDATE",
        finished: true,
        found_something: true,
        rejected: false,
        package_available: true,
        label: "AUTOMATED INVENTION CANDIDATE",
        decision: "Technology ready",
        meaning: "The candidate survived.",
        outcome: "INVENTION_SURVIVED",
        outcome_label: "AUTOMATED INVENTION CANDIDATE",
      }),
    });
    const convincingReady = dossier({ tabs: { design: {
      geometry_state: "visual_complete",
      engineering_authority: "ENGINEERING",
      availability: "AVAILABLE",
      glb: "/api/run/x/model/engineering_model.glb",
      geometry_class: "ENGINEERING_3D",
      generation_id: "gen-1",
      hero_eligibility: { eligible: true, reason: null },
      evolution: [{ generation: 1, current: true,
        glb: "/api/run/x/model/engineering_model.glb" }],
      renders: { status: "OK",
        visual_gate: { verdict: "COMPLETE_PASS" } },
    }, evidence: null } });
    const r = resolvePresentationState(contradictory, convincingReady);
    check("C: RUN_BLOCKED_TRANSPORT + COMPLETED_CANDIDATE + " +
        "found_something + package_available + visual_complete + " +
        "ENGINEERING -> INFRASTRUCTURE_PAUSED",
      r.state === "INFRASTRUCTURE_PAUSED" &&
        r.infrastructurePaused === true);
    check("C: the contradiction NEVER becomes a ready scientific surface",
      r.state !== "VISUAL_READY" &&
        r.state !== "GEOMETRY_READY_RENDER_BLOCKED" &&
        r.state !== "SCIENTIFIC_REJECTION" &&
        r.state !== "TECHNOLOGY_NOT_ESTABLISHED" &&
        r.state !== "GEOMETRY_UNAVAILABLE");
    check("C: the blocked copy is the verdict the state speaks " +
        "('No scientific conclusion was reached.')",
      r.blocked?.verdictLine === "No scientific conclusion was reached.");
    // the same transport authority must hold for the whole family and
    // must not need the projection at all
    for (const st of ["RUN_BLOCKED_TRANSPORT", "RUN_BLOCKED_ENGINE"]) {
      const rr = resolvePresentationState(
        detail({ status: st, user_state_view: usv({
          user_state: "COMPLETED_CANDIDATE", found_something: true,
          package_available: true }) }),
        convincingReady);
      check(`C: transport-terminal status ${st} -> INFRASTRUCTURE_PAUSED ` +
          "regardless of the projection",
        rr.state === "INFRASTRUCTURE_PAUSED" && rr.infrastructurePaused);
    }
    // positive control: the same scientific payload WITHOUT the
    // transport-terminal status still reaches VISUAL_READY (the
    // authority is transport-terminal-specific, not a universal
    // rejector — Art. V)
    const ok = resolvePresentationState(
      detail({ status: "COMPLETE", user_state_view: usv({
        user_state: "COMPLETED_CANDIDATE", found_something: true,
        package_available: true }) }),
      convincingReady);
    check("C: positive control — status COMPLETE + the same ready " +
        "payload still reaches VISUAL_READY",
      ok.state === "VISUAL_READY");
    // source pins: the status-first transport check exists in the
    // mapping source, ahead of the projection-based rule
    const psSource = fsRead("lib", "presentationState.ts");
    const statusRule = psSource.indexOf(
      'detail.status.startsWith("RUN_BLOCKED")');
    const usvRule = psSource.indexOf("INFRASTRUCTURE_USER_STATES.has(");
    check("C: source pin — the canonical-status transport check exists " +
        "in the mapping (the record outranks the projection)",
      statusRule !== -1 && usvRule !== -1 && statusRule < usvRule);
    check("C: source pin — the authority is documented as singular in " +
        "the mapping source",
      psSource.includes("is the ONLY transport") ||
        psSource.includes("ONLY transport\n//   authority"));
  }

  // ----------------------------------------------------------------
  console.log("\n== R452-C2 — item 2: the sovereign-state boundary ==");
  // The visual layer may render UNKNOWN-class, BLOCKED,
  // READY_FOR_REVIEW-class and VISUAL_READY states; it must NEVER
  // manufacture VALIDATED / SURVIVOR / ENGINEERING_READY. Two pins:
  // (a) the shipping presentation sources carry NO such state
  // vocabulary at all (structural absence), and (b) a payload whose
  // ONLY completion signals are artifact presence (a GLB route, a
  // PDF, an engineering JSON, old UI fields, diagnostic metadata)
  // resolves to a NON-CLAIM state — presence is never an authority.
  {
    // (a) structural absence of the forbidden state vocabulary
    const forbidden = /\b(VALIDATED|SURVIVOR|ENGINEERING_READY)\b/;
    const presentationSources = [
      ["lib", "presentationState.ts"],
      ["components", "TechStage.tsx"],
      ["components", "InfrastructureBlockedHero.tsx"],
      ["components", "DossierSections.tsx"],
      ["components", "DeepDive.tsx"],
      ["components", "DiscoveryPipelineStrip.tsx"],
    ];
    for (const [dir, file] of presentationSources) {
      const src = fsRead(dir, file);
      check(`R452: ${file} carries NO manufactured-state vocabulary ` +
          "(VALIDATED / SURVIVOR / ENGINEERING_READY absent)",
        !forbidden.test(src));
    }
    // (b) the presence-only payload: every directive-named presence
    // signal populated, NO typed geometry_state, NO canonical contract
    const presenceOnly = dossier({
      tabs: {
        design: {
          // old UI fields + artifact presence, all stale/unauthoritative
          availability: "AVAILABLE",
          glb: "/runs/run/MODEL/model-001.glb",
          renders: { status: "OK", visual_gate: "COMPLETE_PASS" },
          pdf_available: true,
          engineering_json_present: true,
          diagnostics: { render_job: "done", watchdog: "PASS" },
          // NO geometry_state field at all
        },
        evidence: null,
      },
    });
    let r = resolvePresentationState(
      detail({ status: "COMPLETE", user_state_view: usv({
        user_state: "COMPLETED_CANDIDATE", finished: true,
        found_something: true, package_available: true,
        decision: "Technology ready",
        meaning: "The candidate survived." }) }),
      presenceOnly);
    check("R452: presence-only payload (GLB route + PDF + engineering " +
        "JSON + legacy fields + diagnostics, no typed state) NEVER " +
        "resolves to VISUAL_READY",
      r.state !== "VISUAL_READY");
    check("R452: presence-only payload -> LEGACY_STATE_UNAVAILABLE " +
        "(the legacy-payload rule: raw presence derives no current " +
        "state at all)",
      r.state === "LEGACY_STATE_UNAVAILABLE");
    check("R452: presence-only payload never claims the engineering " +
        "authority",
      r.engineeringAuthority !== "ENGINEERING");
    // the stale scientific decision strings cannot ride the mapping's
    // output — the mapping returns typed states, never verdict copies
    check("R452: the stale decision/meaning strings never ride the " +
        "mapping output (the mapping returns states, not verdicts)",
      !JSON.stringify(r).includes("Technology ready") &&
        !JSON.stringify(r).includes("The candidate survived"));
    // positive control: the SAME canonical shape through the typed
    // contract still reaches VISUAL_READY (Art. V — not a universal
    // rejector)
    r = resolvePresentationState(
      detail({ status: "COMPLETE", user_state_view: usv({
        user_state: "COMPLETED_CANDIDATE", finished: true,
        found_something: true, package_available: true }) }),
      dossier({ tabs: { design: {
        geometry_state: "visual_complete",
        engineering_authority: "ENGINEERING" }, evidence: null } }));
    check("R452: positive control — the typed canonical chain still " +
        "reaches VISUAL_READY",
      r.state === "VISUAL_READY");
  }
} finally {
  rmSync(OUT, { recursive: true, force: true });
}

console.log(failures === 0
  ? "\nUI TEST BATTERY: ALL PASS"
  : `\nUI TEST BATTERY: ${failures} FAILURE(S)`);
process.exit(failures === 0 ? 0 : 1);
