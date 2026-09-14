// R453-C2 — ADVERSARIAL UI TESTS (brief §40) for the canonical-state
// presentation layer (lib/present.ts).
//
// These are the six REQUIRED fixtures plus positive controls and
// metamorphic attacks. They run the React-free presentation core in
// plain Node — the honesty contracts are executable evidence
// (Art. XVI: code is a hypothesis; tests are evidence).
//
// Run: npm run test:present   (compiles lib/present*.ts -> tests/.build,
//                              then node --test)

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const build = path.join(here, ".build");
const mod = await import(path.join(build, "present.js"));

if (!existsSync(path.join(build, "present.js"))) {
  throw new Error("presentation layer not compiled — run npm run test:present");
}

// ---------------------------------------------------------------------------
// fixture builders — minimal canonical-state objects with ONLY the fields
// the presentation layer reads (the compiled core is type-erased; the
// fixtures double as the executable documentation of the contract).
// ---------------------------------------------------------------------------

function baseDetail(overrides = {}) {
  return {
    session_id: "ts_test",
    title: "Reduce pressure loss in multi-lumen medical tubing",
    user_text: "Find a better way to reduce pressure loss in multi-lumen medical tubing.",
    status: "RUNNING",
    created_at: "2026-09-14T00:00:00Z",
    run_dir: null,
    problem_id: null,
    final_status: null,
    stages: [],
    ...overrides,
  };
}

function detailWithRunState(status, runState, extra = {}) {
  return baseDetail({ status, run_state: runState, ...extra });
}

// ---------------------------------------------------------------------------
// POSITIVE CONTROL — a healthy successful run reads as success
// ---------------------------------------------------------------------------

test("positive control: complete run with package reads positive end-to-end", () => {
  const detail = detailWithRunState("COMPLETE", {
    outcome: "INVENTION_SURVIVED",
    outcome_label: "Invention survived",
    evidence_state: { state: "GATHERED", records_found: 18, sources: ["europepmc", "nasa"] },
    mechanism_state: { state: "GENERATED", mechanism: "lumen geometry staging", intervention: "staged lumen taper" },
    attack_state: { state: "DONE", overall: "SURVIVED" },
    generations: {
      generations: [
        {
          gen: 1,
          label: "INVENTION 01",
          architecture: {
            mechanism: "lumen geometry staging",
            intervention: "staged lumen taper",
            expected_effect: "lower pressure loss at equal flow",
            falsification_test: "bench pressure sweep vs baseline tubing",
          },
          challenge: { survived: true, evidence_verified: true },
        },
      ],
      current_invention: { gen: 1 },
    },
  }, {
    user_state_view: {
      user_state: "COMPLETED_PACKAGE",
      label: "Completed — package ready",
      decision: "The surviving candidate is packaged.",
      meaning: "",
      finished: true,
      found_something: true,
      rejected: false,
      package_available: true,
    },
  });
  const dossier = {
    tabs: {
      overview: { availability: "AVAILABLE", mechanism: "lumen geometry staging" },
      evidence: { availability: "AVAILABLE", retrieved_count: 18, used_count: 14, items: [{ id: "e1" }] },
      design: { availability: "AVAILABLE", conceptual: false, hero_eligibility: { eligible: true } },
      experiment: { availability: "AVAILABLE" },
      engineering: { availability: "AVAILABLE" },
      transfer: { availability: "AVAILABLE" },
    },
  };
  const msgs = mod.deriveConversation(detail, dossier, true);
  const kinds = msgs.map((m) => m.kind);
  assert.ok(kinds.includes("evidence"), "evidence card present");
  const ev = msgs.find((m) => m.kind === "evidence");
  assert.equal(ev.state, "RETRIEVED_POSITIVE");
  assert.equal(ev.retrieved, 18);
  assert.ok(kinds.includes("candidates"), "candidates present");
  assert.ok(kinds.includes("attack"), "attack present");
  const atk = msgs.find((m) => m.kind === "attack");
  assert.equal(atk.state, "SURVIVED");
  assert.ok(!/not been completed/i.test(atk.body));
  const out = msgs.find((m) => m.kind === "outcome");
  assert.equal(out.tone, "positive");
  const arts = msgs.filter((m) => m.kind === "artifact");
  assert.ok(arts.some((a) => a.surface === "package"), "package artifact present");
  assert.ok(arts.some((a) => a.surface === "model"), "model artifact present");
  assert.equal(out.next?.label, "Download the technology package");
});

// ---------------------------------------------------------------------------
// TEST A — candidate = REJECTED, visual complete -> "Rejected", never success
// ---------------------------------------------------------------------------

test("Test A: rejected outcome renders Rejected, never a successful invention", () => {
  const detail = detailWithRunState("COMPLETE", {
    outcome: "FALSE_PREMISE_INCOHERENT",
    evidence_state: { state: "GATHERED", records_found: 7, sources: [] },
    generations: {
      generations: [
        {
          gen: 1,
          architecture: { intervention: "flexible neck", mechanism: "bending relief" },
          challenge: { killed: true, kill_stage: "PROBLEM_EXISTENCE", kill_reason: "failure mode not documented" },
        },
      ],
      current_invention: { gen: 1 },
    },
  }, {
    user_state_view: {
      user_state: "COMPLETED_FALSE_PREMISE",
      label: "Completed — false premise",
      decision: "The premise is physically incoherent; reformulate.",
      meaning: "",
      finished: true,
      found_something: false,
      rejected: true,
      package_available: false,
    },
  });
  const dossier = {
    tabs: {
      design: { availability: "AVAILABLE", conceptual: true, hero_eligibility: { eligible: true } },
      overview: {},
      evidence: { availability: "AVAILABLE", retrieved_count: 7 },
    },
  };
  const msgs = mod.deriveConversation(detail, dossier, false);
  const out = msgs.find((m) => m.kind === "outcome");
  assert.ok(out, "outcome present");
  assert.equal(out.tone, "rejected");
  assert.match(out.label, /Rejected/i);
  assert.ok(!/promising technology/i.test(out.label + out.body));
  assert.ok(!msgs.some((m) => m.kind === "artifact" && m.surface === "package"));
  // the next action is NOT a package
  assert.notEqual(out.next?.kind, "package");
});

// ---------------------------------------------------------------------------
// TEST B — RUN_BLOCKED_TRANSPORT + stale COMPLETED_CANDIDATE +
// visual_complete + ENGINEERING -> current run blocked; stale positives
// SUPPRESSED (the exact regression fixture from the directive)
// ---------------------------------------------------------------------------

test("Test B: blocked run suppresses stale COMPLETED_CANDIDATE + visual_complete + ENGINEERING positives", () => {
  const detail = detailWithRunState("RUN_BLOCKED_TRANSPORT", {
    outcome: "RUN_BLOCKED",
    outcome_label: "Blocked by infrastructure",
    evidence_state: { state: "GATHERED", records_found: 12, sources: ["europepmc"] },
    mechanism_state: { state: "GENERATED", mechanism: "staged taper" },
    invention_state: { state: "EXISTS", final_status: "AUTOMATED_INVENTION_CANDIDATE", package_built: true },
    engineering: { state: "EXISTS" },
    failure_state: { state: "INFRASTRUCTURE", error: "all LLM transports unreachable" },
    generations: {
      generations: [
        {
          gen: 1,
          architecture: { intervention: "staged taper", expected_effect: "lower pressure loss" },
          challenge: { survived: true },
        },
      ],
      current_invention: { gen: 1 },
      survivor_reached: true,
    },
  }, {
    // THE STALE POSITIVE: an older user_state_view snapshot says the run
    // completed with a candidate and a package. The CURRENT run status is
    // blocked. The conversation must read BLOCKED.
    user_state_view: {
      user_state: "COMPLETED_CANDIDATE",
      label: "Completed — candidate found",
      decision: "candidate recorded",
      meaning: "",
      finished: true,
      found_something: true,
      rejected: false,
      package_available: true,
    },
    package: { complete: true, zip_name: "package.zip" },
  });
  const dossier = {
    tabs: {
      design: {
        availability: "AVAILABLE",
        conceptual: false,
        hero_eligibility: { eligible: true },
        renders: { status: "SUCCEEDED", visual_gate: { verdict: "COMPLETE_PASS" } },
      },
      overview: {},
      evidence: { availability: "AVAILABLE", retrieved_count: 12 },
    },
  };
  // suppression gate itself
  assert.equal(mod.suppressStalePositives(detail), true);
  const msgs = mod.deriveConversation(detail, dossier, true);
  assert.ok(!msgs.some((m) => m.kind === "candidates"), "no stale candidates message");
  assert.ok(!msgs.some((m) => m.kind === "artifact"), "no stale artifact cards");
  const out = msgs.find((m) => m.kind === "outcome");
  assert.ok(out, "outcome present");
  assert.equal(out.tone, "blocked");
  assert.match(out.label, /blocked/i);
  assert.ok(!/candidate found/i.test(out.label + out.body), "stale COMPLETED_CANDIDATE label suppressed");
  assert.match(out.body, /infrastructure state, never a scientific result/i);
  assert.equal(out.next?.kind, "retry");
  // next-action ladder agrees
  assert.equal(mod.deriveNextAction(detail, dossier, true)?.kind, "retry");
  // and the rejected-state guard cannot be tricked into calling it rejected
  assert.equal(mod.isRejectedOutcome(detail), false);
});

test("Test B (metamorphic): blocked status wins even when outcome field is missing", () => {
  const detail = detailWithRunState("INTERRUPTED", {
    // no outcome field at all — stale positives on the record only
  }, {
    user_state_view: {
      user_state: "COMPLETED_CANDIDATE",
      label: "Completed — candidate found",
      decision: "x", meaning: "", finished: true,
      found_something: true, rejected: false, package_available: true,
    },
    package: { complete: true },
  });
  assert.equal(mod.suppressStalePositives(detail), true);
  const msgs = mod.deriveConversation(detail, {}, true);
  const out = msgs.find((m) => m.kind === "outcome");
  assert.equal(out.tone, "blocked");
  assert.ok(!msgs.some((m) => m.kind === "artifact"));
});

// ---------------------------------------------------------------------------
// TEST C — retrieval = PENDING -> "in progress", never "not found"
// ---------------------------------------------------------------------------

test("Test C: PENDING retrieval says in-progress, never not-found", () => {
  const detail = detailWithRunState("RUNNING", {
    evidence_state: { state: "PENDING", records_found: 0, sources: [] },
  });
  assert.equal(mod.deriveRetrievalState(detail, null), "PENDING");
  const s = mod.retrievalSentence("PENDING", detail, null);
  assert.match(s, /in progress/i);
  assert.doesNotMatch(s, /not found|no evidence|no records/i);
  const msgs = mod.deriveConversation(detail, null, false);
  const line = msgs.find((m) => m.id?.startsWith?.("e"));
  assert.ok(line, "evidence line present");
  assert.doesNotMatch(JSON.stringify(line), /not found|no evidence exists/i);
});

// ---------------------------------------------------------------------------
// TEST D — retrieval = FAILED -> "retrieval failed", never "no evidence exists"
// ---------------------------------------------------------------------------

test("Test D: FAILED retrieval says failed — an infrastructure state, never absence", () => {
  const detail = detailWithRunState("RUNNING", {
    evidence_state: { state: "FAILED", records_found: 0, sources: [] },
  });
  assert.equal(mod.deriveRetrievalState(detail, null), "FAILED");
  const s = mod.retrievalSentence("FAILED", detail, null);
  assert.match(s, /failed/i);
  assert.match(s, /not evidence of absence/i);
  assert.doesNotMatch(s, /no evidence exists|no relevant sources exist/i);
});

test("Test D (sibling): RETRIEVED_ZERO states the query-scoped fact, never novelty", () => {
  const detail = detailWithRunState("COMPLETE", {
    evidence_state: { state: "GATHERED", records_found: 0, sources: [] },
  });
  assert.equal(mod.deriveRetrievalState(detail, null), "RETRIEVED_ZERO");
  const s = mod.retrievalSentence("RETRIEVED_ZERO", detail, null);
  assert.match(s, /returned no matching records/i);
  assert.match(s, /not evidence that the concept is novel/i);
});

test("Test D (sibling): NOT_REACHED never becomes a finding about the problem", () => {
  const detail = detailWithRunState("ERROR_BUILD", {
    evidence_state: { state: "NOT_REACHED", records_found: 0, sources: [] },
  });
  assert.equal(mod.deriveRetrievalState(detail, null), "NOT_REACHED");
  const s = mod.retrievalSentence("NOT_REACHED", detail, null);
  assert.match(s, /not reached|never began/i);
  assert.doesNotMatch(s, /no evidence exists/i);
});

// ---------------------------------------------------------------------------
// TEST E — geometry = UNKNOWN -> "not established", NOT "unavailable"
// ---------------------------------------------------------------------------

test("Test E: UNKNOWN geometry says not-established; UNAVAILABLE is a different sentence", () => {
  const unknown = { tabs: { design: { availability: "NOT_ESTABLISHED" } } };
  assert.equal(mod.deriveGeometryState(baseDetail({ status: "COMPLETE" }), unknown), "UNKNOWN");
  const sUnknown = mod.geometrySentence("UNKNOWN", unknown);
  assert.match(sUnknown, /not established/i);
  assert.doesNotMatch(sUnknown, /unavailable/i);

  const unavail = {
    tabs: { design: { availability: "UNAVAILABLE", note: "renderer offline" } },
  };
  assert.equal(mod.deriveGeometryState(baseDetail({ status: "COMPLETE" }), unavail), "UNAVAILABLE");
  const sUnavail = mod.geometrySentence("UNAVAILABLE", unavail);
  assert.match(sUnavail, /exists on this run/i);
  assert.match(sUnavail, /unavailable/i);
  assert.notEqual(sUnknown, sUnavail);
});

test("Test E (sibling): conceptual model never claims engineering geometry", () => {
  const d = {
    tabs: { design: { availability: "AVAILABLE", conceptual: true, hero_eligibility: { eligible: true } } },
  };
  assert.equal(mod.deriveGeometryState(baseDetail({ status: "COMPLETE" }), d), "CONCEPTUAL");
  const s = mod.geometrySentence("CONCEPTUAL", d);
  assert.match(s, /conceptual/i);
  assert.match(s, /not validated engineering geometry/i);
});

// ---------------------------------------------------------------------------
// TEST F — attack = NOT_RUN -> "has not been completed", never "survived"
// ---------------------------------------------------------------------------

test("Test F: NOT_RUN attack never reads as survived", () => {
  const detail = detailWithRunState("COMPLETE", {
    // a terminal run whose record carries a candidate but NO attack result
    generations: {
      generations: [{ gen: 1, architecture: { intervention: "x" } }],
      current_invention: { gen: 1 },
    },
  });
  assert.equal(mod.deriveAttackState(detail, null), "NOT_RUN");
  const s = mod.attackSentence("NOT_RUN", detail);
  assert.match(s, /has not been completed/i);
  assert.doesNotMatch(s, /candidate survived|it survived/i);
  const msgs = mod.deriveConversation(detail, { tabs: {} }, false);
  const atk = msgs.find((m) => m.kind === "attack");
  assert.ok(atk, "attack line present for candidate-bearing runs");
  assert.equal(atk.state, "NOT_RUN");
  assert.doesNotMatch(atk.body, /candidate survived|it survived/i);
});

test("Test F (metamorphic): explicit escalation is CONTESTED, never silently survived", () => {
  const detail = detailWithRunState("COMPLETE", {
    generations: {
      generations: [
        {
          gen: 1,
          challenge: {
            escalated_objection: {
              calibration_state: "NOT_CALIBRATED",
              preserved_objections: [{ attack_class: "evidence", basis: "objection basis" }],
            },
          },
        },
      ],
      current_invention: { gen: 1 },
    },
  });
  assert.equal(mod.deriveAttackState(detail, null), "CONTESTED");
  const s = mod.attackSentence("CONTESTED", detail);
  assert.match(s, /not calibrated/i);
  assert.match(s, /escalated/i);
  assert.doesNotMatch(s, /^it survived/i);
});

// ---------------------------------------------------------------------------
// next-action ladder (brief §19 — ONE primary recommendation)
// ---------------------------------------------------------------------------

test("next-best action: single recommendation ladder", () => {
  const running = detailWithRunState("RUNNING", {});
  assert.equal(mod.deriveNextAction(running, null, false), null);
  const blocked = detailWithRunState("RUN_BLOCKED_TRANSPORT", { outcome: "RUN_BLOCKED" });
  assert.equal(mod.deriveNextAction(blocked, null, false)?.kind, "retry");
  const rejected = detailWithRunState("COMPLETE", { outcome: "FALSE_PREMISE_INCOHERENT" }, {
    user_state_view: { rejected: true, user_state: "COMPLETED_FALSE_PREMISE" },
  });
  assert.equal(mod.deriveNextAction(rejected, null, false)?.kind, "new");
  const withPkg = detailWithRunState("COMPLETE", { outcome: "INVENTION_SURVIVED" }, {
    user_state_view: { user_state: "COMPLETED_PACKAGE", rejected: false },
  });
  assert.equal(mod.deriveNextAction(withPkg, null, true)?.kind, "package");
});

// ---------------------------------------------------------------------------
// epistemic meta vocabulary (brief §10) — derived, never upgraded
// ---------------------------------------------------------------------------

test("epistemic meta mapping preserves the recorded class", () => {
  assert.equal(mod.epistemicMeta("RETRIEVED"), "FOUND");
  assert.equal(mod.epistemicMeta("INFERRED"), "INFERRED");
  assert.equal(mod.epistemicMeta("HYPOTHESIZED"), "HYPOTHESIS");
  assert.equal(mod.epistemicMeta("COMPUTED"), "TESTED");
  assert.equal(mod.epistemicMeta("SIMULATED"), "TESTED");
  assert.equal(mod.epistemicMeta("UNKNOWN"), "UNKNOWN");
  assert.equal(mod.epistemicMeta("SOMETHING_NEW"), null);
});
