// adversarial_r477_p0.test.mjs — the CTO line of the R477 parallel the external audit's P0 batch executed
// as code (the 2026-09-16 audit's "9/10 BLOCKERS", items 1/3/4/5 and
// the P0-2 STORED chip):
//
//   P0-1  QUEUED MID-RUN STEER — the receipt: the engine already saves
//         every mid-run direction durably (R471); the UI now SAYS SO
//         (queued receipt, not a bare refusal), the steer chips no
//         longer hide while the run is live, and the terminal thread
//         carries the directive-outcome card verbatim.
//   P0-2  STORED-EXPLICIT CHIP — a stored-not-read attachment is an
//         unmissable badge with the custody hash, never a footnote.
//   P0-3  INTENT ROUTER V2 — verbatim-direction + confirm: a typed
//         steering phrase stops and asks "Send as: <label>? Do it /
//         Ask" instead of silently demoting to the read-only ask
//         endpoint (the audit's measured silent no-op).
//   P0-4  SINGLE NBA — the UI reads GET /api/run/{id}/contract and the
//         engine's recorded next action IS the one next action when it
//         exists (source: "engine-record"); the presentation derivation
//         is the documented fallback, never a second displayed
//         authority.
//   P0-5  PACKAGE 200-PROBE — packageAvailable survives only while the
//         actual download route has not answered 409; the gate's typed
//         payload renders as a sentence + the diagnostic fallback.
//
// They run the React-free presentation core in plain Node — executable
// evidence, not prose (Art. XVI). Run: npm run test:r477p0

import { test } from "node:test";
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const webapp = path.resolve(here, "..");
const build = path.join(here, ".build-r477p0");
if (!existsSync(path.join(build, "actionContract.js"))) {
  throw new Error("r477 modules not compiled — run npm run test:r477p0");
}
const read = (rel) => readFileSync(path.join(webapp, rel), "utf8");

const contract = await import(path.join(build, "actionContract.js"));
const api = await import(path.join(build, "api.js"));
const present = await import(path.join(build, "present.js"));

const conversation = read("components/Conversation.tsx");
const workspace = read("components/Workspace.tsx");
const page = read("app/page.tsx");
const css = read("app/globals.css");

// ---------------------------------------------------------------------------
// helpers
// ---------------------------------------------------------------------------

function minimalDetail(overrides) {
  return {
    session_id: "ts_fixture_r477",
    title: "Fixture problem",
    user_text: "Fixture problem text",
    status: "COMPLETE",
    created_at: "2026-09-16T00:00:00Z",
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

// ---------------------------------------------------------------------------
// P0-3 — the intent router v2: the audit's 20-follow-up battery
// (acceptance: "20 follow-up battery 18/20 routed as intended")
// ---------------------------------------------------------------------------

// The battery. `intent` is what a user with that message wants:
//   { confirm: verb } — the composer must stop and offer the action;
//   { ask: true }     — the message must flow as a plain question.
const BATTERY = [
  // — steering directions (the audit's own examples first) —
  { text: "make it cheaper", intent: { confirm: "CHANGE_MECHANISM" } },
  { text: "use a different material", intent: { confirm: "CHANGE_MECHANISM" } },
  { text: "optimize for manufacturability", intent: { confirm: "REQUEST_ENGINEERING" } },
  { text: "try another mechanism", intent: { confirm: "CHANGE_MECHANISM" } },
  { text: "challenge this candidate", intent: { confirm: "ATTACK" } },
  { text: "look for contradictory evidence", intent: { confirm: "FIND_EVIDENCE" } },
  { text: "compare the mechanisms", intent: { confirm: "COMPARE_MECHANISMS" } },
  { text: "design the decisive experiment", intent: { confirm: "REQUEST_EXPERIMENT" } },
  { text: "keep the pressure drop but change the mechanism", intent: { confirm: "CHANGE_MECHANISM" } },
  { text: "no external literature search", intent: { confirm: "CHANGE_MECHANISM" } },
  { text: "reduce the pressure loss", intent: { confirm: "CHANGE_MECHANISM" } },
  { text: "make it smaller and lighter", intent: { confirm: "CHANGE_MECHANISM" } },
  { text: "use a different coating", intent: { confirm: "CHANGE_MECHANISM" } },
  { text: "dig deeper", intent: { confirm: "RESEARCH" } },
  { text: "avoid the kink", intent: { confirm: "CHANGE_MECHANISM" } },
  { text: "work out the engineering", intent: { confirm: "REQUEST_ENGINEERING" } },
  // — questions (hijacking a question into an action would be a worse
  // defect than the one P0-3 closes) —
  { text: "what mechanisms did you consider?", intent: { ask: true } },
  { text: "why did the strongest candidate fail?", intent: { ask: true } },
  { text: "how does the pump mechanism work?", intent: { ask: true } },
  { text: "hello there", intent: { ask: true } },
];

test("R477 P0-3: the 20-follow-up battery routes 20/20 as intended (>= 18/20 required)", () => {
  let hits = 0;
  const misses = [];
  for (const c of BATTERY) {
    const route = contract.classifyMessage(c.text);
    const verb = contract.directionConfirmVerb(c.text, route);
    const ok =
      c.intent.confirm
        ? verb === c.intent.confirm
        : verb === null;
    if (ok) hits += 1;
    else misses.push({ text: c.text, got: verb, wanted: c.intent });
  }
  assert.deepEqual(misses, []);
  assert.ok(hits >= 18, `battery ${hits}/20 — acceptance is 18/20`);
});

test("R477 P0-3: the audit's lead case confirms as an action, never a silent ask", () => {
  const route = contract.classifyMessage("make it cheaper");
  assert.equal(route.kind, "action");
  assert.equal(contract.directionConfirmVerb("make it cheaper", route), "CHANGE_MECHANISM");
});

test("R477 P0-3: an unmatched direction-shaped message lifts to the generic steer verb", () => {
  const route = contract.classifyMessage("no external literature search");
  assert.equal(route.kind, "ask");
  assert.equal(contract.directionConfirmVerb("no external literature search", route), "CHANGE_MECHANISM");
});

test("R477 P0-3: a question stays a question — no hijack", () => {
  for (const q of [
    "what is the strongest candidate?",
    "why did it fail?",
    "is the seal safe?",
    "can it be manufactured?",
  ]) {
    const route = contract.classifyMessage(q);
    assert.equal(
      contract.directionConfirmVerb(q, route),
      null,
      `question hijacked: ${q}`
    );
  }
});

test("R477 P0-3: a table-matched question CONFIRMS — the ambiguous class gets the explicit choice", () => {
  // "how would we test this?" is the settled table's REQUEST_EXPERIMENT
  // shape AND a question — exactly the ambiguity the old router resolved
  // SILENTLY (the audit's defect). v2 stops and asks; it never sends
  // either way without the user's choice.
  const route = contract.classifyMessage("how would we test this?");
  assert.equal(route.kind, "action");
  assert.equal(route.verb, "REQUEST_EXPERIMENT");
  assert.equal(
    contract.directionConfirmVerb("how would we test this?", route),
    "REQUEST_EXPERIMENT"
  );
});

test("R477 P0-3: benign chatter stays a plain ask", () => {
  const route = contract.classifyMessage("hello there");
  assert.equal(route.kind, "ask");
  assert.equal(contract.directionConfirmVerb("hello there", route), null);
});

test("R477 P0-3: the composer renders the confirm row with Do it / Ask", () => {
  assert.match(conversation, /data-confirm-send/);
  assert.match(conversation, /data-confirm-act/);
  assert.match(conversation, /data-confirm-ask/);
  assert.match(conversation, /Do it/);
  // the Ask choice rides the confirm row (JSX text after its marker)
  assert.match(conversation, /data-confirm-ask[\s\S]{0,160}Ask/);
  // the intercept exists in the submit path
  assert.match(conversation, /directionConfirmVerb/);
  // the old silent gate is gone
  assert.ok(!conversation.includes("data-conv-steer-locked"),
    "the 'Steering opens when complete' locked note must be gone");
});

// ---------------------------------------------------------------------------
// P0-1 — the queued receipt + the directive-outcome card
// ---------------------------------------------------------------------------

test("R477 P0-1: the queued receipt renders from the engine's note, never as a bare refusal", () => {
  assert.match(conversation, /result\.queued/);
  assert.match(conversation, /queued_note/);
  assert.match(conversation, /data-queued=/);
  // the fallback copy mirrors the engine's 409 note in meaning
  assert.match(contract.QUEUED_RECEIPT_COPY, /saved/);
  assert.match(contract.QUEUED_RECEIPT_COPY, /finishes/);
});

test("R477 P0-1: the steer chips are visible while the run is live, with the honest lead-in", () => {
  assert.match(conversation, /While it runs, your direction is saved/);
  assert.match(conversation, /steerLead/);
});

test("R477 P0-1: the terminal thread carries the directive-outcome card verbatim", () => {
  const detail = minimalDetail({
    queued_directive: {
      verb: "CHANGE_MECHANISM",
      params: { direction: "make it cheaper" },
      directive: "[CHANGE_MECHANISM] make it cheaper",
      queued_at: "2026-09-16T01:00:00Z",
    },
  });
  const msgs = present.deriveConversation(detail, null, false);
  const queued = msgs.filter((m) => m.kind === "queued");
  assert.equal(queued.length, 1);
  // the USER'S words verbatim — the machine verb tag stays out (BS-009)
  assert.equal(queued[0].text, "make it cheaper");
  // and the ONE next action is running that saved direction
  const outcome = msgs.find((m) => m.kind === "outcome");
  assert.ok(outcome?.next);
  assert.equal(outcome.next.kind, "run_queued");
  assert.match(outcome.next.label, /make it cheaper/);
});

test("R477 P0-1: a live run renders no queued card (nothing saved yet)", () => {
  const detail = minimalDetail({ status: "RUNNING", final_status: null });
  const msgs = present.deriveConversation(detail, null, false);
  assert.equal(msgs.filter((m) => m.kind === "queued").length, 0);
});

test("R477 P0-1: no queued record -> no invented card (Art. VI)", () => {
  const detail = minimalDetail({});
  const msgs = present.deriveConversation(detail, null, false);
  assert.equal(msgs.filter((m) => m.kind === "queued").length, 0);
});

// ---------------------------------------------------------------------------
// P0-4 — the single NBA: the engine's record is the one authority
// ---------------------------------------------------------------------------

test("R477 P0-4: the engine's recorded next action wins with source engine-record", () => {
  const detail = minimalDetail({});
  const next = present.deriveNextAction(detail, null, false, {
    action: "ATTACK_CANDIDATE",
    reason: "the strongest candidate carries one untested load path",
  });
  assert.ok(next);
  assert.equal(next.kind, "act");
  assert.equal(next.verb, "ATTACK");
  assert.equal(next.source, "engine-record");
  assert.equal(next.label, "Challenge the strongest candidate");
  assert.match(next.basis, /untested load path/);
});

test("R477 P0-4: the full closed engine vocabulary maps to honest product actions", () => {
  const cases = [
    ["RETRIEVE_MORE_EVIDENCE", "act", "FIND_EVIDENCE"],
    ["ATTACK_CANDIDATE", "act", "ATTACK"],
    ["GENERATE_COMPETING_MECHANISM", "act", "CHANGE_MECHANISM"],
    ["ENGINEERING_ESCALATION", "act", "REQUEST_ENGINEERING"],
    ["PROPOSE_DECISIVE_EXPERIMENT", "act", "REQUEST_EXPERIMENT"],
  ];
  for (const [action, kind, verb] of cases) {
    const next = present.deriveNextAction(minimalDetail({}), null, false, { action });
    assert.equal(next.kind, kind, action);
    assert.equal(next.verb, verb, action);
    assert.equal(next.source, "engine-record", action);
  }
  const pkg = present.deriveNextAction(minimalDetail({}), null, false, {
    action: "PACKAGE_READY",
  });
  assert.equal(pkg.kind, "package");
  assert.equal(pkg.source, "engine-record");
});

test("R477 P0-4: STOP_HONEST / ASK_CLARIFICATION are NOT invented into buttons", () => {
  for (const action of ["STOP_HONEST", "ASK_CLARIFICATION"]) {
    const next = present.deriveNextAction(minimalDetail({}), null, false, { action });
    assert.ok(next);
    assert.equal(next.source, "presentation", action);
    assert.notEqual(next.kind, "act", action);
  }
});

test("R477 P0-4: an unknown engine action falls through — never an invented button", () => {
  const next = present.deriveNextAction(minimalDetail({}), null, false, {
    action: "SOMETHING_NEW",
  });
  assert.ok(next);
  assert.equal(next.source, "presentation");
});

test("R477 P0-4: no engine record -> the presentation derivation stands (fail-open)", () => {
  const next = present.deriveNextAction(minimalDetail({}), null, false, null);
  assert.ok(next);
  assert.equal(next.source, "presentation");
});

test("R477 P0-4: the shell fetches the contract at terminal and passes it down", () => {
  assert.match(page, /getRunContract/);
  assert.match(page, /engineNextAction=\{contractNext\}/);
  // the executed engine action rides the ONE canonical endpoint
  assert.match(page, /sendAction/);
  assert.match(page, /data-nba-note/);
});

test("R477 P0-4: the queued direction still outranks the engine NBA (never lost)", () => {
  const detail = minimalDetail({
    queued_directive: {
      verb: "RESEARCH",
      directive: "[RESEARCH] keep digging",
      queued_at: "2026-09-16T01:00:00Z",
    },
  });
  const next = present.deriveNextAction(detail, null, false, {
    action: "ATTACK_CANDIDATE",
  });
  assert.equal(next.kind, "run_queued");
  assert.equal(next.source, "presentation");
});

// ---------------------------------------------------------------------------
// P0-5 — the package 200-probe
// ---------------------------------------------------------------------------

test("R477 P0-5: a 200 probe passes and never downloads the body", async () => {
  let cancelled = false;
  const stub = async () => ({
    status: 200,
    ok: true,
    body: { cancel: async () => { cancelled = true; } },
  });
  const out = await api.probePackage("ts_x", stub);
  assert.equal(out.result, "pass");
  assert.equal(cancelled, true);
});

test("R477 P0-5: a 409 probe is BLOCKED and carries the gate's typed payload", async () => {
  const gate = {
    error: "package release blocked",
    package_state: "SURVIVOR_RELEASE_BLOCKED",
    reason: "the survivor gate rejected this invention (NOT_A_SURVIVOR)",
  };
  const stub = async () => ({
    status: 409,
    ok: false,
    json: async () => gate,
  });
  const out = await api.probePackage("ts_x", stub);
  assert.equal(out.result, "blocked");
  assert.equal(out.gate.package_state, "SURVIVOR_RELEASE_BLOCKED");
  assert.match(out.gate.reason, /survivor gate/);
});

test("R477 P0-5: a non-JSON 409 is still blocked (fail-closed)", async () => {
  const stub = async () => ({ status: 409, ok: false, json: async () => { throw new Error("no json"); } });
  const out = await api.probePackage("ts_x", stub);
  assert.equal(out.result, "blocked");
  assert.deepEqual(out.gate, {});
});

test("R477 P0-5: a failed probe is unverified — the UI claims nothing", async () => {
  const out = await api.probePackage("ts_x", async () => {
    throw new Error("network down");
  });
  assert.equal(out.result, "unverified");
  const out2 = await api.probePackage("ts_x", async () => ({
    status: 500, ok: false, body: { cancel: async () => {} },
  }));
  assert.equal(out2.result, "unverified");
});

test("R477 P0-5: packageAvailable survives only while the gate has not answered 409", () => {
  assert.match(page, /pkgProbe\?\.result !== "blocked"/);
  assert.match(page, /probePackage/);
  // the gate renders as a stated state with the diagnostic fallback
  assert.match(workspace, /data-package-gate/);
  assert.match(workspace, /Download the diagnostic record instead/);
  assert.match(css, /\.pkg-gate-note/);
});

// ---------------------------------------------------------------------------
// P0-2 — the STORED chip is unmissable
// ---------------------------------------------------------------------------

test("R477 P0-2: the stored-not-read badge is a bordered chip with the hash tooltip", () => {
  assert.match(page, /ask-stored-badge/);
  assert.match(page, /stored, not read/);
  assert.match(page, /sha256/);
  assert.match(css, /\.ask-stored-badge\s*\{/);
  // the faint footnote class is gone from the stored chip
  assert.ok(
    !/className="faint" data-attachment-stored/.test(page),
    "the stored state must not render as a faint footnote"
  );
});

// ---------------------------------------------------------------------------
// sendAction — the queued result path the receipt consumes (R471 pin,
// re-pinned here because the receipt renders it)
// ---------------------------------------------------------------------------

test("R477: sendAction surfaces the engine's queued=true + note verbatim", async () => {
  const calls = [];
  const stub = async (p, init) => {
    calls.push({ p, init });
    return {
      status: 409,
      ok: false,
      json: async () => ({
        accepted: false,
        code: "RUN_IN_PROGRESS",
        reason: "the investigation is already running",
        queued: true,
        note: "your direction is saved — it will be ready to run the moment this investigation finishes",
      }),
    };
  };
  const out = await contract.sendAction("ts_x", "CHANGE_MECHANISM",
    { direction: "make it cheaper" }, stub);
  assert.equal(out.accepted, false);
  assert.equal(out.queued, true);
  assert.match(out.queued_note, /saved/);
  assert.equal(calls.length, 1);
  assert.match(calls[0].p, /\/api\/run\/ts_x\/actions$/);
});
