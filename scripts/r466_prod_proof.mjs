#!/usr/bin/env node
// R466 — PRODUCTION UX proof: the deployed landing (prerendered hero +
// new CTA fill) and the real child round (in-thread continuation card +
// the steering words from the durable record while user_directive={}).
import { createRequire } from "node:module";
import { resolve } from "node:path";
import { readFileSync } from "node:fs";
const REPO = "/home/z/my-project/hf_space";
const RENDERER = resolve(REPO, "discovery_fabric", "engine", "visual_compiler", "renderer");
const require2 = createRequire(resolve(RENDERER, "package.json"));
const puppeteer = require2("puppeteer-core");
import { readdirSync, mkdirSync } from "node:fs";
import os from "node:os";

const st = JSON.parse(readFileSync(resolve(REPO, "R466", "RUNS", "driver_state.json"), "utf8"));
const child = st.runs.irrigation_child;
const BASE = "https://prateekm1-toscanini-prod-validation.hf.space";
const SHOTDIR = resolve(REPO, "R466");
mkdirSync(SHOTDIR, { recursive: true });

const cache = resolve(os.homedir(), ".cache", "puppeteer", "chrome");
const ver = readdirSync(cache)[0];
const inner = readdirSync(resolve(cache, ver))[0];
const bin = resolve(cache, ver, inner, "chrome");

const browser = await puppeteer.launch({ executablePath: bin, args: ["--no-sandbox", "--disable-dev-shm-usage", "--force-device-scale-factor=1"] });
const errors = [];

// 1 — the production landing, mobile + desktop
for (const [w, h, name] of [[390, 844, "ux_prod_landing_mobile_390.png"], [1440, 900, "ux_prod_landing_desktop_1440.png"]]) {
  const page = await browser.newPage();
  page.on("console", (m) => { if (m.type() === "error") errors.push(`${name}: ${m.text().slice(0, 120)}`); });
  page.on("pageerror", (e) => errors.push(`${name}: ${e.message.slice(0, 120)}`));
  await page.setViewport({ width: w, height: h });
  await page.goto(BASE + "/", { waitUntil: "networkidle2", timeout: 60000 });
  await new Promise((r) => setTimeout(r, 2500));
  await page.screenshot({ path: resolve(SHOTDIR, name) });
  await page.close();
}

// 2 — the real child round: the owner capability rides localStorage
// (the client's own transport — apiFetch attaches it as the header).
// evaluateOnNewDocument seeds it BEFORE any page script runs — the
// app's first /api/sessions then echoes the same key back (the server
// returns the caller's own capability) and the seed survives.
const page = await browser.newPage();
page.on("console", (m) => { if (m.type() === "error") errors.push(`child: ${m.text().slice(0, 120)}`); });
page.on("pageerror", (e) => errors.push(`child: ${e.message.slice(0, 120)}`));
await page.evaluateOnNewDocument(
  (k) => localStorage.setItem("tosca_owner_key", k),
  child.owner
);
await page.setViewport({ width: 1440, height: 900 });
await page.goto(`${BASE}/?run=${child.session_id}`, { waitUntil: "networkidle2", timeout: 60000 });
await new Promise((r) => setTimeout(r, 3500));
const audit = await page.evaluate(() => {
  const card = document.querySelector("[data-continued-card]");
  return {
    cardPresent: !!card,
    cardText: card ? card.textContent.replace(/\s+/g, " ").trim() : null,
    bubbles: [...document.querySelectorAll(".conv-user-bubble")].map((b) => b.textContent.trim()),
    forkRow: document.querySelector("[data-fork-note]")?.textContent?.replace(/\s+/g, " ").trim() ?? null,
    railOl: document.querySelectorAll(".rail-list").length,
  };
});
console.log("PROD_CARD_AUDIT " + JSON.stringify(audit));
await page.screenshot({ path: resolve(SHOTDIR, "ux_prod_child_continuation_1440.png") });
await browser.close();
console.log("CONSOLE_ERRORS " + JSON.stringify(errors));
process.exit(0);
