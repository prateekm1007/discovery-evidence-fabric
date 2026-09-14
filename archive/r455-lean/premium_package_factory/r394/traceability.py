"""traceability.py — R394: construct GENUINE traceability links where
canonical identifiers exist (CEO directive 10).

The R372 classifiers bind only by exact full-text containment of the DI
value/input in another artifact's field — which almost never happens,
so P-07 shipped 10/10 UNKNOWN. The R370Q record actually carries
CANONICAL ENGINEERING IDENTIFIERS (Q_min, G_floor, d_floor, Cpk, ISO
10555-1) that appear across DIs, critical parameters, failure modes,
verification items, and work packages. Two artifacts that share a
recorded identifier genuinely concern the same quantity — that is a
real traceability link, not a manufactured one.

Binding rules (recorded, deterministic, auditable — Art. II):
  IDENTIFIER    a shared underscore-bearing symbol (>= 2 segments) or
                standard number (ISO/IEC + digits), appearing in both
                artifacts' text -> EXPLICIT with the identifier named
  PHRASE        exact normalized phrase containment (>= 12 chars) that
                the R372 containment check missed at slot level
  Otherwise     the R372 classification stands (UNKNOWN stays UNKNOWN —
                never manufactured)

Extended chain slots (the CEO's canonical chain):
  mechanism_feature  subsystem bound by shared identifier
  geometry_parameter critical parameter bound by shared identifier
  failure_mode       (R372, upgraded where identifiers bind)
  verification       (R372, upgraded where identifiers bind)
  experiment         work package bound by shared identifier
  expected_observation  the bound WP's recorded measurement
  decision              the bound WP's recorded acceptance criterion
"""

from __future__ import annotations

import re

_IDENT_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+\b")
_STD_RE = re.compile(r"\b(?:ISO|IEC|ASTM|AAMI)[\s-]?\d{3,6}(?:-\d+)?\b")
_MIN_PHRASE = 12

# Generic evidence-class/status identifiers that appear across the
# record without carrying engineering meaning — they never bind two
# artifacts (a shared evidence-class word is not a traceability link).
_GENERIC_IDENTS = {
    "MODEL_DERIVED", "NOT_APPLICABLE", "NOT_ESTABLISHED",
    "SOURCE_FACT", "EXTERNAL_PRECEDENT", "COMPUTATIONAL_RESULT",
    "COMPUTATIONALLY_SUPPORTED", "PHYSICAL_OBSERVATION", "NOT_TESTED",
    "NOT_PERFORMED", "ENGINEERING_PROPOSED", "CRITICAL_UNKNOWN",
    "TBD_BLOCKED",
}


def identifiers_of(*texts) -> set:
    """Canonical engineering identifiers in the given texts."""
    out = set()
    for t in texts:
        s = str(t or "")
        out.update(m.group(0) for m in _IDENT_RE.finditer(s))
        out.update(" ".join(m.group(0).split())
                   for m in _STD_RE.finditer(s))
    return {i for i in out if i not in _GENERIC_IDENTS}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", str(s or "").strip().lower())


def _phrase_share(a: str, b: str) -> str | None:
    """Longest exact normalized phrase shared, requiring at least TWO
    alphabetic words and >= _MIN_PHRASE characters (a single-word match
    with padding spaces is not a phrase — Art. II discipline)."""
    na, nb = _norm(a), _norm(b)
    if not na or not nb or len(na) < _MIN_PHRASE:
        return None
    shorter, longer = (na, nb) if len(na) <= len(nb) else (nb, na)
    best = None
    for size in range(min(len(shorter), 80), _MIN_PHRASE - 1, -1):
        for i in range(0, len(shorter) - size + 1):
            cand = shorter[i:i + size]
            if cand in longer:
                words = [w for w in cand.split() if w.isalpha()]
                if len(words) >= 2:
                    best = cand
                    break
        if best:
            break
    return best


def _bind(source_text: str, targets: list, target_text_fn) -> dict | None:
    """Bind source_text to one target by shared identifier (exact) or
    exact shared phrase. Returns the binding record or None."""
    src_idents = identifiers_of(source_text)
    if not src_idents:
        return None
    for target in targets:
        tgt_text = target_text_fn(target)
        shared = src_idents & identifiers_of(tgt_text)
        if shared:
            return {
                "target": target,
                "shared_identifiers": sorted(shared),
                "how": "shared canonical engineering identifier",
            }
    return None


def attach(pkg, trace: dict) -> dict:
    """Upgrade an R372 traceability record with genuine identifier
    bindings + the extended chain slots. Never downgrades an EXPLICIT
    slot; never converts UNKNOWN without a real binding."""
    dis = pkg.design_inputs
    cps = pkg.critical_parameters
    fms = pkg.failure_analysis
    vers = pkg.verification
    wps = pkg.build_plan
    subs = (pkg.eng.get("system_architecture") or {}).get(
        "subsystems") or []
    chains = {c["design_input_id"]: c for c in trace.get("chains", [])}

    def di_text(di):
        return " ".join(str(di.get(k, "")) for k in
                        ("input", "value", "resolution_plan"))

    def v_text(v):
        return " ".join(str(v.get(k, "")) for k in
                        ("requirement", "method", "acceptance"))

    def fm_text(fm):
        return " ".join(str(fm.get(k, "")) for k in (
            "failure_mode", "mechanism", "design_feature",
            "design_feature_affected", "verification_test", "evidence"))

    def cp_text(cp):
        return " ".join(str(cp.get(k, "")) for k in
                        ("name", "basis", "verification_requirement"))

    def wp_text(wp):
        return " ".join(str(wp.get(k, "")) for k in (
            "test_article", "measurement", "acceptance_criterion",
            "deliverable"))

    def sub_text(ss):
        return " ".join(str(ss.get(k, "")) for k in ("name", "function"))

    upgraded = 0
    for di in dis:
        chain = chains.get(di.get("id"))
        if not chain:
            continue
        src = di_text(di)
        slots = chain.setdefault("slots", {})

        # --- mechanism_feature (subsystem) -----------------------------
        mech = _bind(src, subs, sub_text)
        if mech:
            slots["mechanism_feature"] = _slot(
                "EXPLICIT", mech["target"].get("id"),
                f"shares canonical identifier(s) "
                f"{', '.join(mech['shared_identifiers'])} with subsystem "
                f"{mech['target'].get('name', '')[:60]}")
        else:
            slots["mechanism_feature"] = _unknown_slot(
                "no subsystem shares a canonical identifier with this "
                "design input (identifier binding; Art. II — no guess)")

        # --- geometry_parameter (critical parameter) -------------------
        par = _bind(src, cps, cp_text)
        if par:
            slots["geometry_parameter"] = _slot(
                "EXPLICIT", par["target"].get("name"),
                f"shares canonical identifier(s) "
                f"{', '.join(par['shared_identifiers'])} with critical "
                "parameter")
        else:
            slots["geometry_parameter"] = _unknown_slot(
                "no critical parameter shares a canonical identifier with "
                "this design input")

        # --- upgrade failure_mode / verification by identifier ----------
        for slot_name, targets, tfn, id_fmt in (
            ("failure_mode", fms, fm_text,
             lambda t: f"FM-{t.get('failure_mode', '')[:40]}"),
            ("verification", vers, v_text,
             lambda t: str(t.get("id", ""))),
        ):
            cur = slots.get(slot_name) or {}
            if cur.get("state") == "EXPLICIT":
                continue
            b = _bind(src, targets, tfn)
            phrase = None
            if b is None:
                for t in targets:
                    p = _phrase_share(src, tfn(t))
                    if p:
                        b = {"target": t, "shared_identifiers": [],
                             "how": "exact shared phrase"}
                        phrase = p
                        break
            if b:
                ev = (f"shares canonical identifier(s) "
                      f"{', '.join(b['shared_identifiers'])}"
                      if b["shared_identifiers"]
                      else f"exact shared phrase '{phrase}'")
                slots[slot_name] = _slot("EXPLICIT",
                                         id_fmt(b["target"]), ev)
                upgraded += 1

        # --- experiment (work package) + observation + decision ----------
        cur_v = slots.get("verification") or {}
        v_bound = cur_v.get("linked_id")
        src_for_wp = src
        if v_bound:
            v_rec = next((v for v in vers if str(v.get("id")) == v_bound),
                         None)
            if v_rec:
                src_for_wp = src + " " + v_text(v_rec)
        wpb = _bind(src_for_wp, wps, wp_text)
        if wpb is None:
            for w in wps:
                p = _phrase_share(src_for_wp, wp_text(w))
                if p:
                    wpb = {"target": w, "shared_identifiers": [],
                           "how": "exact shared phrase", "phrase": p}
                    break
        if wpb:
            w = wpb["target"]
            ev = (f"shares canonical identifier(s) "
                  f"{', '.join(wpb['shared_identifiers'])}"
                  if wpb["shared_identifiers"]
                  else f"exact shared phrase '{wpb.get('phrase')}'")
            slots["experiment"] = _slot("EXPLICIT",
                                        w.get("work_package"), ev)
            if w.get("measurement"):
                slots["expected_observation"] = _slot(
                    "EXPLICIT", w.get("work_package"),
                    f"work package {w.get('work_package')} records the "
                    f"measurement: {w.get('measurement')}")
            if w.get("acceptance_criterion"):
                slots["decision"] = _slot(
                    "EXPLICIT", w.get("work_package"),
                    f"work package {w.get('work_package')} records the "
                    f"acceptance criterion: "
                    f"{w.get('acceptance_criterion')}")
        else:
            slots["experiment"] = _unknown_slot(
                "no work package shares a canonical identifier or exact "
                "phrase with this design input or its bound verification")
            slots["expected_observation"] = _unknown_slot(
                "no bound experiment")
            slots["decision"] = _unknown_slot("no bound experiment")

        # recompute chain state over ALL slots
        chain["chain_state"] = _chain_state(slots)

    # recompute package summary + state
    all_chains = list(chains.values())
    states = [c["chain_state"] for c in all_chains]
    pkg_state = ("TRACEABILITY_COMPLETE"
                 if all(s == "TRACEABILITY_COMPLETE" for s in states)
                 and states else
                 "TRACEABILITY_PARTIAL"
                 if any(s in ("TRACEABILITY_COMPLETE",
                              "TRACEABILITY_PARTIAL") for s in states)
                 and states else
                 "TRACEABILITY_UNKNOWN" if states else
                 "TRACEABILITY_NOT_APPLICABLE")
    explicit = sum(1 for c in all_chains
                   if any(s.get("state") == "EXPLICIT"
                          for s in c["slots"].values()))
    partial = sum(1 for c in all_chains
                  if any(s.get("state") == "PARTIAL"
                         for s in c["slots"].values())
                  and not any(s.get("state") == "EXPLICIT"
                              for s in c["slots"].values()))
    unknown = sum(1 for c in all_chains
                  if c["chain_state"] == "TRACEABILITY_UNKNOWN")
    trace.setdefault("summary", {})
    trace["summary"].update({
        "explicitly_linked": explicit,
        "partially_linked": partial,
        "unknown": unknown,
        "chain_state_counts": {s: states.count(s)
                               for s in set(states) if states.count(s)},
    })
    trace["release_gate"] = trace.get("release_gate") or {}
    trace["release_gate"]["traceability_state"] = pkg_state
    trace["release_gate"]["r394_upgrade"] = {
        "binding_rules": {
            "IDENTIFIER": "shared canonical engineering identifier "
                          "(underscore symbol or standard number) present "
                          "in both artifacts' recorded text",
            "PHRASE": "exact normalized phrase (>= 12 chars) shared",
            "NEVER": "semantic association, fuzzy match, or invented "
                     "binding (Art. II)",
        },
        "slots_added": ["mechanism_feature", "geometry_parameter",
                        "experiment", "expected_observation", "decision"],
        "slots_upgraded_to_explicit": upgraded,
        "chain": ("DESIGN INPUT (requirement) -> mechanism feature -> "
                  "geometry parameter -> failure mode -> verification -> "
                  "experiment -> expected observation -> decision"),
    }
    if pkg_state == "TRACEABILITY_PARTIAL":
        trace["release_gate"]["reason"] = (
            f"R394 identifier binding: {explicit} of {len(all_chains)} "
            "design-input chains now carry explicit links through shared "
            "canonical identifiers; the remaining chains carry record-"
            "cited justifications. The graph is honest — complete where "
            "the record supports it, unknown where it does not.")
    return trace


def _slot(state, linked_id, evidence):
    return {"state": state, "linked_id": linked_id,
            "evidence": evidence, "justification": None}


def _unknown_slot(text):
    return {"state": "UNKNOWN", "linked_id": None, "evidence": None,
            "justification": {
                "code": "NO_IDENTIFIER_BINDING",
                "text": text,
                "data_basis": "canonical identifier scan "
                              "(r394.traceability)",
            }}


def _chain_state(slots: dict) -> str:
    states = {s.get("state") for s in slots.values() if isinstance(
        s, dict) and "state" in s}
    if states == {"EXPLICIT"}:
        return "TRACEABILITY_COMPLETE"
    if states and states <= {"NOT_APPLICABLE"}:
        return "TRACEABILITY_NOT_APPLICABLE"
    if "EXPLICIT" in states or "PARTIAL" in states:
        return "TRACEABILITY_PARTIAL"
    return "TRACEABILITY_UNKNOWN"
