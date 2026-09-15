#!/usr/bin/env node
// R466 — LCP timeline probe: when does the hero-note actually paint?
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
const bin = joinDir(cache, ver);
function joinDir(a, b) {
  const inner = readdirSync(resolve(a, b))[0];
  return resolve(a, b, inner, "chrome");
}

const url = process.argv[2] || "http://127.0.0.1:8124/";
const browser = await puppeteer.launch({ executablePath: bin, args: ["--no-sandbox", "--disable-dev-shm-usage"] });
const page = await browser.newPage();
const client = await page.createCDPSession();
await client.send("Emulation.setCPUThrottlingRate", { rate: 4 });
await client.send("Network.enable");
await client.send("Network.emulateNetworkConditions", {
  offline: false, latency: 150, downloadThroughput: (1.6 * 1024 * 1024) / 8, uploadThroughput: (750 * 1024) / 8,
});
await page.evaluateOnNewDocument(() => {
  window.__lcps = [];
  try {
    new PerformanceObserver((l) => {
      for (const e of l.getEntries()) window.__lcps.push({ t: Math.round(e.startTime), size: e.size, tag: e.element ? e.element.tagName + "." + (e.element.className || "") : "?" });
    }).observe({ type: "largest-contentful-paint", buffered: true });
  } catch (e) {}
});
await page.goto(url, { waitUntil: "load", timeout: 60000 });
await new Promise((r) => setTimeout(r, 6000));
const lcps = await page.evaluate(() => window.__lcps);
console.log(JSON.stringify(lcps, null, 1));
await browser.close();
