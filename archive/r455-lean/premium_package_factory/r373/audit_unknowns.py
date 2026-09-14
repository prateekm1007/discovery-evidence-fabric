"""
audit_unknowns.py — R373-6: audit every UNKNOWN.

Each unknown in the shipped UNKNOWN_ROADMAP.json must identify:
    why_unknown            the record-state reason (non-empty)
    what_would_resolve_it  resolution action (non-empty)
    method                 the resolution method (non-empty)
    responsible_function   the owning function (non-empty, or an explicit
                           not-assignable statement)
    decision_impact        the recorded impact (non-empty)

Anti-gaming invariants (Constitution Art. XXV — unknown must remain
unknown; CEO R373-6: "Do not reduce UNKNOWN simply to increase the
release score"):
  * COUNT_PRESERVED   roadmap count == canonical remaining_unknowns count
  * NO_RESOLUTION_INFLATION  the FUNDAMENTALLY_UNRESOLVED / unresolved
                      classifications are not silently converted to
                      easier classes; the shipped classification of every
                      unknown is re-derived mechanically from the same
                      rules and must match
  * NO_DROPPED_UNKNOWNS  every canonical unknown statement appears in the
                      roadmap verbatim
"""

import re

_RULES = [
    ("LEGAL_IP_REQUIRED",
     re.compile(r"\b(patent|FTO|freedom to operate|novelty determination|"
                r"licens)", re.I)),
    ("REGULATORY_REQUIRED",
     re.compile(r"(regulatory|FDA|510\(k\)|PMA\b|clearance|ISO 10993|"
                r"biocompatib|IEC 60601|ISO 14708|clinical endpoint|"
                r"surrogate endpoint|classification as)", re.I)),
    ("FUNDAMENTALLY_UNRESOLVED",
     re.compile(r"(dataset|training data|no real data|clinical data|"
                r"in vivo|clinical trial|clinical benefit|revision "
                r"reduction|market|reimburse)", re.I)),
    ("COMPUTATION_RESOLVABLE",
     re.compile(r"(simulat|computational|in silico|finite element|CFD)",
                re.I)),
    ("LITERATURE_RESOLVABLE",
     re.compile(r"(literature|published|citation|prior art|reported in)",
                re.I)),
    ("ENGINEERING_DESIGN_REQUIRED",
     re.compile(r"(technology choice|\bchoice\b|\bselect\b|cost vs|value "
                r"analysis|battery life|architecture|controller gains|"
                r"duty cycle|vs\b.*vs\b|power budget|optimal frequency|"
                r"balancing)", re.I)),
    ("BENCH_TEST_REQUIRED",
     re.compile(r"(process capability|Cpk|extrusion|half-life|fouling|"
                r"drift|infectivity|retention|competition|surface density|"
                r"deactivation|assay|in CSF environment|CSF/catheter "
                r"environment|strain amplitude|chronic implant "
                r"environment|rate in|measured|irradiance|scale-up|"
                r"\befficiency\b)", re.I)),
]

_REQUIRED_FIELDS = ("why_unknown", "what_would_resolve_it", "method",
                    "responsible_function", "decision_impact")


def _expected_classification(unknown: str, pkg=None) -> str:
    """Full mechanical rule chain, mirroring the disclosed R371 rules:
    keyword rules in priority order, then recorded-parameter basis, then
    the achievable-default, then the honest FUNDAMENTALLY_UNRESOLVED
    default."""
    for cls, pattern in _RULES:
        if pattern.search(unknown):
            return cls
    if pkg is not None:
        import re as _re
        topic = unknown.split("—")[0].split("--")[0].strip(" -")
        for cp in pkg.critical_parameters:
            name = cp.get("name") or ""
            if name and name.split()[0].lower() in topic.lower().split():
                basis = (cp.get("basis") or "").lower()
                ver = (cp.get("verification_requirement") or "").lower()
                if "design choice" in basis:
                    return "ENGINEERING_DESIGN_REQUIRED"
                if _re.search(r"bench|test|assay|measure|calibrat", ver):
                    return "BENCH_TEST_REQUIRED"
        if _re.match(r"\s*Achievable\b", unknown):
            return "BENCH_TEST_REQUIRED"
    return "FUNDAMENTALLY_UNRESOLVED"  # NO_MECHANICAL_RULE default


def audit_unknowns(pkg, shipped: dict) -> dict:
    failures = []
    canonical = [str(u) for u in pkg.unknowns]
    entries = shipped.get("unknowns", [])

    # COUNT_PRESERVED
    if shipped.get("unknown_count_source") != len(canonical):
        failures.append({"check": "COUNT_SOURCE_MISMATCH",
                         "detail": f"declared source count "
                                   f"{shipped.get('unknown_count_source')} "
                                   f"!= canonical {len(canonical)}"})
    if len(entries) != len(canonical):
        failures.append({"check": "COUNT_NOT_PRESERVED",
                         "detail": f"roadmap carries {len(entries)} "
                                   f"unknowns, canonical record has "
                                   f"{len(canonical)} — UNKNOWNs may not "
                                   f"be reduced to increase the release "
                                   f"score"})

    # NO_DROPPED_UNKNOWNS (verbatim statements)
    shipped_statements = {e.get("unknown_statement") for e in entries}
    for u in canonical:
        if u not in shipped_statements:
            failures.append({"check": "UNKNOWN_DROPPED",
                             "detail": f"canonical unknown not in roadmap: "
                                       f"{u[:80]!r}"})

    # five required fields per unknown
    for e in entries:
        for field in _REQUIRED_FIELDS:
            v = str(e.get(field, "")).strip()
            if not v:
                failures.append({"check": "FIELD_MISSING",
                                 "detail": f"{e.get('unknown_id')} lacks a "
                                           f"non-empty {field}"})
            elif v.upper() in ("N/A", "NOT_APPLICABLE", "TBD"):
                failures.append({"check": "FIELD_PLACEHOLDER",
                                 "detail": f"{e.get('unknown_id')}." 
                                           f"{field} is a placeholder"})

    # NO_RESOLUTION_INFLATION: classification re-derived mechanically
    for e in entries:
        expected = _expected_classification(e.get("unknown_statement", ""),
                                            pkg)
        if e.get("classification") != expected:
            failures.append({
                "check": "CLASSIFICATION_DRIFT",
                "detail": (f"{e.get('unknown_id')} shipped "
                           f"{e.get('classification')!r}; mechanical "
                           f"re-derivation gives {expected!r} — a shipped "
                           f"easier class would inflate the release score"),
            })

    # classification counts consistent with entries
    counts = {}
    for e in entries:
        counts[e.get("classification")] = \
            counts.get(e.get("classification"), 0) + 1
    for cls, n in (shipped.get("classification_counts") or {}).items():
        if counts.get(cls, 0) != n:
            failures.append({"check": "COUNT_TABLE_DRIFT",
                             "detail": f"{cls}: declared {n}, entries "
                                       f"carry {counts.get(cls, 0)}"})

    return {
        "package_id": pkg.pkg_id,
        "canonical_unknown_count": len(canonical),
        "roadmap_unknown_count": len(entries),
        "required_fields": list(_REQUIRED_FIELDS),
        "failures": failures,
        "ok": not failures,
    }
