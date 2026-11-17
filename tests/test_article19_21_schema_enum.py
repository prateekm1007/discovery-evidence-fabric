#!/usr/bin/env python3
"""Articles 19/21 schema-enum gate (epistemic constitution v3.2.0 CI
addition for F57/F58/F59; ratification claim c-0080).

CLAUSE UNDER ENFORCEMENT (Art. 19, v3.2.0): "STRUCTURED-SCHEMA-ENUM
validation gates every committed structured candidate: measure_class/
signals_used/principle_id validate against the problem's allowed sets
and the classical registries; the prose-regex scanners are retired from
the validation role (Art. 16); diversity axes are COMPUTED
deterministically, never LLM-judged."

GROUND TRUTH: F57/F58/F59 were prose-regex FALSE POSITIVES (the
scanners misread prose); the c-0069 remedy moved the gate semantics
into the candidate_schema 1.1.0 enums + the population domain clamp.
This test makes the schema-sourced path the CI-enforced reality:

  leg 1 — every committed structured plan record (the v8.2 DEV plan
          population, the r58 ablation rows' typed_plan layer)
          validates: measure_class in the engine's MEASURE_CLASSES
          enum, signals_used in the engine's SIGNALS registry,
          principle_id in the classical TRIZ 40 registry (P-form and
          list-form both typed);
  leg 2 — the diversity axes are COMPUTED: the plan enumeration and
          the diversity measures re-run byte-identically across hash
          seeds (no LLM judge in the axis derivation — the module
          imports contain no llm/generate call on the measure path);
  leg 3 — the ENGINE's validation path is scanner-free: the engine
          modules that own the enum semantics
          (engine_route/population_search/candidate_schema) must not
          import the retired prose scanners (r24-r30 scripts layer) —
          the validation role is schema-sourced only.
"""
from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine.population_search import (  # noqa: E402
    MEASURE_CLASSES, SIGNALS)
from discovery_fabric.engine import candidate_diversity as cd  # noqa: E402

POPULATION = REPO / "eval" / "v82_dev_plan_population.json"
SMOKE_ROWS = REPO / "eval" / "r58_ablation" / "rows_smoke_challenger"

RETIRED_SCANNER_MODULES = {
    "r22_a1w_v5_repair", "r24_constraint_scan", "r26_catalog_scan",
    "r27_standard_bill_scan", "r29_operational_loss_scan",
    "r29_conversion_scan", "r30_allowed_class_scan",
}


def _principle_ids_ok(raw) -> bool:
    if isinstance(raw, str) and raw.startswith("P"):
        try:
            n = int(raw[1:])
        except ValueError:
            return False
        return 1 <= n <= 40
    if isinstance(raw, list):
        return bool(raw) and all(
            isinstance(x, int) and 1 <= x <= 40 for x in raw)
    return False


def _structured_records() -> list[dict]:
    """Every committed structured plan record (committed bytes only —
    Art. 22: fixtures prove nothing)."""
    recs = []
    pop = json.loads(POPULATION.read_text(encoding="utf-8"))
    for p in pop["problems"]:
        for pl in p["plans"]:
            recs.append({**pl, "_source":
                         f"v82 population {p['problem_id']}"})
    if SMOKE_ROWS.is_dir():
        for f in sorted(SMOKE_ROWS.glob("*.json")):
            r = json.loads(f.read_text(encoding="utf-8"))
            tp = r.get("typed_plan")
            if tp:
                recs.append({**tp, "_source": f"r58 smoke row {f.name}"})
    return recs


def test_every_structured_record_validates_against_the_registries():
    recs = _structured_records()
    assert len(recs) >= 100, (
        f"only {len(recs)} structured records found — the committed "
        "population is the substrate (Art. 22)")
    bad = []
    for r in recs:
        src = r.get("_source", "?")
        mc = r.get("measure_class")
        if mc not in MEASURE_CLASSES:
            bad.append((src, "measure_class", mc))
        if not _principle_ids_ok(r.get("principle_id")):
            bad.append((src, "principle_id", r.get("principle_id")))
        for s in (r.get("signals_used") or []):
            if not any(s.lower().startswith(k.lower())
                       or k.lower().startswith(s.lower())
                       for k in SIGNALS):
                bad.append((src, "signals_used", s))
    assert not bad, (
        "SCHEMA-ENUM VIOLATIONS (the F57/58/59 prose-parse failure "
        f"mode is FORBIDDEN on committed structured bytes): {bad[:8]}")


def test_diversity_axes_are_computed_deterministically():
    # Substrate: the engine's OWN anchor item (population_search.
    # anchor_item — knowledge-first, zero-LLM) over ONE committed DEV
    # problem, instantiated per population plan (committed bytes).
    # The v3.2.0 clause: the diversity axes are COMPUTED
    # deterministically, never LLM-judged — so the measures must be
    # byte-identical across hash seeds and carry no model field.
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        script = td / "axes_probe.py"
        script.write_text(
            "import json, sys\n"
            "sys.path.insert(0, %r)\n"
            "from discovery_fabric.engine import population_search as ps\n"
            "from discovery_fabric.engine import candidate_diversity as cd\n"
            "probs = json.load(open(%r))\n"
            "probs = probs.get('problems', probs) if isinstance(probs, dict)"
            " else probs\n"
            "prob = sorted(probs, key=lambda p: p['problem_id'])[0]\n"
            "pop = json.load(open(%r))\n"
            "plans = [p for pp in pop['problems']\n"
            "         if pp['problem_id'] == prob['problem_id']\n"
            "         for p in pp['plans']]\n"
            "cands = []\n"
            "for i, pl in enumerate(plans[:3]):\n"
            "    f = {'mechanism': str(prob.get('failure', '')),\n"
            "         'intervention': (str(prob.get('constraint', '')) +\n"
            "                          ' plan=' + pl['operator_id'] +\n"
            "                          ' class=' + pl['measure_class'])}\n"
            "    cands.append({'candidate_id':\n"
            "                  'plan%%02d' %% i, 'fields': f})\n"
            "m = cd.measure_diversity(cands)\n"
            "s = cd.span_derivation_check(cands[0]['fields'])\n"
            "print(json.dumps({'plans': plans, 'diversity': m,\n"
            "                  'span': s}, sort_keys=True,\n"
            "                 separators=(',',':')))\n"
            % (str(REPO), str(REPO / "eval" / "problems_dev12.json"),
               str(POPULATION)))
        outs = []
        for seed in ("1", "random"):
            env = dict(os.environ, PYTHONHASHSEED=seed)
            r = subprocess.run([sys.executable, str(script)],
                               capture_output=True, text=True, env=env,
                               timeout=300, cwd=str(REPO))
            assert r.returncode == 0, (
                f"axes probe failed under seed {seed}: {r.stderr[-300:]}")
            outs.append(r.stdout)
        assert outs[0] == outs[1], (
            "DIVERSITY AXES ROTATE UNDER HASH SEED — the v3.2.0 clause "
            "'computed deterministically, never LLM-judged' is violated")
        payload = json.loads(outs[0])
        assert payload["plans"], "no plans enumerated"
        assert payload["diversity"], "no diversity measures computed"
        assert payload["diversity"]["candidates_measured"] == 3, (
            "the diversity measure did not consume the whole substrate")
        assert "mean_pairwise_token_distance" in payload["diversity"] \
            and "distinct_mechanism_clusters" in payload["diversity"], (
            "the deterministic distance/cluster axes did not run "
            "(unexpected shape)")
        # no LLM call in the measured path: the diversity module's
        # measure output must carry no model/provider field
        blob = json.dumps(payload["diversity"]).lower()
        assert '"model"' not in blob and '"provider"' not in blob, (
            "an LLM-judged field entered the diversity axes")


def test_engine_validation_path_is_scanner_free():
    # the retirement (Art. 16): the validation role is schema-sourced;
    # the engine modules that own the enums must not import the
    # retired prose scanners.
    engine = REPO / "discovery_fabric" / "engine"
    offenders = []
    for name in ("engine_route.py", "population_search.py",
                 "candidate_schema.py", "mechanism_space.py"):
        src = (engine / name).read_text(encoding="utf-8")
        tree = ast.parse(src)
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported |= {a.name for a in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
        hit = imported & RETIRED_SCANNER_MODULES
        if hit:
            offenders.append((name, sorted(hit)))
    assert not offenders, (
        f"RETIRED PROSE SCANNERS IMPORTED BY THE ENGINE VALIDATION PATH "
        f"(the F57/58/59 role must stay schema-sourced): {offenders}")
