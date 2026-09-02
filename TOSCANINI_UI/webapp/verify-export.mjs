#!/usr/bin/env node
// R393 (CEO directive 2): mechanical build assertion. A deployment cannot
// be considered valid if CSS/JS assets are missing. Wired into the Docker
// build right after the static export — a failed assertion MUST abort the
// image build.
//
// Why this exists: the webapp shipped R389→R392 with globals.css present
// but imported by nothing. The static export contained ZERO CSS (no
// <link rel="stylesheet"> in any page, no _next/static/css/ directory) and
// the public deployment rendered as browser-default HTML. The health
// endpoint was green the whole time — readiness never measured assets.
// This script makes the regression mechanically impossible to ship.
//
// Checks:
//   1. every expected page shell exists and is non-empty
//   2. at least one non-empty CSS file under _next/static/css/
//   3. at least three JS chunks under _next/static/chunks/
//   4. every page references at least one stylesheet
//   5. every /_next/... href/src in every page resolves to a real file
//
// Exit 0 = export valid. Exit 1 = deployment MUST NOT proceed.

import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";

const outDir = process.argv[2] || "out";
const errors = [];
const notes = [];

function must(cond, msg) {
  if (!cond) errors.push(msg);
}

// --- 1. page shells ------------------------------------------------------
const PAGES = ["index.html", "run/index.html", "showcase/index.html"];
for (const p of PAGES) {
  const f = join(outDir, p);
  if (!existsSync(f)) {
    errors.push(`MISSING PAGE: ${p}`);
    continue;
  }
  const size = statSync(f).size;
  must(size > 500, `SUSPICIOUSLY SMALL PAGE: ${p} (${size} bytes)`);
  notes.push(`${p}: ${size}B`);
}

// --- 2. CSS must exist ----------------------------------------------------
const cssDir = join(outDir, "_next", "static", "css");
let cssFiles = [];
if (existsSync(cssDir)) {
  cssFiles = readdirSync(cssDir).filter((n) => n.endsWith(".css"));
}
must(
  cssFiles.length > 0,
  `NO CSS IN EXPORT: _next/static/css/ has ${cssFiles.length} files — ` +
    `the design system is not reaching the browser (this exact defect ` +
    `shipped the public deployment unstyled)`
);
for (const c of cssFiles) {
  const f = join(cssDir, c);
  must(
    statSync(f).size > 200,
    `SUSPICIOUSLY SMALL CSS: ${c} (${statSync(f).size}B)`
  );
  notes.push(`css/${c}: ${statSync(f).size}B`);
}

// --- 3. JS chunks must exist ---------------------------------------------
const chunkDir = join(outDir, "_next", "static", "chunks");
let jsFiles = [];
if (existsSync(chunkDir)) {
  jsFiles = readdirSync(chunkDir).filter((n) => n.endsWith(".js"));
}
must(
  jsFiles.length >= 3,
  `TOO FEW JS CHUNKS: expected >= 3, found ${jsFiles.length}`
);
notes.push(`js chunks: ${jsFiles.length}`);

// --- 4 + 5. every page references a stylesheet and resolves all assets ---
const assetRef = /(?:href|src)="(\/[^"]+)"/g;
for (const p of PAGES) {
  const f = join(outDir, p);
  if (!existsSync(f)) continue; // already errored above
  const html = readFileSync(f, "utf8");
  must(
    /<link[^>]+rel="stylesheet"/.test(html),
    `PAGE HAS NO STYLESHEET LINK: ${p} — it will render as browser-default HTML`
  );
  let m;
  let refs = 0;
  while ((m = assetRef.exec(html)) !== null) {
    const url = m[1];
    if (!url.startsWith("/_next/")) continue;
    refs++;
    const target = join(outDir, url.slice(1));
    if (!existsSync(target)) {
      errors.push(`BROKEN ASSET REF in ${p}: ${url} (file not in export)`);
    }
  }
  must(refs > 0, `PAGE REFERENCES NO _next ASSETS: ${p}`);
}

// --- verdict ---------------------------------------------------------------
if (errors.length > 0) {
  console.error("EXPORT VERIFICATION FAILED — deployment MUST NOT proceed:");
  for (const e of errors) console.error("  ✗ " + e);
  process.exit(1);
}
console.log("EXPORT VERIFICATION PASSED:");
for (const n of notes) console.log("  ✓ " + n);
