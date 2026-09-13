#!/usr/bin/env python3
"""R451-C2 Step 8 - the trajectory handoff builder (canonical bytes -> viewer).

Builds the trajectory viewer artifact from a canonical INVENTION_LINEAGE
record:

  Coder 1 canonical lineage bytes
        -> Coder 2 projection (visual-lab/trajectory/lineage_projection.py)
        -> web viewer (self-contained HTML + the projection JSON)

The viewer is a PROJECTION, never a second truth store: the artifact records
the sha256 of the exact canonical bytes it was built from, every displayed
value carries its JSON pointer into the canonical record, and rebuilding
always re-derives everything from the bytes.

Portable (directive step 4): paths come from CLI arguments; defaults are
derived from the lineage file's own location - never from an author-machine
directory. Works from any cwd and in a fresh clone.

Usage:
  python3 visual-lab/trajectory/build_trajectory_view.py \
      --lineage R445/EVOLUTION_RUNS/evol-x01-desalination-scaling/INVENTION_LINEAGE.json \
      [--html OUT.html] [--json OUT.json]

Fail closed: a record that fails a binding proof builds a REJECTED viewer
that renders the typed rejections and NEVER renders invented trajectory data.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import lineage_projection as lp  # noqa: E402

_VIEWER_TITLE = "Toscanini Trajectory Viewer (projection of the canonical lineage)"


def _viewer_html(payload: dict) -> str:
    embedded = json.dumps(payload, ensure_ascii=False, indent=2).replace(
        "</", "<\\/"
    )
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>__TITLE__</title>
<style>
  :root { color-scheme: light dark; }
  body { font-family: ui-sans-serif, system-ui, sans-serif; margin: 0;
         background: #14161a; color: #e8e6e1; }
  header { padding: 20px 28px; border-bottom: 1px solid #2a2e35; }
  header h1 { font-size: 17px; margin: 0 0 4px; font-weight: 600; }
  header .sub { font-size: 12.5px; color: #9aa3ad; }
  main { padding: 20px 28px 48px; max-width: 1080px; margin: 0 auto; }
  .hash { font-family: ui-monospace, monospace; font-size: 12px;
          color: #7fb5a3; word-break: break-all; }
  .boundary { border: 1px solid #3a3f47; background: #1b1e23;
              border-radius: 8px; padding: 12px 16px; margin: 14px 0 26px;
              font-size: 12.5px; color: #b9c2cc; }
  .boundary b { color: #e8e6e1; }
  .rejected { border: 1px solid #8a3a3a; background: #2a1717; color: #f2c4c4;
              border-radius: 8px; padding: 16px 18px; margin: 18px 0;
              font-family: ui-monospace, monospace; font-size: 12.5px; }
  .lane { display: flex; gap: 0; align-items: stretch; flex-wrap: wrap;
          margin: 8px 0 22px; }
  .state { flex: 1 1 300px; border: 1px solid #3a3f47; border-radius: 10px;
           margin: 8px; padding: 14px 16px; background: #1b1e23;
           min-width: 280px; }
  .state h2 { font-size: 13.5px; margin: 0 0 2px; }
  .gen { font-size: 11px; letter-spacing: .08em; color: #8f98a3;
         text-transform: uppercase; }
  .badge { display: inline-block; font-size: 10.5px; font-weight: 700;
           letter-spacing: .06em; padding: 3px 9px; border-radius: 999px;
           margin: 7px 0; border: 1px solid #4a5160; color: #d7dee7; }
  .badge.PROPOSED { border-color: #6b7bd6; color: #b7c0f2; }
  .badge.INFERRED { border-color: #3d8f6f; color: #9fd9c2; }
  .badge.SIMULATED { border-color: #b28f3d; color: #ecd9a8; }
  .badge.UNVERIFIED { border-color: #8a5a3a; color: #e8b898; }
  .badge.MEASURED { border-color: #3d8f8f; color: #9fe0e0; }
  .field { margin: 8px 0; font-size: 12.5px; line-height: 1.45; }
  .field .k { color: #8f98a3; font-size: 11px; display: block; }
  .field .ptr { font-family: ui-monospace, monospace; font-size: 10.5px;
                color: #6f7883; word-break: break-all; }
  .absent { color: #c9a36b; font-style: italic; }
  .arrow { align-self: center; text-align: center; font-size: 11px;
           color: #8f98a3; padding: 0 6px; min-width: 120px; }
  .arrow .binding { font-family: ui-monospace, monospace; font-size: 10px;
                    color: #6f7883; margin-top: 4px; white-space: pre; }
  .current { border: 1px solid #3d5a3f; background: #18211a; }
  footer { padding: 18px 28px 40px; font-size: 11.5px; color: #6f7883; }
</style>
</head>
<body>
<header>
  <h1>__TITLE__</h1>
  <div class="sub">source <span class="hash" id="src-hash"></span></div>
</header>
<main>
  <div class="boundary" id="boundary"></div>
  <div id="content"></div>
</main>
<footer>
  This viewer is a projection of Coder 1's canonical INVENTION_LINEAGE
  record and holds no independent state. Rebuilding re-derives every value
  from the canonical bytes. The visual layer does not decide why the engine
  failed, what caused the improvement, whether the mechanism is true, or
  whether an invention is novel.
</footer>
<script type="application/json" id="projection">__EMBEDDED__</script>
<script>
  const P = JSON.parse(document.getElementById('projection').textContent
                       .replace(/<\\\\\\//g, '</'));
  document.getElementById('src-hash').textContent =
    (P.source && P.source.sha256 ? P.source.sha256 : '(unknown)');

  function esc(s) { const d = document.createElement('div');
                    d.textContent = String(s); return d.innerHTML; }

  function fieldHTML(entry, label) {
    if (entry.status === 'RECORDED') {
      return '<div class="field"><span class="k">' + esc(label) +
        ' <span class="ptr">' + esc(entry.pointer) + '</span></span>' +
        esc(entry.value) + '</div>';
    }
    return '<div class="field absent"><span class="k">' + esc(label) +
      ' <span class="ptr">' + esc(entry.pointer) + '</span></span>' +
      esc(entry.status) + '</div>';
  }

  if (P.verdict === 'REJECTED') {
    document.getElementById('content').innerHTML =
      '<div class="rejected"><b>PROJECTION REJECTED</b> - the source record ' +
      'failed a binding proof; no trajectory is rendered (fail closed).<br>' +
      P.rejections.map(r => esc(r.code) + ' @ ' + esc(r.pointer) + ' - ' +
      esc(r.detail)).join('<br>') + '</div>';
  } else {
    const vs = P.viewer_state;
    document.getElementById('boundary').innerHTML =
      '<b>Presentation boundary.</b> Canonical authority: ' +
      esc(vs.presentation_boundary.canonical_authority) + '. The viewer may ' +
      'show: ' + esc(vs.presentation_boundary.this_viewer_may_show.join('; ')) +
      '. The viewer may NOT decide: ' +
      esc(vs.presentation_boundary.this_viewer_may_not_decide.join('; ')) + '.';
    let html = '<div class="lane">';
    vs.states.forEach((s, i) => {
      if (i > 0 && vs.transitions[i - 1]) {
        const t = vs.transitions[i - 1];
        const b = t.binding;
        html += '<div class="arrow">&#8594;<br>transition ' +
          esc(t.from_gen) + '\\u2192' + esc(t.to_gen) +
          '<div class="binding">result.gen=' + esc(b['transition.result.gen']) +
          '\\nresult.status=' + esc(b['transition.result.status']) + '</div>' +
          (t.recorded_cause.change_delta.status === 'RECORDED'
            ? '<div class="binding">recorded cause attached</div>'
            : '<div class="binding">no recorded cause</div>') + '</div>';
      }
      html += '<div class="state' +
        (s.index === (vs.current.bound_generation_index ?? -1)
          ? ' current' : '') + '">' +
        '<div class="gen">gen ' + esc(s.gen) + ' | ' + esc(s.origin.value) +
        '</div>' +
        '<h2>' + esc(s.invention_id.value) + '</h2>' +
        '<span class="badge ' + esc(s.epistemic_badge.label) + '">' +
        esc(s.epistemic_badge.label) + '</span>' +
        '<div class="field"><span class="k">engine state</span>' +
        esc(s.state.value) + ' <span class="ptr">' + esc(s.state.pointer) +
        '</span></div>' +
        '<div class="field"><span class="k">engine maturity</span>' +
        esc(s.maturity.value) + ' <span class="ptr">' +
        esc(s.maturity.pointer) + '</span></div>' +
        fieldHTML(s.architecture.mechanism, 'mechanism (recorded)') +
        fieldHTML(s.architecture.intervention, 'intervention (recorded)') +
        fieldHTML(s.architecture.expected_effect,
                  'expected_effect (recorded prediction)') +
        fieldHTML(s.architecture.falsification_test,
                  'falsification_test (recorded kill path)') +
        '</div>';
    });
    html += '</div>';
    const cur = vs.current;
    if (cur.resolution === 'NOT_RECORDED') {
      html += '<div class="state"><div class="gen">current invention</div>' +
        '<h2>NOT RECORDED in the canonical record</h2></div>';
    } else {
      html += '<div class="state current"><div class="gen">current ' +
        'invention (bound to generation ' +
        esc(vs.current.bound_generation_index) + ')</div><h2>' +
        esc(cur.fields.invention_id.value) + '</h2>' +
        '<div class="field"><span class="k">state</span>' +
        esc(cur.fields.state.value) + '</div>' +
        '<div class="field"><span class="k">maturity</span>' +
        esc(cur.fields.maturity.value) + '</div></div>';
    }
    document.getElementById('content').innerHTML = html;
  }
</script>
</body>
</html>""".replace("__TITLE__", _VIEWER_TITLE).replace(
        "__EMBEDDED__", embedded
    )


def build(lineage_path: str, out_html: str, out_json: str) -> dict:
    src = Path(lineage_path).resolve()
    payload = lp.project_file(str(src))

    # Portability (directive step 4): the artifact records the source path
    # relative to the checkout root when possible - never an author-machine
    # absolute directory.
    repo_root = HERE.parents[1]
    try:
        display_path = str(src.relative_to(repo_root))
    except ValueError:
        display_path = src.name
    payload["source"]["path"] = display_path

    out_json_path = Path(out_json)
    out_json_path.parent.mkdir(parents=True, exist_ok=True)
    out_json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
    )

    out_html_path = Path(out_html)
    out_html_path.parent.mkdir(parents=True, exist_ok=True)
    out_html_path.write_text(_viewer_html(payload), encoding="utf-8")

    print("projection verdict:", payload["verdict"])
    print("viewer json:", out_json_path)
    print("viewer html:", out_html_path)
    if payload["verdict"] == "PROJECTED":
        print(
            "source sha256:", payload["source"]["sha256"]
        )
    else:
        for r in payload["rejections"]:
            print("  rejection:", r["code"], "@", r["pointer"])
    return payload


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lineage", required=True,
                    help="path to the canonical INVENTION_LINEAGE.json")
    ap.add_argument("--html", default=None,
                    help="output HTML path (default: alongside the lineage)")
    ap.add_argument("--json", default=None,
                    help="output JSON path (default: alongside the lineage)")
    args = ap.parse_args()

    lineage = Path(args.lineage)
    if not lineage.is_file():
        # resolve relative to the checkout root (two levels up from here)
        candidate = HERE.parents[1] / lineage
        if candidate.is_file():
            lineage = candidate
        else:
            ap.error(f"lineage file not found: {args.lineage}")

    stem = "trajectory_viewer_" + (
        json.loads(lineage.read_text(encoding="utf-8")).get("run_id", "record")
        .replace("/", "_")
    )
    out_html = args.html or str(lineage.parent / f"{stem}.html")
    out_json = args.json or str(lineage.parent / f"{stem}.json")
    build(str(lineage), out_html, out_json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
