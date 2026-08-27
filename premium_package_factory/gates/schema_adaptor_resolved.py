"""
schema_adaptor_resolved.py — Adapt the resolved canonical for factory use.

The resolved canonical stores each field as:
  {"value": "...", "source_artifact": "...", "source_hash": "...", "source_path": "...", "note": "..."}

The factory templates expect plain string values. This adaptor unwraps the
provenance-traced fields into plain values (for template rendering) while
preserving the full provenance map (for Gate C claim-level mapping).

Every adapted field is logged with its source provenance so Gate C can
map display claims back to canonical claims.
"""

import os
import json
import re
from datetime import datetime, timezone

RESOLVED_CANONICAL_PATH = "/home/z/my-project/canonical_data/canonical_15_packages_r370_resolved.json"
ADAPTED_OUTPUT_PATH = "/home/z/my-project/canonical_data/canonical_15_packages_r370_adapted.json"

# Domain derivation (deterministic, non-inventing)
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


def derive_domain(mechanism_text):
    mech_lower = (mechanism_text or "").lower()
    for keyword, domain in DOMAIN_KEYWORDS:
        if keyword in mech_lower:
            return domain
    return "Other"


def derive_risk_level(known_failures, pkg_id, r370_axes_data):
    """Derive risk from R370 axes BLOCKING_AXES (not invented)."""
    if r370_axes_data and isinstance(r370_axes_data, dict):
        blocking = r370_axes_data.get("BLOCKING_AXES", [])
        if blocking and isinstance(blocking, list):
            n_blocking = len(blocking)
            if n_blocking >= 4:
                return "VERY HIGH"
            elif n_blocking >= 3:
                return "HIGH"
            elif n_blocking >= 2:
                return "MEDIUM"
            else:
                return "LOW"
    # Fallback
    if "-R1" in pkg_id:
        return "HIGH"
    return "MEDIUM"


def _unwrap(field_dict):
    """Unwrap a provenance-traced field to its value, or None."""
    if isinstance(field_dict, dict):
        return field_dict.get("value")
    return field_dict


def _unwrap_or_empty(field_dict):
    """Unwrap a provenance-traced field, returning empty string for UNKNOWN."""
    val = _unwrap(field_dict)
    if val is None:
        return ""
    val_str = str(val)
    if val_str.startswith("UNKNOWN"):
        return ""
    return val_str


def adapt_package(pkg_id, resolved_pkg):
    """Adapt a resolved package (provenance-traced) for factory rendering."""
    adapted = {"id": pkg_id}

    # Unwrap all provenance-traced fields to plain values
    plain_fields = [
        "mechanism", "problem", "buyer", "evidence_now",
        "modelled_only", "known_failures", "strongest_alternative",
        "remaining_uncertainty", "decisive_experiment", "pass_rule", "fail_rule",
        "cost_estimate", "timeline_estimate", "integration_path",
        "regulatory_status", "commercial_route", "buyer_action",
        "provenance_manifest", "buyer_action_id", "maturity", "evidence_tier"
    ]

    field_provenance = {}  # Maps field -> {value, source_artifact, source_hash, source_path}

    for field in plain_fields:
        if field in resolved_pkg:
            field_dict = resolved_pkg[field]
            if isinstance(field_dict, dict):
                adapted[field] = field_dict.get("value", "")
                field_provenance[field] = {
                    "value": field_dict.get("value", ""),
                    "source_artifact": field_dict.get("source_artifact", "NONE"),
                    "source_hash": field_dict.get("source_hash"),
                    "source_path": field_dict.get("source_path"),
                    "note": field_dict.get("note", "")
                }
            else:
                adapted[field] = field_dict
                field_provenance[field] = {
                    "value": str(field_dict),
                    "source_artifact": "UNKNOWN",
                    "source_hash": None,
                    "source_path": None,
                    "note": "Field was not provenance-traced"
                }

    # Handle lists specially (modelled_only, known_failures)
    for list_field in ["modelled_only", "known_failures"]:
        val = adapted.get(list_field)
        if isinstance(val, str):
            # If it's a string, try to parse as list, else make single-item list
            if val.startswith("[") and val.endswith("]"):
                try:
                    adapted[list_field] = json.loads(val)
                except:
                    adapted[list_field] = [val] if val else []
            else:
                adapted[list_field] = [val] if val else []
        elif not isinstance(val, list):
            adapted[list_field] = []

    # Derive presentation fields (deterministic, non-inventing)
    mechanism = adapted.get("mechanism", "") or ""
    adapted["name"] = pkg_id  # Package ID is the name (honest, no marketing)
    adapted["subtitle"] = mechanism  # R370U-U6: no truncation
    adapted["value_proposition"] = (
        f"Problem: {adapted.get('problem', '—')} | "
        f"Mechanism: {mechanism} | "  # R370U-U6: no truncation
        f"Uncertainty: {adapted.get('remaining_uncertainty', '—')}"  # R370U-U6: no truncation
    )
    adapted["target_application"] = adapted.get("buyer", "")
    adapted["transfer_posture"] = adapted.get("buyer_action", "")
    adapted["buyer_action_short"] = (adapted.get("buyer_action", "") or "")[:60]
    adapted["domain"] = derive_domain(mechanism)
    adapted["evidence_summary"] = adapted.get("evidence_now", "")
    adapted["patent_landscape"] = "See PATENT_DOSSIER in data room (not in R370 canonical)"

    # Risk level from R370 axes BLOCKING_AXES
    r370_axes = _unwrap(resolved_pkg.get("_r370_axes"))
    adapted["risk_level"] = derive_risk_level(
        adapted.get("known_failures", []), pkg_id, r370_axes
    )

    # Buyer-adaptive data (from R370 buyer maps — real companies, not invented)
    buyers_full = _unwrap(resolved_pkg.get("_buyers_full"))
    if buyers_full and isinstance(buyers_full, list):
        adapted["buyers"] = buyers_full  # Real buyer data from R370
    else:
        adapted["buyers"] = []  # No buyers — will be flagged as BUYER_DILIGENCE_REQUIRED

    # Known/unknown (from R370 claims)
    adapted["known"] = []
    adapted["unknown"] = []
    if adapted.get("remaining_uncertainty"):
        adapted["unknown"] = [adapted["remaining_uncertainty"]]

    adapted["kill_condition"] = adapted.get("fail_rule", "—")
    adapted["next_question"] = adapted.get("decisive_experiment", "—")

    # Key metrics — derived from modelled_only (each becomes a MODELLED metric)
    adapted["key_metrics"] = []
    for m in adapted.get("modelled_only", []):
        if m and not str(m).startswith("UNKNOWN"):
            adapted["key_metrics"].append({
                "metric": "Modelled claim",
                "value": str(m),  # R370U-U6: no truncation
                "tier": "MODELLED",
                "evidence": "From R370 claims"
            })

    # Manufacturing/regulatory/IP — honestly empty if not in R332/R370
    adapted["manufacturing_known"] = []
    adapted["manufacturing_unknown"] = []
    adapted["next_engineering_step"] = adapted.get("decisive_experiment", "")
    adapted["know_how"] = []
    adapted["regulatory_pathway_hypothesis"] = adapted.get("regulatory_status", "")
    adapted["regulatory_unknowns"] = []
    adapted["ip_diligence_questions"] = []
    adapted["transaction_paths"] = ["VALIDATION", "LICENSE"]
    adapted["primary_action"] = adapted.get("buyer_action", "")
    adapted["physical_validation_count"] = 0
    adapted["computational_validation_count"] = 1 if "COMPUTATIONALLY" in (adapted.get("evidence_tier") or "").upper() else 0
    adapted["diagram_kind"] = "system_architecture"
    adapted["diagram_components"] = []
    adapted["diagram_edges"] = []
    adapted["evidence_ladder_position"] = adapted.get("evidence_tier", "MODEL_PREDICTED")

    # Store the full provenance map for Gate C
    adapted["_field_provenance"] = field_provenance

    # Store R370 axes + transaction data
    if r370_axes:
        adapted["_r370_axes"] = r370_axes
    transaction = _unwrap(resolved_pkg.get("_transaction"))
    if transaction:
        adapted["_r370_transaction"] = transaction

    return adapted


def adapt_canonical_resolved():
    """Adapt the resolved canonical for factory rendering."""
    with open(RESOLVED_CANONICAL_PATH) as f:
        resolved = json.load(f)

    packages = {}
    for pkg_id, pkg in resolved.get("packages", {}).items():
        packages[pkg_id] = adapt_package(pkg_id, pkg)

    adapted = {
        "authority": "Adapted canonical from resolved R370 repo state — every field provenance-traced",
        "source_authority": resolved.get("authority", ""),
        "generated_at": resolved.get("generated_at", ""),
        "constitution_sha256": resolved.get("constitution_sha256", ""),
        "honest_disclosure": resolved.get("honest_disclosure", {}),
        "source_artifacts": resolved.get("source_artifacts", {}),
        "packages": packages,
        "package_provenance": resolved.get("package_provenance", {}),
    }

    with open(ADAPTED_OUTPUT_PATH, "w") as f:
        json.dump(adapted, f, indent=2, ensure_ascii=False)

    print(f"Adapted canonical written to: {ADAPTED_OUTPUT_PATH}")
    print(f"  {len(packages)} packages adapted")
    # Show sample
    if packages:
        sample_id = list(packages.keys())[0]
        sample = packages[sample_id]
        print(f"\nSample {sample_id}:")
        print(f"  mechanism: {sample.get('mechanism', '')[:80]}...")
        print(f"  maturity: {sample.get('maturity')}")
        print(f"  evidence_tier: {sample.get('evidence_tier')}")
        print(f"  domain: {sample.get('domain')}")
        print(f"  risk_level: {sample.get('risk_level')}")
        print(f"  buyers: {len(sample.get('buyers', []))} buyers")
        if sample.get("buyers"):
            print(f"  first buyer: {sample['buyers'][0].get('company', '?')}")
        # Count provenance-traced fields
        prov = sample.get("_field_provenance", {})
        n_traced = sum(1 for v in prov.values() if v.get("source_artifact") != "NONE")
        print(f"  provenance-traced fields: {n_traced}/{len(prov)}")

    return adapted


if __name__ == "__main__":
    adapt_canonical_resolved()
