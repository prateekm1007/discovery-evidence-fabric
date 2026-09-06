"""selection.py — deterministic solver selection (R413 Physics Stack V1).

THE OPERATOR'S RULE: "with the AI deciding which solver(s) a proposed
invention actually requires."

ROLE-SEPARATION READING (Art. XLV, the repo's standing pattern):
  the AI (PROPOSER) may PROPOSE which physical phenomena a mechanism
  engages — as TYPED phenomenon class ids from the closed vocabulary
  below (search-space neutrality, Art. XLIII analog: no invented
  phenomenon classes, no 'ALL_PHYSICS').
  The MAPPING phenomenon -> solver is DETERMINISTIC CODE (zero LLM —
  the same discipline as the retrieval-resilience RETRIEVER role).
  No single model controls both what physics is claimed and what
  computes it.

FAIL-CLOSED (Art. IV):
  - phenomenon not in the vocabulary -> PHENOMENON_NOT_COVERED refusal;
    the layer NEVER silently substitutes an available solver for an
    unavailable one (a forced analogy is the R394 V0's declared sin,
    and it stays a sin at stack scale).
  - solver not installed -> refusal carries the honest state
    (PROBED_NOT_INSTALLED) + the alternates list; it is an
    infrastructure fact, never a scientific verdict (Art. LXI).
  - visualization / orchestration records are UNSELECTABLE for physics
    (empty phenomenon_classes by schema — enforced again here).
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List

from discovery_fabric.physics_stack.solver_registry import (
    SOLVER_REGISTRY, validate_registry,
)

#: The closed phenomenon vocabulary — exactly the coverage registry's
#: phenomena (loaded and cross-checked at import; a mismatch is a hard
#: import failure, never a silent drift).
def _load_vocabulary() -> List[str]:
    from discovery_fabric.physics_stack.coverage import (
        load_coverage_registry,
    )
    reg = load_coverage_registry()
    return [e["phenomenon"] for e in reg["entries"]]


PHENOMENON_VOCABULARY: List[str] = _load_vocabulary()

_VOCAB_SET = set(PHENOMENON_VOCABULARY)

SELECTION_STATE_SELECTED = "SELECTED"
SELECTION_STATE_NOT_INSTALLED = "REFUSED_SOLVER_NOT_INSTALLED"
SELECTION_STATE_NOT_COVERED = "REFUSED_PHENOMENON_NOT_COVERED"
SELECTION_STATE_NO_SOLVER = "REFUSED_NO_SOLVER_REGISTERED"


def select_solvers(phenomenon_classes: List[str]) -> Dict[str, Any]:
    """Deterministic selection. Byte-identical output for identical
    input (the selection record itself is hashed — callers and tests
    verify determinism, Art. LXII)."""
    registry_problems = validate_registry()
    if registry_problems:
        return {
            "state": "REFUSED_REGISTRY_INVALID",
            "reasons": registry_problems,
            "note": "a registry that fails self-validation may not "
                    "drive solver selection (Art. XVI: code is a "
                    "hypothesis; validate_registry is the evidence)",
        }

    seen: set = set()
    requested: List[str] = []
    duplicates: List[str] = []
    for ph in phenomenon_classes:
        if ph in seen:
            duplicates.append(ph)
            continue
        seen.add(ph)
        requested.append(ph)

    selections: List[Dict[str, Any]] = []
    refusals: List[Dict[str, Any]] = []
    for ph in requested:
        if ph not in _VOCAB_SET:
            refusals.append({
                "phenomenon": ph,
                "state": SELECTION_STATE_NOT_COVERED,
                "reason": (f"phenomenon {ph!r} is not in the closed "
                           "vocabulary — the PROPOSER may only name "
                           "registered phenomenon classes (Art. XLIII: "
                           "no invented physics classes; Art. IV: no "
                           "fallback onto a neighboring phenomenon)"),
            })
            continue
        candidates = [r for r in SOLVER_REGISTRY
                      if ph in r["phenomenon_classes"]]
        if not candidates:
            refusals.append({
                "phenomenon": ph,
                "state": SELECTION_STATE_NO_SOLVER,
                "reason": "no solver registers this phenomenon — "
                          "MECHANISM_NOT_SIMULATABLE (fail-closed, "
                          "never a forced analogy)",
            })
            continue
        # deterministic: registry order; installed solvers preferred over
        # not-installed alternates (an independent available solver beats
        # a blocked primary — the retrieval-resilience router principle,
        # applied to solvers)
        installed = [r for r in candidates
                     if r["availability"]["state"] == "INSTALLED"]
        pool = installed or candidates
        chosen = pool[0]
        state = (SELECTION_STATE_SELECTED
                 if chosen["availability"]["state"] == "INSTALLED"
                 else SELECTION_STATE_NOT_INSTALLED)
        selections.append({
            "phenomenon": ph,
            "solver_id": chosen["solver_id"],
            "solver_version": chosen["solver_version"],
            "state": state,
            "availability": chosen["availability"]["state"],
            "availability_probe": chosen["availability"].get("probe"),
            "alternates": [r["solver_id"] for r in candidates
                           if r["solver_id"] != chosen["solver_id"]],
            "reason": (None if state == SELECTION_STATE_SELECTED else
                       f"solver {chosen['solver_id']} is "
                       f"{chosen['availability']['state']} in this "
                       "environment (MEASURED, Art. VI) — an "
                       "infrastructure fact, never a scientific "
                       "verdict (Art. LXI); alternates listed"),
        })

    n_selected = sum(1 for s in selections
                     if s["state"] == SELECTION_STATE_SELECTED)
    doc = {
        "requested_phenomena": requested,
        "duplicate_requests_ignored": duplicates,
        "selections": selections,
        "refusals": refusals,
        "n_selected_installable": n_selected,
        "n_refused": len(refusals) + sum(
            1 for s in selections
            if s["state"] == SELECTION_STATE_NOT_INSTALLED),
        "execution_allowed": n_selected > 0 and not refusals and all(
            s["state"] == SELECTION_STATE_SELECTED
            for s in selections),
        "role_separation": {
            "proposer_role": "the AI PROPOSES typed phenomenon classes "
                             "(from the closed vocabulary) — it never "
                             "selects solvers",
            "selector_role": "deterministic code (this module; zero LLM)",
            "llm_in_selection": False,
        },
        "determinism_note": "identical input -> byte-identical record "
                            "(the selection hash below is computed over "
                            "the canonical serialization)",
    }
    doc["selection_sha256"] = hashlib.sha256(
        json.dumps({k: v for k, v in doc.items()
                    if k != "selection_sha256"},
                   sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()
    return doc
