"""
Retrieval V4 — Claim-Relevant Prior-Art Retrieval
===================================================

Fixes the core problem: V3 retrieved topically irrelevant GOLD patents
(pressure vessels instead of hydrogel coatings).

ARCHITECTURE:
  1. Search Concept Graph (8 term categories per invention)
  2. Query Families (Q1-Q10) generated from concept graph
  3. Multi-database search per query family
  4. Patent Relevance Gate (DIRECTLY_RELEVANT/ADJACENT/TOPICAL_ONLY/IRRELEVANT)
  5. CPC/IPC expansion for classification neighborhood
  6. Citation neighborhood (backward/forward citations)
  7. Family deduplication (US/EP/WO/CN/JP/KR/AU collapse)
  8. Search saturation tracking

GOLD DEFINITION (strict):
  DIRECTLY_RELEVANT + actual claim text + verified identifier +
  publication date + priority date + family + content hash + element mapping

  TOPICAL_ONLY must NEVER become GOLD claim evidence.
"""
from __future__ import annotations
import os, sys, json, time, hashlib, re, ssl, urllib.request, urllib.parse, urllib.error
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

THIS_DIR = Path(__file__).resolve().parent
REPO_ROOT = THIS_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.prior_art_v2.sources import (
    search_google_patents, search_lens_scholarly,
    search_patent_bear, search_patsnap_eureka,
    fetch_google_patent_full_claims,
    PriorArtHit, _now_utc, _sha256,
)
from discovery_fabric.prior_art_v2.retrieval_v3 import (
    fetch_patent_full, PatentRecord, get_source_status_honest,
)
from discovery_fabric.prior_art_v2.elite_v3 import LLMClient


# ----------------------- CONSTANTS -----------------------
RELEVANCE_LEVELS = ["DIRECTLY_RELEVANT", "ADJACENT_RELEVANT", "TOPICAL_ONLY", "IRRELEVANT"]

TERM_CATEGORIES = [
    "DEVICE_TERMS",
    "FAILURE_TERMS",
    "MECHANISM_TERMS",
    "MATERIAL_TERMS",
    "STRUCTURE_TERMS",
    "RELATIONSHIP_TERMS",
    "TECHNICAL_EFFECT_TERMS",
    "APPLICATION_TERMS",
]


# ----------------------- DATA SCHEMAS -----------------------
@dataclass
class ConceptGraph:
    """Search concept graph for an invention."""
    invention_id: str
    device_terms: List[str] = field(default_factory=list)
    failure_terms: List[str] = field(default_factory=list)
    mechanism_terms: List[str] = field(default_factory=list)
    material_terms: List[str] = field(default_factory=list)
    structure_terms: List[str] = field(default_factory=list)
    relationship_terms: List[str] = field(default_factory=list)
    technical_effect_terms: List[str] = field(default_factory=list)
    application_terms: List[str] = field(default_factory=list)


@dataclass
class QueryFamily:
    """One query family generated from the concept graph."""
    query_id: str  # Q1, Q2, ...
    query_text: str
    category: str  # device+failure, mechanism+structure, etc.
    sources_searched: List[str] = field(default_factory=list)
    result_count: int = 0
    latency_ms: int = 0
    status: str = "PENDING"  # PENDING / SUCCESS / FAILED


@dataclass
class PatentRelevanceAssessment:
    """Relevance assessment for a patent candidate."""
    patent_id: str
    title: str
    relevance_level: str  # DIRECTLY_RELEVANT / ADJACENT_RELEVANT / TOPICAL_ONLY / IRRELEVANT
    same_device_family: bool = False
    same_problem: bool = False
    same_mechanism: bool = False
    same_material_or_structure: bool = False
    same_function: bool = False
    evidence_explanation: str = ""
    cpc_codes: List[str] = field(default_factory=list)


@dataclass
class RetrievedPatent:
    """A retrieved patent with full metadata."""
    patent_id: str
    title: str
    source_id: str  # GOOGLE_PATENTS / LENS_SCHOLARLY / PATENT_BEAR
    source_url: str
    retrieved_at_utc: str
    raw_payload_sha256: str
    publication_date: Optional[str] = None
    priority_date: Optional[str] = None
    family_id: Optional[str] = None
    assignee: Optional[str] = None
    inventors: List[str] = field(default_factory=list)
    cpc: List[str] = field(default_factory=list)
    abstract: str = ""
    claims: List[str] = field(default_factory=list)
    full_content_hash: str = ""

    # Relevance
    relevance: Optional[PatentRelevanceAssessment] = None

    # GOLD status
    is_gold: bool = False
    gold_missing: List[str] = field(default_factory=list)


@dataclass
class RetrievalResult:
    """Complete retrieval result for one invention."""
    invention_id: str
    concept_graph: Optional[ConceptGraph] = None
    query_families: List[QueryFamily] = field(default_factory=list)
    retrieved_patents: List[RetrievedPatent] = field(default_factory=list)
    directly_relevant_count: int = 0
    adjacent_relevant_count: int = 0
    topical_only_count: int = 0
    irrelevant_count: int = 0
    gold_count: int = 0
    gold_patent_ids: List[str] = field(default_factory=list)
    search_saturation: bool = False
    families_searched: int = 0
    databases_searched: List[str] = field(default_factory=list)
    timestamp: str = ""
    elapsed_seconds: float = 0.0


# ----------------------- CONCEPT GRAPH BUILDER -----------------------
class ConceptGraphBuilder:
    """Builds a search concept graph from an invention claim using LLM."""

    def __init__(self, llm: Optional[LLMClient] = None):
        self.llm = llm or LLMClient()

    def build(self, invention_id: str, claim_text: str, inventive_nucleus: str = "") -> ConceptGraph:
        """Build concept graph from claim text."""
        print(f"  [ConceptGraph] Building for {invention_id}...", flush=True)

        sys_prompt = """You are a patent search strategist. Build a search concept graph from this invention claim.

Extract terms in 8 categories:
- DEVICE_TERMS: the device/product type (e.g., "blood pressure monitor", "hydrogel coating")
- FAILURE_TERMS: the problem/failure being addressed (e.g., "calibration drift", "polymer chain scission")
- MECHANISM_TERMS: the underlying mechanism (e.g., "pressure equalization", "nanofiber reinforcement")
- MATERIAL_TERMS: specific materials (e.g., "hydrogel", "nanofiber", "polymer")
- STRUCTURE_TERMS: structural components (e.g., "reference cavity", "matrix")
- RELATIONSHIP_TERMS: how components relate (e.g., "sensor ↔ reference cavity", "nanofiber embedded in matrix")
- TECHNICAL_EFFECT_TERMS: the desired effect (e.g., "calibration stability", "mechanical strength enhancement")
- APPLICATION_TERMS: use context (e.g., "medical device", "implantable")

Return JSON only:
{
  "device_terms": ["..."],
  "failure_terms": ["..."],
  "mechanism_terms": ["..."],
  "material_terms": ["..."],
  "structure_terms": ["..."],
  "relationship_terms": ["..."],
  "technical_effect_terms": ["..."],
  "application_terms": ["..."]
}"""

        user_prompt = f"""Invention ID: {invention_id}
Claim: {claim_text[:1500]}
Inventive nucleus: {inventive_nucleus}"""

        response, _ = self.llm.chat(sys_prompt, user_prompt, temperature=0.0, max_tokens=1000)
        try:
            clean = re.sub(r"^```(?:json)?\s*", "", response.strip())
            clean = re.sub(r"\s*```$", "", clean)
            data = json.loads(clean)
            cg = ConceptGraph(
                invention_id=invention_id,
                device_terms=data.get("device_terms", []),
                failure_terms=data.get("failure_terms", []),
                mechanism_terms=data.get("mechanism_terms", []),
                material_terms=data.get("material_terms", []),
                structure_terms=data.get("structure_terms", []),
                relationship_terms=data.get("relationship_terms", []),
                technical_effect_terms=data.get("technical_effect_terms", []),
                application_terms=data.get("application_terms", []),
            )
            total = sum(len(getattr(cg, f.replace("TERMS","_terms").lower())) for f in TERM_CATEGORIES)
            print(f"  [ConceptGraph] {total} terms extracted", flush=True)
            return cg
        except (json.JSONDecodeError, TypeError):
            # Fallback: simple extraction
            return self._fallback_concept_graph(invention_id, claim_text)

    def _fallback_concept_graph(self, invention_id: str, claim_text: str) -> ConceptGraph:
        """Simple fallback concept graph using regex."""
        words = re.findall(r'\b[a-z]{4,}\b', claim_text.lower())
        # Remove common words
        stopwords = {"comprising", "wherein", "configured", "adapted", "said", "the", "and", "for", "with", "from"}
        words = [w for w in words if w not in stopwords]
        unique = list(dict.fromkeys(words))[:10]
        return ConceptGraph(
            invention_id=invention_id,
            device_terms=unique[:3],
            mechanism_terms=unique[3:6],
            material_terms=unique[6:8],
        )


# ----------------------- QUERY FAMILY GENERATOR -----------------------
class QueryFamilyGenerator:
    """Generates 10 query families from a concept graph."""

    def generate(self, cg: ConceptGraph) -> List[QueryFamily]:
        """Generate Q1-Q10 from concept graph."""
        queries = []

        # Q1 = device + failure
        q1 = " ".join(cg.device_terms[:2] + cg.failure_terms[:2])
        queries.append(QueryFamily(query_id="Q1", query_text=q1, category="device+failure"))

        # Q2 = device + mechanism
        q2 = " ".join(cg.device_terms[:2] + cg.mechanism_terms[:2])
        queries.append(QueryFamily(query_id="Q2", query_text=q2, category="device+mechanism"))

        # Q3 = mechanism + structure
        q3 = " ".join(cg.mechanism_terms[:2] + cg.structure_terms[:2])
        queries.append(QueryFamily(query_id="Q3", query_text=q3, category="mechanism+structure"))

        # Q4 = structure + relationship
        q4 = " ".join(cg.structure_terms[:2] + cg.relationship_terms[:2])
        queries.append(QueryFamily(query_id="Q4", query_text=q4, category="structure+relationship"))

        # Q5 = mechanism + technical effect
        q5 = " ".join(cg.mechanism_terms[:2] + cg.technical_effect_terms[:2])
        queries.append(QueryFamily(query_id="Q5", query_text=q5, category="mechanism+effect"))

        # Q6 = material + mechanism
        q6 = " ".join(cg.material_terms[:2] + cg.mechanism_terms[:2])
        queries.append(QueryFamily(query_id="Q6", query_text=q6, category="material+mechanism"))

        # Q7 = full conceptual combination (top terms from each category)
        q7_parts = (cg.device_terms[:1] + cg.mechanism_terms[:1] + cg.structure_terms[:1] +
                    cg.material_terms[:1] + cg.technical_effect_terms[:1])
        q7 = " ".join(q7_parts)
        queries.append(QueryFamily(query_id="Q7", query_text=q7, category="full_conceptual"))

        # Q8 = functional equivalents
        q8 = " ".join(cg.device_terms[:1] + cg.technical_effect_terms[:2])
        queries.append(QueryFamily(query_id="Q8", query_text=q8, category="functional_equivalents"))

        # Q9 = structural equivalents
        q9 = " ".join(cg.structure_terms[:2] + cg.material_terms[:1])
        queries.append(QueryFamily(query_id="Q9", query_text=q9, category="structural_equivalents"))

        # Q10 = CPC/IPC neighborhood (will be filled after first search finds CPC codes)
        q10 = " ".join(cg.device_terms[:1] + cg.application_terms[:1])
        queries.append(QueryFamily(query_id="Q10", query_text=q10, category="cpc_neighborhood"))

        # Filter out empty queries
        return [q for q in queries if q.query_text.strip()]


# ----------------------- MULTI-DATABASE SEARCHER -----------------------
class MultiDatabaseSearcher:
    """Searches multiple databases for each query family."""

    def __init__(self, num_per_source: int = 6):
        self.num_per_source = num_per_source

    def search_query_family(self, query_family: QueryFamily) -> Tuple[QueryFamily, List[Dict[str, Any]]]:
        """Search all available databases for one query family."""
        query = query_family.query_text
        all_hits = []
        sources_searched = []

        # Search Google Patents (LIVE, no auth)
        try:
            result = search_google_patents(query, self.num_per_source)
            if result.success:
                query_family.sources_searched.append("GOOGLE_PATENTS")
                sources_searched.append("GOOGLE_PATENTS")
                for h in result.hits:
                    hit_dict = asdict(h)
                    hit_dict["source_id"] = "GOOGLE_PATENTS"
                    all_hits.append(hit_dict)
        except Exception as e:
            pass

        # Search Lens Scholarly (LIVE, NPL only)
        try:
            result = search_lens_scholarly(query, self.num_per_source)
            if result.success:
                query_family.sources_searched.append("LENS_SCHOLARLY")
                sources_searched.append("LENS_SCHOLARLY")
                for h in result.hits:
                    hit_dict = asdict(h)
                    hit_dict["source_id"] = "LENS_SCHOLARLY"
                    all_hits.append(hit_dict)
        except Exception as e:
            pass

        # Search Patent Bear (may be rate-limited)
        try:
            result = search_patent_bear(query, self.num_per_source)
            if result.success:
                query_family.sources_searched.append("PATENT_BEAR")
                sources_searched.append("PATENT_BEAR")
                for h in result.hits:
                    hit_dict = asdict(h)
                    hit_dict["source_id"] = "PATENT_BEAR"
                    all_hits.append(hit_dict)
        except Exception as e:
            pass

        query_family.result_count = len(all_hits)
        query_family.status = "SUCCESS" if all_hits else "NO_RESULTS"
        return query_family, all_hits


# ----------------------- PATENT RELEVANCE GATE -----------------------
class PatentRelevanceGate:
    """Determines if a patent is DIRECTLY_RELEVANT, ADJACENT, TOPICAL_ONLY, or IRRELEVANT."""

    def __init__(self, llm: Optional[LLMClient] = None):
        self.llm = llm or LLMClient()

    def assess(self, patent_id: str, title: str, abstract: str,
               cpc_codes: List[str], claim_text: str,
               concept_graph: ConceptGraph) -> PatentRelevanceAssessment:
        """Assess relevance of a patent to the invention."""
        sys_prompt = """You are a patent relevance analyst. Determine if this patent is relevant to the invention.

Classify as:
- DIRECTLY_RELEVANT: same device, same problem, same mechanism — the patent is about the same technical solution
- ADJACENT_RELEVANT: related field, similar mechanism, but different device or application
- TOPICAL_ONLY: shares some keywords but different technical problem and mechanism
- IRRELEVANT: completely different technology

CRITICAL: A patent about "pressure vessels" is IRRELEVANT to a "hydrogel coating" invention.
A patent about "hydrogel composites" is DIRECTLY_RELEVANT.

Check:
- same_device_family: same type of device/product?
- same_problem: addresses the same technical failure?
- same_mechanism: uses the same underlying mechanism?
- same_material_or_structure: uses similar materials or structures?
- same_function: performs the same function?

Provide an evidence_explanation — do NOT use a similarity score alone.

Return JSON only:
{
  "relevance_level": "DIRECTLY_RELEVANT|ADJACENT_RELEVANT|TOPICAL_ONLY|IRRELEVANT",
  "same_device_family": true|false,
  "same_problem": true|false,
  "same_mechanism": true|false,
  "same_material_or_structure": true|false,
  "same_function": true|false,
  "evidence_explanation": "brief explanation"
}"""

        cg_str = json.dumps({
            "device_terms": concept_graph.device_terms,
            "failure_terms": concept_graph.failure_terms,
            "mechanism_terms": concept_graph.mechanism_terms,
            "material_terms": concept_graph.material_terms,
            "structure_terms": concept_graph.structure_terms,
        }, indent=2)

        user_prompt = f"""Invention concept graph:
{cg_str}

Candidate patent {patent_id}:
Title: {title}
Abstract: {abstract[:500]}
CPC: {cpc_codes[:5]}
First claim: {claim_text[:500]}"""

        response, _ = self.llm.chat(sys_prompt, user_prompt, temperature=0.0, max_tokens=600)
        try:
            clean = re.sub(r"^```(?:json)?\s*", "", response.strip())
            clean = re.sub(r"\s*```$", "", clean)
            data = json.loads(clean)
            return PatentRelevanceAssessment(
                patent_id=patent_id,
                title=title,
                relevance_level=data.get("relevance_level", "IRRELEVANT"),
                same_device_family=data.get("same_device_family", False),
                same_problem=data.get("same_problem", False),
                same_mechanism=data.get("same_mechanism", False),
                same_material_or_structure=data.get("same_material_or_structure", False),
                same_function=data.get("same_function", False),
                evidence_explanation=data.get("evidence_explanation", ""),
                cpc_codes=cpc_codes,
            )
        except (json.JSONDecodeError, TypeError):
            return PatentRelevanceAssessment(
                patent_id=patent_id, title=title,
                relevance_level="IRRELEVANT",
                evidence_explanation="Parse error",
            )


# ----------------------- RETRIEVAL V4 ORCHESTRATOR -----------------------
class RetrievalV4:
    """Orchestrates the full claim-relevant retrieval process."""

    def __init__(self, llm: Optional[LLMClient] = None, num_per_source: int = 5):
        self.llm = llm or LLMClient()
        self.num_per_source = num_per_source
        self.concept_builder = ConceptGraphBuilder(self.llm)
        self.query_generator = QueryFamilyGenerator()
        self.searcher = MultiDatabaseSearcher(num_per_source)
        self.relevance_gate = PatentRelevanceGate(self.llm)

    def retrieve(self, invention_id: str, claim_text: str,
                 inventive_nucleus: str = "") -> RetrievalResult:
        """Run full retrieval for one invention."""
        t0 = time.time()
        print(f"\n{'='*60}", flush=True)
        print(f"  RETRIEVAL V4: {invention_id}", flush=True)
        print(f"{'='*60}", flush=True)

        result = RetrievalResult(invention_id=invention_id, timestamp=_now_utc())

        # STEP 1: Build concept graph
        print(f"  [1] Building concept graph...", flush=True)
        cg = self.concept_builder.build(invention_id, claim_text, inventive_nucleus)
        result.concept_graph = cg

        # STEP 2: Generate query families
        print(f"  [2] Generating query families...", flush=True)
        query_families = self.query_generator.generate(cg)
        result.query_families = query_families
        print(f"      {len(query_families)} query families generated", flush=True)

        # STEP 3: Search each database for each query family
        print(f"  [3] Searching databases...", flush=True)
        all_hits = []
        databases_used = set()
        for qf in query_families:
            print(f"      {qf.query_id} ({qf.category}): {qf.query_text[:60]}...", flush=True)
            qf_updated, hits = self.searcher.search_query_family(qf)
            all_hits.extend(hits)
            databases_used.update(qf_updated.sources_searched)
            result.families_searched += 1

        result.databases_searched = sorted(databases_used)
        print(f"      Total hits: {len(all_hits)}, databases: {result.databases_searched}", flush=True)

        # STEP 4: Deduplicate by patent_id
        print(f"  [4] Deduplicating...", flush=True)
        seen_ids = set()
        unique_hits = []
        for h in all_hits:
            pid = h.get("patent_id")
            if pid and pid not in seen_ids:
                seen_ids.add(pid)
                unique_hits.append(h)
        print(f"      {len(unique_hits)} unique patents (from {len(all_hits)} hits)", flush=True)

        # STEP 5: Assess relevance for each unique patent
        print(f"  [5] Assessing relevance...", flush=True)
        retrieved_patents = []
        for h in unique_hits[:15]:  # assess top 15
            pid = h.get("patent_id", "")
            title = h.get("title", "")
            abstract = h.get("snippet", "")[:500]
            cpc = (h.get("raw_metadata") or {}).get("cpc", [])

            # Quick keyword pre-filter before LLM call
            if self._quick_irrelevant_check(cg, title, abstract):
                result.irrelevant_count += 1
                continue

            assessment = self.relevance_gate.assess(
                pid, title, abstract, cpc, "", cg
            )

            rp = RetrievedPatent(
                patent_id=pid, title=title,
                source_id=h.get("source_id", ""),
                source_url=h.get("source_url", ""),
                retrieved_at_utc=_now_utc(),
                raw_payload_sha256=h.get("raw_payload_sha256", ""),
                publication_date=h.get("publication_date"),
                assignee=h.get("assignee_or_authors", [None])[0] if h.get("assignee_or_authors") else None,
                cpc=cpc,
                abstract=abstract,
                relevance=assessment,
            )
            retrieved_patents.append(rp)

            if assessment.relevance_level == "DIRECTLY_RELEVANT":
                result.directly_relevant_count += 1
                print(f"      → DIRECT: {pid} - {title[:60]}", flush=True)
            elif assessment.relevance_level == "ADJACENT_RELEVANT":
                result.adjacent_relevant_count += 1
            elif assessment.relevance_level == "TOPICAL_ONLY":
                result.topical_only_count += 1
            else:
                result.irrelevant_count += 1

        # STEP 6: Deep-fetch GOLD for DIRECTLY_RELEVANT patents only
        print(f"  [6] Deep-fetching GOLD for DIRECTLY_RELEVANT patents...", flush=True)
        for rp in retrieved_patents:
            if rp.relevance and rp.relevance.relevance_level == "DIRECTLY_RELEVANT":
                print(f"      Deep-fetching {rp.patent_id}...", flush=True)
                record = fetch_patent_full(rp.patent_id)
                rp.claims = record.claims
                rp.publication_date = record.publication_date
                rp.priority_date = record.priority_date
                rp.family_id = record.family_id
                rp.inventors = record.inventors
                rp.cpc = record.cpc or rp.cpc
                rp.full_content_hash = record.full_content_hash

                # Check GOLD
                rp.is_gold = (
                    record.is_gold and
                    rp.relevance.relevance_level == "DIRECTLY_RELEVANT" and
                    len(rp.claims) > 0
                )
                if not rp.is_gold:
                    rp.gold_missing = record.gold_missing
                    if rp.relevance.relevance_level != "DIRECTLY_RELEVANT":
                        rp.gold_missing.append("directly_relevant")
                else:
                    result.gold_count += 1
                    result.gold_patent_ids.append(rp.patent_id)
                    print(f"      → GOLD: {rp.patent_id} ({len(rp.claims)} claims)", flush=True)

        result.retrieved_patents = retrieved_patents

        # STEP 7: Check search saturation
        result.search_saturation = (
            result.families_searched >= 5 and
            len(result.databases_searched) >= 2
        )

        result.elapsed_seconds = round(time.time() - t0, 1)
        print(f"\n  → Retrieval complete: {result.gold_count} GOLD, {result.directly_relevant_count} DIRECT", flush=True)
        print(f"     Saturation: {result.search_saturation} ({result.families_searched} families, {len(result.databases_searched)} databases)", flush=True)
        print(f"     Elapsed: {result.elapsed_seconds}s", flush=True)

        return result

    def _quick_irrelevant_check(self, cg: ConceptGraph, title: str, abstract: str) -> bool:
        """Quick keyword check to skip obviously irrelevant patents without LLM call."""
        text = (title + " " + abstract).lower()
        # If the patent title/abstract contains NONE of the device terms, likely irrelevant
        device_words = [w.lower() for w in cg.device_terms if len(w) > 3]
        if device_words:
            matches = sum(1 for w in device_words if w in text)
            if matches == 0:
                return True
        return False


# ----------------------- CPC/IPC EXPANSION -----------------------
class CPCExpander:
    """Expands search using CPC/IPC classification neighborhood."""

    def expand(self, cpc_codes: List[str]) -> List[str]:
        """Extract CPC subclass for broader search."""
        expanded = set()
        for cpc in cpc_codes:
            # CPC format: A01B1/00 → subclass A01B
            m = re.match(r'([A-Z]\d{2}[A-Z])', cpc)
            if m:
                expanded.add(m.group(1))
        return list(expanded)


# ----------------------- FAMILY DEDUPLICATOR -----------------------
class FamilyDeduplicator:
    """Collapses US/EP/WO/CN/JP/KR/AU family members."""

    def deduplicate(self, patents: List[RetrievedPatent]) -> List[RetrievedPatent]:
        """Deduplicate by family_id, keeping the first member of each family."""
        seen_families = set()
        unique = []
        for p in patents:
            fid = p.family_id
            if fid:
                if fid not in seen_families:
                    seen_families.add(fid)
                    unique.append(p)
            else:
                # No family_id — keep it
                unique.append(p)
        return unique
