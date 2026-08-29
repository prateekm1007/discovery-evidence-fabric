"""
unknowns.py — R371 Phase 7: UNKNOWNs become an engineering roadmap.

Classification discipline (CEO Phase 7):
  - UNKNOWN counts are NOT reduced to make packages look better.
  - Each unknown is classified into exactly one of:
      LITERATURE_RESOLVABLE / COMPUTATION_RESOLVABLE / BENCH_TEST_REQUIRED /
      ENGINEERING_DESIGN_REQUIRED / REGULATORY_REQUIRED / LEGAL_IP_REQUIRED /
      FUNDAMENTALLY_UNRESOLVED
  - Each carries resolution_action, expected_output, decision_impact.

Classification is MECHANICAL and each entry records the rule that fired
(classification_basis). Rules are applied in priority order and never use
judgment. Where no rule fires, the unknown is classified
FUNDAMENTALLY_UNRESOLVED with basis NO_MECHANICAL_RULE — honest default,
never a guess (Constitution Art. XXV: unknown stays unknown).
"""

import re

CLASSES = [
    "LITERATURE_RESOLVABLE",
    "COMPUTATION_RESOLVABLE",
    "BENCH_TEST_REQUIRED",
    "ENGINEERING_DESIGN_REQUIRED",
    "REGULATORY_REQUIRED",
    "LEGAL_IP_REQUIRED",
    "FUNDAMENTALLY_UNRESOLVED",
]

_RULES = [
    # (class, compiled pattern, rule id) — priority order
    ("LEGAL_IP_REQUIRED",
     re.compile(r"\b(patent|FTO|freedom to operate|novelty determination|licens)", re.I),
     "RULE_LEGAL_KEYWORD"),
    ("REGULATORY_REQUIRED",
     re.compile(r"(regulatory|FDA|510\(k\)|PMA\b|clearance|ISO 10993|biocompatib|IEC 60601|ISO 14708|clinical endpoint|surrogate endpoint|classification as)", re.I),
     "RULE_REGULATORY_KEYWORD"),
    ("FUNDAMENTALLY_UNRESOLVED",
     re.compile(r"(dataset|training data|no real data|clinical data|in vivo|clinical trial|clinical benefit|revision reduction|market|reimburse)", re.I),
     "RULE_LIVING_SYSTEM_OR_DATA_BLOCKER"),
    ("COMPUTATION_RESOLVABLE",
     re.compile(r"(simulat|computational|in silico|finite element|CFD)", re.I),
     "RULE_COMPUTATION_KEYWORD"),
    ("LITERATURE_RESOLVABLE",
     re.compile(r"(literature|published|citation|prior art|reported in)", re.I),
     "RULE_LITERATURE_KEYWORD"),
    ("ENGINEERING_DESIGN_REQUIRED",
     re.compile(r"(technology choice|\bchoice\b|\bselect\b|cost vs|value analysis|battery life|architecture|controller gains|duty cycle|vs\b.*vs\b|power budget|optimal frequency|balancing)", re.I),
     "RULE_DESIGN_DECISION_KEYWORD"),
    ("BENCH_TEST_REQUIRED",
     re.compile(r"(process capability|Cpk|extrusion|half-life|fouling|drift|infectivity|retention|competition|surface density|deactivation|assay|in CSF environment|CSF/catheter environment|strain amplitude|chronic implant environment|rate in|measured|irradiance|scale-up|\befficiency\b)", re.I),
     "RULE_BENCH_MEASUREMENT_KEYWORD"),
]


def _topic(unknown: str) -> str:
    """Extract the topic span: text before ' — UNKNOWN' or the whole string."""
    t = unknown.split("—")[0].split("--")[0].strip(" -")
    return t if t else unknown.strip()


def _critical(unknown: str) -> bool:
    return bool(re.search(r"critical", unknown, re.I))


def _match_build_plan_step(topic: str, pkg):
    """Find the canonical build-plan step whose measurement/test article
    overlaps the unknown topic (word-overlap scoring, deterministic)."""
    stop = {"the", "a", "an", "of", "for", "in", "at", "to", "and", "with",
            "given", "achievable", "actual", "unknown", "critical", "value"}
    words = {w for w in re.findall(r"[a-zA-Z]{3,}", topic.lower()) if w not in stop}
    if not words:
        return None
    best, best_score = None, 0
    for step in pkg.build_plan:
        hay = " ".join(
            str(step.get(k, "")) for k in
            ("test_article", "measurement", "equipment", "work_package")
        ).lower()
        score = sum(1 for w in words if w in hay)
        if score > best_score:
            best, best_score = step, score
    return best if best_score >= 2 else None


def classify_unknown(unknown: str, pkg) -> dict:
    """Classify one unknown string with full mechanical provenance."""
    # 1. keyword rules in priority order
    for cls, pattern, rule_id in _RULES:
        if pattern.search(unknown):
            return _entry(unknown, cls, pkg, rule_id)
    # 2. recorded parameter basis: design choice -> design-required
    topic = _topic(unknown)
    for cp in pkg.critical_parameters:
        name = (cp.get("name") or "")
        if name and name.split()[0].lower() in topic.lower().split():
            basis = (cp.get("basis") or "").lower()
            ver = (cp.get("verification_requirement") or "").lower()
            if "design choice" in basis:
                return _entry(unknown, "ENGINEERING_DESIGN_REQUIRED", pkg,
                              "RULE_PARAMETER_BASIS_DESIGN_CHOICE")
            if re.search(r"bench|test|assay|measure|calibrat", ver):
                return _entry(unknown, "BENCH_TEST_REQUIRED", pkg,
                              "RULE_PARAMETER_VERIFICATION_BENCH")
    # 3. 'Achievable X' default: achievable values are measured on a bench
    if re.match(r"\s*Achievable\b", unknown):
        return _entry(unknown, "BENCH_TEST_REQUIRED", pkg,
                      "RULE_ACHIEVABLE_DEFAULT_BENCH")
    # 4. honest default
    return _entry(unknown, "FUNDAMENTALLY_UNRESOLVED", pkg,
                  "NO_MECHANICAL_RULE")


def _entry(unknown: str, cls: str, pkg, rule_id: str) -> dict:
    topic = _topic(unknown)
    critical = _critical(unknown)
    step = _match_build_plan_step(topic, pkg)

    if cls == "BENCH_TEST_REQUIRED" and step:
        action = (f"Execute canonical build-plan step "
                  f"{step.get('work_package','WP')}: "
                  f"{step.get('measurement','measure the quantity')}")
    elif cls == "ENGINEERING_DESIGN_REQUIRED":
        action = (f"Design work package in the canonical build plan: select "
                  f"{topic.lower()} with documented basis")
    elif cls == "LITERATURE_RESOLVABLE":
        action = f"Targeted literature search on: {topic}"
    elif cls == "COMPUTATION_RESOLVABLE":
        action = (f"Computational study (model/simulation) on: {topic}; "
                  f"credibility per FDA CM&S / ASME V&V 40 discipline")
    elif cls == "REGULATORY_REQUIRED":
        action = (f"Regulatory pathway engagement on: {topic} "
                  f"(FDA pre-submission / standards applicability review)")
    elif cls == "LEGAL_IP_REQUIRED":
        action = (f"Patent counsel work on: {topic} "
                  f"(prior-art classification search / FTO opinion)")
    else:
        action = (f"Data-acquisition or long-lead program on: {topic} "
                  f"— not resolvable by bench, computation, literature or "
                  f"design work alone at the current stage")

    if cls == "BENCH_TEST_REQUIRED":
        expected = f"Measured value of {topic.lower()} with stated uncertainty"
    elif cls == "ENGINEERING_DESIGN_REQUIRED":
        expected = f"Selected {topic.lower()} with recorded design basis"
    elif cls == "LITERATURE_RESOLVABLE":
        expected = "Cited literature result or documented absence"
    elif cls == "COMPUTATION_RESOLVABLE":
        expected = "Simulation result with uncertainty and model credibility statement"
    elif cls == "REGULATORY_REQUIRED":
        expected = "Documented pathway decision (product code / submission type)"
    elif cls == "LEGAL_IP_REQUIRED":
        expected = "Counsel-authored FTO/novelty opinion"
    else:
        expected = "Acquired dataset or long-lead evidence; not predictable at this stage"

    impact = ("Gates package feasibility (marked CRITICAL in the canonical record)"
              if critical else
              "Gates design detail and the next work package, not package feasibility")

    return {
        "unknown_id": None,  # assigned by caller (U-01...)
        "unknown_statement": unknown,
        "classification": cls,
        "classification_basis": rule_id,
        "is_critical": critical,
        "resolution_action": action,
        "expected_output": expected,
        "decision_impact": impact,
        "linked_build_plan_step": step.get("work_package") if step else None,
    }


def build_unknown_roadmap(pkg) -> dict:
    """UNKNOWN_ROADMAP.json content for one package."""
    entries = []
    for i, unknown in enumerate(pkg.unknowns, start=1):
        e = classify_unknown(unknown, pkg)
        e["unknown_id"] = f"U-{i:02d}"
        entries.append(e)
    counts = {c: 0 for c in CLASSES}
    for e in entries:
        counts[e["classification"]] += 1
    return {
        "package_id": pkg.pkg_id,
        "portfolio_number": pkg.num,
        "unknown_count_source": len(pkg.unknowns),
        "unknown_count_roadmap": len(entries),
        "discipline": (
            "UNKNOWN counts are preserved exactly as recorded in the "
            "canonical engineering record. Classification is mechanical "
            "(each entry records the rule that fired) and converts each "
            "unknown into a resolution action, expected output and "
            "decision impact — an engineering roadmap, not a reduced count."
        ),
        "classification_counts": counts,
        "unknowns": entries,
    }
