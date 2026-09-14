"""
Invention Rescue V2 — Real Rescue Loop
=======================================

Fixes V1 issues:
  - Clean claim text (no "Claim N:" prefix)
  - New concept graph PER claim version (not reused)
  - Simulation per architecture (baseline, mechanism, predicted effect, failure condition)
  - Experiment design (IV, DV, baseline, control, measurement, success/failure/falsifier)
  - Commercial value preservation check
  - Design-around test per surviving claim
  - No GOLD → INSUFFICIENT_EVIDENCE (never NOVEL)

RESCUE STATUS VALUES:
  RESCUE_PENDING_EVIDENCE — claim constructed, 0 GOLD
  RESCUE_SURVIVES_102 — survived 102 with GOLD evidence
  RESCUE_SURVIVES_103 — survived 102 + 103
  RESCUE_STRONG_CANDIDATE — survived + technical effect + commercial + experiment
  RESCUE_ABANDONED — all architectures failed

FINAL INVENTION DECISION:
  CLAIM_DEAD — claim rejected, no rescue attempted
  CLAIM_ALIVE — claim survived
  INVENTION_ALIVE — claim may be dead but invention redesign works
  INVENTION_REDESIGN_REQUIRED — needs redesign
  INVENTION_ABANDONED — all redesigns failed
"""
from __future__ import annotations
import os, sys, json, time, hashlib, re
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

THIS_DIR = Path(__file__).resolve().parent
REPO_ROOT = THIS_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.prior_art_v2.elite_v3 import LLMClient, _now_utc, _sha256
from discovery_fabric.prior_art_v2.retrieval_v4 import (
    RetrievalV4, ConceptGraph, ConceptGraphBuilder,
    QueryFamilyGenerator, MultiDatabaseSearcher,
    PatentRelevanceGate, CPCExpander, FamilyDeduplicator,
    RetrievedPatent,
)
from discovery_fabric.prior_art_v2.retrieval_v3 import fetch_patent_full, PatentRecord
from discovery_fabric.prior_art_v2.claim_attack import (
    ClaimAttackAuditor, ClaimAttackResult, ClaimElement,
    NoveltyResult,
)
from discovery_fabric.prior_art_v2.forensic_review import (
    ObviousnessAttackForensic, DesignAroundForensic, EliteGateResult,
)


# ----------------------- DATA SCHEMAS -----------------------
@dataclass
class SimulationResult:
    """Simulation test for an architecture."""
    architecture_id: str = ""
    baseline: str = ""
    new_mechanism: str = ""
    predicted_effect: str = ""
    failure_condition: str = ""
    simulated_advantage: bool = False
    simulation_notes: str = ""
    status: str = ""  # ARCHITECTURE_VIABLE / ARCHITECTURE_WEAK


@dataclass
class ExperimentDesign:
    """Cheapest decisive experiment for an architecture."""
    architecture_id: str = ""
    independent_variable: str = ""
    dependent_variable: str = ""
    baseline: str = ""
    control: str = ""
    measurement: str = ""
    success_criterion: str = ""
    failure_criterion: str = ""
    falsifier: str = ""
    cheapest_decisive_experiment: str = ""


@dataclass
class CommercialValueCheck:
    """Commercial value preservation check."""
    architecture_id: str = ""
    customer_problem: str = ""
    economic_value: str = ""
    manufacturing_consequence: str = ""
    integration_burden: str = ""
    preserves_value: bool = False
    status: str = ""  # VALUE_PRESERVED / ABANDON_REDESIGN


@dataclass
class ClaimRescueV2Result:
    """One claim version with full V2 rescue."""
    version: int
    claim_text: str
    claim_hash: str
    concept_graph: Optional[Dict[str, Any]] = None
    search_gold_count: int = 0
    search_gold_patent_ids: List[str] = field(default_factory=list)
    search_databases: List[str] = field(default_factory=list)
    search_saturation: bool = False
    novelty_102_result: Optional[Dict[str, Any]] = None
    obviousness_103_result: Optional[Dict[str, Any]] = None
    simulation: Optional[SimulationResult] = None
    experiment: Optional[ExperimentDesign] = None
    commercial_value: Optional[CommercialValueCheck] = None
    design_around: Optional[Dict[str, Any]] = None
    status: str = ""  # RESCUE_PENDING_EVIDENCE / RESCUE_SURVIVES_102 / RESCUE_SURVIVES_103 / RESCUE_STRONG_CANDIDATE / REJECTED_102 / REJECTED_103 / ABANDONED
    rationale: str = ""


@dataclass
class RescueV2Result:
    """Complete V2 rescue result."""
    invention_id: str
    claim_0: Dict[str, Any] = field(default_factory=dict)
    commercial_objective: Dict[str, Any] = field(default_factory=dict)
    architectures: List[Dict[str, Any]] = field(default_factory=list)
    claim_1: Optional[ClaimRescueV2Result] = None
    claim_2: Optional[ClaimRescueV2Result] = None
    final_resolution: str = ""
    final_reasoning: str = ""
    invention_decision: str = ""  # CLAIM_DEAD / CLAIM_ALIVE / INVENTION_ALIVE / INVENTION_REDESIGN_REQUIRED / INVENTION_ABANDONED
    timestamp: str = ""
    llm_calls: int = 0
    elapsed_seconds: float = 0.0


# ----------------------- RESCUE V2 AUDITOR -----------------------
class RescueV2Auditor:
    """Runs the real invention rescue loop."""

    def __init__(self, llm: Optional[LLMClient] = None):
        self.llm = llm or LLMClient()
        self.retriever = RetrievalV4(llm=llm)
        self.claim_auditor = ClaimAttackAuditor(llm=llm)
        self.concept_builder = ConceptGraphBuilder(llm=llm)

    def _extract_json(self, response: str) -> Optional[dict]:
        """Extract JSON from LLM response."""
        try: return json.loads(response.strip())
        except: pass
        clean = re.sub(r"^```(?:json)?\s*", "", response.strip())
        clean = re.sub(r"\s*```$", "", clean)
        try: return json.loads(clean)
        except: pass
        start = response.find("{")
        if start < 0: return None
        depth = 0
        for i in range(start, len(response)):
            if response[i] == "{": depth += 1
            elif response[i] == "}":
                depth -= 1
                if depth == 0:
                    try: return json.loads(response[start:i+1])
                    except: pass
        return None

    def rescue(self, invention_id: str, claim_0_text: str,
               claim_0_result: Dict[str, Any],
               architectures: List[Dict[str, Any]],
               commercial_objective: Dict[str, Any]) -> RescueV2Result:
        """Run full V2 rescue loop."""
        t0 = time.time()
        print(f"\n{'='*60}", flush=True)
        print(f"  RESCUE V2: {invention_id}", flush=True)
        print(f"{'='*60}", flush=True)

        result = RescueV2Result(
            invention_id=invention_id,
            claim_0=claim_0_result,
            commercial_objective=commercial_objective,
            architectures=architectures,
            timestamp=_now_utc(),
        )

        # STEP 1: Run simulation + experiment + commercial value for each architecture
        print(f"  [1] Simulating architectures...", flush=True)
        for arch in architectures:
            arch_id = arch.get("architecture_id", "")
            print(f"      {arch_id}: simulating...", flush=True)
            sim = self._simulate(arch, commercial_objective)
            arch["simulation"] = asdict(sim)
            if sim.status == "ARCHITECTURE_WEAK":
                print(f"        → ARCHITECTURE_WEAK", flush=True)
                continue
            exp = self._design_experiment(arch, commercial_objective)
            arch["experiment"] = asdict(exp)
            cv = self._check_commercial_value(arch, commercial_objective)
            arch["commercial_value"] = asdict(cv)
            if cv.status == "ABANDON_REDESIGN":
                print(f"        → ABANDON_REDESIGN (commercial value destroyed)", flush=True)

        # STEP 2: Try Claim 1 (use first viable architecture)
        viable_archs = [a for a in architectures
                        if a.get("simulation", {}).get("status") == "ARCHITECTURE_VIABLE"
                        and a.get("commercial_value", {}).get("status") == "VALUE_PRESERVED"]

        if not viable_archs:
            print(f"  No viable architectures — trying all anyway", flush=True)
            viable_archs = architectures

        for attempt, arch in enumerate(viable_archs[:2], 1):
            print(f"\n  [{attempt+1}] Constructing Claim {attempt} from {arch.get('architecture_id','')}...", flush=True)

            # Construct clean claim
            claim_text = self._construct_clean_claim(claim_0_text, arch, commercial_objective, attempt)
            if not claim_text or len(claim_text) < 30:
                print(f"      Could not construct claim", flush=True)
                continue

            print(f"      Claim text: {claim_text[:120]}...", flush=True)

            # Build NEW concept graph for this claim (not reused)
            print(f"      Building new concept graph...", flush=True)
            cg = self.concept_builder.build(invention_id, claim_text, arch.get("material_difference", ""))

            # Full V4 retrieval with new concept graph
            print(f"      Running V4 retrieval...", flush=True)
            retrieval = self.retriever.retrieve(invention_id, claim_text, arch.get("material_difference", ""))

            # Build claim result
            cr = ClaimRescueV2Result(
                version=attempt,
                claim_text=claim_text,
                claim_hash=_sha256(claim_text),
                concept_graph=asdict(cg) if cg else None,
                search_gold_count=retrieval.gold_count,
                search_gold_patent_ids=retrieval.gold_patent_ids,
                search_databases=retrieval.databases_searched,
                search_saturation=retrieval.search_saturation,
                simulation=SimulationResult(
                    architecture_id=arch.get("architecture_id", ""),
                    status=arch.get("simulation", {}).get("status", ""),
                ),
                experiment=ExperimentDesign(
                    architecture_id=arch.get("architecture_id", ""),
                ),
                commercial_value=CommercialValueCheck(
                    architecture_id=arch.get("architecture_id", ""),
                    status=arch.get("commercial_value", {}).get("status", ""),
                ),
            )

            # Check GOLD evidence
            if retrieval.gold_count == 0:
                cr.status = "RESCUE_PENDING_EVIDENCE"
                cr.rationale = f"0 GOLD patents retrieved. Cannot validate. (NOT novel — insufficient evidence)"
                print(f"      → RESCUE_PENDING_EVIDENCE (0 GOLD)", flush=True)
            else:
                # Run 102 attack with GOLD patents
                print(f"      Running 102 attack with {retrieval.gold_count} GOLD patents...", flush=True)
                gold_patents = [asdict(rp) for rp in retrieval.retrieved_patents if rp.is_gold]
                attack_result = self.claim_auditor.attack(invention_id, claim_text, gold_patents)

                # Check 102
                killed = False
                for nr in attack_result.novelty_results:
                    if nr.novelty_attacked:
                        cr.status = "REJECTED_102"
                        cr.rationale = f"Claim {attempt} rejected by 102: {nr.patent_id}"
                        cr.novelty_102_result = asdict(nr)
                        killed = True
                        print(f"      → REJECTED_102 by {nr.patent_id}", flush=True)
                        break

                if not killed:
                    cr.status = "RESCUE_SURVIVES_102"
                    cr.rationale = f"Claim {attempt} survived 102"
                    cr.novelty_102_result = asdict(attack_result.novelty_results[0]) if attack_result.novelty_results else None
                    print(f"      → RESCUE_SURVIVES_102!", flush=True)

                    # Run 103
                    if attack_result.obviousness_result:
                        cr.obviousness_103_result = asdict(attack_result.obviousness_result)
                        if attack_result.obviousness_result.attack_succeeded:
                            cr.status = "REJECTED_103"
                            cr.rationale = f"Claim {attempt} rejected by 103"
                            print(f"      → REJECTED_103", flush=True)
                        else:
                            cr.status = "RESCUE_SURVIVES_103"
                            cr.rationale = f"Claim {attempt} survived 102 and 103"
                            print(f"      → RESCUE_SURVIVES_103!", flush=True)

                            # Design-around test
                            print(f"      Running design-around test...", flush=True)
                            da = self._test_design_around(claim_text)
                            cr.design_around = da

                            # Check for STRONG_CANDIDATE
                            if da.get("design_around_risk") != "HIGH":
                                cr.status = "RESCUE_STRONG_CANDIDATE"
                                cr.rationale = f"Claim {attempt} survived all attacks + design-around"
                                print(f"      → RESCUE_STRONG_CANDIDATE!", flush=True)

            if attempt == 1:
                result.claim_1 = cr
            else:
                result.claim_2 = cr

            # If survived, stop
            if cr.status in ("RESCUE_SURVIVES_102", "RESCUE_SURVIVES_103", "RESCUE_STRONG_CANDIDATE"):
                break

        # Determine final resolution
        result.final_resolution, result.final_reasoning, result.invention_decision = self._determine_resolution(result)
        result.elapsed_seconds = round(time.time() - t0, 1)
        result.llm_calls = self.llm._call_count

        print(f"\n  → FINAL: {result.final_resolution}", flush=True)
        print(f"     Decision: {result.invention_decision}", flush=True)
        print(f"     Elapsed: {result.elapsed_seconds}s, LLM: {result.llm_calls}", flush=True)

        return result

    def _simulate(self, arch: Dict[str, Any], commercial: Dict[str, Any]) -> SimulationResult:
        """Simulate the architecture to test if it has a real advantage."""
        sys_prompt = """You are a technical simulation analyst. Simulate this architecture change and determine if it provides a real advantage.

Return JSON:
{
  "baseline": "how the current technology performs",
  "new_mechanism": "how the new architecture works differently",
  "predicted_effect": "what improvement is predicted",
  "failure_condition": "under what conditions would this fail",
  "simulated_advantage": true|false,
  "simulation_notes": "brief analysis",
  "status": "ARCHITECTURE_VIABLE|ARCHITECTURE_WEAK"
}

If the proposed mechanism has no simulated advantage, status = ARCHITECTURE_WEAK."""
        user_prompt = f"""Architecture: {arch.get('architecture_id','')}
Type: {arch.get('technical_change_type','')}
Description: {arch.get('description','')}
Material difference: {arch.get('material_difference','')}
New effect: {arch.get('new_technical_effect','')}

Commercial objective: {commercial.get('customer_problem','')}"""
        response, _ = self.llm.chat(sys_prompt, user_prompt, temperature=0.0, max_tokens=600)
        data = self._extract_json(response)
        if data:
            return SimulationResult(
                architecture_id=arch.get("architecture_id", ""),
                baseline=data.get("baseline", ""),
                new_mechanism=data.get("new_mechanism", ""),
                predicted_effect=data.get("predicted_effect", ""),
                failure_condition=data.get("failure_condition", ""),
                simulated_advantage=data.get("simulated_advantage", False),
                simulation_notes=data.get("simulation_notes", ""),
                status=data.get("status", "ARCHITECTURE_WEAK"),
            )
        return SimulationResult(architecture_id=arch.get("architecture_id", ""), status="ARCHITECTURE_WEAK")

    def _design_experiment(self, arch: Dict[str, Any], commercial: Dict[str, Any]) -> ExperimentDesign:
        """Design the cheapest decisive experiment."""
        sys_prompt = """Design the cheapest decisive experiment to validate this architecture's technical effect.

Return JSON:
{
  "independent_variable": "...",
  "dependent_variable": "...",
  "baseline": "...",
  "control": "...",
  "measurement": "...",
  "success_criterion": "...",
  "failure_criterion": "...",
  "falsifier": "...",
  "cheapest_decisive_experiment": "brief description of the cheapest experiment that would decide"
}"""
        user_prompt = f"""Architecture: {arch.get('architecture_id','')}
New effect: {arch.get('new_technical_effect','')}
Material difference: {arch.get('material_difference','')}"""
        response, _ = self.llm.chat(sys_prompt, user_prompt, temperature=0.0, max_tokens=600)
        data = self._extract_json(response)
        if data:
            return ExperimentDesign(architecture_id=arch.get("architecture_id", ""), **data)
        return ExperimentDesign(architecture_id=arch.get("architecture_id", ""))

    def _check_commercial_value(self, arch: Dict[str, Any], commercial: Dict[str, Any]) -> CommercialValueCheck:
        """Check if the redesign preserves commercial value."""
        sys_prompt = """Does this architecture redesign preserve the commercial value?

Return JSON:
{
  "customer_problem": "what problem the buyer faces",
  "economic_value": "what economic value is preserved",
  "manufacturing_consequence": "what manufacturing changes are needed",
  "integration_burden": "how hard is it to integrate",
  "preserves_value": true|false,
  "status": "VALUE_PRESERVED|ABANDON_REDESIGN"
}

If the redesign destroys the commercial value, status = ABANDON_REDESIGN."""
        user_prompt = f"""Architecture: {arch.get('description','')}
Material change: {arch.get('material_difference','')}
Customer problem: {commercial.get('customer_problem','')}
Desired effect: {commercial.get('desired_technical_effect','')}"""
        response, _ = self.llm.chat(sys_prompt, user_prompt, temperature=0.0, max_tokens=500)
        data = self._extract_json(response)
        if data:
            return CommercialValueCheck(architecture_id=arch.get("architecture_id", ""), **data)
        return CommercialValueCheck(architecture_id=arch.get("architecture_id", ""), status="ABANDON_REDESIGN")

    def _construct_clean_claim(self, claim_0_text: str, arch: Dict[str, Any],
                                commercial: Dict[str, Any], version: int) -> str:
        """Construct a clean claim (no 'Claim N:' prefix)."""
        sys_prompt = f"""Construct a new independent patent claim. Return ONLY the claim text — no preamble, no "Claim N:" prefix, no markdown.

Start with "A" or "An" or "A method".

The claim must:
1. Use the material technical distinction: {arch.get('material_difference','')}
2. Create the new technical effect: {arch.get('new_technical_effect','')}
3. Preserve commercial value: {commercial.get('customer_problem','')}
4. NOT be anticipated by: hydrogel coating + nanofiber reinforcement (physical mixing)
5. Change: {arch.get('technical_change_type','')}

Write a proper patent claim with preamble, elements, and relationships."""
        user_prompt = f"""Rejected Claim 0: {claim_0_text[:500]}

Architecture {arch.get('architecture_id','')}: {arch.get('description','')}"""
        response, _ = self.llm.chat(sys_prompt, user_prompt, temperature=0.2, max_tokens=600)
        claim = response.strip()
        # Remove any markdown or prefix
        claim = re.sub(r"^```[a-z]*\s*", "", claim)
        claim = re.sub(r"\s*```$", "", claim)
        claim = re.sub(r"^Claim\s+\d+\s*:?\s*", "", claim, flags=re.IGNORECASE)
        claim = re.sub(r"^#{1,3}\s*", "", claim)
        # Must start with "A" or "An" or "A method"
        if not re.match(r'^(A |An |A method)', claim):
            # Try to find the start
            m = re.search(r'(A (?:method|device|hydrogel|coating|composition|system))', claim, re.IGNORECASE)
            if m:
                claim = claim[m.start():]
            else:
                claim = "A " + claim
        return claim[:2000]

    def _test_design_around(self, claim_text: str) -> Dict[str, Any]:
        """5-workaround design-around test."""
        sys_prompt = """Generate 5 competitor workarounds. Return JSON:
{"workarounds": [{"strategy": "...", "description": "...", "competitor_preserves_value": true|false}], "design_around_risk": "HIGH|MEDIUM|LOW"}"""
        response, _ = self.llm.chat(sys_prompt, f"Claim: {claim_text[:800]}", temperature=0.0, max_tokens=800)
        data = self._extract_json(response)
        return data or {"design_around_risk": "UNKNOWN"}

    def _determine_resolution(self, result: RescueV2Result) -> Tuple[str, str, str]:
        """Determine final resolution + invention decision."""
        for cr in [result.claim_1, result.claim_2]:
            if cr and cr.status == "RESCUE_STRONG_CANDIDATE":
                return ("RESCUE_STRONG_CANDIDATE",
                        f"Claim {cr.version} survived all attacks + design-around",
                        "INVENTION_ALIVE")
            if cr and cr.status == "RESCUE_SURVIVES_103":
                return ("RESCUE_SURVIVES_103",
                        f"Claim {cr.version} survived 102 and 103",
                        "INVENTION_ALIVE")
            if cr and cr.status == "RESCUE_SURVIVES_102":
                return ("RESCUE_SURVIVES_102",
                        f"Claim {cr.version} survived 102",
                        "INVENTION_ALIVE")

        # Check if any claim was constructed but pending evidence
        for cr in [result.claim_1, result.claim_2]:
            if cr and cr.status == "RESCUE_PENDING_EVIDENCE":
                return ("RESCUE_PENDING_EVIDENCE",
                        f"Claim {cr.version} constructed but 0 GOLD evidence (NOT novel — insufficient evidence)",
                        "INVENTION_REDESIGN_REQUIRED")

        # All rejected or not constructed
        any_constructed = any(cr for cr in [result.claim_1, result.claim_2] if cr)
        if any_constructed:
            return ("RESCUE_ABANDONED", "All claim versions rejected", "INVENTION_ABANDONED")
        return ("RESCUE_ABANDONED", "No claims could be constructed", "INVENTION_ABANDONED")
