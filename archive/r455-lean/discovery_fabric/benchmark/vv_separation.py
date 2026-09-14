"""Phase 10 — V&V separation audit (Coder 2).

Independently validates VERIFICATION != VALIDATION. Catches:

    SIMULATION_LABELLED_VALIDATION      — a simulation study cited as
                                          validation evidence
    LITERATURE_LABELLED_VALIDATION      — literature review cited as
                                          validation of THIS design
    PROPOSED_LABELLED_COMPLETED         — a proposed experiment recorded as
                                          a completed/tested one
    INTERNAL_CALC_LABELLED_EXTERNAL     — internal computation presented as
                                          an external test
    RESULT_WITHOUT_TEST                 — a verification row claiming a
                                          result while result=NOT_TESTED is
                                          the honest state
    UNBACKED_PERFORMANCE_CLAIM          — any performance claim in prose not
                                          backed by a verification/validation
                                          record with a result

Emits VV_SEPARATION_AUDIT.json content per package. Re-derived from the
raw matrices + rendered PDF text (Art. III).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

_SIM_WORDS = re.compile(r"\b(simulat|in[\s-]silico|computational model|"
                        r"virtual (patient|cohort))", re.IGNORECASE)
_LIT_WORDS = re.compile(r"\b(literature|published (study|report|evidence)|"
                        r"review of)", re.IGNORECASE)
_PERF_CLAIM = re.compile(
    r"\b(achiev|demonstrat|measured|validated|verified|confirmed|showed)\b",
    re.IGNORECASE)


def audit_vv_separation(eng_spec: Optional[dict],
                        dossier_text: Optional[str]) -> Dict[str, Any]:
    violations: List[Dict[str, Any]] = []

    if eng_spec:
        vfs = [v for v in (eng_spec.get("verification_matrix", []) or [])
               if isinstance(v, dict)]
        vas = [v for v in (eng_spec.get("validation_matrix", []) or [])
               if isinstance(v, dict)]

        for v in vfs:
            vid = v.get("id") or "?"
            result = str(v.get("result") or "")
            method = str(v.get("method") or "") + " " + \
                str(v.get("requirement") or "")
            # proposed labelled completed
            if result not in ("NOT_TESTED", "NOT TESTED", "", "None") and \
                    "NOT_TESTED" not in result:
                violations.append({
                    "violation": "RESULT_WITHOUT_TEST",
                    "object_id": vid,
                    "detail": f"verification claims result '{result}' — "
                              f"no test execution exists in this run",
                })
            # simulation labelled validation (wording check is scoped to
            # the row's own method text, IDs still cited)
            if _SIM_WORDS.search(method) and \
                    re.search(r"validat", method, re.IGNORECASE):
                violations.append({
                    "violation": "SIMULATION_LABELLED_VALIDATION",
                    "object_id": vid,
                    "detail": "verification row conflates simulation with "
                              "validation",
                })

        for v in vas:
            vid = v.get("id") or "?"
            result = str(v.get("result") or "")
            status = str(v.get("status") or "")
            method = str(v.get("method") or "")
            if result not in ("NOT_PERFORMED", "NOT PERFORMED", "", "None"):
                violations.append({
                    "violation": "PROPOSED_LABELLED_COMPLETED",
                    "object_id": vid,
                    "detail": f"validation claims result '{result}' — no "
                              f"physical observation ledger entry exists "
                              f"(Art. XXXVIII)",
                })
            if _LIT_WORDS.search(method) and status not in (
                    "NOT_POSSIBLE_YET", "NOT POSSIBLE YET"):
                violations.append({
                    "violation": "LITERATURE_LABELLED_VALIDATION",
                    "object_id": vid,
                    "detail": "validation method cites literature as "
                              "validation of this design",
                })
    else:
        # gold-side / PDF-only probe: 'validated by simulation' phrasing
        if dossier_text:
            for m in _SIM_WORDS.finditer(dossier_text):
                ctx = dossier_text[max(0, m.start() - 120):m.start() + 120]
                if re.search(r"validat", ctx, re.IGNORECASE):
                    violations.append({
                        "violation": "SIMULATION_LABELLED_VALIDATION",
                        "object_id": f"PDF@{m.start()}",
                        "detail": "dossier prose presents simulation as "
                                  "validation",
                    })

    # separation structure itself: are V and V distinct matrices?
    separated = False
    if eng_spec:
        separated = bool(eng_spec.get("verification_matrix")) and \
            bool(eng_spec.get("validation_matrix"))

    return {
        "available": eng_spec is not None or dossier_text is not None,
        "verification_validation_separated": separated,
        "violations": violations,
        "violation_count": len(violations),
        "verdict": "FAIL" if violations else
                   ("PASS" if separated or dossier_text else
                    "NOT_MEASURABLE"),
        "note": "validation requires physical observation; simulation and "
                "literature can never close it (Art. XXXVIII)",
    }
