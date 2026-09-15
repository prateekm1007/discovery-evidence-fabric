// adversarial_r463.test.mjs — R463 steering-router acceptance battery.
//
// The independent audit's P0-1, verbatim: "10 paraphrased steering
// prompts (incl. 'make it cheaper', 'use a different material',
// 'optimize for manufacturability') → ≥9 classified as actions, 0
// silently demoted to ASK." PLUS the settled R458 guarantees must not
// regress: the canonical route table still holds and questions about
// the record stay ASK (a wrong action is worse than a safe question —
// the demotion defect was steering paraphrases falling through, not
// questions being served).
//
// Zero dependencies — runs the REAL module the webapp ships.
import { test } from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import { existsSync, readFileSync } from "node:fs";
import { execSync } from "node:child_process";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const webapp = path.resolve(here, "..");

// compile the shipped TS to a temp JS the test imports (the shipped
// module, not a copy — Art. XVI: the evidence IS the artifact)
const outDir = execSync("mktemp -d").toString().trim();
execSync(
  `npx --yes esbuild@0.25.5 lib/actionContract.ts --bundle ` +
    `--format=cjs --outfile=${outDir}/actionContract.cjs --log-level=error`,
  { cwd: webapp, stdio: "pipe" },
);
const require = createRequire(import.meta.url);
const ac = require(path.join(outDir, "actionContract.cjs"));

// ---------------------------------------------------------------------------
// THE P0-1 ACCEPTANCE BATTERY — 10 paraphrased steering prompts
// ---------------------------------------------------------------------------

const STEERING_BATTERY = [
  // the three named by the audit
  ["Make it cheaper.", "CHANGE_MECHANISM"],
  ["Use a different material.", "CHANGE_MECHANISM"],
  ["Optimize for manufacturability.", "REQUEST_ENGINEERING"],
  // natural paraphrases across the remaining verbs
  ["Can you try a different approach?", "CHANGE_MECHANISM"],
  ["I'm not convinced — look for weaknesses.", "ATTACK"],
  ["Find prior art on this.", "FIND_EVIDENCE"],
  ["How do the candidates stack up against each other?", "COMPARE_MECHANISMS"],
  ["Keep digging.", "RESEARCH"],
  ["Work out how to actually manufacture this.", "REQUEST_ENGINEERING"],
  ["Show me the package.", "REVIEW_PACKAGE"],
];

test("P0-1 battery: 10 paraphrased steering prompts route to actions", () => {
  let actions = 0;
  const demoted = [];
  for (const [text] of STEERING_BATTERY) {
    const r = ac.classifyMessage(text);
    if (r.kind === "action") actions += 1;
    else demoted.push(text);
  }
  assert.equal(demoted.length, 0,
    `silently demoted to ASK: ${JSON.stringify(demoted)}`);
  assert.ok(actions >= 9, `only ${actions}/10 classified as actions`);
});

test("P0-1 battery: every steering prompt carries the user's words", () => {
  for (const [text, verb] of STEERING_BATTERY) {
    const params = ac.buildActionParams(verb, text);
    assert.equal(params.direction, text,
      "the user's words ride the action verbatim");
  }
});

test("P0-1: politeness-prefixed and question-shaped steering still steers", () => {
  for (const text of [
    "Please make it cheaper.",
    "Could you use a different material?",
    "What if we used a different polymer?",
    "Reduce the pressure loss.",
    "Design a benchtop test for this.",
    "Is there evidence against candidate 2?",
    "Any sources on this mechanism?",
    "How would we verify this?",
  ]) {
    const r = ac.classifyMessage(text);
    assert.equal(r.kind, "action", text);
  }
});

// ---------------------------------------------------------------------------
// the settled R458 route table must not regress (Art. XXIV: the settled
// contract outranks the round's narrative)
// ---------------------------------------------------------------------------

test("R458 route table regression: canonical directives unchanged", () => {
  const cases = [
    ["Try another mechanism.", "CHANGE_MECHANISM"],
    ["Look for contradictory evidence.", "FIND_EVIDENCE"],
    ["Use this paper.", "UPLOAD_EVIDENCE"],
    ["Use this manufacturer's PDF.", "UPLOAD_EVIDENCE"],
    ["Challenge candidate 2.", "ATTACK"],
    ["Keep the engineering constraint but change the mechanism.", "CHANGE_MECHANISM"],
    ["Compare the mechanisms.", "COMPARE_MECHANISMS"],
    ["Design the decisive experiment.", "REQUEST_EXPERIMENT"],
    ["Work out the engineering.", "REQUEST_ENGINEERING"],
    ["Review the package.", "REVIEW_PACKAGE"],
    ["What else could cause this?", "CHANGE_MECHANISM"],
  ];
  for (const [text, verb] of cases) {
    const r = ac.classifyMessage(text);
    assert.equal(r.kind, "action", text);
    assert.equal(r.verb, verb, text);
  }
});

test("R458 route table regression: read-only questions stay ASK", () => {
  for (const text of [
    "Why was candidate 2 rejected?",
    "What experiment would kill this?",
    "What does Toscanini believe here?",
    "What remains unknown?",
    "Which attachment did the engine use?",
    "Is the run still going?",
  ]) {
    const r = ac.classifyMessage(text);
    assert.equal(r.kind, "ask", text);
  }
});

test("ASK is still the default for non-steering chatter", () => {
  for (const text of [
    "ok",
    "thanks",
    "Tell me about the evidence.",
    "Summarize the run.",
  ]) {
    const r = ac.classifyMessage(text);
    assert.equal(r.kind, "ask", text);
  }
});

// ---------------------------------------------------------------------------
// the shipped export must be the tested one (no drift between the webapp
// bundle and this suite)
// ---------------------------------------------------------------------------

test("the tested contract source is the shipped actionContract.ts", () => {
  const src = readFileSync(
    path.join(webapp, "lib", "actionContract.ts"), "utf8");
  assert.ok(src.includes("export function classifyMessage"));
  // the P0-1 steering lexicon is present in the shipped file
  assert.ok(src.includes("make it cheaper"));
  assert.ok(src.includes("different material"));
});
