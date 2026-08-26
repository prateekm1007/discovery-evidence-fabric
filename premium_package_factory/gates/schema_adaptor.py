"""
schema_adaptor.py — Derive presentation fields from R332 canonical schema.

The R332 canonical has 17+2 fields per package:
  buyer_action_id, problem, buyer, mechanism, evidence_now,
  modelled_only, known_failures, strongest_alternative,
  remaining_uncertainty, decisive_experiment, pass_rule, fail_rule,
  cost_estimate, timeline_estimate, integration_path,
  regulatory_status, commercial_route, buyer_action, provenance_manifest

The factory's PDF templates need presentation fields:
  id, name, subtitle, value_proposition, target_application, maturity,
  transfer_posture, buyer_action_short, domain, evidence_tier, etc.

This adaptor DERIVES presentation fields from R332 fields using
DETERMINISTIC, NON-INVENTING rules. Every derived field is traceable
to its R332 source field. No new technical claims are introduced.

Derivation rules:
  name             <- buyer_action_id (e.g., "P-01" → "P-01")
                     + mechanism (first 50 chars as subtitle)
  subtitle         <- mechanism (full text)
  value_proposition <- problem + " " + mechanism + " " + remaining_uncertainty
                      (assembled from R332 fields, no new claims)
  target_application <- buyer field (the buyer segment IS the target application)
  maturity         <- derived from evidence_now:
                      "T2" in evidence_now → "ENGINEERING"
                      "T1" in evidence_now → "RESEARCH"
                      "R1 repair" in evidence_now → "RESEARCH" (R1 repair)
                      else → "RESEARCH"
  transfer_posture <- buyer_action field (verbatim from R332)
  buyer_action_short <- first 60 chars of buyer_action
  domain           <- derived from mechanism keywords (deterministic mapping)
  evidence_tier    <- extracted from evidence_now (T0/T1/T2/T3)
  evidence_summary <- evidence_now (verbatim)
  patent_landscape <- "See PATENT_DOSSIER.json in data room" (not in R332)

Every derived field is logged with its derivation rule.
"""

import re
import json


# Domains derived from mechanism keywords (deterministic, non-inventing)
DOMAIN_KEYWORDS = [
    ("multi-segment", "Hydraulics + Control"),
    ("bayesian", "Hydraulics + Control"),
    ("occlusion", "Hydraulics + Control"),
    ("valve", "Valve Mechanics"),
    ("icp", "Valve Mechanics"),
    ("postural", "Valve Mechanics"),
    ("gravity", "Passive Fluidic Mechanics"),
    ("damper", "Passive Fluidic Mechanics"),
    ("enzyme", "Enzyme Kinetics"),
    ("catalytic", "Enzyme Kinetics"),
    ("nep", "Enzyme Kinetics"),
    ("ab42", "Enzyme Kinetics"),
    ("tau", "Enzyme Kinetics"),
    ("phage", "Microbiology"),
    ("biofilm", "Microbiology"),
    ("s. aureus", "Microbiology"),
    ("ml", "Machine Learning"),
    ("predictor", "Machine Learning"),
    ("gradient boosting", "Machine Learning"),
    ("energy harvest", "Energy Harvesting"),
    ("piezoelectric", "Energy Harvesting"),
    ("capacitor", "Energy Harvesting"),
    ("940nm", "Optics + Photonics"),
    ("nir", "Optics + Photonics"),
    ("gaas", "Optics + Photonics"),
    ("photovoltaic", "Optics + Photonics"),
    ("rfid", "RF + Localization"),
    ("uwb", "RF + Localization"),
    ("localization", "RF + Localization"),
    ("hydraulic", "Hydraulics + Catheter Navigation"),
    ("navigation", "Hydraulics + Catheter Navigation"),
    ("shape-memory", "Hydraulics + Catheter Navigation"),
    ("osmotic", "Chemical-Mechanical Fluidics"),
    ("osmolarity", "Chemical-Mechanical Fluidics"),
    ("piezoresistive", "MEMS + Sensor Materials"),
    ("pressure sensor", "MEMS + Sensor Materials"),
    ("acoustic", "Acoustics + Sensing"),
    ("resonance", "Acoustics + Sensing"),
    ("nmr", "Magnetic Resonance + Sensors"),
    ("spin", "Magnetic Resonance + Sensors"),
    ("mr flow", "Magnetic Resonance + Sensors"),
]


def derive_domain(mechanism):
    """Derive domain from mechanism text using keyword matching."""
    mech_lower = (mechanism or "").lower()
    for keyword, domain in DOMAIN_KEYWORDS:
        if keyword in mech_lower:
            return domain
    return "Other"


def derive_maturity(evidence_now, pkg_id=""):
    """Derive maturity from evidence_now field.

    Rules (deterministic, non-inventing):
    - If evidence_now contains "T2-CONFIRMED" or "T2-CONDITIONAL" → ENGINEERING
    - If evidence_now contains "T1" → RESEARCH
    - If pkg_id contains "-R1" → RESEARCH (R1 repair, even if base was T2)
    - Else → RESEARCH
    """
    ev = (evidence_now or "").upper()
    if "R1" in pkg_id.upper():
        return "RESEARCH"  # R1 repairs are always RESEARCH (model unverified)
    if "T2-CONFIRMED" in ev:
        return "ENGINEERING"
    if "T2-CONDITIONAL" in ev:
        return "ENGINEERING"
    return "RESEARCH"


def derive_evidence_tier(evidence_now):
    """Extract evidence tier from evidence_now field."""
    ev = (evidence_now or "").upper()
    if "T2-CONFIRMED" in ev:
        return "T2-CONFIRMED"
    if "T2-CONDITIONAL" in ev:
        return "T2-CONDITIONAL"
    if "T2" in ev:
        return "T2"
    if "T1" in ev:
        return "T1_MODEL_PREDICTED"
    return "T1_MODEL_PREDICTED"


def derive_name(pkg_id, mechanism):
    """Derive a short name from package ID + mechanism.

    The name is the package ID. The subtitle is the mechanism.
    This is the most honest approach — we don't invent marketing names.
    """
    return pkg_id


def derive_subtitle(mechanism):
    """Subtitle = mechanism (verbatim from R332)."""
    return mechanism or ""


def derive_value_proposition(problem, mechanism, remaining_uncertainty):
    """Assemble value proposition from R332 fields.

    Format: "Problem: {problem} Mechanism: {mechanism} Uncertainty: {remaining_uncertainty}"
    This is NOT an invented marketing claim — it's a structured assembly of R332 fields.
    """
    parts = []
    if problem:
        parts.append(f"Problem: {problem}")
    if mechanism:
        parts.append(f"Mechanism: {mechanism}")
    if remaining_uncertainty:
        parts.append(f"Uncertainty: {remaining_uncertainty}")
    return " | ".join(parts)


def derive_target_application(buyer):
    """Target application = buyer field (the buyer segment IS the target)."""
    return buyer or ""


def derive_buyer_action_short(buyer_action):
    """First 60 chars of buyer_action."""
    if not buyer_action:
        return ""
    return buyer_action[:60] + ("…" if len(buyer_action) > 60 else "")


def derive_buyers_list(buyer_field):
    """Derive a single buyer entry from the R332 buyer field.

    R332 has a single 'buyer' string (e.g., "Shunt OEM (Medtronic, Integra, Sophysa)").
    We parse this into a single buyer card with the raw buyer field.
    We do NOT invent specific buyer names, gaps, or objections — those would be
    inventions not present in R332.

    The buyer-adaptive packaging (Gate 4) will need the CEO to provide
    buyer-specific context, OR we use the buyer field as-is.
    """
    return [{
        "name": buyer_field or "—",
        "why": "(not specified in R332 canonical — buyer-specific 'why' requires CEO-provided buyer context)",
        "existing_product": "(not specified in R332 canonical)",
        "gap": "(not specified in R332 canonical)",
        "build_vs_buy": "(not specified in R332 canonical)",
        "likely_objection": "(not specified in R332 canonical)",
        "first_technical_action": "(see buyer_action field)",
    }]


def derive_risk_level(known_failures, pkg_id):
    """Derive risk level from known_failures count + R1 status.

    Rules:
    - If pkg_id contains "-R1" → HIGH (R1 repair, original failed)
    - If known_failures has >= 3 items → HIGH
    - If known_failures has 1-2 items → MEDIUM
    - If known_failures is empty → MEDIUM
    """
    if "-R1" in pkg_id:
        return "HIGH"
    n_failures = len(known_failures or [])
    if n_failures >= 3:
        return "HIGH"
    return "MEDIUM"


def derive_known_unknown(manufacturing_known=None, manufacturing_unknown=None,
                          known=None, unknown=None):
    """Pass through known/unknown lists if provided, else empty."""
    return {
        "known": known or [],
        "unknown": unknown or [],
    }


def derive_kill_condition(fail_rule):
    """Kill condition = fail_rule (verbatim from R332)."""
    return fail_rule or "—"


def derive_next_question(decisive_experiment):
    """Next question = decisive_experiment (verbatim from R332)."""
    return decisive_experiment or "—"


def derive_key_metrics(modelled_only, cost_estimate, timeline_estimate):
    """Derive key metrics from R332 fields.

    Each modelled_only entry becomes a metric with tier=MODELLED.
    Cost and timeline become metrics with tier=ESTIMATED.
    """
    metrics = []
    for m in (modelled_only or []):
        metrics.append({
            "metric": "Modelled claim",
            "value": m,
            "tier": "MODELLED",
            "evidence": "Computational model (R332 evidence_now field)"
        })
    if cost_estimate:
        metrics.append({
            "metric": "Cost",
            "value": cost_estimate,
            "tier": "ESTIMATED",
            "evidence": "R332 cost_estimate field"
        })
    if timeline_estimate:
        metrics.append({
            "metric": "Timeline",
            "value": timeline_estimate,
            "tier": "ESTIMATED",
            "evidence": "R332 timeline_estimate field"
        })
    return metrics


def adapt_package(pkg_id, r332_pkg):
    """Adapt a single R332 package to the factory's expected schema.

    Every derived field is logged with its derivation rule.
    """
    mechanism = r332_pkg.get("mechanism", "")
    problem = r332_pkg.get("problem", "")
    evidence_now = r332_pkg.get("evidence_now", "")
    remaining_uncertainty = r332_pkg.get("remaining_uncertainty", "")
    buyer = r332_pkg.get("buyer", "")
    buyer_action = r332_pkg.get("buyer_action", "")
    known_failures = r332_pkg.get("known_failures", [])
    modelled_only = r332_pkg.get("modelled_only", [])
    decisive_experiment = r332_pkg.get("decisive_experiment", "")
    fail_rule = r332_pkg.get("fail_rule", "")
    cost_estimate = r332_pkg.get("cost_estimate", "")
    timeline_estimate = r332_pkg.get("timeline_estimate", "")

    # Start with all R332 fields VERBATIM
    adapted = dict(r332_pkg)
    adapted["id"] = pkg_id

    # Add derived fields
    adapted["name"] = derive_name(pkg_id, mechanism)
    adapted["subtitle"] = derive_subtitle(mechanism)
    adapted["value_proposition"] = derive_value_proposition(
        problem, mechanism, remaining_uncertainty
    )
    adapted["target_application"] = derive_target_application(buyer)
    adapted["maturity"] = derive_maturity(evidence_now, pkg_id)
    adapted["transfer_posture"] = buyer_action  # verbatim
    adapted["buyer_action_short"] = derive_buyer_action_short(buyer_action)
    adapted["domain"] = derive_domain(mechanism)
    adapted["evidence_tier"] = derive_evidence_tier(evidence_now)
    adapted["evidence_summary"] = evidence_now  # verbatim
    adapted["patent_landscape"] = "See PATENT_DOSSIER.json in data room (not in R332 canonical)"
    adapted["buyers"] = derive_buyers_list(buyer)
    adapted["risk_level"] = derive_risk_level(known_failures, pkg_id)
    adapted["known"] = []  # R332 doesn't have explicit known list
    adapted["unknown"] = [remaining_uncertainty] if remaining_uncertainty else []
    adapted["kill_condition"] = derive_kill_condition(fail_rule)
    adapted["next_question"] = derive_next_question(decisive_experiment)
    adapted["key_metrics"] = derive_key_metrics(modelled_only, cost_estimate, timeline_estimate)
    adapted["manufacturing_known"] = []  # not in R332
    adapted["manufacturing_unknown"] = []  # not in R332
    adapted["next_engineering_step"] = decisive_experiment  # map to decisive experiment
    adapted["know_how"] = []  # not in R332
    adapted["regulatory_pathway_hypothesis"] = r332_pkg.get("regulatory_status", "")
    adapted["regulatory_unknowns"] = []  # not in R332
    adapted["ip_diligence_questions"] = []  # not in R332
    adapted["transaction_paths"] = ["VALIDATION", "LICENSE"]  # default
    adapted["primary_action"] = buyer_action  # verbatim
    adapted["physical_validation_count"] = 0  # honest default
    adapted["computational_validation_count"] = 1 if "T2" in (evidence_now or "").upper() else 0
    adapted["diagram_kind"] = "system_architecture"  # default, will be overridden by diagram factory
    adapted["diagram_components"] = []
    adapted["diagram_edges"] = []
    adapted["evidence_ladder_position"] = adapted["evidence_tier"]

    # Provenance: which fields are verbatim vs derived
    adapted["_derivation_provenance"] = {
        "verbatim_from_r332": [
            "buyer_action_id", "problem", "buyer", "mechanism", "evidence_now",
            "modelled_only", "known_failures", "strongest_alternative",
            "remaining_uncertainty", "decisive_experiment", "pass_rule", "fail_rule",
            "cost_estimate", "timeline_estimate", "integration_path",
            "regulatory_status", "commercial_route", "buyer_action", "provenance_manifest"
        ],
        "derived_deterministically": {
            "name": f"= package_id ({pkg_id})",
            "subtitle": "= mechanism (verbatim)",
            "value_proposition": "= 'Problem: ' + problem + ' | Mechanism: ' + mechanism + ' | Uncertainty: ' + remaining_uncertainty",
            "target_application": "= buyer (verbatim)",
            "maturity": f"= derive_maturity(evidence_now, pkg_id) → {adapted['maturity']}",
            "transfer_posture": "= buyer_action (verbatim)",
            "buyer_action_short": "= buyer_action[:60]",
            "domain": f"= derive_domain(mechanism) → {adapted['domain']}",
            "evidence_tier": f"= derive_evidence_tier(evidence_now) → {adapted['evidence_tier']}",
            "evidence_summary": "= evidence_now (verbatim)",
            "risk_level": f"= derive_risk_level(known_failures, pkg_id) → {adapted['risk_level']}",
            "kill_condition": "= fail_rule (verbatim)",
            "next_question": "= decisive_experiment (verbatim)",
            "key_metrics": "= modelled_only + cost_estimate + timeline_estimate (assembled)",
            "primary_action": "= buyer_action (verbatim)",
        },
        "not_in_r332_honestly_empty": [
            "manufacturing_known", "manufacturing_unknown", "know_how",
            "regulatory_unknowns", "ip_diligence_questions", "known",
            "diagram_components", "diagram_edges"
        ],
        "note": (
            "All technical claims are VERBATIM from R332 canonical. "
            "Presentation fields (name, subtitle, value_proposition, etc.) are "
            "DETERMINISTICALLY DERIVED from R332 fields — no new technical claims introduced. "
            "Fields not present in R332 (manufacturing, IP diligence, regulatory unknowns) "
            "are honestly empty, not invented."
        )
    }

    return adapted


def adapt_canonical(honest_canonical):
    """Adapt the honest canonical file to the factory's expected schema.

    Returns a dict with 'packages' (adapted) + provenance.
    """
    packages = {}
    for pkg_id, r332_pkg in honest_canonical.get("packages", {}).items():
        packages[pkg_id] = adapt_package(pkg_id, r332_pkg)

    return {
        "authority": "Adapted canonical for Premium Package Factory — R332 verbatim + deterministic derivation",
        "source_authority": honest_canonical.get("authority", ""),
        "generated_at": honest_canonical.get("generated_at", ""),
        "constitution_sha256": honest_canonical.get("constitution_sha256", ""),
        "honest_disclosure": honest_canonical.get("honest_disclosure", {}),
        "packages": packages,
        "package_provenance": honest_canonical.get("package_provenance", {}),
    }


if __name__ == "__main__":
    with open("/home/z/my-project/canonical_data/canonical_15_packages_r370_verified.json") as f:
        honest = json.load(f)
    adapted = adapt_canonical(honest)
    print(f"Adapted {len(adapted['packages'])} packages")
    for pkg_id, pkg in list(adapted["packages"].items())[:3]:
        print(f"\n{pkg_id}:")
        print(f"  name: {pkg['name']}")
        print(f"  subtitle: {pkg['subtitle'][:60]}...")
        print(f"  maturity: {pkg['maturity']}")
        print(f"  evidence_tier: {pkg['evidence_tier']}")
        print(f"  domain: {pkg['domain']}")
        print(f"  risk_level: {pkg['risk_level']}")

    # Write adapted canonical for factory use
    output = "/home/z/my-project/canonical_data/canonical_15_packages_r370_adapted.json"
    with open(output, "w") as f:
        json.dump(adapted, f, indent=2, ensure_ascii=False)
    print(f"\nAdapted canonical written to: {output}")
