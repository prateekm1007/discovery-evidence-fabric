// R461 — ADVERSARIAL TESTS for the independent-audit fixes:
//   P0-2  the user's typed action words ride the action byte-for-byte
//         (buildActionParams) and render in the child round's
//         conversation (directiveDisplayText + deriveConversation)
//   P1-10 the maturity boundary is a first-line human sentence that
//         can never read as physical validation (presentMaturity)
//
// They run the React-free presentation core in plain Node — executable
// evidence, not prose (Art. XVI). Run: npm run test:r461

import { test } from "node:test";
import assert from "node:assert/strict";
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const build = path.join(here, ".build-r461");
if (!existsSync(path.join(build, "actionContract.js"))) {
  throw new Error("r461 modules not compiled — run npm run test:r461");
}
const { buildActionParams, findEvidenceMode } = await import(
  path.join(build, "actionContract.js")
);
const present = await import(path.join(build, "present.js"));

// ---------------------------------------------------------------------------
// P0-2 — the words survive
// ---------------------------------------------------------------------------

test("buildActionParams: the user's words ride the action byte-for-byte", () => {
  // the audit's acceptance: "exact free-text instruction preserved
  // byte-for-byte in child directive" — the params are where it starts
  const text =
    "Try another mechanism — focus on passive pressure recovery, keep the 6 mm envelope";
  const params = buildActionParams("CHANGE_MECHANISM", text);
  assert.equal(params.direction, text);
  // byte-for-byte includes the multibyte characters, not a normalized copy
  const text2 = "Use this manufacturer's PDF — the ±0.1 mm tolerance is measured";
  assert.equal(buildActionParams("ATTACK", text2).direction, text2);
});

test("buildActionParams: no words → no invented direction", () => {
  assert.deepEqual(buildActionParams("REQUEST_ENGINEERING", ""), {});
  assert.deepEqual(buildActionParams("REVIEW_PACKAGE", "   "), {});
});

test("buildActionParams: FIND_EVIDENCE derives its honest mode from the words", () => {
  assert.equal(findEvidenceMode("Look for contradictory evidence"), "contradictory");
  assert.equal(findEvidenceMode("find supporting evidence for the seal"), "supporting");
  assert.equal(findEvidenceMode("Look for more evidence"), "general");
  // mode rides WITH the verbatim text, never instead of it
  const p = buildActionParams("FIND_EVIDENCE", "Look for contradictory evidence about the seal");
  assert.equal(p.direction, "Look for contradictory evidence about the seal");
  assert.equal(p.mode, "contradictory");
});

test("directiveDisplayText: the machine verb tag stays out of the visible line", () => {
  assert.equal(
    present.directiveDisplayText(
      "[CHANGE_MECHANISM] Try another mechanism — keep the constraint"
    ),
    "Try another mechanism — keep the constraint"
  );
  // the stored record keeps the tag; only the DISPLAY strips it
  assert.equal(
    present.directiveDisplayText("[ATTACK] Challenge candidate 2"),
    "Challenge candidate 2"
  );
  assert.equal(present.directiveDisplayText(null), null);
  assert.equal(present.directiveDisplayText(""), null);
  assert.equal(present.directiveDisplayText("[GARBAGE]"), null);
});

test("deriveConversation: an action-opened round opens with the user's own words", () => {
  const detail = minimalDetail({
    user_directive: {
      action_id: "act_test",
      verb: "CHANGE_MECHANISM",
      directive: "[CHANGE_MECHANISM] Keep the goal, drop the pump — try a passive restrictor",
      parent_session_id: "ts_parent",
    },
  });
  const msgs = present.deriveConversation(detail, null, false);
  const userMsgs = msgs.filter((m) => m.kind === "user");
  // the problem, then the steering words
  assert.ok(userMsgs.length >= 2, "expected problem + directive user lines");
  assert.equal(
    userMsgs[1].text,
    "Keep the goal, drop the pump — try a passive restrictor"
  );
});

test("deriveConversation: a parent round renders NO phantom directive line", () => {
  const detail = minimalDetail({});
  const msgs = present.deriveConversation(detail, null, false);
  const userMsgs = msgs.filter((m) => m.kind === "user");
  assert.equal(userMsgs.length, 1);
});

// ---------------------------------------------------------------------------
// P1-10 — the maturity boundary is first-line and honest
// ---------------------------------------------------------------------------

test("presentMaturity: a machine maturity label can never read as physical validation", () => {
  for (const [raw, must] of [
    ["ENGINEERING_DEFINITION", "not physically validated"],
    ["ENGINEERING_DEFINED", "not physically validated"],
    ["SIMULATED", "not physically validated"],
    ["COMPUTATIONAL", "not physically validated"],
    ["MODELLED", "not physically validated"],
  ]) {
    const out = present.presentMaturity(raw);
    assert.ok(out.includes(must), `${raw} → ${out} must carry the boundary`);
    assert.ok(!out.includes(raw), `${raw} must not headline raw`);
  }
});

test("presentMaturity: physical observation is claimed ONLY when the record says so", () => {
  const out = present.presentMaturity("PHYSICALLY_OBSERVED");
  assert.match(out, /Physically observed/);
});

test("presentMaturity: unknown label falls back honest, never invented semantics", () => {
  const out = present.presentMaturity("SOME_FUTURE_STATE");
  assert.ok(out.includes("SOME_FUTURE_STATE".toLowerCase()) === false || out.length > 0);
  assert.ok(out.includes("not physically validated"), out);
  assert.equal(present.presentMaturity(null), null);
  assert.equal(present.presentMaturity(""), null);
});

// ---------------------------------------------------------------------------
// P0 observability — elapsed time on the live line, from the record only
// ---------------------------------------------------------------------------

test("elapsedSuffix: honest durations, never an invented ETA", () => {
  const now = Date.parse("2026-09-14T12:30:00Z");
  assert.equal(present.elapsedSuffix("2026-09-14T12:30:30Z", now), "");      // <1 min: silent
  assert.equal(present.elapsedSuffix(undefined, now), "");                   // no record: silent
  assert.equal(present.elapsedSuffix("garbage", now), "");                   // unparseable: silent
  assert.equal(present.elapsedSuffix("2026-09-14T12:05:00Z", now), " for 25 min");
  assert.equal(present.elapsedSuffix("2026-09-14T10:00:00Z", now), " for 2 h 30 min");
  assert.equal(present.elapsedSuffix("2026-09-14T10:30:00Z", now), " for 2 h");
});

// ---------------------------------------------------------------------------
// fixture — a minimal RUNNING session detail
// ---------------------------------------------------------------------------

function minimalDetail(overrides) {
  return {
    session_id: "ts_fixture_r461",
    title: "Fixture problem",
    user_text: "Fixture problem text",
    status: "COMPLETE",
    created_at: "2026-09-14T00:00:00Z",
    run_dir: null,
    problem_id: null,
    final_status: "COMPLETE",
    stages: [],
    final_state: null,
    package: null,
    user_state_view: { user_state: "COMPLETED_CANDIDATE", outcome: null },
    run_state: { generations: { generations: [] } },
    ...overrides,
  };
}
