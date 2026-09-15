#!/usr/bin/env node
// R466 — does the hero-note DOM node survive hydration, or is it replaced?
import { createRequire } from "node:module";
import { resolve } from "node:path";
const REPO = "/home/z/my-project/hf_space";
const RENDERER = resolve(REPO, "discovery_fabric", "engine", "visual_compiler", "renderer");
const require2 = createRequire(resolve(RENDERER, "package.json"));
const puppeteer = require2("puppeteer-core");
import { readdirSync } from "node:fs";
import os from "node:os";

const cache = resolve(os.homedir(), ".cache", "puppeteer", "chrome");
const ver = readdirSync(cache)[0];
const inner = readdirSync(resolve(cache, ver))[0];
const bin = resolve(cache, ver, inner, "chrome");

const url = process.argv[2] || "http://127.0.0.1:8124/";
const browser = await puppeteer.launch({ executablePath: bin, args: ["--no-sandbox", "--disable-dev-shm-usage"] });
const page = await browser.newPage();
const client = await page.createCDPSession();
await client.send("Emulation.setCPUThrottlingRate", { rate: 4 });
page.on("console", (m) => { if (/hydration|hydrat|mismatch/i.test(m.text())) console.log("CONSOLE:", m.text().slice(0, 300)); });
await page.evaluateOnNewDocument(() => {
  window.__firstHero = null;
  window.__replaced = null;
  const mo = new MutationObserver(() => {
    const el = document.querySelector(".hero-note");
    if (el && !window.__firstHero) {
      window.__firstHero = el;
    } else if (el && window.__firstHero && el !== window.__firstHero && !window.__replaced) {
      window.__replaced = performance.now();
    }
  });
  mo.observe(document.documentElement, { childList: true, subtree: true });
});
await page.goto(url, { waitUntil: "load", timeout: 60000 });
await new Promise((r) => setTimeout(r, 6000));
const out = await page.evaluate(() => ({
  firstSeen: !!window.__firstHero,
  replaced: window.__replaced,
  sameNode: window.__firstHero === document.querySelector(".hero-note"),
}));
console.log(JSON.stringify(out));
await browser.close();
