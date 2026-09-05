"""discovery_fabric/r411/extract.py — Directive s3/s5/s6: evidence-grounded
candidate extraction.

The LLM proposes technology opportunities from the domain's FROZEN fabric
evidence pool. The no-fabrication gate (same discipline as R409's query
expansion gate) enforces:
  - every evidence_ref must be a record id that EXISTS in the frozen pool
    (LLM-invented record ids / DOIs / patent numbers never enter records);
  - every candidate must carry the Art. XLI canonical fields;
  - every candidate records the generation provenance (provider, model,
    prompt hash, output hash — Art. LXII).

Problem-first prompting (s5): the prompt presents the domain's PAIN
POINTS + the evidence pool, and asks for mechanisms that attack the pain
via phenomena EVIDENCED in the records — never "invent a technology".

Cross-domain forcing (s6): the prompt requires a cross-domain transition
field — "where else does this physical mechanism appear" — and the
candidate may retarget the mechanism to a different domain than the
source literature.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Dict, List, Optional

from .medical_exclusion import medical_exclusion_screen

EXTRACTION_VERSION = "R411-EXTRACT-V1"

# The 13 evidence-grounded candidates-per-call target: keep prompts small
# enough for the gateway's token budget while hitting the >=500 pool.
CANDIDATES_PER_CALL = 6

EXTRACTION_PROMPT = """You are a mechanism-discovery instrument inside an engineering discovery engine.

DOMAIN: {domain_label} ({domain_id})
PAIN POINTS TO ATTACK (the machine's problem facts — do not restate them, attack them):
{pain_points}

EVIDENCE POOL (retrieved from the live open-retrieval fabric; each record has a RECORD_ID):
{evidence_records}

TASK: Extract {n_candidates} TECHNOLOGY OPPORTUNITIES grounded in this evidence. Each opportunity is a mechanism-level hypothesis that attacks one pain point using a physical phenomenon DOCUMENTED in the records above. For each candidate you MUST:
1. Ground every mechanism claim in specific RECORD_IDs from the pool. Only cite RECORD_IDs that appear above. NEVER invent record ids, DOIs, patent numbers, or findings not present in the records.
2. Search for the pain point's underlying mechanism and ask: what unexploited physical phenomenon or cross-domain analogue could attack it? Where else does this mechanism appear (aerospace -> energy, optics -> manufacturing, biology -> industrial, ...)? A candidate MAY retarget a mechanism evidenced in one domain to a different target domain.
3. State a QUANTITATIVE predicted effect with magnitude class and governing variables (the physics that determines the magnitude).
4. State the incumbent approach (baseline) the candidate is measured against.
5. Define ONE cheapest decisive experiment that could kill the mechanism, with a kill condition and cost class (BENCH < ~25 kUSD commodity instruments; LAB ~25-150 kUSD custom apparatus; PILOT ~150k-2M process-scale; FIELD > 2M).
6. Enumerate at least 2 failure modes of the candidate itself with detection and mitigation.

OUTPUT FORMAT — for EACH candidate, exactly this block (plain text, no markdown):
CANDIDATE_ID: C-{domain_id}-{n}
TECHNOLOGY_NAME: <short name>
TARGET_DOMAIN: <the commercial application domain (NON-MEDICAL only: energy, industrial, manufacturing, materials, robotics, aerospace, automotive, electronics, thermal, fluid, environmental, agriculture, construction, semiconductor, telecom, data-center, mining, marine, chemical)>
SOURCE_DOMAIN: <the domain the evidence/mechanism comes from>
PAIN_CLASS: <one of the pain classes listed above>
PROBLEM: <the expensive/inefficient engineering problem, one sentence>
CAUSAL_CHAIN: <3-6 step mechanism chain: cause -> ... -> effect>
UNEXPLOITED_PHENOMENON: <the physical phenomenon from the records the candidate exploits>
INTERVENTION: <what is built/changed in the system>
GOVERNING_VARIABLES: <the physics variables that set the magnitude, with units>
PREDICTED_EFFECT: <quantitative magnitude class + direction, e.g. '30-60% reduction in X because Y scales with Z'>
EQUATIONS: <one or two governing equations with symbols, units stated>
BOUNDARY_CONDITIONS: <where the mechanism holds and where it fails>
EVIDENCE_REFS: <comma-separated RECORD_IDs from the pool that ground the mechanism/phenomenon claims>
CROSS_DOMAIN_TRANSITION: <source mechanism domain -> target application domain + one sentence why the transfer creates value; or 'NONE' if same-domain>
BASELINE_INCUMBENT: <the incumbent approach + its documented limitation>
BASELINE_METRIC: <metric the incumbent achieves, with units/uncertainty if stated in evidence>
CANDIDATE_METRIC: <predicted metric on the same measure>
EXPECTED_DELTA: <predicted change + magnitude class>
CHEAPEST_DECISIVE_EXPERIMENT: <apparatus, treatment vs control, measurement, sample>
DECISIVE_UNCERTAINTY: <the single unknown the experiment resolves>
KILL_CONDITION: <the experimental outcome that kills the mechanism>
COST_CLASS: <BENCH | LAB | PILOT | FIELD>
FAILURE_MODES: <2-4 modes, each 'mode | detectability | mitigation'>
BUYER: <who would pay: industry role, not a company name guess>
USE_CASE: <the buyer's use case>
INTEGRATION_POINT: <where it integrates into the buyer's system>
END CANDIDATE

Constraints:
- NON-MEDICAL target applications only (no clinical/implantable/diagnostic/therapeutic devices).
- Do not fabricate numbers: every magnitude must be either stated in the evidence records (cite the RECORD_ID) or derived from stated physics with its derivation shown in one sentence.
- Prefer candidates where the decisive experiment is cheap (BENCH/LAB) and the kill condition is sharp.
- Do NOT propose solution classes the evidence does not support.
"""

_CAND_RE = re.compile(
    r"CANDIDATE_ID:\s*(.+?)\n(.*?)END CANDIDATE", re.DOTALL)
_FIELD_RE = re.compile(r"^([A-Z_]+):\s*(.*)$", re.MULTILINE)

REQUIRED_FIELDS = [
    "TECHNOLOGY_NAME", "TARGET_DOMAIN", "SOURCE_DOMAIN", "PAIN_CLASS",
    "PROBLEM", "CAUSAL_CHAIN", "UNEXPLOITED_PHENOMENON", "INTERVENTION",
    "GOVERNING_VARIABLES", "PREDICTED_EFFECT", "EQUATIONS",
    "BOUNDARY_CONDITIONS", "EVIDENCE_REFS", "CROSS_DOMAIN_TRANSITION",
    "BASELINE_INCUMBENT", "BASELINE_METRIC", "CANDIDATE_METRIC",
    "EXPECTED_DELTA", "CHEAPEST_DECISIVE_EXPERIMENT",
    "DECISIVE_UNCERTAINTY", "KILL_CONDITION", "COST_CLASS",
    "FAILURE_MODES", "BUYER", "USE_CASE", "INTEGRATION_POINT",
]


def _evidence_block(pool: List[Dict[str, Any]], limit: int = 28) -> str:
    lines = []
    for r in pool[:limit]:
        rid = r.get("record_id") or r.get("id")
        title = str(r.get("title") or "")[:140]
        abstract = str(r.get("abstract") or r.get("snippet")
                       or r.get("summary") or "")[:420]
        year = r.get("year") or ""
        lane = r.get("fabric_lane") or (r.get("labeling") or {}).get("lane", "")
        pub = r.get("publication_status") or \
            (r.get("labeling") or {}).get("publication_status", "")
        lines.append(
            f"RECORD_ID: {rid}\n  year: {year} | lane: {lane} | type: {pub}"
            f"\n  title: {title}\n  abstract: {abstract}")
    return "\n".join(lines)


def build_extraction_prompt(entry: Dict[str, Any],
                            domain_spec: Dict[str, Any],
                            pool: List[Dict[str, Any]],
                            batch_offset: int = 0) -> str:
    pains = "\n".join(
        f"- {p}: {domain_spec['label']} / {system}"
        for system in domain_spec["systems"]
        for p in domain_spec["pain_points"])
    return EXTRACTION_PROMPT.format(
        domain_label=domain_spec["label"],
        domain_id=entry["domain_id"],
        pain_points=pains,
        evidence_records=_evidence_block(pool[batch_offset:]),
        n_candidates=CANDIDATES_PER_CALL,
    )


def parse_candidates(text: str, domain_id: str,
                     pool: List[Dict[str, Any]],
                     generation_meta: Dict[str, Any]) -> Dict[str, Any]:
    """Parse + validate LLM output. The NO-FABRICATION GATE:
    - every EVIDENCE_REFS entry must exist in the pool;
    - all REQUIRED_FIELDS present;
    - any violation REJECTS that candidate (recorded, never repaired —
      Art. IV: no fallback epistemology, Art. VII: no weakening to
      rescue).
    """
    pool_ids = {str(r.get("record_id") or r.get("id")) for r in pool}
    accepted: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []
    for m in _CAND_RE.finditer(text or ""):
        body = m.group(2)
        fields = dict(_FIELD_RE.findall(body))
        cand_id = m.group(1).strip()
        reasons = []
        for f in REQUIRED_FIELDS:
            if not fields.get(f, "").strip():
                reasons.append(f"missing field {f}")
        refs_raw = fields.get("EVIDENCE_REFS", "")
        ref_ids = [x.strip() for x in re.split(r"[,;]", refs_raw)
                   if x.strip()]
        valid_refs = [r for r in ref_ids if r in pool_ids]
        if not valid_refs:
            reasons.append("no valid evidence refs (fabrication gate)")
        elif len(valid_refs) < len(ref_ids):
            reasons.append(
                f"invalid refs dropped: "
                f"{[r for r in ref_ids if r not in pool_ids]}")
        if reasons:
            rejected.append({
                "candidate_id": cand_id,
                "reasons": reasons,
            })
            continue
        causal = [s.strip(" ->") for s in re.split(
            r"->|=>|→", fields["CAUSAL_CHAIN"]) if s.strip()]
        fms = []
        for fm in re.split(r"[;\n]", fields["FAILURE_MODES"]):
            parts = [p.strip() for p in fm.split("|")]
            if parts and parts[0] and parts[0].lower() not in ("none", ""):
                fms.append({
                    "failure_mode": parts[0],
                    "detectability": parts[1] if len(parts) > 1 else "",
                    "mitigation": parts[2] if len(parts) > 2 else "",
                })
        cross = fields.get("CROSS_DOMAIN_TRANSITION", "NONE")
        candidate = {
            "candidate_id": cand_id,
            "extraction_version": EXTRACTION_VERSION,
            "technology_name": fields["TECHNOLOGY_NAME"].strip(),
            "target_domain": fields["TARGET_DOMAIN"].strip(),
            "source_domain": fields["SOURCE_DOMAIN"].strip(),
            "domain_id": domain_id,
            "pain_class": fields["PAIN_CLASS"].strip(),
            "problem": fields["PROBLEM"].strip(),
            "causal_chain": causal,
            "unexploited_phenomenon": fields["UNEXPLOITED_PHENOMENON"].strip(),
            "intervention": fields["INTERVENTION"].strip(),
            "governing_variables": fields["GOVERNING_VARIABLES"].strip(),
            "predicted_effect": fields["PREDICTED_EFFECT"].strip(),
            "equations": [e.strip() for e in
                          re.split(r"[;\n]", fields["EQUATIONS"])
                          if e.strip()],
            "boundary_conditions": fields["BOUNDARY_CONDITIONS"].strip(),
            "evidence_refs": valid_refs,
            "cross_domain_transition": None if cross.strip().upper() == "NONE"
            else cross.strip(),
            "baseline": {
                "baseline_incumbent": fields["BASELINE_INCUMBENT"].strip(),
                "baseline_metric": fields["BASELINE_METRIC"].strip(),
                "candidate_metric": fields["CANDIDATE_METRIC"].strip(),
                "expected_delta": fields["EXPECTED_DELTA"].strip(),
            },
            "killer_experiment": {
                "experiment": fields["CHEAPEST_DECISIVE_EXPERIMENT"].strip(),
                "decisive_uncertainty": fields["DECISIVE_UNCERTAINTY"].strip(),
                "kill_condition": fields["KILL_CONDITION"].strip(),
                "cost_class": fields["COST_CLASS"].strip().upper(),
            },
            "failure_modes": fms,
            "commercial_path": {
                "buyer": fields["BUYER"].strip(),
                "use_case": fields["USE_CASE"].strip(),
                "integration_point": fields["INTEGRATION_POINT"].strip(),
            },
            "generation": {
                "provider": generation_meta.get("provider"),
                "model": generation_meta.get("model"),
                "prompt_hash": generation_meta.get("prompt_hash"),
                "output_hash": generation_meta.get("output_hash"),
                "purpose": "r411_candidate_extraction",
            },
        }
        candidate["medical_screen"] = medical_exclusion_screen(candidate)
        accepted.append(candidate)
    return {
        "accepted": accepted,
        "rejected": rejected,
        "extraction_version": EXTRACTION_VERSION,
        "no_fabrication_rule": (
            "every evidence_ref validated against the frozen pool; "
            "violations rejected, never repaired (Art. IV/VII)"),
    }
