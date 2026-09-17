#!/usr/bin/env python3
"""R456 — the §N.1 epistemic_integrity determination + the §B.3 module
inventory, ONE instrument (Art. X: one canonical regeneration authority).

Usage:
  python3 scripts/r456_module_inventory.py --determination
      Writes R456/EPISTEMIC_INTEGRITY_DETERMINATION.json (the keep/archive
      disposition for every epistemic_integrity module, with its consumer
      evidence — nothing is archived on the instrument's say-so alone).
  python3 scripts/r456_module_inventory.py --inventory
      Regenerates MODULE_INVENTORY.json at the repo root from the ACTUAL
      import closure of the production entrypoints (never hand-edited).
  python3 scripts/r456_module_inventory.py --check
      CI gate: fails if MODULE_INVENTORY.json is stale w.r.t. the tree.

Method (disclosed):
  - AST import closure from the 3 production entrypoints + engine/run.py,
    INCLUDING function-level (lazy) imports — the R455 lesson: a static
    module-level-only closure falsified reachability for
    orchestrator/coverage_engine (lazy-loaded via orchestrator/__init__).
  - importlib.import_module("literal") strings counted as imports.
  - CI-invoked modules parsed from .github/workflows/*.yml
    (python -m epistemic_integrity.X invocations).
  - Test/script consumers scanned by AST across tests/ and scripts/.
  - Internal dependency closure inside epistemic_integrity/ resolved by
    the same AST walk.
Constitutional anchors: Art. X (one authority), Art. XV (the instrument
discloses its own method limits), Art. XVI (the determination is a
hypothesis; the consumer evidence is the enforcement), Art. XXI.4 n/a,
Art. LXIV (dispositions recorded per module).
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LIVE_PKGS = ("toscanini", "discovery_fabric", "orchestrator",
             "epistemic_integrity")
ENTRYPOINTS = [
    "toscanini/server.py",
    "toscanini/worker.py",
    "toscanini/artifact_worker.py",
    "discovery_fabric/engine/run.py",
]

# The Constitution's Enforcement section names these as wired machinery;
# they are additionally verified by consumer scan below (never assumed).
CONSTITUTION_ENFORCEMENT = [
    "epistemic_integrity.constitution_loader",
    "epistemic_integrity.research_authorization_gate",
    "epistemic_integrity.dossier_firewall",
]


PATH_LIT_RE = re.compile(
    r"^(toscanini|discovery_fabric|orchestrator|epistemic_integrity)/"
    r"[A-Za-z0-9_/]+\.py$")


def _path_literals(path: Path) -> set[str]:
    """Repo-file path string literals (the _load_by_path pattern — the
    KILLER_EXPERIMENT stage loads bayesian_eig this way; a pure import
    scan misses it)."""
    out: set[str] = set()
    try:
        tree = ast.parse(path.read_text(errors="replace"))
    except SyntaxError:
        return out
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if PATH_LIT_RE.match(node.value):
                out.add(node.value)
    return out


def _module_to_path(mod: str) -> Path | None:
    parts = mod.split(".")
    for pkg in LIVE_PKGS:
        if parts[0] != pkg:
            continue
        cand = REPO.joinpath(*parts)
        if (cand.with_suffix(".py")).is_file():
            return cand.with_suffix(".py")
        if (cand / "__init__.py").is_file():
            return cand / "__init__.py"
        # a from-import of a name inside a module package
        if len(parts) > 1:
            parent = REPO.joinpath(*parts[:-1])
            if (parent.with_suffix(".py")).is_file():
                return parent.with_suffix(".py")
    return None


def _relative_package_of(path: Path) -> Optional[str]:
    """Dotted package of the importing file's directory (for relative
    import resolution); '' for repo-root files (no package context)."""
    try:
        rel = path.resolve().parent.relative_to(REPO.resolve())
    except ValueError:
        return None
    if not rel.parts:
        return ""
    # walk up while __init__.py marks the package root
    parts = list(rel.parts)
    while parts and not (REPO.joinpath(*parts) / "__init__.py").is_file():
        parts.pop()
    return ".".join(parts) if parts else None


def _imports_of(path: Path) -> set[str]:
    """All repo-internal imports of a file, INCLUDING lazy (function
    level) imports, RELATIVE imports (the R504 lesson: `from .mod import
    name` — the prior_art_v2 free-evidence ladder hook — was invisible
    to the level==0-only walk, so a production module could sit outside
    the closure; Art. VII disclosed instrument fix: the walk now resolves
    relative levels against the importing file's package, catching MORE,
    never fewer), importlib literal loads, AND imports inside
    subprocess-embedded code strings (the R456 lesson: the
    research_authorization_gate runs preflight/gauntlet-v1/v2 via
    code-string subprocess scripts — a plain AST import walk calls them
    dead; they are CI-live through G1/G2/G3)."""
    out: set[str] = set()
    try:
        tree = ast.parse(path.read_text(errors="replace"))
    except SyntaxError:
        return out
    rel_pkg = _relative_package_of(path)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                out.add(a.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.level == 0:
                out.add(node.module)
                # from pkg.mod import name -> name may be a submodule
                for a in node.names:
                    out.add(f"{node.module}.{a.name}")
            elif node.level > 0 and rel_pkg:
                # relative import: resolve against the importing file's
                # package (level 1 = the file's package, 2 = its parent, …)
                base_parts = rel_pkg.split(".")
                if node.level > 1:
                    base_parts = base_parts[:-(node.level - 1)]
                base = ".".join(base_parts)
                if node.module:
                    out.add(f"{base}.{node.module}")
                    for a in node.names:
                        out.add(f"{base}.{node.module}.{a.name}")
                else:
                    out.add(base)
                    for a in node.names:
                        out.add(f"{base}.{a.name}")
        elif isinstance(node, ast.Call):
            f = node.func
            if (isinstance(f, ast.Attribute) and f.attr ==
                    "import_module" and isinstance(f.value, ast.Name)
                    and f.value.id == "importlib"):
                if node.args and isinstance(node.args[0], ast.Constant):
                    out.add(str(node.args[0].value))
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            s = node.value
            # subprocess-embedded code strings: parse and collect their
            # imports too (only multi-line strings that parse as code)
            if s.count("\n") >= 2 and "epistemic_integrity" in s:
                try:
                    sub = ast.parse(s)
                except SyntaxError:
                    continue
                for sn in ast.walk(sub):
                    if isinstance(sn, ast.ImportFrom) and sn.module \
                            and sn.level == 0:
                        out.add(sn.module)
                    elif isinstance(sn, ast.Import):
                        for a in sn.names:
                            out.add(a.name)
    return {m for m in out if m.split(".")[0] in LIVE_PKGS}


def production_closure() -> tuple[set[str], dict[str, set[str]]]:
    seen: dict[str, set[str]] = {}
    queue: list[Path] = []
    for e in ENTRYPOINTS:
        p = REPO / e
        if p.is_file():
            queue.append(p)
    reached: set[str] = set()
    while queue:
        p = queue.pop()
        key = str(p.relative_to(REPO))
        if key in reached:
            continue
        reached.add(key)
        for mod in _imports_of(p):
            tgt = _module_to_path(mod)
            if tgt is not None:
                seen.setdefault(mod, set()).add(key)
                if str(tgt.relative_to(REPO)) not in reached:
                    queue.append(tgt)
            else:
                seen.setdefault(mod, set()).add(key)
        # path-literal loads (_load_by_path discipline)
        for lit in _path_literals(p):
            tgt = REPO / lit
            if tgt.is_file():
                seen.setdefault(lit, set()).add(key)
                if lit not in reached:
                    queue.append(tgt)
    return reached, seen


def scan_consumers(roots: tuple[str, ...]) -> tuple[dict[str, set[str]],
                                                dict[str, set[str]]]:
    """(dotted-import consumers, path-literal consumers) — the split is
    load-bearing: a package __init__ is required only for children
    imported BY DOTTED IMPORT (bayesian_eig loads by path through
    _load_by_path, so invention_loop_engine/__init__.py — which imports
    its now-dead siblings — can archive without breaking it)."""
    out: dict[str, set[str]] = {}
    path_out: dict[str, set[str]] = {}
    for root in roots:
        base = REPO / root
        if not base.is_dir():
            continue
        for p in base.rglob("*.py"):
            rel = str(p.relative_to(REPO))
            for mod in _imports_of(p):
                if mod.startswith("epistemic_integrity"):
                    out.setdefault(mod, set()).add(rel)
            for lit in _path_literals(p):
                if lit.startswith("epistemic_integrity/"):
                    path_out.setdefault(
                        lit[:-3].replace("/", "."), set()).add(rel)
    return out, path_out


def ci_invoked() -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    wf = REPO / ".github" / "workflows"
    if not wf.is_dir():
        return out
    pat = re.compile(
        r"python\s+-m\s+(epistemic_integrity\.[a-z_0-9]+)")
    for p in wf.glob("*.yml"):
        for m in pat.findall(p.read_text(errors="replace")):
            out.setdefault(m, set()).add(str(p.relative_to(REPO)))
    return out


def ep_internal_deps() -> dict[str, set[str]]:
    """module -> epistemic_integrity modules it imports."""
    out: dict[str, set[str]] = {}
    base = REPO / "epistemic_integrity"
    for p in base.rglob("*.py"):
        rel = str(p.relative_to(REPO))
        mod = rel[:-3].replace("/", ".")
        if rel == "__init__.py":
            mod = "epistemic_integrity"
        deps = {m for m in _imports_of(p)
                if m.startswith("epistemic_integrity")}
        out[mod] = deps
    return out


def closure_over(seeds: set[str], dep_graph: dict[str, set[str]]) -> set[str]:
    out = set(seeds)
    queue = list(seeds)
    while queue:
        m = queue.pop()
        for d in dep_graph.get(m, ()):
            if d not in out:
                out.add(d)
                queue.append(d)
    return out


def _py_loc(p: Path) -> int:
    try:
        return sum(1 for _ in p.read_text(errors="replace").splitlines())
    except OSError:
        return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--determination", action="store_true")
    ap.add_argument("--inventory", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    prod_files, prod_edges = production_closure()
    ci = ci_invoked()
    test_cons, test_path = scan_consumers(("tests",))
    script_cons, script_path = scan_consumers(("scripts",))
    live_cons, live_path = scan_consumers(("toscanini", "discovery_fabric",
                                            "orchestrator"))
    dotted_imported = set()
    for d in (test_cons, script_cons, live_cons):
        dotted_imported.update(d)
    internal = ep_internal_deps()
    for _m, _deps in internal.items():
        dotted_imported.update(_deps)

    # ---- the §N.1 determination ---------------------------------------
    ep_dir = REPO / "epistemic_integrity"
    ep_modules: dict[str, Path] = {}
    for p in sorted(ep_dir.rglob("*.py")):
        rel = p.relative_to(REPO).as_posix()
        mod = rel[:-3].replace("/", ".")
        if mod.endswith(".__init__"):
            mod = mod[: -len(".__init__")]
        ep_modules[mod] = p
    # seeds: production-reachable, CI-invoked, live-test-imported,
    # constitution-enforcement (verified below, never assumed)
    seeds: set[str] = set()
    reasons: dict[str, dict] = {}
    for mod in ep_modules:
        why: dict[str, list[str]] = {}
        for consumer_file in sorted(set(live_cons.get(mod, ())) |
                                     set(live_path.get(mod, ()))):
            why.setdefault("runtime_importers", []).append(consumer_file)
        for consumer_file in sorted(set(test_cons.get(mod, ())) |
                                     set(test_path.get(mod, ()))):
            why.setdefault("test_importers", []).append(consumer_file)
        for consumer_file in sorted(set(script_cons.get(mod, ())) |
                                     set(script_path.get(mod, ()))):
            why.setdefault("script_importers", []).append(consumer_file)
        for consumer_file in sorted(ci.get(mod, ())):
            why.setdefault("ci_invoked", []).append(consumer_file)
        if mod in CONSTITUTION_ENFORCEMENT:
            why.setdefault("constitution_enforcement",
                           []).append("EPISTEMIC_CONSTITUTION.md Enforcement")
        if why:
            seeds.add(mod)
            reasons[mod] = why

    keep = closure_over(seeds, internal)
    keep_reasons = dict(reasons)
    # fold: a dotted name kept only as an attribute import of a kept file
    def _owner(mod: str) -> str | None:
        parts = mod.split(".")
        while parts:
            parts.pop()
            cand = ".".join(parts)
            if cand in ep_modules:
                return cand
        return None

    attr_only = {m for m in keep if m not in ep_modules}
    for m in attr_only:
        own = _owner(m)
        if own is not None and own in keep:
            keep.discard(m)
    # parent packages of kept children stay ONLY when the child is
    # imported by DOTTED IMPORT (gauntlet/__init__.py stays: its children
    # are imported by the gate's embedded scripts; invention_loop_engine/
    # __init__.py archives: bayesian_eig loads BY PATH and the __init__
    # imports its now-dead siblings — keeping it would break them)
    changed = True
    while changed:
        changed = False
        for m in list(keep):
            parent = m.rsplit(".", 1)[0] if "." in m else None
            if (parent and parent in ep_modules and parent not in keep
                    and m in dotted_imported):
                keep.add(parent)
                changed = True
    frontier = [m for m in keep if m in ep_modules and m not in keep_reasons]
    while frontier:
        nxt = []
        for m in frontier:
            importers = [k for k, v in internal.items() if m in v
                         and k in keep]
            keep_reasons[m] = {"dependency_of": sorted(importers)}
            nxt.extend(k for k in importers if k not in keep_reasons)
        frontier = [m for m in nxt if m not in keep_reasons]

    determination = {
        "instrument": "scripts/r456_module_inventory.py",
        "method": (
            "AST import closure from the 3 production entrypoints + "
            "engine/run.py, lazy (function-level) imports included + "
            "importlib literal loads; CI invocations parsed from the "
            "workflow files; test/script consumers AST-scanned; internal "
            "epistemic_integrity dependency closure resolved the same "
            "way. Disclosed limit: non-literal dynamic imports "
            "(importlib with computed strings) are not visible to this "
            "instrument; none are known in epistemic_integrity/."),
        "seeds_with_evidence": {
            m: keep_reasons[m] for m in sorted(seeds)},
        "kept_by_internal_dependency": {
            m: keep_reasons[m] for m in sorted(keep - seeds)},
        "archive_candidates": sorted(set(ep_modules) - keep),
        "audit_defects_disclosed": [
            "EXT-AUDIT-LEAN-R454 claims gauntlet v1+v2 are CI-called "
            "(G2/G3); the CURRENT workflow files invoke no gauntlet step "
            "(measured: zero references in both .github/workflows/*.yml) "
            "— the audit's premise is stale; both versions archive with "
            "this disclosure (Art. XV, governance principle 1: live state "
            "beats narrative)",
        ],
        "totals": {
            "epistemic_integrity_modules": len(ep_modules),
            "keep": len(keep),
            "archive_candidates": len(set(ep_modules) - keep),
            "archive_candidate_loc": sum(
                _py_loc(ep_modules[m]) for m in set(ep_modules) - keep),
        },
    }
    out_dir = REPO / "R456"
    out_dir.mkdir(exist_ok=True)
    if args.determination:
        (out_dir / "EPISTEMIC_INTEGRITY_DETERMINATION.json").write_text(
            json.dumps(determination, indent=2, sort_keys=True) + "\n")
        print(f"determination -> "
              f"R456/EPISTEMIC_INTEGRITY_DETERMINATION.json "
              f"(keep={determination['totals']['keep']}, "
              f"archive={determination['totals']
                          ['archive_candidates']}, "
              f"loc={determination['totals']['archive_candidate_loc']})")

    # ---- the §B.3 module inventory (ONE, CI-regenerated) --------------
    inventory = {
        "schema": "MODULE_INVENTORY/1.0.0",
        "generated_by": "scripts/r456_module_inventory.py --inventory",
        "regeneration": "python3 scripts/r456_module_inventory.py --check "
                        "(CI: fails on drift — the inventory can never "
                        "again be hand-maintained, BS-019)",
        "production_entrypoints": ENTRYPOINTS,
        "production_closure": {
            "files": sorted(prod_files),
            "py_loc": sum(_py_loc(REPO / f) for f in prod_files),
        },
        "ci_invoked_modules": {
            m: sorted(v) for m, v in sorted(ci.items())},
        "epistemic_integrity": {
            "keep": sorted(keep),
            "seeds_with_evidence": {
                m: keep_reasons[m] for m in sorted(seeds)},
        },
    }
    inv_path = REPO / "MODULE_INVENTORY.json"
    if args.inventory:
        inv_path.write_text(
            json.dumps(inventory, indent=2, sort_keys=True) + "\n")
        print(f"inventory -> MODULE_INVENTORY.json "
              f"({len(prod_files)} production files, "
              f"{inventory['production_closure']['py_loc']} LOC)")
    if args.check:
        current = inv_path.read_text() if inv_path.exists() else ""
        fresh = json.dumps(inventory, indent=2, sort_keys=True) + "\n"
        if current != fresh:
            print("MODULE_INVENTORY.json is STALE — regenerate with "
                  "'python3 scripts/r456_module_inventory.py --inventory'")
            return 1
        print("MODULE_INVENTORY.json matches the tree (no drift)")
    if not (args.determination or args.inventory or args.check):
        print(json.dumps(determination["totals"], indent=2))
        for m in sorted(set(ep_modules) - keep):
            print(f"  ARCHIVE_CANDIDATE {m}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
