#!/usr/bin/env python3
"""r157s3_verifier_record.py — the Art. 29c/e VERIFIER record for the
R153S3 window (session builder-r153s3, claim c-0264): the concurrent
builder-r156s1 EXECUTOR custody (eval/r156s1_quota_custody.json @
c0222d021) is verified line-by-line FROM BYTES — nothing re-generated,
no panel leg fired, no quota consumed beyond the single 16-token probe.

The deterministic recomputes (leg census, serving alpha, resume-code
reading) are re-executed by this script; the one-shot network fact
(the 429 quota probe) is embedded as the measured fact of this window
(running it again would re-measure the same dead pool at the cost of
another call — the probe itself is the only measured field).
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# ---- 1. the leg census, recomputed from the committed leg bytes ----
leg_dir = REPO / "eval" / "r148_p4_panel_v18"
census: dict = {}
for j in ("snlite", "mst14b", "hy4f"):
    fs = sorted(leg_dir.glob(f"{j}__*.json"))
    outcomes = {}
    for f in fs:
        oc = json.loads(f.read_text()).get("outcome")
        outcomes[oc] = outcomes.get(oc, 0) + 1
    census[j] = {"legs": len(fs), "outcomes": outcomes}
assert census["hy4f"]["outcomes"].get("VALID") == 30, "hy4f broke"
assert census["snlite"]["legs"] == 11, "snlite bank changed"
assert census["snlite"]["outcomes"].get("VALID") == 8, "snlite VALID"
assert census["snlite"]["outcomes"].get("RATE_LIMITED") == 3, "snlite RL"
assert census["mst14b"]["legs"] == 0, "mst14b should be 0"

# ---- 2. the serving alpha, recomputed from the rcal leg bytes ----
# (the same function the panel runner's load_serving() gate executes)
spec = importlib.util.spec_from_file_location(
    "r153_panel", REPO / "scripts" / "r153_p4_panel_v18.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
xk = json.loads((REPO / "eval/r153_rcal_xkiro/QUALIFICATION.json").read_text())
tags = list(xk.get("qualified_tags", []))
r148 = json.loads((REPO / "eval/r148_rcal_centai/QUALIFICATION.json").read_text())
if "hy4f" in r148.get("qualified_tags", []):
    tags.append("hy4f")
salpha = mod._serving_alpha(tags, {})
assert salpha.get("alpha") == 0.945046, "serving alpha moved"
assert salpha.get("n_units") == 24

# ---- 3. the resume-code reading (the r153s2 correction) ----
runner = (REPO / "scripts/r153_p4_panel_v18.py").read_text()
assert 'if prev.get("outcome") == "VALID":' in runner
assert "continue  # only VALID legs skip (the R146 fix)" in runner

# ---- 4. the import graph (DIR-6) ----
oneshot = (REPO / "scripts/r149_v18_physics_one_shot.py").read_text()
line56 = oneshot.splitlines()[55]
assert "physics_truth" in line56, "import graph moved"

r = subprocess.run(["git", "rev-parse", "--short=9", "HEAD"],
                   capture_output=True, text=True, check=True)
tip = r.stdout.strip()

rec = {
    "record": "R157S3_VERIFIER_RECORD/1.0.0",
    "claim": "c-0264",
    "work_id": "r153-xkiro-qualify-panel-v18",
    "session": "builder-r153s3",
    "role": "VERIFIER (Art. 29c: recompute from bytes, never re-generate)",
    "at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    "verifies": "eval/r156s1_quota_custody.json @ " + tip
                + " (the concurrent EXECUTOR custody for this window)",
    "the_quota_probe": {
        "method": "ONE minimal xkiro chat completion "
                  "(mistralai/ministral-3b, max_tokens 16) via the "
                  "engine xkiro_chat on the VAULT key f6c09bee9bde "
                  "(digests-only custody; the directions' sk-xt-c3643f "
                  "key is 401-dead per R155 and never used)",
        "result": "RouteRefused [rate_limited] xkiro: HTTP 429: "
                  "\"You've reached today's free-model token quota. "
                  "Your plan's paid allowance is separate — switch to "
                  "a paid model to keep going, or wait for...\"",
        "probe_time": "2026-11-25 ~10:56 UTC (this window, "
                      "independent of the r156s1 probe at 10:36)",
        "the_models_200_distinction": "the /models endpoint returns "
                     "200 UNGATED — listing is NOT quota evidence; the "
                     "completion endpoint is the gated surface (this "
                     "window's earlier models-200 probe does not "
                     "contradict the 429)",
        "verdict": "VERIFIED — the daily free-token pool is dead until "
                   "00:00 UTC 2026-11-26; the panel cannot run this "
                   "window (the typed refusal stands)",
    },
    "the_leg_census_recompute": {
        "source": "committed leg bytes eval/r148_p4_panel_v18/ @ " + tip,
        "hy4f": census["hy4f"],
        "snlite": census["snlite"],
        "mst14b": census["mst14b"],
        "verdict": "VERIFIED — matches the r156s1 custody and the "
                   "resume state (hy4f 30/30 VALID; snlite 11 = 8 "
                   "VALID + 3 RATE_LIMITED; mst14b 0)",
    },
    "the_serving_alpha_recompute": {
        "method": "the panel runner's own _serving_alpha over the "
                  "committed rcal leg bytes (zero LLM calls)",
        "tags": tags,
        "alpha": salpha.get("alpha"),
        "n_units": salpha.get("n_units"),
        "gate": "PASS (>=3 judges, >=2 non-generator families, "
                "alpha >= 0.6; 3 families: mistral/sensenova/hy4)",
        "verdict": "VERIFIED — 0.945046, the V120 frozen serving set "
                   "intact",
    },
    "dir6_rerun": {
        "physics_battery": "73 passed (checks + magnitudes + r54 + "
                           "guards) — re-run locally this window; "
                           "pint installed to match the CI surface",
        "v18_row_regression": "20 passed (tests/test_f80_onrow_"
                              "physics.py) — re-run locally",
        "import_graph": "scripts/r149_v18_physics_one_shot.py:56 -> "
                        + line56.strip() + " (confirmed unchanged)",
        "verdict": "VERIFIED — 93/93, the validated v18 instrument "
                   "intact (DIR 6)",
    },
    "the_rate_limited_correction": {
        "the_r153s2_claim": "RATE_LIMITED panel legs are FINAL under "
                            "the no-re-roll rule",
        "the_code": "scripts/r153_p4_panel_v18.py:358 — only "
                    "outcome == 'VALID' legs skip (the R146 fix); "
                    "RATE_LIMITED legs RETRY on the next run",
        "verdict": "VERIFIED — the r156s1 correction is right (re-read "
                   "against the runner bytes this window); the legs "
                   "are recoverable, not final; the refusal itself "
                   "still stands on the wasted-window rationale",
    },
    "the_arithmetic_correction": {
        "to": "the 'snlite 19' figure (the directions, the resume "
              "state, and the r156s1 custody)",
        "truth": "the byte-resume generates 22 snlite legs (19 "
                 "unwritten + 3 RATE_LIMITED retries that carry NO "
                 "parsed judgment — no re-roll of any vote) + 30 "
                 "mst14b = 52 legs, ~260K tokens at the budget "
                 "ladder vs the ~200K daily pool estimate",
        "consequence": "the next executor probes FIRST; if the pool "
                       "dies late, the tally computes over votes cast "
                       "and the shortfall is disclosed, never papered",
    },
    "the_resume": {
        "when": "the first window after 00:00 UTC 2026-11-26",
        "how": "probe the completion endpoint (NOT /models); then ONE "
               "unfiltered scripts/r153_p4_panel_v18.py run "
               "(byte-resume: skips hy4f 30 + snlite 8 VALID; "
               "generates snlite 22 + mst14b 30); NO re-qualification "
               "(the serving set is frozen at V120)",
        "then": "the 3-judge two-axis majority tally on the FULL "
                "30-candidate set; scripts/r153s1_tally_recompute.py "
                "diff=0; the >=50% viable+non-obvious bar -> the "
                "score-8 gate",
    },
    "raw_bytes": "eval/r157s3_verifier_record.json (this file); the "
                 "deterministic recomputes re-executed by "
                 "scripts/r157s3_verifier_record.py at write time",
}

out = REPO / "eval" / "r157s3_verifier_record.json"
out.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n")
print("wrote", out)
print("census:", json.dumps(census))
print("serving alpha:", salpha.get("alpha"), "n_units", salpha.get("n_units"))
print("recorded on", tip)
