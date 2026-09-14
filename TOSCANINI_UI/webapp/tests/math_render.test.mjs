// The math-text splitter battery — the deterministic contract behind
// the summary-surface equation renderer. Zero dependencies; runs in
// plain Node against the compiled lib/math.ts (same pattern as the
// other adversarial suites).
//
// The honest-rendering rules under test:
//   - delimited math is recognized ($…$, $$…$$, \(…\), \[…\]);
//   - money and stray $ NEVER become math;
//   - unbalanced or ambiguous input stays plain text;
//   - splitting is lossless (concatenating all bodies == the input).

import { test } from "node:test";
import assert from "node:assert/strict";
import { execSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const BUILD = path.join(HERE, ".build-math");

execSync(
  `npx tsc lib/math.ts --outDir ${JSON.stringify(BUILD)} ` +
    "--module commonjs --target es2022 --moduleResolution node " +
    "--skipLibCheck --strict",
  { cwd: path.join(HERE, ".."), stdio: "inherit" }
);

const { splitMathSegments, hasMath } = await import(
  `file://${path.join(BUILD, "math.js")}`
);

const kinds = (segs) => segs.map((s) => (s.kind === "math" ? "M" : "T"));
const bodies = (segs) => segs.map((s) => s.body).join("");

test("plain prose stays one text segment (no math, no cost)", () => {
  const segs = splitMathSegments("Pressure loss drops with the fourth power of radius.");
  assert.equal(segs.length, 1);
  assert.equal(segs[0].kind, "text");
  assert.equal(hasMath("plain text"), false);
});

test("inline $…$ becomes math", () => {
  const segs = splitMathSegments("flow $Q = \\pi r^4 \\Delta P / (8\\mu L)$ per Darcy");
  assert.deepEqual(kinds(segs), ["T", "M", "T"]);
  assert.equal(segs[1].display, false);
  assert.equal(segs[1].body, "Q = \\pi r^4 \\Delta P / (8\\mu L)");
  assert.equal(hasMath("flow $Q = \\pi r^4$ ok"), true);
});

test("display $$…$$ becomes display math", () => {
  const segs = splitMathSegments("see $$x = y^2$$ done");
  assert.deepEqual(kinds(segs), ["T", "M", "T"]);
  assert.equal(segs[1].display, true);
});

test("\\(…\\) and \\[…\\] forms are recognized", () => {
  assert.equal(hasMath("a \\(b\\) c"), true);
  const segs = splitMathSegments("a \\[b^2\\] c");
  assert.deepEqual(kinds(segs), ["T", "M", "T"]);
  assert.equal(segs[1].display, true);
});

test("money is never math: '$5 and $6'", () => {
  const segs = splitMathSegments("it costs $5 and $6 total");
  assert.equal(hasMath("it costs $5 and $6 total"), false);
  assert.deepEqual(kinds(segs), ["T"]);
  assert.equal(bodies(segs), "it costs $5 and $6 total");
});

test("loose $ spacing is money, not math ('$ x $')", () => {
  assert.equal(hasMath("the $ x $ sign"), false);
});

test("unbalanced $ stays plain text (nothing swallowed)", () => {
  const segs = splitMathSegments("salary $100 per unit of $x");
  assert.equal(bodies(segs), "salary $100 per unit of $x");
});

test("unbalanced \\( stays plain text", () => {
  const src = "an open \\( paren never renders";
  const segs = splitMathSegments(src);
  assert.equal(hasMath(src), false);
  assert.equal(bodies(segs), src);
});

test("splitting is lossless for every fixture (delimiters consumed)", () => {
  // fixtures where every $ that opens is also a delimiter (money is
  // exercised separately above — a money $ is TEXT and must survive)
  const fixtures = [
    "plain",
    "$a$ + $b$",
    "$$d$$ mid \\(i\\) end \\[D\\]",
    "",
  ];
  const stripDelims = (s) =>
    s.replace(/\$\$|\\\[|\\\]|\\\(|\\\)|\$/g, "");
  for (const f of fixtures) {
    const segs = splitMathSegments(f);
    assert.equal(
      bodies(segs),
      stripDelims(f),
      `lossless (modulo delimiters): ${JSON.stringify(f)}`
    );
  }
});

test("a money $ inside prose survives verbatim next to real math", () => {
  const segs = splitMathSegments("costs $5, then $x$ math");
  assert.equal(bodies(segs), "costs $5, then x math");
});

test("empty math body renders as text (no zero-width artifacts)", () => {
  const segs = splitMathSegments("a $$ b");
  assert.equal(hasMath("a $$ b"), false);
});

test("adjacent math segments without prose between", () => {
  const segs = splitMathSegments("$a$$b$");
  assert.deepEqual(kinds(segs), ["M", "M"]);
  assert.deepEqual(segs.map((s) => s.body), ["a", "b"]);
});
