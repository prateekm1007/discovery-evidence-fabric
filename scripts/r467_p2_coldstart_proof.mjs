#!/usr/bin/env node
// R467 — the P2 behavioral proof (the R466 disclosed store cold-start
// 404 window, closed): the LOCAL static export driven through a stub
// API that reproduces the observed cold-start sequence —
//   phase 1 (cold): /api/health FAILS, /api/run/{id}/result answers
//   the enumeration-safe 404 (the host edge answering for a starting
//   process; observed live twice in R466);
//   phase 2 (warm): health answers ok:true, the run resolves 200.
// The OLD code graded the phase-1 404s toward "Run not found" (4
// misses ~= 10 s). The FIXED code holds the engine-proven-healthy
// marker false while health fails, so the same 404s surface the
// connection-lost copy (persisted, recovering, no verdict) — and the
// standing 4-miss rule still fires for a GENUINELY absent run once
// the engine is healthy (the control arm).
import { createServer } from "node:http";
import { resolve, extname } from "node:path";
import { readFileSync, existsSync, readdirSync, mkdirSync } from "node:fs";
import os from "node:os";
import { createRequire } from "node:module";

const WEBAPP = "/home/z/my-project/repos/discovery-evidence-fabric/TOSCANINI_UI/webapp";
const OUT = resolve(WEBAPP, "out");
const grequire = createRequire(resolve(os.homedir(), ".npm-global",
  "lib", "node_modules", "playwright", "package.json"));
const { chromium } = grequire("playwright");

const RUN_ID = "ts_r467_p2_proof";
const RUN_DETAIL = {
  session_id: RUN_ID,
  title: "Cold-start recovery proof",
  status: "COMPLETE",
  created_at: new Date().toISOString(),
  problem: { title: "proof problem", failure_mode: "none", domain: "thermal" },
};

// ---- the stub API + static export server -------------------------------
let warm = false;          // phase flag: cold -> warm
let servedDetail = false;
const MIME = { ".html": "text/html", ".js": "text/javascript",
               ".css": "text/css", ".svg": "image/svg+xml",
               ".png": "image/png", ".json": "application/json" };
const srv = createServer((req, res) => {
  const url = req.url.split("?")[0];
  if (url === "/api/health") {
    if (!warm) { res.writeHead(503); res.end("starting"); return; }
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ ok: true, discovery_ready: true }));
    return;
  }
  if (url === `/api/run/${RUN_ID}/result`) {
    if (!warm) { res.writeHead(404,
      { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "not found" })); return; }
    servedDetail = true;
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify(RUN_DETAIL));
    return;
  }
  if (url === "/api/sessions") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ sessions: warm ? [{
      session_id: RUN_ID, title: RUN_DETAIL.title,
      status: "COMPLETE", created_at: RUN_DETAIL.created_at }] : [] }));
    return;
  }
  if (url === "/api/events") { res.writeHead(200,
    { "Content-Type": "application/json" });
    res.end(JSON.stringify({ events: [], gauntlet: [] })); return; }
  // static export
  let p = url.endsWith("/") ? url + "index.html" : url;
  let file = resolve(OUT, "." + p);
  if (!existsSync(file) && existsSync(resolve(OUT, "." + url, "index.html")))
    file = resolve(OUT, "." + url, "index.html");
  if (!existsSync(file)) { res.writeHead(404); res.end("no file"); return; }
  res.writeHead(200, { "Content-Type":
    MIME[extname(file)] || "application/octet-stream" });
  res.end(readFileSync(file));
});
await new Promise((r) => srv.listen(0, "127.0.0.1", r));
const port = srv.address().port;
const BASE = `http://127.0.0.1:${port}`;

// ---- the browser drive --------------------------------------------------
const cache = resolve(os.homedir(), ".cache", "puppeteer", "chrome");
const ver = readdirSync(cache)[0];
const bin = resolve(cache, ver, readdirSync(resolve(cache, ver))[0], "chrome");
const browser = await chromium.launch({
  executablePath: bin,
  args: ["--no-sandbox", "--disable-dev-shm-usage"] });
const page = await browser.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(String(e.message).slice(0, 120)));
await page.setViewportSize({ width: 1280, height: 900 });

const results = {};

// PHASE 1 (cold, 16 s > the old 4-miss window): the 404s must NOT
// produce "Run not found" — the connection-lost copy is the honest
// state while the engine is unproven.
await page.goto(`${BASE}/?run=${RUN_ID}`, { waitUntil: "domcontentloaded" });
await new Promise((r) => setTimeout(r, 16000));
results.cold = await page.evaluate(() => ({
  runNotFound: !!Array.from(document.querySelectorAll("b"))
    .find((b) => b.textContent.includes("Run not found")),
  connLost: !!document.querySelector("[data-conn-lost]"),
  bodyHasLoading: !!document.querySelector(".loading"),
}));

// PHASE 2 (warm): health flips ok:true; the run resolves; the view
// renders the run (recovery — the R466 observed poll recovery).
warm = true;
await new Promise((r) => setTimeout(r, 8000));
results.warm = await page.evaluate(() => ({
  runNotFound: !!Array.from(document.querySelectorAll("b"))
    .find((b) => b.textContent.includes("Run not found")),
  connLost: !!document.querySelector("[data-conn-lost]"),
  title: document.body.textContent.includes("Cold-start recovery proof"),
}));
await page.screenshot({ path: resolve(WEBAPP, "..", "..", "R467",
  "ux_p2_coldstart_recovery_1280.png") });

// CONTROL ARM: a genuinely absent run WITH the engine healthy — the
// standing 4-miss rule must still fire (the fix narrows the cold-start
// window ONLY; it never weakens the real verdict).
const page2 = await browser.newPage();
await page2.setViewportSize({ width: 1280, height: 900 });
await page2.goto(`${BASE}/?run=ts_genuinely_absent_0000`,
  { waitUntil: "domcontentloaded" });
await new Promise((r) => setTimeout(r, 14000));
results.control = await page2.evaluate(() => ({
  runNotFound: !!Array.from(document.querySelectorAll("b"))
    .find((b) => b.textContent.includes("Run not found")),
}));
// ---- the verdict ---------------------------------------------------------
results.pass = {
  cold_no_false_not_found: results.cold.runNotFound === false,
  cold_conn_lost_or_loading:
    results.cold.connLost === true || results.cold.bodyHasLoading === true,
  warm_recovered: results.warm.runNotFound === false
    && results.warm.connLost === false && results.warm.title === true,
  control_still_fires: results.control.runNotFound === true,
  no_page_errors: errors.length === 0,
};
console.log(JSON.stringify({ results, page_errors: errors }, null, 1));
const allOk = Object.values(results.pass).every(Boolean);
console.log(allOk ? "P2 PROOF: PASS" : "P2 PROOF: FAIL");
await browser.close();
srv.close();
process.exit(allOk ? 0 : 1);
