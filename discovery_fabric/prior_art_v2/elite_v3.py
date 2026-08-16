"""
ELITE V3 — Fixed Evidence Layer + EPO/USPTO Obviousness + Relationship Mapping
=================================================================================

Per CEO directive: fix the patent evidence bottleneck before more elite audits.

KEY FIXES vs V2:
  1. Deterministic Google Patents retrieval fallback chain (A→B→C→D→E)
  2. Strict GOLD evidence definition (8 requirements, no snippet/abstract/LLM)
  3. LENS_PATENT separated from LENS_SCHOLARLY (never merged)
  4. PATENT_BEAR_RATE_LIMITED and PATSNAP_API_UNAVAILABLE as real statuses
  5. Relationship mapper (A→B, B→C, A+B+C arrangement) per MPEP
  6. Inherency firewall (necessity_evidence + technical_basis)
  7. EPO/USPTO obviousness with COULD/WOULD distinction + no hindsight
  8. EXPERIMENT_TO_ESTABLISH_EFFECT for hypothesized technical effects
  9. Manufacturing: every UNKNOWN needs resolution_method
  10. PROMISING_INSUFFICIENT_EVIDENCE + STRONG_CANDIDATE_FOR_ATTORNEY_REVIEW statuses

GOLD EVIDENCE (per CEO Section 3):
  Requires ALL: verified patent_id, publication_date, priority_date, family_id,
  claim_text, source_url, retrieval_timestamp, full_content_hash.
  Search snippet = NOT GOLD. Abstract only = NOT GOLD. LLM summary = NOT GOLD.

SOURCE STATUS (per CEO Sections 4, 5, 6):
  GOOGLE_PATENTS: LIVE
  LENS_SCHOLARLY: LIVE (NPL only — NOT patents)
  LENS_PATENT: UNAVAILABLE (Lens patent API returns 401)
  PATENT_BEAR: RATE_LIMITED (20/20 monthly exhausted)
  PATSNAP_EUREKA: API_UNAVAILABLE (account tier insufficient)

OBVIOUSNESS (per CEO Section 11 — EPO/USPTO structure):
  closest_prior_art → objective_technical_problem → differences →
  technical_effect → motivation → reasonable_expectation_of_success →
  teaching_away → COULD question → WOULD question
  Both COULD and WOULD must be answered. No hindsight.
"""
from __future__ import annotations
import os, sys, json, time, hashlib, re, subprocess
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

THIS_DIR = Path(__file__).resolve().parent
REPO_ROOT = THIS_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.prior_art_v2.sources import (
    PriorArtHit, SourceQueryResult,
    search_all_sources, search_google_patents, search_lens_scholarly,
    search_patent_bear, search_patsnap_eureka,
    _now_utc, _sha256,
)
from discovery_fabric.prior_art_v2.retrieval_v3 import (
    fetch_patent_full, PatentRecord, RetrievalAttempt,
    get_source_status_honest, normalize_patent_family,
)


# ----------------------- CONSTANTS -----------------------
MAX_REDESIGN_ROUNDS = 3
MIN_GOLD_EVIDENCE_FOR_STRONG = 2  # Need at least 2 GOLD patents for STRONG

DISCLOSURE_TYPES = ["EXPLICIT", "IMPLICIT", "INHERENT", "NOT_DISCLOSED", "UNCERTAIN"]
EVIDENCE_LEVELS = ["GOLD", "SILVER", "BRONZE", "NONE"]
ATTACK_TYPES = ["NOVELTY_102", "OBVIOUSNESS_103", "ENABLEMENT_112",
                "DESIGN_AROUND", "TECHNICAL_EFFECT"]

# Per CEO Section 17: new status names
FINAL_STATUSES = [
    "ELITE",                          # GOLD evidence + survived all attacks + economic value
    "STRONG_CANDIDATE_FOR_ATTORNEY_REVIEW",  # Sufficient evidence, survived attacks
    "PROMISING_INSUFFICIENT_EVIDENCE", # Survived but not enough GOLD evidence
    "WEAK",                           # Partial survival
    "REJECT",                         # Killed
]


# ----------------------- LLM CLIENT (NVIDIA API) -----------------------
class LLMClient:
    """NVIDIA API chat completions client.

    Uses NVIDIA's integrate.api.nvidia.com endpoint with OpenAI-compatible API.
    Primary model: meta/llama-3.1-8b-instruct (fast, 0.3s/call)
    Fallback model: deepseek-ai/deepseek-v4-flash-0731 (slower but capable)

    Replaces z-ai-web-dev-sdk which was rate-limiting (HTTP 429).
    """

    # Model priority list — try in order (V3.6: better models for 103 reasoning)
    MODELS = [
        "meta/llama-3.1-8b-instruct",          # Fast, 0.3s, good for JSON
        "google/gemma-4-31b-it",                # Gemma 4 31B — better legal reasoning (5-8s)
        "deepseek-ai/deepseek-v4-flash-0731",   # DeepSeek V4 flash — fallback
    ]

    MIN_CALL_INTERVAL_S = 1.0  # NVIDIA has higher rate limits than z-ai
    _last_call_time = 0.0

    def __init__(self, timeout_s: int = 60, max_retries: int = 2):
        self.timeout_s = timeout_s
        self.max_retries = max_retries
        self._call_count = 0
        self._total_latency_ms = 0
        self._rate_limit_hits = 0
        self._failed_calls = 0
        # Load NVIDIA API key
        from pathlib import Path as _P
        _keys_file = _P("/home/z/my-project/discovery-evidence-fabric/.env.keys")
        self._api_key = ""
        if _keys_file.exists():
            for line in _keys_file.read_text().splitlines():
                if line.startswith("NVIDIA_API_KEY="):
                    self._api_key = line.split("=", 1)[1].strip()
                    break

    def _throttle(self):
        now = time.time()
        elapsed = now - LLMClient._last_call_time
        if elapsed < LLMClient.MIN_CALL_INTERVAL_S:
            time.sleep(LLMClient.MIN_CALL_INTERVAL_S - elapsed)
        LLMClient._last_call_time = time.time()

    def _call_nvidia(self, model: str, system_prompt: str, user_prompt: str,
                     temperature: float, max_tokens: int) -> Tuple[Optional[str], int, Optional[str]]:
        """Call NVIDIA API. Returns (content, latency_ms, error)."""
        import urllib.request, urllib.error, ssl

        url = "https://integrate.api.nvidia.com/v1/chat/completions"
        payload = json.dumps({
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }).encode("utf-8")

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        t0 = time.time()
        try:
            req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
            resp = urllib.request.urlopen(req, timeout=self.timeout_s, context=ctx)
            body = resp.read()
            elapsed_ms = int((time.time() - t0) * 1000)
            data = json.loads(body)
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return content, elapsed_ms, None
        except urllib.error.HTTPError as e:
            elapsed_ms = int((time.time() - t0) * 1000)
            body = ""
            try: body = e.read().decode("utf-8", errors="ignore")[:200]
            except: pass
            return None, elapsed_ms, f"HTTP {e.code}: {body}"
        except Exception as e:
            elapsed_ms = int((time.time() - t0) * 1000)
            return None, elapsed_ms, f"EXCEPTION: {str(e)[:150]}"

    def chat(self, system_prompt: str, user_prompt: str,
             temperature: float = 0.0, max_tokens: int = 2500) -> Tuple[str, int]:
        """Synchronous chat call using NVIDIA API. Tries multiple models."""
        if not self._api_key:
            return "[LLM_ERROR: no NVIDIA_API_KEY]", 0

        last_error = ""
        for attempt in range(self.max_retries + 1):
            self._throttle()
            # Try each model in priority order
            for model in self.MODELS:
                content, latency, error = self._call_nvidia(
                    model, system_prompt, user_prompt, temperature, max_tokens
                )
                if content is not None:
                    self._call_count += 1
                    self._total_latency_ms += latency
                    return content, latency
                # If 429, try next model
                if error and "429" in error:
                    self._rate_limit_hits += 1
                    continue
                # If 404, model not available — try next
                if error and "404" in error:
                    continue
                # Other error — try next model
                last_error = error
                continue

            # All models failed — wait and retry
            if attempt < self.max_retries:
                wait = 5 * (2 ** attempt)
                print(f"      [LLM] all models failed (attempt {attempt+1}), waiting {wait}s...", flush=True)
                time.sleep(wait)

        self._failed_calls += 1
        return f"[LLM_ERROR: {last_error}]", 0

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "call_count": self._call_count,
            "total_latency_ms": self._total_latency_ms,
            "rate_limit_hits": self._rate_limit_hits,
            "failed_calls": self._failed_calls,
            "provider": "NVIDIA",
            "models": self.MODELS,
        }


# ----------------------- DATA SCHEMAS -----------------------
@dataclass
class ClaimElement:
    element_id: str
    technical_feature: str
    structural_requirement: str = ""
    functional_requirement: str = ""
    relationship: str = ""
    parameter: str = ""


@dataclass
class RelationshipMapping:
    """Maps relationships between elements per MPEP anticipation requirement."""
    element_pair: str  # e.g. "A→B", "B→C", "A+B+C"
    relationship_type: str  # structural | functional | operational | causal
    prior_art_disclosure: str  # does the prior art disclose this relationship?
    disclosure_type: str  # EXPLICIT | IMPLICIT | INHERENT | NOT_DISCLOSED | UNCERTAIN
    evidence_level: str  # GOLD | SILVER | BRONZE | NONE
    necessity_evidence: str = ""  # for INHERENT: why is this necessarily present?
    technical_basis: str = ""  # for INHERENT: scientific/technical basis
    reasoning: str = ""


@dataclass
class ElementMapping:
    element_id: str
    disclosure_type: str  # EXPLICIT | IMPLICIT | INHERENT | NOT_DISCLOSED | UNCERTAIN
    prior_art_text: str
    evidence_level: str
    confidence: float
    reasoning: str
    necessity_evidence: str = ""  # for INHERENT
    technical_basis: str = ""  # for INHERENT


@dataclass
class PriorArtRecord:
    source_id: str
    source_url: str
    retrieved_at_utc: str
    raw_payload_sha256: str
    title: str
    snippet: str
    assignee_or_authors: List[str]
    publication_date: Optional[str]
    patent_id: Optional[str] = None
    doi: Optional[str] = None
    evidence_level: str = "BRONZE"
    # GOLD fields (from retrieval_v3)
    full_claims: Optional[List[str]] = None
    full_abstract: Optional[str] = None
    priority_date: Optional[str] = None
    family_id: Optional[str] = None
    inventors: List[str] = field(default_factory=list)
    cpc: List[str] = field(default_factory=list)
    retrieval_attempts: List[Dict[str, Any]] = field(default_factory=list)
    retrieval_method: str = ""
    full_content_hash: str = ""


@dataclass
class ClaimVersion:
    version: int
    claim_text: str
    claim_hash: str
    created_at_utc: str
    elements: List[ClaimElement] = field(default_factory=list)
    redesign_rationale: str = ""


@dataclass
class Attack:
    attack_type: str
    attack_strength: str
    primary_reference: Optional[Dict[str, Any]] = None
    secondary_references: List[Dict[str, Any]] = field(default_factory=list)
    rationale: str = ""
    elements_addressed: List[str] = field(default_factory=list)
    # EPO/USPTO obviousness structure (per CEO Section 11)
    closest_prior_art: str = ""
    objective_technical_problem: str = ""
    differences: str = ""
    technical_effect: str = ""
    motivation: str = ""
    reasonable_expectation_of_success: str = ""
    teaching_away: str = ""
    could_question: str = ""  # COULD the skilled person do it?
    would_question: str = ""  # WOULD the skilled person do it? (MANDATORY)
    no_hindsight_verified: bool = False
    # Design-around
    design_around_workarounds: List[Dict[str, Any]] = field(default_factory=list)
    # Required arrangement (per CEO Section 9)
    required_arrangement_disclosed: bool = False
    arrangement_analysis: str = ""
    can_survive: bool = True
    survival_path: str = ""
    evidence_level: str = "BRONZE"


@dataclass
class EconomicValue:
    customer_problem: str
    economic_pain: str
    current_cost: str
    current_failure: str
    value_created: str
    who_pays: str
    why_they_pay: str
    adoption_barrier: str
    value_creation_types: List[str]
    market_size_evidence_tag: str = "HYPOTHESIS"
    market_size_basis: str = ""


@dataclass
class ManufacturingFeasibility:
    manufacturing_process: str
    materials: str
    tooling: str
    assembly: str
    quality_control: str
    throughput: str
    yield_rate: str
    supply_chain: str
    regulatory_burden: str
    status: str
    # Per CEO Section 16: every UNKNOWN needs resolution_method
    unknowns: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class TechnicalEffect:
    problem: str
    distinguishing_feature: str
    mechanism: str
    technical_effect: str
    classification: str  # DOCUMENTED | INFERRED | HYPOTHESIZED
    unexpected: bool = False
    synergistic: bool = False
    non_linear: bool = False
    counterintuitive: bool = False
    # Per CEO Section 14: if hypothesized, create experiment
    experiment_to_establish_effect: str = ""


@dataclass
class ClaimRound:
    round_num: int
    claim_version_in: ClaimVersion
    prior_art_search: Dict[str, Any]
    element_mappings: List[ElementMapping]
    relationship_mappings: List[RelationshipMapping]
    kill_search: Dict[str, Any]
    attacks: List[Attack]
    redesign: Optional[ClaimVersion] = None
    round_outcome: str = ""


@dataclass
class EliteV3Result:
    invention_id: str
    device_class: str
    inventive_nucleus: str
    claim_versions: List[ClaimVersion]
    rounds: List[ClaimRound]
    economic_value: EconomicValue
    manufacturing: ManufacturingFeasibility
    technical_effect: TechnicalEffect
    final_claim: str
    final_status: str  # per CEO Section 17
    final_adjudication_reason: str
    sources_status: Dict[str, str]  # honest source status
    total_prior_art_hits: int
    gold_evidence_count: int
    silver_evidence_count: int
    bronze_evidence_count: int
    gold_patent_ids: List[str] = field(default_factory=list)
    timestamp: str = ""
    llm_calls: int = 0
    elapsed_seconds: float = 0.0


# ----------------------- ELITE V3 AUDITOR -----------------------
class EliteV3Auditor:
    """Deep audit with fixed evidence layer."""

    def __init__(self, llm: Optional[LLMClient] = None, num_per_source: int = 6):
        self.llm = llm or LLMClient()
        self.num_per_source = num_per_source

    def audit(self, invention_id: str, device_class: str,
              inventive_nucleus: str, initial_claim: str) -> EliteV3Result:
        t0 = time.time()
        print(f"\n{'='*70}", flush=True)
        print(f"  ELITE V3 DEEP AUDIT: {invention_id} ({device_class})", flush=True)
        print(f"{'='*70}", flush=True)

        # Parse initial claim
        print(f"  [0] Parsing CLAIM_0...", flush=True)
        claim_v0 = ClaimVersion(
            version=0, claim_text=initial_claim,
            claim_hash=_sha256(initial_claim), created_at_utc=_now_utc(),
        )
        claim_v0.elements = self._parse_claim_elements(initial_claim)
        print(f"      Parsed {len(claim_v0.elements)} elements", flush=True)

        # Economic value
        print(f"  [1] Economic value assessment...", flush=True)
        economic = self._assess_economic_value(invention_id, device_class, inventive_nucleus, initial_claim)

        # Technical effect
        print(f"  [2] Technical effect classification...", flush=True)
        tech_effect = self._classify_technical_effect(invention_id, inventive_nucleus, initial_claim)
        # If hypothesized, create experiment
        if tech_effect.classification == "HYPOTHESIZED" and not tech_effect.experiment_to_establish_effect:
            tech_effect.experiment_to_establish_effect = self._design_effect_experiment(tech_effect, inventive_nucleus)

        # Manufacturing
        print(f"  [3] Manufacturing feasibility...", flush=True)
        manufacturing = self._assess_manufacturing(invention_id, device_class, inventive_nucleus, initial_claim)

        # Claim attack loop
        rounds: List[ClaimRound] = []
        current_claim = claim_v0
        sources_status = get_source_status_honest()
        total_hits = 0
        gold_count = 0
        silver_count = 0
        bronze_count = 0
        gold_patent_ids: List[str] = []

        for round_num in range(1, MAX_REDESIGN_ROUNDS + 1):
            print(f"\n  --- Round {round_num}/{MAX_REDESIGN_ROUNDS} ---", flush=True)

            # 4-source search (with honest status)
            print(f"  [R{round_num}.1] 4-source prior-art search (honest status)...", flush=True)
            search_result = self._four_source_search(current_claim.claim_text)
            all_hits = self._collect_hits(search_result)
            total_hits += len(all_hits)

            # Deep-fetch top patents for GOLD evidence
            print(f"  [R{round_num}.2] Deep-fetching top patents for GOLD evidence...", flush=True)
            # Prioritize hits with patent_id (skip NPL hits that have no patent to fetch)
            patent_hits = [h for h in all_hits if h.get("patent_id")]
            print(f"       {len(patent_hits)} hits have patent_id (out of {len(all_hits)} total)", flush=True)
            for h in patent_hits[:5]:
                if h.get("patent_id") and h.get("evidence_level") != "GOLD":
                    pid = h["patent_id"]
                    print(f"       Deep-fetching {pid}...", flush=True)
                    record = fetch_patent_full(pid)
                    if record.is_gold:
                        h["evidence_level"] = "GOLD"
                        h["full_claims"] = record.claims
                        h["full_abstract"] = record.abstract
                        h["priority_date"] = record.priority_date
                        h["family_id"] = record.family_id
                        h["inventors"] = record.inventors
                        h["cpc"] = record.cpc
                        h["retrieval_attempts"] = [asdict(a) for a in record.retrieval_attempts]
                        h["retrieval_method"] = record.retrieval_method
                        h["full_content_hash"] = record.full_content_hash
                        if pid not in gold_patent_ids:
                            gold_patent_ids.append(pid)
                        gold_count += 1
                        print(f"       → GOLD: {len(record.claims)} claims, family={record.family_id}", flush=True)
                    elif record.claims:
                        h["evidence_level"] = "SILVER"
                        h["full_claims"] = record.claims
                        silver_count += 1
                    else:
                        if h.get("evidence_level") not in ("GOLD", "SILVER"):
                            h["evidence_level"] = "BRONZE"
                            bronze_count += 1

            # Element mapping (EXPLICIT/IMPLICIT/INHERENT)
            print(f"  [R{round_num}.3] Element mapping (explicit/implicit/inherent)...", flush=True)
            mappings = self._map_elements(current_claim.elements, all_hits[:8])

            # Relationship mapping (A→B, B→C, A+B+C arrangement) per MPEP
            print(f"  [R{round_num}.4] Relationship mapping (A→B, B→C, arrangement)...", flush=True)
            rel_mappings = self._map_relationships(current_claim.elements, all_hits[:8])

            # KILL_SEARCH
            print(f"  [R{round_num}.5] KILL_SEARCH (negative search)...", flush=True)
            kill_search = self._kill_search(current_claim, inventive_nucleus, tech_effect)

            # 5-attack destruction with EPO/USPTO structure
            print(f"  [R{round_num}.6] 5-attack destruction (EPO/USPTO structure)...", flush=True)
            attacks = self._construct_5_attacks(
                current_claim, mappings, rel_mappings, all_hits, kill_search, economic, tech_effect)

            # Check for fatal/strong attacks
            fatal_attacks = [a for a in attacks if a.attack_strength == "FATAL"]
            strong_attacks = [a for a in attacks if a.attack_strength in ("STRONG", "FATAL")]

            if not strong_attacks:
                print(f"  [R{round_num}] SURVIVED — no strong/fatal attacks", flush=True)
                rounds.append(ClaimRound(
                    round_num=round_num, claim_version_in=current_claim,
                    prior_art_search=search_result, element_mappings=mappings,
                    relationship_mappings=rel_mappings, kill_search=kill_search,
                    attacks=attacks, round_outcome="SURVIVED",
                ))
                break

            # Redesign
            if round_num < MAX_REDESIGN_ROUNDS:
                print(f"  [R{round_num}.7] Claim redesign...", flush=True)
                new_claim = self._redesign_claim(current_claim, attacks, inventive_nucleus, economic)
                if new_claim and new_claim.claim_text:
                    print(f"  [R{round_num}] REDESIGNED → CLAIM_{new_claim.version}", flush=True)
                    rounds.append(ClaimRound(
                        round_num=round_num, claim_version_in=current_claim,
                        prior_art_search=search_result, element_mappings=mappings,
                        relationship_mappings=rel_mappings, kill_search=kill_search,
                        attacks=attacks, redesign=new_claim, round_outcome="REDESIGNED",
                    ))
                    current_claim = new_claim
                else:
                    print(f"  [R{round_num}] KILLED — redesign failed", flush=True)
                    rounds.append(ClaimRound(
                        round_num=round_num, claim_version_in=current_claim,
                        prior_art_search=search_result, element_mappings=mappings,
                        relationship_mappings=rel_mappings, kill_search=kill_search,
                        attacks=attacks, round_outcome="KILLED",
                    ))
                    break
            else:
                print(f"  [R{round_num}] KILLED — max rounds exhausted", flush=True)
                rounds.append(ClaimRound(
                    round_num=round_num, claim_version_in=current_claim,
                    prior_art_search=search_result, element_mappings=mappings,
                    relationship_mappings=rel_mappings, kill_search=kill_search,
                    attacks=attacks, round_outcome="KILLED",
                ))
                break

        # Final status (per CEO Section 17)
        final_status, final_reason = self._assign_final_status(
            rounds, economic, manufacturing, tech_effect,
            gold_count, silver_count, total_hits)

        elapsed = time.time() - t0
        print(f"\n  → FINAL STATUS: {final_status}", flush=True)
        print(f"     Reason: {final_reason}", flush=True)
        print(f"     Sources: {sources_status}", flush=True)
        print(f"     Evidence: GOLD={gold_count}, SILVER={silver_count}, BRONZE={bronze_count}", flush=True)
        print(f"     GOLD patent IDs: {gold_patent_ids}", flush=True)
        print(f"     Elapsed: {elapsed:.1f}s, LLM calls: {self.llm._call_count}", flush=True)

        return EliteV3Result(
            invention_id=invention_id, device_class=device_class,
            inventive_nucleus=inventive_nucleus,
            claim_versions=[claim_v0] + [r.redesign for r in rounds if r.redesign],
            rounds=rounds, economic_value=economic, manufacturing=manufacturing,
            technical_effect=tech_effect, final_claim=current_claim.claim_text,
            final_status=final_status, final_adjudication_reason=final_reason,
            sources_status=sources_status, total_prior_art_hits=total_hits,
            gold_evidence_count=gold_count, silver_evidence_count=silver_count,
            bronze_evidence_count=bronze_count, gold_patent_ids=gold_patent_ids,
            timestamp=_now_utc(), llm_calls=self.llm._call_count,
            elapsed_seconds=round(elapsed, 1),
        )

    # ----------------------- CLAIM PARSING -----------------------
    def _parse_claim_elements(self, claim_text: str) -> List[ClaimElement]:
        sys_prompt = """You are a patent claim parser. Identify the structural elements AND their relationships.
Return JSON only. Format:
{"elements": [{"element_id": "A", "technical_feature": "...", "structural_requirement": "...", "functional_requirement": "...", "relationship": "how this element relates to others (e.g. 'sends signal to B', 'is mounted on C')", "parameter": "..."}]}
Element IDs are A, B, C, ... Limit to 8 elements max. The relationship field is CRITICAL for anticipation analysis."""
        user_prompt = f"Claim text:\n\n{claim_text[:2000]}"
        response, _ = self.llm.chat(sys_prompt, user_prompt, temperature=0.0, max_tokens=1000)
        try:
            clean = re.sub(r"^```(?:json)?\s*", "", response.strip())
            clean = re.sub(r"\s*```$", "", clean)
            data = json.loads(clean)
            return [ClaimElement(**e) for e in data.get("elements", [])[:8]]
        except (json.JSONDecodeError, TypeError):
            elements = []
            m = re.search(r'comprising[:\s]+(.+?)(?:;|wherein|hereby|$)', claim_text, re.IGNORECASE | re.DOTALL)
            if m:
                parts = re.split(r'[;,]', m.group(1))
                for i, p in enumerate(parts):
                    p = p.strip().rstrip('.')
                    if len(p) > 5:
                        elements.append(ClaimElement(element_id=chr(65+i), technical_feature=p[:200]))
            return elements[:8]

    # ----------------------- 4-SOURCE SEARCH (with honest LENS distinction) -----------------------
    def _extract_search_query(self, claim_text: str) -> str:
        cleaned = re.sub(r'^(A|An|The)\s+(method|apparatus|device|system|composition|article|coating|compound)\s+(for|comprising|including|of|having)', '', claim_text, flags=re.IGNORECASE)
        cleaned = re.sub(r'\b(comprising|wherein|configured to|adapted to|operably|coupled to|in fluid communication|characterized in that|characterized by)\b', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\b[A-Z]\)\s', ' ', cleaned)
        cleaned = re.sub(r'[;:()\[\]{}\"\'\\/&]', ' ', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned[:120] if cleaned else claim_text[:120]

    def _four_source_search(self, claim_text: str) -> Dict[str, Any]:
        """Query all 4 sources. Per CEO Section 4: LENS_SCHOLARLY ≠ LENS_PATENT."""
        query = self._extract_search_query(claim_text)
        results = search_all_sources(query, num_per_source=self.num_per_source)
        # Build honest result with LENS distinction
        output = {}
        for sid, r in results.items():
            # Per CEO Section 4: separate LENS_PATENT from LENS_SCHOLARLY
            if sid == "LENS_SCHOLARLY":
                # This is NPL (scholarly), NOT patent
                output["LENS_SCHOLARLY"] = {
                    "success": r.success,
                    "hit_count": len(r.hits),
                    "hits": [asdict(h) for h in r.hits],
                    "error": r.error,
                    "note": "NPL prior art only — NOT patent coverage",
                }
                # Also record LENS_PATENT as UNAVAILABLE
                output["LENS_PATENT"] = {
                    "success": False,
                    "hit_count": 0,
                    "error": "Lens patent API returns 401 (not subscribed)",
                    "note": "Lens patent API UNAVAILABLE — do not count as searched",
                }
            elif sid == "PATENT_BEAR":
                output["PATENT_BEAR"] = {
                    "success": r.success,
                    "hit_count": len(r.hits),
                    "hits": [asdict(h) for h in r.hits],
                    "error": r.error,
                    "note": "RATE_LIMITED — 20/20 monthly quota exhausted" if not r.success else "LIVE",
                }
            elif sid == "PATSNAP_EUREKA":
                output["PATSNAP_EUREKA"] = {
                    "success": r.success,
                    "hit_count": 0,
                    "error": r.error,
                    "note": "API_UNAVAILABLE — account tier insufficient",
                }
            else:
                output[sid] = {
                    "success": r.success,
                    "hit_count": len(r.hits),
                    "hits": [asdict(h) for h in r.hits],
                    "error": r.error,
                    "query_used": query,
                }
        return output

    def _collect_hits(self, search_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Collect all hits from successful sources."""
        hits = []
        for sid, sr in search_result.items():
            if sr.get("success"):
                for h in sr.get("hits", []):
                    h["source_id"] = sid
                    hits.append(h)
        return hits

    # ----------------------- ELEMENT MAPPING (with inherency firewall) -----------------------
    def _map_elements(self, elements: List[ClaimElement],
                      prior_art_hits: List[Dict[str, Any]]) -> List[ElementMapping]:
        """Map elements with EXPLICIT/IMPLICIT/INHERENT + inherency firewall."""
        if not elements or not prior_art_hits:
            return []

        sys_prompt = """You are a patent mapper. For each claim element, assess disclosure in the prior-art hit.

Disclosure types:
- EXPLICIT: the prior art directly states this feature
- IMPLICIT: the prior art necessarily implies this feature (not just "could")
- INHERENT: the feature necessarily results from the prior-art teaching. CRITICAL FIREWALL: "necessarily present" means it MUST occur, NOT "possible", "likely", "compatible", "could contain", or "would usually be". If you mark INHERENT, you MUST provide necessity_evidence (why it must occur) and technical_basis (scientific/technical reason).
- NOT_DISCLOSED: the prior art does not teach this feature
- UNCERTAIN: cannot determine from available text

FIREWALL: IMPLICIT_DISCLOSURE ≠ NOVELTY_FAILURE automatically.

Evidence levels:
- GOLD: actual claim/passage + verified metadata (publication date, priority date, family)
- SILVER: strong disclosure but one metadata gap
- BRONZE: semantic/topical relevance only
- NONE: no evidence

BRONZE evidence CANNOT create a novelty failure.

Return JSON only. Format:
{"mappings": [{"element_id": "A", "disclosure_type": "...", "prior_art_text": "exact quote from claims", "evidence_level": "...", "confidence": 0.0-1.0, "reasoning": "...", "necessity_evidence": "required if INHERENT", "technical_basis": "required if INHERENT"}]}"""

        all_mappings = []
        for hit in prior_art_hits[:6]:
            elements_str = json.dumps([asdict(e) for e in elements], indent=2)
            # Use full claims if available (GOLD), else abstract
            full_claims = (hit.get("raw_metadata") or {}).get("full_claims", [])
            if not full_claims and hit.get("full_claims"):
                full_claims = hit.get("full_claims")
            hit_str = json.dumps({
                "title": hit.get("title", ""),
                "snippet": hit.get("snippet", "")[:300],
                "abstract": (hit.get("raw_metadata") or {}).get("abstract", "")[:600] or hit.get("full_abstract", "")[:600],
                "patent_id": hit.get("patent_id"),
                "source_id": hit.get("source_id"),
                "evidence_level": hit.get("evidence_level", "BRONZE"),
                "full_claims": full_claims[:3] if full_claims else [],
                "publication_date": hit.get("publication_date"),
                "priority_date": hit.get("priority_date"),
                "family_id": hit.get("family_id"),
            }, indent=2)

            user_prompt = f"""Claim elements:
{elements_str}

Prior-art hit:
{hit_str}"""

            response, _ = self.llm.chat(sys_prompt, user_prompt, temperature=0.0, max_tokens=1500)
            try:
                clean = re.sub(r"^```(?:json)?\s*", "", response.strip())
                clean = re.sub(r"\s*```$", "", clean)
                data = json.loads(clean)
                # Handle both {"mappings": [...]} and [...] formats
                if isinstance(data, dict):
                    mappings_list = data.get("mappings", [])
                elif isinstance(data, list):
                    mappings_list = data
                else:
                    mappings_list = []
                for m in mappings_list:
                    if isinstance(m, dict):
                        all_mappings.append(ElementMapping(**m))
            except (json.JSONDecodeError, TypeError):
                for e in elements:
                    all_mappings.append(ElementMapping(
                        element_id=e.element_id, disclosure_type="UNCERTAIN",
                        prior_art_text="", evidence_level="BRONZE",
                        confidence=0.0, reasoning="LLM parse error",
                    ))
        return all_mappings

    # ----------------------- RELATIONSHIP MAPPING (per MPEP) -----------------------
    def _map_relationships(self, elements: List[ClaimElement],
                            prior_art_hits: List[Dict[str, Any]]) -> List[RelationshipMapping]:
        """Map relationships A→B, B→C, A+B+C arrangement per MPEP anticipation requirement.

        Per CEO Section 9: 'Does the reference disclose the required arrangement?'
        USPTO MPEP requires every claim element AND its required arrangement for anticipation.
        """
        if len(elements) < 2 or not prior_art_hits:
            return []

        # Build relationship pairs to check
        rel_pairs = []
        for i, e1 in enumerate(elements):
            for e2 in elements[i+1:]:
                rel_pairs.append(f"{e1.element_id}→{e2.element_id}")
        # Also check full arrangement
        if len(elements) >= 3:
            rel_pairs.append("+".join(e.element_id for e in elements))

        sys_prompt = """You are a patent relationship mapper. Per USPTO MPEP, anticipation requires EVERY claim element AND its required arrangement.

For each relationship (A→B, B→C, A+B+C arrangement), assess whether the prior art discloses:
1. The individual elements
2. The RELATIONSHIP between them (structural, functional, operational, causal)
3. The required ARRANGEMENT (how the elements are combined/positioned/connected)

Disclosure types:
- EXPLICIT: the prior art directly states this relationship
- IMPLICIT: necessarily implied
- INHERENT: necessarily results (requires necessity_evidence + technical_basis)
- NOT_DISCLOSED: the relationship is not taught
- UNCERTAIN

CRITICAL: A reference may disclose elements A and B individually but NOT the A→B relationship. In that case, the arrangement is NOT disclosed.

Return JSON only. Format:
{"relationships": [{"element_pair": "A→B", "relationship_type": "structural|functional|operational|causal", "prior_art_disclosure": "what the prior art says about this relationship", "disclosure_type": "...", "evidence_level": "...", "necessity_evidence": "if INHERENT", "technical_basis": "if INHERENT", "reasoning": "..."}]}"""

        all_rels = []
        for hit in prior_art_hits[:4]:
            full_claims = (hit.get("raw_metadata") or {}).get("full_claims", [])
            if not full_claims and hit.get("full_claims"):
                full_claims = hit.get("full_claims")
            elements_str = json.dumps([asdict(e) for e in elements], indent=2)
            hit_str = json.dumps({
                "title": hit.get("title", ""),
                "abstract": (hit.get("raw_metadata") or {}).get("abstract", "")[:600] or hit.get("full_abstract", "")[:600],
                "full_claims": full_claims[:3] if full_claims else [],
                "evidence_level": hit.get("evidence_level", "BRONZE"),
            }, indent=2)
            user_prompt = f"""Claim elements (with relationships):
{elements_str}

Relationship pairs to check: {rel_pairs}

Prior-art hit:
{hit_str}"""

            response, _ = self.llm.chat(sys_prompt, user_prompt, temperature=0.0, max_tokens=1500)
            try:
                clean = re.sub(r"^```(?:json)?\s*", "", response.strip())
                clean = re.sub(r"\s*```$", "", clean)
                data = json.loads(clean)
                if isinstance(data, dict):
                    rels_list = data.get("relationships", [])
                elif isinstance(data, list):
                    rels_list = data
                else:
                    rels_list = []
                for r in rels_list:
                    if isinstance(r, dict):
                        all_rels.append(RelationshipMapping(**r))
            except (json.JSONDecodeError, TypeError):
                pass
        return all_rels

    # ----------------------- KILL_SEARCH -----------------------
    def _kill_search(self, claim: ClaimVersion, nucleus: str,
                     tech_effect: TechnicalEffect) -> Dict[str, Any]:
        """Negative search: 'What evidence would destroy this claim?'"""
        sys_prompt = """You are a patent destruction adversary. Find evidence that would DESTROY this claim.

Ask: "What evidence would destroy this claim?"

Search for:
- closest prior art (same mechanism, same relationship)
- same operating condition
- same manufacturing method
- same technical effect
- same element combination (A+B, A+C, B+C, A+B+C)
- same relationship (A→B, B→C, A→B→C)

Do NOT ask "Is this novel?" — that biases toward confirmation.

Return JSON only. Format:
{
  "kill_hypotheses": [{"hypothesis": "...", "search_query": "...", "evidence_type": "patent|npl|both"}],
  "closest_prior_art_prediction": "...",
  "destruction_paths": ["novelty", "obviousness", "design_around", "enablement", "technical_effect"]
}"""
        user_prompt = f"""Claim (v{claim.version}):
{claim.claim_text[:1500]}

Inventive nucleus: {nucleus}
Technical effect: {tech_effect.technical_effect}
Distinguishing feature: {tech_effect.distinguishing_feature}"""
        response, _ = self.llm.chat(sys_prompt, user_prompt, temperature=0.0, max_tokens=1200)
        try:
            clean = re.sub(r"^```(?:json)?\s*", "", response.strip())
            clean = re.sub(r"\s*```$", "", clean)
            return json.loads(clean)
        except (json.JSONDecodeError, TypeError):
            return {"error": "parse failure"}

    # ----------------------- 5-ATTACK DESTRUCTION (EPO/USPTO structure) -----------------------
    def _construct_5_attacks(self, claim: ClaimVersion,
                              mappings: List[ElementMapping],
                              rel_mappings: List[RelationshipMapping],
                              all_hits: List[Dict[str, Any]],
                              kill_search: Dict[str, Any],
                              economic: EconomicValue,
                              tech_effect: TechnicalEffect) -> List[Attack]:
        """Construct 5 attacks with EPO/USPTO obviousness structure."""
        gold_silver_hits = [h for h in all_hits if h.get("evidence_level") in ("GOLD", "SILVER")]
        top_hits = (gold_silver_hits or all_hits)[:6]

        hits_str = json.dumps([{
            "title": h.get("title", "")[:150],
            "patent_id": h.get("patent_id"),
            "source_id": h.get("source_id"),
            "evidence_level": h.get("evidence_level", "BRONZE"),
            "full_claims": (h.get("full_claims") or [])[:2],
            "abstract": (h.get("raw_metadata") or {}).get("abstract", "")[:400] or h.get("full_abstract", "")[:400],
            "publication_date": h.get("publication_date"),
            "priority_date": h.get("priority_date"),
            "family_id": h.get("family_id"),
        } for h in top_hits], indent=2)

        mappings_str = json.dumps([asdict(m) for m in mappings[:12]], indent=2)
        rel_str = json.dumps([asdict(r) for r in rel_mappings[:10]], indent=2)

        sys_prompt = """You are a patent examiner adversary. Construct 5 attacks using EPO/USPTO structure.

QUALITY FIREWALLS:
- LLM output → NEVER becomes patent citation directly
- Snippet alone → NEVER creates novelty failure (need full claim text = GOLD)
- Similarity → NEVER equals anticipation
- Multiple references → NEVER creates 102 (only 103)
- TOPICAL_RELATED → NEVER equals NOVEL
- NO_MATCH_FOUND → NEVER equals PATENTABLE
- BRONZE evidence CANNOT create a novelty failure
- PASS → NEVER automatically equals ELITE

5 ATTACKS:

1. NOVELTY_102: ONE reference disclosing ALL elements AND the required arrangement.
   Per MPEP: anticipation requires every element AND its required arrangement.
   Multiple references CANNOT combine for 102.
   Requires GOLD evidence (full claim text).

2. OBVIOUSNESS_103 (EPO/USPTO structure — NO HINDSIGHT):
   - closest_prior_art: identify the single closest reference
   - objective_technical_problem: what problem does the invention solve?
   - differences: what are the differences from the closest prior art?
   - technical_effect: what technical effect do the differences provide?
   - motivation: WHY would a PHOSITA combine? (not just "could")
   - reasonable_expectation_of_success: would the PHOSITA expect success?
   - teaching_away: any teaching away from the combination?
   - could_question: COULD the skilled person do it? (technical capability)
   - would_question: WOULD the skilled person do it? (motivation/likelihood) — MANDATORY
   - no_hindsight_verified: confirm analysis does NOT use knowledge of the invention

   CRITICAL: First establish closest prior art, technical problem, and available teachings.
   THEN see whether they lead to the claimed solution.
   Do NOT mention the final invention before constructing the motivation analysis.

3. ENABLEMENT_112: Can a PHOSITA make and use without undue experimentation?

4. DESIGN_AROUND: Generate 5 workarounds:
   - remove_element
   - replace_element
   - move_element
   - change_material
   - change_control_logic
   For each: does the competitor still achieve the economic value?

5. TECHNICAL_EFFECT: Is the effect unexpected, synergistic, non-linear, or counterintuitive?
   Or merely the expected result?

Return JSON only. Format:
{
  "attacks": [
    {
      "attack_type": "NOVELTY_102",
      "attack_strength": "WEAK|MODERATE|STRONG|FATAL|NONE",
      "primary_reference": {...}|null,
      "rationale": "...",
      "elements_addressed": ["A","B"],
      "required_arrangement_disclosed": true|false,
      "arrangement_analysis": "does the reference disclose the required arrangement?",
      "can_survive": true|false,
      "survival_path": "...",
      "evidence_level": "GOLD|SILVER|BRONZE|NONE"
    },
    {
      "attack_type": "OBVIOUSNESS_103",
      "attack_strength": "...",
      "primary_reference": {...},
      "secondary_references": [...],
      "closest_prior_art": "which reference is closest?",
      "objective_technical_problem": "...",
      "differences": "...",
      "technical_effect": "...",
      "motivation": "WHY would PHOSITA combine?",
      "reasonable_expectation_of_success": "...",
      "teaching_away": "...",
      "could_question": "COULD the skilled person do it?",
      "would_question": "WOULD the skilled person do it?",
      "no_hindsight_verified": true|false,
      "can_survive": true|false,
      "survival_path": "...",
      "evidence_level": "..."
    },
    {"attack_type": "ENABLEMENT_112", ...},
    {"attack_type": "DESIGN_AROUND", "design_around_workarounds": [...], ...},
    {"attack_type": "TECHNICAL_EFFECT", "unexpected_effect": "...", ...}
  ]
}"""

        user_prompt = f"""Claim (v{claim.version}):
{claim.claim_text[:1500]}

Element mappings:
{mappings_str}

Relationship mappings:
{rel_str}

Prior-art hits (top {len(top_hits)}):
{hits_str}

KILL_SEARCH:
{json.dumps(kill_search, indent=2)[:800]}

Economic value: {economic.value_created}
Technical effect: {tech_effect.technical_effect}"""

        response, _ = self.llm.chat(sys_prompt, user_prompt, temperature=0.0, max_tokens=2500)
        attacks = []
        try:
            clean = re.sub(r"^```(?:json)?\s*", "", response.strip())
            clean = re.sub(r"\s*```$", "", clean)
            data = json.loads(clean)
            if isinstance(data, dict):
                attacks_list = data.get("attacks", [])
            elif isinstance(data, list):
                attacks_list = data
            else:
                attacks_list = []
            for a in attacks_list:
                if isinstance(a, dict):
                    attacks.append(Attack(**a))
        except (json.JSONDecodeError, TypeError):
            for at in ATTACK_TYPES:
                attacks.append(Attack(attack_type=at, attack_strength="NONE", rationale="Parse error"))

        seen = {a.attack_type for a in attacks}
        for at in ATTACK_TYPES:
            if at not in seen:
                attacks.append(Attack(attack_type=at, attack_strength="NONE", rationale="Not constructed"))
        return attacks

    # ----------------------- CLAIM REDESIGN -----------------------
    def _redesign_claim(self, current: ClaimVersion, attacks: List[Attack],
                        nucleus: str, economic: EconomicValue) -> Optional[ClaimVersion]:
        strong_attacks = [a for a in attacks if a.attack_strength in ("STRONG", "FATAL")]
        if not strong_attacks:
            return None

        sys_prompt = """You are a patent claim drafter. Redesign this claim to survive the attacks while:
1. Preserving the inventive nucleus (core technical insight)
2. Preserving the economic value (what the buyer pays for)
3. Adding specific technical features that distinguish over the prior art
4. NOT narrowing purely to manufacture artificial novelty
5. The change must preserve the actual invention's value

Return JSON only. Format:
{"new_claim_text": "...", "redesign_rationale": "...", "elements_changed": [...], "economic_value_preserved": true|false, "economic_value_note": "..."}
If CANNOT redesign honestly: {"new_claim_text": "", "redesign_rationale": "CANNOT_REDESIGN"}"""

        attacks_str = json.dumps([{
            "attack_type": a.attack_type, "attack_strength": a.attack_strength,
            "rationale": a.rationale[:300], "survival_path": a.survival_path[:200],
        } for a in strong_attacks], indent=2)

        user_prompt = f"""Current claim (v{current.version}):
{current.claim_text[:2000]}

Inventive nucleus: {nucleus}
Economic value: {economic.value_created}

Strong/fatal attacks:
{attacks_str}"""
        response, _ = self.llm.chat(sys_prompt, user_prompt, temperature=0.2, max_tokens=1500)
        try:
            clean = re.sub(r"^```(?:json)?\s*", "", response.strip())
            clean = re.sub(r"\s*```$", "", clean)
            data = json.loads(clean)
            if not data.get("new_claim_text"):
                return None
            new_text = data["new_claim_text"]
            new_claim = ClaimVersion(
                version=current.version + 1, claim_text=new_text,
                claim_hash=_sha256(new_text), created_at_utc=_now_utc(),
                redesign_rationale=data.get("redesign_rationale", ""),
            )
            new_claim.elements = self._parse_claim_elements(new_text)
            return new_claim
        except (json.JSONDecodeError, TypeError):
            return None

    # ----------------------- ECONOMIC VALUE -----------------------
    def _assess_economic_value(self, inv_id: str, device_class: str,
                                nucleus: str, claim: str) -> EconomicValue:
        sys_prompt = """You are a commercial IP strategist. Assess economic value honestly.
Never fabricate market size. If unknown, say HYPOTHESIS.
Return JSON only. Format:
{"customer_problem": "...", "economic_pain": "...", "current_cost": "... (EVIDENCE|INFERENCE|HYPOTHESIS)", "current_failure": "...", "value_created": "...", "who_pays": "...", "why_they_pay": "...", "adoption_barrier": "...", "value_creation_types": [...], "market_size_evidence_tag": "EVIDENCE|INFERENCE|HYPOTHESIS", "market_size_basis": "..."}"""
        user_prompt = f"Invention: {inv_id}\nDevice: {device_class}\nNucleus: {nucleus}\nClaim: {claim[:1500]}"
        response, _ = self.llm.chat(sys_prompt, user_prompt, temperature=0.0, max_tokens=1200)
        try:
            clean = re.sub(r"^```(?:json)?\s*", "", response.strip())
            clean = re.sub(r"\s*```$", "", clean)
            return EconomicValue(**json.loads(clean))
        except (json.JSONDecodeError, TypeError):
            return EconomicValue(customer_problem="UNKNOWN", economic_pain="UNKNOWN",
                current_cost="UNKNOWN (HYPOTHESIS)", current_failure="UNKNOWN",
                value_created="UNKNOWN", who_pays="UNKNOWN", why_they_pay="UNKNOWN",
                adoption_barrier="UNKNOWN", value_creation_types=[],
                market_size_evidence_tag="HYPOTHESIS", market_size_basis="UNKNOWN")

    # ----------------------- TECHNICAL EFFECT -----------------------
    def _classify_technical_effect(self, inv_id: str, nucleus: str, claim: str) -> TechnicalEffect:
        sys_prompt = """You are a patent technical effect analyst. Identify and classify the technical effect.
Return JSON only. Format:
{"problem": "...", "distinguishing_feature": "...", "mechanism": "...", "technical_effect": "...", "classification": "DOCUMENTED|INFERRED|HYPOTHESIZED", "unexpected": true|false, "synergistic": true|false, "non_linear": true|false, "counterintuitive": true|false}
Strong candidates preferentially have unexpected/synergistic/non-linear/counterintuitive effects.
If the effect is only hypothesized, the system will design an experiment to establish it."""
        user_prompt = f"Invention: {inv_id}\nNucleus: {nucleus}\nClaim: {claim[:1500]}"
        response, _ = self.llm.chat(sys_prompt, user_prompt, temperature=0.0, max_tokens=800)
        try:
            clean = re.sub(r"^```(?:json)?\s*", "", response.strip())
            clean = re.sub(r"\s*```$", "", clean)
            return TechnicalEffect(**json.loads(clean))
        except (json.JSONDecodeError, TypeError):
            return TechnicalEffect(problem="UNKNOWN", distinguishing_feature="UNKNOWN",
                mechanism="UNKNOWN", technical_effect="UNKNOWN", classification="HYPOTHESIZED")

    def _design_effect_experiment(self, te: TechnicalEffect, nucleus: str) -> str:
        """Per CEO Section 14: if effect is hypothesized, create EXPERIMENT_TO_ESTABLISH_EFFECT."""
        sys_prompt = f"""Design the cheapest decisive experiment to establish whether this hypothesized technical effect is real.

Technical effect: {te.technical_effect}
Mechanism: {te.mechanism}
Distinguishing feature: {te.distinguishing_feature}

Return a brief experiment description with: baseline, control, independent variable, dependent variable, measurement, success criterion, failure criterion, falsifier."""
        response, _ = self.llm.chat("You are an experimental designer.", sys_prompt, temperature=0.0, max_tokens=800)
        return response[:1000] if response else "UNKNOWN"

    # ----------------------- MANUFACTURING (with resolution_method) -----------------------
    def _assess_manufacturing(self, inv_id: str, device_class: str,
                               nucleus: str, claim: str) -> ManufacturingFeasibility:
        sys_prompt = """You are a manufacturing engineer. Assess manufacturing feasibility.
Per CEO directive: every UNKNOWN must have a resolution_method.
Return JSON only. Format:
{
  "manufacturing_process": "...",
  "materials": "...",
  "tooling": "...",
  "assembly": "...",
  "quality_control": "...",
  "throughput": "...",
  "yield_rate": "...",
  "supply_chain": "...",
  "regulatory_burden": "...",
  "status": "EVIDENCE|INFERENCE|HYPOTHESIS|SIMULATED_FEASIBLE|SIMULATED_RISK|EXPERIMENT_REQUIRED",
  "unknowns": [{"field": "yield_rate", "resolution_method": "prototype and measure", "estimated_cost": "low|medium|high"}]
}"""
        user_prompt = f"Invention: {inv_id}\nDevice: {device_class}\nNucleus: {nucleus}\nClaim: {claim[:1500]}"
        response, _ = self.llm.chat(sys_prompt, user_prompt, temperature=0.0, max_tokens=1200)
        try:
            clean = re.sub(r"^```(?:json)?\s*", "", response.strip())
            clean = re.sub(r"\s*```$", "", clean)
            data = json.loads(clean)
            unknowns = data.get("unknowns", [])
            return ManufacturingFeasibility(
                manufacturing_process=data.get("manufacturing_process", "UNKNOWN"),
                materials=data.get("materials", "UNKNOWN"),
                tooling=data.get("tooling", "UNKNOWN"),
                assembly=data.get("assembly", "UNKNOWN"),
                quality_control=data.get("quality_control", "UNKNOWN"),
                throughput=data.get("throughput", "UNKNOWN"),
                yield_rate=data.get("yield_rate", "UNKNOWN"),
                supply_chain=data.get("supply_chain", "UNKNOWN"),
                regulatory_burden=data.get("regulatory_burden", "UNKNOWN"),
                status=data.get("status", "EXPERIMENT_REQUIRED"),
                unknowns=unknowns,
            )
        except (json.JSONDecodeError, TypeError):
            return ManufacturingFeasibility(
                manufacturing_process="UNKNOWN", materials="UNKNOWN", tooling="UNKNOWN",
                assembly="UNKNOWN", quality_control="UNKNOWN", throughput="UNKNOWN",
                yield_rate="UNKNOWN", supply_chain="UNKNOWN", regulatory_burden="UNKNOWN",
                status="EXPERIMENT_REQUIRED",
                unknowns=[{"field": "all", "resolution_method": "manufacturing assessment required"}],
            )

    # ----------------------- FINAL STATUS (per CEO Section 17) -----------------------
    def _assign_final_status(self, rounds: List[ClaimRound],
                              economic: EconomicValue, manufacturing: ManufacturingFeasibility,
                              tech_effect: TechnicalEffect,
                              gold_count: int, silver_count: int,
                              total_hits: int) -> Tuple[str, str]:
        """Assign final status per CEO Section 17."""
        if not rounds:
            return "REJECT", "No rounds completed"

        last_round = rounds[-1]

        if last_round.round_outcome == "KILLED":
            return "REJECT", f"Killed after {len(rounds)} redesign rounds"
        if last_round.round_outcome == "INSUFFICIENT_EVIDENCE":
            return "PROMISING_INSUFFICIENT_EVIDENCE", f"Insufficient evidence ({total_hits} hits)"

        strong_attacks = sum(1 for a in last_round.attacks if a.attack_strength in ("STRONG", "FATAL"))
        if strong_attacks > 0:
            return "REJECT", f"{strong_attacks} strong/fatal attacks survived"

        # Per CEO Section 17: Do NOT use ELITE until GOLD evidence exists
        # OR a strong claim survives a fully sourced attack without material evidence gaps.
        # Use PROMISING_INSUFFICIENT_EVIDENCE for current state.
        # Use STRONG_CANDIDATE_FOR_ATTORNEY_REVIEW only when evidence coverage is materially sufficient.

        econ_ok = economic.market_size_evidence_tag in ("EVIDENCE", "INFERENCE")
        tech_ok = tech_effect.classification in ("DOCUMENTED", "INFERRED")
        mfg_ok = manufacturing.status not in ("EXPERIMENT_REQUIRED", "SIMULATED_RISK")
        has_unexpected = tech_effect.unexpected or tech_effect.synergistic or tech_effect.non_linear or tech_effect.counterintuitive

        if gold_count >= MIN_GOLD_EVIDENCE_FOR_STRONG and econ_ok and tech_ok and mfg_ok and has_unexpected:
            return "ELITE", f"GOLD evidence ({gold_count}), survived all attacks, unexpected technical effect, evidence-backed economic value"
        elif gold_count >= MIN_GOLD_EVIDENCE_FOR_STRONG and tech_ok and mfg_ok:
            return "STRONG_CANDIDATE_FOR_ATTORNEY_REVIEW", f"GOLD evidence ({gold_count}), survived attacks. Missing for ELITE: {self._missing_elite_factors(econ_ok, tech_ok, mfg_ok, has_unexpected)}"
        elif gold_count >= 1:
            return "PROMISING_INSUFFICIENT_EVIDENCE", f"Survived attacks but only {gold_count} GOLD evidence (need {MIN_GOLD_EVIDENCE_FOR_STRONG})"
        elif total_hits >= 3:
            return "PROMISING_INSUFFICIENT_EVIDENCE", f"Survived attacks but 0 GOLD evidence (only BRONZE/SILVER). Cannot validate without full patent claims."
        else:
            return "WEAK", f"Only {total_hits} prior-art hits"

    def _missing_elite_factors(self, econ: bool, tech: bool, mfg: bool, unexpected: bool) -> str:
        """List which ELITE factors are missing."""
        missing = []
        if not econ: missing.append("evidence-backed economic value")
        if not tech: missing.append("DOCUMENTED/INFERRED technical effect")
        if not mfg: missing.append("manufacturing plausibility")
        if not unexpected: missing.append("unexpected/synergistic effect")
        return ", ".join(missing) if missing else "none"
