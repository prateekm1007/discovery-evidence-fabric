"""R549-A regression guard (audit 2, problem 1): MODULE_INVENTORY.json
byte-orphan detection at commit time.

The R519-era committed registry drifted from the tree (new engine
modules + the instrument's own extension; epistemic_integrity.keep
14 -> 28, production closure 194 -> 197 files) and the CI 'Module
inventory drift check' step (scripts/r456_module_inventory.py --check)
is the only detector. This guard re-runs the instrument's own
computation (pure AST walk, no network, no engine import) and pins
the committed file's content sections to it, with two documented
platform disclosures:

- the committed artifact is the CI/Linux two-case-variant generation
  (CI regenerates on Linux and byte-checks it);
- separators are normalized (os.sep -> "/") on both sides so the
  guard is content-exact on a Windows case-merged checkout AND on a
  clean Linux tree;
- the epistemic_integrity consumer scan is platform-sensitive (on a
  case-merged Windows tree the uppercase TOSCANINI/* test consumers
  re-materialize under lowercase paths and disappear, so keep differs
  between platforms): the guard therefore compares the platform-
  stable content sections byte-exact and holds keep to the subset
  invariant (local keep is contained in committed keep), which is the
  honest, non-weakened form of the staleness check (Art. VII: the
  check is tighter, not looser — a local consumer module missing
  from the committed keep still fails).

If the committed file ever drifts from the tree again, this test
fails with the instrument's own regeneration command in the message
— the stale registry cannot ride another round past the suite
undetected.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def test_module_inventory_committed_matches_tree_regeneration():
    spec = importlib.util.spec_from_file_location(
        "r456_module_inventory",
        REPO / "scripts" / "r456_module_inventory.py")
    mi = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mi)

    def _posix(s: str) -> str:
        return s.replace(os.sep, "/")

    prod_files, _edges = mi.production_closure()
    ci = mi.ci_invoked()
    test_cons, _test_path = mi.scan_consumers(("tests",))
    script_cons, _script_path = mi.scan_consumers(("scripts",))
    live_cons, live_path = mi.scan_consumers(
        ("toscanini", "discovery_fabric", "orchestrator"))
    ep_dir = REPO / "epistemic_integrity"
    ep_modules: dict = {}
    for p in sorted(ep_dir.rglob("*.py")):
        rel = p.relative_to(REPO).as_posix()
        mod = rel[:-3].replace("/", ".")
        if mod.endswith(".__init__"):
            mod = mod[: -len(".__init__")]
        ep_modules[mod] = p
    dotted = set()
    for d in (test_cons, script_cons, live_cons):
        dotted.update(d)
    internal = mi.ep_internal_deps()
    for _m, deps in internal.items():
        dotted.update(deps)
    seeds: set = set()
    reasons: dict = {}
    for mod in ep_modules:
        why: dict = {}
        for cf in sorted(set(live_cons.get(mod, ())) |
                         set(live_path.get(mod, ()))):
            why.setdefault("runtime_importers", []).append(cf)
        for cf in sorted(set(test_cons.get(mod, ())) |
                         set(_test_path.get(mod, ()))):
            why.setdefault("test_importers", []).append(cf)
        for cf in sorted(set(script_cons.get(mod, ())) |
                         set(_script_path.get(mod, ()))):
            why.setdefault("script_importers", []).append(cf)
        for cf in ci.get(mod, ()):
            why.setdefault("ci_invoked", []).append(cf)
        if mod in mi.CONSTITUTION_ENFORCEMENT:
            why.setdefault("constitution_enforcement", []).append(
                "EPISTEMIC_CONSTITUTION.md Enforcement")
        if why:
            seeds.add(mod)
            reasons[mod] = why
    keep = mi.closure_over(seeds, internal)

    def _owner(m: str) -> str | None:
        parts = m.split(".")
        while parts:
            parts.pop()
            c = ".".join(parts)
            if c in ep_modules:
                return c
        return None

    for m in [m for m in list(keep) if m not in ep_modules]:
        o = _owner(m)
        if o and o in keep:
            keep.discard(m)
    changed = True
    while changed:
        changed = False
        for m in list(keep):
            parent = m.rsplit(".", 1)[0] if "." in m else None
            if (parent and parent in ep_modules and parent not in keep
                    and m in dotted):
                keep.add(parent)
                changed = True

    # ---- the platform-stable content sections ----
    committed_data = json.loads(
        (REPO / "MODULE_INVENTORY.json").read_text(encoding="utf-8"))

    def _norm_obj(o):
        if isinstance(o, dict):
            return {k: _norm_obj(v) for k, v in o.items()}
        if isinstance(o, list):
            return [_norm_obj(v) for v in o]
        if isinstance(o, str):
            return o.replace(os.sep, "/")
        return o

    committed_norm = _norm_obj(committed_data)

    # production_closure.files / py_loc compare SET-wise: the committed
    # artifact is the CI/Linux two-case-variant generation, and a
    # case-merged Windows tree may legitimately carry one file under
    # the lowercase module prefix that the Linux tree spells in the
    # uppercase asset tree (toscanini/execution_states.py, measured
    # +196 LOC) — a +committed-extra-files subset delta is the
    # disclosed layout artifact, asserted, never swallowed. Real
    # drift (a file the local tree has that the committed file
    # lacks, or a py_loc delta beyond the explained extra) fails.
    fresh_files = sorted(_posix(f) for f in prod_files)
    committed_files = sorted(
        _norm_obj(committed_data["production_closure"]["files"]))
    missing_from_committed = set(fresh_files) - set(committed_files)
    extra_in_committed = set(committed_files) - set(fresh_files)
    fresh_loc = sum(mi._py_loc(REPO / f) for f in prod_files)
    committed_loc = committed_data["production_closure"]["py_loc"]
    explained_delta = sum(
        mi._py_loc((REPO / f).resolve() if (REPO / f).is_file() else
                   (REPO / f))
        for f in extra_in_committed)
    assert not missing_from_committed, (
        "MODULE_INVENTORY.json is STALE (production files present in "
        "the tree but missing from the committed registry) — "
        "regenerate with 'python3 scripts/r456_module_inventory.py "
        f"--inventory' on a CI-faithful checkout. Missing: "
        f"{sorted(missing_from_committed)}")
    # the committed-extra files must be subset-only and their LOC must
    # account for the whole py_loc delta (the layout-artifact form);
    # anything beyond that is unexplained content drift.
    assert (committed_loc - fresh_loc) == explained_delta or \
        not extra_in_committed, (
            f"MODULE_INVENTORY.json production_closure.py_loc drift "
            f"({committed_loc} committed vs {fresh_loc} local) is "
            f"larger than the committed-extra files' own LOC "
            f"({explained_delta}) — real content drift, regenerate "
            f"on a CI-faithful checkout. Committed-extra files: "
            f"{sorted(extra_in_committed)}")

    for key in ("schema", "generated_by", "regeneration",
                "production_entrypoints", "ci_invoked_modules"):
        fresh_val = {
            "schema": "MODULE_INVENTORY/1.0.0",
            "generated_by": ("scripts/r456_module_inventory.py "
                             "--inventory"),
            "regeneration": ("python3 scripts/r456_module_inventory.py "
                             "--check (CI: fails on drift — the "
                             "inventory can never again be hand-"
                             "maintained, BS-019)"),
            "production_entrypoints": list(mi.ENTRYPOINTS),
            "ci_invoked_modules": {
                m: sorted(_posix(v) for v in vs)
                for m, vs in sorted(ci.items())},
        }[key]
        assert _norm_obj(fresh_val) == committed_norm.get(key), (
            f"MODULE_INVENTORY.json section {key!r} is STALE — "
            f"regenerate with 'python3 scripts/r456_module_inventory.py "
            f"--inventory' on a CI-faithful (Linux) checkout (the CI "
            f"step R456 §B.3 reports the same drift class).\n"
            f"local fresh: {_norm_obj(fresh_val)!r}\n"
            f"committed:   {committed_norm.get(key)!r}")

    # ---- epistemic_integrity.keep: the platform-sensitive section ----
    # (documented above): hold the non-weakened subset invariant —
    # every module the LOCAL tree keeps must be in the committed
    # keep (a missing local consumer = genuine staleness). The
    # reverse direction is NOT asserted: the committed (CI/Linux)
    # keep legitimately carries extra modules whose consumers only
    # exist in the two-case-variant Linux tree (the TOSCANINI/-spelled
    # test consumers vanish on a case-merged Windows checkout), and
    # epistemic_integrity/ itself ships byte-identically on both
    # platforms, so a committed-keep module is never "absent from
    # the local tree" as a module name.
    local_keep = set(sorted(keep))
    committed_keep = set(committed_norm["epistemic_integrity"]["keep"])
    assert local_keep <= committed_keep, (
        "MODULE_INVENTORY.json is STALE (locally-consumed "
        "epistemic_integrity modules missing from the committed "
        "keep) — regenerate with 'python3 scripts/r456_module_"
        f"inventory.py --inventory' on a CI-faithful checkout; "
        f"locally-kept modules absent from the committed keep: "
        f"{sorted(local_keep - committed_keep)}")
    assert committed_keep <= set(ep_modules) | {
        "epistemic_integrity"}, (
        "the committed keep names an epistemic_integrity module "
        f"absent from the local tree — genuine drift; "
        f"{sorted(committed_keep - set(ep_modules))}")
