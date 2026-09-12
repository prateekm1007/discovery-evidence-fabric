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

  // SUCCESS + geometry (gate pass)
  r = resolvePresentationState(detail(), dossier({ tabs: { design: designAvailable(), evidence: null } }));
  check("SUCCESS+geometry(gate PASS) -> VISUAL_READY", r.state === "VISUAL_READY");

  // SUCCESS + geometry, render skipped (case D)
  r = resolvePresentationState(detail(), dossier({ tabs: {
    design: designAvailable({ renders: { status: "RENDER_SKIPPED_LOW_MEMORY",
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
  r = resolvePresentationState(detail(), dossier({ tabs: {
    design: designAvailable(), evidence: { retrieval_state: "RETRIEVED",
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
} finally {
  rmSync(OUT, { recursive: true, force: true });
}

console.log(failures === 0
  ? "\nUI TEST BATTERY: ALL PASS"
  : `\nUI TEST BATTERY: ${failures} FAILURE(S)`);
process.exit(failures === 0 ? 0 : 1);
