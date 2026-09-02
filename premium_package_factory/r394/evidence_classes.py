"""evidence_classes.py — R394 five-way evidence classification and the
mechanism-evidence record answering the CEO's questions.

Classes (CEO directive 11):
  BACKGROUND                 domain literature without the mechanism feature
  ANALOGY                    adjacent-domain evidence (no CSF-shunt bearing)
  DIRECT_MECHANISM_EVIDENCE  the mechanism feature itself, evidenced
  DIRECT_PRIOR_ART           device/patent-shaped records naming the
                             mechanism's device class
  CONTRADICTORY_EVIDENCE     evidence AGAINST the mechanism or its
                             critical assumptions

The buyer-visible MECHANISM_EVIDENCE.json answers, from the classified
records only (no invented content):
  WHAT IS ALREADY KNOWN
  WHAT IS DIFFERENT
  WHY THE DIFFERENCE MATTERS
  WHAT EVIDENCE SUPPORTS IT
  WHAT REMAINS UNKNOWN
No novelty/patentability conclusions (explicitly forbidden).
"""

from __future__ import annotations

CLASSES = ("BACKGROUND", "ANALOGY", "DIRECT_MECHANISM_EVIDENCE",
           "DIRECT_PRIOR_ART", "CONTRADICTORY_EVIDENCE")


def classify_records(records: list) -> dict:
    """Group the classified external evidence records by class."""
    out = {c: [] for c in CLASSES}
    for r in records or []:
        cls = r.get("classification")
        if cls in out:
            out[cls].append({
                "source": r.get("source"),
                "title": r.get("source_title"),
                "snippet": (r.get("source_snippet") or "")[:400],
                "classification_rationale": r.get("classification_rationale"),
                "year": r.get("year"),
                "provenance": r.get("provenance"),
            })
    return out


def build_mechanism_evidence(pkg, statements: dict | None = None) -> dict:
    """MECHANISM_EVIDENCE.json for one package.

    The classification is computed from the package's own classified
    external evidence. The four narrative answers come from RECORDED
    statements (the V3 corrections carry them for P-07); when a package
    has no recorded statements, the fields degrade to None — never
    synthesized (Art. II).
    """
    records = (pkg.eng.get("external_engineering_precedent") or [])
    grouped = classify_records(records)
    st = statements or {}
    direct = grouped["DIRECT_MECHANISM_EVIDENCE"] + \
        grouped["DIRECT_PRIOR_ART"]
    return {
        "package_id": pkg.pkg_id,
        "schema": "R394_MECHANISM_EVIDENCE",
        "classification_scheme": {
            c: _SCHEME[c] for c in CLASSES
        },
        "counts": {c: len(v) for c, v in grouped.items()},
        "what_is_already_known": st.get("what_is_already_known"),
        "what_is_different": st.get("what_is_different"),
        "why_the_difference_matters": st.get("why_the_difference_matters"),
        "what_evidence_supports_it": st.get("what_evidence_supports_it"),
        "what_remains_unknown": st.get("what_remains_unknown"),
        "evidence_by_class": grouped,
        "direct_evidence_count": len(direct),
        "discipline": (
            "Classes are assigned per record with recorded rationale and "
            "provenance (provider, query, retrieval). Adjacent-domain "
            "analogy never supports an invention claim alone (CEO "
            "directive 11). No novelty or patentability conclusion is "
            "drawn anywhere in this record — that determination requires "
            "an exhaustive classification search by qualified counsel."),
    }


_SCHEME = {
    "BACKGROUND": "Domain literature without the specific mechanism "
                  "feature (problem landscape, incumbent state of the art).",
    "ANALOGY": "Adjacent-domain evidence; never sufficient alone for a "
               "mechanism-bearing invention claim.",
    "DIRECT_MECHANISM_EVIDENCE": "The mechanism feature itself is "
                                 "evidenced in the domain.",
    "DIRECT_PRIOR_ART": "Device/patent-shaped records naming the "
                        "mechanism's device class.",
    "CONTRADICTORY_EVIDENCE": "Evidence against the mechanism or its "
                              "critical assumptions.",
}
