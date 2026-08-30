"""General-purpose FAILURE-UNIVERSE connectors — CEO directive 2026-08-30 #3.

> "Add the missing general-purpose failure universe … NHTSA/NTSB/NASA/OSTI
> should become the PATTERN, not isolated connectors."

Domains the CEO named and this module's measured coverage:

    aerospace failures        — honest gap (ASRS 404, LLIS SPA-shell,
                                 NTSB HTML, FAA SDR 503 — all measured
                                 2026-08-30; NTRS carries aerospace tech
                                 reports, not incident data)
    automotive failures       — nhtsa_recalls (LIVE, prior cycle) +
                                nhtsa_complaints (NEW, LIVE)
    industrial failures       — fra_rail_accidents (NEW, LIVE — rail
                                equipment accidents Form 54, cause-coded);
                                OSHA route 404 (measured)
    energy failures           — NRC RSS 403 / ADAMS 404 / PHMSA Socrata
                                non-tabular anonymous (all measured) —
                                honest gap; OSTI carries energy R&D reports
    infrastructure failures   — usgs_earthquakes (NEW, LIVE — natural-
                                hazard INPUT for infrastructure-resilience
                                problems, explicitly NOT a failure record)
    electronics failures      — cpsc_recalls (NEW, LIVE — consumer
                                electronics recall class within CPSC)
    chemical/process failures — CSB 404 both routes (measured) — honest gap

Measured live (this session, 2026-08-30):
- NHTSA complaints: https://api.nhtsa.gov/complaints/complaintsByVehicle
  200 JSON {count, message, results[]}; result fields: odiNumber,
  components, crash, fire, numberOfInjuries, numberOfDeaths,
  dateOfIncident, dateComplaintFiled, vin, summary (268 records for
  toyota|camry|2020 at probe time).
- CPSC recalls: https://www.saferproducts.gov/RestWebServices/Recall
  ?format=json 200 JSON list[]; fields RecallID/RecallNumber/RecallDate/
  Hazards[]/Products[]/Injuries[]/Remedies/Description… (141 records for
  a 2.5-month window at probe time).
- USGS earthquakes: https://earthquake.usgs.gov/fdsnws/event/1/query
  200 GeoJSON FeatureCollection; properties.mag/place/time…
- FRA rail accidents: https://data.transportation.gov/resource/
  85tf-25kj.json 200 Socrata rows; cause-coded Form 54 fields.

Epistemic classes (Art. XXI.5 generalized — every class carries caps):
- NHTSA complaint = VOLUNTARY REPORT, unverified, causality unknown —
  the MAUDE-not-ground-truth caps verbatim in spirit.
- CPSC recall = acknowledged product defect (regulatory action), NOT
  incidence.
- USGS event = measured geophysical event (instrument-derived, PRIMARY
  for hazard exposure; NOT an engineering-failure record).
- FRA Form 54 = regulatory accident report with cause classification —
  reported-by-railroad, cause codes are classifications not findings.
"""

from __future__ import annotations

import json
import urllib.parse
from typing import Any, Dict, List, Optional

from discovery_fabric.source_registry.base import (
    ConnectorBase,
    SourceRecord,
    utc_now,
)

# ---------------------------------------------------------------------------
# NHTSA complaints — automotive adverse events (voluntary reports)
# ---------------------------------------------------------------------------

NHTSA_COMPLAINT_LIMITATIONS = [
    "VOLUNTARY_REPORT: owner-complaint subset; unverified narratives, "
    "causality NOT established (Art. XXI.5 caps generalized)",
    "INCIDENCE_UNKNOWN: complaint counts are NOT failure rates; "
    "denominator (vehicles in service) absent from this endpoint",
    "NARRATIVE_BIAS: summaries are complainant-authored; engineering "
    "verification absent",
    "JURISDICTION: US vehicle market only",
]


class NhtsaComplaintConnector(ConnectorBase):
    """NHTSA ODI vehicle-owner complaints — transport adverse events."""

    SOURCE_ID = "nhtsa_complaints"
    ROLES = ("ADVERSE_EVENT",)
    HEALTH_QUERY = "toyota|camry|2020"
    # Declared grammar for the base-class grammar gate (2026-08-31):
    # this endpoint answers VEHICLE-parameterized questions only.
    QUERY_GRAMMAR = "make|model|year (e.g. toyota|camry|2020)"
    LIMIT = 25

    def parse_query(self, query: str) -> Optional[Dict[str, str]]:
        parts = [p.strip() for p in query.split("|")]
        if len(parts) != 3 or not all(parts):
            return None
        make, model, year = parts
        if not (year.isdigit() and 1900 <= int(year) <= 2100):
            return None
        return {"make": make, "model": model, "modelYear": year}

    def build_url(self, query: str) -> str:
        pq = self.parse_query(query) or {}
        return ("https://api.nhtsa.gov/complaints/complaintsByVehicle"
                f"?make={urllib.parse.quote(pq.get('make', ''))}"
                f"&model={urllib.parse.quote(pq.get('model', ''))}"
                f"&modelYear={urllib.parse.quote(pq.get('modelYear', ''))}")

    def parse_payload(self, raw: bytes, query: str) -> Any:
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict) or "results" not in payload:
            raise ValueError("nhtsa complaints payload missing results key")
        return payload

    def definitive_empty(self, http_status, body) -> bool:
        # MEASURED 2026-08-30 (benchmark dry-run): a vehicle with zero
        # complaints answers HTTP 400 with a VALID empty body
        # {"count":0,"message":"Results returned successfully","results":[]}
        # — that is the provider's DEFINITIVE zero (Art. XXI.3), not a
        # failed request. Any other 400 stays SEARCH_FAILED.
        if http_status != 400 or not body:
            return False
        try:
            j = json.loads(body.decode("utf-8", "replace"))
            return (j.get("count") == 0 and j.get("results") == []
                    and "success" in str(j.get("message", "")).lower())
        except Exception:  # noqa: BLE001
            return False

    def normalize_payload(self, payload: Any, query: str, raw_sha: str) -> List[SourceRecord]:
        out: List[SourceRecord] = []
        for r in (payload.get("results") or [])[: self.LIMIT]:
            odi = r.get("odiNumber")
            if odi is None:
                continue
            comps = r.get("components") or ""
            first_comp = comps.split(",")[0].strip() if comps else "component unspecified"
            out.append(SourceRecord(
                source_id=self.SOURCE_ID,
                role="ADVERSE_EVENT",
                record_id=f"nhtsa_odi:{odi}",
                title=f"{r.get('manufacturer', '')} — {first_comp}",
                uri=f"https://odirecords.nhtsa.gov/complaints/{odi}" if odi else "",
                retrieved_at=utc_now(),
                query=query,
                raw_payload_sha256=raw_sha,
                normalized={
                    "odi_number": odi,
                    "manufacturer": r.get("manufacturer"),
                    "components": comps,
                    "crash": r.get("crash"),
                    "fire": r.get("fire"),
                    "number_of_injuries": r.get("numberOfInjuries"),
                    "number_of_deaths": r.get("numberOfDeaths"),
                    "date_of_incident": r.get("dateOfIncident"),
                    "date_complaint_filed": r.get("dateComplaintFiled"),
                    "summary": (r.get("summary") or "")[:4000] or None,
                    "failure_domain": "transport",
                    "report_class": "VOLUNTARY_OWNER_REPORT",
                },
                provenance={
                    "provider": self.SOURCE_ID,
                    "api": "api.nhtsa.gov/complaints/complaintsByVehicle",
                    "query": query,
                    "raw_payload_sha256": raw_sha,
                    "retrieved_at": utc_now(),
                },
                epistemic_state="OBSERVED",
                limitations=list(NHTSA_COMPLAINT_LIMITATIONS),
            ))
        return out

    def extract_total_hits(self, payload: Any) -> Optional[int]:
        c = payload.get("count")
        return c if isinstance(c, int) else None


# ---------------------------------------------------------------------------
# CPSC recalls — consumer products incl. electronics (regulatory actions)
# ---------------------------------------------------------------------------

CPSC_LIMITATIONS = [
    "RECALL_SEMANTICS: a recall is an acknowledged product hazard, NOT an "
    "incidence or injury rate",
    "INJURY_UNDERCOUNT: reported Injuries[] are complaints associated with "
    "the recall, not a census",
    "JURISDICTION: US Consumer Product Safety Commission domain only "
    "(consumer products; not food/drugs/vehicles)",
]


class CpscRecallConnector(ConnectorBase):
    """CPSC SaferProducts recall database — consumer-product failures."""

    SOURCE_ID = "cpsc_recalls"
    ROLES = ("RECALL", "COMMERCIAL")
    HEALTH_QUERY = "2026-06-01"
    # Declared grammar for the base-class grammar gate (2026-08-31):
    # this endpoint offers a date window only — no content search.
    QUERY_GRAMMAR = "YYYY-MM-DD date window (RecallDateStart)"

    def build_url(self, query: str) -> str:
        # query = ISO date (YYYY-MM-DD) — recalls published since that date.
        # free-text search is NOT offered by this endpoint; date-window is
        # the measured query grammar. Malformed dates fail in parse_query.
        q = urllib.parse.quote(query)
        return (f"https://www.saferproducts.gov/RestWebServices/Recall"
                f"?format=json&RecallDateStart={q}")

    def parse_query(self, query: str) -> Optional[str]:
        import re
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", query or ""):
            return query
        return None

    def parse_payload(self, raw: bytes, query: str) -> Any:
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, list):
            raise ValueError("cpsc payload is not a list")
        return payload

    def normalize_payload(self, payload: Any, query: str, raw_sha: str) -> List[SourceRecord]:
        out: List[SourceRecord] = []
        for r in payload[: self.LIMIT] if hasattr(self, "LIMIT") else payload[:50]:
            rn = r.get("RecallNumber") or r.get("RecallID")
            hazards = "; ".join(h.get("Name", "") if isinstance(h, dict) else str(h)
                                for h in (r.get("Hazards") or []))
            products = "; ".join(
                (p.get("Name", "") if isinstance(p, dict) else str(p))
                for p in (r.get("Products") or [])[:4])
            injuries = "; ".join(
                (i.get("Name", "") if isinstance(i, dict) else str(i))
                for i in (r.get("Injuries") or [])[:4])
            out.append(SourceRecord(
                source_id=self.SOURCE_ID,
                role="RECALL",
                record_id=f"cpsc:{rn}",
                title=(r.get("Title") or "")[:200] or f"CPSC recall {rn}",
                uri=r.get("URL") or "",
                retrieved_at=utc_now(),
                query=query,
                raw_payload_sha256=raw_sha,
                normalized={
                    "recall_number": str(rn),
                    "recall_date": r.get("RecallDate"),
                    "hazards": hazards or None,
                    "products": products or None,
                    "injuries": injuries or None,
                    "description": (r.get("Description") or "")[:4000] or None,
                    "manufacturer_countries": ", ".join(
                        m.get("Name", "") if isinstance(m, dict) else str(m)
                        for m in (r.get("ManufacturerCountries") or [])[:4]) or None,
                    "last_publish_date": r.get("LastPublishDate"),
                    "failure_domain": "consumer_products",
                    "report_class": "REGULATORY_RECALL_ACTION",
                },
                provenance={
                    "provider": self.SOURCE_ID,
                    "api": "saferproducts.gov/RestWebServices/Recall",
                    "query": query,
                    "raw_payload_sha256": raw_sha,
                    "retrieved_at": utc_now(),
                },
                epistemic_state="OBSERVED",
                limitations=list(CPSC_LIMITATIONS),
            ))
        return out

    def extract_total_hits(self, payload: Any) -> Optional[int]:
        return len(payload) if isinstance(payload, list) else None


# ---------------------------------------------------------------------------
# USGS earthquakes — infrastructure hazard inputs (measured geophysics)
# ---------------------------------------------------------------------------

USGS_LIMITATIONS = [
    "HAZARD_INPUT_NOT_FAILURE: an earthquake is a measured geophysical "
    "event, NOT an engineering-failure record; structural consequences "
    "require engineering corpora this endpoint does not carry",
    "DETECTION_BIAS: catalog completeness varies with magnitude, region "
    "and network density",
    "MAGNITUDE_UNCERTAINTY: preliminary magnitudes revise",
]


class UsgsEarthquakeConnector(ConnectorBase):
    """USGS FDSN earthquake events — infrastructure hazard exposure."""

    SOURCE_ID = "usgs_earthquakes"
    ROLES = ("HAZARD_EVENT",)
    HEALTH_QUERY = "2026-07-01"
    # Declared grammar for the base-class grammar gate (2026-08-31).
    QUERY_GRAMMAR = "YYYY-MM-DD date window (starttime)"

    def parse_query(self, query: str) -> Optional[str]:
        import re
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", query or ""):
            return query
        return None

    def build_url(self, query: str) -> str:
        q = self.parse_query(query) or ""
        return ("https://earthquake.usgs.gov/fdsnws/event/1/query"
                f"?format=geojson&limit=25&minmagnitude=4.5&starttime={q}")

    def parse_payload(self, raw: bytes, query: str) -> Any:
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict) or "features" not in payload:
            raise ValueError("usgs payload missing features key")
        return payload

    def normalize_payload(self, payload: Any, query: str, raw_sha: str) -> List[SourceRecord]:
        out: List[SourceRecord] = []
        for f in payload.get("features") or []:
            p = f.get("properties", {}) or {}
            g = f.get("geometry", {}) or {}
            eid = f.get("id")
            if not eid:
                continue
            coords = (g.get("coordinates") or [None, None, None])
            out.append(SourceRecord(
                source_id=self.SOURCE_ID,
                role="HAZARD_EVENT",
                record_id=f"usgs:{eid}",
                title=f"M{p.get('mag')} earthquake — {p.get('place') or 'location unspecified'}",
                uri=p.get("url") or f"https://earthquake.usgs.gov/earthquakes/eventpage/{eid}",
                retrieved_at=utc_now(),
                query=query,
                raw_payload_sha256=raw_sha,
                normalized={
                    "event_id": eid,
                    "magnitude": p.get("mag"),
                    "magnitude_type": p.get("magType"),
                    "place": p.get("place"),
                    "event_time_epoch_ms": p.get("time"),
                    "depth_km": coords[2] if len(coords) > 2 else None,
                    "latitude": coords[1] if len(coords) > 1 else None,
                    "longitude": coords[0] if len(coords) > 0 else None,
                    "tsunami_flag": p.get("tsunami"),
                    "felt_reports": p.get("felt"),
                    "alert_level": p.get("alert"),
                    "failure_domain": "infrastructure_hazard",
                    "report_class": "INSTRUMENT_MEASURED_EVENT",
                },
                provenance={
                    "provider": self.SOURCE_ID,
                    "api": "earthquake.usgs.gov/fdsnws/event/1/query",
                    "query": query,
                    "raw_payload_sha256": raw_sha,
                    "retrieved_at": utc_now(),
                },
                epistemic_state="OBSERVED",
                limitations=list(USGS_LIMITATIONS),
            ))
        return out

    def extract_total_hits(self, payload: Any) -> Optional[int]:
        c = (payload.get("metadata") or {}).get("count")
        return c if isinstance(c, int) else None


# ---------------------------------------------------------------------------
# FRA rail equipment accidents — industrial/transport failures, cause-coded
# ---------------------------------------------------------------------------

FRA_LIMITATIONS = [
    "REPORTED_BY_RAILROAD: Form 54 data is carrier-reported under 49 CFR "
    "225; cause codes are classifications of the initial report, not "
    "NTSB-grade findings",
    "REPORTING_THRESHOLD: reportable accidents above FRA cost/injury "
    "thresholds — below-threshold events are absent",
    "CAUSE_CODE_SEMANTICS: accidentcausecode follows FRA cause hierarchy "
    "(track/human/equipment/signal); codes label categories, not proven "
    "root causes",
]


class FraRailAccidentConnector(ConnectorBase):
    """FRA rail equipment accidents (Form 54) via USDOT Socrata."""

    SOURCE_ID = "fra_rail_accidents"
    ROLES = ("INCIDENT",)
    HEALTH_QUERY = "2023-01-01"
    # Declared grammar for the base-class grammar gate (2026-08-31).
    QUERY_GRAMMAR = "YYYY-MM-DD date floor ($where date >= X)"

    def parse_query(self, query: str) -> Optional[str]:
        import re
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", query or ""):
            return query
        return None

    def build_url(self, query: str) -> str:
        q = self.parse_query(query) or ""
        where = urllib.parse.quote(f"date >= '{q}T00:00:00'")
        return ("https://data.transportation.gov/resource/85tf-25kj.json"
                f"?$limit=25&$order=date%20DESC&$where={where}")

    def parse_payload(self, raw: bytes, query: str) -> Any:
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, list):
            raise ValueError("fra payload is not a list")
        return payload

    def normalize_payload(self, payload: Any, query: str, raw_sha: str) -> List[SourceRecord]:
        out: List[SourceRecord] = []
        for r in payload:
            acc = r.get("accidentnumber")
            rr = r.get("reportingrailroadname") or ""
            if not acc:
                continue
            atype = r.get("accidenttype") or "accident type unclassified"
            derailed = sum(int(r.get(k) or 0) for k in (
                "derailedemptyfreightcars", "derailedloadedfreightcars",
                "derailedpassengercars", "derailedemptypassengercars",
                "derailedcabooses"))
            out.append(SourceRecord(
                source_id=self.SOURCE_ID,
                role="INCIDENT",
                record_id=f"fra:{rr.split()[0].lower() if rr else 'rr'}:{acc}",
                title=f"{rr} — {atype} — {r.get('date', '')[:10]}",
                uri=(r.get("url") or {}).get("url", "") if isinstance(r.get("url"), dict) else "",
                retrieved_at=utc_now(),
                query=query,
                raw_payload_sha256=raw_sha,
                normalized={
                    "accident_number": acc,
                    "reporting_railroad": rr,
                    "accident_type": atype,
                    "accident_year": r.get("accidentyear"),
                    "accident_month": r.get("accidentmonth"),
                    "date": r.get("date"),
                    "cause_code": r.get("accidentcausecode"),
                    "cause": r.get("accidentcause"),
                    "state": r.get("state"),
                    "countyname": r.get("countyname"),
                    "derailed_cars_total": derailed or None,
                    "fatalities": r.get("fatalities"),
                    "injured": r.get("injured"),
                    "track_type": r.get("tracktype"),
                    "train_speed": r.get("trainspeed"),
                    "failure_domain": "industrial_transport",
                    "report_class": "REGULATORY_ACCIDENT_REPORT",
                },
                provenance={
                    "provider": self.SOURCE_ID,
                    "api": "data.transportation.gov/resource/85tf-25kj.json",
                    "query": query,
                    "raw_payload_sha256": raw_sha,
                    "retrieved_at": utc_now(),
                },
                epistemic_state="OBSERVED",
                limitations=list(FRA_LIMITATIONS),
            ))
        return out

    def extract_total_hits(self, payload: Any) -> Optional[int]:
        return len(payload) if isinstance(payload, list) else None
