// adversarial_r472.test.mjs — the 2026-09-16 external audit's P0-4
// frontend contract: the no-survivor learning card.
//
// The audit's acceptance: "A terminal no-mechanism card shows searched
// territory, strongest failed hypothesis, key missing evidence, and
// 2-3 ranked next actions" — and section 12: "The ideal refusal
// surface has three lines: what was tested; what failed or remained
// unknown; the smallest next action that could change the result."
//
// The card is BACKEND-DERIVED (toscanini/run_state.py learning_card,
// recorded fields only); the frontend contract here pins that the
// surface renders it exactly where the settled no-survivor verdict is
// stated, and NEVER for any other outcome class.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const webapp = path.resolve(here, "..");
const read = (rel) => readFileSync(path.join(webapp, rel), "utf8");

const narrative = read("components/RunNarrative.tsx");
const types = read("lib/types.ts");

// ---------------------------------------------------------------------------
// P0-4 — the card renders under the settled no-survivor verdict only
// ---------------------------------------------------------------------------

test("R472: the learning card renders only when settledNoSurvivor AND the card exists", () => {
  assert.match(
    narrative,
    /\{settledNoSurvivor && learningCard && \(/,
    "the card must be gated on the settled no-survivor verdict AND the backend card",
  );
});

test("R472: the card carries the data-learning-card marker for E2E pinning", () => {
  assert.match(narrative, /data-learning-card/);
});

test("R472: the four audit-named sections are all present", () => {
  assert.match(narrative, /What was tested:/);
  assert.match(narrative, /Strongest failed hypothesis:/);
  assert.match(narrative, /Key missing evidence:/);
  // the ranked actions render from the card's own ranked_next_actions
  assert.match(narrative, /learningCard\.ranked_next_actions\.map/);
  // the trust line (the derivation basis) is shown, not hidden
  assert.match(narrative, /\{learningCard\.basis\}/);
});

test("R472: the card reads both surfaces (run state object AND user_state_view)", () => {
  assert.match(
    narrative,
    /runState\?\.learning_card \?\? detail\.user_state_view\?\.learning_card/,
  );
});

test("R472: no outcome promise vocabulary in the rendered action copy", () => {
  // the action text comes from the backend, but the rendering must not
  // ADD promise language of its own — the surrounding copy stays
  // factual (the settled banner sentence already says none survived)
  const cardBlock = narrative.slice(
    narrative.indexOf("settledNoSurvivor && learningCard"),
    narrative.indexOf("data-evidence-pack"),
  );
  for (const banned of ["will survive", "will succeed", "guaranteed"]) {
    assert.ok(!cardBlock.includes(banned), `banned phrase: ${banned}`);
  }
});

// ---------------------------------------------------------------------------
// P0-4 — the typed contract (lib/types.ts)
// ---------------------------------------------------------------------------

test("R472: LearningCard type pins the backend contract", () => {
  assert.match(types, /export interface LearningCard \{/);
  assert.match(types, /kind: "no_survivor_learning_card";/);
  for (const field of ["what_was_tested", "strongest_failed_hypothesis",
                       "key_missing_evidence", "ranked_next_actions",
                       "basis"]) {
    assert.match(types, new RegExp(`${field}:`), `field ${field}`);
  }
  // the typed action union — machine-readable kinds, never free prose
  assert.match(
    types,
    /action_kind: "ADD_EVIDENCE" \| "REFINE_PROBLEM" \| "NEW_TERRITORY";/,
  );
});

test("R472: UserStateView and RunStateObject both carry the card", () => {
  assert.match(
    types,
    /learning_card\?: LearningCard \| null;/,
    "both projections carry the optional card",
  );
  // count occurrences: UserStateView + RunStateObject = 2 declarations
  const n = (types.match(/learning_card\?: LearningCard \| null;/g) || []).length;
  assert.ok(n >= 2, `expected the card on both projections, found ${n}`);
});

// ---------------------------------------------------------------------------
// the honesty floor — the settled banner sentence stays (the card
// ADDS the learning surface, it never softens the verdict)
// ---------------------------------------------------------------------------

test("R472: the settled no-survivor verdict sentence is unchanged", () => {
  assert.match(
    narrative,
    /no candidate survived the machine's own challenge gauntlet/,
  );
});

// ---------------------------------------------------------------------------
// the sibling line's R472 pins (the P2 dead-code closure) — the union
// keeps both lines' contracts: the learning card above, the compliance
// attribute mapping below.
// ---------------------------------------------------------------------------

const CONV = read(
  "components/Conversation.tsx");
const CSS = read("app/globals.css");

test("the directive card derives the styled compliance attribute from the typed verdicts", () => {
  // the mapping exists, sourced from the ONE shared instrument's verdicts
  assert.ok(CONV.includes("COMPLIANCE_STATE"), "mapping constant present");
  assert.ok(CONV.includes('COMPLIED_CHANGED: "COMPLIANT"'));
  assert.ok(CONV.includes('MOVED_BUT_IN_TERRITORY: "PARTIAL"'));
  assert.ok(CONV.includes('NOT_COMPLIED_SAME_AS_PARENT: "VIOLATED"'));
  // the card emits the attribute the CSS actually selects
  assert.ok(CONV.includes("data-directive-compliance={"),
    "the styled attribute is emitted");
});

test("every card emitting the raw verdict also emits the derived attribute", () => {
  // the R470 dead-code shape was: data-compliance-verdict without the
  // derived attribute. The single render site must carry BOTH.
  const cardAt = CONV.indexOf("data-directive-outcome-card");
  assert.ok(cardAt >= 0, "the directive outcome card exists");
  const chunk = CONV.slice(cardAt, cardAt + 600);
  assert.ok(chunk.includes("data-compliance-verdict="));
  assert.ok(chunk.includes("data-directive-compliance="));
});

test("the CSS and the component agree on the styled vocabulary", () => {
  for (const state of ["VIOLATED", "PARTIAL", "COMPLIANT"]) {
    assert.ok(CSS.includes(`[data-directive-compliance="${state}"]`),
      `css targets ${state}`);
    assert.ok(CONV.includes(`"${state}"`), `component maps ${state}`);
  }
});

test("untyped verdicts stay neutral — never styled as compliance outcomes", () => {
  for (const neutral of ["NO_BASELINE", "NO_CHILD_MECHANISM",
    "NOT_APPLICABLE", "CONSTRAINT_DERIVATION_FAILED"]) {
    assert.ok(!CONV.includes(`${neutral}: "`),
      `${neutral} must not map to a styled state`);
  }
});
