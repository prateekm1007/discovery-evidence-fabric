"""Source substitution (R449 directive Phase 5).

The required behavior:
    source unavailable
           |
    alternate source
           |
    same proposition search
           |
    provenance preserved
           |
    coverage limitation preserved

And the FORBIDDEN ladder (never implemented, test-enforced):
    OpenAlex unavailable -> LLM "knows" the literature -> evidence

Substitution is declared PER FAMILY with a fixed alternate chain and an
explicit coverage-limitation note (what the alternate does NOT cover —
e.g. USPTO text does not cover non-US patents; OpenAlex work indexes do
not carry patent claims). The limitation travels into every run report
that used the substitution, so downstream synthesis can never mistake
"alternate served" for "same coverage".
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

#: the substitution ladders, by registry source_id. Alternates are
#: registry source_ids (evidence-fabric sources) or fabric V2 sources
#: (declared with family "FABRIC_V2" — the existing retrieval system is
#: never modified by substitution; it is only consulted as a declared
#: alternate channel).
SUBSTITUTION_LADDERS: Dict[str, Dict[str, Any]] = {
    "wopto": {
        "family": "E1_patent_intelligence",
        "alternates": ["uspto_patents"],
        "coverage_limitation": (
            "USPTO text covers United States patent applications only; "
            "the worldwide (non-US) bibliographic coverage of WOPTO is "
            "NOT served by the alternate — any worldwide-prior-art "
            "conclusion drawn from the substituted run is coverage-"
            "limited and must be re-run when WOPTO's index is warm"),
    },
    "uspto_patents": {
        "family": "E1_patent_intelligence",
        "alternates": ["wopto"],
        "coverage_limitation": (
            "WOPTO carries bibliographic data + titles + abstracts of "
            "worldwide applications EXCLUDING the United States; US "
            "full-text detail (claims as text) is NOT served"),
    },
    "openalex_mirror": {
        "family": "E2_scientific_intelligence",
        "alternates": ["s2orc_abstracts"],
        "coverage_limitation": (
            "S2ORC abstracts are a different corpus snapshot; citation-"
            "graph neighborhoods of OpenAlex are NOT served by the "
            "alternate"),
    },
    "s2orc_abstracts": {
        "family": "E2_scientific_intelligence",
        "alternates": ["openalex_mirror"],
        "coverage_limitation": (
            "the OpenAlex mirror's works indexes are a different "
            "snapshot; full-text-adjacent abstract curation of S2ORC "
            "is NOT served"),
    },
    "qm9": {
        "family": "E5_chemical_intelligence",
        "alternates": ["chemrag_reactions"],
        "coverage_limitation": (
            "reaction records do not carry molecular electronic-"
            "structure properties (HOMO/LUMO/gap/dipole); property-"
            "based screening conclusions are NOT served"),
    },
    "chemrag_reactions": {
        "family": "E5_chemical_intelligence",
        "alternates": ["qm9"],
        "coverage_limitation": (
            "QM9 property rows do not carry reaction transformations; "
            "reactant->product conclusions are NOT served"),
    },
    # engineering + materials families: no in-fabric alternate exists
    # yet — the honest answer is the coverage limitation, never an
    # LLM-knowledge substitute (Art. IV no-fallback epistemology)
    "openfoam_cases": {
        "family": "E3_engineering_intelligence",
        "alternates": [],
        "coverage_limitation": (
            "no validated-CFD-case alternate in this subset; validated "
            "fluid-mechanism case knowledge is NOT served when this "
            "source is unavailable"),
    },
    "materials_project": {
        "family": "E4_materials_intelligence",
        "alternates": [],
        "coverage_limitation": (
            "no inorganic-formation-energy alternate in this subset; "
            "thermodynamic-stability conclusions are NOT served"),
    },
}


def substitution_ladder() -> Dict[str, Dict[str, Any]]:
    """The declared ladders (a copy — callers may not mutate the
    module-level declaration)."""
    import copy
    return copy.deepcopy(SUBSTITUTION_LADDERS)


def substitute_source(failed_source_id: str,
                      ladder: Dict[str, Dict[str, Any]],
                      available: List[Dict[str, Any]]
                      ) -> Optional[Dict[str, Any]]:
    """Resolve the FIRST alternate of a failed source that is present
    among the registry's available sources.

    Never returns an LLM, never returns None-with-absence-claim:
    None simply means "no declared alternate is available" — the caller
    records the coverage limitation. Provenance is preserved by
    construction: the alternate source's records carry the ALTERNATE's
    source identity (the substitution is recorded in the run report,
    never laundered into the primary's identity).
    """
    entry = ladder.get(failed_source_id) or {}
    for alt_id in entry.get("alternates") or []:
        for s in available:
            if s.get("source_id") == alt_id and \
                    s.get("status") == "PRODUCTION":
                return s
    return None
