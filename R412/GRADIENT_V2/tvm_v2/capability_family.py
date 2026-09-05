"""tvm_v2.capability_family — the typed capability-abstraction layer (Step 5).

Operator directive (R412 gradient v2, Step 5): add a deterministic/typed
capability_family layer with:
    exact_capability, capability_family, measurement_dimension,
    required_regime, target_constraint
so the TVM can search for a technological frontier using the underlying
CAPABILITY, not merely the terminology appearing in the death record.

Example from the directive (the seeded canonical demonstration mapping):
    "10-100x misalignment vs deflection"
        -> actuation/control precision       (capability_family)
        -> dynamic positioning                (search vocabulary)
        -> closed-loop disturbance rejection  (search vocabulary)

Constitutional basis:
  - Article XLIII (search-space neutrality): the search vocabulary is
    DERIVED_FROM_EVIDENCE when it is bound to a recorded failure/limiting
    capability, or explicitly labeled EXPLORATORY_HYPOTHESIS otherwise.
    Both labels are machine-enforced; unlabeled vocabulary is invalid.
  - Article II (exact beats semantic): family lookup is by exact key
    (family_id, exact_capability, or a listed alias). There is NO fuzzy
    or embedding-based family matching in this layer. A miss returns
    EMPTY (recorded), never a nearest-neighbor guess.
  - Article VI (never manufacture provenance): every family entry
    records where it came from. The single seeded entry's provenance is
    the operator directive's own example — nothing else is invented.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

FAMILY_MAP_PATH = Path(__file__).resolve().parent.parent / \
    "CAPABILITY_FAMILY_MAP.json"

REQUIRED_FAMILY_FIELDS = [
    "family_id",
    "exact_capability",
    "capability_family",
    "measurement_dimension",
    "required_regime",
    "target_constraints",
    "search_vocabulary",
    "derivation_status",
    "provenance",
]

DERIVATION_STATUSES = ["DERIVED_FROM_EVIDENCE", "EXPLORATORY_HYPOTHESIS"]

_CACHE: Optional[Dict[str, Any]] = None


def load_family_map(path: Optional[Path] = None) -> Dict[str, Any]:
    """Load (and cache) the frozen capability-family map."""
    global _CACHE
    if _CACHE is not None and path is None:
        return _CACHE
    data = json.loads((path or FAMILY_MAP_PATH).read_text(encoding="utf-8"))
    _CACHE = data
    return data


def validate_family_entry(entry: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Deterministically validate one family entry against the typed schema."""
    issues: List[str] = []
    for f in REQUIRED_FAMILY_FIELDS:
        if f not in entry or entry[f] in (None, "", [], {}):
            issues.append(f"missing_field:{f}")
    if entry.get("derivation_status") not in DERIVATION_STATUSES:
        issues.append("invalid_derivation_status")
    vocab = entry.get("search_vocabulary", [])
    if not isinstance(vocab, list) or not all(isinstance(v, str) and v
                                              for v in vocab):
        issues.append("search_vocabulary_not_string_list")
    regime = entry.get("required_regime", {})
    if not isinstance(regime, dict) or not regime:
        issues.append("required_regime_not_typed_object")
    return len(issues) == 0, issues


def validate_family_map(path: Optional[Path] = None) -> Tuple[bool, List[str]]:
    """Validate the whole frozen map (used by tests and seal verification)."""
    data = load_family_map(path)
    issues: List[str] = []
    families = data.get("families", [])
    ids = [f.get("family_id") for f in families]
    if len(ids) != len(set(ids)):
        issues.append("duplicate_family_ids")
    for f in families:
        ok, fam_issues = validate_family_entry(f)
        if not ok:
            issues.extend(f"{f.get('family_id', '?')}:{p}"
                          for p in fam_issues)
    return len(issues) == 0, issues


def validate_family_reference(ref: str) -> Tuple[bool, List[str]]:
    """Check that a TVM entry's capability_family_ref resolves exactly."""
    data = load_family_map()
    ids = {f["family_id"] for f in data.get("families", [])}
    if ref in ids:
        return True, []
    return False, [f"unresolved_family_reference:{ref}"]


def expand_search_vocabulary(query: str) -> List[str]:
    """Deterministic exact-key expansion of a query to search vocabulary.

    Matches by exact_capability, exact capability text, or a listed alias.
    NO fuzzy matching: a miss returns [] (the caller records the miss;
    it never guesses a nearest family).
    """
    data = load_family_map()
    q = query.strip().lower()
    for f in data.get("families", []):
        keys = [f.get("exact_capability", "").strip().lower()]
        keys += [a.strip().lower() for a in f.get("aliases", [])]
        if q and q in keys:
            return list(f.get("search_vocabulary", []))
    return []
