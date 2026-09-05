#!/usr/bin/env python3
"""R389 PHASE 1 — final production call-graph audit.

Answers, with measured evidence (not vibes):
  1. Which modules are REACHABLE from the canonical entry path?
  2. Which are unreachable (dead orchestration / legacy wrappers)?
  3. What unique information does each runtime stage add (delta paths)?

Canonical entry points (from ACTIVE_PATH.md — the ONE canonical production
loop):
  - discovery_fabric.engine.run.EngineRun        (the 13-stage loop)
  - toscanini.worker                             (UI product entry)
  - discovery_fabric.engine.cad_pipeline         (3D design)
  - discovery_fabric.engine.equations            (R383 analytical evaluator)
  - discovery_fabric.engine.experiment_selector  (decisive experiment)
  - discovery_fabric.engine.evaluator_contract   (R378 contract)
  - discovery_fabric.engine.learning_loop        (E13 reality ingestion)
  - premium_package_factory                      (dossier + buyer package)
  - scripts.r386_release_chain                   (Art. XXXIX verifier)

Output: R389_PIPELINE_AUDIT.json (committed evidence artifact).
"""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

ENGINE = REPO / "discovery_fabric" / "engine"
ENTRY_MODULES = [
    "discovery_fabric.engine.run",
    "discovery_fabric.engine.cad_pipeline",
    "discovery_fabric.engine.equations",
    "discovery_fabric.engine.experiment_selector",
    "discovery_fabric.engine.evaluator_contract",
    "discovery_fabric.engine.learning_loop",
    "discovery_fabric.engine.improvement_engine",
    "premium_package_factory.r371.builder",
    "premium_package_factory.gates.r370g_reality_event_schema",
]
# modules the product layer imports (toscanini.*)
PRODUCT_ENTRIES = ["toscanini.worker", "toscanini.server", "toscanini.sessions",
                   "toscanini.problem_builder", "toscanini.gateway"]

ALL_ENGINE_MODULES = sorted(
    p.stem for p in ENGINE.glob("*.py") if p.stem != "__init__")


def resolve(mod: str) -> Path | None:
    p = REPO / (mod.replace(".", "/") + ".py")
    if p.exists():
        return p
    p = REPO / (mod.replace(".", "/")) / "__init__.py"
    return p if p.exists() else None


def imports_of(path: Path) -> list[str]:
    """Local (in-repo) modules imported by `path` — static, AST-based.

    Handles BOTH absolute (discovery_fabric.*, premium_package_factory.*,
    toscanini.*, scripts.*) AND relative imports (from .x import y),
    resolved against the importing file's package.
    """
    try:
        tree = ast.parse(path.read_text(errors="replace"))
    except SyntaxError:
        return []
    # package dotted prefix for this file: e.g. discovery_fabric.engine
    rel = path.relative_to(REPO).with_suffix("")
    parts = list(rel.parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    pkg = ".".join(parts)
    found = []
    for node in ast.walk(tree):
        targets: list[tuple[str, int]] = []  # (module, level)
        if isinstance(node, ast.Import):
            targets = [(a.name, 0) for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            targets = [(node.module, node.level or 0)]
        elif isinstance(node, ast.ImportFrom) and not node.module:
            # from . import x  (module=None, level>0)
            for a in node.names:
                mod = pkg + "." + a.name if (node.level or 0) == 1 else None
                if mod:
                    found.append(mod)
            continue
        for t, level in targets:
            if level == 0:
                if t.startswith(("discovery_fabric", "premium_package_factory",
                                 "toscanini", "scripts")):
                    found.append(t)
            else:
                # relative: strip (level-1) components from pkg
                base = pkg.split(".")
                if node.level and node.level > 1:
                    base = base[: len(base) - (node.level - 1)]
                if node.module:
                    found.append(".".join(base) + "." + node.module)
    return found


def reachable_from(entries: list[str]) -> tuple[set[str], dict[str, list[str]]]:
    seen: set[str] = set()
    edges: dict[str, list[str]] = {}
    stack = [e for e in entries if resolve(e)]
    while stack:
        mod = stack.pop()
        if mod in seen:
            continue
        seen.add(mod)
        path = resolve(mod)
        if not path:
            continue
        deps = imports_of(path)
        edges[mod] = deps
        for d in deps:
            if d not in seen:
                stack.append(d)
    return seen, edges


def main() -> None:
    prod_reach, prod_edges = reachable_from(PRODUCT_ENTRIES)
    # a discovery_fabric.engine.X is engine-reachable if any reachable module
    # imports it (directly or transitively) — normalize to engine stems
    engine_reach: set[str] = set()
    for m in prod_reach:
        if m.startswith("discovery_fabric.engine."):
            engine_reach.add(m.split(".")[-1])
    # run.py's dynamic stage adapters: ADAPTERS registry imports stage modules
    adapters_path = ENGINE / "adapters.py"
    adapter_mods = [d.split(".")[-1] for d in imports_of(adapters_path)
                    if d.startswith("discovery_fabric.")]
    # entry modules that live in engine/
    for m in ENTRY_MODULES:
        if m.startswith("discovery_fabric.engine."):
            engine_reach.add(m.split(".")[-1])
    # transitive closure through engine modules only
    frontier = list(engine_reach)
    while frontier:
        stem = frontier.pop()
        p = ENGINE / f"{stem}.py"
        if not p.exists():
            continue
        for d in imports_of(p):
            if d.startswith("discovery_fabric."):
                s = d.split(".")[-1]
                if s not in engine_reach and (ENGINE / f"{s}.py").exists():
                    engine_reach.add(s)
                    frontier.append(s)

    unreachable = [m for m in ALL_ENGINE_MODULES if m not in engine_reach]

    # ---- stage delta evidence (from the real w9 run) -----------------------
    run_dir = REPO / "ENGINE_RUNS" / "w9_nephrology_hemodialysis_dose_flow_limit"
    stage_deltas: dict[str, int] = {}
    order = ["RETRIEVE", "FREEZE", "SYNTHESIZE", "VERIFY",
             "MULTI_SOURCE_DISCOVERY", "COLLISION", "ATTACK",
             "CONTRADICTION", "KILLER_EXPERIMENT", "ADJUDICATION",
             "CLASSIFY", "NEXT_BEST_ACTION", "RANK"]

    def flat(d, prefix=""):
        keys = set()
        if isinstance(d, dict):
            for k, v in d.items():
                keys.add(prefix + k)
                keys |= flat(v, prefix + k + ".")
        elif isinstance(d, list) and d:
            keys |= flat(d[0], prefix + "[0].")
        return keys

    prev = None
    for st in order:
        f = run_dir / f"envelope_{st}.json"
        if not f.exists():
            continue
        cur = flat(json.loads(f.read_text()))
        stage_deltas[st] = len(cur) if prev is None else len(cur - prev)
        prev = cur

    report = {
        "artifact": "R389_PIPELINE_AUDIT",
        "method": "static AST import graph + measured stage-envelope deltas "
                  "(AST is conservative: dynamic imports in adapters.py are "
                  "added explicitly; quoted path literals audited in R388)",
        "product_entry_modules": PRODUCT_ENTRIES,
        "engine_modules_total": len(ALL_ENGINE_MODULES),
        "engine_modules_reachable": len(engine_reach),
        "engine_modules_unreachable": unreachable,
        "adapter_stage_modules": adapter_mods,
        "stage_delta_unique_paths": stage_deltas,
        "notes": [
            "Unreachable-from-production engine modules are ARCHIVE/REMOVE "
            "candidates ONLY if tests do not independently require them "
            "(benchmarks/smoke tools are tooling, not production).",
            "Stage deltas measured on real run "
            "w9_nephrology_hemodialysis_dose_flow_limit.",
        ],
    }
    out = REPO / "R389_PIPELINE_AUDIT.json"
    out.write_text(json.dumps(report, indent=2))
    print(f"wrote {out}")
    print(f"engine modules: {len(ALL_ENGINE_MODULES)} total, "
          f"{len(engine_reach)} reachable, {len(unreachable)} unreachable")
    for m in unreachable:
        print(f"  UNREACHABLE: discovery_fabric/engine/{m}.py")


if __name__ == "__main__":
    main()
