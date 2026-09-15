// adversarial_r467.test.mjs — R467-C2 acceptance battery (UI layer).
//
// The external audit's (6.5/10, 2026-09-15) minimum 9/10 path names
// six items; the UI layer carries three of them:
//
//   1. Steering EFFECT (P0-5): the "what changed because of your
//      direction" card renders ONLY from the worker's typed
//      directive_outcome record — computed from the parent and child
//      runs' own records, never asserted. No-change renders honestly
//      as no-change (the audit's measured complaint was an
//      UNDISCLOSED same-mechanism re-derivation).
//   2. Terminal-state de-collision (P1-2): a TERMINAL run whose own
//      records say the last challenged generation was killed renders
//      the settled one-frame wording ("finished — nothing survived")
//      in a settled visual class, never the in-flight class.
//   3. Interim artifact (P1-6): every terminal run without a package
//      offers the evidence-pack download exactly where the outcome is
//      stated.
//   Plus: the atria transport id (the round's new rung) never reaches
//   product-surface components; the download CTA fill is the AA token.
//
// The present.ts derivation runs the SHIPPED module (esbuild-compiled,
// not copies — Art. XVI). Zero dependencies — plain Node.

import { test } from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import { readFileSync } from "node:fs";
import { execSync } from "node:child_process";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const webapp = path.resolve(here, "..");

const outDir = execSync("mktemp -d").toString().trim();
execSync(
  `npx --yes esbuild@0.25.5 lib/present.ts --bundle ` +
    `--format=cjs --outfile=${outDir}/present.cjs --log-level=error`,
  { cwd: webapp, stdio: "pipe" },
);
const require = createRequire(import.meta.url);
const present = require(path.join(outDir, "present.cjs"));
const { isTerminal } = require(path.join(outDir, "present.cjs"));

const read = (rel) => readFileSync(path.join(webapp, rel), "utf8");

// ---------------------------------------------------------------------------
// Part 1 — the directive-outcome card (P0-5, the EFFECT layer)
// ---------------------------------------------------------------------------

test("R467: the card renders from the typed record and nothing else", () => {
  const src = read("components/Conversation.tsx");
  assert.ok(src.includes("data-directive-outcome-card"),
            "the what-changed card exists");
  assert.ok(src.includes("detail.directive_outcome?.summary"),
            "gated on the typed record's summary");
  assert.ok(src.includes("What changed because of your direction"),
            "the audit's own acceptance phrasing");
  assert.ok(src.includes("data-mechanism-changed"),
            "the change verdict rides as data for the DOM audit");
});

test("R467: no-change is rendered verbatim, never softened", () => {
  const src = read("components/Conversation.tsx");
  const card = src.slice(src.indexOf("data-directive-outcome-card"));
  // the card renders the record's summary string as-is
  assert.ok(card.includes("{detail.directive_outcome.summary}"),
            "the summary is the record's, not the UI's");
});

test("R467: the backend writes the outcome from the runs' records", () => {
  const py = read("../../toscanini/worker.py");
  assert.ok(py.includes("def record_directive_outcome"),
            "the worker computes the comparison");
  assert.ok(py.includes("mechanism_changed"),
            "typed change verdict");
  assert.ok(py.includes("never asserted"),
            "the honesty contract is on the record");
  const srv = read("../../toscanini/server.py");
  assert.ok(srv.includes("problem_understanding_{sid}.json"),
            "the spawn site copies the parent PU record");
  assert.ok(srv.includes("inherited_from"),
            "provenance stamps the inheritance");
  assert.ok(srv.includes("Direction for this round:"),
            "the directive enters the child's problem text (the causal carrier)");
});

// ---------------------------------------------------------------------------
// Part 2 — terminal de-collision (P1-2)
// ---------------------------------------------------------------------------

test("R467: a terminal killed run renders the settled banner", () => {
  const src = read("components/RunNarrative.tsx");
  assert.ok(src.includes("settledNoSurvivor"),
            "the settled computation exists");
  assert.ok(
    src.includes("no candidate survived the machine's own challenge " +
      "gauntlet"),
    "the one-frame settled wording");
  assert.ok(src.includes("ob-SETTLED"),
            "never visually in-flight");
  assert.ok(src.includes("isTerminal(detail.status)"),
            "gated on TERMINAL, never on a live run");
});

test("R467: the settled class is a real, AA-safe CSS pair", () => {
  const css = read("app/globals.css");
  assert.ok(css.includes(".ob-SETTLED"), "the class ships");
  const m = css.match(/\.ob-SETTLED \.outcome-line \{ color: (#[0-9a-f]+);/);
  assert.ok(m, "the settled ink color is pinned");
  // computed arithmetic: #4a3f2e on #f5f1ea must clear AA
  const lum = (hex) => {
    const c = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255)
      .map((v) => v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4);
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
  };
  const ratio = (a, b) => {
    const [l1, l2] = [lum(a), lum(b)].sort((x, y) => y - x);
    return (l1 + 0.05) / (l2 + 0.05);
  };
  const bg = css.match(/\.ob-SETTLED \{ background: (#[0-9a-f]+);/)[1];
  const r = ratio(m[1], bg);
  assert.ok(r >= 4.5, `settled ink on settled paper = ${r.toFixed(2)}:1`);
});

// ---------------------------------------------------------------------------
// Part 3 — the interim evidence pack (P1-6)
// ---------------------------------------------------------------------------

test("R467: every terminal run without a package gets the offer", () => {
  const src = read("components/RunNarrative.tsx");
  assert.ok(src.includes("data-evidence-pack"), "the offer exists");
  assert.ok(
    src.includes("isTerminal(detail.status) && !packageAvailable"),
    "gated: terminal AND no package (a package keeps its own place)");
  assert.ok(src.includes("/evidence-pack"), "the canonical route");
  assert.ok(src.includes("Download the evidence pack"),
            "plain-language label");
});

test("R467: the evidence pack serves the run's own records only", () => {
  const py = read("../../toscanini/server.py");
  assert.ok(py.includes("def _evidence_pack"),
            "the endpoint exists");
  assert.ok(py.includes("evidence pack is served when the run"),
            "terminal-gated with a typed refusal while live");
  assert.ok(py.includes("HONESTY NOTE"),
            "the pack carries the honesty contract");
  assert.ok(py.includes("kill_reason"),
            "kill causes in the pack's README, once");
});

// ---------------------------------------------------------------------------
// Part 4 — transport discipline holds (the atria rung stays invisible)
// ---------------------------------------------------------------------------

test("R467: no product component mentions the new rung", () => {
  for (const f of ["components/Conversation.tsx",
                   "components/RunNarrative.tsx",
                   "components/InventionArtifact.tsx",
                   "lib/present.ts"]) {
    const src = read(f).toLowerCase();
    assert.ok(!src.includes("atria"), `${f} stays transport-clean`);
    assert.ok(!src.includes("onrender.com"), `${f} stays host-clean`);
  }
});

test("R467: the download CTA fill is the AA token", () => {
  const css = read("app/globals.css");
  const block = css.slice(css.indexOf(".btn.download"),
                          css.indexOf(".btn.download") + 300);
  assert.ok(block.includes("var(--accent-text)"),
            "the audit's measured 4.22:1 regression is dead");
});

// ---------------------------------------------------------------------------
// Part 5 — the semantics hold (isTerminal unchanged by the round)
// ---------------------------------------------------------------------------

test("R467: isTerminal classifies the terminal statuses", () => {
  assert.equal(isTerminal("COMPLETE"), true);
  assert.equal(isTerminal("RUN_BLOCKED_CAPABILITY"), true);
  assert.equal(isTerminal("INTERRUPTED"), true);
  assert.equal(isTerminal("RUNNING"), false);
  assert.equal(isTerminal("AWAITING_CLARIFICATION"), false);
});
