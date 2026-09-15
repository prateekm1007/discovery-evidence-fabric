// adversarial_r470.test.mjs — R470 acceptance battery (UI layer).
//
// The external re-audit's (7.0/10, 2026-09-15) remaining UI items,
// closed with executable evidence:
//
//   1. Kill causes in plain language, stated ONCE (P1-3): the eight
//      canonical adversarial dimensions become one plain-language
//      enumeration on the FAILED attack card; the machine taxonomy
//      never repeats on the surface (the record layer dedupes too —
//      tests/test_r470_audit_closes.py).
//   2. Mid-run feedback density (P1-1): the waiting user can state
//      the current phase (the live sentence), the LAST COMPLETED step,
//      and the EVIDENCE COUNT — all derived from the run's own
//      recorded events (progressContext), never asserted.
//
// The present.ts / productEvents.ts derivation runs the SHIPPED module
// (esbuild-compiled, not copies — Art. XVI). Zero dependencies.

import { test } from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import { execSync } from "node:child_process";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const webapp = path.resolve(here, "..");

const outDir = execSync("mktemp -d").toString().trim();
for (const mod of ["present", "productEvents"]) {
  execSync(
    `npx --yes esbuild@0.25.5 lib/${mod}.ts --bundle ` +
      `--format=cjs --outfile=${outDir}/${mod}.cjs --log-level=error`,
    { cwd: webapp, stdio: "pipe" },
  );
}
const require = createRequire(import.meta.url);
const present = require(path.join(outDir, "present.cjs"));
const events = require(path.join(outDir, "productEvents.cjs"));

// ---------------------------------------------------------------------------
// helpers — the canonical detail fixture shape (same as the r467 battery)
// ---------------------------------------------------------------------------

function detailWithRunState(status, runState, extra = {}) {
  return {
    session_id: "s1",
    status,
    problem: "test problem",
    created_at: "2026-09-16T00:00:00Z",
    run_state: runState,
    events: [],
    ...extra,
  };
}

const TAXONOMY_KILL_REASON =
  "adversarial challenge failed: unsupported_mechanism: KILLED, " +
  "weak_transfer: KILLED, contradiction: KILLED, " +
  "regulatory_incompatibility: KILLED";

// ---------------------------------------------------------------------------
// 1. P1-3 — kill causes in plain language, stated once
// ---------------------------------------------------------------------------

test("kill cause taxonomy becomes ONE plain-language enumeration", () => {
  const detail = detailWithRunState("COMPLETE", {
    outcome: "INVENTION_KILLED_BY_CHALLENGE",
    generations: { generations: [{
      gen: 1,
      architecture: { mechanism: "m", intervention: "i" },
      challenge: { killed: true, kill_reason: TAXONOMY_KILL_REASON },
    }] },
  });
  const s = present.attackSentence("FAILED", detail);
  assert.ok(s.includes("rejected it on 4 fronts"));
  // the machine taxonomy never repeats on the surface
  assert.ok(!s.includes("killed dimensions"));
  assert.ok(!s.includes("unsupported_mechanism"));
  assert.ok(!s.includes("KILLED"));
  // each cause stated once, in plain language
  assert.ok(s.includes("the recorded evidence did not support the mechanism"));
  assert.ok(s.includes("it would face regulatory barriers"));
  // no duplication of the plain clauses either
  assert.ok(s.split("the recorded evidence did not support the mechanism").length - 1 === 1);
});

test("non-taxonomy kill reason still renders the recorded cause verbatim", () => {
  const detail = detailWithRunState("COMPLETE", {
    outcome: "INVENTION_KILLED_BY_CHALLENGE",
    generations: { generations: [{
      gen: 1,
      architecture: { mechanism: "m", intervention: "i" },
      challenge: { killed: true, kill_reason: "failure mode not documented" },
    }] },
  });
  const s = present.attackSentence("FAILED", detail);
  assert.ok(s.includes("Recorded cause: failure mode not documented"));
});

test("killCauseSentence with no recognizable cause returns empty", () => {
  assert.equal(present.killCauseSentence(null), "");
  assert.equal(present.killCauseSentence(undefined), "");
  assert.equal(present.killCauseSentence("unrelated wording"), "");
});

// ---------------------------------------------------------------------------
// 2. P1-1 — the progress context line (phase / last step / evidence)
// ---------------------------------------------------------------------------

test("progressContext prefers the run-state's canonical record count", () => {
  const evs = [
    { kind: "stage.RETRIEVE", status: "COMPLETED" },
    { kind: "evidence.retrieved", status: "COMPLETED", source: "arxiv", count: 5 },
    { kind: "evidence.retrieved", status: "COMPLETED", source: "core", count: 11 },
    { kind: "stage.FREEZE", status: "COMPLETED" },
    { kind: "stage.SYNTHESIZE", status: "ACTIVE" },
  ];
  const ctx = events.progressContext(evs, 16);
  assert.equal(ctx.evidenceCount, 16);
  assert.equal(ctx.lastCompleted,
    "The evidence base is frozen — every record carries its content hash.");
});

test("progressContext falls back to the recorded per-source sum", () => {
  const evs = [
    { kind: "evidence.retrieved", status: "COMPLETED", source: "arxiv", count: 5 },
    { kind: "evidence.retrieved", status: "COMPLETED", source: "core", count: 11 },
    { kind: "stage.RETRIEVE", status: "COMPLETED" },
  ];
  const ctx = events.progressContext(evs, null);
  assert.equal(ctx.evidenceCount, 16);
  assert.equal(ctx.lastCompleted, "The evidence search for this problem is in.");
});

test("progressContext with nothing recorded states nothing", () => {
  const ctx = events.progressContext([], null);
  assert.equal(ctx.evidenceCount, null);
  assert.equal(ctx.lastCompleted, "");
});

test("progressContext never invents a count from a zero-only record", () => {
  const ctx = events.progressContext(
    [{ kind: "evidence.retrieved", status: "COMPLETED", count: 0 }], null);
  assert.equal(ctx.evidenceCount, null);
});
