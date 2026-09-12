/* R450-C2: render the lab trajectory route with the repo's own renderer
 * family (headless Chromium + the webapp's served HTML) and capture
 * full-page screenshots + a DOM-presence report, as fresh UI evidence
 * that the trajectory is rendered and understandable. */
const puppeteer = require('/home/z/my-project/hf_space/renderer/node_modules/puppeteer-core');

(async () => {
  const browser = await puppeteer.launch({
    executablePath: '/home/z/.agent-browser/browsers/chrome-152.0.7977.64/chrome',
    args: ['--no-sandbox', '--disable-gpu', '--single-process', '--no-zygote'],
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1100, height: 1400 });
  await page.goto('http://localhost:3000/lab/trajectory', { waitUntil: 'networkidle0', timeout: 60000 });

  const report = await page.evaluate(() => {
    const q = (s) => document.querySelector(s);
    const qa = (s) => Array.from(document.querySelectorAll(s));
    return {
      trajectory_viewer_present: !!q('[data-trajectory-viewer]'),
      states: qa('[data-traj-state]').map((n) => n.getAttribute('data-traj-status')),
      transitions: qa('[data-traj-transition]').length,
      badges: qa('[data-badge]').map((n) => n.getAttribute('data-badge')),
      uncertainty_labels: qa('[data-uncertainty-label]').map((n) => n.textContent.trim()),
      before_after_delta_tables: qa('[data-before-after-delta]').length,
      causal_stages: qa('[data-causal-stage]').map((n) => n.getAttribute('data-causal-stage')),
      prediction_outcomes: qa('[data-prediction-outcome]').map((n) => n.getAttribute('data-prediction-outcome')),
      sensitivity_panel: !!q('[data-sensitivity-panel]'),
      sensitivity_points: qa('[data-sensitivity-point]').length,
      badge_legend: !!q('[data-badge-legend]'),
      lab_banner: (q('.pill.RUNNING') || {}).textContent || null,
    };
  });
  console.log(JSON.stringify(report, null, 1));

  await page.screenshot({ path: '/tmp/r450_lab_trajectory_full.png', fullPage: true });
  await browser.close();
  console.log('screenshot saved: /tmp/r450_lab_trajectory_full.png');
})().catch((e) => { console.error('RENDER FAILED:', e.message); process.exit(1); });
