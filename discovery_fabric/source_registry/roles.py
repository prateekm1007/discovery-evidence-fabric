"""Authority roles for the source registry (CEO database-layer directive).

A source's authority_role defines WHAT KIND OF EVIDENCE it is authoritative
for. Roles are the unit of the auditable coverage matrix: a role is covered
only when at least one source measured LIVE serves it.

Constitutional anchors:
- Art. XXI: a source being listed is NOT evidence it is integrated; coverage
  is a MEASURED property (see health.py / SOURCE_HEALTH_REPORT).
- Art. XXV: UNKNOWN stays UNKNOWN — a role with no live source stays an
  honest gap, never a silently-passed one.
"""

from __future__ import annotations

ROLE_DEFINITIONS = {
    "SCIENTIFIC": (
        "Peer-reviewed literature, preprints, and citation graphs. "
        "Authoritative for: mechanism evidence, prior scientific art, "
        "quantities reported in publications."
    ),
    "PATENT": (
        "Patent corpora and patent-family/claim structures. Authoritative "
        "for: prior patented art, claim language, priority dates, families."
    ),
    "REGULATORY": (
        "Regulatory-body records (clearances, approvals, classifications, "
        "registrations). Authoritative for: what reached a regulator, under "
        "which pathway, with which predicate."
    ),
    "DEVICE_IDENTITY": (
        "Device identification registries (UDI/GUDID). Authoritative for: "
        "device identity, identifiers, and manufacturer linkage."
    ),
    "CLINICAL": (
        "Clinical-trial registries. Authoritative for: what has been tested "
        "clinically, on which populations, with which outcomes status."
    ),
    "ADVERSE_EVENT": (
        "Post-market adverse-event reporting systems (e.g., MAUDE). "
        "Authoritative ONLY as a signal source (Art. XXI.5): report counts "
        "are NOT incidence; causality is NOT established by a report."
    ),
    "RECALL": (
        "Recall and enforcement records. Authoritative for: what was "
        "recalled, why (recall reason), and classification severity."
    ),
    "MATERIALS": (
        "Materials property databases. Authoritative for: measured material "
        "properties with provenance to the measurement source."
    ),
    "CHEMISTRY": (
        "Chemical compound databases. Authoritative for: compound identity "
        "and computed/measured chemical properties."
    ),
    "BIOLOGY": (
        "Protein/sequence/bioassay databases. Authoritative for: biological "
        "entity identity, function annotations, assay activities."
    ),
    "MANUFACTURING": (
        "Manufacturing and process-evidence sources. Authoritative for: "
        "process capability, tolerance practice, fabrication constraints."
    ),
    "STANDARDS": (
        "Consensus standards and their regulatory recognition. "
        "Authoritative for: test methods, acceptance criteria, and "
        "standard designations a regulator recognizes."
    ),
    "COMMERCIAL": (
        "Procurement, company, and product-reality data. Authoritative for: "
        "what is actually marketed, by whom, at what price point."
    ),
    "INCIDENT": (
        "Cause-coded accident/incident regulatory reports outside "
        "healthcare (rail Form 54, transport, industrial). Authoritative "
        "for: what failed in service, under which cause classification, "
        "with which severity. Cause codes are classifications of the "
        "initial report, NOT proven root causes (Art. XXI.5-analog)."
    ),
    "HAZARD_EVENT": (
        "Instrument-measured natural-hazard events (seismic, etc.). "
        "Authoritative for: hazard EXPOSURE inputs to infrastructure/"
        "resilience problems. A hazard event is NOT an engineering-"
        "failure record; consequences require engineering corpora."
    ),
    "EXPERIMENT": (
        "Funded research-attempt records (grants/projects with objectives, "
        "dates, and where available outcomes). Authoritative for: WHAT WAS "
        "TRIED, at what scale, with which declared objectives — the "
        "attempt-outcome universe beyond publication bias (a funded "
        "attempt that never published is still an attempt). Project "
        "records establish that research HAPPENED and what it targeted; "
        "they do NOT establish that a mechanism works (absence of a "
        "positive outcome is not evidence of failure — Art. XXV)."
    ),
}

# Roles the CEO coverage matrix reports on (directive-specified order).
COVERAGE_MATRIX_ROLES = [
    "SCIENTIFIC", "PATENT", "REGULATORY", "DEVICE_IDENTITY",
    "ADVERSE_EVENT", "RECALL", "CLINICAL", "MATERIALS",
    "MANUFACTURING", "STANDARDS", "CHEMISTRY", "BIOLOGY", "COMMERCIAL",
    "INCIDENT", "HAZARD_EVENT", "EXPERIMENT",
]

VALID_ROLES = set(ROLE_DEFINITIONS)


def validate_role(role: str) -> None:
    if role not in VALID_ROLES:
        raise ValueError(
            f"Unknown authority role {role!r}; valid roles: {sorted(VALID_ROLES)}"
        )
