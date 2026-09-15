// adversarial_r471.test.mjs — the 2026-09-16 external product audit's
// frontend contract closures.
//
// The audit measured, on the live product:
//   P0-2  "retryRun() treats non-2xx as an exception, so the advertised
//          Resume path is not contract-safe" — the Resume action was a
//          silent no-op on every refusal. The retry call is now
//          outcome-typed: a refusal is a RESULT the UI states, never a
//          thrown error.
//   P0-6  "No URL field or URL payload in the audited composer" — the
//          composer now carries a reference-URL input whose ingestion
//          rides the same typed attachment record as a file.
//   P2-3  the home textarea relied on placeholder text with no
//          accessible name; the hidden file input had none either.
//
// The api.ts tests run the SHIPPED module (esbuild-compiled), not
// copies (Art. XVI). Zero dependencies — plain Node.

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
  `npx --yes esbuild@0.25.5 lib/api.ts --bundle ` +
    `--format=cjs --outfile=${outDir}/api.cjs --log-level=error`,
  { cwd: webapp, stdio: "pipe" },
);
const require = createRequire(import.meta.url);
const api = require(path.join(outDir, "api.cjs"));

const read = (rel) => readFileSync(path.join(webapp, rel), "utf8");

// ---------------------------------------------------------------------------
// P0-2 — retryRun is outcome-typed: refusal is a RESULT, not an exception
// ---------------------------------------------------------------------------

test("R471: a 409 refusal is returned as a typed outcome, never thrown", async () => {
  globalThis.fetch = async () => new Response(
    JSON.stringify({
      refusal: "RETRY_NOT_PERMITTED",
      error: "session status 'COMPLETE' is not retryable",
      session_id: "ts_x",
      session_status: "COMPLETE",
      retryable: false,
    }),
    { status: 409, headers: { "Content-Type": "application/json" } },
  );
  const outcome = await api.retryRun("ts_x");
  assert.equal(outcome.ok, false);
  assert.equal(outcome.httpStatus, 409);
  assert.equal(outcome.refusal, "RETRY_NOT_PERMITTED");
  assert.equal(outcome.sessionStatus, "COMPLETE");
  assert.match(outcome.error, /not retryable/);
});

test("R471: an accepted retry (202) surfaces the typed retry_id", async () => {
  globalThis.fetch = async () => new Response(
    JSON.stringify({
      retry_id: "rt_abc123def456",
      session_id: "ts_x",
      status: "PENDING",
      retry_attempts: 2,
      session: { session_id: "ts_x" },
    }),
    { status: 202, headers: { "Content-Type": "application/json" } },
  );
  const outcome = await api.retryRun("ts_x");
  assert.equal(outcome.ok, true);
  assert.equal(outcome.httpStatus, 202);
  assert.equal(outcome.retryId, "rt_abc123def456");
  assert.equal(outcome.sessionStatus, "PENDING");
});

test("R471: a non-json error body still returns the status contract", async () => {
  globalThis.fetch = async () => new Response("gateway timeout", { status: 504 });
  const outcome = await api.retryRun("ts_x");
  assert.equal(outcome.ok, false);
  assert.equal(outcome.httpStatus, 504);
  assert.equal(outcome.refusal, undefined);
});

// ---------------------------------------------------------------------------
// P0-6 — the URL/reference leg of the composer
// ---------------------------------------------------------------------------

test("R471: attachUrl returns the typed ingestion record", async () => {
  globalThis.fetch = async () => new Response(
    JSON.stringify({
      attachments: [{
        attachment_id: "att_123",
        name: "example.com/paper",
        source_url: "https://example.com/paper",
        sha256: "deadbeef",
        ingestion: { status: "TEXT_EXTRACTED", text_chars_total: 1200 },
        rejected: false,
      }],
      rejected: [],
      bound_run: null,
    }),
    { status: 201, headers: { "Content-Type": "application/json" } },
  );
  const rec = await api.attachUrl("https://example.com/paper");
  assert.equal(rec.ingestion.status, "TEXT_EXTRACTED");
  assert.equal(rec.attachment_id, "att_123");
  assert.equal(rec.rejected, false);
});

test("R471: attachUrl carries the typed refusal of a blocked URL", async () => {
  globalThis.fetch = async () => new Response(
    JSON.stringify({
      attachments: [{
        attachment_id: "att_456",
        name: "file:///etc/passwd",
        ingestion: { status: "REJECTED_BLOCKED_URL",
                     note: "scheme 'file' is not allowed" },
        rejected: true,
      }],
      rejected: ["att_456"],
    }),
    { status: 201, headers: { "Content-Type": "application/json" } },
  );
  const rec = await api.attachUrl("file:///etc/passwd");
  assert.equal(rec.rejected, true);
  assert.equal(rec.ingestion.status, "REJECTED_BLOCKED_URL");
  assert.match(rec.ingestion.note, /not allowed/);
});

// ---------------------------------------------------------------------------
// P0-2/P0-6/P2-3 — the shipped source carries the closed contracts
// ---------------------------------------------------------------------------

test("R471: the composer renders the reference-URL input with an accessible name", () => {
  const page = read("app/page.tsx");
  assert.match(page, /className="ask-urlrow"/);
  assert.match(page, /aria-label="Reference URL"/);
  // the URL leg rides the SAME pending queue as files (one canonical chip)
  assert.match(page, /async function addUrl\(\)/);
});

test("R471: the home inputs carry accessible names (P2-3)", () => {
  const page = read("app/page.tsx");
  assert.match(
    page,
    /aria-label="Describe the problem you want to solve or invent"/,
  );
  assert.match(page, /aria-label="Attach documents"/);
});

test("R471: the Resume action states the refusal instead of swallowing it", () => {
  const page = read("app/page.tsx");
  // the retry branch inspects the outcome; a refusal renders a note
  assert.match(page, /outcome\.refusal === "RETRY_NOT_PERMITTED"/);
  assert.match(page, /data-retry-note/);
  // the old contract violation is gone: no bare then(() => reload)
  assert.doesNotMatch(
    page,
    /retryRun\([^\n]*\)\s*\.then\(\(\)\s*=>\s*location\.reload\(\)\)/,
  );
});

// ---------------------------------------------------------------------------
// PARALLEL-LINE UNION additions (this line's unique closures):
// P1-2 the queued directive, P2-1 the measured duration line, P2-5 the
// model-state explainer, and the reason-vocabulary refusal copy.
// ---------------------------------------------------------------------------

// present.ts compiles for the next-action derivation
import { execSync as _execSync } from "node:child_process";
_execSync(
  `npx --yes esbuild@0.25.5 lib/present.ts --bundle ` +
    `--format=cjs --outfile=${outDir}/present.cjs --log-level=error`,
  { cwd: webapp, stdio: "pipe" },
);
const present = require(path.join(outDir, "present.cjs"));

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

function terminalDetail(extra = {}) {
  return detailWithRunState("COMPLETE", {
    outcome: "INVENTION_KILLED_BY_CHALLENGE",
    generations: { generations: [] },
    failed_stages: {},
  }, extra);
}

test("R471: a queued directive becomes the first next action on terminal", () => {
  const detail = terminalDetail({
    queued_directive: {
      verb: "RESEARCH",
      params: { direction: "make it cheaper" },
      directive: "research make it cheaper",
      queued_at: "2026-09-16T01:00:00Z",
    },
  });
  const next = present.deriveNextAction(detail, null, true);
  assert.equal(next.kind, "run_queued");
  assert.match(next.label, /make it cheaper/);
});

test("R471: the queued action outranks the package download", () => {
  const detail = terminalDetail({
    queued_directive: { directive: "use recycled materials" },
  });
  const next = present.deriveNextAction(detail, null, true);
  assert.equal(next.kind, "run_queued");
});

test("R471: a long queued directive is truncated, not sprawling", () => {
  const detail = terminalDetail({
    queued_directive: { directive: "x".repeat(140) },
  });
  const next = present.deriveNextAction(detail, null, false);
  assert.equal(next.kind, "run_queued");
  assert.ok(next.label.length < 100);
});

test("R471: no queued directive -> the canonical terminal actions stand", () => {
  const detail = terminalDetail();
  const next = present.deriveNextAction(detail, null, true);
  assert.equal(next.kind, "package");
});

test("R471: the retry refusal surfaces the reason vocabulary", () => {
  const page = read("app/page.tsx");
  assert.match(page, /COMPLETE_APPEND_ONLY/);
  assert.match(page, /WORKER_ALIVE/);
  assert.match(page, /AWAITING_ANSWER/);
  // and the page refreshes state after a refusal (never a dead end)
  assert.match(page, /getRunResult\(detail\.session_id\)/);
});

test("R471: the design tab carries the model-state explainer (P2-5)", () => {
  const src = read("components/DossierSections.tsx");
  assert.ok(src.includes("data-model-state-explainer"));
  assert.match(src, /What the model states mean/);
  assert.match(src, /conceptual/i);
  assert.match(src, /Engineering geometry/);
  assert.match(src, /Computational/);
  assert.match(src, /Physical/);
});

test("R471: the hero note renders the measured p50/p90 when present (P2-1)", () => {
  const src = read("app/page.tsx");
  assert.match(src, /p50_minutes/);
  assert.match(src, /p90_minutes/);
  assert.match(src, /measured from/);
});
