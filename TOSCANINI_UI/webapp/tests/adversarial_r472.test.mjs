// R472 — adversarial pins for the third-pass audit fixes that live in
// the webapp layer (node --test, the house src-pin style used by
// adversarial_r467/r470).
//
// The auditor's P2 dead-code finding: the R470 component emitted
// data-compliance-verdict (typed vocabulary) while the CSS targeted
// data-directive-compliance (VIOLATED/PARTIAL/COMPLIANT) — the styling
// could never fire. The R472 component derives the styled attribute
// from the typed verdicts via COMPLIANCE_STATE. These pins make the
// pairing non-optional: any render site that re-introduces the raw
// verdict without the derived attribute fails here.

import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { test } from "node:test";
import assert from "node:assert/strict";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const TSX = readFileSync(
  join(ROOT, "components", "Conversation.tsx"), "utf8");
const CSS = readFileSync(join(ROOT, "app", "globals.css"), "utf8");

test("the directive card derives the styled compliance attribute from the typed verdicts", () => {
  // the mapping exists, sourced from the ONE shared instrument's verdicts
  assert.ok(TSX.includes("COMPLIANCE_STATE"), "mapping constant present");
  assert.ok(TSX.includes('COMPLIED_CHANGED: "COMPLIANT"'));
  assert.ok(TSX.includes('MOVED_BUT_IN_TERRITORY: "PARTIAL"'));
  assert.ok(TSX.includes('NOT_COMPLIED_SAME_AS_PARENT: "VIOLATED"'));
  // the card emits the attribute the CSS actually selects
  assert.ok(TSX.includes("data-directive-compliance={"),
    "the styled attribute is emitted");
});

test("every card emitting the raw verdict also emits the derived attribute", () => {
  // the R470 dead-code shape was: data-compliance-verdict without the
  // derived attribute. The single render site must carry BOTH.
  const cardAt = TSX.indexOf("data-directive-outcome-card");
  assert.ok(cardAt >= 0, "the directive outcome card exists");
  const chunk = TSX.slice(cardAt, cardAt + 600);
  assert.ok(chunk.includes("data-compliance-verdict="));
  assert.ok(chunk.includes("data-directive-compliance="));
});

test("the CSS and the component agree on the styled vocabulary", () => {
  for (const state of ["VIOLATED", "PARTIAL", "COMPLIANT"]) {
    assert.ok(CSS.includes(`[data-directive-compliance="${state}"]`),
      `css targets ${state}`);
    assert.ok(TSX.includes(`"${state}"`), `component maps ${state}`);
  }
});

test("untyped verdicts stay neutral — never styled as compliance outcomes", () => {
  for (const neutral of ["NO_BASELINE", "NO_CHILD_MECHANISM",
    "NOT_APPLICABLE", "CONSTRAINT_DERIVATION_FAILED"]) {
    assert.ok(!TSX.includes(`${neutral}: "`),
      `${neutral} must not map to a styled state`);
  }
});
