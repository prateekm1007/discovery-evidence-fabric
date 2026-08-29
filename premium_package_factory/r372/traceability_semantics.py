"""
traceability_semantics.py — R372-1: explicit traceability semantics.

PROBLEM BEING FIXED (CEO R372 audit finding #1):
The legacy ENGINEERING_TRACEABILITY.json shipped in every package declared
`"passed": true` while its own data showed 3 orphan design outputs, 4 orphan
failure modes and most design inputs NOT_LINKED. A gate may legitimately
pass with deliberately classified incomplete links, but the generated
artifact must never imply a healthy graph while most engineering
relationships are absent.

CORRECTION:
Every DI/DO/FM/V chain slot is classified EXPLICITLY, computed FROM the
canonical engineering record (never trusting the legacy `passed` flag —
Constitution Art. III: the verifier must never trust the claimant):

  EXPLICIT        the link is recorded in canonical data
                  (DI.value == V.requirement; DI.input name inside
                  FM.failure_mode/mechanism; FM.verification_test binds a
                  recorded V-id)
  PARTIAL         a related artifact exists but the binding is incomplete
                  (FM carries a verification_test that names no recorded
                  V-id)
  UNKNOWN         no link recorded and no applicability statement
  NOT_APPLICABLE  the record explicitly states the link type does not apply

Chain states: TRACEABILITY_COMPLETE / TRACEABILITY_PARTIAL /
TRACEABILITY_UNKNOWN / TRACEABILITY_NOT_APPLICABLE, each with a reason.

A package may pass the release gate with incomplete traceability ONLY when
every non-EXPLICIT slot carries a justification that cites non-empty
canonical data (mechanically checked — see `_justification_valid`). The
release report carries: critical_DIs, explicitly_linked, partially_linked,
unknown, not_applicable, orphan_DOs, orphan_FMs.

The legacy R370 record is preserved verbatim inside the shipped file
(Art. XI: history is evidence), with an explicit note that its ambiguous
`passed` flag is superseded.
"""

import json
import os
import re

# ---------------------------------------------------------------------------
# text normalization for EXACT containment matching (no semantics — Art. II)
# ---------------------------------------------------------------------------

def _norm(s: str) -> str:
    """Lowercase, collapse whitespace. Character-level identity preserved."""
    return re.sub(r"\s+", " ", str(s or "").strip().lower())


def _contains(hay: str, needle: str) -> bool:
    """Exact substring containment on normalized forms. needle is required
    to be non-trivial (>= 5 chars) so short tokens cannot fake a match."""
    if not needle or len(needle) < 5:
        return False
    return needle in hay


# ---------------------------------------------------------------------------
# slot classification
# ---------------------------------------------------------------------------

def _classify_di_to_v(di: dict, verification: list) -> dict:
    """DI -> V link: EXPLICIT iff the DI's recorded value text matches a
    recorded verification requirement (exact normalized containment, both
    directions, with a length guard)."""
    val = _norm(di.get("value", ""))
    for v in verification:
        req = _norm(v.get("requirement", ""))
        if not req or not val:
            continue
        if _contains(req, val) or _contains(val, req):
            return {
                "state": "EXPLICIT",
                "linked_id": v.get("id"),
                "evidence": f"DI value matches verification {v.get('id')} "
                            f"requirement text exactly (normalized).",
                "justification": None,
            }
    return {
        "state": "UNKNOWN",
        "linked_id": None,
        "evidence": None,
        "justification": _justification_no_v_binding(di, verification),
    }


def _classify_di_to_fm(di: dict, failure_analysis: list) -> dict:
    """DI -> FM link: EXPLICIT iff the DI's recorded input name appears
    verbatim inside a recorded failure-mode field (exact containment)."""
    name = _norm(di.get("input", ""))
    for i, fm in enumerate(failure_analysis, start=1):
        hay = " ".join(_norm(fm.get(k, "")) for k in (
            "failure_mode", "mechanism", "design_feature_affected"))
        if _contains(hay, name):
            return {
                "state": "EXPLICIT",
                "linked_id": f"FM-{i}",
                "evidence": f"Design-input name appears verbatim in failure "
                            f"mode '{fm.get('failure_mode', '')[:60]}'.",
                "justification": None,
            }
    return {
        "state": "UNKNOWN",
        "linked_id": None,
        "evidence": None,
        "justification": _justification_no_fm_binding(di, failure_analysis),
    }


_VID_RE = re.compile(r"\bV-\d{3}\b")


def _classify_fm_to_v(fm: dict, verification: list) -> dict:
    """FM -> V link: EXPLICIT iff FM's recorded verification_test names a
    recorded V-id; PARTIAL iff a test is described but binds no recorded
    V-id; UNKNOWN iff no test is recorded."""
    vt = fm.get("verification_test") or ""
    vids = sorted(set(_VID_RE.findall(vt)))
    known = {v.get("id") for v in verification}
    bound = [v for v in vids if v in known]
    if bound:
        return {
            "state": "EXPLICIT",
            "linked_id": ", ".join(bound),
            "evidence": "verification_test names recorded verification id(s).",
            "justification": None,
        }
    if vt.strip():
        return {
            "state": "PARTIAL",
            "linked_id": None,
            "evidence": "A verification test is described but is not bound "
                        "to a recorded V-id.",
            "justification": {
                "code": "FM_TEST_DESCRIBED_NOT_BOUND",
                "text": "The failure mode records a verification test "
                        f"(\"{vt[:120]}\") but the canonical verification "
                        "matrix contains no V-id binding for it.",
                "data_basis": "failure_analysis.verification_test",
            },
        }
    return {
        "state": "UNKNOWN",
        "linked_id": None,
        "evidence": None,
        "justification": {
            "code": "FM_NO_VERIFICATION_TEST_RECORDED",
            "text": f"Failure mode '{(fm.get('failure_mode') or '')[:80]}' "
                    "records no verification test.",
            "data_basis": "failure_analysis.verification_test (empty)",
        },
    }


def _classify_di_to_do(di: dict, design_outputs: list) -> dict:
    """DI -> DO link: the canonical record contains NO design-output binding
    field (design outputs carry description/status/missing_inputs only).
    Per Art. II the absence of an explicit binding may not be replaced by
    semantic similarity, so the honest state is UNKNOWN with a record-state
    justification — never a guessed link."""
    statuses = [f"{do.get('id')} ({do.get('status', 'UNKNOWN')})"
                for do in design_outputs]
    return {
        "state": "UNKNOWN",
        "linked_id": None,
        "evidence": None,
        "justification": {
            "code": "DI_DO_BINDING_NOT_RECORDED_IN_CANONICAL_STATE",
            "text": (
                "The canonical engineering record (R370Q export) contains no "
                "design-output binding for this design input. Design outputs "
                "present: "
                + ("; ".join(statuses) if statuses else "NONE")
                + ". Binding design outputs to design inputs is assigned "
                "engineering development work (build plan / transfer "
                "boundary), not an established fact."
            ),
            "data_basis": (
                "design_outputs[].status" if statuses else None
            ),
        },
    }


# ---------------------------------------------------------------------------
# justifications (must cite non-empty canonical data to be valid)
# ---------------------------------------------------------------------------

def _justification_no_v_binding(di: dict, verification: list) -> dict:
    """Justify a missing DI->V link from record facts only."""
    val = str(di.get("value", "")).strip()
    val_is_unknown = val.upper() == "UNKNOWN" or val == ""
    rp = di.get("resolution_plan") or ""
    if val_is_unknown and rp:
        return {
            "code": "DI_VALUE_UNKNOWN_RESOLUTION_PLAN_RECORDED",
            "text": "Design input value is UNKNOWN; a resolution plan is "
                    f"recorded: {rp[:200]}",
            "data_basis": "design_inputs.resolution_plan",
        }
    if val_is_unknown and not rp:
        if verification:
            return {
                "code": "DI_VALUE_UNKNOWN_NO_PLAN_VERIFICATION_EXISTS",
                "text": (
                    "Design input value is UNKNOWN and no resolution plan "
                    f"is recorded. {len(verification)} verification item(s) "
                    "exist in the matrix, but an unquantified input cannot "
                    "be bound to an acceptance test (Art. II — no guessed "
                    "link)."
                ),
                "data_basis": "engineering_core.verification",
            }
        return {
            "code": "DI_VALUE_UNKNOWN_NO_RESOLUTION_PLAN",
            "text": "Design input value is UNKNOWN and no resolution plan is "
                    "recorded.",
            "data_basis": None,  # invalid justification -> gate must fail
        }
    # the value carries recorded content (possibly UNKNOWN-qualified)
    if verification:
        return {
            "code": "NO_VERIFICATION_BINDING_FOR_DI",
            "text": (
                f"{len(verification)} verification item(s) are recorded, "
                "none matches this design input's value text exactly; per "
                "Constitution Art. II a semantic near-match is not a link."
            ),
            "data_basis": "engineering_core.verification",
        }
    note = di.get("note") or ""
    if note:
        return {
            "code": "NO_VERIFICATION_RECORDED_DI_NOTE_EXISTS",
            "text": "No verification matrix exists; the design input "
                    f"records a note: {str(note)[:160]}",
            "data_basis": "design_inputs.note",
        }
    return {
        "code": "NO_VERIFICATION_RECORDED",
        "text": "The canonical record contains no verification matrix.",
        "data_basis": None,
    }


def _justification_no_fm_binding(di: dict, fms: list) -> dict:
    app = di.get("applicability") or ""
    if app and "not applicable" in _norm(app):
        return {
            "code": "DI_NOT_APPLICABLE_RECORDED",
            "text": f"Design input applicability recorded as: {app}",
            "data_basis": "design_inputs.applicability",
        }
    if not fms:
        return {
            "code": "NO_FAILURE_ANALYSIS_RECORDED",
            "text": "The canonical record contains no failure analysis.",
            "data_basis": None,
        }
    return {
        "code": "NO_FAILURE_MODE_BINDING_FOR_DI",
        "text": (
            f"{len(fms)} failure mode(s) are recorded, none references this "
            "design input's name verbatim; a semantic association would be "
            "a guessed link (Art. II) and is not emitted."
        ),
        "data_basis": "failure_analysis",
    }


def _orphan_do_justification(do: dict) -> dict:
    parts = []
    if do.get("status"):
        parts.append(f"status {do.get('status')}")
    if do.get("missing_inputs"):
        parts.append("missing inputs: " + "; ".join(do["missing_inputs"]))
    if do.get("note"):
        parts.append(f"note: {str(do['note'])[:150]}")
    return {
        "code": "ORPHAN_DESIGN_OUTPUT",
        "text": (
            f"Design output {do.get('id')} is not bound to any design input "
            "in the canonical record (" + ("; ".join(parts) if parts else
                                           "no status recorded") + ")."
        ),
        "data_basis": "design_outputs.status" if do.get("status") else None,
    }


def _orphan_fm_justification(fm: dict) -> dict:
    parts = []
    if fm.get("mitigation"):
        parts.append(f"mitigation recorded: {str(fm['mitigation'])[:120]}")
    if fm.get("verification_test"):
        parts.append("verification test described (unbound)")
    if fm.get("residual_uncertainty"):
        parts.append(f"residual uncertainty: "
                     f"{str(fm['residual_uncertainty'])[:120]}")
    return {
        "code": "ORPHAN_FAILURE_MODE",
        "text": (
            f"Failure mode '{(fm.get('failure_mode') or '')[:70]}' is not "
            "referenced by any design input. "
            + ("; ".join(parts) if parts else "No mitigation or verification "
                                              "is recorded.")
        ),
        "data_basis": ("failure_analysis.mitigation"
                       if fm.get("mitigation") else None),
    }


def _justification_valid(j) -> bool:
    """A justification is valid only if it cites non-empty canonical data."""
    return bool(j) and bool(j.get("data_basis"))


# ---------------------------------------------------------------------------
# chain + package classification
# ---------------------------------------------------------------------------

_CHAIN_STATE_ORDER = {
    "TRACEABILITY_COMPLETE": 0,
    "TRACEABILITY_PARTIAL": 1,
    "TRACEABILITY_NOT_APPLICABLE": 2,
    "TRACEABILITY_UNKNOWN": 3,
}


def _chain_state(slots: dict) -> str:
    states = {s["state"] for s in slots.values()}
    if states == {"EXPLICIT"}:
        return "TRACEABILITY_COMPLETE"
    if states and states <= {"NOT_APPLICABLE"}:
        return "TRACEABILITY_NOT_APPLICABLE"
    if "EXPLICIT" in states or "PARTIAL" in states:
        return "TRACEABILITY_PARTIAL"
    return "TRACEABILITY_UNKNOWN"


_QUANT_RE = re.compile(
    r"(<=|>=|<|>|=)\s*\d|%|(\d+\s*(?:mmHg|mL|min\b|h\b|Hz|kHz|MHz|GHz|"
    r"V\b|mA|W\b|mW|µW|uW|°C|kPa|mm\b|cm\b|µm|nm|days|weeks|months))", re.I)


def _is_critical_di(di: dict) -> bool:
    """A design input is CRITICAL for traceability when its recorded value
    carries a quantitative acceptance criterion (comparator+number, a
    percentage, or a number with an engineering unit). Mechanical,
    disclosed in the shipped file."""
    val = str(di.get("value", ""))
    return bool(_QUANT_RE.search(val))


def classify_package(pkg, legacy_record: dict = None) -> dict:
    """Compute explicit traceability semantics for one canonical package."""
    dis = pkg.design_inputs
    dos = pkg.design_outputs
    fms = pkg.failure_analysis
    vers = pkg.verification

    chains = []
    unjustified_slots = []
    fm_linked = set()
    for di in dis:
        slot_v = _classify_di_to_v(di, vers)
        slot_fm = _classify_di_to_fm(di, fms)
        slot_do = _classify_di_to_do(di, dos)
        slots = {"verification": slot_v, "failure_mode": slot_fm,
                 "design_output": slot_do}
        if slot_fm["state"] == "EXPLICIT" and slot_fm.get("linked_id"):
            fm_linked.add(slot_fm["linked_id"])
        state = _chain_state(slots)
        reason = _chain_reason(state, slots)
        for slot_name, slot in slots.items():
            if slot["state"] != "EXPLICIT" and not _justification_valid(
                    slot.get("justification")):
                unjustified_slots.append(f"{di.get('id')}.{slot_name}")
        chains.append({
            "design_input_id": di.get("id"),
            "parameter": di.get("input"),
            "critical": _is_critical_di(di),
            "slots": {
                "design_output": _public_slot(slots["design_output"]),
                "failure_mode": _public_slot(slots["failure_mode"]),
                "verification": _public_slot(slots["verification"]),
            },
            "chain_state": state,
            "reason": reason,
        })

    orphan_dos = []
    for do in dos:
        j = _orphan_do_justification(do)
        orphan_dos.append({
            "id": do.get("id"),
            "description": do.get("description", ""),
            "justification": j,
            "justified": _justification_valid(j),
        })
        if not _justification_valid(j):
            unjustified_slots.append(f"orphan_DO:{do.get('id')}")

    orphan_fms = []
    for i, fm in enumerate(fms, start=1):
        fid = f"FM-{i}"
        if fid in fm_linked:
            continue
        j = _orphan_fm_justification(fm)
        orphan_fms.append({
            "id": fid,
            "failure_mode": fm.get("failure_mode", ""),
            "justification": j,
            "justified": _justification_valid(j),
        })
        if not _justification_valid(j):
            unjustified_slots.append(f"orphan_FM:{fid}")

    # package-level state = strongest chain state present
    chain_states = [c["chain_state"] for c in chains]
    pkg_state = "TRACEABILITY_UNKNOWN"
    if chain_states:
        pkg_state = min(chain_states, key=lambda s: _CHAIN_STATE_ORDER[s])

    summary = {
        "critical_DIs": sum(1 for c in chains if c["critical"]),
        "critical_DI_definition": (
            "Design inputs whose recorded value carries a quantitative "
            "acceptance criterion (comparator+number, percentage, or "
            "number+unit). All design inputs are traceability subjects; "
            "this field isolates the quantitatively binding ones."
        ),
        "total_DIs": len(chains),
        "explicitly_linked": sum(1 for c in chains
                                 if any(s["state"] == "EXPLICIT"
                                        for s in c["slots"].values())),
        "partially_linked": sum(
            1 for c in chains
            if any(s["state"] == "PARTIAL" for s in c["slots"].values())
            and not any(s["state"] == "EXPLICIT" for s in c["slots"].values())),
        "unknown": sum(1 for c in chains
                       if c["chain_state"] == "TRACEABILITY_UNKNOWN"),
        "not_applicable": sum(1 for c in chains
                              if c["chain_state"] ==
                              "TRACEABILITY_NOT_APPLICABLE"),
        "orphan_DOs": len(orphan_dos),
        "orphan_FMs": len(orphan_fms),
        "chain_state_counts": {
            s: chain_states.count(s) for s in _CHAIN_STATE_ORDER
            if chain_states.count(s)
        },
    }

    release_gate = {
        "traceability_state": pkg_state,
        "reason": _package_reason(pkg_state, summary),
        "incomplete_parts_explicitly_justified": not unjustified_slots,
        "unjustified_slots": unjustified_slots,
        "supersedes_legacy_passed_flag": (
            "The R370-era record in this file declared a boolean 'passed' "
            "that did not distinguish a complete graph from an "
            "almost-unlinked one. It is superseded by the explicit "
            "classifications above; incomplete links pass ONLY with a "
            "record-cited justification (CEO R372-1)."
        ),
    }

    out = {
        "package_id": pkg.pkg_id,
        "portfolio_number": pkg.num,
        "schema": "R372_TRACEABILITY_SEMANTICS",
        "classification_scheme": {
            "EXPLICIT": "link recorded in canonical data (exact text match)",
            "PARTIAL": "related artifact exists, binding incomplete",
            "UNKNOWN": "no link recorded, no applicability statement",
            "NOT_APPLICABLE": "record states the link type does not apply",
            "chain_states": [
                "TRACEABILITY_COMPLETE (all slots EXPLICIT)",
                "TRACEABILITY_PARTIAL (>=1 slot EXPLICIT or PARTIAL)",
                "TRACEABILITY_UNKNOWN (no links recorded)",
                "TRACEABILITY_NOT_APPLICABLE (all slots N/A)",
            ],
            "pass_rule": (
                "A package passes with incomplete traceability only when "
                "every non-EXPLICIT slot and every orphan carries a "
                "justification citing non-empty canonical data."
            ),
        },
        "summary": summary,
        "release_gate": release_gate,
        "chains": chains,
        "orphan_design_outputs": orphan_dos,
        "orphan_failure_modes": orphan_fms,
    }
    if legacy_record is not None:
        out["legacy_r370_record"] = legacy_record
    return out


def _public_slot(slot: dict) -> dict:
    out = {"state": slot["state"], "linked_id": slot.get("linked_id")}
    if slot.get("evidence"):
        out["evidence"] = slot["evidence"]
    if slot.get("justification"):
        out["justification"] = slot["justification"]
    return out


def _chain_reason(state: str, slots: dict) -> str:
    if state == "TRACEABILITY_COMPLETE":
        return "All three slots (DO, FM, V) explicitly recorded."
    ex = [k for k, v in slots.items() if v["state"] == "EXPLICIT"]
    pa = [k for k, v in slots.items() if v["state"] == "PARTIAL"]
    un = [k for k, v in slots.items() if v["state"] == "UNKNOWN"]
    parts = []
    if ex:
        parts.append("explicit: " + ", ".join(ex))
    if pa:
        parts.append("partial: " + ", ".join(pa))
    if un:
        parts.append("unknown (justified in slots): " + ", ".join(un))
    return " | ".join(parts) if parts else state


def _package_reason(state: str, summary: dict) -> str:
    if state == "TRACEABILITY_COMPLETE":
        return "Every design-input chain is fully linked (DO, FM, V)."
    if state == "TRACEABILITY_PARTIAL":
        return (
            f"The traceability graph is PARTIAL: {summary['explicitly_linked']} "
            f"of {summary['total_DIs']} design-input chains carry at least "
            f"one explicit link; {summary['unknown']} chain(s) have no "
            f"recorded link; {summary['orphan_DOs']} design output(s) and "
            f"{summary['orphan_FMs']} failure mode(s) are unbound. This is "
            "the honest state of an ENGINEERING_DEFINITION package: the "
            "binding work is downstream engineering development, and every "
            "non-explicit slot carries a record-cited justification. The "
            "graph is NOT represented as healthy."
        )
    if state == "TRACEABILITY_NOT_APPLICABLE":
        return "All chains are explicitly not applicable."
    return (
        f"No design-input chain carries any recorded link "
        f"({summary['total_DIs']} chains, all UNKNOWN). This is the honest "
        "state of an ENGINEERING_DEFINITION package whose DI/DO/FM/V "
        "bindings are downstream engineering development; every unknown "
        "slot carries a record-cited justification. The graph is NOT "
        "represented as healthy."
    )


# ---------------------------------------------------------------------------
# shipped-file builder (replaces the verbatim legacy copy in the build)
# ---------------------------------------------------------------------------

def build_traceability_json(pkg, legacy_path: str = None) -> dict:
    legacy = None
    if legacy_path and os.path.exists(legacy_path):
        with open(legacy_path, encoding="utf-8") as f:
            legacy = json.load(f)
        if isinstance(legacy, dict):
            legacy = dict(legacy)
            legacy["legacy_note"] = (
                "Verbatim R370-era record. Its boolean 'passed' field is "
                "ambiguous (a graph with orphans and unlinked DIs also "
                "passed) and is superseded by release_gate in this file. "
                "Preserved for history (Constitution Art. XI)."
            )
    return classify_package(pkg, legacy)


def portfolio_traceability_table(packages, results: dict) -> list:
    """Rows for the release report traceability table (CEO R372-1 fields)."""
    rows = [["Pkg", "critical_DIs", "explicit", "partial", "unknown",
             "n/a", "orphan_DOs", "orphan_FMs", "state"]]
    for p in packages:
        s = results[p.pkg_id]["summary"]
        rows.append([
            p.pkg_id, str(s["critical_DIs"]), str(s["explicitly_linked"]),
            str(s["partially_linked"]), str(s["unknown"]),
            str(s["not_applicable"]), str(s["orphan_DOs"]),
            str(s["orphan_FMs"]),
            results[p.pkg_id]["release_gate"]["traceability_state"]
            .replace("TRACEABILITY_", ""),
        ])
    return rows
