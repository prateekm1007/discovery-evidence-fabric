"""Knowledge-graph entities — the 12 first-class entity types.

CEO database-layer directive: first-class entities for

    DEVICE, DEVICE_FAMILY, PREDICATE, REGULATORY_ACTION, RECALL,
    ADVERSE_EVENT, CLINICAL_TRIAL, PATENT_FAMILY, PATENT_CLAIM,
    MATERIAL, MANUFACTURING_PROCESS, STANDARD

Constitutional anchors:
- Art. VI: entity identity is only what a source record MEASURABLY carries.
  No invented identifiers, no inferred materials, no fabricated families.
- Art. XXV / XXI.6 (entity resolution): devices with different identity
  strengths are DISTINCT nodes with an explicit identity_status. Silent
  merging by name similarity is FORBIDDEN. Resolution happens only on
  EXACT identifier equality (udi_di / k_number / pma_number).
- Art. XXI.9: every entity carries provenance back to the exact source
  record (source_id, record_id, raw_payload_sha256).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

ENTITY_TYPES = [
    "DEVICE",
    "DEVICE_FAMILY",
    "PREDICATE",
    "REGULATORY_ACTION",
    "RECALL",
    "ADVERSE_EVENT",
    "CLINICAL_TRIAL",
    "PATENT_FAMILY",
    "PATENT_CLAIM",
    "MATERIAL",
    "MANUFACTURING_PROCESS",
    "STANDARD",
]

# Identity strength for DEVICE nodes: exact identifiers only.
IDENTITY_STRONG = "RESOLVED"            # udi_di / k_number / pma_number present
IDENTITY_NAME_ONLY = "UNRESOLVED_NAME_ONLY"  # only brand/name text


@dataclass
class Entity:
    entity_type: str
    entity_id: str                      # canonical: "<type>:<namespace>:<identifier>"
    display_name: str
    identifiers: Dict[str, Any]         # measured identifiers this node carries
    identity_status: str = IDENTITY_STRONG
    epistemic_state: str = "OBSERVED"
    provenance: List[Dict[str, Any]] = field(default_factory=list)  # custody refs
    attributes: Dict[str, Any] = field(default_factory=dict)
    limitations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "display_name": self.display_name,
            "identifiers": self.identifiers,
            "identity_status": self.identity_status,
            "epistemic_state": self.epistemic_state,
            "provenance": self.provenance,
            "attributes": self.attributes,
            "limitations": self.limitations,
        }


def _custody(record) -> Dict[str, Any]:
    """Custody reference from a SourceRecord (Art. XXI.9 chain)."""
    return {
        "source_id": record.source_id,
        "record_id": record.record_id,
        "raw_payload_sha256": record.raw_payload_sha256,
        "retrieved_at": record.retrieved_at,
        "query": record.query,
    }


def _regulatory_namespace(number) -> Optional[tuple]:
    """Classify an FDA clearance/approval number by its deterministic prefix.

    FDA numbering convention: K-prefix = 510(k) premarket notification;
    P-prefix (e.g. P980012, P100021) = PMA. This is an exact convention,
    not fuzzy matching. Returns (namespace, number) or None.
    """
    if not number:
        return None
    n = str(number).strip().upper()
    if n.startswith("K"):
        return "510k", n
    if n.startswith("P") and len(n) >= 2 and n[1].isdigit():
        return "pma", n
    return None


def device_entity_from_record(record) -> Optional[Entity]:
    """DEVICE node from a source record, with identity discipline.

    Identity priority (measured fields only):
      udi_di (GUDID) > k_number > pma_number > name-only
    MAUDE's pma_pmn_number carries BOTH K- and P-numbers; the namespace is
    derived from the deterministic FDA prefix (K = 510k, P = pma), so the
    same clearance referenced by MAUDE and by the 510(k) endpoint resolves
    to the SAME device node.
    A record with NO exact identifier still creates a node, but with
    identity_status=UNRESOLVED_NAME_ONLY — never silently merged.
    """
    n = record.normalized
    di = n.get("udi_di") or n.get("di")
    k = n.get("k_number") or (n.get("openfda") or {}).get("k_numbers")
    if isinstance(k, list):
        k = k[0] if k else None
    pma = n.get("pma_number") or (n.get("openfda") or {}).get("pma_numbers")
    if isinstance(pma, list):
        pma = pma[0] if pma else None
    # pma_pmn_number (MAUDE) carries either form; classify by prefix
    pmn = _regulatory_namespace(n.get("pma_pmn_number"))
    if pmn and not k and not pma:
        ns, num = pmn
        if ns == "510k":
            k = num
        else:
            pma = num
    brand = n.get("device_brand_name") or n.get("brand_name") or n.get("device_name") \
        or n.get("proprietary_name") or n.get("trade_name") or n.get("product_description")

    if di:
        return Entity(
            entity_type="DEVICE", entity_id=f"DEVICE:gudid:{di}",
            display_name=brand or di,
            identifiers={"udi_di": di, "k_number": k, "pma_number": pma},
            identity_status=IDENTITY_STRONG,
            provenance=[_custody(record)],
            attributes={"manufacturer": n.get("device_manufacturer") or n.get("company_name")},
        )
    if k:
        return Entity(
            entity_type="DEVICE", entity_id=f"DEVICE:510k:{k}",
            display_name=brand or k,
            identifiers={"k_number": k, "pma_number": pma},
            identity_status=IDENTITY_STRONG,
            provenance=[_custody(record)],
            attributes={"manufacturer": n.get("applicant") or n.get("device_manufacturer")},
        )
    if pma:
        return Entity(
            entity_type="DEVICE", entity_id=f"DEVICE:pma:{pma}",
            display_name=brand or pma,
            identifiers={"pma_number": pma},
            identity_status=IDENTITY_STRONG,
            provenance=[_custody(record)],
            attributes={"manufacturer": n.get("applicant")},
        )
    if brand:
        # name-only identity: distinct node, explicitly unresolved
        return Entity(
            entity_type="DEVICE",
            entity_id=f"DEVICE:name:{_slug(brand)}",
            display_name=brand,
            identifiers={},
            identity_status=IDENTITY_NAME_ONLY,
            provenance=[_custody(record)],
            attributes={"manufacturer": n.get("device_manufacturer") or n.get("company_name")},
            limitations=[
                "Identity by name text only; NO exact identifier in the "
                "source record; NOT merged with identifier-resolved device "
                "nodes (Art. XXI.6)",
            ],
        )
    return None


def adverse_event_entity(record) -> Entity:
    n = record.normalized
    return Entity(
        entity_type="ADVERSE_EVENT",
        entity_id=f"ADVERSE_EVENT:maude:{n.get('mdr_report_key') or n.get('report_number')}",
        display_name=f"MAUDE {n.get('report_number') or n.get('mdr_report_key')}: {n.get('event_type', '')}",
        identifiers={"mdr_report_key": n.get("mdr_report_key"),
                     "report_number": n.get("report_number")},
        provenance=[_custody(record)],
        attributes={
            "event_type": n.get("event_type"),
            "date_received": n.get("date_received"),
            "product_problems": n.get("product_problems"),
            "narrative_present": bool(n.get("narrative_text")),
        },
        limitations=list(record.limitations),
    )


def recall_entity(record) -> Entity:
    n = record.normalized
    rid = n.get("res_event_number") or n.get("cfres_id") or n.get("product_res_number")
    return Entity(
        entity_type="RECALL",
        entity_id=f"RECALL:fda:{rid}",
        display_name=f"Recall {rid} (class {n.get('classification', '?')})",
        identifiers={"res_event_number": n.get("res_event_number"),
                     "cfres_id": n.get("cfres_id"),
                     "product_res_number": n.get("product_res_number")},
        provenance=[_custody(record)],
        attributes={
            "classification": n.get("classification"),
            "reason_for_recall": n.get("reason_for_recall"),
            "recall_status": n.get("recall_status"),
            "event_date_initiated": n.get("event_date_initiated"),
            "root_cause_description": n.get("root_cause_description"),
        },
        limitations=list(record.limitations),
    )


def regulatory_action_entity(record, action_type: str) -> Entity:
    n = record.normalized
    if action_type == "510K_CLEARANCE":
        ident = n.get("k_number")
        eid = f"REGULATORY_ACTION:510k:{ident}"
        extra = {"decision_code": n.get("decision_code"),
                 "clearance_type": n.get("clearance_type")}
    elif action_type == "PMA_APPROVAL":
        ident = n.get("pma_number")
        eid = f"REGULATORY_ACTION:pma:{ident}"
        extra = {"decision_code": n.get("decision_code"),
                 "supplement_reason": n.get("supplement_reason")}
    else:
        raise ValueError(f"unknown action_type {action_type}")
    return Entity(
        entity_type="REGULATORY_ACTION",
        entity_id=eid,
        display_name=f"{action_type} {ident}",
        identifiers={"identifier": ident},
        provenance=[_custody(record)],
        attributes={
            "action_type": action_type,
            "decision_date": n.get("decision_date"),
            "applicant": n.get("applicant"),
            **extra,
        },
        limitations=list(record.limitations),
    )


def clinical_trial_entity(record) -> Entity:
    n = record.normalized
    return Entity(
        entity_type="CLINICAL_TRIAL",
        entity_id=f"CLINICAL_TRIAL:nct:{n.get('nct_id')}",
        display_name=n.get("brief_title") or n.get("nct_id") or "",
        identifiers={"nct_id": n.get("nct_id")},
        provenance=[_custody(record)],
        attributes={
            "overall_status": n.get("overall_status"),
            "study_type": n.get("study_type"),
            "phases": n.get("phases"),
            "conditions": n.get("conditions"),
            "interventions": n.get("interventions"),
            "enrollment_count": n.get("enrollment_count"),
            "lead_sponsor": n.get("lead_sponsor"),
            "why_stopped": n.get("why_stopped"),
        },
        limitations=list(record.limitations),
    )


def patent_family_entity(record) -> Entity:
    n = record.normalized
    pid = n.get("patent_id") or n.get("publication_number") or n.get("patent_number") or ""
    return Entity(
        entity_type="PATENT_FAMILY",
        entity_id=f"PATENT_FAMILY:pub:{_slug(str(pid))}",
        display_name=record.title or str(pid),
        identifiers={"publication_number": pid},
        provenance=[_custody(record)],
        attributes={
            "publication_date": n.get("publication_date"),
            "assignee_or_authors": n.get("assignee_or_authors"),
            "snippet": n.get("snippet"),
        },
        limitations=list(record.limitations),
    )


def _slug(text: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in (text or "").strip())[:120]
