// R510 dry-run cliff — ADVERSARIAL UI TESTS for the canonical
// portfolio projection (lib/present.ts deriveCandidates).
//
// The contract under test: when the backend serves run_state.portfolio,
// React renders rank, candidate_id, distinctness and ranking basis
// VERBATIM in canonical order. React derives nothing: no client-side
// sort, no client-side scoring, no order inference. Absent portfolio
// keeps the legacy generations path byte-identical.
//
// Run: npm run test:r510portfolio (compiles the presentation core ->
// tests/.build-r510 then node --test)

import { test } from "node:test";
import assert from "node:assert/strict";
import { existsSync } from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const build = path.join(here, ".build-r510");

if (!existsSync(path.join(build, "present.js"))) {
  throw new Error(
    "presentation layer not compiled — run npm run test:r510portfolio");
}
const mod = await import(
  pathToFileURL(path.join(build, "present.js")).href);

function baseDetail(overrides = {}) {
  return {
    session_id: "ts_test",
    title: "t",
    user_text: "t",
    status: "RUNNING",
    created_at: "2026-09-19T00:00:00Z",
    run_dir: null,
    run_state: null,
    ...overrides,
  };
}

// canonical portfolio deliberately OUT OF RANK ORDER on the wire:
// React must preserve wire order (canonical order), never sort.
function portfolioDetail() {
  return baseDetail({
    run_state: {
      run_id: "r1",
      status: "COMPLETE",
      portfolio: {
        candidates: [
          {
            candidate_id: "cand:B",
            rank: 2,
            mechanism: "mB",
            intervention: "iB",
            predicted_effect: "eB",
            falsification_test: "fB",
            distinctness: "DISTINCT",
            ranking_basis: { span_bound: 2 },
            state: "CANDIDATE",
          },
          {
            candidate_id: "cand:A",
            rank: 1,
            mechanism: "mA",
            intervention: "iA",
            predicted_effect: "eA",
            falsification_test: "fA",
            distinctness: "DISTINCT",
            ranking_basis: { span_bound: 2, testability: 1 },
            state: "CANDIDATE",
          },
        ],
        candidate_count_ranked: 2,
        mode: "DRY_RUN_FIXTURE",
        r506_eligible: false,
      },
    },
  });
}

test("portfolio renders verbatim in canonical wire order (no sort)", () => {
  const items = mod.deriveCandidates(portfolioDetail());
  assert.equal(items.length, 2);
  assert.equal(items[0].candidateId, "cand:B");
  assert.equal(items[0].rank, 2);
  assert.equal(items[1].candidateId, "cand:A");
  assert.equal(items[1].rank, 1);
});

test("rank, distinctness and basis ride verbatim (no derivation)", () => {
  const items = mod.deriveCandidates(portfolioDetail());
  assert.equal(items[1].distinctness, "DISTINCT");
  assert.equal(
    items[1].rankingBasis,
    JSON.stringify({ span_bound: 2, testability: 1 }));
  assert.equal(items[1].mechanism, "mA");
  assert.equal(items[1].risk, "fA");
});

test("absent portfolio keeps the legacy generations path", () => {
  const detail = baseDetail({
    run_state: {
      run_id: "r1",
      status: "COMPLETE",
      generations: {
        generations: [
          {
            gen: 1,
            label: "Invention 01",
            architecture: {
              intervention: "i",
              mechanism: "m",
              expected_effect: "e",
              falsification_test: "f",
            },
            challenge: {},
            maturity: null,
            what_changed: null,
          },
        ],
      },
    },
  });
  const items = mod.deriveCandidates(detail);
  assert.equal(items.length, 1);
  assert.equal(items[0].label, "Invention 01");
  assert.equal(items[0].candidateId, null);
  assert.equal(items[0].rank, null);
  assert.equal(items[0].distinctness, null);
  assert.equal(items[0].rankingBasis, null);
});

test("null portfolio behaves like absent portfolio", () => {
  const detail = baseDetail({
    run_state: { run_id: "r1", status: "COMPLETE", portfolio: null },
  });
  assert.deepEqual(mod.deriveCandidates(detail), []);
});
