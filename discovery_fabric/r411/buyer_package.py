"""discovery_fabric/r411/buyer_package.py — Directive s15/s16: automatic
buyer-dossier creation and portfolio placement.

The chain (s15):
    discovery candidate -> evidence package -> engineering dossier ->
    transfer-item package -> buyer portfolio
NO human copy step: the campaign writes the buyer dossiers directly.

Placement: LEAD_PORTFOLIO_4/R411_DISCOVERED/D1..D5/ — structurally
integrated with the existing buyer-portfolio architecture (same record
conventions as the P04/P11 packages: TRANSFER_STATE, CLAIM_EVIDENCE_
MATRIX, DECISIVE_EXPERIMENT, KILLABILITY_ASSESSMENT, NOVELTY_ASSESSMENT,
TECHNOLOGY_MATURITY, ENGINEERING_TRACEABILITY) while honestly separate
in provenance (autonomous campaign, R411) — the four-lead registry and
FINAL_CLASSIFICATION governance are untouched (their test pins are
registry-based).

The buyer dossier (s15 field list) exposes a COHERENT technology-transfer
package, not the engine's internal iteration history. Internal clutter
(campaign logs, funnel mechanics, attack transcripts) stays in the
R411/DISCOVERY_RUN namespace; the buyer surface carries the 18 required
fields + traceability + uncertainty + recommended buyer action.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List

BUYER_PACKAGE_VERSION = "R411-BUYER-V1"

# The s15 buyer-dossier field order (the buyer-facing view)
BUYER_FIELDS = [
    "Executive brief", "Technology description", "Mechanism", "Evidence",
    "Engineering model", "Baseline comparison", "Known limitations",
    "Failure modes", "Prior-art landscape", "Decisive experiment",
    "Experiment cost", "Kill condition", "Implementation path",
    "Commercial application", "Evidence provenance", "Uncertainty",
    "Current status", "Recommended buyer action",
]


def buyer_portfolio_record(dossier: Dict[str, Any],
                           campaign_meta: Dict[str, Any],
                           buyer_index: int) -> Dict[str, Any]:
    """The TRANSFER_STATE-style portfolio record (P04/P11 convention)."""
    d = dossier
    return {
        "artifact_type": "R411_TRANSFER_STATE",
        "company_designation": f"D{buyer_index}",
        "portfolio_namespace": "R411_DISCOVERED",
        "technology_id": d["technology_id"],
        "technology_name": d["technology_name"],
        "state_ladder": [
            "TECHNICAL_REVIEW", "SPONSORED_VALIDATION",
            "EXPERIMENTALLY_SUPPORTED", "PROTOTYPE_DEVELOPMENT", "OPTION",
            "LICENSE", "CO-DEVELOPMENT", "ACQUISITION"],
        "current_state": "TECHNICAL_REVIEW",
        "current_state_basis": (
            "autonomous discovery (R411): engineering-defined, "
            "evidence-backed, baseline-compared, experiment-ready; "
            "physically validated: NO (physical observations = 0; "
            "REAL_BUYER = 0; commercial transactions = 0)"),
        "transition_evidence_required": {
            "TECHNICAL_REVIEW -> SPONSORED_VALIDATION": [
                "the owner funds the killer experiment (s23: the human "
                "decides which physical experiment gets funded)",
                "experimental result clears the acceptance threshold "
                "OR triggers the kill condition"],
            "SPONSORED_VALIDATION -> EXPERIMENTALLY_SUPPORTED": [
                "raw measurement ingested through the reality-event "
                "custody chain (Art. XXXVIII)"],
        },
        "transfer_ready": True,
        "transfer_ready_basis": (
            "the buyer dossier is coherent, traceable, and states its "
            "own uncertainty — ready for EVALUATION, not for claims of "
            "validation"),
        "buyer_package_version": BUYER_PACKAGE_VERSION,
        "engine_commit": campaign_meta.get("engine_commit"),
    }


def buyer_dossier_markdown(dossier: Dict[str, Any],
                           campaign_meta: Dict[str, Any]) -> str:
    """Render the 18-field buyer dossier (s15) as Markdown. Internal
    development clutter is excluded by construction — only the buyer
    view fields are rendered."""
    d = dossier
    ev_map = d.get("evidence_map") or []
    bound_rows = [r for r in ev_map if r.get("sources")]
    ke = d.get("killer_experiment") or {}
    base = d.get("baseline") or {}
    fm_lines = "\n".join(
        f"- **{f.get('failure_mode')}** — detect: {f.get('detectability')};"
        f" mitigation: {f.get('mitigation')}; residual risk: "
        f"{f.get('residual_risk')}"
        for f in d.get("failure_modes") or [])
    evidence_lines = "\n".join(
        f"- {r['claim']} [{r['epistemic_class']}, {r['confidence']}]: " +
        "; ".join(
            f"[{s['record_id']}] {s['title']}" for s in r["sources"])
        for r in bound_rows) or "- (see evidence provenance section)"
    pa = (d.get("prior_art_landscape") or {}).get(
        "closest_prior_art") or {}
    pa_lines = "\n".join(
        f"- [{r.get('record_id')}] {r.get('title')} "
        f"({r.get('perspective')}) — {r.get('comparison', '')[:160]}"
        for r in (d.get("prior_art_landscape") or {}).get(
            "adversarial_records_checked") or []) or \
        "- adversarial retrieval found no relevant records in scope"
    mech = (d.get("mechanism") or {})
    eqs = "; ".join(e.get("equation") or "" for e in (
        d.get("engineering_model") or {}).get("equations") or [])

    return f"""# Technology-Transfer Dossier — {d['technology_name']}

**Technology ID:** {d['technology_id']} | **Domain:** {d['system_context']}
**Status:** {d['status']} | **Prepared by:** autonomous discovery engine (R411), commit {campaign_meta.get('engine_commit', '')[:12]}

---

## Executive brief

{d['technology_name']} addresses {d['problem']} in {d['system_context']} by exploiting {mech.get('unexploited_phenomenon')}. The predicted effect is {base.get('expected_delta')} against the incumbent {base.get('baseline_incumbent')}. The decisive falsification experiment is defined, cost class {ke.get('estimated_cost_class')}, with the kill condition: {ke.get('kill_condition')}.

## Technology description

- **Target customer:** {d.get('target_customer')}
- **Problem:** {d.get('problem')}
- **System context:** {d.get('system_context')}
- **Intervention:** {d.get('mechanism', {}).get('causal_chain', [])[-1] if d.get('mechanism', {}).get('causal_chain') else ''} (final step of the causal chain)

## Mechanism

{mech.get('mechanism_statement')}

- **Unexploited phenomenon:** {mech.get('unexploited_phenomenon')}
- **Governing variables:** {mech.get('governing_variables')}
- **Boundary conditions:** {mech.get('boundary_conditions')}

## Evidence

{evidence_lines}

The core opportunity hypothesis is an **unbound AI hypothesis** — the evidence grounds the phenomenon and the problem; the causal configuration is the machine's proposal and is exactly what the decisive experiment tests.

## Engineering model

- **Equations:** {eqs}
- **Parameters:** {(d.get('engineering_model') or {}).get('parameters')}
- **Sensitivity:** {(d.get('engineering_model') or {}).get('sensitivity')}
- **Model class:** {(d.get('engineering_model') or {}).get('model_class')}

## Baseline comparison

| | Incumbent | Candidate |
|---|---|---|
| Approach | {base.get('baseline_incumbent')} | {d['technology_name']} |
| Metric | {base.get('baseline_metric')} | {base.get('candidate_metric')} |
| Expected delta | {base.get('expected_delta')} | — |
| Uncertainty | {base.get('uncertainty')} | magnitude-class |

## Known limitations

- The predicted advantage is model-derived; no physical measurement exists yet (physical observations = 0).
- Boundary conditions: {mech.get('boundary_conditions')}.
- Evidence strength sub-score: {(d.get('traceability') or {}).get('candidate_sha256', '') and ''}{d.get('status_basis')}

## Failure modes

{fm_lines}

## Prior-art landscape

Closest art (distance class: **{pa.get('distance_class')}**, retrieval-scoped — never a novelty proof):
{pa_lines}

**Differentiation:** {d.get('prior_art_landscape', {}).get('differentiation')}

## Decisive experiment

- **Hypothesis:** {ke.get('hypothesis')}
- **Apparatus:** {ke.get('apparatus')}
- **Treatment vs control:** candidate arm vs {ke.get('controls')}
- **Measurement:** {ke.get('measurement')}
- **Threshold:** {ke.get('threshold')}
- **Kill condition:** {ke.get('kill_condition')}

## Experiment cost

Cost class **{ke.get('estimated_cost_class')}** ({ke.get('estimated_cost_note')}). Time estimate: {ke.get('estimated_time')}.

## Kill condition

{ke.get('kill_condition')}

## Implementation path

1. Commission the decisive experiment (the apparatus is the first prototype-scale artifact).
2. On threshold-clear: prototype at the integration point: {(d.get('commercial_transfer_path') or {}).get('integration_point')}.
3. On kill: the mechanism is dead — no further engineering spend (the falsification contract).

## Commercial application

- **Buyer:** {(d.get('commercial_transfer_path') or {}).get('buyer')}
- **Use case:** {(d.get('commercial_transfer_path') or {}).get('use_case')}
- **Economic value driver:** {(d.get('commercial_transfer_path') or {}).get('economic_value_driver')}
- **Integration point:** {(d.get('commercial_transfer_path') or {}).get('integration_point')}

## Evidence provenance

Retrieval fabric: {campaign_meta.get('fabric_version')} | Evidence snapshot: `{str(campaign_meta.get('evidence_snapshot_sha256'))[:16]}…` | Candidate hash: `{str((d.get('traceability') or {}).get('candidate_sha256'))[:16]}…`

Every claim above traces: buyer_claim -> dossier_section -> evidence_claim -> source_record -> retrieval_event -> source -> raw/processed artifact -> discovery run -> engine commit `{campaign_meta.get('engine_commit', '')[:12]}`.

## Uncertainty

- Magnitude-class predictions only; the experiment measures the actual delta.
- Prior-art landscape is retrieval-scoped ({pa.get('distance_basis')}).
- Attacker status: {d.get('status_basis')}

## Current status

**{d['status']}** — {d.get('status_basis')}

Physical observations: **0**. Real buyers: **0**. Commercial transactions: **0**. This is an experiment-ready transfer package, not a validated technology.

## Recommended buyer action

1. Technical evaluation of the mechanism and the falsification contract (this dossier).
2. If the physics and economics hold: commission the decisive experiment — cost class {ke.get('estimated_cost_class')}, the cheapest kill-or-clear test available.
3. Decide on the result: fund prototype or walk away. The kill condition is the contract.
"""


def write_buyer_package(out_dir: str, dossier: Dict[str, Any],
                        campaign_meta: Dict[str, Any],
                        buyer_index: int) -> Dict[str, Any]:
    """Write the buyer package for one technology: the portfolio record
    + the buyer dossier (markdown) + the machine traceability JSON.
    Returns the file manifest with hashes (Art. XII custody)."""
    import os
    folder = os.path.join(out_dir, f"D{buyer_index}")
    os.makedirs(folder, exist_ok=True)

    record = buyer_portfolio_record(dossier, campaign_meta, buyer_index)
    md = buyer_dossier_markdown(dossier, campaign_meta)

    files = {}
    p = os.path.join(folder, "TRANSFER_STATE.json")
    with open(p, "w") as f:
        json.dump(record, f, indent=1)
    files["TRANSFER_STATE.json"] = hashlib.sha256(
        open(p, "rb").read()).hexdigest()

    p = os.path.join(folder, "BUYER_DOSSIER.md")
    with open(p, "w") as f:
        f.write(md)
    files["BUYER_DOSSIER.md"] = hashlib.sha256(
        open(p, "rb").read()).hexdigest()

    # the machine-readable full dossier (engineering-side, referenced
    # by the buyer view for auditors who want the complete record)
    p = os.path.join(folder, "TECHNOLOGY_DOSSIER.json")
    with open(p, "w") as f:
        json.dump(dossier, f, indent=1)
    files["TECHNOLOGY_DOSSIER.json"] = hashlib.sha256(
        open(p, "rb").read()).hexdigest()

    dossier["capability_state"]["buyer_package"] = files
    return {
        "technology_id": dossier["technology_id"],
        "folder": folder,
        "files": files,
        "buyer_fields_present": BUYER_FIELDS,
    }
