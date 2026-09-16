// adversarial_r476.test.mjs — the operator's UI audit (9 files,
// file:line grounded) executed as code.
//
// The audit's verified findings, landed this round:
//   (1) COMPLEXITY HIDING — Workspace rendered the raw machine gate
//       verdict (`PASS` / `COMPLETE_PASS`) as badge text: the same
//       BS-009 class MATURITY_PRESENTATION and stageShortName already
//       govern. The badge now speaks product language; the raw verdict
//       rides the title deep layer (the ModelViewer badge/badgeTitle
//       pattern).
//   (2) A11Y — the workspace panel was an unnamed <aside> with no
//       focus management; the model viewer's toggles had no
//       aria-pressed and the canvas region no accessible name; the
//       derived "Still working" line (the ONLY live line on screen in
//       the worst moments — early run, stalled stream) was not a live
//       region.
//   (3) ERROR UX — api.ts json() interpolated the raw response body
//       (a JSON blob) into Error messages that surface in the UI.
//   (4) CSS — a dead `.wk-siblings { display: none; }` rule fought the
//       R459 restore block at equal specificity (later block wins):
//       dead weight + a live contradiction.
//   (5) PERF — hero ContactShadows rendered at 1024 (2x drei's
//       default) for a soft shadow indistinguishable at 512.
//
// AUDIT CORRECTIONS recorded (the audit's own claims, measured):
//   - "live progress has no aria-live" is TRUE only for the DERIVED
//     line; the SSE live block (Conversation.tsx data-conv-live-block)
//     already carried aria-live="polite". Both are live regions now.
//   - the sibling contradiction was BENIGN at runtime (later block
//     wins) — a latent contradiction, not a visible bug; removed.
//   - the hud/toggle buttons carry visible text, which IS the
//     accessible name; adding aria-label there would have OVERRIDDEN
//     the visible text. The correct fix is aria-pressed on the toggles
//     and a group label on the region — applied.

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const webapp = path.resolve(here, "..");
const read = (rel) => readFileSync(path.join(webapp, rel), "utf8");

// the compiled presentation authority (same shape as test:present /
// test:r461 — tsc to commonjs, then require)
const { presentGateVerdict } = await import(
  path.join(webapp, "tests/.build-r476/present.js")
);

const workspace = read("components/Workspace.tsx");
const viewer = read("components/ModelViewer.tsx");
const conversation = read("components/Conversation.tsx");
const api = read("lib/api.ts");
const css = read("app/globals.css");

// ---------------------------------------------------------------------------
// (1) the gate badge — product language on the surface, raw verdict deep
// ---------------------------------------------------------------------------

test("R476: presentGateVerdict maps the certified verdicts to product language", () => {
  assert.equal(presentGateVerdict("PASS"), "certified");
  assert.equal(presentGateVerdict("COMPLETE_PASS"), "fully certified");
});

test("R476: presentGateVerdict is case-insensitive and whitespace-safe", () => {
  assert.equal(presentGateVerdict("pass"), "certified");
  assert.equal(presentGateVerdict("  COMPLETE_PASS  "), "fully certified");
});

test("R476: BS-009 — presentGateVerdict NEVER passes a raw verdict through", () => {
  const vocabulary = [
    "PASS",
    "COMPLETE_PASS",
    "FAIL",
    "FAILED",
    "BLOCKED",
    "UNKNOWN",
    "NOT_RUN",
    "PENDING",
    "SOME_FUTURE_VERDICT",
  ];
  for (const v of vocabulary) {
    const out = presentGateVerdict(v);
    assert.notEqual(out, v, `raw verdict leaked through for ${v}`);
    assert.doesNotMatch(out, /_/u, `machine casing leaked through for ${v}`);
  }
});

test("R476: presentGateVerdict is total — empty input states the absence honestly", () => {
  assert.equal(presentGateVerdict(""), "not certified");
  assert.equal(presentGateVerdict("   "), "not certified");
  assert.equal(presentGateVerdict(undefined), "not certified");
  assert.equal(presentGateVerdict(null), "not certified");
});

test("R476: the badge renders the presentation mapping, never the raw verdict", () => {
  assert.match(workspace, /presentGateVerdict\(gateVerdict\)/);
  // the leak, verbatim as the audit pinned it, is gone
  assert.doesNotMatch(
    workspace,
    /\} \{gateVerdict\}/u,
    "the raw gate verdict still renders as badge text",
  );
  // the raw verdict rides the title deep layer (badge/badgeTitle pattern)
  assert.match(workspace, /title=\{`visual quality gate verdict: \$\{gateVerdict\}`\}/);
});

// ---------------------------------------------------------------------------
// (2) the workspace panel — a named, focusable, non-modal surface
// ---------------------------------------------------------------------------

test("R476: the workspace aside is a named panel", () => {
  assert.match(
    workspace,
    /<aside\s*\n\s*ref=\{panelRef\}[\s\S]*?aria-label=\{SURFACE_TITLES\[surface\] \?\? surface\}/u,
  );
});

test("R476: the panel takes focus when it opens (and on surface switch)", () => {
  assert.match(workspace, /panelRef = useRef/);
  assert.match(workspace, /panelRef\.current\?\.focus\(\)/);
  assert.match(workspace, /tabIndex=\{-1\}/);
});

test("R476: the panel stays NON-modal — no focus trap is imported or used", () => {
  // the workspace coexists with the conversation; trapping focus would
  // break that contract. Initial focus + Escape-close is the pattern.
  // (prose mentioning "focus-trap" in comments is fine — pin USAGE.)
  assert.doesNotMatch(workspace, /from ["']focus-trap|createFocusTrap|useFocusTrap|focus-trap-react/i);
  // the Escape-close contract is untouched
  assert.match(workspace, /if \(e\.key === "Escape"\) onClose\(\)/);
});

// ---------------------------------------------------------------------------
// (3) the model viewer — named region, honest toggle state
// ---------------------------------------------------------------------------

test("R476: the viewer region has an accessible name without breaking the ONE-viewer invariant", () => {
  assert.match(viewer, /role="group"/);
  assert.match(viewer, /aria-label=\{\`\$\{label\} — interactive 3D viewer/);
  // the machine-checked invariant (test_r433) is untouched
  assert.match(viewer, /data-model-viewer=\{label\}/);
});

test("R476: the wireframe/clip toggles expose their pressed state", () => {
  assert.match(viewer, /setWire\(!wire\)[^>]*aria-pressed=\{wire\}/s);
  assert.match(viewer, /setClip\(!clip\)[^>]*aria-pressed=\{clip\}/s);
  // the visible text stays the accessible name — no aria-label override
  assert.match(viewer, /aria-pressed=\{wire\}>\s*\{wire \? "shaded" : "wireframe"\}/s);
});

test("R476: hero ContactShadows render at 512 (the audit's perf finding)", () => {
  assert.doesNotMatch(viewer, /resolution=\{1024\}/);
  assert.match(viewer, /resolution=\{512\}/);
});

// ---------------------------------------------------------------------------
// (4) json() — the wire format never leaks into UI error copy
// ---------------------------------------------------------------------------

test("R476: json() no longer stringifies the raw body into the message", () => {
  assert.doesNotMatch(
    api,
    /JSON\.stringify\(await res\.json\(\)\)/u,
    "the raw JSON blob still lands in the error message",
  );
  // the typed detail (FastAPI error shape) is extracted when present
  assert.match(api, /"detail" in body/);
  // the status stays the FIRST token — transport handling keys on it
  assert.match(api, /`\$\{res\.status\} \$\{res\.statusText\}\$\{detail \? `: \$\{detail\}` : ""\}`/);
});

test("R476: json() surfaces the engine's typed detail, and never a JSON blob", async () => {
  const apiModule = await import(
    path.join(webapp, "tests/.build-r476/api.js")
  );
  const realFetch = globalThis.fetch;
  const respond = (body, status, statusText) =>
    new Response(typeof body === "string" ? body : JSON.stringify(body), {
      status,
      statusText,
      headers: { "Content-Type": "application/json" },
    });
  try {
    // typed detail — the engine's own readable reason surfaces verbatim
    globalThis.fetch = async () =>
      respond({ detail: "the evidence index is rebuilding" }, 500, "Internal Server Error");
    await assert.rejects(
      () => apiModule.askRun("ts_x", "why?"),
      (e) => e.message === "500 Internal Server Error: the evidence index is rebuilding",
    );

    // status-first token preserved (page.tsx keys its 404 branch on it)
    globalThis.fetch = async () =>
      respond({ detail: "Run not found" }, 404, "Not Found");
    await assert.rejects(
      () => apiModule.askRun("ts_missing", "why?"),
      (e) => e.message.startsWith("404") && e.message.includes("Run not found"),
    );

    // a body WITHOUT a string detail — no wire format in the message
    globalThis.fetch = async () =>
      respond({ error: { code: 7, blob: "x".repeat(400) } }, 500, "Internal Server Error");
    await assert.rejects(
      () => apiModule.askRun("ts_x", "why?"),
      (e) => e.message === "500 Internal Server Error",
    );

    // non-JSON body — the status line alone
    globalThis.fetch = async () =>
      respond("<html>gateway error</html>", 502, "Bad Gateway");
    await assert.rejects(
      () => apiModule.askRun("ts_x", "why?"),
      (e) => e.message === "502 Bad Gateway",
    );

    // success passes the body through untouched
    globalThis.fetch = async () =>
      respond({ question: "why?", response: { status: "ANSWERED" } }, 200, "OK");
    const ok = await apiModule.askRun("ts_x", "why?");
    assert.equal(ok.response.status, "ANSWERED");
  } finally {
    globalThis.fetch = realFetch;
  }
});

// ---------------------------------------------------------------------------
// (5) the live region — the derived "Still working" line speaks too
// ---------------------------------------------------------------------------

test("R476: the derived progress line is a live region (the audit's a11y finding)", () => {
  // the exact line the audit pinned: the case "progress" render —
  // the ONLY live line on screen when the SSE stream is silent
  assert.match(
    conversation,
    /case "progress":[\s\S]*?aria-live="polite"[\s\S]*?data-conv-live/u,
  );
});

test("R476: the SSE live block keeps its existing live region (audit correction)", () => {
  assert.match(conversation, /data-conv-live-block aria-live="polite"/);
});

// ---------------------------------------------------------------------------
// (6) the dead CSS rule — the R459 decision stands, alone
// ---------------------------------------------------------------------------

test("R476: the contradictory mobile rule is gone, the R459 restore stands", () => {
  assert.doesNotMatch(css, /\.wk-siblings \{ display: none; \}/u);
  // the R459 restore block, verbatim (comment rides the display line)
  assert.match(
    css,
    /\.wk-siblings \{\s*display: flex; \/\* R459: restoring one-tap surface switching on mobile \*\//u,
  );
});
