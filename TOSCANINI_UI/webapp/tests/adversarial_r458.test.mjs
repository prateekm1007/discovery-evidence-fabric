// R458-C2 — THE ADVERSARIAL UX BATTERY (directive §25/§26) + the new
// conversational-action contracts (§4/§5/§7/§18).
//
// The visible result must always match the canonical state. Fourteen
// required states (§25) are exercised at the presentation layer, plus
// the R458 additions: the clarification pause, the Ask/Act route
// table, the honest action-absence copy, the rotation abstraction
// sentence (§26), and the one-line progress discipline (§7).
//
// Run: npm run test:r458   (compiles the lib core -> tests/.build-r458,
//                           then node --test)

import { test } from "node:test";
import assert from "node:assert/strict";
import { execSync } from "node:child_process";
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const build = path.join(here, ".build-r458");
const webapp = path.dirname(here);

if (!existsSync(path.join(build, "present.js"))) {
  execSync(
    `npx tsc lib/present.ts lib/present-types.ts lib/presentationState.ts lib/productEvents.ts lib/actionContract.ts ` +
      `--outDir ${JSON.stringify(build)} --module commonjs --target es2022 ` +
      `--moduleResolution node --skipLibCheck --strict --jsx react-jsx`,
    { cwd: webapp, stdio: "inherit" },
  );
}

const present = await import(path.join(build, "present.js"));
const pe = await import(path.join(build, "productEvents.js"));
const ac = await import(path.join(build, "actionContract.js"));

// ---------------------------------------------------------------------------
// fixtures
// ---------------------------------------------------------------------------

function baseDetail(overrides = {}) {
  return {
    session_id: "ts_r458",
    title: "Reduce pressure loss in multi-lumen tubing",
    user_text: "Find a way to reduce pressure loss in multi-lumen tubing.",
    status: "RUNNING",
    created_at: "2026-09-15T00:00:00Z",
    run_dir: null,
    problem_id: null,
    final_status: null,
    stages: [],
    ...overrides,
  };
}

function conversationText(detail, dossier = null, pkg = false) {
  return present
    .deriveConversation(detail, dossier, pkg)
    .map((m) => {
      const b = m.body ?? m.text ?? m.question ?? "";
      return `${m.kind}: ${b}`;
    })
    .join("\n");
}

// ---------------------------------------------------------------------------
// §25 battery — the fourteen states
// ---------------------------------------------------------------------------

test("B1 transport failure: RUN_BLOCKED_TRANSPORT renders the honest pause, never a verdict", () => {
  const t = conversationText(
    baseDetail({
      status: "RUN_BLOCKED_TRANSPORT",
      run_state: { outcome: "RUN_BLOCKED" },
      user_state_view: { user_state: "COMPLETED_CANDIDATE", found_something: true },
    })
  );
  assert.match(t, /infrastructure/i);
  assert.doesNotMatch(t, /invention survived|promising technology/i);
  assert.doesNotMatch(t, /rejected/i);
});

test("B2 provider rotation (§26): infra failure then progress -> the one abstraction sentence", () => {
  const note = pe.deriveRotationNote([
    { kind: "stage.SYNTHESIZE", status: "FAILED_INFRASTRUCTURE", summary: "transport" },
    { kind: "stage.SYNTHESIZE", status: "COMPLETED", summary: "ok" },
  ]);
  assert.match(note, /continued the investigation using another available reasoning route/);
  // and the NEGATIVE: no progress after the failure -> no rotation claim
  assert.equal(
    pe.deriveRotationNote([{ kind: "stage.SYNTHESIZE", status: "FAILED_INFRASTRUCTURE" }]),
    null
  );
  // the sentence never names a provider, model, or route (§26)
  const events = [
    { kind: "evidence.retrieval_failed", status: "FAILED_INFRASTRUCTURE", source: "unorouter" },
    { kind: "stage.SYNTHESIZE", status: "ACTIVE" },
  ];
  const live = pe.productEventSentence(pe.pickLiveEvent(events));
  const joined = `${pe.deriveRotationNote(events)} ${live.text}`;
  assert.doesNotMatch(joined, /unorouter|xkiro|apinex|bai|qwen|glm|deepseek|minimax/i);
});

test("B3 retrieval failure: FAILED is infrastructure, never evidence of absence", () => {
  const detail = baseDetail({
    status: "COMPLETE",
    run_state: { evidence_state: { state: "FAILED" } },
  });
  const t = conversationText(detail);
  assert.match(t, /Evidence retrieval failed/i);
  assert.match(t, /not evidence of absence|infrastructure state/i);
  assert.doesNotMatch(t, /no (relevant )?(sources|evidence) (were )?found/i);
});

test("B4 retrieval pending: PENDING never collapses into zero or not-reached", () => {
  const detail = baseDetail({ status: "RUNNING" });
  assert.equal(present.deriveRetrievalState(detail, null), "PENDING");
  const t = conversationText(detail);
  assert.match(t, /retrieval is in progress|searching the indexed sources/i);
});

test("B5 stale positive candidate: blocked run suppresses the old COMPLETED snapshot", () => {
  const detail = baseDetail({
    status: "RUN_BLOCKED_TRANSPORT",
    run_state: {
      outcome: "RUN_BLOCKED",
      generations: { generations: [{ gen: 1, label: "Invention 01", challenge: { survived: true } }] },
    },
    user_state_view: { user_state: "COMPLETED_CANDIDATE", label: "A promising technology" },
  });
  const t = conversationText(detail);
  assert.match(t, /infrastructure/i);
  assert.doesNotMatch(t, /promising technology|survived attack/i);
  // the next action is the resume — the one honest action on a blocked run
  const msgs = present.deriveConversation(detail, null, false);
  const outcome = msgs.find((m) => m.kind === "outcome");
  assert.equal(outcome.next.kind, "retry");
});

test("B6 candidate rejection: a real scientific verdict reads as Rejected — a finding", () => {
  const detail = baseDetail({
    status: "COMPLETE",
    final_status: "MALFORMED_OR_FALSE_PREMISE",
    user_state_view: { user_state: "COMPLETED_FALSE_PREMISE", rejected: true },
  });
  const t = conversationText(detail);
  assert.match(t, /Rejected/i);
  assert.match(t, /a finding|did its job/i);
});

test("B7 attack NOT_RUN: never a default 'survived'", () => {
  const detail = baseDetail({
    status: "COMPLETE",
    run_state: {
      evidence_state: { state: "GATHERED", records_found: 3 },
      attack_state: { overall: "" },
      generations: { generations: [{ gen: 1, label: "Invention 01" }] },
    },
  });
  assert.equal(present.deriveAttackState(detail, null), "NOT_RUN");
  const msgs = present.deriveConversation(detail, null, false);
  const attack = msgs.find((m) => m.kind === "attack");
  assert.equal(attack.state, "NOT_RUN");
  assert.match(attack.body, /has not been completed/i);
  assert.match(attack.body, /Nothing is claimed either way/i);
  // no message carries the SURVIVED meta label
  assert.ok(!msgs.some((m) => m.epi === "SURVIVED_ATTACK"));
  // no candidate renders the SURVIVED chip
  const cands = msgs.find((m) => m.kind === "candidates");
  assert.ok(cands.items.every((c) => c.attack !== "SURVIVED"));
});

test("B8 attack CONTESTED: objection preserved and escalated — never a pass, never a kill", () => {
  const detail = baseDetail({
    status: "COMPLETE",
    run_state: {
      generations: {
        generations: [
          { gen: 1, challenge: { escalated_objection: "uncalibrated instrument" } },
        ],
      },
    },
  });
  assert.equal(present.deriveAttackState(detail, null), "CONTESTED");
  const t = conversationText(detail);
  assert.match(t, /escalated for adjudication|not treated as a verdict/i);
});

test("B9 geometry unknown: nothing established is said so — never 'unavailable'", () => {
  const detail = baseDetail({ status: "COMPLETE" });
  assert.equal(present.deriveGeometryState(detail, null), "UNKNOWN");
  const s = present.geometrySentence("UNKNOWN", null);
  assert.match(s, /not established/i);
});

test("B10 engineering complete: the canonical-geometry sentence, never an upgrade", () => {
  const dossier = {
    tabs: {
      design: { availability: "AVAILABLE", engineering_authority: "ENGINEERING" },
    },
  };
  const detail = baseDetail({ status: "COMPLETE" });
  assert.equal(present.deriveGeometryState(detail, dossier), "ENGINEERING");
  const s = present.geometrySentence("ENGINEERING", dossier);
  assert.match(s, /canonical engineering geometry/i);
});

test("B11 experiment proposed: the decisive test reads as designed, with its falsification", () => {
  const dossier = {
    tabs: { experiment: { availability: "AVAILABLE" } },
  };
  const next = present.deriveNextAction(baseDetail({ status: "COMPLETE" }), dossier, false);
  assert.equal(next.kind, "surface");
  assert.equal(next.surface, "experiment");
});

test("B12 experiment contradicted: infrastructure contradiction is not a scientific kill", () => {
  // the experiment stage failing on transport is FAILED_INFRASTRUCTURE —
  // the product-event map renders the distinction
  const s = pe.productEventSentence({
    kind: "stage.KILLER_EXPERIMENT",
    status: "FAILED_INFRASTRUCTURE",
  });
  assert.match(s.text, /could not complete|infrastructure, not a verdict/i);
  assert.equal(s.infrastructure, true);
  // a scientific failure keeps its finding language
  const sci = pe.productEventSentence({
    kind: "stage.KILLER_EXPERIMENT",
    status: "FAILED_SCIENTIFIC",
  });
  assert.match(sci.text, /scientific failure|finding/i);
  assert.equal(sci.infrastructure, false);
});

test("B13 package blocked: no package exists and none is promised", () => {
  const detail = baseDetail({
    status: "COMPLETE",
    final_status: "INVENTION_REQUIRES_EXPERIMENT",
    user_state_view: { user_state: "COMPLETED_CANDIDATE", package_available: false },
  });
  const next = present.deriveNextAction(detail, null, false);
  assert.notEqual(next.kind, "package");
  const t = conversationText(detail, null, false);
  assert.doesNotMatch(t, /Download the technology package/i);
});

test("B14 package ready: exactly one package action", () => {
  const detail = baseDetail({
    status: "COMPLETE",
    final_status: "INVENTION_REQUIRES_EXPERIMENT",
    user_state_view: { user_state: "COMPLETED_PACKAGE", package_available: true },
  });
  const next = present.deriveNextAction(detail, null, true);
  assert.equal(next.kind, "package");
  assert.match(next.label, /Download the technology package/);
});

// ---------------------------------------------------------------------------
// §4 — the clarification pause: the conversation changes the discovery
// ---------------------------------------------------------------------------

test("R458 clarification pause: the engine's ONE question renders; nothing resumes it but the answer", () => {
  const detail = baseDetail({
    status: "AWAITING_CLARIFICATION",
    clarification: {
      field: "target_variable",
      question: "You asked to reduce pressure loss — should the engine optimize lumen geometry, or the manifold layout?",
      decision_changed: "which mechanisms are admissible",
    },
  });
  const msgs = present.deriveConversation(detail, null, false);
  const cl = msgs.find((m) => m.kind === "clarification");
  assert.ok(cl, "the clarification message exists");
  assert.match(cl.question, /manifold layout/);
  assert.match(cl.decisionChanged, /mechanisms are admissible/);
  // the pause is not an outcome, not an error, and never a progress claim
  assert.ok(!msgs.some((m) => m.kind === "outcome"));
  const t = conversationText(detail);
  assert.match(t, /paused/i);
});

// ---------------------------------------------------------------------------
// §4/§5/§18 — Ask vs Act: the deterministic route table
// ---------------------------------------------------------------------------

test("R458 route table: directives map to their canonical actions", () => {
  const cases = [
    ["Try another mechanism.", "CHANGE_MECHANISM"],
    ["Look for contradictory evidence.", "FIND_EVIDENCE"],
    ["Use this paper.", "UPLOAD_EVIDENCE"],
    ["Challenge candidate 2.", "ATTACK"],
    ["Keep the engineering constraint but change the mechanism.", "CHANGE_MECHANISM"],
    ["Compare the mechanisms.", "COMPARE_MECHANISMS"],
    ["Design the decisive experiment.", "REQUEST_EXPERIMENT"],
  ];
  for (const [text, verb] of cases) {
    const r = ac.classifyMessage(text);
    assert.equal(r.kind, "action", text);
    assert.equal(r.verb, verb, text);
  }
});

test("R458 route table: questions stay questions (ASK is the default)", () => {
  for (const text of [
    "Why was candidate 2 rejected?",
    "What experiment would kill this?",
    "What does Toscanini believe here?",
    "What remains unknown?",
  ]) {
    const r = ac.classifyMessage(text);
    assert.equal(r.kind, "ask", text);
  }
});

test("R458 honest action absence: the not-available copy never claims execution", () => {
  assert.match(ac.ACTION_NOT_AVAILABLE_COPY, /can't change the investigation/i);
  assert.match(ac.ACTION_NOT_AVAILABLE_COPY, /Nothing was changed/i);
});

// ---------------------------------------------------------------------------
// §7 — one progress sentence; the clarification event is not machinery
// ---------------------------------------------------------------------------

test("R458 one-line discipline: the live block renders the newest ACTIVE event only", () => {
  const events = [
    { kind: "stage.RETRIEVE", status: "COMPLETED" },
    { kind: "stage.FREEZE", status: "COMPLETED" },
    { kind: "stage.SYNTHESIZE", status: "ACTIVE" },
  ];
  const live = pe.productEventSentence(pe.pickLiveEvent(events));
  assert.ok(live.loading);
  assert.match(live.text, /Comparing mechanisms/);
});

test("R458 clarification.requested renders as a question, never as infrastructure", () => {
  const s = pe.productEventSentence({ kind: "clarification.requested", status: "BLOCKED" });
  assert.ok(s.text.length > 0);
  assert.equal(s.infrastructure, false);
  assert.doesNotMatch(s.text, /technical step|infrastructure/i);
});
