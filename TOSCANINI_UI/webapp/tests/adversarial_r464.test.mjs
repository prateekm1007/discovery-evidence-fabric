// adversarial_r464.test.mjs — R464 external-UX-audit acceptance battery.
//
// The independent 7.0/10 review's fixable blockers, pinned as
// executable evidence (Art. XVI: the evidence IS the artifact — these
// tests run the SHIPPED modules, not copies):
//
//   P0-2  the live line carries the run's POSITION (steps derived
//         from recorded events only — never a total, never an ETA)
//   P0-2  the landing states the duration at full weight (source)
//   P0-3  the landing carries a concrete example outcome (source)
//   P0-4  the accent TEXT tokens pass WCAG AA at their rendered sizes
//         (computed here, not asserted by eye)
//   P1-1  the decisive experiment rides the conversation thread
//   P1-2  rounds group under their parent; round numbers derive from
//         the recorded parentage chain (rounds.ts)
//   P1-3  mid-run steering is suppressed with the calm note (source)
//   P1-4  the workspace title is a real heading (source)
//   P1-6  the file input names its types (source)
//   P1-7  the action note carries a dismissal (source)
//   P1-8  the capped rail states its count (source)
//
// Zero dependencies — plain Node.

import { test } from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import { readFileSync } from "node:fs";
import { execSync } from "node:child_process";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const webapp = path.resolve(here, "..");

// compile the shipped TS modules to a temp JS the test imports
const outDir = execSync("mktemp -d").toString().trim();
for (const [name, entry] of [
  ["present", "lib/present.ts"],
  ["productEvents", "lib/productEvents.ts"],
  ["rounds", "lib/rounds.ts"],
]) {
  execSync(
    `npx --yes esbuild@0.25.5 ${entry} --bundle ` +
      `--format=cjs --outfile=${outDir}/${name}.cjs --log-level=error`,
    { cwd: webapp, stdio: "pipe" },
  );
}
const require = createRequire(import.meta.url);
const present = require(path.join(outDir, "present.cjs"));
const productEvents = require(path.join(outDir, "productEvents.cjs"));
const rounds = require(path.join(outDir, "rounds.cjs"));

const read = (rel) => readFileSync(path.join(webapp, rel), "utf8");

// ---------------------------------------------------------------------------
// P0-2 — the stage position suffix
// ---------------------------------------------------------------------------

test("P0-2: the live line suffix counts recorded stages, never a total", () => {
  const events = [
    { kind: "problem.extract", status: "COMPLETED" },
    { kind: "stage.RETRIEVE", status: "ACTIVE" },
    // no completed stages yet -> the active one is step 1
  ];
  assert.equal(productEvents.stageProgressSuffix(events), " · step 1");
});

test("P0-2: distinct completed stages + the active one", () => {
  const events = [
    { kind: "stage.RETRIEVE", status: "COMPLETED" },
    { kind: "stage.RETRIEVE", status: "COMPLETED" }, // duplicate: counted once
    { kind: "stage.FREEZE", status: "COMPLETED" },
    { kind: "stage.SYNTHESIZE", status: "ACTIVE" },
  ];
  // R470 (audit P1-1): the suffix now carries the last completed stage
  // in HUMAN language and the evidence count — derived from recorded
  // events only, never a total (the standing R464 rule).
  assert.equal(
    productEvents.stageProgressSuffix(events),
    " · step 3 — last completed: evidence freeze"
  );
});

test("P0-2: no ACTIVE stage event -> no suffix (never invented)", () => {
  assert.equal(
    productEvents.stageProgressSuffix([{ kind: "stage.RETRIEVE", status: "COMPLETED" }]),
    ""
  );
  assert.equal(productEvents.stageProgressSuffix([]), "");
  // a non-stage live event (problem.extract) carries no position
  assert.equal(
    productEvents.stageProgressSuffix([{ kind: "problem.extract", status: "ACTIVE" }]),
    ""
  );
});

test("P0-2: a paused (infra) live event carries no position", () => {
  const events = [
    { kind: "stage.RETRIEVE", status: "COMPLETED" },
    { kind: "stage.SYNTHESIZE", status: "FAILED_INFRASTRUCTURE" },
  ];
  assert.equal(productEvents.stageProgressSuffix(events), "");
});

test("P0-2: the suffix never states a total or a stage name", () => {
  const events = [
    { kind: "stage.RETRIEVE", status: "COMPLETED" },
    { kind: "stage.SYNTHESIZE", status: "ACTIVE" },
  ];
  const s = productEvents.stageProgressSuffix(events);
  assert.ok(!/of\s+\d+/i.test(s), "no 'of N' denominator (the pipeline length varies by run)");
  assert.ok(!/[A-Z_]{3,}/.test(s), "no machine stage vocabulary");
});

// ---------------------------------------------------------------------------
// P0-2 / P0-3 / P1-3 / P1-4 / P1-6 / P1-7 / P1-8 — source-level acceptance
// ---------------------------------------------------------------------------

test("P0-2: the landing states the duration at full visual weight", () => {
  const src = read("app/page.tsx");
  assert.ok(/data-hero-note/.test(src), "the duration note exists as its own block");
  assert.ok(/takes minutes, not seconds/.test(src), "the honest duration class is stated");
  // the 12.5px hint no longer buries the duration
  const hintMatch = src.match(/className="hint"[^<]*<\/span>|<span className="hint">([\s\S]*?)<\/span>/);
  assert.ok(hintMatch, "the keyboard hint still exists");
  assert.ok(!/runs take minutes/i.test(hintMatch[1] ?? ""), "the duration left the keyboard hint");
});

test("P0-3: the landing carries a concrete example outcome", () => {
  const src = read("app/page.tsx");
  assert.ok(/data-expect-card/.test(src), "the example card exists");
  assert.ok(/What a finished discovery looks like/.test(src), "the card is headed in product language");
  assert.ok(/technology package/.test(src), "the deliverable is named");
  assert.ok(/illustrative example/i.test(src), "the card labels itself an example — never a fake record");
});

test("P0-4: the accent text tokens exist and pass WCAG AA", () => {
  const css = read("app/globals.css");
  assert.ok(/--accent-text:\s*#a34d2e/.test(css), "the AA text token is defined");
  assert.ok(/--accent-deep:\s*#8f4220/.test(css), "the AA-on-tint token is defined");

  // compute the ratios here — evidence, not opinion
  const lum = (hex) => {
    const h = hex.replace("#", "");
    const [r, g, b] = [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16) / 255);
    const f = (c) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
  };
  const ratio = (a, b) => {
    const [la, lb] = [lum(a), lum(b)].sort((x, y) => y - x);
    return (la + 0.05) / (lb + 0.05);
  };
  assert.ok(ratio("#a34d2e", "#ffffff") >= 4.5, "accent-text on white");
  assert.ok(ratio("#a34d2e", "#faf9f5") >= 4.5, "accent-text on paper");
  assert.ok(ratio("#8f4220", "#e8ddd2") >= 4.5, "accent-deep on the soft tint");
  // the small-text contexts use the AA token, not the raw accent
  assert.ok(!/\.card \.kicker[^}]*color:\s*var\(--accent\)/.test(css));
  assert.ok(!/\.arg \.step \.k[^}]*color:\s*var\(--accent\)/.test(css));
  assert.ok(/\.card \.kicker[^}]*color:\s*var\(--accent-text\)/.test(css));
  assert.ok(/\.arg \.step \.k[^}]*color:\s*var\(--accent-text\)/.test(css));
});

test("P0-4: the dead 780px breakpoint is gone (CSS hygiene)", () => {
  const css = read("app/globals.css");
  assert.ok(!/@media\s*\(max-width:\s*780px\)\s*\{\s*\}/.test(css));
});

test("P1-3: a running run shows the calm steering note, not the chips", () => {
  const src = read("components/Conversation.tsx");
  assert.ok(/steerOpen = isTerminal\(detail\.status\)/.test(src), "chip visibility mirrors the engine's action gate");
  assert.ok(/data-conv-steer-locked/.test(src), "the locked state is observable in the DOM");
  assert.ok(/Steering opens when this investigation completes/.test(src), "the calm sentence exists");
});

test("P1-4: the workspace title is a real heading", () => {
  const src = read("components/Workspace.tsx");
  assert.ok(/<h2 className="wk-title">/.test(src));
  assert.ok(!/<span className="wk-title">/.test(src));
});

test("P1-6: the file input names what it accepts", () => {
  const src = read("app/page.tsx");
  assert.ok(/accept=\{UPLOAD_ACCEPT\}/.test(src), "the accept attribute is wired");
  assert.ok(/\.\s*pdf/.test(src) && /\.txt/.test(src) && /\.step/.test(src), "text, PDF, and CAD types are named");
  assert.ok(/20 MB/.test(src), "the size limit is stated up front");
  assert.ok(/data-attachment-stored/.test(src), "a stored-not-read file says so on its chip");
});

test("P1-7: the action note carries a dismissal", () => {
  const src = read("components/Conversation.tsx");
  assert.ok(/conv-action-dismiss/.test(src));
  assert.ok(/aria-label="dismiss this note"/.test(src));
});

test("P1-8: the capped rail states its count", () => {
  const src = read("components/Sidebar.tsx");
  assert.ok(/data-rail-see-all/.test(src), "the see-all affordance exists");
  assert.ok(/Show all \{sessions\.length\} discoveries/.test(src), "the real count is stated");
});

test("P0-1: the round structure is navigable both directions", () => {
  const src = read("app/page.tsx");
  assert.ok(/data-fork-note/.test(src) && /data-round=/.test(src), "the back-link names the round");
  assert.ok(/data-fork-fwd/.test(src), "a forked parent links forward to its newest round");
  assert.ok(/Round \$\{currentRound\}/.test(src), "the round number renders");
});

// ---------------------------------------------------------------------------
// P1-1 — the decisive experiment rides the conversation thread
// ---------------------------------------------------------------------------

function minimalDetail(over = {}) {
  return {
    session_id: "ts_test",
    title: "Test problem",
    user_text: "Why do the seals fail under cyclic load?",
    status: "COMPLETE",
    created_at: "2026-09-14T10:00:00Z",
    run_dir: null,
    problem_id: null,
    final_status: null,
    stages: [],
    user_state_view: {
      user_state: "COMPLETED_CANDIDATE",
      label: "A promising technology",
      meaning: "",
      decision: "The surviving candidate is presented with its honest maturity.",
      finished: true,
      found_something: true,
      rejected: false,
      package_available: false,
    },
    ...over,
  };
}

test("P1-1: a terminal run with an AVAILABLE experiment tab gets an in-thread card", () => {
  const dossier = { tabs: { experiment: { availability: "AVAILABLE" } } };
  const msgs = present.deriveConversation(minimalDetail(), dossier, false);
  const exp = msgs.find((m) => m.kind === "artifact" && m.surface === "experiment");
  assert.ok(exp, "the experiment artifact card renders in the conversation");
  assert.equal(exp.title, "The decisive experiment");
  assert.ok(/falsif/.test(exp.body), "the card states the falsification boundary");
});

test("P1-1: no experiment tab -> no card (honest absence)", () => {
  const msgs = present.deriveConversation(minimalDetail(), { tabs: {} }, false);
  assert.ok(!msgs.some((m) => m.kind === "artifact" && m.surface === "experiment"));
});

test("P1-1: a RUNNING run shows no experiment card (the record decides)", () => {
  const dossier = { tabs: { experiment: { availability: "AVAILABLE" } } };
  const detail = minimalDetail({ status: "RUNNING" });
  const msgs = present.deriveConversation(detail, dossier, false);
  assert.ok(!msgs.some((m) => m.kind === "artifact" && m.surface === "experiment"));
});

// ---------------------------------------------------------------------------
// P1-2 — rounds.ts: grouping, numbering, forward links
// ---------------------------------------------------------------------------

const S = (id, parent, at) => ({
  session_id: id,
  parent_session_id: parent ?? null,
  created_at: at,
  title: id,
});

test("P1-2: a child renders grouped under its parent, in thread order", () => {
  const visible = [
    S("r2", "r1", "2026-09-15T12:00:00Z"), // newer child first (recency list)
    S("r1", null, "2026-09-15T10:00:00Z"),
  ];
  const out = rounds.groupRounds(visible);
  assert.equal(out.map((r) => r.row.session_id).join(","), "r1,r2");
  assert.equal(out[0].grouped, false, "the parent anchors the thread");
  assert.equal(out[1].grouped, true, "the child is indented under it");
  assert.equal(out[1].round, 2, "the child carries its round number");
  assert.equal(out[0].round, 1);
});

test("P1-2: a grandchild chains (Round 3) after its own parent", () => {
  const visible = [
    S("r3", "r2", "2026-09-15T14:00:00Z"),
    S("r2", "r1", "2026-09-15T12:00:00Z"),
    S("r1", null, "2026-09-15T10:00:00Z"),
  ];
  const out = rounds.groupRounds(visible);
  assert.equal(out.map((r) => r.row.session_id).join(","), "r1,r2,r3");
  assert.equal(out[2].round, 3);
});

test("P1-2: an orphan child (parent not in view) stays visible, ungrouped", () => {
  const visible = [S("r5", "r0-missing", "2026-09-15T12:00:00Z")];
  const out = rounds.groupRounds(visible);
  assert.equal(out.length, 1);
  assert.equal(out[0].grouped, false);
  assert.equal(out[0].round, 2, "the unknown parent still counts as one step — a lower bound, never a guess");
});

test("P1-2: a corrupt parent cycle cannot spin the numbering", () => {
  const a = S("a", "b", "2026-09-15T10:00:00Z");
  const b = S("b", "a", "2026-09-15T11:00:00Z");
  const out = rounds.groupRounds([a, b]);
  assert.equal(out.length, 2, "both rows survive the cycle");
  const byId = new Map([a, b].map((r) => [r.session_id, r]));
  assert.ok(Number.isFinite(rounds.roundNumberOf(a, byId)));
});

test("P1-2: latestChildOf returns the newest child, or null honestly", () => {
  const rows = [S("r2", "r1", "2026-09-15T12:00:00Z"), S("r3", "r1", "2026-09-15T14:00:00Z")];
  assert.equal(rounds.latestChildOf("r1", rows).session_id, "r3");
  assert.equal(rounds.latestChildOf("r9", rows), null);
  assert.equal(rounds.latestChildOf(null, rows), null);
});
