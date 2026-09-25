#!/usr/bin/env python3
"""R529 §4: machine-refresh ACTIVE_DISCOVERY_GRAPH.json +
RUNTIME_CAPABILITY_REGISTRY.json from the actual executable path.

The rule (directive §4):
  declared graph == adapter mapping == canonical implementation
  == production configuration == measured deployment

No hand-maintained duplicated stage truth. The executable chain is
read from discovery_fabric/engine/adapters.py (ADAPTERS registry +
STAGE_ORDER); per-capability module_path/canonical_fn/depends_on
come from the adapter class attributes; repo_head is the current
HEAD. The RETRIEVE + SYNTHESIS descriptions are corrected to the
measured production path:
  RETRIEVE .... V2 retrieval fabric (DEFAULT) / V1 legacy two-source
                pipeline via ENGINE_RETRIEVAL_FABRIC; multi-source
                (semantic scholar, core, datacite, crossref,
                europepmc, arxiv, doaj, openaire, patents) with
                canonical dedup + lineage attribution
  SYNTHESIS ... policy-routed through the provider registry
                (reg.SelectionPolicy + reg.generate; purpose=
                synthesis; R518 Atria retired from synthesis;
                OPERATOR OVERRIDE via ENGINE_SYNTHESIS_PROVIDER);
                provider/model vary per call (durable routing truth
                rides the candidate provenance)
  MECHANISM_SPACE  R453 lean path (adapters._lean_mechanism_space):
                FREEZE/VERIFY facts reused, deterministic item
                construction, at most ONE operator-instantiation LLM
                call (deterministic selection), deterministic
                validation/distinctness tail; instrumented by
                mechanism_attribution/1.0.0 (12 subphases)

Non-executable metadata (historical validation notes, test lists,
promotion history, conductor side-effects, credential blocks) is
PRESERVED from the existing files — only the executable chain,
the per-capability implementation pointers, the stale
descriptions, and the repo_head stamps are refreshed.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

GRAPH = REPO / "ACTIVE_DISCOVERY_GRAPH.json"
REGISTRY = REPO / "RUNTIME_CAPABILITY_REGISTRY.json"


def _head() -> str:
    out = subprocess.run(["git", "rev-parse", "HEAD"],
                         capture_output=True, text=True, cwd=str(REPO))
    return out.stdout.strip()


def main() -> int:
    from discovery_fabric.engine import adapters as ad

    head = _head()
    assert len(head) == 40, f"bad HEAD: {head!r}"

    # ---- executable chain from ADAPTERS + STAGE_ORDER ----
    chain = []
    for i, stage in enumerate(ad.STAGE_ORDER, start=1):
        inst = ad.ADAPTERS.get(stage)
        if inst is None:
            print(f"FATAL: STAGE_ORDER stage {stage!r} has no "
                  f"ADAPTERS entry — the adapter mapping is broken")
            return 2
        chain.append({
            "order": i,
            "stage": stage,
            "capability_id": getattr(inst, "capability_id", ""),
            "module_path": getattr(inst, "module_path", ""),
            "canonical_fn": getattr(inst, "canonical_fn", ""),
            "needs_network": bool(getattr(inst, "needs_network",
                                          False)),
            "depends_on": list(getattr(inst, "depends_on", []) or []),
        })

    # ---- ACTIVE_DISCOVERY_GRAPH.json ----
    g = json.loads(GRAPH.read_text(encoding="utf-8"))
    g["executable_chain"] = chain
    g["repo_head"] = head
    g.setdefault("refreshed_by", "scripts/r529_refresh_metadata.py")
    g["refreshed_at_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                          time.gmtime())
    g["refresh_rule"] = ("machine-generated from "
                         "discovery_fabric/engine/adapters.py "
                         "(ADAPTERS registry + STAGE_ORDER); "
                         "per-capability attributes read from the "
                         "adapter class; repo_head = current HEAD")
    GRAPH.write_text(json.dumps(g, indent=1, ensure_ascii=False) + "\n",
                     encoding="utf-8")
    print(f"refreshed {GRAPH} (repo_head={head[:12]}, "
          f"{len(chain)} stages)")

    # ---- RUNTIME_CAPABILITY_REGISTRY.json ----
    r = json.loads(REGISTRY.read_text(encoding="utf-8"))
    caps = r.get("capabilities", [])
    by_id = {}
    for c in caps:
        if isinstance(c, dict):
            by_id[c.get("capability_id") or c.get("id")] = c
    # update every capability whose adapter exists in the registry
    n_updated = 0
    for stage, inst in ad.ADAPTERS.items():
        cid = getattr(inst, "capability_id", "")
        c = by_id.get(cid)
        if c is None:
            continue
        c["module_path"] = getattr(inst, "module_path", "") or c.get(
            "module_path")
        c["canonical_function"] = getattr(inst, "canonical_fn", "") \
            or c.get("canonical_function")
        c["adapter"] = (f"discovery_fabric/engine/adapters.py::"
                        f"{type(inst).__name__}")
        n_updated += 1
    # corrected descriptions for the two stale entries (directive §4)
    ret = by_id.get("A2_RETRIEVAL")
    if ret is not None:
        ret["purpose"] = ("V2 multi-source retrieval fabric "
                          "(DEFAULT via ENGINE_RETRIEVAL_FABRIC=V2; "
                          "V1 legacy two-source pipeline on "
                          "ENGINE_RETRIEVAL_FABRIC=V1): semantic "
                          "scholar, core, datacite, crossref, "
                          "europepmc, arxiv, doaj, openaire, patents, "
                          "with canonical dedup + lineage "
                          "attribution + content hashes")
        ret["module_path"] = \
            "discovery_fabric/retrieval_fabric/pipeline.py"
        ret["canonical_function"] = \
            "retrieve_fabric(problem) [V2] / retrieve(problem) [V1]"
    syn = by_id.get("SYNTHESIS")
    if syn is not None:
        syn["purpose"] = ("LLM candidate generation from frozen "
                          "evidence, policy-routed through the "
                          "provider registry (reg.SelectionPolicy + "
                          "reg.generate; purpose=synthesis; R518 "
                          "Atria retired from synthesis; OPERATOR "
                          "OVERRIDE via ENGINE_SYNTHESIS_PROVIDER). "
                          "Provider/model vary per call; the durable "
                          "routing truth rides the candidate "
                          "provenance (provider_route, retry_notes, "
                          "cost_policy_refusals, ladder_head).")
    ms = by_id.get("MECHANISM_SPACE")
    if isinstance(ms, dict):
        ms["purpose"] = ("R453 lean mechanism-space construction "
                         "(adapters._lean_mechanism_space): "
                         "FREEZE/VERIFY facts reused, deterministic "
                         "item construction, at most ONE operator-"
                         "instantiation LLM call (deterministic "
                         "selection), deterministic validation/"
                         "distinctness tail; instrumented by "
                         "mechanism_attribution/1.0.0 (12 subphases)")
    r["repo_head_at_creation"] = head
    r["refreshed_by"] = "scripts/r529_refresh_metadata.py"
    r["refreshed_at_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                          time.gmtime())
    r["refresh_rule"] = ("per-capability module_path/canonical_fn/"
                         "adapter read from the adapter class; "
                         "RETRIEVE/SYNTHESIS/MECHANISM_SPACE "
                         "descriptions corrected to the measured "
                         "production path; historical notes/tests/"
                         "promotion history preserved")
    REGISTRY.write_text(json.dumps(r, indent=1, ensure_ascii=False)
                        + "\n", encoding="utf-8")
    print(f"refreshed {REGISTRY} (repo_head={head[:12]}, "
          f"{n_updated} capabilities updated)")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
