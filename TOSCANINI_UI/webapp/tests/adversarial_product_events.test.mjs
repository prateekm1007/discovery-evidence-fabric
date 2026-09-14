// R454-C2 — ADVERSARIAL TESTS for the product event map
// (lib/productEvents.ts — brief §22 "conversation event rendering" +
// §25 "loading states").
//
// Executable honesty contracts:
//   G1  machine vocabulary NEVER reaches the conversation
//       ("engine stage X recorded at …", "persisted its envelope",
//       raw kind tokens) — the BS-009 class this round closes
//   G2  infrastructure events read as infrastructure, never as a
//       scientific verdict (Art. LXI; the §22 BLOCKED_PROVIDER rule:
//       "The candidate has not been rejected")
//   G3  a completed ATTACK stage never announces "survived" (the
//       Test F discipline applies to the event layer too)
//   G4  loading sentences are meaningful actions (§25), never
//       implementation telemetry, never verdict language
//   G5  pickLiveEvent: active work wins; an infrastructure pause is
//       its own state and is never rendered as active work (R436 §5B)
//
// Run: npm run test:events  (compiles lib/productEvents.ts ->
//      tests/.build-events, then node --test)

import { test } from "node:test";
import assert from "node:assert/strict";
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const build = path.join(here, ".build-events");
const mod = await import(path.join(build, "productEvents.js"));

if (!existsSync(path.join(build, "productEvents.js"))) {
  throw new Error("product event map not compiled — run npm run test:events");
}

const MACHINE_VOCAB =
  /engine stage|persisted its envelope|envelope_[A-Z_]+|recorded at 20\d\d|RUN_BLOCKED|FAILED_INFRASTRUCTURE|stage\.SYNTHESIZE|\bevt_[0-9a-f]/i;

function ev(kind, status, extra = {}) {
  return { kind, status, summary: "engine stage X recorded at 2026-09-14T00:00:00Z", ...extra };
}

// ---------------------------------------------------------------------------
// G1 — machine vocabulary never reaches the conversation
// ---------------------------------------------------------------------------

test("G1: every mapped event renders human language, never the journal's machine summary", () => {
  const kinds = [
    ["problem.extract", "ACTIVE"],
    ["problem.extract", "COMPLETED"],
    ["evidence.retrieval_started", "ACTIVE"],
    ["evidence.retrieved", "COMPLETED", { source: "europepmc", count: 13 }],
    ["evidence.retrieval_failed", "FAILED_INFRASTRUCTURE"],
    ["evidence.bound", "COMPLETED"],
    ["stage.RETRIEVE", "ACTIVE"],
    ["stage.SYNTHESIZE", "ACTIVE"],
    ["stage.ATTACK", "ACTIVE"],
    ["stage.KILLER_EXPERIMENT", "ACTIVE"],
    ["stage.ADJUDICATION", "COMPLETED"],
    ["geometry.created", "COMPLETED"],
    ["package.completed", "COMPLETED"],
    ["investigation.terminal", "COMPLETED"],
    ["investigation.terminal", "FAILED_INFRASTRUCTURE"],
  ];
  for (const [kind, status, extra] of kinds) {
    const s = mod.productEventSentence(ev(kind, status, extra));
    assert.ok(s.text.length > 0, `${kind}/${status} renders a sentence`);
    assert.doesNotMatch(s.text, MACHINE_VOCAB, `${kind}/${status} is machine-free`);
  }
});

test("G1 (metamorphic): the backend summary is preserved for the technical record, not shown", () => {
  const e = ev("stage.SYNTHESIZE", "ACTIVE");
  const s = mod.productEventSentence(e);
  assert.doesNotMatch(s.text, /recorded at/);
  // the raw summary stays on the event itself (the component passes it
  // to title + the journal surface) — the map never needs to fake it
  assert.match(e.summary, /recorded at/);
});

// ---------------------------------------------------------------------------
// G2 — infrastructure reads as infrastructure, never a scientific verdict
// ---------------------------------------------------------------------------

test("G2: BLOCKED_PROVIDER class (terminal infra) — 'could not be completed', never 'rejected'", () => {
  const s = mod.productEventSentence(ev("investigation.terminal", "FAILED_INFRASTRUCTURE"));
  assert.match(s.text, /infrastructure/i);
  assert.match(s.text, /could not be completed/i);
  assert.match(s.text, /nothing has been rejected/i);
  assert.equal(s.infrastructure, true);
  assert.doesNotMatch(s.text, /candidate (was|has been) rejected|the candidate failed/i);
});

test("G2: a failed evidence source is never 'no evidence exists'", () => {
  const s = mod.productEventSentence(ev("evidence.retrieval_failed", "FAILED_INFRASTRUCTURE"));
  assert.match(s.text, /could not be reached/i);
  assert.match(s.text, /absence is never concluded/i);
  assert.equal(s.infrastructure, true);
  assert.doesNotMatch(s.text, /no evidence exists|no records exist/i);
});

test("G2: an infrastructure-blocked stage step names infrastructure, not the idea", () => {
  const s = mod.productEventSentence(ev("stage.SYNTHESIZE", "FAILED_INFRASTRUCTURE"));
  assert.match(s.text, /infrastructure/i);
  assert.doesNotMatch(s.text, /failed the mechanism|rejected/i);
  assert.equal(s.infrastructure, true);
});

// ---------------------------------------------------------------------------
// G3 — the attack stage's COMPLETED event never upgrades to "survived"
// ---------------------------------------------------------------------------

test("G3: ATTACK COMPLETED is verdict-neutral", () => {
  const s = mod.productEventSentence(ev("stage.ATTACK", "COMPLETED"));
  assert.doesNotMatch(s.text, /survived|passed|it held up/i);
  assert.match(s.text, /record/i);
  assert.equal(s.loading, false);
});

// ---------------------------------------------------------------------------
// G4 — loading sentences are meaningful actions (brief §25 register)
// ---------------------------------------------------------------------------

test("G4: the §25 example actions exist as loading sentences", () => {
  const investigating = mod.productEventSentence(ev("evidence.retrieval_started", "ACTIVE"));
  assert.match(investigating.text, /Investigating evidence/i);
  assert.equal(investigating.loading, true);
  const comparing = mod.productEventSentence(ev("stage.SYNTHESIZE", "ACTIVE"));
  assert.match(comparing.text, /Comparing mechanisms/i);
  const challenging = mod.productEventSentence(ev("stage.ATTACK", "ACTIVE"));
  assert.match(challenging.text, /Challenging the leading candidate/i);
  const engineering = mod.productEventSentence(ev("geometry.created", "ACTIVE"));
  assert.match(engineering.text, /technology model/i);
});

test("G4: loading sentences never carry verdict language", () => {
  const kinds = [
    ["stage.RETRIEVE", "ACTIVE"],
    ["stage.SYNTHESIZE", "ACTIVE"],
    ["stage.ATTACK", "ACTIVE"],
    ["stage.KILLER_EXPERIMENT", "ACTIVE"],
    ["evidence.retrieval_started", "ACTIVE"],
  ];
  for (const [kind, status] of kinds) {
    const s = mod.productEventSentence(ev(kind, status));
    assert.equal(s.loading, true, `${kind} is a loading sentence`);
    assert.doesNotMatch(s.text, /failed|rejected|survived|blocked/i);
  }
});

// ---------------------------------------------------------------------------
// G5 — pickLiveEvent: active wins; pause is its own state
// ---------------------------------------------------------------------------

test("G5: active work wins over an older infrastructure pause", () => {
  const events = [
    ev("stage.RETRIEVE", "COMPLETED"),
    ev("stage.SYNTHESIZE", "FAILED_INFRASTRUCTURE"),
    ev("stage.SYNTHESIZE", "ACTIVE"),
  ];
  const live = mod.pickLiveEvent(events);
  assert.equal(live.status, "ACTIVE");
  const s = mod.productEventSentence(live);
  assert.equal(s.loading, true);
  assert.doesNotMatch(s.text, /infrastructure/i);
});

test("G5: with no active work, the newest infrastructure pause is the live line", () => {
  const events = [
    ev("stage.RETRIEVE", "COMPLETED"),
    ev("stage.SYNTHESIZE", "FAILED_INFRASTRUCTURE"),
  ];
  const live = mod.pickLiveEvent(events);
  assert.equal(live.status, "FAILED_INFRASTRUCTURE");
  const s = mod.productEventSentence(live);
  assert.equal(s.loading, false);
  assert.equal(s.infrastructure, true);
});

test("G5: structured evidence fields render counts; missing fields stay honest", () => {
  const withCount = mod.productEventSentence(ev("evidence.retrieved", "COMPLETED", { source: "core", count: 1 }));
  assert.match(withCount.text, /core/);
  assert.match(withCount.text, /1 record\b/);
  const noFields = mod.productEventSentence(ev("evidence.retrieved", "COMPLETED"));
  assert.doesNotMatch(noFields.text, /undefined|null|NaN/);
});

// ---------------------------------------------------------------------------
// closed vocabulary — unknown inputs fall through to honest generics
// ---------------------------------------------------------------------------

test("unknown kinds and statuses fall through to honest generic sentences", () => {
  const unknownActive = mod.productEventSentence(ev("brand.new.kind", "ACTIVE"));
  assert.match(unknownActive.text, /Still working/i);
  const unknownDone = mod.productEventSentence(ev("brand.new.kind", "COMPLETED"));
  assert.match(unknownDone.text, /step of the investigation is recorded/i);
  const queued = mod.productEventSentence(ev("stage.ATTACK", "QUEUED"));
  assert.equal(queued.text, ""); // render nothing — never a fake action
  const empty = mod.productEventSentence(null);
  assert.equal(empty.text, "");
  const weird = mod.productEventSentence(ev("stage.MYSTERY_STAGE", "ACTIVE"));
  assert.doesNotMatch(weird.text, MACHINE_VOCAB);
  assert.match(weird.text, /Still working/i);
});
