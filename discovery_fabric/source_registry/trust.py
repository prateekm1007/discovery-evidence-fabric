"""SOURCE-ROLE TRUST WEIGHTING — CEO directive 2026-08-30 #5.

> "Do not trust sources equally."

Five tiers (CEO-specified vocabulary):

    PRIMARY_REGULATORY   4  a regulator's OWN actions/records (clearances,
                            recalls, registrations, recognized standards)
    PRIMARY_MEASURED    4   instrument-measured property/event data
                            (NIST WebBook, USGS seismic, materials DBs)
    PEER_REVIEWED       3   peer-reviewed literature
    SECONDARY           2   self-reported/aggregate/repackaged signal
                            (MAUDE, NHTSA complaints, preprints, patent
                            aggregators)
    MACHINE_INFERRED    1   engine-generated content (LLM synthesis,
                            derived annotations)

Constitutional anchors:
- Art. XXI.5: MAUDE-class signal sources carry structural caps; FDA
  itself warns reports may be incomplete/inaccurate/unverified — such a
  source can NEVER be treated as unquestioned ground truth, no matter
  that FDA hosts it. Hosting is not authorship.
- Art. III: weighting ORDERS evidence for a reader; it never adjudicates
  contradictions (both sides stay visible) and never HIDES lower-tier
  evidence.
- Art. XXV: an unmapped source raises (never silently defaults).
- Art. XXVII: tier assignment is DECLARED with per-source rationale;
  numeric weights are ENGINEERING-class, disclosed, and used ONLY for
  ordering/aggregation — never as a truth probability.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

TRUST_TIERS: Dict[str, int] = {
    "PRIMARY_REGULATORY": 4,
    "PRIMARY_MEASURED": 4,
    "PEER_REVIEWED": 3,
    "SECONDARY": 2,
    "MACHINE_INFERRED": 1,
}

TIER_DEFINITIONS = {
    "PRIMARY_REGULATORY": (
        "A regulator's own actions and records: clearances, approvals, "
        "recall actions, registrations, recognized-standard lists. The "
        "record IS the regulatory fact. Note: a voluntary-report "
        "DATABASE hosted by a regulator is NOT regulatory action — "
        "see SECONDARY."
    ),
    "PRIMARY_MEASURED": (
        "Instrument-measured property or event data: thermophysical "
        "constants, crystal structures, seismic events. The record is a "
        "measurement with its own uncertainty, not an assertion."
    ),
    "PEER_REVIEWED": (
        "Peer-reviewed literature. Editorial review is a filter, not "
        "proof; retracted/erratum literature is not distinguished at "
        "this layer."
    ),
    "SECONDARY": (
        "Self-reported, pre-review, or repackaged signal: adverse-event "
        "complaints (MAUDE, NHTSA ODI), preprints, patent aggregators' "
        "views of primary offices. Usable as SIGNAL under explicit "
        "caps; never as ground truth (Art. XXI.5 generalized)."
    ),
    "MACHINE_INFERRED": (
        "Engine-generated content: LLM synthesis, derived annotations, "
        "inference-from-absence classes. Untrusted component "
        "(Art. XVIII); admissible as proposal, never as evidence."
    ),
}

# Per-source tier assignment (DECLARED, with rationale). A regulatory
# HOST is not sufficient for PRIMARY_REGULATORY — what matters is
# whether the record IS a regulatory ACTION (recall=yes, complaint=no).
SOURCE_TRUST: Dict[str, Tuple[str, str]] = {
    # --- REGULATORY actions / registries (issuer's own records) ---
    "fda_510k": ("PRIMARY_REGULATORY", "FDA clearance record — the agency's own action"),
    "fda_pma": ("PRIMARY_REGULATORY", "FDA PMA approval record — the agency's own action"),
    "fda_pma_supplements": ("PRIMARY_REGULATORY", "FDA PMA supplement actions"),
    "fda_denovo": ("PRIMARY_REGULATORY", "FDA De Novo decision record"),
    "fda_classification": ("PRIMARY_REGULATORY", "FDA device classification record"),
    "fda_registrationlisting": ("PRIMARY_REGULATORY", "FDA establishment registration record"),
    "fda_udi": ("PRIMARY_REGULATORY", "FDA GUDID device identifier record"),
    "fda_recall": ("PRIMARY_REGULATORY", "FDA recall action — enforcement record"),
    "fda_recognized_standards": ("PRIMARY_REGULATORY", "FDA's own recognition list"),
    "ecfr_title21": ("PRIMARY_REGULATORY", "codified US regulation text (eCFR)"),
    "eudamed": ("PRIMARY_REGULATORY", "EU MDR database (blocked; issuer records)"),
    "gudid_commercial": ("PRIMARY_REGULATORY", "GUDID commercial lens on issuer registry"),
    "gudid_sterilization": ("PRIMARY_REGULATORY", "GUDID registry view"),
    "nhtsa_recalls": ("PRIMARY_REGULATORY", "NHTSA recall campaign — acknowledged-defect action"),
    "cpsc_recalls": ("PRIMARY_REGULATORY", "CPSC recall action — enforcement record"),
    "fra_rail_accidents": ("PRIMARY_REGULATORY", "FRA Form 54 regulatory accident report (carrier-reported under 49 CFR 225; cause codes are classifications — caps carried separately)"),
    # --- MEASURED data ---
    "nist_webbook": ("PRIMARY_MEASURED", "NIST-measured thermophysical properties"),
    "cod_optimade": ("PRIMARY_MEASURED", "curated crystallography measurements (COD)"),
    "materials_project": ("PRIMARY_MEASURED", "DFT-computed materials data — computed, not instrument-measured; carries provider's method caveats"),
    "usgs_earthquakes": ("PRIMARY_MEASURED", "seismic network instrument measurements"),
    "pubchem": ("PRIMARY_MEASURED", "chemical identifiers + measured/computed properties (computed flags carried per property)"),
    # --- PEER-REVIEWED ---
    "pubmed": ("PEER_REVIEWED", "MEDLINE-indexed literature (mostly peer-reviewed journals)"),
    "europepmc": ("PEER_REVIEWED", "life-science literature index incl. preprints (per-record flags carried where present)"),
    "openalex": ("PEER_REVIEWED", "open scholarly index — aggregator of publisher metadata; per-record peer-review status mixed"),
    "semantic_scholar": ("PEER_REVIEWED", "scholarly index — aggregator metadata"),
    "crossref": ("PEER_REVIEWED", "publisher-deposited metadata (DOI registration agency)"),
    "elsevier_scopus": ("PEER_REVIEWED", "curated scholarly index"),
    "lens_scholarly": ("PEER_REVIEWED", "scholarly index (aggregator view)"),
    # --- SECONDARY ---
    "fda_maude": ("SECONDARY", "voluntary adverse-event reports; FDA explicitly warns: incomplete, inaccurate, unverified; NOT incidence, NOT causation (Art. XXI.5)"),
    "nhtsa_complaints": ("SECONDARY", "voluntary owner complaints; unverified narratives; NOT incidence"),
    "arxiv": ("SECONDARY", "preprints — not peer-reviewed"),
    "clinicaltrials_gov": ("SECONDARY", "registry entries (sponsor-reported, not peer-reviewed); outcome posting discipline varies"),
    "who_ictrp": ("SECONDARY", "registry entries (sponsor-reported)"),
    "nasa_ntrs": ("SECONDARY", "technical reports — editorially curated, not peer-reviewed"),
    "doe_osti": ("SECONDARY", "technical reports/OSTI records — not peer-reviewed"),
    "manufacturing_literature": ("SECONDARY", "process literature mix incl. non-peer-reviewed"),
    # patent sources: aggregator views of PRIMARY offices (EPO/USPTO/WIPO
    # bibliographic facts are regulatory; the AGGREGATOR layer can err)
    "google_patents": ("SECONDARY", "patent aggregator view"),
    "lens_patent": ("SECONDARY", "patent aggregator view (high-quality curation, still a repackager)"),
    "patentbear": ("SECONDARY", "patent full-text repackager"),
    "patsnap_eureka": ("SECONDARY", "patent aggregator view"),
    "epo_ops": ("PRIMARY_REGULATORY", "EPO's OWN bibliographic/register service — issuer records (blocked without credential)"),
    "uspto_odp": ("PRIMARY_REGULATORY", "USPTO's OWN open-data service — issuer records (blocked without credential)"),
    "wipo_patentscope": ("PRIMARY_REGULATORY", "WIPO's OWN service — issuer records (blocked without credential)"),
    "google_bigquery_patents": ("SECONDARY", "repackaged patent corpus (billing-blocked)"),
    # --- BIOLOGY ---
    "uniprot": ("PRIMARY_MEASURED", "curated+evidenced protein annotations (evidence tags per annotation)"),
    "chembl": ("PRIMARY_MEASURED", "curated bioactivity measurements"),
    "rcsb_pdb": ("PRIMARY_MEASURED", "experimentally determined 3D structures"),
    # --- STANDARDS bodies ---
    "iso_catalogue": ("PRIMARY_REGULATORY", "ISO's own catalogue (blocked)"),
    "astm_standards": ("PRIMARY_REGULATORY", "ASTM's own catalogue (paywalled)"),
}

# Record-level tier OVERRIDES: structured fields that demote/promote a
# specific record regardless of its source default (Art. II — the record,
# not the source, is the evidence). Keys map normalized field -> rule.
RECORD_TIER_OVERRIDES: List[Dict[str, Any]] = [
    {
        "match": {"source_id": "fda_maude", "normalized.report_class": None},
        "note": "MAUDE records stay SECONDARY regardless of volume — "
                "report counts are signals, never incidence",
    },
]


def trust_tier(source_id: str, record: Optional[Dict[str, Any]] = None) -> Tuple[str, int]:
    """Tier + weight for a source (optionally record-level override).

    Unknown source raises KeyError — never a silent default (Art. XXV):
    an unmapped source MUST block aggregation until it is classified.
    """
    entry = SOURCE_TRUST.get(source_id)
    if entry is None:
        raise KeyError(
            f"source {source_id!r} has no declared trust tier — classify it "
            "in SOURCE_TRUST before aggregating (Art. XXV: no silent default)"
        )
    tier, _rationale = entry
    return tier, TRUST_TIERS[tier]


def rationale(source_id: str) -> str:
    entry = SOURCE_TRUST.get(source_id)
    if entry is None:
        raise KeyError(source_id)
    return entry[1]


def tier_of(source_id: str) -> str:
    return trust_tier(source_id)[0]


def weight(source_id: str) -> int:
    return trust_tier(source_id)[1]


def aggregate_by_tier(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Tier-weighted aggregation over records (raw counts NEVER hidden).

    Returns raw counts AND tier distribution AND the weighted count.
    The weighted count is an ORDERING device, not a truth probability;
    contradictions between tiers are surfaced elsewhere, never averaged
    away here.
    """
    from collections import Counter
    tier_counts: Counter = Counter()
    raw = 0
    missing = []
    for r in records:
        sid = r.get("source_id") or (r.get("provenance") or {}).get("provider")
        if sid is None:
            missing.append(r.get("record_id"))
            continue
        try:
            t, w = trust_tier(sid, r)
        except KeyError:
            missing.append(sid)
            continue
        tier_counts[t] += 1
        raw += 1
    weighted = sum(TRUST_TIERS[t] * n for t, n in tier_counts.items())
    return {
        "raw_record_count": raw,
        "tier_distribution": dict(tier_counts),
        "weighted_count": weighted,
        "unclassified": sorted(set(missing)),
        "note": "weighted_count is an ordering device (Art. XXVII "
                "ENGINEERING weights), not a probability; raw counts are "
                "always reported alongside",
    }


def ordering_key(record: Dict[str, Any]) -> int:
    """Sort key that ranks higher-trust records first (display order)."""
    sid = record.get("source_id") or (record.get("provenance") or {}).get("provider")
    if sid is None or sid not in SOURCE_TRUST:
        return 0
    return weight(sid)


def all_sources_classified(source_ids: List[str]) -> List[str]:
    """Sources with no tier — used by tests to keep coverage total."""
    return sorted(set(source_ids) - set(SOURCE_TRUST))
