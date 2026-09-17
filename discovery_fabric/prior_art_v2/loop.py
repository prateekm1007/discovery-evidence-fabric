"""
Autonomous Patentability Loop V2

Implements the full evidence → claim → prior-art → attack → redesign → re-search →
adjudication cycle with three independent prior-art sources and a three-agent
structure (Searcher / Mapper / Adversary).

DESIGN (per CEO directive):
  - Searcher: queries Google Patents + Lens Scholarly + PatSnap in parallel
  - Mapper:   maps prior-art hits to claim elements (element-by-element)
  - Adversary: attempts to construct 102 (novelty) or 103 (obviousness) rejections
  - Redesigner: if attack succeeds, modifies the claim to distinguish over prior art
  - Adjudicator: after MAX_ROUNDS (default 3), decides:
        PASS                    — claim survives all attacks
        INSUFFICIENT_EVIDENCE   — prior-art searches returned too few hits to decide
        KILL                    — claim cannot be saved after 3 redesigns

CONTRACT (V2 three-state):
  Per the prior_art_forensic V2 contract, the loop NEVER returns a binary KILL on
  the basis of insufficient evidence. INSUFFICIENT_EVIDENCE is a separate state.

LLM:
  Uses z-ai-web-dev-sdk chat completions for mapper/adversary/redesigner reasoning.
  Falls back to deterministic rule-based logic if LLM is unavailable.

PROVENANCE:
  Every prior-art hit includes source_id, source_url, retrieved_at_utc, raw_payload_sha256.
  Every claim version is hashed and timestamped.
  Every adversary attack includes the specific prior-art hit(s) used.
"""
from __future__ import annotations
import os, sys, json, time, asyncio, hashlib, re, subprocess
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add parent dirs to path for imports
THIS_DIR = Path(__file__).resolve().parent
REPO_ROOT = THIS_DIR.parent.parent  # discovery-evidence-fabric/
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.prior_art_v2.sources import (
    PriorArtHit, SourceQueryResult,
    search_all_sources, fetch_google_patent_full_claims,
    get_source_status, _now_utc, _sha256,
)


# ----------------------- CONSTANTS -----------------------
MAX_ROUNDS = 3
MIN_HITS_PER_CLAIM = 3  # below this → INSUFFICIENT_EVIDENCE
LLM_TIMEOUT_S = 60
LLM_MODEL = "glm-4.6"  # default z-ai model

# ----------------------- DATA SCHEMAS -----------------------
@dataclass
class ClaimVersion:
    """A single version of a claim, tracked through redesign rounds."""
    version: int                            # 0 = initial, 1 = after 1st redesign, etc.
    claim_text: str
    claim_hash: str                         # sha256 of claim_text
    created_at_utc: str
    elements: List[Dict[str, str]] = field(default_factory=list)  # parsed elements


@dataclass
class PriorArtMapping:
    """One prior-art hit mapped to claim elements."""
    prior_art: Dict[str, Any]               # serialized PriorArtHit
    mapped_elements: List[Dict[str, Any]]   # [{claim_element_id, prior_art_text, mapping_confidence}]


@dataclass
class AdversaryAttack:
    """An attack on a claim version."""
    attack_id: str                          # e.g. "ATTACK_R0_001"
    claim_version: int
    attack_type: str                        # NOVELTY_102 | OBVIOUSNESS_103 | ENABLEMENT_112
    attack_strength: str                    # WEAK | MODERATE | STRONG | FATAL
    primary_reference: Dict[str, Any]       # the main prior-art hit
    secondary_references: List[Dict[str, Any]] = field(default_factory=list)
    rationale: str = ""
    anticipated_outcome: str = ""           # what the attack predicts the examiner will say


@dataclass
class Redesign:
    """A claim redesign in response to an attack."""
    new_claim_text: str
    new_claim_hash: str
    change_summary: str
    rationale: str
    new_elements: List[Dict[str, str]] = field(default_factory=list)
    distinguished_over: List[str] = field(default_factory=list)  # attack_ids addressed


@dataclass
class LoopRound:
    """One round of search → map → attack → (possibly redesign)."""
    round_num: int
    claim_version_in: ClaimVersion
    searcher_result: Dict[str, Any]         # source_id -> {success, hit_count, hits, error}
    mapper_result: List[PriorArtMapping]
    adversary_attacks: List[AdversaryAttack]
    redesign: Optional[Redesign] = None     # None if claim survived all attacks
    round_outcome: str = ""                 # SURVIVED | REDESIGNED | KILLED | INSUFFICIENT_EVIDENCE


@dataclass
class LoopFinalResult:
    """Final adjudication for one invention."""
    invention_id: str
    device_class: str
    inventive_nucleus: str
    initial_claim: str
    final_claim: str
    rounds: List[Dict[str, Any]]            # serialized LoopRound list
    final_adjudication: str                 # PASS | INSUFFICIENT_EVIDENCE | KILL
    final_adjudication_reason: str
    total_prior_art_hits: int
    sources_used: List[str]
    sources_live: List[str]
    sources_failed: List[str]
    timestamp: str


# ----------------------- LLM CLIENT (z-ai SDK) -----------------------
class LLMClient:
    """Wraps the z-ai-web-dev-sdk chat completions as a sync callable.

    Implements rate-limit handling: on HTTP 429 (Too Many Requests), waits
    and retries with exponential backoff (max 3 retries).
    """

    # Class-level rate limiter: ensure at least MIN_CALL_INTERVAL_S between calls
    MIN_CALL_INTERVAL_S = 4.0  # 15 calls/minute max (z-ai limit appears to be ~20/min)
    _last_call_time = 0.0

    def __init__(self, model: str = LLM_MODEL, timeout_s: int = LLM_TIMEOUT_S,
                 max_retries: int = 3):
        self.model = model
        self.timeout_s = timeout_s
        self.max_retries = max_retries
        self._call_count = 0
        self._total_latency_ms = 0
        self._rate_limit_hits = 0
        self._failed_calls = 0

    def _throttle(self):
        """Ensure we don't exceed the rate limit by waiting if needed."""
        now = time.time()
        elapsed = now - LLMClient._last_call_time
        if elapsed < LLMClient.MIN_CALL_INTERVAL_S:
            wait = LLMClient.MIN_CALL_INTERVAL_S - elapsed
            time.sleep(wait)
        LLMClient._last_call_time = time.time()

    def chat(self, system_prompt: str, user_prompt: str, temperature: float = 0.0,
             max_tokens: int = 1200) -> Tuple[str, int]:
        """
        Synchronous chat call. Returns (response_text, latency_ms).
        Uses a Node subprocess because z-ai-web-dev-sdk is a Bun/Node SDK.
        Retries on 429 with exponential backoff.
        """
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
        tmp = Path(f"/tmp/llm_call_{os.getpid()}_{int(time.time()*1000)}_{self._call_count}.mjs")
        tmp.write_text(js_code)

        last_error = ""
        for attempt in range(self.max_retries + 1):
            # Throttle before each call
            self._throttle()

            try:
                result = subprocess.run(
                    ["bun", "run", str(tmp)],
                    capture_output=True, text=True, timeout=self.timeout_s,
                )
                if result.returncode != 0:
                    last_error = f"bun_returncode={result.returncode}: {result.stderr[:200]}"
                    self._failed_calls += 1
                    if attempt < self.max_retries:
                        wait = 5 * (2 ** attempt)  # 5s, 10s, 20s
                        print(f"      [LLM] bun failed (attempt {attempt+1}/{self.max_retries+1}), waiting {wait}s...", flush=True)
                        time.sleep(wait)
                        continue
                    return f"[LLM_ERROR: {last_error}]", 0

                # Parse stdout
                lines = [l for l in result.stdout.strip().split("\n") if l.strip().startswith("{")]
                if not lines:
                    last_error = f"no JSON output: {result.stdout[:200]}"
                    self._failed_calls += 1
                    if attempt < self.max_retries:
                        wait = 5 * (2 ** attempt)
                        print(f"      [LLM] no output (attempt {attempt+1}), waiting {wait}s...", flush=True)
                        time.sleep(wait)
                        continue
                    return f"[LLM_NO_OUTPUT: {last_error}]", 0

                data = json.loads(lines[-1])

                # Check for 429 rate limit
                if "error" in data and "429" in str(data.get("error", "")):
                    self._rate_limit_hits += 1
                    if attempt < self.max_retries:
                        wait = 15 * (2 ** attempt)  # 15s, 30s, 60s
                        print(f"      [LLM] 429 rate limited (attempt {attempt+1}/{self.max_retries+1}), waiting {wait}s...", flush=True)
                        time.sleep(wait)
                        continue
                    last_error = f"429_RATE_LIMITED: {data['error'][:200]}"
                    self._failed_calls += 1
                    return f"[LLM_ERROR: {last_error}]", 0

                # Check for other errors
                if "error" in data:
                    last_error = f"API_ERROR: {data['error'][:200]}"
                    self._failed_calls += 1
                    if attempt < self.max_retries:
                        wait = 5 * (2 ** attempt)
                        print(f"      [LLM] API error (attempt {attempt+1}), waiting {wait}s...", flush=True)
                        time.sleep(wait)
                        continue
                    return f"[LLM_ERROR: {last_error}]", 0

                # Success
                self._call_count += 1
                self._total_latency_ms += data.get("elapsed_ms", 0)
                tmp.unlink(missing_ok=True)
                return data.get("content", ""), data.get("elapsed_ms", 0)

            except subprocess.TimeoutExpired:
                last_error = f"TIMEOUT after {self.timeout_s}s"
                self._failed_calls += 1
                if attempt < self.max_retries:
                    wait = 5 * (2 ** attempt)
                    print(f"      [LLM] timeout (attempt {attempt+1}), waiting {wait}s...", flush=True)
                    time.sleep(wait)
                    continue
                return f"[LLM_TIMEOUT after {self.timeout_s}s]", 0
            except Exception as e:
                last_error = f"EXCEPTION: {str(e)[:200]}"
                self._failed_calls += 1
                if attempt < self.max_retries:
                    wait = 5 * (2 ** attempt)
                    print(f"      [LLM] exception (attempt {attempt+1}), waiting {wait}s...", flush=True)
                    time.sleep(wait)
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
            "avg_latency_ms": (self._total_latency_ms / self._call_count) if self._call_count else 0,
            "rate_limit_hits": self._rate_limit_hits,
            "failed_calls": self._failed_calls,
        }


# ----------------------- SEARCHER -----------------------
class Searcher:
    """Queries all prior-art sources in parallel for a given claim."""

    def __init__(self, num_per_source: int = 8, deep_fetch_top_n: int = 3):
        self.num_per_source = num_per_source
        self.deep_fetch_top_n = deep_fetch_top_n

    def search(self, claim: ClaimVersion) -> Dict[str, Any]:
        """Query all sources with the claim text and return unified results."""
        # Build a search query: use the claim text (truncated for query length)
        query = claim.claim_text[:300]

        print(f"    [Searcher] Querying 3 sources for claim v{claim.version}...", flush=True)
        results = search_all_sources(query, num_per_source=self.num_per_source)

        # Deep-fetch full claims for top Google Patents hits
        gp_result = results.get("GOOGLE_PATENTS")
        deep_fetched = []
        if gp_result and gp_result.success:
            for hit in gp_result.hits[:self.deep_fetch_top_n]:
                if hit.patent_id:
                    print(f"    [Searcher] Deep-fetching full claims for {hit.patent_id}...", flush=True)
                    full = fetch_google_patent_full_claims(hit.patent_id)
                    if "claims" in full and full["claims"]:
                        deep_fetched.append(full)

        # Serialize for return
        serialized = {}
        total_hits = 0
        for sid, r in results.items():
            hits_data = [asdict(h) for h in r.hits]
            serialized[sid] = {
                "success": r.success,
                "latency_ms": r.latency_ms,
                "hit_count": len(r.hits),
                "hits": hits_data,
                "error": r.error,
                "error_code": r.error_code,
            }
            total_hits += len(r.hits)

        serialized["_deep_fetched"] = deep_fetched
        serialized["_total_hits"] = total_hits
        serialized["_query"] = query
        return serialized


# ----------------------- MAPPER -----------------------
class Mapper:
    """Maps prior-art hits to claim elements using LLM."""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def parse_claim_elements(self, claim_text: str) -> List[Dict[str, str]]:
        """Parse a claim into structural elements (preamble, elements, relationships)."""
        # Try LLM first
        sys_prompt = """You are a patent claim parser. Identify the structural elements of the given claim.
Return JSON only — no markdown, no prose. Format:
{
  "elements": [
    {"element_id": "A", "technical_feature": "...", "structural_requirement": "...", "functional_requirement": "...", "parameter": "..."}
  ]
}
Element IDs are A, B, C, ... Limit to 8 elements max. If the claim has no clear elements, return an empty list."""
        user_prompt = f"Claim text:\n\n{claim_text[:2000]}"

        response, _ = self.llm.chat(sys_prompt, user_prompt, temperature=0.0, max_tokens=800)
        try:
            # Strip markdown fences if present
            clean = re.sub(r"^```(?:json)?\s*", "", response.strip())
            clean = re.sub(r"\s*```$", "", clean)
            data = json.loads(clean)
            if isinstance(data, dict) and "elements" in data:
                return data["elements"][:8]
        except json.JSONDecodeError:
            pass

        # Fallback: simple regex-based parsing (split on commas/semicolons, identify "comprising")
        elements = []
        # Crude split: look for "comprising" then list items separated by commas/semicolons
        m = re.search(r'comprising[:\s]+(.+?)(?:;|wherein|hereby|$)', claim_text, re.IGNORECASE | re.DOTALL)
        if m:
            parts = re.split(r'[;,]', m.group(1))
            for i, p in enumerate(parts):
                p = p.strip().rstrip('.')
                if len(p) > 5:
                    elements.append({
                        "element_id": chr(65 + i),
                        "technical_feature": p[:200],
                        "structural_requirement": "",
                        "functional_requirement": "",
                        "parameter": "",
                    })
        return elements[:8]

    def map_prior_art(self, claim_elements: List[Dict[str, str]],
                      prior_art_hits: List[Dict[str, Any]]) -> List[PriorArtMapping]:
        """For each prior-art hit, identify which claim elements it addresses."""
        mappings: List[PriorArtMapping] = []

        if not claim_elements:
            return mappings

        for hit in prior_art_hits:
            # Build LLM prompt
            elements_str = json.dumps(claim_elements, indent=2)
            hit_str = json.dumps({
                "title": hit.get("title", ""),
                "snippet": hit.get("snippet", ""),
                "abstract": (hit.get("raw_metadata") or {}).get("abstract", ""),
                "patent_id": hit.get("patent_id"),
                "doi": hit.get("doi"),
                "source_id": hit.get("source_id"),
            }, indent=2)

            sys_prompt = """You are a patent mapper. For each claim element, decide whether the prior-art hit discloses (teaches) that element.
Return JSON only. Format:
{
  "mapped_elements": [
    {"element_id": "A", "disclosed": true|false, "prior_art_text": "exact quote from snippet/abstract that discloses this element", "mapping_confidence": 0.0-1.0}
  ]
}
Be conservative: only mark "disclosed: true" if the prior art EXPLICITLY teaches the element. If unsure, mark false with confidence < 0.5."""

            user_prompt = f"""Claim elements:
{elements_str}

Prior-art hit:
{hit_str}"""

            response, _ = self.llm.chat(sys_prompt, user_prompt, temperature=0.0, max_tokens=800)

            mapped = []
            try:
                clean = re.sub(r"^```(?:json)?\s*", "", response.strip())
                clean = re.sub(r"\s*```$", "", clean)
                data = json.loads(clean)
                if isinstance(data, dict) and "mapped_elements" in data:
                    mapped = data["mapped_elements"]
            except json.JSONDecodeError:
                # Fallback: simple keyword matching
                snippet_lower = (hit.get("snippet", "") + " " + hit.get("title", "")).lower()
                for elem in claim_elements:
                    tf = elem.get("technical_feature", "").lower()
                    keywords = [w for w in re.split(r'\W+', tf) if len(w) > 4]
                    matches = sum(1 for kw in keywords if kw in snippet_lower)
                    conf = matches / max(1, len(keywords))
                    mapped.append({
                        "element_id": elem.get("element_id"),
                        "disclosed": conf > 0.4,
                        "prior_art_text": hit.get("snippet", "")[:200],
                        "mapping_confidence": round(conf, 2),
                    })

            mappings.append(PriorArtMapping(prior_art=hit, mapped_elements=mapped))

        return mappings


# ----------------------- ADVERSARY -----------------------
class Adversary:
    """Constructs 102 (novelty) or 103 (obviousness) attacks from prior-art mappings."""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def construct_attacks(self, claim: ClaimVersion,
                          mappings: List[PriorArtMapping]) -> List[AdversaryAttack]:
        """Build attacks for the claim based on the prior-art mappings."""
        if not mappings:
            return []

        # Compute disclosure scores per prior-art hit
        scored = []
        for m in mappings:
            disclosed_count = sum(1 for e in m.mapped_elements if e.get("disclosed"))
            total = max(1, len(m.mapped_elements))
            score = disclosed_count / total
            scored.append((m, score, disclosed_count, total))

        # Sort by score descending
        scored.sort(key=lambda x: -x[1])

        attacks: List[AdversaryAttack] = []

        # 102 attack: if a single reference discloses ALL elements
        for m, score, disclosed, total in scored:
            if disclosed == total and total >= 2:
                # Strong novelty attack
                attack = AdversaryAttack(
                    attack_id=f"ATTACK_R{claim.version}_{len(attacks)+1:03d}",
                    claim_version=claim.version,
                    attack_type="NOVELTY_102",
                    attack_strength="STRONG" if score >= 0.9 else "MODERATE",
                    primary_reference=m.prior_art,
                    rationale=f"Single reference discloses all {total} claim elements (score={score:.2f}). Anticipates the claim under 35 USC 102.",
                    anticipated_outcome="Examiner likely issues 102 rejection — claim not novel.",
                )
                attacks.append(attack)
                break  # one strong 102 attack is enough

        # 103 attack: if 2-3 references together disclose all elements
        if not any(a.attack_type == "NOVELTY_102" and a.attack_strength == "STRONG" for a in attacks):
            # Try combining top 2 references
            if len(scored) >= 2:
                m1, s1, d1, t1 = scored[0]
                m2, s2, d2, t2 = scored[1]
                # Combine disclosed element IDs
                e1 = {e["element_id"] for e in m1.mapped_elements if e.get("disclosed")}
                e2 = {e["element_id"] for e in m2.mapped_elements if e.get("disclosed")}
                combined = e1 | e2
                all_elem_ids = {e.get("element_id") for e in (m1.mapped_elements or [])}
                if combined and all_elem_ids and combined >= all_elem_ids:
                    attack = AdversaryAttack(
                        attack_id=f"ATTACK_R{claim.version}_{len(attacks)+1:03d}",
                        claim_version=claim.version,
                        attack_type="OBVIOUSNESS_103",
                        attack_strength="MODERATE",
                        primary_reference=m1.prior_art,
                        secondary_references=[m2.prior_art],
                        rationale=f"References 1+2 together disclose all claim elements. Obvious to combine under 35 USC 103.",
                        anticipated_outcome="Examiner may issue 103 rejection — combination is obvious.",
                    )
                    attacks.append(attack)

        # Also add an LLM-adversary attack for the top hit if no structural attack was built
        if not attacks and mappings:
            top_hit = scored[0][0]
            attack = self._llm_adversary_attack(claim, top_hit)
            if attack:
                attacks.append(attack)

        return attacks

    def _llm_adversary_attack(self, claim: ClaimVersion, mapping: PriorArtMapping) -> Optional[AdversaryAttack]:
        """Use LLM to construct an attack when structural analysis is inconclusive."""
        sys_prompt = """You are a patent examiner adversary. Given a claim and a prior-art hit, construct the strongest possible rejection.
If the prior art does NOT support a rejection, say so honestly.
Return JSON only. Format:
{
  "attack_type": "NOVELTY_102" | "OBVIOUSNESS_103" | "NO_ATTACK",
  "attack_strength": "WEAK" | "MODERATE" | "STRONG" | "FATAL",
  "rationale": "...",
  "anticipated_outcome": "..."
}"""
        user_prompt = f"""Claim:
{claim.claim_text[:1500]}

Prior-art hit:
{json.dumps(mapping.prior_art, indent=2)[:1500]}

Mapped elements:
{json.dumps(mapping.mapped_elements, indent=2)}"""

        response, _ = self.llm.chat(sys_prompt, user_prompt, temperature=0.0, max_tokens=600)
        try:
            clean = re.sub(r"^```(?:json)?\s*", "", response.strip())
            clean = re.sub(r"\s*```$", "", clean)
            data = json.loads(clean)
            if data.get("attack_type") == "NO_ATTACK":
                return None
            return AdversaryAttack(
                attack_id=f"ATTACK_R{claim.version}_LLM_001",
                claim_version=claim.version,
                attack_type=data.get("attack_type", "OBVIOUSNESS_103"),
                attack_strength=data.get("attack_strength", "WEAK"),
                primary_reference=mapping.prior_art,
                rationale=data.get("rationale", ""),
                anticipated_outcome=data.get("anticipated_outcome", ""),
            )
        except json.JSONDecodeError:
            return None


# ----------------------- REDESIGNER -----------------------
class Redesigner:
    """Modifies the claim to distinguish over prior-art attacks."""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def redesign(self, claim: ClaimVersion, attacks: List[AdversaryAttack]) -> Optional[Redesign]:
        """Produce a new claim version that distinguishes over the attacks."""
        if not attacks:
            return None

        sys_prompt = """You are a patent claim drafter. Given a claim under attack and the prior-art attacks against it, propose a redesigned claim that:
1. Preserves the inventive nucleus (the core technical insight)
2. Adds specific technical features that distinguish over the prior art
3. Is narrowly tailored — do NOT add features that the prior art already teaches
4. Is supported by the original disclosure (don't invent new matter)

Return JSON only. Format:
{
  "new_claim_text": "...",
  "change_summary": "what was added/modified",
  "rationale": "why this should survive the attacks",
  "new_elements": [{"element_id": "X", "technical_feature": "..."}],
  "distinguished_over": ["ATTACK_R0_001", ...]
}
If you CANNOT design around the attacks honestly, return {"new_claim_text": "", "rationale": "CANNOT_REDESIGN"}."""

        attacks_str = json.dumps([{
            "attack_id": a.attack_id,
            "attack_type": a.attack_type,
            "attack_strength": a.attack_strength,
            "rationale": a.rationale,
            "primary_reference_title": a.primary_reference.get("title", ""),
            "primary_reference_snippet": a.primary_reference.get("snippet", "")[:300],
        } for a in attacks], indent=2)

        user_prompt = f"""Current claim (v{claim.version}):
{claim.claim_text[:2000]}

Claim elements:
{json.dumps(claim.elements, indent=2)}

Attacks to distinguish over:
{attacks_str}"""

        response, _ = self.llm.chat(sys_prompt, user_prompt, temperature=0.2, max_tokens=1000)
        try:
            clean = re.sub(r"^```(?:json)?\s*", "", response.strip())
            clean = re.sub(r"\s*```$", "", clean)
            data = json.loads(clean)
            if not data.get("new_claim_text"):
                return None
            new_text = data["new_claim_text"]
            return Redesign(
                new_claim_text=new_text,
                new_claim_hash=_sha256(new_text),
                change_summary=data.get("change_summary", ""),
                rationale=data.get("rationale", ""),
                new_elements=data.get("new_elements", []),
                distinguished_over=data.get("distinguished_over", []),
            )
        except json.JSONDecodeError:
            return None


# ----------------------- ADJUDICATOR -----------------------
class Adjudicator:
    """Decides the final outcome after MAX_ROUNDS rounds."""

    def adjudicate(self, rounds: List) -> Tuple[str, str]:
        """
        Returns (final_adjudication, reason).
        final_adjudication ∈ {PASS, INSUFFICIENT_EVIDENCE, KILL}
        """
        if not rounds:
            return "INSUFFICIENT_EVIDENCE", "No rounds completed."

        last_round = rounds[-1]

        # Check if last round had insufficient prior art
        total_hits = sum(
            (sr.get("hit_count", 0) if isinstance(sr, dict) else 0)
            for sr in last_round.searcher_result.values()
            if isinstance(sr, dict)
        )
        if total_hits < MIN_HITS_PER_CLAIM:
            return ("INSUFFICIENT_EVIDENCE",
                    f"Only {total_hits} prior-art hits found in final round (min {MIN_HITS_PER_CLAIM} required).")

        # Check if last round survived
        if last_round.round_outcome == "SURVIVED":
            return ("PASS",
                    f"Claim survived all adversary attacks in round {last_round.round_num} "
                    f"({len(last_round.adversary_attacks)} attacks, none successful).")

        # Check if we exhausted rounds with continuing attacks
        if last_round.round_outcome == "REDESIGNED" and len(rounds) >= MAX_ROUNDS:
            return ("KILL",
                    f"Claim could not survive after {MAX_ROUNDS} redesign rounds. "
                    f"Final round still had {len(last_round.adversary_attacks)} attacks.")

        # Default: insufficient evidence
        return ("INSUFFICIENT_EVIDENCE",
                f"Loop ended in an indeterminate state after {len(rounds)} rounds.")


# ----------------------- LOOP ORCHESTRATOR -----------------------
class AutonomousPatentabilityLoop:
    """Orchestrates the full Searcher → Mapper → Adversary → Redesigner cycle."""

    def __init__(self, llm: Optional[LLMClient] = None,
                 num_per_source: int = 8, deep_fetch_top_n: int = 3,
                 max_rounds: int = MAX_ROUNDS):
        self.llm = llm or LLMClient()
        self.searcher = Searcher(num_per_source=num_per_source, deep_fetch_top_n=deep_fetch_top_n)
        self.mapper = Mapper(self.llm)
        self.adversary = Adversary(self.llm)
        self.redesigner = Redesigner(self.llm)
        self.adjudicator = Adjudicator()
        self.max_rounds = max_rounds

    def run(self, invention_id: str, device_class: str, inventive_nucleus: str,
            initial_claim: str) -> LoopFinalResult:
        """Run the full loop for one invention."""
        print(f"\n{'='*60}", flush=True)
        print(f"  LOOP START: {invention_id} ({device_class})", flush=True)
        print(f"{'='*60}", flush=True)
        print(f"  Inventive nucleus: {inventive_nucleus[:120]}...", flush=True)
        print(f"  Initial claim: {initial_claim[:120]}...", flush=True)

        # Initial claim version
        current_claim = ClaimVersion(
            version=0,
            claim_text=initial_claim,
            claim_hash=_sha256(initial_claim),
            created_at_utc=_now_utc(),
        )
        # Parse initial elements
        current_claim.elements = self.mapper.parse_claim_elements(initial_claim)
        print(f"  Parsed {len(current_claim.elements)} claim elements", flush=True)

        rounds: List[LoopRound] = []
        sources_used = set()
        sources_live = set()
        sources_failed = set()
        total_hits = 0

        for round_num in range(1, self.max_rounds + 1):
            print(f"\n  --- Round {round_num}/{self.max_rounds} ---", flush=True)
            print(f"  Claim v{current_claim.version}: {current_claim.claim_text[:100]}...", flush=True)

            # SEARCHER
            searcher_result = self.searcher.search(current_claim)

            # Track source stats
            for sid, sr in searcher_result.items():
                if sid.startswith("_"): continue
                if not isinstance(sr, dict): continue
                sources_used.add(sid)
                if sr.get("success"):
                    sources_live.add(sid)
                else:
                    sources_failed.add(sid)
                total_hits += sr.get("hit_count", 0)

            # Check for insufficient evidence
            hits_this_round = searcher_result.get("_total_hits", 0)
            if hits_this_round < MIN_HITS_PER_CLAIM:
                print(f"  [INSUFFICIENT_EVIDENCE] Only {hits_this_round} hits this round.", flush=True)
                round_obj = LoopRound(
                    round_num=round_num,
                    claim_version_in=current_claim,
                    searcher_result=searcher_result,
                    mapper_result=[],
                    adversary_attacks=[],
                    round_outcome="INSUFFICIENT_EVIDENCE",
                )
                rounds.append(round_obj)
                break

            # MAPPER
            all_hits = []
            for sid, sr in searcher_result.items():
                if sid.startswith("_"): continue
                if not isinstance(sr, dict): continue
                if sr.get("success"):
                    all_hits.extend(sr.get("hits", []))
            # Also include deep-fetched patents as enriched hits
            for df in searcher_result.get("_deep_fetched", []):
                all_hits.append({
                    "source_id": "GOOGLE_PATENTS_DEEP",
                    "source_url": df.get("source_url", ""),
                    "retrieved_at_utc": df.get("fetched_at_utc", ""),
                    "query": searcher_result.get("_query", ""),
                    "raw_payload_sha256": df.get("raw_html_sha256", ""),
                    "title": df.get("abstract", "")[:120],
                    "snippet": df.get("abstract", "")[:400],
                    "assignee_or_authors": [],
                    "publication_date": None,
                    "patent_id": df.get("patent_id"),
                    "doi": None,
                    "raw_metadata": {
                        "abstract": df.get("abstract", ""),
                        "claims": df.get("claims", []),
                        "description_excerpt": df.get("description_excerpt", ""),
                    },
                })

            mappings = self.mapper.map_prior_art(current_claim.elements, all_hits[:6])
            print(f"  [Mapper] Mapped {len(mappings)} prior-art hits to claim elements", flush=True)

            # ADVERSARY
            attacks = self.adversary.construct_attacks(current_claim, mappings)
            print(f"  [Adversary] Constructed {len(attacks)} attacks", flush=True)
            for a in attacks:
                print(f"    - {a.attack_id}: {a.attack_type} ({a.attack_strength})", flush=True)

            # Decide round outcome
            strong_attacks = [a for a in attacks if a.attack_strength in ("STRONG", "FATAL")]
            if not attacks or not strong_attacks:
                # Claim survived
                round_obj = LoopRound(
                    round_num=round_num,
                    claim_version_in=current_claim,
                    searcher_result=searcher_result,
                    mapper_result=mappings,
                    adversary_attacks=attacks,
                    round_outcome="SURVIVED",
                )
                rounds.append(round_obj)
                print(f"  [Outcome] SURVIVED", flush=True)
                break

            # Need to redesign
            if round_num < self.max_rounds:
                redesign = self.redesigner.redesign(current_claim, attacks)
                if redesign and redesign.new_claim_text:
                    print(f"  [Redesigner] Redesigned claim (change: {redesign.change_summary[:80]})", flush=True)
                    # Create new claim version
                    new_claim = ClaimVersion(
                        version=current_claim.version + 1,
                        claim_text=redesign.new_claim_text,
                        claim_hash=redesign.new_claim_hash,
                        created_at_utc=_now_utc(),
                    )
                    new_claim.elements = self.mapper.parse_claim_elements(redesign.new_claim_text)
                    round_obj = LoopRound(
                        round_num=round_num,
                        claim_version_in=current_claim,
                        searcher_result=searcher_result,
                        mapper_result=mappings,
                        adversary_attacks=attacks,
                        redesign=redesign,
                        round_outcome="REDESIGNED",
                    )
                    rounds.append(round_obj)
                    current_claim = new_claim
                    print(f"  [Outcome] REDESIGNED → v{new_claim.version}", flush=True)
                else:
                    # Redesign failed
                    round_obj = LoopRound(
                        round_num=round_num,
                        claim_version_in=current_claim,
                        searcher_result=searcher_result,
                        mapper_result=mappings,
                        adversary_attacks=attacks,
                        round_outcome="KILLED",
                    )
                    rounds.append(round_obj)
                    print(f"  [Outcome] KILLED (redesign failed)", flush=True)
                    break
            else:
                # Final round — no more redesigns
                round_obj = LoopRound(
                    round_num=round_num,
                    claim_version_in=current_claim,
                    searcher_result=searcher_result,
                    mapper_result=mappings,
                    adversary_attacks=attacks,
                    round_outcome="KILLED",
                )
                rounds.append(round_obj)
                print(f"  [Outcome] KILLED (max rounds exhausted)", flush=True)

        # ADJUDICATE
        final, reason = self.adjudicator.adjudicate(rounds)
        print(f"\n  [FINAL] {final}", flush=True)
        print(f"  [REASON] {reason}", flush=True)
        print(f"  [LLM stats] {self.llm.stats}", flush=True)

        return LoopFinalResult(
            invention_id=invention_id,
            device_class=device_class,
            inventive_nucleus=inventive_nucleus,
            initial_claim=initial_claim,
            final_claim=current_claim.claim_text,
            rounds=[self._serialize_round(r) for r in rounds],
            final_adjudication=final,
            final_adjudication_reason=reason,
            total_prior_art_hits=total_hits,
            sources_used=sorted(sources_used),
            sources_live=sorted(sources_live),
            sources_failed=sorted(sources_failed),
            timestamp=_now_utc(),
        )

    def _serialize_round(self, r: LoopRound) -> Dict[str, Any]:
        return {
            "round_num": r.round_num,
            "claim_version_in": asdict(r.claim_version_in),
            "searcher_result": r.searcher_result,
            "mapper_result": [asdict(m) for m in r.mapper_result],
            "adversary_attacks": [asdict(a) for a in r.adversary_attacks],
            "redesign": asdict(r.redesign) if r.redesign else None,
            "round_outcome": r.round_outcome,
        }


# ----------------------- CLI -----------------------
if __name__ == "__main__":
    # Smoke test on one invention
    test_claim = (
        "A hydrogel coating comprising a hydrogel matrix reinforced with nanofibers, "
        "wherein the nanofibers enhance the mechanical strength of the hydrogel matrix "
        "and reduce the impact of polymer chain scission."
    )

    loop = AutonomousPatentabilityLoop(max_rounds=2)  # reduced for smoke test
    result = loop.run(
        invention_id="SMOKE_TEST_001",
        device_class="Hydrogel Coating",
        inventive_nucleus="Nanofiber-reinforced hydrogel for medical device coatings",
        initial_claim=test_claim,
    )

    out = Path(__file__).resolve().parents[2] / "patent_sources" / "v2" / "loop_smoke_test.json"
    out.write_text(json.dumps(asdict(result), indent=2))
    print(f"\nSmoke test result: {out}")
