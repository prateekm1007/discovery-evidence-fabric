"""
ELITE VALUE AUDIT FRAMEWORK
============================

Implements the CEO directive for elite invention assessment.

An ELITE_INVENTION must satisfy most of these 12 criteria:
  A. large or expensive real-world problem
  B. clear economic buyer
  C. substantial measurable benefit
  D. technically meaningful mechanism
  E. difficult to reproduce without the invention
  F. meaningful structural/functional relationship
  G. plausible manufacturing path
  H. manageable regulatory pathway
  I. credible validation experiment
  J. credible patent claim space
  K. meaningful difficulty of design-around
  L. potential for platform/product expansion

VALUE CREATION TYPES (at least one required):
  COST_REDUCTION, FAILURE_REDUCTION, THROUGHPUT_INCREASE, YIELD_INCREASE,
  ENERGY_REDUCTION, SERVICE_LIFE_EXTENSION, CLINICAL_OUTCOME_IMPROVEMENT,
  REGULATORY_RISK_REDUCTION, MANUFACTURING_SIMPLIFICATION,
  NEW_PRODUCT_CAPABILITY, REVENUE_GENERATION, OTHER

REJECTION CRITERIA (auto-REJECT if merely):
  - material substitution
  - size change
  - parameter tuning
  - obvious automation
  - generic AI control
  - generic sensor improvement
  - known component substitution
  unless the combination creates a new technical effect.

FOUR-ATTACK DESTRUCTION TEST:
  1. NOVELTY_ATTACK (102) — one reference, all elements
  2. OBVIOUSNESS_ATTACK (103) — multiple references, motivation to combine
  3. ENABLEMENT_ATTACK (112) — can a PHOSITA make and use it?
  4. DESIGN_AROUND_ATTACK — easiest competitor workaround

TIER ASSIGNMENT:
  ELITE    — 10+ criteria met, no fatal attacks, HIGH_VALUE_PROBLEM=YES
  STRONG   — 7-9 criteria met, no fatal attacks
  PROMISING — 5-6 criteria met, or 7+ with one recoverable attack
  WEAK     — 3-4 criteria met, or multiple attacks
  REJECT   — <3 criteria met, or fatal attack, or mere material substitution

HONESTY RULES:
  - Every economic number must be tagged: EVIDENCE | INFERENCE | HYPOTHESIS
  - Never fabricate market size
  - If prior-art search returns <3 hits → INSUFFICIENT_EVIDENCE (not PASS)
  - If an attack cannot be constructed → say so honestly (don't assume survival)
  - Tier assignment is based on ACTUAL evidence, not optimism
"""
from __future__ import annotations
import os, sys, json, time, hashlib, re, subprocess
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

THIS_DIR = Path(__file__).resolve().parent
REPO_ROOT = THIS_DIR.parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.prior_art_v2.sources import (
    search_all_sources, fetch_google_patent_full_claims,
    _now_utc, _sha256,
)


# ----------------------- ELITE CRITERIA -----------------------
ELITE_CRITERIA = [
    "A_large_expensive_problem",
    "B_clear_economic_buyer",
    "C_substantial_measurable_benefit",
    "D_technically_meaningful_mechanism",
    "E_difficult_to_reproduce",
    "F_meaningful_structural_functional_relationship",
    "G_plausible_manufacturing_path",
    "H_manageable_regulatory_pathway",
    "I_credible_validation_experiment",
    "J_credible_patent_claim_space",
    "K_meaningful_design_around_difficulty",
    "L_platform_product_expansion_potential",
]

VALUE_CREATION_TYPES = [
    "COST_REDUCTION", "FAILURE_REDUCTION", "THROUGHPUT_INCREASE",
    "YIELD_INCREASE", "ENERGY_REDUCTION", "SERVICE_LIFE_EXTENSION",
    "CLINICAL_OUTCOME_IMPROVEMENT", "REGULATORY_RISK_REDUCTION",
    "MANUFACTURING_SIMPLIFICATION", "NEW_PRODUCT_CAPABILITY",
    "REVENUE_GENERATION", "OTHER",
]

REJECTION_PATTERNS = [
    "mere_material_substitution",
    "mere_size_change",
    "mere_parameter_tuning",
    "obvious_automation",
    "generic_AI_control",
    "generic_sensor_improvement",
    "known_component_substitution",
]

TIERS = ["ELITE", "STRONG", "PROMISING", "WEAK", "REJECT"]


# ----------------------- LLM CLIENT -----------------------
class LLMClient:
    """Wraps z-ai-web-dev-sdk with rate limiting and retry."""

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
             temperature: float = 0.0, max_tokens: int = 2000) -> Tuple[str, int]:
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
        tmp = Path(f"/tmp/elite_llm_{os.getpid()}_{int(time.time()*1000)}_{self._call_count}.mjs")
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
                    return f"[429_RATE_LIMITED: {data['error'][:200]}]", 0

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
class EliteCriteriaScore:
    criteria: str
    met: bool
    confidence: str  # EVIDENCE | INFERENCE | HYPOTHESIS
    reasoning: str
    evidence_tag: str  # EVIDENCE | INFERENCE | HYPOTHESIS


@dataclass
class EconomicValueAssessment:
    customer_problem: str
    economic_pain: str
    current_cost: str
    current_failure: str
    value_created: str
    who_pays: str
    why_they_pay: str
    adoption_barrier: str
    value_creation_types: List[str]
    market_size_evidence_tag: str  # EVIDENCE | INFERENCE | HYPOTHESIS
    market_size_basis: str


@dataclass
class PriorArtAttack:
    attack_type: str  # NOVELTY_102 | OBVIOUSNESS_103 | ENABLEMENT_112 | DESIGN_AROUND
    attack_strength: str  # WEAK | MODERATE | STRONG | FATAL
    primary_reference: Optional[Dict[str, Any]]
    secondary_references: List[Dict[str, Any]]
    rationale: str
    elements_addressed: List[str]
    can_survive: bool  # can the claim survive this attack?
    survival_path: str  # if can_survive, how?


@dataclass
class EliteAuditResult:
    invention_id: str
    device_class: str
    inventive_nucleus: str
    claim_text: str
    claim_hash: str

    # Economic value
    economic_assessment: EconomicValueAssessment

    # Elite criteria (12)
    criteria_scores: List[EliteCriteriaScore]
    criteria_met_count: int

    # Rejection patterns
    rejection_patterns_matched: List[str]
    new_technical_effect: str  # if rejection patterns matched, does combination create new effect?

    # Prior-art attacks (4)
    attacks: List[PriorArtAttack]
    fatal_attacks: List[str]
    surviving_attacks: List[str]

    # Prior-art search provenance
    prior_art_search: Dict[str, Any]
    sources_searched: List[str]
    sources_live: List[str]
    total_prior_art_hits: int

    # Final tier
    tier: str  # ELITE | STRONG | PROMISING | WEAK | REJECT
    tier_reasoning: str

    # Metadata
    timestamp: str
    llm_calls: int
    elapsed_seconds: float


# ----------------------- ELITE AUDITOR -----------------------
class EliteAuditor:
    """Runs the full elite audit on a single invention."""

    def __init__(self, llm: Optional[LLMClient] = None, num_per_source: int = 6):
        self.llm = llm or LLMClient()
        self.num_per_source = num_per_source

    def audit(self, invention_id: str, device_class: str, inventive_nucleus: str,
              claim_text: str) -> EliteAuditResult:
        """Run the full elite audit."""
        t0 = time.time()
        print(f"\n{'='*60}", flush=True)
        print(f"  ELITE AUDIT: {invention_id} ({device_class})", flush=True)
        print(f"{'='*60}", flush=True)

        claim_hash = _sha256(claim_text)

        # STEP 1: Real prior-art search
        print(f"  [1/5] Searching prior art...", flush=True)
        prior_art_search = self._search_prior_art(claim_text)
        sources_searched = list(prior_art_search.keys())
        sources_live = [s for s in sources_searched
                        if prior_art_search.get(s, {}).get("success")]
        total_hits = sum(prior_art_search.get(s, {}).get("hit_count", 0)
                         for s in sources_searched)
        print(f"       Sources live: {sources_live}, total hits: {total_hits}", flush=True)

        # Collect all hits for attack construction
        all_hits = []
        for sid in sources_searched:
            sr = prior_art_search.get(sid, {})
            if sr.get("success"):
                all_hits.extend(sr.get("hits", []))
        # Deep-fetch top 2 Google Patents hits for full claims
        gp_hits = [h for h in all_hits if h.get("source_id") == "GOOGLE_PATENTS"]
        for h in gp_hits[:2]:
            if h.get("patent_id"):
                print(f"       Deep-fetching {h['patent_id']}...", flush=True)
                full = fetch_google_patent_full_claims(h["patent_id"])
                if "claims" in full and full["claims"]:
                    h["raw_metadata"]["full_claims"] = full["claims"]
                    h["raw_metadata"]["abstract"] = full.get("abstract", "")

        # STEP 2: Economic value assessment
        print(f"  [2/5] Assessing economic value...", flush=True)
        economic = self._assess_economic_value(
            invention_id, device_class, inventive_nucleus, claim_text)

        # STEP 3: Elite criteria scoring
        print(f"  [3/5] Scoring 12 elite criteria...", flush=True)
        criteria_scores = self._score_elite_criteria(
            invention_id, device_class, inventive_nucleus, claim_text, economic)
        criteria_met = sum(1 for c in criteria_scores if c.met)

        # STEP 4: Rejection pattern check
        print(f"  [4/5] Checking rejection patterns...", flush=True)
        rejection_patterns, new_technical_effect = self._check_rejection_patterns(
            invention_id, device_class, inventive_nucleus, claim_text)

        # STEP 5: Four-attack destruction test
        print(f"  [5/5] Running 4-attack destruction test...", flush=True)
        attacks = self._construct_attacks(
            claim_text, inventive_nucleus, all_hits, economic)
        fatal_attacks = [a.attack_type for a in attacks if a.attack_strength == "FATAL"]
        surviving_attacks = [a.attack_type for a in attacks if a.can_survive]

        # TIER ASSIGNMENT
        tier, tier_reasoning = self._assign_tier(
            criteria_met, len(fatal_attacks), len(surviving_attacks),
            rejection_patterns, new_technical_effect, total_hits, economic)

        elapsed = time.time() - t0
        print(f"\n  → TIER: {tier}", flush=True)
        print(f"     Criteria met: {criteria_met}/12", flush=True)
        print(f"     Fatal attacks: {len(fatal_attacks)}", flush=True)
        print(f"     Rejection patterns: {rejection_patterns}", flush=True)
        print(f"     Elapsed: {elapsed:.1f}s", flush=True)

        return EliteAuditResult(
            invention_id=invention_id,
            device_class=device_class,
            inventive_nucleus=inventive_nucleus,
            claim_text=claim_text,
            claim_hash=claim_hash,
            economic_assessment=economic,
            criteria_scores=criteria_scores,
            criteria_met_count=criteria_met,
            rejection_patterns_matched=rejection_patterns,
            new_technical_effect=new_technical_effect,
            attacks=attacks,
            fatal_attacks=fatal_attacks,
            surviving_attacks=surviving_attacks,
            prior_art_search={
                sid: {
                    "success": sr.get("success"),
                    "hit_count": sr.get("hit_count", 0),
                    "error": sr.get("error"),
                } for sid, sr in prior_art_search.items()
            },
            sources_searched=sources_searched,
            sources_live=sources_live,
            total_prior_art_hits=total_hits,
            tier=tier,
            tier_reasoning=tier_reasoning,
            timestamp=_now_utc(),
            llm_calls=self.llm._call_count,
            elapsed_seconds=round(elapsed, 1),
        )

    # ----------------------- STEP 1: PRIOR-ART SEARCH -----------------------
    def _search_prior_art(self, claim_text: str) -> Dict[str, Any]:
        """Run real prior-art search via the V2 sources adapter."""
        query = claim_text[:250]
        results = search_all_sources(query, num_per_source=self.num_per_source)
        return {
            sid: {
                "success": r.success,
                "hit_count": len(r.hits),
                "hits": [asdict(h) for h in r.hits],
                "error": r.error,
                "error_code": r.error_code,
            } for sid, r in results.items()
        }

    # ----------------------- STEP 2: ECONOMIC VALUE -----------------------
    def _assess_economic_value(self, inv_id: str, device_class: str,
                                nucleus: str, claim: str) -> EconomicValueAssessment:
        """LLM-driven economic value assessment."""
        sys_prompt = """You are a commercial IP strategist. Assess the economic value of this invention.
Be HONEST. If you don't know a number, say HYPOTHESIS. Never fabricate market size.
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
  "market_size_evidence_tag": "EVIDENCE|INFERENCE|HYPOTHESIS",
  "market_size_basis": "explain basis or say UNKNOWN"
}"""
        user_prompt = f"""Invention: {inv_id}
Device class: {device_class}
Inventive nucleus: {nucleus}
Claim: {claim[:1500]}"""

        response, _ = self.llm.chat(sys_prompt, user_prompt, temperature=0.0, max_tokens=1200)
        try:
            clean = re.sub(r"^```(?:json)?\s*", "", response.strip())
            clean = re.sub(r"\s*```$", "", clean)
            data = json.loads(clean)
            return EconomicValueAssessment(**data)
        except (json.JSONDecodeError, TypeError) as e:
            return EconomicValueAssessment(
                customer_problem=f"[PARSE_ERROR: {e}]",
                economic_pain="UNKNOWN",
                current_cost="UNKNOWN (HYPOTHESIS)",
                current_failure="UNKNOWN",
                value_created="UNKNOWN",
                who_pays="UNKNOWN",
                why_they_pay="UNKNOWN",
                adoption_barrier="UNKNOWN",
                value_creation_types=[],
                market_size_evidence_tag="HYPOTHESIS",
                market_size_basis="UNKNOWN — LLM parse error",
            )

    # ----------------------- STEP 3: ELITE CRITERIA SCORING -----------------------
    def _score_elite_criteria(self, inv_id: str, device_class: str,
                               nucleus: str, claim: str,
                               economic: EconomicValueAssessment) -> List[EliteCriteriaScore]:
        """Score each of the 12 elite criteria."""
        sys_prompt = f"""You are an elite invention auditor. Score each of the 12 elite criteria for this invention.
For each criterion, assess: is it MET (true), and what is the evidence quality?
Evidence quality: EVIDENCE (verified fact), INFERENCE (reasonable deduction), HYPOTHESIS (speculation).
Return JSON only. Format:
{{
  "scores": [
    {{"criteria": "A_large_expensive_problem", "met": true|false, "confidence": "EVIDENCE|INFERENCE|HYPOTHESIS", "reasoning": "..."}},
    ... (all 12 criteria)
  ]
}}

The 12 criteria:
A. large or expensive real-world problem
B. clear economic buyer
C. substantial measurable benefit
D. technically meaningful mechanism
E. difficult to reproduce without the invention
F. meaningful structural/functional relationship
G. plausible manufacturing path
H. manageable regulatory pathway
I. credible validation experiment
J. credible patent claim space
K. meaningful difficulty of design-around
L. potential for platform/product expansion

Be STRICT. An invention that is merely a material substitution or parameter tuning should fail D, E, F, and K."""

        user_prompt = f"""Invention: {inv_id}
Device class: {device_class}
Inventive nucleus: {nucleus}
Claim: {claim[:1500]}

Economic assessment:
Customer problem: {economic.customer_problem}
Value creation types: {economic.value_creation_types}
Who pays: {economic.who_pays}
Current cost: {economic.current_cost}"""

        response, _ = self.llm.chat(sys_prompt, user_prompt, temperature=0.0, max_tokens=2000)
        try:
            clean = re.sub(r"^```(?:json)?\s*", "", response.strip())
            clean = re.sub(r"\s*```$", "", clean)
            data = json.loads(clean)
            scores = []
            for s in data.get("scores", []):
                scores.append(EliteCriteriaScore(
                    criteria=s.get("criteria", ""),
                    met=s.get("met", False),
                    confidence=s.get("confidence", "HYPOTHESIS"),
                    reasoning=s.get("reasoning", ""),
                    evidence_tag=s.get("confidence", "HYPOTHESIS"),
                ))
            # Ensure all 12 are present
            seen = {s.criteria for s in scores}
            for c in ELITE_CRITERIA:
                if c not in seen:
                    scores.append(EliteCriteriaScore(
                        criteria=c, met=False, confidence="HYPOTHESIS",
                        reasoning="Not assessed", evidence_tag="HYPOTHESIS",
                    ))
            return scores
        except (json.JSONDecodeError, TypeError) as e:
            return [EliteCriteriaScore(
                criteria=c, met=False, confidence="HYPOTHESIS",
                reasoning=f"[PARSE_ERROR: {e}]", evidence_tag="HYPOTHESIS",
            ) for c in ELITE_CRITERIA]

    # ----------------------- STEP 4: REJECTION PATTERNS -----------------------
    def _check_rejection_patterns(self, inv_id: str, device_class: str,
                                   nucleus: str, claim: str) -> Tuple[List[str], str]:
        """Check if the invention is merely a rejection-pattern idea."""
        sys_prompt = """You are a patent destruction adversary. Check if this invention is merely:
- material substitution (e.g., replacing steel with titanium)
- size change (e.g., making it smaller)
- parameter tuning (e.g., adjusting a known parameter)
- obvious automation (e.g., adding a controller to a manual process)
- generic AI control (e.g., "use ML to optimize")
- generic sensor improvement (e.g., "add a better sensor")
- known component substitution (e.g., swapping one known part for another)

If ANY of these patterns match, list them. Then assess: does the combination create a NEW technical effect that transcends the pattern?
Return JSON only. Format:
{
  "matched_patterns": ["mere_material_substitution", ...],
  "new_technical_effect": "...|NONE",
  "reasoning": "..."
}"""
        user_prompt = f"""Invention: {inv_id}
Device class: {device_class}
Inventive nucleus: {nucleus}
Claim: {claim[:1500]}"""

        response, _ = self.llm.chat(sys_prompt, user_prompt, temperature=0.0, max_tokens=800)
        try:
            clean = re.sub(r"^```(?:json)?\s*", "", response.strip())
            clean = re.sub(r"\s*```$", "", clean)
            data = json.loads(clean)
            return data.get("matched_patterns", []), data.get("new_technical_effect", "NONE")
        except (json.JSONDecodeError, TypeError):
            return [], "UNKNOWN"

    # ----------------------- STEP 5: FOUR-ATTACK DESTRUCTION TEST -----------------------
    def _construct_attacks(self, claim: str, nucleus: str,
                            prior_art_hits: List[Dict[str, Any]],
                            economic: EconomicValueAssessment) -> List[PriorArtAttack]:
        """Construct 4 attacks: novelty, obviousness, enablement, design-around."""
        # Prepare top prior-art hits for the prompt
        top_hits = prior_art_hits[:6]
        hits_str = json.dumps([{
            "title": h.get("title", "")[:150],
            "snippet": h.get("snippet", "")[:300],
            "patent_id": h.get("patent_id"),
            "source_id": h.get("source_id"),
            "abstract": (h.get("raw_metadata") or {}).get("abstract", "")[:500],
        } for h in top_hits], indent=2)

        sys_prompt = """You are a patent examiner adversary. Your job is to DESTROY this claim.
Construct 4 attacks:
1. NOVELTY_102 — find ONE reference that discloses ALL claim elements. If no single reference does, say "NO_NOVELTY_ATTACK_POSSIBLE".
2. OBVIOUSNESS_103 — find 2-3 references that TOGETHER disclose all elements + motivation to combine. If no combination works, say "NO_OBVIOUSNESS_ATTACK_POSSIBLE".
3. ENABLEMENT_112 — can a PHOSITA make and use this without undue experimentation? If yes, no attack. If no, explain why.
4. DESIGN_AROUND — what is the EASIEST competitor workaround? Does it still achieve the value?

Be HONEST. If an attack cannot be constructed from the prior art, say so.
Return JSON only. Format:
{
  "attacks": [
    {
      "attack_type": "NOVELTY_102",
      "attack_strength": "WEAK|MODERATE|STRONG|FATAL|NONE",
      "primary_reference": {...}|null,
      "secondary_references": [...],
      "rationale": "...",
      "elements_addressed": ["A","B"],
      "can_survive": true|false,
      "survival_path": "how the claim can survive this attack, or empty if it cannot"
    },
    ... (4 attacks total)
  ]
}

If prior-art hits are insufficient to construct an attack, mark attack_strength="NONE" and explain what evidence is missing. Do NOT assume the claim survives just because you can't find an attack — say INSUFFICIENT_EVIDENCE."""

        user_prompt = f"""Claim: {claim[:1500]}

Inventive nucleus: {nucleus}

Prior-art hits found:
{hits_str if top_hits else 'NO PRIOR-ART HITS FOUND — mark attacks as INSUFFICIENT_EVIDENCE'}

Economic value: {economic.value_created}
Value creation types: {economic.value_creation_types}"""

        response, _ = self.llm.chat(sys_prompt, user_prompt, temperature=0.0, max_tokens=2000)
        try:
            clean = re.sub(r"^```(?:json)?\s*", "", response.strip())
            clean = re.sub(r"\s*```$", "", clean)
            data = json.loads(clean)
            attacks = []
            for a in data.get("attacks", []):
                attacks.append(PriorArtAttack(
                    attack_type=a.get("attack_type", ""),
                    attack_strength=a.get("attack_strength", "NONE"),
                    primary_reference=a.get("primary_reference"),
                    secondary_references=a.get("secondary_references", []),
                    rationale=a.get("rationale", ""),
                    elements_addressed=a.get("elements_addressed", []),
                    can_survive=a.get("can_survive", False),
                    survival_path=a.get("survival_path", ""),
                ))
            # Ensure all 4 attack types are present
            seen = {a.attack_type for a in attacks}
            for at in ["NOVELTY_102", "OBVIOUSNESS_103", "ENABLEMENT_112", "DESIGN_AROUND"]:
                if at not in seen:
                    attacks.append(PriorArtAttack(
                        attack_type=at,
                        attack_strength="NONE",
                        primary_reference=None,
                        secondary_references=[],
                        rationale="Attack not constructed",
                        elements_addressed=[],
                        can_survive=True,
                        survival_path="No attack constructed",
                    ))
            return attacks
        except (json.JSONDecodeError, TypeError) as e:
            return [PriorArtAttack(
                attack_type=at,
                attack_strength="NONE",
                primary_reference=None,
                secondary_references=[],
                rationale=f"[PARSE_ERROR: {e}]",
                elements_addressed=[],
                can_survive=True,
                survival_path="Parse error — attack not evaluated",
            ) for at in ["NOVELTY_102", "OBVIOUSNESS_103", "ENABLEMENT_112", "DESIGN_AROUND"]]

    # ----------------------- TIER ASSIGNMENT -----------------------
    def _assign_tier(self, criteria_met: int, fatal_count: int,
                     surviving_count: int, rejection_patterns: List[str],
                     new_technical_effect: str, total_hits: int,
                     economic: EconomicValueAssessment) -> Tuple[str, str]:
        """Assign tier based on criteria + attacks + rejection patterns."""
        # Auto-REJECT if fatal attack
        if fatal_count > 0:
            return "REJECT", f"{fatal_count} fatal attack(s) — claim cannot survive"

        # Auto-REJECT if rejection patterns matched without new technical effect
        if rejection_patterns and new_technical_effect in ("NONE", "UNKNOWN", ""):
            return "REJECT", f"Rejection patterns matched ({rejection_patterns}) with no new technical effect"

        # INSUFFICIENT_EVIDENCE if too few prior-art hits
        if total_hits < 3:
            return "WEAK", f"Only {total_hits} prior-art hits — insufficient evidence to validate"

        # Tier by criteria count
        if criteria_met >= 10 and economic.market_size_evidence_tag != "HYPOTHESIS":
            return "ELITE", f"{criteria_met}/12 criteria met, no fatal attacks, evidence-backed economic value"
        elif criteria_met >= 7:
            return "STRONG", f"{criteria_met}/12 criteria met, no fatal attacks"
        elif criteria_met >= 5:
            return "PROMISING", f"{criteria_met}/12 criteria met, no fatal attacks"
        elif criteria_met >= 3:
            return "WEAK", f"Only {criteria_met}/12 criteria met"
        else:
            return "REJECT", f"Only {criteria_met}/12 criteria met — below minimum threshold"
