"""
commercial.py — R371 Phases 3 + 8: commercial evidence layer with strict
provenance discipline.

CEO directive (2026-08-29 audit response):
  "every claim must be SOURCE_BACKED or NOT_ESTABLISHED.
   Never fill gaps with guessed market numbers."
  "Reject unsupported market-size insertion."
  "Reject generic 'named competitor' insertion without source verification."

Implementation rules (mechanical, no judgment calls at render time):
  MARKET_EVIDENCE — no market-research source is integrated in the engine
    (the COMMERCIAL source role is GUDID device listing, which is a device
    registry, not a market-sizing source). Therefore every market metric is
    NOT_ESTABLISHED with the full required field schema and an explicit
    establishment pathway. Zero numeric market values are emitted.
  COMPETITOR_EVIDENCE — built ONLY from the package's own external
    engineering-precedent entries whose hashed snippets name a company or
    commercial product. Each entry carries the source, url, hash and the
    verbatim snippet span. If no precedent names a company: NOT_ESTABLISHED.
  COMMERCIAL_PRECEDENT — regulatory/commercial pathway precedents found in
    the package's external precedent entries (FDA classification records,
    predicate devices, standards applicability). Source-backed only.
  BUYER_PROFILE — capability-based (derived from engineering disciplines +
    transfer boundary), never company-named.
  IP_STATUS — internal-record facts only: no patent applications filed by
    the transferor (verifiable from engine records); FTO NOT_ESTABLISHED;
    novelty determination NOT_ESTABLISHED (a patent search is not a novelty
    determination — Constitution Art. XXVIII).
"""

import re

# Company/product tokens searched in hashed precedent snippets ONLY.
COMPANY_PATTERN = re.compile(
    r"\b("
    r"Medtronic|Integra(?:\s+LifeSciences)?|Miethke|Sophysa|Codman|"
    r"Christoph Miethke|Johnson\s*&\s*Johnson|B\.?\s?Braun|"
    r"Raumedic|DePuy|Teleflex|Argon\s+Medical"
    r")\b"
)
# Regulatory pathway precedent pattern in precedent titles/snippets
PRECEDENT_PATTERN = re.compile(
    r"(classification|510\(k\)|PMA|product code|predicate|Class I+I?|"
    r"regulatory|FDA recognized standard|ISO\s?\d+|ASTM\s?\w?\d+)",
    re.IGNORECASE,
)

NOT_ESTABLISHED = "NOT_ESTABLISHED"


def _market_metric(metric: str, definition: str) -> dict:
    """A market metric with the CEO-mandated 11-field schema, honestly empty."""
    return {
        "metric": metric,
        "value": NOT_ESTABLISHED,
        "currency": None,
        "geography": None,
        "year": None,
        "source": None,
        "source_url": None,
        "source_hash": None,
        "methodology": None,
        "confidence": None,
        "limitations": (
            "No market-research source is integrated in the engine's evidence "
            "layer (the COMMERCIAL source role provides GUDID device-listing "
            "records, which do not size markets). Inserting an unsourced "
            "figure would violate the provenance discipline (Constitution "
            "Art. I, VI, XXVII)."
        ),
        "definition": definition,
        "establishment_pathway": (
            "A defensible open market-research source (publication or "
            "registry-derived sizing with stated population, geography, year "
            "and methodology) must be captured into the engine's commercial "
            "evidence layer with source hash before this metric can be stated."
        ),
    }


def build_commercial_evidence(pkg) -> dict:
    """Build COMMERCIAL_EVIDENCE.json content for one canonical package."""
    # ---- MARKET_EVIDENCE -------------------------------------------------
    market = {
        "section": "MARKET_EVIDENCE",
        "discipline": (
            "Every market metric is either SOURCE_BACKED (with source, hash "
            "and methodology) or NOT_ESTABLISHED. No guessed figures."
        ),
        "metrics": [
            _market_metric(
                "TOTAL_ADDRESSABLE_MARKET",
                "Aggregate annual value of purchases in the addressable "
                "device category.",
            ),
            _market_metric(
                "SERVICEABLE_OBTAINABLE_MARKET",
                "Annual value obtainable by the licensee within the served "
                "segment and geography.",
            ),
            _market_metric(
                "REVISION_COST_BURDEN",
                "Average cost per revision procedure relevant to the "
                "problem this package addresses.",
            ),
        ],
        "verdict": f"MARKET_SIZE = {NOT_ESTABLISHED}",
    }

    # ---- COMPETITOR_EVIDENCE ----------------------------------------------
    competitor_entries = []
    for i, ext in enumerate(pkg.external_precedent, start=1):
        snippet = ext.get("source_snippet", "") or ""
        title = ext.get("source_title", "") or ""
        hay = f"{title} {snippet}"
        companies = sorted(set(m.group(1) for m in COMPANY_PATTERN.finditer(hay)))
        if companies:
            competitor_entries.append(
                {
                    "entry_id": f"CE-{i:03d}",
                    "kind": "SOURCE_BACKED_PRECEDENT_MENTION",
                    "companies_named_in_source": companies,
                    "context": (
                        "Company name(s) appear inside a hashed external "
                        "precedent captured by the engine. This is a citation "
                        "of the source, not a competitive claim authored by "
                        "the transferor."
                    ),
                    "source": ext.get("source", ""),
                    "source_title": title,
                    "source_hash": ext.get("source_hash", ""),
                    "snippet_span": snippet[:400],
                }
            )
    competitor = {
        "section": "COMPETITOR_EVIDENCE",
        "discipline": (
            "Named-competitor statements are emitted only when the name "
            "occurs inside a captured, hashed external source. No transferor-"
            "authored competitive comparisons."
        ),
        "entries": competitor_entries,
        "verdict": (
            f"{len(competitor_entries)} source-backed precedent mention(s)"
            if competitor_entries
            else f"COMPETITIVE LANDSCAPE = {NOT_ESTABLISHED}"
        ),
    }

    # ---- COMMERCIAL_PRECEDENT ---------------------------------------------
    precedent_entries = []
    for i, ext in enumerate(pkg.external_precedent, start=1):
        title = ext.get("source_title", "") or ""
        snippet = ext.get("source_snippet", "") or ""
        hay = f"{title} {snippet}"
        if PRECEDENT_PATTERN.search(hay):
            precedent_entries.append(
                {
                    "entry_id": f"CP-{i:03d}",
                    "kind": "REGULATORY_OR_COMMERCIAL_PATHWAY_PRECEDENT",
                    "source": ext.get("source", ""),
                    "source_title": title,
                    "source_hash": ext.get("source_hash", ""),
                    "note": snippet[:300],
                }
            )
    precedent = {
        "section": "COMMERCIAL_PRECEDENT",
        "entries": precedent_entries,
        "verdict": (
            f"{len(precedent_entries)} source-backed pathway precedent(s)"
            if precedent_entries
            else NOT_ESTABLISHED
        ),
    }

    # ---- BUYER_PROFILE (capability-based, never company-named) ------------
    disciplines = pkg.eng.get("engineering_disciplines", [])
    buyer_profile = {
        "section": "BUYER_PROFILE",
        "discipline": (
            "Capability-based. Company names are deliberately absent from "
            "the buyer profile: no source-backed basis exists for naming a "
            "specific target company (CEO audit directive). Source-named "
            "companies appear only under COMPETITOR_EVIDENCE."
        ),
        "required_capabilities": _required_capabilities(pkg),
        "engineering_disciplines_involved": disciplines,
    }

    # ---- IP_STATUS ---------------------------------------------------------
    ip_status = {
        "section": "IP_STATUS",
        "patent_applications_filed_by_transferor": "NONE (internal record)",
        "patent_basis": (
            "Engine repository records contain no patent application "
            "filings. This is an internal state fact, not a legal opinion."
        ),
        "freedom_to_operate": NOT_ESTABLISHED,
        "fto_basis": "No freedom-to-operate search has been performed.",
        "novelty_determination": NOT_ESTABLISHED,
        "novelty_basis": (
            "Prior-art search results are included in the evidence summary, "
            "but a patent search result is not a novelty determination "
            "(Constitution Art. XXVIII). Exhaustive classification search "
            "by patent counsel is required."
        ),
    }

    return {
        "package_id": pkg.pkg_id,
        "portfolio_number": pkg.num,
        "commercial_evidence": [
            market,
            competitor,
            precedent,
            buyer_profile,
            ip_status,
        ],
    }


def _required_capabilities(pkg) -> list:
    """Derive buyer capability requirements from transfer_boundary +
    build-plan equipment. Labels come from canonical engineering data only."""
    caps = []
    tb = pkg.transfer_boundary
    if isinstance(tb, dict):
        for item in tb.get("buyer_must_develop", []) or []:
            if item:
                caps.append(str(item))
    # equipment classes from build plan (dedup, canonical text)
    equip_classes = []
    for step in pkg.build_plan:
        eq = (step.get("equipment") or "").strip()
        if eq and eq not in equip_classes:
            equip_classes.append(eq)
    if equip_classes:
        caps.append(
            "Access to bench/test infrastructure: "
            + "; ".join(equip_classes[:3])
        )
    return caps[:8]


def count_unsourced_claims(evidence: dict) -> int:
    """Acceptance helper: count numeric market values (must be 0)."""
    n = 0
    for section in evidence["commercial_evidence"]:
        for metric in section.get("metrics", []) or []:
            v = metric.get("value")
            if v is not None and v != NOT_ESTABLISHED and not isinstance(v, str):
                n += 1
            if isinstance(v, str) and v != NOT_ESTABLISHED and re.search(r"\d", v):
                n += 1
    return n
