// adversarial_r477.test.mjs — the audit-response closure round, executed
// as code. Scope: the two surgically-open items the deployed R476 tree
// left + the honest-record pins for the deferred items.
//
//   (1) MOBILE — the composer occlusion risk is closed with the standard
//       safe-area mechanics: env(safe-area-inset-bottom, 0px) fallbacks
//       inside calc() on the composer, its note row, and the mobile
//       conversation clearance. The old bare rules are GONE.
//   (2) PERF — the drei optimizePackageImports attempt was MEASURED
//       (baseline 2115.2 KB chunks -> 2115.4 KB with the flag: no gain,
//       top chunks byte-identical) and REVERTED per Art. XVI/LXIV (no
//       non-executing config accumulates). The real perf structure is
//       pinned instead: ModelViewer behind next/dynamic in BOTH mounts,
//       First Load JS stays lean, ContactShadows at 512.
//   (3) DEFERRED-WITH-REASON pins (the audit's remaining deductions,
//       answered as recorded decisions, not silence):
//       - cache: "no-store" stays BY DESIGN (run state is never stale).
//       - the workspace panel stays NON-MODAL (the R476 decision: no
//         focus-trap dependency; Escape closes; focus-on-open).

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const webapp = path.resolve(here, "..");
const read = (rel) => readFileSync(path.join(webapp, rel), "utf8");

const css = read("app/globals.css");
const nextConfig = read("next.config.mjs");
const workspace = read("components/Workspace.tsx");
const stage = read("components/InventionStage.tsx");
const api = read("lib/api.ts");

// ---- (1) MOBILE: composer safe-area + occlusion clearance ---------------

test("R477: the mobile composer lifts off the home indicator (calc + env with fallback)", () => {
  assert.match(
    css,
    /\.conv-composer\s*\{\s*bottom:\s*calc\(8px\s*\+\s*env\(safe-area-inset-bottom,\s*0px\)\);?\s*\}/
  );
});

test("R477: the composer note row carries the same inset (the pill+note stack clears)", () => {
  assert.match(
    css,
    /\.conv-composer-note\s*\{\s*padding:\s*0 6px calc\(2px\s*\+\s*env\(safe-area-inset-bottom,\s*0px\)\);?\s*\}/
  );
});

test("R477: the 1180px conversation clearance is safe-area aware", () => {
  assert.match(
    css,
    /\.conv\s*\{\s*padding-bottom:\s*calc\(24px\s*\+\s*env\(safe-area-inset-bottom,\s*0px\)\);?\s*\}/
  );
});

test("R477: the OLD bare mobile rules are gone (no un-lifted composer path)", () => {
  // the 880px block previously carried `bottom: 8px` bare; the 1180px
  // block previously carried `padding-bottom: 20px` bare
  assert.doesNotMatch(css, /\.conv-composer\s*\{\s*bottom:\s*8px;?\s*\}/);
  assert.doesNotMatch(css, /\.conv\s*\{\s*padding-bottom:\s*20px;?\s*\}/);
});

test("R477: every env() in the sheet has the 0px fallback (no invalid-at-parse risk)", () => {
  const uses = css.match(/env\(safe-area-inset-bottom[^)]*\)/g) ?? [];
  assert.ok(uses.length >= 3, `expected >=3 env() uses, got ${uses.length}`);
  for (const u of uses) {
    assert.match(u, /,\s*0px\)/, `env() without fallback: ${u}`);
  }
});

test("R477: the bottom-sheet mechanics are untouched (no drive-by damage)", () => {
  assert.match(css, /max-height:\s*78vh/);
  assert.match(css, /transform:\s*translateY\(105%\)/);
  assert.match(css, /\.ws-panel\.open \.wk\s*\{\s*transform:\s*translateY\(0\)/);
});

// ---- (2) PERF: the measured revert + the real structure -----------------

test("R477: the no-gain optimizePackageImports flag is NOT in the config (measured, reverted)", () => {
  assert.doesNotMatch(nextConfig, /optimizePackageImports/);
});

test("R477: the canonical config lines survived the round byte-identical", () => {
  assert.match(nextConfig, /ENGINE_API\s*=\s*process\.env\.ENGINE_API\s*\|\|\s*"http:\/\/127\.0\.0\.1:8788"/);
  assert.match(nextConfig, /EXPORT\s*\?\s*\{\s*output:\s*"export",\s*trailingSlash:\s*true\s*\}\s*:\s*\{\}/);
});

test("R477: ModelViewer stays behind next/dynamic at BOTH mounts (three.js rides the async chunk)", () => {
  assert.match(workspace, /dynamic\(\(\)\s*=>\s*import\("\.\/ModelViewer"\)/);
  assert.match(stage, /dynamic\(\(\)\s*=>\s*import\("\.\/ModelViewer"\)/);
});

test("R477: ContactShadows stays at 512 (the R476 landing holds)", () => {
  const viewer = read("components/ModelViewer.tsx");
  assert.match(viewer, /resolution=\{512\}/);
  assert.doesNotMatch(viewer, /resolution=\{1024\}/);
});

// ---- (3) DEFERRED-WITH-REASON pins ---------------------------------------

test("R477: cache stays no-store BY DESIGN (run state is never stale) — the recorded decision", () => {
  assert.match(api, /cache:\s*"no-store"/);
});

test("R477: the workspace panel stays NON-MODAL (R476 decision: no focus-trap, Escape closes)", () => {
  // the R476 pin shape: no focus-trap import/usage — the token may
  // appear in the comment that records the deliberate decision
  assert.doesNotMatch(workspace, /from ["']focus-trap|createFocusTrap|useFocusTrap|focus-trap-react/i);
  assert.match(workspace, /Deliberately NOT a focus-trap/);
  assert.match(workspace, /if \(e\.key === "Escape"\) onClose\(\)/);
});
