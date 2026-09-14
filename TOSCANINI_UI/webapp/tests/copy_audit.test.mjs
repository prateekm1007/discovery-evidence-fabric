// R459 (audit P1-1) — THE COMPLEXITY-HIDING COPY AUDIT.
//
// "Every technical concept must earn its place on the screen." Internal
// protocol names, round numbers, constitutional article citations, and
// governance codes NEVER appear in user-visible strings. The audit trail
// lives in the technical record and the repository — not in the chat.
//
// This is a STATIC scan of the user-surface source: it walks every
// string literal in the components/lib sources and fails when a
// forbidden token appears outside a comment (comments are stripped
// line-wise; block comments are handled by the simple state machine
// below). Zero dependencies; runs in plain Node (Art. XVI).

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync, statSync } from "node:fs";
import path from "node:path";

const ROOT = path.join(path.dirname(new URL(import.meta.url).pathname), "..");
// the PRIMARY SURFACE (the conversation chain) — the audit's P1-1
// acceptance targets the chat + navigation; the journal/technical
// record legitimately keeps precise technical vocabulary (§9/§15)
const FILES = [
  "components/Conversation.tsx",
  "components/AskBox.tsx",
  "components/Sidebar.tsx",
  "app/page.tsx",
  "lib/actionContract.ts",
  "lib/productEvents.ts",
  "lib/present.ts",
];
const EXTS = [".tsx", ".ts"];

// tokens that must never reach a user's eyes. Two classes:
//  ALWAYS — forbidden anywhere on a line (comments already stripped):
//    internal round numbers, constitutional citations, register ids,
//    the word "contract" in user copy.
//  IN_STRINGS — raw enum/provider tokens forbidden when they appear
//    INSIDE a quoted string (record KEYS are code; the rendered VALUE
//    is what the user sees).
const ALWAYS = [
  /\bR4\d\d\b/,
  /\bArt\.\s?[IVXLCD]+/,
  /\bBS-\d+/,
  /\bcontract\b/i,
  /\bAI_INTERPRETATION\b/,
];
const IN_STRINGS = [
  /["'`](?:[^"'`]*)(MODEL_DERIVED|ENGINEERING_DEFINED|UNOROUTER|XKIRO|APINEX|QWEN|GLM)/i,
];

function stripComments(src) {
  // state machine: remove // line comments and /* */ blocks, keep
  // string contents (the tokens are forbidden INSIDE strings)
  let out = "";
  let i = 0;
  let mode = "code"; // code | line | block | squote | dquote | tick
  while (i < src.length) {
    const c = src[i];
    const next = src[i + 1];
    if (mode === "code") {
      if (c === "/" && next === "/") { mode = "line"; i += 2; continue; }
      if (c === "/" && next === "*") { mode = "block"; i += 2; continue; }
      if (c === "'") { mode = "squote"; out += c; i++; continue; }
      if (c === '"') { mode = "dquote"; out += c; i++; continue; }
      if (c === "`") { mode = "tick"; out += c; i++; continue; }
      out += c; i++; continue;
    }
    if (mode === "line") { if (c === "\n") { mode = "code"; out += c; } i++; continue; }
    if (mode === "block") { if (c === "*" && next === "/") { mode = "code"; i += 2; } else i++; continue; }
    if (mode === "squote") {
      if (c === "\\") { out += src.slice(i, i + 2); i += 2; continue; }
      if (c === "'") mode = "code";
      out += c; i++; continue;
    }
    if (mode === "dquote") {
      if (c === "\\") { out += src.slice(i, i + 2); i += 2; continue; }
      if (c === '"') mode = "code";
      out += c; i++; continue;
    }
    if (mode === "tick") {
      if (c === "\\") { out += src.slice(i, i + 2); i += 2; continue; }
      if (c === "`") mode = "code";
      out += c; i++; continue;
    }
  }
  return out;
}

test("P1-1: no internal protocol names in primary-surface strings", () => {
  const violations = [];
  for (const rel of FILES) {
    const file = path.join(ROOT, rel);
    const src = stripComments(readFileSync(file, "utf8"));
    const lines = src.split("\n");
    lines.forEach((line, idx) => {
      for (const re of ALWAYS) {
        if (re.test(line)) {
          violations.push(`${rel}:${idx + 1} ${re} -> ` + line.trim().slice(0, 90));
        }
      }
      const quoted = line.match(/"([^"]*)"|'([^']*)'|`([^`]*)`/g) ?? [];
      for (const re of IN_STRINGS) {
        for (const q of quoted) {
          if (re.test(q)) {
            violations.push(`${rel}:${idx + 1} ${re} -> ` + line.trim().slice(0, 90));
          }
        }
      }
    });
  }
  // the audit's acceptance: ZERO violations in the primary surface
  assert.equal(violations.length, 0, violations.join("\n"));
});
