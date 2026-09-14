"""
ELITE V2 — Deep Claim Attack Framework
=======================================

Implements the CEO directive for elite invention assessment with:
  - 4-source prior-art search (Google Patents, Lens, Patent Bear, PatSnap)
  - EXPLICIT/IMPLICIT/INHERENT/NOT_DISCLOSED/UNCERTAIN mapper
  - Relationship search (element combinations + mechanism + technical effect)
  - KILL_SEARCH (negative search — "what evidence would destroy this claim?")
  - 5-attack destruction: novelty_102, obviousness_103, enablement_112,
    design_around, technical_effect
  - Claim redesign loop (max 3 iterations: CLAIM_0 → CLAIM_1 → CLAIM_2)
  - GOLD/SILVER/BRONZE/NONE evidence quality levels
  - 5-workaround design-around generation
  - Manufacturing feasibility assessment
  - Technical effect classification (DOCUMENTED/INFERRED/HYPOTHESIZED)

QUALITY FIREWALLS (per CEO Section 23):
  - LLM output → NEVER becomes a patent citation directly
  - Snippet alone → NEVER creates a novelty failure
  - Similarity score → NEVER equals anticipation
  - Multiple references → NEVER creates a 102 failure (only 103)
  - TOPICAL_RELATED → NEVER equals NOVEL
  - NO_MATCH_FOUND → NEVER equals PATENTABLE
  - PASS → NEVER automatically equals ELITE

EVIDENCE LEVELS (per CEO Section 12):
  GOLD:   actual claim/passage + verified metadata
  SILVER: strong disclosure but one important metadata gap
  BRONZE: semantic/topical relevance only
  NONE:   no evidence

Only GOLD or sufficiently strong SILVER can drive claim destruction.
BRONZE cannot create a novelty failure.
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
    fetch_google_patent_full_claims, fetch_patent_bear_record,
    get_source_status, _now_utc, _sha256,
)


# ----------------------- CONSTANTS -----------------------
MAX_REDESIGN_ROUNDS = 3
MIN_HITS_FOR_VALID_SEARCH = 3

EVIDENCE_LEVELS = ["GOLD", "SILVER", "BRONZE", "NONE"]
DISCLOSURE_TYPES = ["EXPLICIT", "IMPLICIT", "INHERENT", "NOT_DISCLOSED", "UNCERTAIN"]
ATTACK_TYPES = ["NOVELTY_102", "OBVIOUSNESS_103", "ENABLEMENT_112",
                "DESIGN_AROUND", "TECHNICAL_EFFECT"]
TIERS = ["ELITE", "STRONG", "PROMISING", "WEAK", "REJECT"]

DESIGN_AROUND_STRATEGIES = [
    "remove_element",
    "replace_element",
    "move_element",
    "change_material",
    "change_control_logic",
]


# ----------------------- LLM CLIENT -----------------------
class LLMClient:
    """z-ai-web-dev-sdk chat completions with rate limiting and retry."""

    MIN_CALL_INTERVAL_S = 4.0
    _last_call_time = 0.0

    def __init__(self, timeout_s: int = 90, max_retries: int = 3):
        self.timeout_s = timeout_s
        self.max_retries = max_retries
        self._call_count = 0
        self._total_latency_ms = 0
        self._rate_limit_hits = 0
        self._failed_calls = 0

    def _throttle(self):
        now = time.time()
        elapsed = now - LLMClient._last_call_time
        if elapsed < LLMClient.MIN_CALL_INTERVAL_S:
            time.sleep(LLMClient.MIN_CALL_INTERVAL_S - elapsed)
        LLMClient._last_call_time = time.time()

    def chat(self, system_prompt: str, user_prompt: str,
             temperature: float = 0.0, max_tokens: int = 2500) -> Tuple[str, int]:
        js_code = f"""
import ZAI from 'z-ai-web-dev-sdk';
const z = await ZAI.create();
const t0 = Date.now();
try {{
  const r = await z.chat.completions.create({{
    messages: [
      {{role: 'system', content: {json.dumps(system_prompt)}}},
      {{role: 'user', content: {json.dumps(user_prompt)}}},
    ],
    temperature: {temperature},
    max_tokens: {max_tokens},
  }});
  const elapsed = Date.now() - t0;
  console.log(JSON.stringify({{
    content: r.choices?.[0]?.message?.content || '',
    elapsed_ms: elapsed,
  }}));
}} catch (e) {{
  const elapsed = Date.now() - t0;
  console.log(JSON.stringify({{
    error: e.message,
    elapsed_ms: elapsed,
  }}));
}}
"""
        tmp = Path(f"/tmp/elite_v2_llm_{os.getpid()}_{int(time.time()*1000)}_{self._call_count}.mjs")
        tmp.write_text(js_code)

        last_error = ""
        for attempt in range(self.max_retries + 1):
            self._throttle()
            try:
                result = subprocess.run(
                    ["bun", "run", str(tmp)],
                    capture_output=True, text=True, timeout=self.timeout_s,
                )
                if result.returncode != 0:
                    last_error = f"bun_rc={result.returncode}: {result.stderr[:200]}"
                    if attempt < self.max_retries:
                        time.sleep(5 * (2 ** attempt))
                        continue
                    return f"[LLM_ERROR: {last_error}]", 0

                lines = [l for l in result.stdout.strip().split("\n") if l.strip().startswith("{")]
                if not lines:
                    last_error = f"no output: {result.stdout[:200]}"
                    if attempt < self.max_retries:
                        time.sleep(5 * (2 ** attempt))
                        continue
                    return f"[LLM_NO_OUTPUT: {last_error}]", 0

                data = json.loads(lines[-1])

                if "error" in data and "429" in str(data.get("error", "")):
                    self._rate_limit_hits += 1
                    if attempt < self.max_retries:
                        wait = 15 * (2 ** attempt)
                        print(f"      [LLM] 429 (attempt {attempt+1}/{self.max_retries+1}), waiting {wait}s...", flush=True)
                        time.sleep(wait)
                        continue
                    return f"[429_RATE_LIMITED]", 0

                if "error" in data:
                    last_error = f"API_ERROR: {data['error'][:200]}"
                    if attempt < self.max_retries:
                        time.sleep(5 * (2 ** attempt))
                        continue
                    return f"[LLM_ERROR: {last_error}]", 0

                self._call_count += 1
                self._total_latency_ms += data.get("elapsed_ms", 0)
                tmp.unlink(missing_ok=True)
                return data.get("content", ""), data.get("elapsed_ms", 0)

            except subprocess.TimeoutExpired:
                last_error = f"TIMEOUT after {self.timeout_s}s"
                if attempt < self.max_retries:
                    time.sleep(5 * (2 ** attempt))
                    continue
                return f"[LLM_TIMEOUT]", 0
            except Exception as e:
                last_error = f"EXCEPTION: {str(e)[:200]}"
                if attempt < self.max_retries:
                    time.sleep(5 * (2 ** attempt))
                    continue
                return f"[LLM_EXCEPTION: {last_error}]", 0

        try: tmp.unlink(missing_ok=True)
        except: pass
        return f"[LLM_ERROR: {last_error}]", 0

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "call_count": self._call_count,
            "total_latency_ms": self._total_latency_ms,
            "rate_limit_hits": self._rate_limit_hits,
            "failed_calls": self._failed_calls,
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
class ElementMapping:
    """Maps a prior-art hit to a claim element with disclosure level."""
    element_id: str
    disclosure_type: str  # EXPLICIT | IMPLICIT | INHERENT | NOT_DISCLOSED | UNCERTAIN
    prior_art_text: str   # exact quote or close paraphrase
    evidence_level: str   # GOLD | SILVER | BRONZE | NONE
    confidence: float     # 0.0-1.0
    reasoning: str


@dataclass
class PriorArtRecord:
    """A prior-art hit with full metadata and evidence level."""
    source_id: str          # GOOGLE_PATENTS | LENS_SCHOLARLY | PATENT_BEAR | PATSNAP_EUREKA
    source_url: str
    retrieved_at_utc: str
    raw_payload_sha256: str
    title: str
    snippet: str
    assignee_or_authors: List[str]
    publication_date: Optional[str]
    patent_id: Optional[str] = None
    doi: Optional[str] = None
    evidence_level: str = "BRONZE"  # GOLD | SILVER | BRONZE | NONE
    full_claims: Optional[List[str]] = None  # if deep-fetched
    full_abstract: Optional[str] = None
    cpc: List[str] = field(default_factory=list)
    inventors: List[str] = field(default_factory=list)
    family_id: Optional[str] = None  # patent family normalization
    raw_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ClaimVersion:
    version: int  # 0, 1, 2
    claim_text: str
    claim_hash: str
    created_at_utc: str
    elements: List[ClaimElement] = field(default_factory=list)
    redesign_rationale: str = ""  # why this version was created


@dataclass
class Attack:
    attack_type: str  # NOVELTY_102 | OBVIOUSNESS_103 | ENABLEMENT_112 | DESIGN_AROUND | TECHNICAL_EFFECT
    attack_strength: str  # WEAK | MODERATE | STRONG | FATAL | NONE
    primary_reference: Optional[Dict[str, Any]] = None
    secondary_references: List[Dict[str, Any]] = field(default_factory=list)
    rationale: str = ""
    elements_addressed: List[str] = field(default_factory=list)
    motivation_to_combine: str = ""  # for 103
    reasonable_expectation_of_success: str = ""  # for 103
    teaching_away: str = ""  # for 103
    unexpected_effect: str = ""  # for 103
    design_around_workarounds: List[Dict[str, Any]] = field(default_factory=list)
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
    cost_reduction: str = ""
    failure_reduction: str = ""
    yield_increase: str = ""
    throughput_increase: str = ""
    energy_reduction: str = ""
    service_life_extension: str = ""
    clinical_outcome_improvement: str = ""
    regulatory_risk_reduction: str = ""
    revenue_opportunity: str = ""
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
    status: str  # EVIDENCE | INFERENCE | HYPOTHESIS | SIMULATED_FEASIBLE | SIMULATED_RISK | EXPERIMENT_REQUIRED


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


@dataclass
class ClaimRound:
    round_num: int
    claim_version_in: ClaimVersion
    prior_art_search: Dict[str, Any]
    element_mappings: List[ElementMapping]
    kill_search: Dict[str, Any]
    attacks: List[Attack]
    redesign: Optional[ClaimVersion] = None
    round_outcome: str = ""  # SURVIVED | REDESIGNED | KILLED | INSUFFICIENT_EVIDENCE


@dataclass
class EliteV2Result:
    invention_id: str
    device_class: str
    inventive_nucleus: str
    claim_versions: List[ClaimVersion]
    rounds: List[ClaimRound]
    economic_value: EconomicValue
    manufacturing: ManufacturingFeasibility
    technical_effect: TechnicalEffect
    final_claim: str
    final_tier: str
    final_adjudication_reason: str
    sources_live: List[str]
    sources_failed: List[str]
    total_prior_art_hits: int
    gold_evidence_count: int
    silver_evidence_count: int
    bronze_evidence_count: int
    timestamp: str
    llm_calls: int
    elapsed_seconds: float


# ----------------------- ELITE V2 AUDITOR -----------------------
class EliteV2Auditor:
    """Runs the full deep claim attack loop on one invention."""

    def __init__(self, llm: Optional[LLMClient] = None, num_per_source: int = 6):
        self.llm = llm or LLMClient()
        self.num_per_source = num_per_source

    def audit(self, invention_id: str, device_class: str,
              inventive_nucleus: str, initial_claim: str) -> EliteV2Result:
        t0 = time.time()
        print(f"\n{'='*70}", flush=True)
        print(f"  ELITE V2 DEEP AUDIT: {invention_id} ({device_class})", flush=True)
        print(f"{'='*70}", flush=True)

        # STEP 0: Parse initial claim
        print(f"  [0] Parsing CLAIM_0...", flush=True)
        claim_v0 = self._make_claim_version(0, initial_claim, "")
        claim_v0.elements = self._parse_claim_elements(initial_claim)
        print(f"      Parsed {len(claim_v0.elements)} elements", flush=True)

        # STEP 1: Economic value assessment
        print(f"  [1] Economic value assessment...", flush=True)
        economic = self._assess_economic_value(invention_id, device_class, inventive_nucleus, initial_claim)

        # STEP 2: Technical effect
        print(f"  [2] Technical effect classification...", flush=True)
        tech_effect = self._classify_technical_effect(invention_id, inventive_nucleus, initial_claim)

        # STEP 3: Manufacturing feasibility
        print(f"  [3] Manufacturing feasibility...", flush=True)
        manufacturing = self._assess_manufacturing(invention_id, device_class, inventive_nucleus, initial_claim)

        # STEP 4: Claim attack loop (max 3 rounds)
        rounds: List[ClaimRound] = []
        current_claim = claim_v0
        all_sources_live = set()
        all_sources_failed = set()
        total_hits = 0
        gold_count = 0
        silver_count = 0
        bronze_count = 0

        for round_num in range(1, MAX_REDESIGN_ROUNDS + 1):
            print(f"\n  --- Round {round_num}/{MAX_REDESIGN_ROUNDS} ---", flush=True)
            print(f"  CLAIM_{current_claim.version}: {current_claim.claim_text[:100]}...", flush=True)

            # 4-source search
            print(f"  [R{round_num}.1] 4-source prior-art search...", flush=True)
            search_result = self._four_source_search(current_claim.claim_text)
            for sid, sr in search_result.items():
                if sr.get("success"):
                    all_sources_live.add(sid)
                else:
                    all_sources_failed.add(sid)
                total_hits += sr.get("hit_count", 0)

            hits_this_round = sum(sr.get("hit_count", 0) for sr in search_result.values() if sr.get("success"))
            if hits_this_round < MIN_HITS_FOR_VALID_SEARCH:
                print(f"  [R{round_num}] INSUFFICIENT_EVIDENCE — only {hits_this_round} hits", flush=True)
                rounds.append(ClaimRound(
                    round_num=round_num,
                    claim_version_in=current_claim,
                    prior_art_search=search_result,
                    element_mappings=[],
                    kill_search={},
                    attacks=[],
                    round_outcome="INSUFFICIENT_EVIDENCE",
                ))
                break

            # Deep-fetch top hits for GOLD evidence
            print(f"  [R{round_num}.2] Deep-fetching top patents for GOLD evidence...", flush=True)
            all_hits = self._collect_hits(search_result)
            deep_fetched = self._deep_fetch_top_hits(all_hits[:3])
            # Upgrade evidence levels
            for h in all_hits:
                h["evidence_level"] = self._classify_evidence_level(h, deep_fetched)
                if h["evidence_level"] == "GOLD": gold_count += 1
                elif h["evidence_level"] == "SILVER": silver_count += 1
                elif h["evidence_level"] == "BRONZE": bronze_count += 1

            # Element mapping (EXPLICIT/IMPLICIT/INHERENT)
            print(f"  [R{round_num}.3] Element mapping (explicit/implicit/inherent)...", flush=True)
            mappings = self._map_elements(current_claim.elements, all_hits[:8])

            # KILL_SEARCH (negative search)
            print(f"  [R{round_num}.4] KILL_SEARCH (negative search)...", flush=True)
            kill_search = self._kill_search(current_claim, inventive_nucleus, tech_effect)

            # 5-attack destruction
            print(f"  [R{round_num}.5] 5-attack destruction test...", flush=True)
            attacks = self._construct_5_attacks(current_claim, mappings, all_hits, kill_search, economic, tech_effect)

            # Check for fatal attacks
            fatal_attacks = [a for a in attacks if a.attack_strength == "FATAL"]
            strong_attacks = [a for a in attacks if a.attack_strength in ("STRONG", "FATAL")]

            if not strong_attacks:
                print(f"  [R{round_num}] SURVIVED — no strong/fatal attacks", flush=True)
                rounds.append(ClaimRound(
                    round_num=round_num,
                    claim_version_in=current_claim,
                    prior_art_search=search_result,
                    element_mappings=mappings,
                    kill_search=kill_search,
                    attacks=attacks,
                    round_outcome="SURVIVED",
                ))
                break

            # Redesign if attacks found
            if round_num < MAX_REDESIGN_ROUNDS:
                print(f"  [R{round_num}.6] Claim redesign...", flush=True)
                new_claim = self._redesign_claim(current_claim, attacks, inventive_nucleus, economic)
                if new_claim and new_claim.claim_text:
                    print(f"  [R{round_num}] REDESIGNED → CLAIM_{new_claim.version}", flush=True)
                    rounds.append(ClaimRound(
                        round_num=round_num,
                        claim_version_in=current_claim,
                        prior_art_search=search_result,
                        element_mappings=mappings,
                        kill_search=kill_search,
                        attacks=attacks,
                        redesign=new_claim,
                        round_outcome="REDESIGNED",
                    ))
                    current_claim = new_claim
                else:
                    print(f"  [R{round_num}] KILLED — redesign failed", flush=True)
                    rounds.append(ClaimRound(
                        round_num=round_num,
                        claim_version_in=current_claim,
                        prior_art_search=search_result,
                        element_mappings=mappings,
                        kill_search=kill_search,
                        attacks=attacks,
                        round_outcome="KILLED",
                    ))
                    break
            else:
                print(f"  [R{round_num}] KILLED — max rounds exhausted", flush=True)
                rounds.append(ClaimRound(
                    round_num=round_num,
                    claim_version_in=current_claim,
                    prior_art_search=search_result,
                    element_mappings=mappings,
                    kill_search=kill_search,
                    attacks=attacks,
                    round_outcome="KILLED",
                ))
                break

        # FINAL TIER ASSIGNMENT
        final_tier, final_reason = self._assign_tier(
            rounds, economic, manufacturing, tech_effect, total_hits, gold_count)

        elapsed = time.time() - t0
        print(f"\n  → FINAL TIER: {final_tier}", flush=True)
        print(f"     Reason: {final_reason}", flush=True)
        print(f"     Rounds: {len(rounds)}", flush=True)
        print(f"     Sources live: {sorted(all_sources_live)}", flush=True)
        print(f"     Total hits: {total_hits} (GOLD={gold_count}, SILVER={silver_count}, BRONZE={bronze_count})", flush=True)
        print(f"     Elapsed: {elapsed:.1f}s, LLM calls: {self.llm._call_count}", flush=True)

        return EliteV2Result(
            invention_id=invention_id,
            device_class=device_class,
            inventive_nucleus=inventive_nucleus,
            claim_versions=[claim_v0] + [r.redesign for r in rounds if r.redesign],
            rounds=rounds,
            economic_value=economic,
            manufacturing=manufacturing,
            technical_effect=tech_effect,
            final_claim=current_claim.claim_text,
            final_tier=final_tier,
            final_adjudication_reason=final_reason,
            sources_live=sorted(all_sources_live),
            sources_failed=sorted(all_sources_failed),
            total_prior_art_hits=total_hits,
            gold_evidence_count=gold_count,
            silver_evidence_count=silver_count,
            bronze_evidence_count=bronze_count,
            timestamp=_now_utc(),
            llm_calls=self.llm._call_count,
            elapsed_seconds=round(elapsed, 1),
        )

    # ----------------------- CLAIM PARSING -----------------------
    def _make_claim_version(self, version: int, claim_text: str, rationale: str) -> ClaimVersion:
        return ClaimVersion(
            version=version,
            claim_text=claim_text,
            claim_hash=_sha256(claim_text),
            created_at_utc=_now_utc(),
            redesign_rationale=rationale,
        )

    def _parse_claim_elements(self, claim_text: str) -> List[ClaimElement]:
        sys_prompt = """You are a patent claim parser. Identify the structural elements of the given claim.
Return JSON only. Format:
{"elements": [{"element_id": "A", "technical_feature": "...", "structural_requirement": "...", "functional_requirement": "...", "relationship": "...", "parameter": "..."}]}
Element IDs are A, B, C, ... Limit to 8 elements max."""
        user_prompt = f"Claim text:\n\n{claim_text[:2000]}"
        response, _ = self.llm.chat(sys_prompt, user_prompt, temperature=0.0, max_tokens=1000)
        try:
            clean = re.sub(r"^```(?:json)?\s*", "", response.strip())
            clean = re.sub(r"\s*```$", "", clean)
            data = json.loads(clean)
            return [ClaimElement(**e) for e in data.get("elements", [])[:8]]
        except (json.JSONDecodeError, TypeError):
            # Fallback: simple regex parsing
            elements = []
            m = re.search(r'comprising[:\s]+(.+?)(?:;|wherein|hereby|$)', claim_text, re.IGNORECASE | re.DOTALL)
            if m:
                parts = re.split(r'[;,]', m.group(1))
                for i, p in enumerate(parts):
                    p = p.strip().rstrip('.')
                    if len(p) > 5:
                        elements.append(ClaimElement(element_id=chr(65+i), technical_feature=p[:200]))
            return elements[:8]

    # ----------------------- 4-SOURCE SEARCH -----------------------
    def _extract_search_query(self, claim_text: str) -> str:
        """Extract a clean search query from claim text."""
        cleaned = re.sub(r'^(A|An|The)\s+(method|apparatus|device|system|composition|article|coating|compound)\s+(for|comprising|including|of|having)', '', claim_text, flags=re.IGNORECASE)
        cleaned = re.sub(r'\b(comprising|wherein|configured to|adapted to|operably|coupled to|in fluid communication|characterized in that|characterized by)\b', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\b[A-Z]\)\s', ' ', cleaned)
        cleaned = re.sub(r'[;:()\[\]{}\"\'\\/&]', ' ', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned[:120] if cleaned else claim_text[:120]

    def _four_source_search(self, claim_text: str) -> Dict[str, Any]:
        """Query all 4 sources in parallel."""
        query = self._extract_search_query(claim_text)
        results = search_all_sources(query, num_per_source=self.num_per_source)
        return {
            sid: {
                "success": r.success,
                "hit_count": len(r.hits),
                "hits": [asdict(h) for h in r.hits],
                "error": r.error,
                "error_code": r.error_code,
                "query_used": query,
            } for sid, r in results.items()
        }

    def _collect_hits(self, search_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Collect all hits from successful sources."""
        hits = []
        for sid, sr in search_result.items():
            if sr.get("success"):
                for h in sr.get("hits", []):
                    h["source_id"] = sid
                    hits.append(h)
        return hits

    def _deep_fetch_top_hits(self, hits: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Deep-fetch full claims for top hits. Returns dict keyed by patent_id."""
        deep = {}
        for h in hits[:3]:
            pid = h.get("patent_id")
            if not pid: continue
            # Try Google Patents deep fetch first (no rate limit)
            print(f"       Deep-fetching {pid} via Google Patents...", flush=True)
            full = fetch_google_patent_full_claims(pid)
            if full.get("claims"):
                deep[pid] = full
                continue
            # Try Patent Bear (may be rate-limited)
            if h.get("source_id") == "PATENT_BEAR":
                print(f"       Deep-fetching {pid} via Patent Bear...", flush=True)
                pb_full = fetch_patent_bear_record(pid)
                if pb_full.get("claims") or pb_full.get("abstract"):
                    deep[pid] = pb_full
        return deep

    def _classify_evidence_level(self, hit: Dict[str, Any], deep_fetched: Dict[str, Any]) -> str:
        """Classify evidence quality: GOLD, SILVER, BRONZE, NONE.
        
        GOLD:   actual claim/passage + verified metadata
        SILVER: strong disclosure but one important metadata gap
        BRONZE: semantic/topical relevance only
        NONE:   no evidence
        """
        pid = hit.get("patent_id")
        has_deep = pid in deep_fetched if pid else False
        has_claims = bool(deep_fetched.get(pid, {}).get("claims")) if has_deep else False
        has_abstract = bool(hit.get("snippet") or hit.get("raw_metadata", {}).get("abstract"))
        has_assignee = bool(hit.get("assignee_or_authors"))
        has_pub_date = bool(hit.get("publication_date"))
        has_cpc = bool(hit.get("raw_metadata", {}).get("cpc"))

        if has_deep and has_claims and has_assignee and has_pub_date:
            return "GOLD"
        if has_abstract and has_assignee and has_pub_date and (has_cpc or has_deep):
            return "SILVER"
        if has_abstract:
            return "BRONZE"
        return "NONE"

    # ----------------------- ELEMENT MAPPING (EXPLICIT/IMPLICIT/INHERENT) -----------------------
    def _map_elements(self, elements: List[ClaimElement],
                      prior_art_hits: List[Dict[str, Any]]) -> List[ElementMapping]:
        """Map each element to prior-art disclosure with disclosure type."""
        if not elements or not prior_art_hits:
            return []

        sys_prompt = """You are a patent mapper. For each claim element, assess the disclosure level in the prior-art hit.

Disclosure types:
- EXPLICIT: the prior art directly states this feature
- IMPLICIT: the prior art necessarily implies this feature (not just "could")
- INHERENT: the feature necessarily results from the prior-art teaching (necessarily present, not merely probable)
- NOT_DISCLOSED: the prior art does not teach this feature
- UNCERTAIN: cannot determine from available text

CRITICAL FIREWALL:
- IMPLICIT_DISCLOSURE ≠ NOVELTY_FAILURE automatically
- INHERENT requires "necessarily present", NOT "possible" or "likely" or "compatible"
- Do NOT treat "could contain" or "may include" as inherent

Evidence levels:
- GOLD: actual claim/passage + verified metadata
- SILVER: strong disclosure but one metadata gap
- BRONZE: semantic/topical relevance only
- NONE: no evidence

BRONZE evidence CANNOT create a novelty failure.

Return JSON only. Format:
{"mappings": [{"element_id": "A", "disclosure_type": "EXPLICIT|IMPLICIT|INHERENT|NOT_DISCLOSED|UNCERTAIN", "prior_art_text": "exact quote", "evidence_level": "GOLD|SILVER|BRONZE|NONE", "confidence": 0.0-1.0, "reasoning": "..."}]}"""

        all_mappings = []
        for hit in prior_art_hits[:6]:
            elements_str = json.dumps([asdict(e) for e in elements], indent=2)
            hit_str = json.dumps({
                "title": hit.get("title", ""),
                "snippet": hit.get("snippet", "")[:500],
                "abstract": (hit.get("raw_metadata") or {}).get("abstract", "")[:800],
                "patent_id": hit.get("patent_id"),
                "source_id": hit.get("source_id"),
                "evidence_level": hit.get("evidence_level", "BRONZE"),
                "full_claims": (hit.get("raw_metadata") or {}).get("full_claims", [])[:3],
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
                for m in data.get("mappings", []):
                    all_mappings.append(ElementMapping(**m))
            except (json.JSONDecodeError, TypeError):
                # Fallback: mark all as UNCERTAIN
                for e in elements:
                    all_mappings.append(ElementMapping(
                        element_id=e.element_id,
                        disclosure_type="UNCERTAIN",
                        prior_art_text="",
                        evidence_level="BRONZE",
                        confidence=0.0,
                        reasoning="LLM parse error",
                    ))

        return all_mappings

    # ----------------------- KILL_SEARCH (NEGATIVE SEARCH) -----------------------
    def _kill_search(self, claim: ClaimVersion, nucleus: str,
                     tech_effect: TechnicalEffect) -> Dict[str, Any]:
        """Negative search: 'What evidence would destroy this claim?'"""
        sys_prompt = """You are a patent destruction adversary. Your job is to find evidence that would DESTROY this claim.

Ask: "What evidence would destroy this claim?"

Search specifically for:
- closest prior art (same mechanism, same relationship)
- same operating condition
- same manufacturing method
- same technical effect
- same element combination (A+B, A+C, B+C, A+B+C)
- same relationship (A→B, B→C, A→B→C)

Do NOT ask "Is this novel?" — that biases toward confirmation.
Instead ask "What would kill this?"

Return JSON only. Format:
{
  "kill_hypotheses": [
    {"hypothesis": "Prior art X teaches A+B combination", "search_query": "specific query to find this", "evidence_type": "patent|npl|both"}
  ],
  "closest_prior_art_prediction": "what the closest prior art likely teaches",
  "destruction_paths": ["novelty", "obviousness", "design_around", "enablement", "technical_effect"]
}"""

        user_prompt = f"""Claim (v{claim.version}):
{claim.claim_text[:1500]}

Inventive nucleus: {nucleus}

Technical effect: {tech_effect.technical_effect}
Distinguishing feature: {tech_effect.distinguishing_feature}
Mechanism: {tech_effect.mechanism}"""

        response, _ = self.llm.chat(sys_prompt, user_prompt, temperature=0.0, max_tokens=1500)
        try:
            clean = re.sub(r"^```(?:json)?\s*", "", response.strip())
            clean = re.sub(r"\s*```$", "", clean)
            return json.loads(clean)
        except (json.JSONDecodeError, TypeError):
            return {"error": "parse failure", "raw": response[:500]}

    # ----------------------- 5-ATTACK DESTRUCTION -----------------------
    def _construct_5_attacks(self, claim: ClaimVersion,
                              mappings: List[ElementMapping],
                              all_hits: List[Dict[str, Any]],
                              kill_search: Dict[str, Any],
                              economic: EconomicValue,
                              tech_effect: TechnicalEffect) -> List[Attack]:
        """Construct 5 attacks: novelty, obviousness, enablement, design-around, technical-effect."""
        # Prepare top hits with GOLD/SILVER evidence
        gold_silver_hits = [h for h in all_hits if h.get("evidence_level") in ("GOLD", "SILVER")]
        top_hits = (gold_silver_hits or all_hits)[:6]

        hits_str = json.dumps([{
            "title": h.get("title", "")[:150],
            "snippet": h.get("snippet", "")[:300],
            "patent_id": h.get("patent_id"),
            "source_id": h.get("source_id"),
            "evidence_level": h.get("evidence_level", "BRONZE"),
            "abstract": (h.get("raw_metadata") or {}).get("abstract", "")[:500],
            "claims": (h.get("raw_metadata") or {}).get("full_claims", [])[:2],
            "assignee": h.get("assignee_or_authors", []),
            "cpc": (h.get("raw_metadata") or {}).get("cpc", []),
        } for h in top_hits], indent=2)

        mappings_str = json.dumps([asdict(m) for m in mappings[:12]], indent=2)

        sys_prompt = """You are a patent examiner adversary. Construct 5 attacks to DESTROY this claim.

QUALITY FIREWALLS (CRITICAL):
- LLM output → NEVER becomes a patent citation directly
- Snippet alone → NEVER creates a novelty failure (need full claim text)
- Similarity score → NEVER equals anticipation
- Multiple references → NEVER creates a 102 failure (only 103)
- TOPICAL_RELATED → NEVER equals NOVEL
- NO_MATCH_FOUND → NEVER equals PATENTABLE
- BRONZE evidence CANNOT create a novelty failure

5 ATTACKS:
1. NOVELTY_102: ONE reference disclosing ALL elements. Requires GOLD evidence (full claim text). Multiple references CANNOT combine for 102.
2. OBVIOUSNESS_103: Multiple references + motivation_to_combine + reasonable_expectation_of_success. Must explain WHY a PHOSITA would combine. No hindsight. Check for teaching_away.
3. ENABLEMENT_112: Can a PHOSITA make and use without undue experimentation?
4. DESIGN_AROUND: Generate 5 competitor workarounds (remove_element, replace_element, move_element, change_material, change_control_logic). Does competitor still achieve economic value?
5. TECHNICAL_EFFECT: Is the technical effect unexpected, synergistic, non-linear, or counterintuitive? Or is it merely the expected result?

Be HONEST. If an attack cannot be constructed, say attack_strength="NONE" and explain what evidence is missing.
Do NOT assume survival just because you can't find an attack — say "INSUFFICIENT_EVIDENCE" if unsure.

Return JSON only. Format:
{
  "attacks": [
    {
      "attack_type": "NOVELTY_102",
      "attack_strength": "WEAK|MODERATE|STRONG|FATAL|NONE",
      "primary_reference": {...}|null,
      "rationale": "...",
      "elements_addressed": ["A","B"],
      "can_survive": true|false,
      "survival_path": "...",
      "evidence_level": "GOLD|SILVER|BRONZE|NONE"
    },
    {
      "attack_type": "OBVIOUSNESS_103",
      "attack_strength": "...",
      "primary_reference": {...},
      "secondary_references": [...],
      "rationale": "...",
      "motivation_to_combine": "WHY would PHOSITA combine?",
      "reasonable_expectation_of_success": "...",
      "teaching_away": "any teaching away?",
      "unexpected_effect": "...",
      "can_survive": true|false,
      "survival_path": "...",
      "evidence_level": "GOLD|SILVER|BRONZE|NONE"
    },
    {
      "attack_type": "ENABLEMENT_112",
      ...
    },
    {
      "attack_type": "DESIGN_AROUND",
      "attack_strength": "...",
      "design_around_workarounds": [
        {"strategy": "remove_element", "description": "...", "competitor_achieves_value": true|false},
        {"strategy": "replace_element", ...},
        {"strategy": "move_element", ...},
        {"strategy": "change_material", ...},
        {"strategy": "change_control_logic", ...}
      ],
      "can_survive": true|false,
      "survival_path": "how to refine claim",
      "evidence_level": "..."
    },
    {
      "attack_type": "TECHNICAL_EFFECT",
      "attack_strength": "...",
      "rationale": "...",
      "unexpected_effect": "...",
      "can_survive": true|false,
      "survival_path": "...",
      "evidence_level": "..."
    }
  ]
}"""

        user_prompt = f"""Claim (v{claim.version}):
{claim.claim_text[:1500]}

Element mappings:
{mappings_str}

Prior-art hits (top {len(top_hits)}):
{hits_str}

KILL_SEARCH hypotheses:
{json.dumps(kill_search, indent=2)[:1000]}

Economic value: {economic.value_created}
Technical effect: {tech_effect.technical_effect}
Technical effect classification: {tech_effect.classification}
Unexpected: {tech_effect.unexpected}, Synergistic: {tech_effect.synergistic}"""

        response, _ = self.llm.chat(sys_prompt, user_prompt, temperature=0.0, max_tokens=2500)
        attacks = []
        try:
            clean = re.sub(r"^```(?:json)?\s*", "", response.strip())
            clean = re.sub(r"\s*```$", "", clean)
            data = json.loads(clean)
            for a in data.get("attacks", []):
                attacks.append(Attack(**a))
        except (json.JSONDecodeError, TypeError) as e:
            # Fallback: empty attacks
            for at in ATTACK_TYPES:
                attacks.append(Attack(
                    attack_type=at,
                    attack_strength="NONE",
                    rationale=f"[PARSE_ERROR: {e}]",
                    can_survive=True,
                ))

        # Ensure all 5 attack types present
        seen = {a.attack_type for a in attacks}
        for at in ATTACK_TYPES:
            if at not in seen:
                attacks.append(Attack(attack_type=at, attack_strength="NONE", rationale="Not constructed"))
        return attacks

    # ----------------------- CLAIM REDESIGN -----------------------
    def _redesign_claim(self, current: ClaimVersion, attacks: List[Attack],
                        nucleus: str, economic: EconomicValue) -> Optional[ClaimVersion]:
        """Redesign the claim to survive attacks while preserving economic value."""
        strong_attacks = [a for a in attacks if a.attack_strength in ("STRONG", "FATAL")]
        if not strong_attacks:
            return None

        sys_prompt = """You are a patent claim drafter. Redesign this claim to survive the attacks while:
1. Preserving the inventive nucleus (the core technical insight)
2. Preserving the economic value (what the buyer pays for)
3. Adding specific technical features that distinguish over the prior art
4. Not narrowing purely to manufacture artificial novelty
5. The change must preserve the actual invention's value

Return JSON only. Format:
{
  "new_claim_text": "...",
  "redesign_rationale": "why this survives the attacks",
  "elements_changed": ["A", "B"],
  "economic_value_preserved": true|false,
  "economic_value_note": "how value is preserved"
}
If you CANNOT redesign honestly, return {"new_claim_text": "", "redesign_rationale": "CANNOT_REDESIGN"}."""

        attacks_str = json.dumps([{
            "attack_type": a.attack_type,
            "attack_strength": a.attack_strength,
            "rationale": a.rationale[:300],
            "survival_path": a.survival_path[:200],
            "primary_reference_title": (a.primary_reference or {}).get("title", ""),
        } for a in strong_attacks], indent=2)

        user_prompt = f"""Current claim (v{current.version}):
{current.claim_text[:2000]}

Inventive nucleus: {nucleus}
Economic value: {economic.value_created}

Strong/fatal attacks to survive:
{attacks_str}"""

        response, _ = self.llm.chat(sys_prompt, user_prompt, temperature=0.2, max_tokens=1500)
        try:
            clean = re.sub(r"^```(?:json)?\s*", "", response.strip())
            clean = re.sub(r"\s*```$", "", clean)
            data = json.loads(clean)
            if not data.get("new_claim_text"):
                return None
            new_text = data["new_claim_text"]
            new_claim = self._make_claim_version(current.version + 1, new_text, data.get("redesign_rationale", ""))
            new_claim.elements = self._parse_claim_elements(new_text)
            return new_claim
        except (json.JSONDecodeError, TypeError):
            return None

    # ----------------------- ECONOMIC VALUE -----------------------
    def _assess_economic_value(self, inv_id: str, device_class: str,
                                nucleus: str, claim: str) -> EconomicValue:
        sys_prompt = """You are a commercial IP strategist. Assess the economic value of this invention.
Be HONEST. Never fabricate market size. If unknown, say HYPOTHESIS.
Return JSON only. Format:
{
  "customer_problem": "...",
  "economic_pain": "...",
  "current_cost": "... (EVIDENCE|INFERENCE|HYPOTHESIS)",
  "current_failure": "...",
  "value_created": "...",
  "who_pays": "...",
  "why_they_pay": "...",
  "adoption_barrier": "...",
  "value_creation_types": ["COST_REDUCTION", ...],
  "cost_reduction": "...|UNKNOWN",
  "failure_reduction": "...|UNKNOWN",
  "yield_increase": "...|UNKNOWN",
  "throughput_increase": "...|UNKNOWN",
  "energy_reduction": "...|UNKNOWN",
  "service_life_extension": "...|UNKNOWN",
  "clinical_outcome_improvement": "...|UNKNOWN",
  "regulatory_risk_reduction": "...|UNKNOWN",
  "revenue_opportunity": "...|UNKNOWN",
  "market_size_evidence_tag": "EVIDENCE|INFERENCE|HYPOTHESIS",
  "market_size_basis": "explain or UNKNOWN"
}"""
        user_prompt = f"Invention: {inv_id}\nDevice: {device_class}\nNucleus: {nucleus}\nClaim: {claim[:1500]}"
        response, _ = self.llm.chat(sys_prompt, user_prompt, temperature=0.0, max_tokens=1500)
        try:
            clean = re.sub(r"^```(?:json)?\s*", "", response.strip())
            clean = re.sub(r"\s*```$", "", clean)
            return EconomicValue(**json.loads(clean))
        except (json.JSONDecodeError, TypeError) as e:
            return EconomicValue(
                customer_problem=f"[PARSE_ERROR: {e}]", economic_pain="UNKNOWN",
                current_cost="UNKNOWN (HYPOTHESIS)", current_failure="UNKNOWN",
                value_created="UNKNOWN", who_pays="UNKNOWN", why_they_pay="UNKNOWN",
                adoption_barrier="UNKNOWN", value_creation_types=[],
                market_size_evidence_tag="HYPOTHESIS", market_size_basis="UNKNOWN",
            )

    # ----------------------- TECHNICAL EFFECT -----------------------
    def _classify_technical_effect(self, inv_id: str, nucleus: str,
                                    claim: str) -> TechnicalEffect:
        sys_prompt = """You are a patent technical effect analyst. Identify and classify the technical effect.
Return JSON only. Format:
{
  "problem": "...",
  "distinguishing_feature": "...",
  "mechanism": "...",
  "technical_effect": "...",
  "classification": "DOCUMENTED|INFERRED|HYPOTHESIZED",
  "unexpected": true|false,
  "synergistic": true|false,
  "non_linear": true|false,
  "counterintuitive": true|false
}
Strong candidates should preferentially have unexpected/synergistic/non-linear/counterintuitive effects."""
        user_prompt = f"Invention: {inv_id}\nNucleus: {nucleus}\nClaim: {claim[:1500]}"
        response, _ = self.llm.chat(sys_prompt, user_prompt, temperature=0.0, max_tokens=800)
        try:
            clean = re.sub(r"^```(?:json)?\s*", "", response.strip())
            clean = re.sub(r"\s*```$", "", clean)
            return TechnicalEffect(**json.loads(clean))
        except (json.JSONDecodeError, TypeError):
            return TechnicalEffect(
                problem="UNKNOWN", distinguishing_feature="UNKNOWN",
                mechanism="UNKNOWN", technical_effect="UNKNOWN",
                classification="HYPOTHESIZED",
            )

    # ----------------------- MANUFACTURING -----------------------
    def _assess_manufacturing(self, inv_id: str, device_class: str,
                               nucleus: str, claim: str) -> ManufacturingFeasibility:
        sys_prompt = """You are a manufacturing engineer. Assess manufacturing feasibility.
No unbounded UNKNOWN for an elite candidate — classify as SIMULATED_FEASIBLE, SIMULATED_RISK, or EXPERIMENT_REQUIRED.
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
  "status": "EVIDENCE|INFERENCE|HYPOTHESIS|SIMULATED_FEASIBLE|SIMULATED_RISK|EXPERIMENT_REQUIRED"
}"""
        user_prompt = f"Invention: {inv_id}\nDevice: {device_class}\nNucleus: {nucleus}\nClaim: {claim[:1500]}"
        response, _ = self.llm.chat(sys_prompt, user_prompt, temperature=0.0, max_tokens=1000)
        try:
            clean = re.sub(r"^```(?:json)?\s*", "", response.strip())
            clean = re.sub(r"\s*```$", "", clean)
            return ManufacturingFeasibility(**json.loads(clean))
        except (json.JSONDecodeError, TypeError):
            return ManufacturingFeasibility(
                manufacturing_process="UNKNOWN", materials="UNKNOWN", tooling="UNKNOWN",
                assembly="UNKNOWN", quality_control="UNKNOWN", throughput="UNKNOWN",
                yield_rate="UNKNOWN", supply_chain="UNKNOWN", regulatory_burden="UNKNOWN",
                status="EXPERIMENT_REQUIRED",
            )

    # ----------------------- TIER ASSIGNMENT -----------------------
    def _assign_tier(self, rounds: List[ClaimRound],
                     economic: EconomicValue, manufacturing: ManufacturingFeasibility,
                     tech_effect: TechnicalEffect, total_hits: int,
                     gold_count: int) -> Tuple[str, str]:
        """Assign final tier based on all evidence."""
        if not rounds:
            return "REJECT", "No rounds completed"

        last_round = rounds[-1]

        # Check if survived
        if last_round.round_outcome != "SURVIVED":
            if last_round.round_outcome == "KILLED":
                return "REJECT", f"Killed after {len(rounds)} redesign rounds"
            if last_round.round_outcome == "INSUFFICIENT_EVIDENCE":
                return "WEAK", f"Insufficient evidence ({total_hits} hits)"

        # Count strong attacks survived
        strong_attacks = sum(1 for a in last_round.attacks if a.attack_strength in ("STRONG", "FATAL"))
        if strong_attacks > 0:
            return "REJECT", f"{strong_attacks} strong/fatal attacks survived"

        # ELITE requires:
        # - high economic value (EVIDENCE or INFERENCE, not HYPOTHESIS)
        # - strong technical differentiation (DOCUMENTED or INFERRED tech effect)
        # - manufacturing plausibility (not EXPERIMENT_REQUIRED)
        # - strong claim distinction (survived 5 attacks)
        # - manageable design-around risk

        econ_ok = economic.market_size_evidence_tag in ("EVIDENCE", "INFERENCE")
        tech_ok = tech_effect.classification in ("DOCUMENTED", "INFERRED")
        mfg_ok = manufacturing.status not in ("EXPERIMENT_REQUIRED", "SIMULATED_RISK")
        has_unexpected = tech_effect.unexpected or tech_effect.synergistic or tech_effect.non_linear or tech_effect.counterintuitive
        enough_gold = gold_count >= 2

        if econ_ok and tech_ok and mfg_ok and has_unexpected and enough_gold:
            return "ELITE", f"Survived 5 attacks, {gold_count} GOLD evidence, unexpected technical effect, evidence-backed economic value"
        elif tech_ok and mfg_ok and enough_gold:
            return "STRONG", f"Survived 5 attacks, {gold_count} GOLD evidence, but missing: {self._missing_elite_factors(econ_ok, tech_ok, mfg_ok, has_unexpected, enough_gold)}"
        elif total_hits >= MIN_HITS_FOR_VALID_SEARCH:
            return "PROMISING", f"Survived attacks but insufficient GOLD evidence ({gold_count})"
        else:
            return "WEAK", f"Only {total_hits} prior-art hits"

    def _missing_elite_factors(self, econ, tech, mfg, unexpected, gold):
        missing = []
        if not econ: missing.append("evidence-backed economic value")
        if not tech: missing.append("DOCUMENTED/INFERRED technical effect")
        if not mfg: missing.append("manufacturing plausibility")
        if not unexpected: missing.append("unexpected/synergistic effect")
        if not gold: missing.append("GOLD evidence (>=2)")
        return ", ".join(missing)
