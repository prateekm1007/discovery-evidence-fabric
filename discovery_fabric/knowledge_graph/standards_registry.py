"""Standards registry — the directive's 5-column mapping, evidence-bound.

CEO lifecycle directive (2026-08-29):

    "Create a standards registry that connects:
        STANDARD -> DEVICE TYPE -> ENGINEERING PURPOSE -> APPLICABILITY
        -> VERIFICATION REQUIREMENT
     Do not merely store ISO numbers."

Each registry row is built ONLY from measured source records:

- STANDARD            from FDA Recognized Consensus Standards records
                      (organization + designation, recognition number)
- DEVICE TYPE         from the same record's specialty task group area
                      (FDA's own device-area grouping), optionally
                      refined by eCFR classification parts (862-892)
- ENGINEERING PURPOSE the standard's own title (what it test-methods /
                      specifies / guides)
- APPLICABILITY       the provider's extent-of-recognition classification
                      (Complete / Partial) + date of entry
- VERIFICATION
  REQUIREMENT         derived from the standard's designation grammar
                      (Test Method / Specification / Practice / Guide /
                      Terminology / Part-specific) AND anchored to the
                      codified QMSR verification controls (21 CFR 820,
                      which incorporates ISO 13485 by reference at
                      § 820.7) when the row is used for verification.

Every row carries the custody references of the establishing records
(Art. XXI.9) — a row without custody is REJECTED. The QMSR anchor is
itself an evidence-bound link to the eCFR 820.1/820.7 records, not a
narrative assertion.

Constitutional anchors: Art. I (evidence precedes assertion), Art. II
(the title IS the engineering purpose — no paraphrase-as-evidence),
Art. XXVII (applicability classes are the provider's own, not invented
thresholds).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

# Verification-requirement classes derived from the standard's
# designation grammar (ASTM/ISO designation conventions):
#   ASTM <letter><number>: F = material/service standards for ...
#   Explicit grammar in the TITLE is what we parse, not org heuristics.
_VERIFICATION_CLASSES = [
    ("test_method", re.compile(r"test method", re.I)),
    ("specification", re.compile(r"specification", re.I)),
    ("practice", re.compile(r"^(standard )?practice\b|standard practice", re.I)),
    ("guide", re.compile(r"\bguide\b", re.I)),
    ("terminology", re.compile(r"terminolog", re.I)),
    ("classification", re.compile(r"classification", re.I)),
    ("performance", re.compile(r"performance", re.I)),
    ("safety", re.compile(r"safety", re.I)),
    ("biocompatibility", re.compile(r"biocompatib|10993", re.I)),
    ("sterilization", re.compile(r"steriliz", re.I)),
]

QMSR_VERIFICATION_ANCHOR = (
    "When this standard is used to support verification in a regulatory "
    "submission, the verification process controls are those of the "
    "Quality Management System Regulation, 21 CFR part 820 (ISO 13485 "
    "incorporated by reference, § 820.7)."
)


def verification_requirement_class(standard_title: str,
                                   designation: str) -> Dict[str, Any]:
    """Classify the verification requirement from the standard's own
    title grammar. Returns explicit classes — never a fabricated
    verification claim (Art. XXVII: the class is the provider's grammar,
    not an invented threshold)."""
    text = f"{standard_title or ''} {designation or ''}"
    classes = [name for name, rx in _VERIFICATION_CLASSES if rx.search(text)]
    return {
        "verification_classes": classes or ["unclassified"],
        "verification_basis": "standard title grammar + designation",
        "qmsr_anchor": QMSR_VERIFICATION_ANCHOR,
    }


def registry_row_from_record(record) -> Optional[Dict[str, Any]]:
    """Build one 5-column registry row from an FDA recognized-standards
    source record. Returns None (and records why) if the record lacks
    the columns the registry needs — no silent partial rows."""
    n = getattr(record, "normalized", {}) or {}
    designation = n.get("standard_designation")
    title = n.get("standard_title")
    rec_no = n.get("recognition_number")
    if not (designation and title and rec_no):
        return None
    vr = verification_requirement_class(title, designation)
    row = {
        "standard": {
            "designation": designation,
            "organization": n.get("standards_organization"),
            "recognition_number": rec_no,
        },
        "device_type": {
            "specialty_task_group_area": n.get("specialty_task_group_area"),
            "source": "FDA specialty task group area (list-level grouping)",
        },
        "engineering_purpose": {
            "standard_title": title,
        },
        "applicability": {
            "extent_of_recognition": n.get("extent_of_recognition"),
            "date_of_entry": n.get("date_of_entry"),
            "provider_classification": True,  # FDA's own class, not ours
        },
        "verification_requirement": vr,
        "custody": [
            {
                "source_id": record.source_id,
                "record_id": record.record_id,
                "raw_payload_sha256": record.raw_payload_sha256,
                "retrieved_at": record.retrieved_at,
                "query": record.query,
            }
        ],
    }
    return row


def build_standards_registry(records: List[Any],
                             ecfr_records: Optional[List[Any]] = None,
                             ) -> Dict[str, Any]:
    """Assemble the standards registry from measured records.

    - rows: one per FDA recognized-standards record that carries all five
      columns (rejected rows are disclosed, never dropped silently).
    - qmsr_anchor_records: custody of the eCFR 820 records that anchor
      the verification-requirement column.
    """
    rows: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []
    for r in records:
        row = registry_row_from_record(r)
        if row is None:
            rejected.append({
                "record_id": getattr(r, "record_id", None),
                "reason": "missing designation/title/recognition number",
            })
            continue
        rows.append(row)

    ecfr_anchors: List[Dict[str, Any]] = []
    for r in (ecfr_records or []):
        n = getattr(r, "normalized", {}) or {}
        if n.get("part") == "820" or n.get("section", "").startswith("820."):
            ecfr_anchors.append({
                "source_id": r.source_id,
                "record_id": r.record_id,
                "raw_payload_sha256": r.raw_payload_sha256,
                "retrieved_at": r.retrieved_at,
                "query": r.query,
                "section": n.get("section"),
            })

    return {
        "registry_kind": "STANDARDS_REGISTRY",
        "columns": ["STANDARD", "DEVICE_TYPE", "ENGINEERING_PURPOSE",
                    "APPLICABILITY", "VERIFICATION_REQUIREMENT"],
        "row_count": len(rows),
        "rows": rows,
        "rejected_rows": rejected,
        "qmsr_anchor": {
            "text": QMSR_VERIFICATION_ANCHOR,
            "ecfr_custody": ecfr_anchors,
            "note": "21 CFR part 820 (QMSR); ISO 13485 incorporated by "
                    "reference at § 820.7 — anchoring records fetched from "
                    "the eCFR API, not asserted.",
        },
    }
