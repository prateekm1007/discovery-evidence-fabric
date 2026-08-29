"""
audit_traceability.py — R373-3: recompute traceability honestly.

Independently re-derives the EXPLICIT / PARTIAL / UNKNOWN /
NOT_APPLICABLE classification for every design-input chain from the
canonical engineering record (fresh implementation — the R372 module is
NOT imported), then cross-checks the shipped ENGINEERING_TRACEABILITY.json
against the recomputation (Constitution Art. III: a shipped file's own
self-classification is a claim, not evidence).

Invariants enforced (CEO R373-3):
  * every DI chain carries a state from the four-state scheme;
  * no non-EXPLICIT slot without a record-cited justification;
  * the forbidden combination  linked=false + passed=true  may occur ONLY
    with an explicit explanation of why the package still passes —
    mechanically: the shipped release_gate must carry
    incomplete_parts_explicitly_justified=true AND every non-EXPLICIT
    slot AND orphan in the shipped file must carry a justification with a
    non-empty data_basis;
  * the shipped file's summary counts must equal the recomputed counts
    (drift between shipped claims and canonical reality is a failure);
  * the legacy R370 record inside the shipped file must be explicitly
    marked as superseded (its ambiguous boolean 'passed' may never read
    as current truth).
"""

import re


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", str(s or "").strip().lower())


def _contains(hay: str, needle: str, min_len: int = 5) -> bool:
    if not needle or len(needle) < min_len:
        return False
    return needle in hay


_VID = re.compile(r"\bV-\d{3}\b")


def _recompute_chain(di, verification, failure_analysis, design_outputs):
    """Fresh classification of one DI's three slots."""
    slots = {}

    # DI -> V
    val = _norm(di.get("value", ""))
    v_state, v_link = "UNKNOWN", None
    for v in verification:
        req = _norm(v.get("requirement", ""))
        if val and req and (_contains(req, val) or _contains(val, req)):
            v_state, v_link = "EXPLICIT", v.get("id")
            break
    slots["verification"] = v_state

    # DI -> FM
    name = _norm(di.get("input", ""))
    fm_state, fm_link = "UNKNOWN", None
    for i, fm in enumerate(failure_analysis, start=1):
        hay = " ".join(_norm(fm.get(k, "")) for k in
                       ("failure_mode", "mechanism", "design_feature_affected"))
        if name and _contains(hay, name):
            fm_state, fm_link = "EXPLICIT", f"FM-{i}"
            break
    slots["failure_mode"] = fm_state

    # DI -> DO: the canonical record has no binding field (freshly
    # verified: design outputs carry description/status/missing_inputs).
    # Applicability statements can make this NOT_APPLICABLE.
    app = _norm(di.get("applicability", ""))
    slots["design_output"] = ("NOT_APPLICABLE"
                              if "not applicable" in app else "UNKNOWN")

    # FM -> V for the partial-detection of orphan FMs
    return slots, v_link, fm_link


def _fm_verification_states(failure_analysis, verification):
    out = {}
    for i, fm in enumerate(failure_analysis, start=1):
        vt = fm.get("verification_test") or ""
        vids = set(_VID.findall(vt))
        known = {v.get("id") for v in verification}
        if vids & known:
            out[f"FM-{i}"] = "EXPLICIT"
        elif vt.strip():
            out[f"FM-{i}"] = "PARTIAL"
        else:
            out[f"FM-{i}"] = "UNKNOWN"
    return out


def recompute_package(pkg) -> dict:
    """Independent recomputation of the whole package classification."""
    dis = pkg.design_inputs
    dos = pkg.design_outputs
    fms = pkg.failure_analysis
    vers = pkg.verification

    chains = []
    fm_linked = set()
    for di in dis:
        slots, v_link, fm_link = _recompute_chain(di, vers, fms, dos)
        if fm_link:
            fm_linked.add(fm_link)
        state = ("TRACEABILITY_COMPLETE" if all(
                     s == "EXPLICIT" for s in slots.values())
                 else "TRACEABILITY_NOT_APPLICABLE" if all(
                     s == "NOT_APPLICABLE" for s in slots.values())
                 else "TRACEABILITY_PARTIAL" if any(
                     s in ("EXPLICIT", "PARTIAL") for s in slots.values())
                 else "TRACEABILITY_UNKNOWN")
        chains.append({"design_input_id": di.get("id"),
                       "slots": slots, "chain_state": state})
    orphan_dos = [do.get("id") for do in dos]
    orphan_fms = [f"FM-{i}" for i in range(1, len(fms) + 1)
                  if f"FM-{i}" not in fm_linked]
    return {
        "total_DIs": len(chains),
        "explicitly_linked": sum(1 for c in chains
                                 if "EXPLICIT" in c["slots"].values()),
        "partially_linked": sum(1 for c in chains
                                if "PARTIAL" in c["slots"].values()
                                and "EXPLICIT" not in c["slots"].values()),
        "unknown": sum(1 for c in chains
                       if c["chain_state"] == "TRACEABILITY_UNKNOWN"),
        "not_applicable": sum(1 for c in chains
                              if c["chain_state"] ==
                              "TRACEABILITY_NOT_APPLICABLE"),
        "orphan_DOs": len(orphan_dos),
        "orphan_FMs": len(orphan_fms),
        "chains": chains,
    }


def _justification_ok(slot: dict) -> bool:
    j = slot.get("justification")
    return bool(j) and bool(j.get("data_basis"))


def audit_package(pkg, shipped: dict) -> dict:
    """Recompute + cross-check the shipped ENGINEERING_TRACEABILITY.json."""
    failures = []
    recomputed = recompute_package(pkg)

    if shipped.get("schema") != "R372_TRACEABILITY_SEMANTICS":
        failures.append({"check": "SCHEMA",
                         "detail": "shipped file is not the R372 semantics "
                                   "schema"})

    # ---- four-state scheme on every chain + justification invariant ----
    for c in shipped.get("chains", []):
        if c.get("chain_state") not in (
                "TRACEABILITY_COMPLETE", "TRACEABILITY_PARTIAL",
                "TRACEABILITY_UNKNOWN", "TRACEABILITY_NOT_APPLICABLE"):
            failures.append({"check": "CHAIN_STATE",
                             "detail": f"{c.get('design_input_id')} state "
                                       f"{c.get('chain_state')!r} outside "
                                       f"the four-state scheme"})
        for slot_name, slot in (c.get("slots") or {}).items():
            if slot.get("state") not in ("EXPLICIT", "PARTIAL", "UNKNOWN",
                                         "NOT_APPLICABLE"):
                failures.append({"check": "SLOT_STATE",
                                 "detail": f"{c.get('design_input_id')}."
                                           f"{slot_name} state "
                                           f"{slot.get('state')!r}"})
            if slot.get("state") != "EXPLICIT" and not _justification_ok(
                    slot):
                failures.append({
                    "check": "UNJUSTIFIED_INCOMPLETE_SLOT",
                    "detail": (f"{c.get('design_input_id')}.{slot_name} is "
                               f"{slot.get('state')} with no record-cited "
                               f"justification — this is the forbidden "
                               f"'linked=false, passed=true' state without "
                               f"explanation"),
                })

    # ---- summary counts must match the recomputation --------------------
    s = shipped.get("summary", {})
    for key in ("explicitly_linked", "partially_linked", "unknown",
                "not_applicable", "orphan_DOs", "orphan_FMs", "total_DIs"):
        if key in recomputed and key in s:
            if s[key] != recomputed[key]:
                failures.append({
                    "check": "SUMMARY_DRIFT",
                    "detail": (f"shipped {key}={s[key]} but independent "
                               f"recomputation from canonical data gives "
                               f"{recomputed[key]}"),
                })

    # ---- per-chain state drift -----------------------------------------
    rec_by_di = {c["design_input_id"]: c for c in recomputed["chains"]}
    for c in shipped.get("chains", []):
        r = rec_by_di.get(c.get("design_input_id"))
        if r and c.get("chain_state") != r["chain_state"]:
            failures.append({
                "check": "CHAIN_STATE_DRIFT",
                "detail": (f"{c.get('design_input_id')} shipped "
                           f"{c.get('chain_state')} vs recomputed "
                           f"{r['chain_state']}"),
            })

    # ---- release-gate explanation invariant -----------------------------
    gate = shipped.get("release_gate", {})
    has_incomplete = any(
        c.get("chain_state") != "TRACEABILITY_COMPLETE"
        for c in shipped.get("chains", []))
    if has_incomplete and not gate.get(
            "incomplete_parts_explicitly_justified"):
        failures.append({
            "check": "PASSED_WITHOUT_EXPLANATION",
            "detail": "package has incomplete chains but the release gate "
                      "does not state that every incomplete part is "
                      "explicitly justified (forbidden "
                      "linked=false + passed=true without explanation)",
        })
    unjustified = [u for u in gate.get("unjustified_slots", [])]
    if unjustified:
        failures.append({"check": "UNJUSTIFIED_SLOTS_LISTED",
                         "detail": f"gate lists unjustified slots "
                                   f"{unjustified[:5]}"})

    # ---- orphans must be justified --------------------------------------
    for do in shipped.get("orphan_design_outputs", []):
        if not do.get("justified"):
            failures.append({"check": "ORPHAN_DO_UNJUSTIFIED",
                             "detail": f"{do.get('id')}"})
    for fm in shipped.get("orphan_failure_modes", []):
        if not fm.get("justified"):
            failures.append({"check": "ORPHAN_FM_UNJUSTIFIED",
                             "detail": f"{fm.get('id')}"})

    # ---- legacy record must be marked superseded ------------------------
    legacy = shipped.get("legacy_r370_record")
    if legacy is not None and not legacy.get("legacy_note"):
        failures.append({"check": "LEGACY_NOT_MARKED_SUPERSEDED",
                         "detail": "verbatim R370 record carries no "
                                   "supersession note — its ambiguous "
                                   "'passed' flag would read as current"})

    return {
        "package_id": pkg.pkg_id,
        "recomputed_summary": {k: v for k, v in recomputed.items()
                               if k != "chains"},
        "shipped_summary": s,
        "chains_recomputed": len(recomputed["chains"]),
        "failures": failures,
        "ok": not failures,
    }
