#!/usr/bin/env python3
"""scripts/r515_regenerate_architecture.py — R515 architecture-record
regeneration (auditor directive: regenerate from the actual executable
state; no hand-maintained stale stage list).

Reads the executable STAGE_ORDER + ADAPTERS and rewrites:
  1. ACTIVE_DISCOVERY_GRAPH.json — executable_chain drops the retired
     IMPROVE linear slot (renumbered), plus a post_rank_operations
     section recording the kill-point IMPROVE operation. All other
     entries preserved byte-identical; repo_head advanced.
  2. RUNTIME_CAPABILITY_REGISTRY.json — conductor.stage_order_exact_
     per_D8 set to the executable chain, regeneration history
     APPENDED (Art. X: append, never silently rewrite), IMPROVE
     capability status -> post-rank operation.
  3. ACTIVE_PATH.md — the runtime chain block regenerated from
     STAGE_ORDER with the kill-point note.

Fail-closed: refuses to write unless the executable state is exactly
the R515 contract (15-stage STAGE_ORDER without IMPROVE; ADAPTERS
keeps the kill-point ImproveAdapter). Idempotent: re-running on an
already-regenerated tree reports clean without rewriting.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))


def _head() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=str(REPO),
        capture_output=True, text=True).stdout.strip()


def _load(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def _dump(p: Path, doc) -> None:
    p.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                 encoding="utf-8")


def main() -> int:
    from discovery_fabric.engine.adapters import ADAPTERS, STAGE_ORDER

    order = list(STAGE_ORDER)
    assert "IMPROVE" not in order, \
        "executable STAGE_ORDER still carries the linear IMPROVE slot"
    assert len(order) == 15, f"expected the 15-stage D8 chain, got {len(order)}"
    assert "IMPROVE" in ADAPTERS, \
        "kill-point ImproveAdapter missing from ADAPTERS"
    assert set(ADAPTERS) == set(order) | {"IMPROVE"}, \
        "R402 asymmetry broken: ADAPTERS must equal STAGE_ORDER + IMPROVE"
    head = _head()
    chain_str = " -> ".join(order)
    changed = []

    # ---- 1. ACTIVE_DISCOVERY_GRAPH.json ----
    gp = REPO / "ACTIVE_DISCOVERY_GRAPH.json"
    g = _load(gp)
    chain = [e for e in g.get("executable_chain") or []]
    kept = [e for e in chain if e.get("stage") != "IMPROVE"]
    if len(kept) != 15 or sorted(
            e.get("stage") for e in kept) != sorted(order):
        raise SystemExit(
            "graph executable_chain does not cover the executable "
            "STAGE_ORDER after IMPROVE removal — refusing to rewrite "
            "(inspect manually)")
    for i, e in enumerate(
            sorted(kept, key=lambda x: x.get("order", 0)), 1):
        e["order"] = order.index(e["stage"]) + 1
    kept_sorted = sorted(kept, key=lambda x: x["order"])
    g["executable_chain"] = kept_sorted
    g["post_rank_operations"] = [{
        "operation": "IMPROVE",
        "capability_id": "IMPROVE",
        "module_path": "discovery_fabric/engine/improve_stage.py",
        "canonical_fn": "improve_stage.run_improve",
        "invocation": ("post-rank Directive-1 kill-evidence point ONLY "
                       "(run.py kill point, improve_payload present); "
                       "never in the linear D8 chain since R515"),
        "needs_network": True,
        "typed_outcomes": ["CHILDREN_ADMITTED", "NO_CHILD_ADMITTED",
                           "NO_KILL_EVIDENCE",
                           "IMPROVEMENT_BLOCKED_TRANSPORT",
                           "DISABLED_BY_OPERATOR",
                           "DEFERRED_TO_KILL_POINT"],
        "record": ("R515 (auditor directive Part A/B): the linear "
                   "placeholder removed; the canonical mutation "
                   "implementation unchanged and reachable exactly "
                   "once, at the kill point"),
    }]
    if g.get("repo_head") != head or any(
            e.get("stage") == "IMPROVE" for e in chain):
        g["repo_head"] = head
        _dump(gp, g)
        changed.append("ACTIVE_DISCOVERY_GRAPH.json")

    # ---- 2. RUNTIME_CAPABILITY_REGISTRY.json ----
    rp = REPO / "RUNTIME_CAPABILITY_REGISTRY.json"
    d = _load(rp)
    conductor = d.get("conductor") or {}
    if conductor.get("stage_order_exact_per_D8") != order:
        conductor["stage_order_exact_per_D8"] = order
        conductor["stage_order_regeneration_history"] = list(
            conductor.get("stage_order_regeneration_history") or []) + [{
                "regenerated_at": time.strftime(
                    "%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "round": "R515",
                "repo_head": head,
                "was": ("16 stages with the IMPROVE linear placeholder "
                        "(ordinary execution only ever recorded "
                        "DEFERRED_TO_KILL_POINT)"),
                "now": ("15 stages; IMPROVE lives post-rank as the "
                        "kill-point operation (see post_rank_operations "
                        "in ACTIVE_DISCOVERY_GRAPH.json); executable "
                        "STAGE_ORDER remains the authority"),
            }]
        d["conductor"] = conductor
        caps = d.get("capabilities") or []
        for c in caps:
            if c.get("capability_id") == "IMPROVE":
                c["current_status"] = (
                    "POST_RANK_OPERATION (kill-point; no linear D8 "
                    "slot since R515)")
                c["adapter"] = (
                    "ImproveAdapter (registered for the post-rank "
                    "kill-point caller, run.py addresses it by name; "
                    "execution point: the Directive-1 pipeline's "
                    "kill-evidence point, the cemetery-update "
                    "precedent; R402 recorded asymmetry)")
        d["capabilities"] = caps
        d["last_updated_directive"] = (
            "R515 (auditor directive Part A): IMPROVE linear "
            "placeholder removed from the runtime chain — 15 stages; "
            "the kill-point operation stays registered; executable "
            "STAGE_ORDER is the single authority")
        _dump(rp, d)
        changed.append("RUNTIME_CAPABILITY_REGISTRY.json")

    # ---- 3. ACTIVE_PATH.md ----
    ap = REPO / "ACTIVE_PATH.md"
    text = ap.read_text(encoding="utf-8")
    new_block = (
        "Engine stage order (runtime): `" + chain_str + "`\n"
        "(`discovery_fabric/engine/adapters.py`; 15 stages; "
        "`MULTI_SOURCE_DISCOVERY` retired from the live path R513; "
        "the `IMPROVE` linear placeholder retired R515 — the "
        "kill-point operation `improve_stage.run_improve` executes "
        "post-rank with kill evidence only).")
    lines = text.split("\n")
    start = next(i for i, l in enumerate(lines)
                 if l.startswith("Engine stage order (runtime):"))
    # the block spans the chain lines plus the parenthetical line
    end = start
    while not lines[end].rstrip().endswith(")."):
        end += 1
        if end - start > 6:
            raise SystemExit("ACTIVE_PATH chain block shape changed — "
                             "inspect manually")
    old_block = "\n".join(lines[start:end + 1])
    # idempotency: the old signature is the linear-slot arrow form
    # (KILLER_EXPERIMENT -> IMPROVE -> ADJUDICATION); the rewritten
    # block names IMPROVE only as the retired placeholder, so a
    # second run must report clean.
    if "IMPROVE → ADJUDICATION" in old_block.replace("->", "→") \
            or "16 stages;" in old_block:
        lines[start:end + 1] = new_block.split("\n")
        ap.write_text("\n".join(lines), encoding="utf-8")
        changed.append("ACTIVE_PATH.md")

    if changed:
        print("regenerated: " + ", ".join(changed))
    else:
        print("architecture records already match the executable "
              "state — nothing rewritten")
    print(f"chain: {len(order)} stages; "
          f"adapters: {len(ADAPTERS)} operations (R402 asymmetry holds)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
