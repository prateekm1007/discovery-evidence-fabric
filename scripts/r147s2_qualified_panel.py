#!/usr/bin/env python3
"""r147s2_qualified_panel.py — DIR-2c glue: read the twin lane's
QUALIFICATION verdict (eval/r147_rcal_centai/QUALIFICATION.json,
claim c-0255), select the QUALIFIED judges (per-judge acc>=0.8 AND
answered>=0.9 AND miss-bias<=1; the run needs >=3 from >=2 non-agnes
families, alpha>=0.6 — the GATE is theirs; this glue only maps the
verdict onto the panel driver's judge table), then run the P4 panel
on the SEALED-BYTES strengthened generation (packs_sealed_set.json)
via scripts/r147_panel_cent_resume.py in one-judge mode per judge
(byte-resume: only VALID legs skip; the prior UNQUALIFIED panel legs
(eval/r146_p4_panel/<tag>__v17-*.json from ef2865fa8) stand as typed
fallback evidence — the QUALIFIED scoring event is a distinct
composition ordered by the owner (R147 order 10:32Z: qualify THEN
panel), typed in the record; the leg files are shared, so the
byte-resume rule applies across compositions per (judge, candidate):
one generation per (judge, candidate) holds — a leg file written by
the unqualified run will NOT be re-generated (Art. 7).

Wait — the Art. 7 read needs care: the unqualified run's legs (dsv41
30, mm31 30, dsv4f 30) used the SAME model ids as the candidate
qualification set (dsv4f = deepseek-v4-flash). If the verdict
qualifies dsv4f, its 30 panel legs ALREADY EXIST from the fallback
run — byte-resume skips them and those legs count toward the
qualified composition. Typed honestly: those legs were generated
BEFORE the qualification verdict was known (the same instrument, the
same prompt bytes, the same one-generation contract) — they count as
the (judge, candidate) generation; no re-roll is performed and none
is needed (Art. 7 forbids re-rolling on an outcome). The judge's
qualification status is metadata about the judge, not part of the
leg bytes. Disclosed in the tally record.

Modes: R147_JUDGE=<tag> single judge; no env = run all qualified +
the tally.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

QUAL_PATH = REPO / "eval" / "r147_rcal_centai" / "QUALIFICATION.json"
PANEL = REPO / "scripts" / "r147_panel_cent_resume.py"

# the twin runner's verdict tags -> the panel driver's judge-table
# tags (the same model ids; the driver's leg-file naming)
TAG_MAP = {
    "dsv4f": "dsv4f",   # deepseek-v4-flash
    "qw38f": "qw38",    # qwen3.8-flash
    "hy4f": "hy4flash", # hy4-flash:free
    "glm53f": "glm53",  # glm-5.3-flash (paid lane)
}


def qualified_tags() -> list:
    q = json.loads(QUAL_PATH.read_text())
    gate = q.get("gate") or {}
    tags = q.get("qualified_tags") or []
    if not gate.get("pass"):
        raise SystemExit(
            "the qualification GATE did not pass "
            f"(n_qualified={gate.get('n_qualified')}, "
            f"n_families={gate.get('n_families')}, "
            f"alpha={gate.get('alpha')}) — the panel does not run "
            "on unqualified judges (the locked order)")
    if not tags:
        raise SystemExit("gate passed but qualified_tags empty — "
                         "typed abort, inspect the verdict")
    return tags


def main() -> int:
    if not QUAL_PATH.exists():
        raise SystemExit("the qualification verdict has not landed "
                         "(eval/r147_rcal_centai/QUALIFICATION.json) "
                         "— the locked order is qualify THEN panel")
    verdict_tags = qualified_tags()
    tags = [TAG_MAP.get(t) for t in verdict_tags]
    missing = [t for t, m in zip(verdict_tags, tags) if m is None]
    if missing:
        raise SystemExit(f"verdict tags not in TAG_MAP: {missing} — "
                         "extend TAG_MAP first")
    print("qualified judges:", verdict_tags, "->", tags)
    only = os.environ.get("R147_JUDGE", "").strip()
    env = dict(os.environ)
    env["R147_PACKS"] = "eval/r146_p4_panel/packs_sealed_set.json"
    for tag in ([only] if only else tags):
        env["R147_JUDGE"] = tag
        rc = subprocess.run([sys.executable, str(PANEL)], env=env)
        if rc.returncode != 0:
            return rc.returncode
    if only:
        return 0
    rc = subprocess.run([sys.executable, str(PANEL)], env=env)
    return rc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
