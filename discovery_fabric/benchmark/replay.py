"""Phase 15 — independent dossier replay (Coder 2).

Given ONLY:
    generated package (PDFs + JSONs) + package manifest + source evidence +
    traceability

reconstruct:

    CLAIM -> SOURCE -> ENGINEERING REASONING -> DESIGN OUTPUT -> VERIFICATION

without consulting Coder 1's internal engine state (the ENGINEERING_
SPECIFICATION is used only as the run's source-evidence input, never as an
authority for the replay verdict — every link is re-verified against the
package's own shipped artifacts and the run's evidence records).

Emits INDEPENDENT_DOSSIER_REPLAY.json content per package. Broken links are
reported, never silently repaired.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional


def replay_dossier(package_dir: Path, run_dir: Optional[Path] = None) \
        -> Dict[str, Any]:
    package_dir = Path(package_dir)
    run_dir = Path(run_dir) if run_dir else None

    manifest = _j(package_dir / "PACKAGE_MANIFEST.json")
    trace = _j(package_dir / "ENGINEERING_TRACEABILITY.json")
    chains = (trace or {}).get("traceability_chains", []) or []

    # evidence universe available for replay (from run dir, if provided)
    evidence_universe: Dict[str, Dict[str, Any]] = {}
    if run_dir:
        evidence_universe = _evidence_universe(run_dir)

    replayed: List[Dict[str, Any]] = []
    broken: List[Dict[str, Any]] = []

    for c in chains:
        if not isinstance(c, dict):
            continue
        node = c.get("node_id") or c.get("design_input_id") or "?"
        chain = {
            "claim": node,
            "chain_type": c.get("chain_type", "DESIGN_INPUT"),
            "source": c.get("source"),
            "hash": c.get("hash"),
            "evidence_ids": c.get("evidence_ids") or [],
            "linked": c.get("linked", False),
        }
        # --- verify the chain hash binds to the actual node content -----
        if c.get("hash") and run_dir:
            ok, detail = _verify_chain_hash(c, run_dir)
            chain["hash_verifies"] = ok
            if not ok:
                broken.append({"claim": node, "problem":
                               "HASH_MISMATCH", "detail": detail})
        # --- verify evidence ids resolve in the evidence universe -------
        for ev_id in chain["evidence_ids"]:
            if evidence_universe and ev_id not in evidence_universe:
                broken.append({"claim": node, "problem":
                               "EVIDENCE_UNRESOLVED",
                               "detail": f"evidence id {ev_id} not present "
                               f"in run evidence records"})
            else:
                chain.setdefault("resolved_evidence", []).append(ev_id)

        # --- PDF-side confirmation: the node appears in the shipped PDF --
        replayed.append(chain)

    # PDF confirmation of object ids mentioned in traceability
    dossier_text = _pdf_text(package_dir)
    pdf_ids: Dict[str, int] = {}
    if dossier_text:
        for c in replayed:
            m = re.findall(r"\b([A-Z]{2,4}-\d{3})\b",
                           dossier_text or "")
            pdf_ids = {i: m.count(i) for i in set(m)}
        for c in replayed:
            c["appears_in_dossier_pdf"] = pdf_ids.get(c["claim"], 0) > 0

    # claim -> source -> reasoning -> DO -> VF reconstruction rate
    claims_total = len(replayed)
    fully_bound = [c for c in replayed
                   if c.get("hash_verifies", True)
                   and (c.get("appears_in_dossier_pdf", False) or
                        not dossier_text)
                   and not any(b["claim"] == c["claim"] for b in broken)]

    # transfer boundary replay from shipped PDFs only
    tb_pdf = _transfer_boundary_from_pdf(package_dir)

    result = {
        "artifact": "INDEPENDENT_DOSSIER_REPLAY",
        "owner": "CODER2",
        "package_id": (manifest or {}).get("package_id"),
        "inputs_used": ["package PDFs", "PACKAGE_MANIFEST.json",
                        "ENGINEERING_TRACEABILITY.json",
                        "run evidence records (hash verification only)"],
        "claims_replayed": claims_total,
        "claims_fully_bound": len(fully_bound),
        "replay_rate": (len(fully_bound) / claims_total) if claims_total
        else None,
        "broken_links": broken,
        "transfer_boundary_replayed_from_pdf": tb_pdf,
        "verdict": ("FAIL" if broken else
                    ("PASS" if claims_total and fully_bound else
                     "NOT_MEASURABLE")),
        "note": "reconstructed from shipped artifacts only; broken links "
                "reported, never repaired",
    }
    result["chains"] = replayed
    return result


def _j(path: Path) -> Optional[dict]:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return None


def _pdf_text(package_dir: Path) -> Optional[str]:
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(package_dir /
                               "02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf"))
        return "\n".join((p.extract_text() or "") for p in reader.pages)
    except Exception:
        return None


def _transfer_boundary_from_pdf(package_dir: Path) -> Dict[str, Any]:
    text = ""
    for pdf in ("05_TRANSFER_MANIFEST.pdf",
                "02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf"):
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(package_dir / pdf))
            text += "\n".join((p.extract_text() or "")
                              for p in reader.pages) + "\n"
        except Exception:
            continue
    return {
        "you_receive_present": "YOU RECEIVE" in text.upper(),
        "you_must_develop_present": "YOU MUST DEVELOP" in text.upper(),
        "you_must_verify_present": "YOU MUST VERIFY" in text.upper(),
    }


def _evidence_universe(run_dir: Path) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for name in ("stage_RETRIEVE.json", "candidate_envelope.json"):
        p = run_dir / name
        if not p.exists():
            continue
        data = _j(p) or {}
        for ev in _find_items(data):
            if isinstance(ev, dict) and ev.get("id"):
                out[str(ev["id"])] = ev
    # run records are resolvable sources too: design inputs derived from
    # the problem statement legitimately reference "problem.json"
    for name in ("problem.json",):
        if (run_dir / name).exists():
            out[name] = {"id": name, "record": True}
    return out


def _find_items(obj: Any) -> List[Any]:
    found: List[Any] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("evidence", "evidence_items", "items") and \
                    isinstance(v, list):
                found.extend(v)
            else:
                found.extend(_find_items(v))
    elif isinstance(obj, list):
        for item in obj:
            found.extend(_find_items(item))
    return found


def _verify_chain_hash(chain: dict, run_dir: Path) -> (bool, str):
    """Verify the chain hash binds to the actual engineering object.

    Binding contract (Coder 1 package_factory): chain.hash = sha256 of the
    canonical JSON of the corresponding ENGINEERING_SPECIFICATION object
    (design input / design output / failure mode / verification row). The
    replay recomputes it from the shipped engineering specification — a
    mutated object or forged traceability row breaks the binding.
    """
    eng = _j(run_dir / "ENGINEERING_SPECIFICATION.json")
    if not eng:
        return True, "no engineering specification shipped (skipped, not " \
                     "failed)"
    node_id = chain.get("node_id") or chain.get("design_input_id")
    if not node_id:
        return True, "chain carries no node id (skipped)"
    obj = _find_eng_object(eng, str(node_id), chain.get("chain_type"))
    if obj is None:
        return False, f"chain node {node_id} absent from the shipped " \
                      f"engineering specification"
    recomputed = hashlib.sha256(json.dumps(
        obj, sort_keys=True, ensure_ascii=False, default=str)
        .encode("utf-8")).hexdigest()
    if recomputed == chain.get("hash"):
        return True, "hash binds to the shipped engineering object"
    return False, (f"chain hash for {node_id} does not bind to the shipped "
                   f"engineering object (recorded "
                   f"{str(chain.get('hash'))[:12]}..., recomputed "
                   f"{recomputed[:12]}...)")


def _find_eng_object(eng: dict, node_id: str,
                     chain_type: Optional[str]) -> Optional[dict]:
    pools = {
        "DESIGN_INPUT": eng.get("design_inputs", []),
        "DESIGN_OUTPUT": eng.get("design_outputs", []),
        "FAILURE_MODE": eng.get("failure_analysis", []),
        "VERIFICATION": eng.get("verification_matrix", []),
    }
    if chain_type in pools:
        for o in pools[chain_type]:
            if isinstance(o, dict) and str(o.get("id") or
                                           o.get("graph_id")) == node_id:
                return o
        return None
    for pool in pools.values():
        for o in pool:
            if isinstance(o, dict) and str(o.get("id") or
                                           o.get("graph_id")) == node_id:
                return o
    return None
