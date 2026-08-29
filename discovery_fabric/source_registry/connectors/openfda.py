"""openFDA connectors — the device-reality evidence family.

MAUDE / recalls / 510(k) / PMA / UDI (GUDID) / registration & listing /
product classification. No API key required (240 req/min tier).

Field names below were MEASURED against live API responses (probe run,
this session). Where a field does not exist in the source (e.g. 510(k)
records carry NO structured predicate field), the normalizer does NOT
invent it (Art. VI) — predicate linkage is carried only through fields
that measurably exist: MAUDE `pma_pmn_number`, recall `k_numbers`,
openfda nested `k_numbers`.

Constitutional anchors:
- Art. XXI.5: every MAUDE-derived record carries FDA's own limitations as
  STRUCTURED metadata: report counts are not incidence, causality is not
  established, duplicates/inaccuracies exist. No MAUDE record may be used
  as an incidence estimate.
- Art. XXI.3: provider failure is not absence — statuses flow through the
  base class discipline; openFDA's 404+NOT_FOUND JSON is the provider
  DEFINITIVELY answering 'zero records' (EMPTY), not a failure.
"""

from __future__ import annotations

import json
import urllib.parse
from typing import Any, Dict, List

from discovery_fabric.source_registry.base import (
    ConnectorBase,
    SourceRecord,
    utc_now,
)

BASE = "https://api.fda.gov"

# FDA's own warnings about MAUDE data, attached verbatim to every record.
MAUDE_LIMITATIONS = [
    "REPORT_COUNT_SEMANTICS: counts are raw report counts, NOT incidence or event rates",
    "CAUSALITY_UNVERIFIED: FDA has not verified that the device caused the event",
    "DUPLICATES_POSSIBLE: reports may be duplicate, incomplete, or inaccurate",
    "REPORTING_BIAS: mandatory (manufacturer) and voluntary reporting mix; "
    "absence of reports does NOT mean absence of failures",
]


def _limit_str(limit: int) -> str:
    return str(max(1, min(limit, 100)))


def _openfda_nested(r: Dict[str, Any]) -> Dict[str, Any]:
    """Extract the openfda enrichment block (k_numbers, product_codes...)."""
    of = r.get("openfda") or {}
    return {
        "k_numbers": of.get("k_numbers"),
        "pma_numbers": of.get("pma_numbers"),
        "product_codes": of.get("product_codes"),
        "device_name": of.get("device_name"),
        "regulation_number": of.get("regulation_number"),
    }


class _OpenFdaBase(ConnectorBase):
    ENDPOINT = ""       # e.g. "device/event.json"
    RESULT_KEY = "results"
    LIMIT = 10

    def definitive_empty(self, http_status, body) -> bool:
        """openFDA signals zero matching records as HTTP 404 with a JSON
        body {'error': {'code': 'NOT_FOUND', 'message': 'No matches found!'}}.
        That is the provider DEFINITIVELY answering 'zero records' — the
        Art. XXI.3 EMPTY case, not a provider failure."""
        if http_status != 404 or not body:
            return False
        try:
            err = json.loads(body.decode("utf-8")).get("error") or {}
            return err.get("code") == "NOT_FOUND"
        except Exception:  # noqa: BLE001
            return False

    def build_url(self, query: str) -> str:
        q = urllib.parse.quote(query)
        return (
            f"{BASE}/{self.ENDPOINT}?search={q}&limit={_limit_str(self.LIMIT)}"
        )

    def parse_payload(self, raw: bytes, query: str) -> Any:
        return json.loads(raw.decode("utf-8"))

    def normalize_payload(self, payload: Any, query: str, raw_sha: str) -> List[SourceRecord]:
        if not isinstance(payload, dict):
            raise ValueError("openFDA payload is not an object")
        results = payload.get(self.RESULT_KEY)
        if not isinstance(results, list):
            raise ValueError(f"openFDA payload missing '{self.RESULT_KEY}' list")
        return [self.to_record(r, query, raw_sha) for r in results]

    def to_record(self, r: Dict[str, Any], query: str, raw_sha: str) -> SourceRecord:
        raise NotImplementedError

    def _prov(self, query: str, raw_sha: str) -> Dict[str, Any]:
        return {
            "provider": self.SOURCE_ID,
            "api": BASE,
            "endpoint": self.ENDPOINT,
            "query": query,
            "raw_payload_sha256": raw_sha,
            "retrieved_at": utc_now(),
        }


class MaudeConnector(_OpenFdaBase):
    SOURCE_ID = "fda_maude"
    ROLES = ("ADVERSE_EVENT",)
    ENDPOINT = "device/event.json"
    # nested field syntax is REQUIRED (measured: flat device_name -> NOT_FOUND,
    # device.brand_name:pacemaker -> 34,389 reports)
    HEALTH_QUERY = "device.brand_name:pacemaker"
    LIMIT = 100

    def to_record(self, r: Dict[str, Any], query: str, raw_sha: str) -> SourceRecord:
        mdr = r.get("mdr_report_key") or r.get("report_number") or ""
        device_list = r.get("device") or []
        dev = device_list[0] if device_list else {}
        event_type = r.get("event_type") or ""
        mdr_text = r.get("mdr_text") or []
        narrative = " ".join(
            (t.get("text") or "") for t in mdr_text if isinstance(t, dict)
        )
        return SourceRecord(
            source_id=self.SOURCE_ID,
            role="ADVERSE_EVENT",
            record_id=f"maude:{mdr}",
            title=f"MAUDE report {mdr}: {event_type or 'unspecified event'} "
                  f"[{(dev.get('brand_name') or '')[:60]}]",
            uri=(f"https://api.fda.gov/device/event.json?search=mdr_report_key:{mdr}"
                 if mdr else BASE + "/device/event.json"),
            retrieved_at=utc_now(),
            query=query,
            raw_payload_sha256=raw_sha,
            normalized={
                "mdr_report_key": r.get("mdr_report_key"),
                "report_number": r.get("report_number"),
                "event_type": event_type,
                "report_source_code": r.get("report_source_code"),
                "source_type": r.get("source_type"),
                "type_of_report": r.get("type_of_report"),
                "date_received": r.get("date_received"),
                "date_of_event": r.get("date_of_event"),
                "number_devices_in_event": r.get("number_devices_in_event"),
                "device_brand_name": dev.get("brand_name"),
                "device_generic_name": dev.get("generic_name"),
                "device_manufacturer": dev.get("manufacturer_d_name") or r.get("manufacturer_name"),
                "device_model_number": dev.get("model_number"),
                "device_catalog_number": dev.get("catalog_number"),
                "device_report_product_code": dev.get("device_report_product_code"),
                "udi_di": dev.get("udi_di"),
                "implant_flag": dev.get("implant_flag"),
                "device_age_text": dev.get("device_age_text"),
                "device_operator": dev.get("device_operator"),
                "product_problems": r.get("product_problems") or [],
                "pma_pmn_number": r.get("pma_pmn_number"),  # K/PMA linkage (measured field)
                "remedial_action": r.get("remedial_action") or [],
                "adverse_event_flag": r.get("adverse_event_flag"),
                "patient_problems": [
                    (p or {}).get("patient_problems") for p in (r.get("patient") or []) if isinstance(p, dict)
                ],
                "narrative_text": narrative[:4000] if narrative else None,
                "openfda": _openfda_nested(dev),
            },
            provenance=self._prov(query, raw_sha),
            epistemic_state="OBSERVED",
            limitations=list(MAUDE_LIMITATIONS),
        )


class FdaRecallConnector(_OpenFdaBase):
    SOURCE_ID = "fda_recall"
    ROLES = ("RECALL",)
    ENDPOINT = "device/recall.json"
    HEALTH_QUERY = "reason_for_recall:catheter"
    LIMIT = 25

    def to_record(self, r: Dict[str, Any], query: str, raw_sha: str) -> SourceRecord:
        rid = (r.get("res_event_number") or r.get("cfres_id")
               or r.get("product_res_number") or "")
        classification = r.get("classification") or ""
        reason = r.get("reason_for_recall") or ""
        return SourceRecord(
            source_id=self.SOURCE_ID,
            role="RECALL",
            record_id=f"recall:{rid}",
            title=f"Recall {rid} (class {classification or '?'}): {reason[:120]}",
            uri=(f"https://api.fda.gov/device/recall.json?search=res_event_number:{rid}"
                 if rid else BASE + "/device/recall.json"),
            retrieved_at=utc_now(),
            query=query,
            raw_payload_sha256=raw_sha,
            normalized={
                "res_event_number": r.get("res_event_number"),
                "cfres_id": r.get("cfres_id"),
                "product_res_number": r.get("product_res_number"),
                "recall_status": r.get("recall_status"),
                "classification": classification,
                "product_description": r.get("product_description"),
                "code_info": r.get("code_info"),
                "reason_for_recall": reason,
                "recalling_firm": r.get("recalling_firm"),
                "root_cause_description": r.get("root_cause_description"),
                "distribution_pattern": r.get("distribution_pattern"),
                "event_date_initiated": r.get("event_date_initiated"),
                "event_date_posted": r.get("event_date_posted"),
                "event_date_terminated": r.get("event_date_terminated"),
                "product_quantity": r.get("product_quantity"),
                "action": r.get("action"),
                "k_numbers": r.get("k_numbers") or [],  # measured linkage field
                "product_code": r.get("product_code"),
            },
            provenance=self._prov(query, raw_sha),
            epistemic_state="OBSERVED",
            limitations=[
                "Enforcement-report view; firm notification timing differs",
                "Root-cause text is self-reported free-form",
            ],
        )


class Fda510kConnector(_OpenFdaBase):
    SOURCE_ID = "fda_510k"
    ROLES = ("REGULATORY",)
    ENDPOINT = "device/510k.json"
    HEALTH_QUERY = 'device_name:"pacemaker"'
    LIMIT = 25

    def to_record(self, r: Dict[str, Any], query: str, raw_sha: str) -> SourceRecord:
        k = r.get("k_number") or ""
        return SourceRecord(
            source_id=self.SOURCE_ID,
            role="REGULATORY",
            record_id=f"510k:{k}",
            title=f"510(k) {k}: {r.get('device_name', '')}",
            uri=f"https://api.fda.gov/device/510k.json?search=k_number:{k}",
            retrieved_at=utc_now(),
            query=query,
            raw_payload_sha256=raw_sha,
            normalized={
                "k_number": k,
                "device_name": r.get("device_name"),
                "applicant": r.get("applicant"),
                "date_received": r.get("date_received"),
                "decision_date": r.get("decision_date"),
                "decision_code": r.get("decision_code"),
                "decision_description": r.get("decision_description"),
                "clearance_type": r.get("clearance_type"),
                "expedited_review_flag": r.get("expedited_review_flag"),
                "product_code": r.get("product_code"),
                "advisory_committee": r.get("advisory_committee"),
                "review_advisory_committee": r.get("review_advisory_committee"),
                "statement_or_summary": r.get("statement_or_summary"),
                # NOTE (measured): this endpoint carries NO structured
                # predicate field. Predicate chains must be built from
                # decision_description text mining or MAUDE pma_pmn_number —
                # never fabricated here (Art. VI).
            },
            provenance=self._prov(query, raw_sha),
            epistemic_state="OBSERVED",
            limitations=[
                "No structured predicate field in this endpoint; predicate "
                "linkage requires separate evidence",
            ],
        )


class FdaPmaConnector(_OpenFdaBase):
    SOURCE_ID = "fda_pma"
    ROLES = ("REGULATORY",)
    ENDPOINT = "device/pma.json"
    HEALTH_QUERY = "applicant:medtronic"
    LIMIT = 25

    def to_record(self, r: Dict[str, Any], query: str, raw_sha: str) -> SourceRecord:
        pma = r.get("pma_number") or ""
        return SourceRecord(
            source_id=self.SOURCE_ID,
            role="REGULATORY",
            record_id=f"pma:{pma}",
            title=f"PMA {pma}: {r.get('trade_name', '')}",
            uri=f"https://api.fda.gov/device/pma.json?search=pma_number:{pma}",
            retrieved_at=utc_now(),
            query=query,
            raw_payload_sha256=raw_sha,
            normalized={
                "pma_number": pma,
                "supplement_number": r.get("supplement_number"),
                "supplement_reason": r.get("supplement_reason"),
                "trade_name": r.get("trade_name"),
                "generic_name": r.get("generic_name"),
                "applicant": r.get("applicant"),
                "date_received": r.get("date_received"),
                "decision_date": r.get("decision_date"),
                "decision_code": r.get("decision_code"),
                "advisory_committee": r.get("advisory_committee"),
                "product_code": r.get("product_code"),
                "openfda": _openfda_nested(r),
            },
            provenance=self._prov(query, raw_sha),
            epistemic_state="OBSERVED",
            limitations=[],
        )


class FdaUdiConnector(_OpenFdaBase):
    SOURCE_ID = "fda_udi"
    ROLES = ("DEVICE_IDENTITY",)
    ENDPOINT = "device/udi.json"
    HEALTH_QUERY = 'brand_name:"pacemaker"'
    LIMIT = 25

    def to_record(self, r: Dict[str, Any], query: str, raw_sha: str) -> SourceRecord:
        # measured structure: FLAT record (no nested 'device' object)
        key = r.get("public_device_record_key") or ""
        identifiers = r.get("identifiers") or []
        di = next(
            (i.get("id") for i in identifiers
             if isinstance(i, dict) and i.get("type") == "Direct Marking UDID"),
            None,
        ) or (identifiers[0].get("id") if identifiers and isinstance(identifiers[0], dict) else None) or key
        gmdn = [
            (g or {}).get("gmdn_pt_name")
            for g in (r.get("gmdn_terms") or []) if isinstance(g, dict)
        ]
        return SourceRecord(
            source_id=self.SOURCE_ID,
            role="DEVICE_IDENTITY",
            record_id=f"gudid:{key or di}",
            title=f"GUDID {di or key}: {r.get('brand_name', '')}",
            uri=(f"https://api.fda.gov/device/udi.json?search=public_device_record_key:{key}"
                 if key else BASE + "/device/udi.json"),
            retrieved_at=utc_now(),
            query=query,
            raw_payload_sha256=raw_sha,
            normalized={
                "public_device_record_key": key,
                "di": di,
                "identifiers": identifiers,
                "brand_name": r.get("brand_name"),
                "company_name": r.get("company_name"),
                "version_or_model_number": r.get("version_or_model_number"),
                "catalog_number": r.get("catalog_number"),
                "device_description": r.get("device_description"),
                "product_codes": r.get("product_codes"),
                "gmdn_pt_names": gmdn,
                "mri_safety": r.get("mri_safety"),
                "commercial_distribution_status": r.get("commercial_distribution_status"),
                "is_single_use": r.get("is_single_use"),
                "is_rx": r.get("is_rx"),
                "is_otc": r.get("is_otc"),
                "is_combination_product": r.get("is_combination_product"),
                "publish_date": r.get("publish_date"),
                "public_version_status": r.get("public_version_status"),
            },
            provenance=self._prov(query, raw_sha),
            epistemic_state="OBSERVED",
            limitations=[
                "Fields are manufacturer-declared and not independently "
                "verified by FDA",
            ],
        )


class FdaRegListConnector(_OpenFdaBase):
    SOURCE_ID = "fda_registrationlisting"
    ROLES = ("REGULATORY",)
    ENDPOINT = "device/registrationlisting.json"
    # measured field: registration.name (flat establishment_name -> NOT_FOUND)
    HEALTH_QUERY = "registration.name:medtronic"
    LIMIT = 5

    def to_record(self, r: Dict[str, Any], query: str, raw_sha: str) -> SourceRecord:
        reg = r.get("registration") or {}
        products = r.get("products") or []
        prod0 = products[0] if products and isinstance(products[0], dict) else {}
        rid = reg.get("registration_number") or ""
        return SourceRecord(
            source_id=self.SOURCE_ID,
            role="REGULATORY",
            record_id=f"reglist:{rid}",
            title=f"Registration {rid}: {reg.get('name', '')}",
            uri=(f"https://api.fda.gov/device/registrationlisting.json?search=registration.registration_number:{rid}"
                 if rid else BASE + "/device/registrationlisting.json"),
            retrieved_at=utc_now(),
            query=query,
            raw_payload_sha256=raw_sha,
            normalized={
                "registration_number": rid,
                "fei_number": reg.get("fei_number"),
                "establishment_name": reg.get("name"),
                "establishment_type": r.get("establishment_type"),
                "iso_country_code": reg.get("iso_country_code"),
                "owner_operator": reg.get("owner_operator"),
                "reg_status_code": reg.get("status_code"),
                "k_number": r.get("k_number"),
                "pma_number": r.get("pma_number"),
                "proprietary_name": r.get("proprietary_name"),
                "product_codes": prod0.get("product_codes") or prod0.get("product_code"),
                "products_count": len(products),
            },
            provenance=self._prov(query, raw_sha),
            epistemic_state="OBSERVED",
            limitations=["Self-reported listing structure varies across years"],
        )


class FdaClassificationConnector(_OpenFdaBase):
    SOURCE_ID = "fda_classification"
    ROLES = ("REGULATORY",)
    ENDPOINT = "device/classification.json"
    HEALTH_QUERY = 'device_name:"pacemaker"'
    LIMIT = 25

    def to_record(self, r: Dict[str, Any], query: str, raw_sha: str) -> SourceRecord:
        pc = r.get("product_code") or ""
        return SourceRecord(
            source_id=self.SOURCE_ID,
            role="REGULATORY",
            record_id=f"classification:{pc}",
            title=f"Class {r.get('device_class', '?')} {pc}: {r.get('device_name', '')}",
            uri=f"https://api.fda.gov/device/classification.json?search=product_code:{pc}",
            retrieved_at=utc_now(),
            query=query,
            raw_payload_sha256=raw_sha,
            normalized={
                "product_code": pc,
                "device_name": r.get("device_name"),
                "device_class": r.get("device_class"),
                "regulation_number": r.get("regulation_number"),
                "review_panel": r.get("review_panel"),
                "medical_specialty": r.get("medical_specialty"),
                "definition": r.get("definition"),
                "submission_type": r.get("submission_type"),
                "openfda": _openfda_nested(r),
            },
            provenance=self._prov(query, raw_sha),
            epistemic_state="OBSERVED",
            limitations=[],
        )
