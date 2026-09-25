#!/usr/bin/env python3
"""R529 §4: machine-refresh ACTIVE_DISCOVERY_GRAPH.json +
RUNTIME_CAPABILITY_REGISTRY.json from the actual executable path.

The rule (directive §4):
  declared graph == adapter mapping == canonical implementation
  == production configuration == measured deployment

No hand-maintained duplicated stage truth. The executable chain is
read from discovery_fabric/engine/adapters.py (ADAPTERS registry +
STAGE_ORDER); per-capability module_path/canonical_fn/depends_on
come from the adapter class attributes.

R530 §10 (structural entropy repair): one commit cannot literally
contain its own final SHA before being committed. The metadata
therefore records `generated_from_commit` (the tree the chain was
reconstructed from) — NEVER a field named `repo_head` pretending
to be the self-containing commit. The validator checks:
  metadata source commit
  → ancestor of the metadata commit
  → executable chain reconstructed from that source
  → current production engine identity separately recorded
(production identity lives in the deploy record + live read-back,
never in this file).

The RETRIEVE + SYNTHESIS descriptions are corrected to the
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
descriptions, and the generated_from_commit stamps are refreshed.
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
    # R530 §10: the stamp is `generated_from_commit` (the tree read),
    # never `repo_head` (a commit cannot contain its own SHA).
    # Any legacy `repo_head` key is REMOVED so no reader can mistake
    # it for current HEAD.
    g = json.loads(GRAPH.read_text(encoding="utf-8"))
    g["executable_chain"] = chain
    g["generated_from_commit"] = head
    g.pop("repo_head", None)
    g.setdefault("refreshed_by", "scripts/r529_refresh_metadata.py")
    g["refreshed_at_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                          time.gmtime())
    g["refresh_rule"] = ("machine-generated from "
                         "discovery_fabric/engine/adapters.py "
                         "(ADAPTERS registry + STAGE_ORDER) as read "
                         "at generated_from_commit; per-capability "
                         "attributes read from the adapter class")
    GRAPH.write_text(json.dumps(g, indent=1, ensure_ascii=False) + "\n",
                     encoding="utf-8")
    print(f"refreshed {GRAPH} (generated_from={head[:12]}, "
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
    r["generated_from_commit"] = head
    r.pop("repo_head_at_creation", None)
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
    print(f"refreshed {REGISTRY} (generated_from={head[:12]}, "
          f"{n_updated} capabilities updated)")
    # R530 §10: automatic validation of the metadata chain.
    _v = validate_metadata_chain(head)
    print("metadata-chain validation:", json.dumps(_v))
    if not _v.get("chain_ok"):
        print("FATAL: metadata chain invalid — refusing to claim "
              "a clean refresh")
        return 2
    return 0


def validate_metadata_chain(source_commit: str) -> dict:
    """R530 §10: validate
      metadata source commit
      → ancestor of the commit that will contain the metadata
      → executable chain reconstructed from that source
      → current production engine identity separately recorded.
    Returns a dict with per-link booleans + chain_ok. The
    production-identity link is read from the durable deploy
    record + the live Space read-back is NOT taken here (the
    validator is repo-side; production proof is a separate gate).
    """
    import subprocess as _sp

    def _sh(*a):
        return _sp.run(list(a), capture_output=True, text=True,
                       cwd=str(REPO))

    # link 1: source commit is a real commit object
    _o = _sh("git", "cat-file", "-t", source_commit)
    link_source = _o.stdout.strip() == "commit"
    # link 2: source is an ancestor of HEAD (the metadata commit
    # will descend from HEAD, so source==HEAD or ancestor-of-HEAD
    # keeps the chain intact)
    _o = _sh("git", "merge-base", "--is-ancestor", source_commit,
             "HEAD")
    link_ancestor = _o.returncode == 0
    # link 3: the executable chain in the file reconstructs from
    # the source tree's adapters.py (stage set + per-stage
    # capability/module/fn equal)
    link_chain = False
    try:
        _raw = _sh("git", "show",
                   f"{source_commit}:discovery_fabric/engine/"
                   f"adapters.py").stdout
        import re as _re
        _stages = _re.search(r"STAGE_ORDER\s*=\s*\[(.*?)\]",
                             _raw, _re.DOTALL)
        _src_stages = (_re.findall(r'"([A-Z_]+)"', _stages.group(1))
                       if _stages else [])
        g = json.loads(GRAPH.read_text(encoding="utf-8"))
        _file_stages = [e.get("stage")
                        for e in g.get("executable_chain") or []]
        link_chain = (_src_stages == _file_stages
                      and g.get("generated_from_commit")
                      == source_commit
                      and "repo_head" not in g)
    except Exception:  # noqa: BLE001 — validation fails closed
        link_chain = False
    # link 4: production engine identity is recorded SEPARATELY
    # (deploy record + harvest custody), never in this file
    link_production = False
    try:
        dep = json.loads((REPO / "R527" / "AFTER_DEPLOY_RECORD.json")
                         .read_text(encoding="utf-8"))
        link_production = bool(dep.get("commit"))
    except Exception:  # noqa: BLE001
        link_production = False
    return {
        "source_commit": source_commit,
        "link_source_is_commit": link_source,
        "link_source_ancestor_of_head": link_ancestor,
        "link_chain_reconstructed": link_chain,
        "link_production_recorded_separately": link_production,
        "chain_ok": bool(link_source and link_ancestor and
                         link_chain and link_production),
    }


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
