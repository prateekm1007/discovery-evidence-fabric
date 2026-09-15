// adversarial_r466.test.mjs — R466 reaudit-closure acceptance battery.
//
// The reaudit (7.9/10) left two small code changes and named them:
//
//   1. Conversation list semantics — the Discoveries rail renders as a
//      semantic <ol> of <li> items (the reaudit's one open structural
//      item), for the Discoveries list in both views (search and time
//      buckets) and for the packages list.
//   2. Action-continuity residual friction — ROOT CAUSE: the steering
//      directive rode the transient user_directive field, which the
//      worker consumes and CLEARS at spawn (worker.py), so the user's
//      words vanished from the child thread the moment the run began.
//      The durable record (the child's conversation context, appended
//      by the engine at round creation, never cleared) is now the
//      primary read; an in-thread continuation card names the round
//      and keeps the parent one tap away inside the conversation
//      surface.
//
// The present.ts tests run the SHIPPED module (esbuild-compiled), not
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
  `npx --yes esbuild@0.25.5 lib/present.ts --bundle ` +
    `--format=cjs --outfile=${outDir}/present.cjs --log-level=error`,
  { cwd: webapp, stdio: "pipe" },
);
const require = createRequire(import.meta.url);
const present = require(path.join(outDir, "present.cjs"));

const read = (rel) => readFileSync(path.join(webapp, rel), "utf8");

// ---------------------------------------------------------------------------
// Part 2 — the directive survives the run starting (durable record)
// ---------------------------------------------------------------------------

function childDetail(overrides = {}) {
  return {
    session_id: "ts_child",
    title: "Pump cavitation",
    user_text: "Why does the pump cavitate?",
    status: "COMPLETE",
    created_at: "2026-09-15T00:00:00Z",
    run_dir: null,
    problem_id: null,
    final_status: null,
    parent_session_id: "ts_parent",
    user_directive: {},
    conversation: [
      {
        role: "user",
        text: "[CHANGE_MECHANISM] try a different material",
        classification: "directive",
        affects_canonical_state: false,
      },
    ],
    user_state_view: { user_state: "COMPLETED_CANDIDATE" },
    ...overrides,
  };
}

test("R466: the steering words survive the worker clearing user_directive", () => {
  // the worker writes user_directive={} at spawn; the conversation
  // record still carries the directive — the thread must show it
  const msgs = present.deriveConversation(childDetail(), null, false);
  const directive = msgs.find((m) => m.kind === "user" && m.id.startsWith("ud"));
  assert.ok(directive, "the directive line must render");
  assert.equal(directive.text, "try a different material");
});

test("R466: the machine verb tag is stripped, the user's words are not", () => {
  const msgs = present.deriveConversation(childDetail(), null, false);
  const directive = msgs.find((m) => m.kind === "user" && m.id.startsWith("ud"));
  assert.ok(!/\[[A-Z_]+\]/.test(directive.text), "no machine tag on the surface");
});

test("R466: transient user_directive still covers a record without the conversation entry", () => {
  const d = childDetail({
    conversation: undefined,
    user_directive: { verb: "CHANGE_MECHANISM", directive: "[ATTACK] stress-test the seal" },
  });
  const msgs = present.deriveConversation(d, null, false);
  const directive = msgs.find((m) => m.kind === "user" && m.id.startsWith("ud"));
  assert.ok(directive, "the fallback must render");
  assert.equal(directive.text, "stress-test the seal");
});

test("R466: no record anywhere renders nothing (nothing is invented)", () => {
  const d = childDetail({ conversation: undefined, user_directive: {} });
  const msgs = present.deriveConversation(d, null, false);
  assert.ok(!msgs.some((m) => m.id.startsWith("ud")));
});

test("R466: a NON-fork run never reads the conversation as a directive", () => {
  // a clarification answer could be the first conversation entry on a
  // plain run — the durable read is fenced to action-opened rounds
  const d = childDetail({
    parent_session_id: null,
    user_directive: {},
    conversation: [{ role: "user", text: "[ASK] what about temperature?" }],
  });
  const msgs = present.deriveConversation(d, null, false);
  assert.ok(!msgs.some((m) => m.id.startsWith("ud")));
});

test("R466: a non-user first entry (defensive) is skipped, not rendered", () => {
  const d = childDetail({
    conversation: [
      { role: "system", text: "[X] not a user line" },
      { role: "user", text: "[FIND_EVIDENCE] look for contradictory evidence" },
    ],
  });
  const msgs = present.deriveConversation(d, null, false);
  const directive = msgs.find((m) => m.kind === "user" && m.id.startsWith("ud"));
  assert.ok(directive, "the real user directive renders");
  assert.equal(directive.text, "look for contradictory evidence");
});

// ---------------------------------------------------------------------------
// Part 2b — the in-thread continuation card (source assertions)
// ---------------------------------------------------------------------------

test("R466: the continuation card renders inside the conversation surface", () => {
  const src = read("components/Conversation.tsx");
  assert.ok(src.includes("data-continued-card"), "the card exists");
  assert.ok(src.includes("detail.parent_session_id &&"), "gated on a parent");
  assert.ok(src.includes("Continue from the earlier round"), "the back link");
  assert.ok(src.includes("roundNumber"), "the round number rides in");
});

test("R466: the page passes the recorded round number", () => {
  const src = read("app/page.tsx");
  assert.ok(src.includes("roundNumber={currentRound}"));
});

test("R466: the card copy stays plain-language (no machine vocabulary)", () => {
  const src = read("components/Conversation.tsx");
  const card = src.slice(src.indexOf("data-continued-card"));
  assert.ok(!/\b(CHANGE_MECHANISM|RETRIEVE|ADJUDICATION)\b/.test(card.slice(0, 1200)));
});

// ---------------------------------------------------------------------------
// Part 1 — conversation list semantics (ol/li)
// ---------------------------------------------------------------------------

test("R466: the Discoveries rail is a semantic ordered list", () => {
  const src = read("components/Sidebar.tsx");
  assert.ok(/<ol className="rail-list">/.test(src), "the ol exists");
  // BOTH views: the search view and the time-bucket view
  const ols = src.match(/<ol className="rail-list">/g) || [];
  assert.ok(ols.length >= 3, `expected ol in search + buckets + packages, got ${ols.length}`);
  assert.ok(/<li key=/.test(src), "items are li elements");
  // the button markup is unchanged inside the li
  assert.ok(/<li key=\{s\.session_id\}[^>]*>\s*<button/.test(src.replace(/\n/g, " ")) ||
    (src.includes("<li key={s.session_id}") && src.includes("<button")),
    "li wraps the button");
});

test("R466: the list chrome is reset (no visual regression by construction)", () => {
  const css = read("app/globals.css");
  assert.ok(/\.rail-list \{/.test(css), "the reset exists");
  assert.ok(/list-style:\s*none/.test(css), "no bullets");
  assert.ok(/margin:\s*0/.test(css), "no default margins");
  assert.ok(/padding:\s*0/.test(css), "no default padding");
});

test("R466: the packages list is semantic too", () => {
  const src = read("components/Sidebar.tsx");
  assert.ok(src.includes("renderPackage"), "the shared package renderer");
  assert.ok(src.includes("<ol className=\"rail-list\">{focus.map(renderPackage)}</ol>"));
});

// ---------------------------------------------------------------------------
// Part 3 — the production-measured contrast failure, pinned by arithmetic
// ---------------------------------------------------------------------------

test("R466: the CTA fill passes WCAG AA with its white label (computed, not asserted)", () => {
  const css = read("app/globals.css");
  // the .btn fill must be the AA text token, never the decorative accent
  const btnBlock = css.slice(css.indexOf(".btn {"), css.indexOf(".btn:hover"));
  assert.ok(/--accent-text/.test(btnBlock), "the fill is --accent-text");
  assert.ok(!/--accent;/.test(btnBlock), "the decorative accent (#c15f3c, 4.22:1) is not a text-bearing fill");
  // the arithmetic, computed here (R464's method): relative luminance
  const lum = (hex) => {
    const c = hex.match(/[0-9a-f]{2}/gi).map((x) => parseInt(x, 16) / 255)
      .map((v) => (v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4)));
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
  };
  const ratio = (a, b) => (Math.max(lum(a), lum(b)) + 0.05) / (Math.min(lum(a), lum(b)) + 0.05);
  const fill = css.match(/--accent-text:\s*(#[0-9a-f]{6})/)[1];
  const r = ratio("#ffffff", fill);
  assert.ok(r >= 4.5, `white on ${fill} = ${r.toFixed(2)}:1 — must be >= 4.5:1`);
});
