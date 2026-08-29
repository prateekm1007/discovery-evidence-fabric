"""Materials evidence policy — the PROPERTY_DATA vs IMPLANT_SUITABILITY
epistemic split (CEO lifecycle directive, 2026-08-29).

Directive, verbatim: "Prioritize open/free sources such as: Materials
Project, NIST, PubChem — but distinguish chemistry/property data from
actual implant-material suitability."

The distinction is NOT cosmetic. A DFT-computed bulk modulus, a measured
crystal structure, and a thermochemical table are evidence about MATTER.
None of them is evidence that a material is fit to be implanted in a
human. Implant suitability is established (or refuted) only by:

    REGULATORY     — 510(k)/PMA material descriptions, predicates
    CLINICAL       — trial outcomes with the material in situ
    ADVERSE_EVENT  — material-related failure reports (MAUDE)
    STANDARDS      — ISO 10993-class biocompatibility standards as
                     recognized by FDA (with their scope sheets)

This module makes the split mechanical:

- Every MATERIALS-role record is stamped
  evidence_dimension=PROPERTY_DATA and
  implant_suitability=NOT_ESTABLISHED_BY_THIS_SOURCE.
- ``assert_implant_suitability_role`` REFUSES to accept implant-suitability
  claims backed by PROPERTY_DATA-role sources (Art. IV: no fallback
  epistemology — a property database may not silently stand in for a
  biocompatibility study).

Constitutional anchors: Art. II (exact evidence, not plausibility),
Art. XXVIII (no silent semantic promotion: property data cannot promote
to suitability), Art. XXVII (threshold provenance — suitability is a
threshold claim and needs threshold-class evidence).
"""

from __future__ import annotations

from typing import List

DIMENSION_PROPERTY_DATA = "PROPERTY_DATA"
DIMENSION_IMPLANT_SUITABILITY = "IMPLANT_SUITABILITY"

IMPLANT_SUITABILITY_NOT_ESTABLISHED = "NOT_ESTABLISHED_BY_THIS_SOURCE"

#: Roles whose records MAY establish implant suitability (evidence-side
#: gate — mirrors the directive's evidence hierarchy, not a coder mood).
SUITABILITY_ESTABLISHING_ROLES = {
    "REGULATORY",
    "CLINICAL",
    "ADVERSE_EVENT",
    "STANDARDS",
}

#: Roles whose records are PROPERTY_DATA by construction.
PROPERTY_DATA_ROLES = {"MATERIALS", "CHEMISTRY"}

_MATERIALS_SOURCE_LIMITATIONS = {
    "COD": [
        "Published crystallographic structures (CIF provenance); measured "
        "matter data, NOT implant suitability evidence.",
        "Structure existence does not establish purity, toxicity, "
        "biocompatibility, or device-grade processing.",
    ],
    "NIST WebBook": [
        "NIST thermophysical reference data for chemical species; property "
        "data, NOT implant suitability evidence.",
        "Species coverage is chemicals/elements — implant alloys and "
        "polymers (Ti-6Al-4V, PEEK, UHMWPE) are largely out of scope as "
        "multi-component engineering solids.",
    ],
    "Materials Project": [
        "Computed (DFT) properties for inorganic compounds — "
        "COMPUTATIONAL evidence class, one modelling abstraction below "
        "measurement (Art. XXXVIII evidence layers).",
        "Computed properties are for idealized bulk phases, NOT "
        "as-manufactured implant material; no biocompatibility content.",
    ],
}

_GENERIC_LIMITATIONS = [
    "Property/structure data about matter; implant suitability is "
    "NOT established by this source.",
]


def materials_limitations(source_label: str) -> List[str]:
    return list(_MATERIALS_SOURCE_LIMITATIONS.get(source_label, _GENERIC_LIMITATIONS))


def assert_implant_suitability_role(source_role: str) -> None:
    """Raise if a record from ``source_role`` is used to establish implant
    suitability. The evidence side decides, not the claimant (Art. III)."""
    role = (source_role or "").upper()
    if role in SUITABILITY_ESTABLISHING_ROLES:
        return
    raise ValueError(
        f"implant suitability cannot be established by a {source_role!r} "
        f"source; allowed evidence roles: "
        f"{sorted(SUITABILITY_ESTABLISHING_ROLES)} (Art. XXVIII — no "
        f"silent semantic promotion from property data)"
    )


def classify_material_evidence(record) -> dict:
    """Classify a record's material-evidence dimension.

    Returns a dict with evidence_dimension and implant_suitability. For
    MATERIALS/CHEMISTRY sources the answer is always PROPERTY_DATA /
    NOT_ESTABLISHED — regardless of what a claimant attached to the
    record (the verifier decides, Art. III).
    """
    role = getattr(record, "role", "") or ""
    if role.upper() in PROPERTY_DATA_ROLES:
        return {
            "evidence_dimension": DIMENSION_PROPERTY_DATA,
            "implant_suitability": IMPLANT_SUITABILITY_NOT_ESTABLISHED,
            "establishing_role_required": sorted(SUITABILITY_ESTABLISHING_ROLES),
        }
    if role.upper() in SUITABILITY_ESTABLISHING_ROLES:
        return {
            "evidence_dimension": DIMENSION_IMPLANT_SUITABILITY,
            "implant_suitability": "ESTABLISHABLE_FROM_THIS_SOURCE",
            "note": "suitability still requires the exact evidence span, "
                    "not the source's mere existence (Art. II)",
        }
    return {
        "evidence_dimension": "UNKNOWN",
        "implant_suitability": "UNKNOWN",
        "note": "role outside the materials evidence split; unknown "
                "stays unknown (Art. XXV)",
    }
