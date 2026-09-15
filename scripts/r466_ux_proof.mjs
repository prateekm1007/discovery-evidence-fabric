#!/usr/bin/env node
// R466 — local UX proof for the two reaudit-closure changes.
// Serves the verified static export, then:
//   1. screenshots the landing at 1440px and 390px (the R464 pattern;
//      the ol/li change must not move a single pixel of the landing)
//   2. drives the WORKSPACE rail with synthetic session data by
//      intercepting /api/sessions — proving the <ol>/<li> rail renders
//      with identical visual structure (no bullets, no default margins)
//   3. collects console errors on every page (must be zero)
// Zero deps beyond puppeteer-core + the cache Chrome.
import { createRequire } from "node:module";
import http from "node:http";
import { createReadStream, existsSync, mkdirSync, statSync, readdirSync } from "node:fs";
import { join, extname, resolve } from "node:path";
import os from "node:os";

// this script lives at <repo>/scripts/; the webapp is its sibling tree
const REPO = resolve(new URL("..", import.meta.url).pathname);
const WEBAPP = resolve(REPO, "TOSCANINI_UI", "webapp");
const OUT = resolve(WEBAPP, "out");
const SHOTDIR = resolve(REPO, "R466");
const RENDERER = resolve(REPO, "discovery_fabric", "engine", "visual_compiler", "renderer");
const require2 = createRequire(resolve(RENDERER, "package.json"));
const puppeteer = require2("puppeteer-core");
mkdirSync(SHOTDIR, { recursive: true });

const MIME = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".json": "application/json", ".png": "image/png", ".svg": "image/svg+xml", ".glb": "model/gltf-binary", ".woff2": "font/woff2" };

const server = http.createServer((req, res) => {
  const url = new URL(req.url, "http://localhost");
  // the rail data intercept: synthetic history incl. a forked round
  if (url.pathname === "/api/sessions") {
    const rows = [
      { session_id: "ts_parent", title: "Pump cavitation at low flow", status: "COMPLETE", created_at: "2026-09-15T09:00:00Z", has_fork: true, parent_session_id: null, user_state_view: { user_state: "COMPLETED_CANDIDATE", label: "Complete" } },
      { session_id: "ts_child", title: "Pump cavitation at low flow", status: "RUNNING", created_at: "2026-09-15T09:30:00Z", has_fork: false, parent_session_id: "ts_parent", user_state_view: { user_state: "IN_PROGRESS", label: "In progress" } },
      { session_id: "ts_b", title: "Rail fracture under fatigue", status: "COMPLETE", created_at: "2026-09-14T08:00:00Z", user_state_view: { user_state: "COMPLETED_PACKAGE", label: "Complete" } },
      { session_id: "ts_c", title: "Battery thermal runaway", status: "COMPLETE", created_at: "2026-09-01T08:00:00Z", user_state_view: { user_state: "COMPLETED_EVOLVED", label: "Complete" } },
    ];
    res.writeHead(200, { "content-type": "application/json" });
    res.end(JSON.stringify({ sessions: rows, showcase: [
      { slot: "p07", title: "Rescue catheter", domain: "medical", demo_focus: true, blurb: "x" },
      { slot: "p24", title: "eShunt", domain: "medical", demo_focus: false, blurb: "y" },
    ] }));
    return;
  }
  if (url.pathname === "/api/health") {
    res.writeHead(200, { "content-type": "application/json" });
    res.end(JSON.stringify({ ok: true, status: "ok", engine_commit: "local-export-proof" }));
    return;
  }
  // the run-detail alias the workspace opens with
  if (url.pathname === "/api/run/ts_parent/result") {
    res.writeHead(200, { "content-type": "application/json" });
    res.end(JSON.stringify({
      session_id: "ts_parent", title: "Pump cavitation at low flow",
      user_text: "Why does the pump cavitate at low flow?",
      status: "COMPLETE", created_at: "2026-09-15T09:00:00Z",
      run_dir: null, problem_id: null, final_status: null,
      parent_session_id: null,
      user_state_view: { user_state: "COMPLETED_CANDIDATE", label: "Complete", finished: true },
      stages: [],
    }));
    return;
  }
  // the CHILD round — opened by a steering action; the directive rides
  // the DURABLE conversation record (user_directive cleared by the worker)
  if (url.pathname === "/api/run/ts_child/result") {
    res.writeHead(200, { "content-type": "application/json" });
    res.end(JSON.stringify({
      session_id: "ts_child", title: "Pump cavitation at low flow",
      user_text: "Why does the pump cavitate at low flow?",
      status: "COMPLETE", created_at: "2026-09-15T09:30:00Z",
      run_dir: null, problem_id: null, final_status: null,
      parent_session_id: "ts_parent",
      user_directive: {},
      conversation: [
        { role: "user", text: "[CHANGE_MECHANISM] try a different material for the impeller",
          classification: "directive", affects_canonical_state: false },
      ],
      user_state_view: { user_state: "COMPLETED_CANDIDATE", label: "Complete", finished: true },
      stages: [],
    }));
    return;
  }
  if (url.pathname.startsWith("/api/run/ts_child/events")) {
    res.writeHead(200, { "content-type": "application/json" });
    res.end(JSON.stringify({ events: [] }));
    return;
  }
  if (url.pathname.startsWith("/api/run/ts_child/")) {
    res.writeHead(200, { "content-type": "application/json" });
    res.end(JSON.stringify({}));
    return;
  }
  if (url.pathname.startsWith("/api/run/ts_parent/events")) {
    res.writeHead(200, { "content-type": "application/json" });
    res.end(JSON.stringify({ events: [] }));
    return;
  }
  if (url.pathname.startsWith("/api/run/ts_parent/")) {
    res.writeHead(200, { "content-type": "application/json" });
    res.end(JSON.stringify({}));
    return;
  }
  if (url.pathname.startsWith("/api/")) {
    res.writeHead(200, { "content-type": "application/json" });
    res.end(JSON.stringify({}));
    return;
  }
  let p = join(OUT, url.pathname);
  if (!existsSync(p) || statSync(p).isDirectory()) p = join(OUT, url.pathname === "/" ? "index.html" : url.pathname + "/index.html");
  if (!existsSync(p)) p = join(OUT, "index.html");
  res.writeHead(200, { "content-type": MIME[extname(p)] || "application/octet-stream" });
  createReadStream(p).pipe(res);
});
await new Promise((r) => server.listen(0, "127.0.0.1", r));
const port = server.address().port;

// chrome resolution: puppeteer cache layout <kind>/<version>/<dir>/<binary>
const cache = join(os.homedir(), ".cache", "puppeteer", "chrome-headless-shell");
const ver = readdirSync(cache)[0];
const inner = readdirSync(join(cache, ver))[0];
const bin = join(cache, ver, inner, "chrome-headless-shell");

const browser = await puppeteer.launch({
  executablePath: bin,
  args: ["--no-sandbox", "--disable-dev-shm-usage", "--force-device-scale-factor=1"],
});

const errors = [];
async function shot(width, height, path, name, waitMs = 1500) {
  const page = await browser.newPage();
  page.on("console", (m) => { if (m.type() === "error") errors.push(`${name}: ${m.text()}`); });
  page.on("pageerror", (e) => errors.push(`${name}: ${e.message}`));
  await page.setViewport({ width, height });
  await page.goto(`http://127.0.0.1:${port}${path}`, { waitUntil: "networkidle2", timeout: 30000 });
  await new Promise((r) => setTimeout(r, waitMs));
  await page.screenshot({ path: join(SHOTDIR, name) });
  return page;
}

// 1 — the landing at both widths (unchanged by construction)
await shot(1440, 900, "/", "ux_landing_desktop_1440.png");
await shot(390, 844, "/", "ux_landing_mobile_390.png");

// 2 — the workspace rail with the semantic lists (opens with a run id;
// the static export renders the shell + rail with intercepted data)
const ws = await shot(1440, 900, "/?run=ts_parent", "ux_workspace_rail_1440.png", 2500);
const railAudit = await ws.evaluate(() => {
  const ol = document.querySelector(".rail-list");
  const lis = ol ? [...ol.querySelectorAll(":scope > li")] : [];
  const liStyle = lis[0] ? getComputedStyle(lis[0]) : null;
  const btn = ol ? ol.querySelector("button.rail-item") : null;
  return {
    olCount: document.querySelectorAll(".rail-list").length,
    firstOlChildren: ol ? ol.children.length : 0,
    liCount: lis.length,
    listStyle: liStyle ? liStyle.listStyleType : null,
    liMargin: liStyle ? liStyle.margin : null,
    buttonInsideLi: btn ? !!btn.closest("li") : false,
  };
});
console.log("RAIL_AUDIT " + JSON.stringify(railAudit));

// 3 — the CHILD round: the in-thread continuation card + the durable
// directive bubble (user_directive is {} — the worker already consumed it)
const child = await shot(1440, 900, "/?run=ts_child", "ux_child_continuation_1440.png", 2500);
const cardAudit = await child.evaluate(() => {
  const card = document.querySelector("[data-continued-card]");
  const bubble = [...document.querySelectorAll(".conv-user-bubble")]
    .map((b) => b.textContent.trim());
  return {
    cardPresent: !!card,
    cardRound: card ? card.getAttribute("data-round") : null,
    cardText: card ? card.textContent.replace(/\s+/g, " ").trim() : null,
    userBubbles: bubble,
  };
});
console.log("CARD_AUDIT " + JSON.stringify(cardAudit));

await browser.close();
server.close();
console.log("CONSOLE_ERRORS " + JSON.stringify(errors));
console.log("SHOTS -> " + SHOTDIR);
process.exit(0);
