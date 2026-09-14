"""
Invention Rescue Framework
===========================

After Claim 0 is rejected by 102, test whether the underlying invention
can survive through material technical redesign.

ARCHITECTURE:
  1. Freeze Claim 0 (REJECTED_102 status preserved)
  2. Extract the kill (killing reference, elements, relationships, arrangement)
  3. Preserve commercial objective (don't abandon value)
  4. Generate 3 alternative architectures (material technical change, not lexical)
  5. Claim 1: new independent claim around strongest material distinction
  6. Full re-search: concept graph + 10 query families + multi-database
  7. New 102 attack on Claim 1
  8. 103 attack if Claim 1 survives 102
  9. Claim 2 if Claim 1 fails
  10. Independent invention test if all 3 fail

FIREWALLS:
  - Do NOT weaken the 102 rejection
  - Do NOT relabel rejected claim as novel
  - Do NOT merely rename components or change dimensions
  - Do NOT add meaningless parameters
  - Do NOT force ELITE
  - Do NOT claim unproven technical effects as demonstrated
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
    RetrievalV4, ConceptGraph, QueryFamilyGenerator,
    PatentRelevanceGate, CPCExpander, FamilyDeduplicator,
)
from discovery_fabric.prior_art_v2.retrieval_v3 import fetch_patent_full, PatentRecord
from discovery_fabric.prior_art_v2.claim_attack import (
    ClaimAttackAuditor, ClaimAttackResult, ClaimElement,
    ElementMatrixEntry, NoveltyResult,
)
from discovery_fabric.prior_art_v2.forensic_review import (
    ObviousnessAttackForensic, EliteGateResult,
)


# ----------------------- DATA SCHEMAS -----------------------
@dataclass
class KillingReference:
    """The patent that killed Claim 0."""
    patent_id: str = ""
    title: str = ""
    claim_number: str = ""
    killing_elements: List[str] = field(default_factory=list)
    killing_relationships: List[str] = field(default_factory=list)
    killing_arrangement: str = ""
    exact_disclosed_elements: List[Dict[str, str]] = field(default_factory=list)
    what_was_already_disclosed: str = ""


@dataclass
class CommercialObjective:
    """The commercial value that should be preserved through redesign."""
    customer_problem: str = ""
    economic_value_hypothesis: str = ""
    desired_technical_effect: str = ""


@dataclass
class ArchitectureAlternative:
    """One alternative architecture with material technical change."""
    architecture_id: str  # V1, V2, V3
    technical_change_type: str  # structure | relationship | mechanism | operating_condition | material_process | control_logic
    description: str = ""
    material_difference: str = ""
    new_technical_effect: str = ""
    preserves_commercial_value: bool = False
    commercial_value_note: str = ""


@dataclass
class ClaimVersionResult:
    """One claim version (0, 1, or 2) with its attack results."""
    version: int
    claim_text: str
    claim_hash: str
    status: str = ""  # REJECTED_102 / SURVIVED_102 / SURVIVED_103 / REJECTED_103
    search_result: Optional[Dict[str, Any]] = None
    novelty_102_result: Optional[NoveltyResult] = None
    obviousness_103_result: Optional[ObviousnessAttackForensic] = None
    killing_patent: Optional[str] = None
    rationale: str = ""


@dataclass
class RescueResult:
    """Complete rescue result for one invention."""
    invention_id: str = ""
    claim_0: Optional[ClaimVersionResult] = None
    killing_reference: KillingReference = field(default_factory=KillingReference)
    commercial_objective: CommercialObjective = field(default_factory=CommercialObjective)
    architecture_alternatives: List[ArchitectureAlternative] = field(default_factory=list)
    claim_1: Optional[ClaimVersionResult] = None
    claim_2: Optional[ClaimVersionResult] = None
    final_resolution: str = ""  # CLAIM_REJECTED_INVENTION_RESCUED / CLAIM_REJECTED_INVENTION_ABANDONED / CLAIM_SURVIVES_102_REQUIRES_103_REVIEW / STRONG_CANDIDATE_FOR_ATTORNEY_REVIEW
    final_reasoning: str = ""
    timestamp: str = ""
    llm_calls: int = 0
    elapsed_seconds: float = 0.0


# ----------------------- RESCUE AUDITOR -----------------------

class RescueAuditor:
    """Runs the invention rescue loop."""

    def _extract_json_from_response(self, response: str) -> Optional[dict]:
        """Extract JSON from LLM response that may have prose around it."""
        # Try direct parse
        try:
            return json.loads(response.strip())
        except:
            pass
        # Try stripping markdown fences
        clean = re.sub(r"^```(?:json)?\s*", "", response.strip())
        clean = re.sub(r"\s*```$", "", clean)
        try:
            return json.loads(clean)
        except:
            pass
        # Try finding JSON object in the response
        start = response.find("{")
        if start < 0:
            return None
        depth = 0
        for i in range(start, len(response)):
            if response[i] == "{":
                depth += 1
            elif response[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(response[start:i+1])
                    except:
                        pass
        return None

    def __init__(self, llm: Optional[LLMClient] = None):
        self.llm = llm or LLMClient()
        self.retriever = RetrievalV4(llm=llm)
        self.claim_auditor = ClaimAttackAuditor(llm=llm)

    def rescue(self, invention_id: str, claim_0_text: str,
               claim_0_result: ClaimAttackResult) -> RescueResult:
        """Run the full rescue loop for one invention."""
        t0 = time.time()
        print(f"\n{'='*60}", flush=True)
        print(f"  INVENTION RESCUE: {invention_id}", flush=True)
        print(f"{'='*60}", flush=True)

        # STEP 1: Freeze Claim 0
        print(f"  [1] Freezing Claim 0 (REJECTED_102)...", flush=True)
        claim_0 = ClaimVersionResult(
            version=0,
            claim_text=claim_0_text,
            claim_hash=_sha256(claim_0_text),
            status="REJECTED_102",
        )

        # Find the killing patent
        killing_nr = None
        for nr in claim_0_result.novelty_results:
            if nr.novelty_attacked:
                killing_nr = nr
                claim_0.killing_patent = nr.patent_id
                break

        result = RescueResult(
            invention_id=invention_id,
            claim_0=claim_0,
            killing_reference=KillingReference(patent_id=""),
            timestamp=_now_utc(),
        )

        if not killing_nr:
            print(f"      No 102 kill found — Claim 0 not rejected", flush=True)
            claim_0.status = "NOT_REJECTED"
            result.final_resolution = "CLAIM_SURVIVES_102_REQUIRES_103_REVIEW"
            result.final_reasoning = "Claim 0 was not rejected by 102"
            result.elapsed_seconds = round(time.time() - t0, 1)
            return result

        # STEP 2: Extract the kill
        print(f"  [2] Extracting the kill...", flush=True)
        result.killing_reference = self._extract_kill(killing_nr, claim_0_result)
        print(f"      Killing patent: {result.killing_reference.patent_id}", flush=True)
        print(f"      Already disclosed: {result.killing_reference.what_was_already_disclosed[:200]}", flush=True)

        # STEP 3: Preserve commercial objective
        print(f"  [3] Preserving commercial objective...", flush=True)
        result.commercial_objective = self._extract_commercial_objective(claim_0_text, invention_id)
        print(f"      Problem: {result.commercial_objective.customer_problem[:100]}", flush=True)

        # STEP 4: Generate 3 alternative architectures
        print(f"  [4] Generating 3 alternative architectures...", flush=True)
        result.architecture_alternatives = self._generate_architectures(
            claim_0_text, result.killing_reference, result.commercial_objective)
        for arch in result.architecture_alternatives:
            print(f"      {arch.architecture_id}: {arch.technical_change_type} — {arch.material_difference[:80]}", flush=True)

        # STEP 5-9: Try Claim 1 and Claim 2
        for attempt in range(1, 3):  # Claim 1, Claim 2
            print(f"\n  [{5+attempt-1}] Constructing Claim {attempt}...", flush=True)
            best_arch = result.architecture_alternatives[attempt-1] if attempt <= len(result.architecture_alternatives) else None

            new_claim_text = self._construct_claim(
                claim_0_text, result.killing_reference, result.commercial_objective,
                best_arch, attempt)

            if not new_claim_text:
                print(f"      Could not construct Claim {attempt}", flush=True)
                continue

            print(f"      Claim {attempt}: {new_claim_text[:100]}...", flush=True)

            # Full re-search
            print(f"      Re-searching prior art...", flush=True)
            retrieval_result = self.retriever.retrieve(invention_id, new_claim_text)

            # Get GOLD patents
            gold_patents = []
            for rp in retrieval_result.retrieved_patents:
                if rp.is_gold:
                    gold_patents.append(asdict(rp))

            # Build claim version result
            claim_version = ClaimVersionResult(
                version=attempt,
                claim_text=new_claim_text,
                claim_hash=_sha256(new_claim_text),
            )

            if not gold_patents:
                print(f"      No GOLD patents found — cannot test 102", flush=True)
                claim_version.status = "INSUFFICIENT_EVIDENCE"
                claim_version.rationale = "No GOLD patents from re-search"
                if attempt == 1:
                    result.claim_1 = claim_version
                else:
                    result.claim_2 = claim_version
                continue

            # Run 102 attack
            print(f"      Running 102 attack with {len(gold_patents)} GOLD patents...", flush=True)
            attack_result = self.claim_auditor.attack(invention_id, new_claim_text, gold_patents)

            # Check if any 102 succeeded
            killed = False
            for nr in attack_result.novelty_results:
                if nr.novelty_attacked:
                    claim_version.status = "REJECTED_102"
                    claim_version.killing_patent = nr.patent_id
                    claim_version.novelty_102_result = nr
                    claim_version.rationale = f"Claim {attempt} rejected by 102: {nr.patent_id} anticipates"
                    killed = True
                    print(f"      → REJECTED_102 by {nr.patent_id}", flush=True)
                    break

            if not killed:
                # Survived 102 — run 103
                claim_version.status = "SURVIVED_102"
                claim_version.novelty_102_result = attack_result.novelty_results[0] if attack_result.novelty_results else None
                print(f"      → SURVIVED 102", flush=True)

                if attack_result.obviousness_result:
                    claim_version.obviousness_103_result = attack_result.obviousness_result
                    if attack_result.obviousness_result.attack_succeeded:
                        claim_version.status = "REJECTED_103"
                        claim_version.rationale = f"Claim {attempt} rejected by 103"
                        print(f"      → REJECTED_103", flush=True)
                    else:
                        claim_version.status = "SURVIVED_103"
                        claim_version.rationale = f"Claim {attempt} survived 102 and 103"
                        print(f"      → SURVIVED 103!", flush=True)

            if attempt == 1:
                result.claim_1 = claim_version
            else:
                result.claim_2 = claim_version

            # If survived, stop
            if claim_version.status in ("SURVIVED_102", "SURVIVED_103"):
                break

        # STEP 11: Determine final resolution
        result.final_resolution, result.final_reasoning = self._determine_resolution(result)
        result.elapsed_seconds = round(time.time() - t0, 1)
        result.llm_calls = self.llm._call_count

        print(f"\n  → FINAL RESOLUTION: {result.final_resolution}", flush=True)
        print(f"     {result.final_reasoning}", flush=True)
        print(f"     Elapsed: {result.elapsed_seconds}s, LLM: {result.llm_calls}", flush=True)

        return result

    def _extract_kill(self, killing_nr: NoveltyResult,
                      claim_0_result: ClaimAttackResult) -> KillingReference:
        """Extract what exactly was already disclosed."""
        kr = KillingReference(
            patent_id=killing_nr.patent_id,
            title="",
            killing_elements=killing_nr.elements_found,
            killing_arrangement=killing_nr.rationale,
        )

        # Get patent title and claims
        for gp in claim_0_result.gold_patents_data:
            if gp["patent_id"] == killing_nr.patent_id:
                kr.title = gp.get("title", "")
                kr.claim_number = f"claim_1"
                break

        # Use LLM to identify exactly what was disclosed
        sys_prompt = """You are a patent analyst. The claim was rejected because a prior-art patent anticipates it (102).

Identify EXACTLY what technical combination was already disclosed. Do NOT say "similar invention."

Name the specific:
1. Killing elements (which claim elements were disclosed)
2. Killing relationships (which A→B relationships were disclosed)
3. Killing arrangement (how the elements were arranged)
4. What was already disclosed (the specific technical combination)

Return JSON:
{
  "killing_elements": ["A: hydrogel coating", "B: nanofiber reinforcement", ...],
  "killing_relationships": ["nanofibers embedded in hydrogel matrix", ...],
  "killing_arrangement": "specific arrangement description",
  "what_was_already_disclosed": "The prior art already teaches: [specific technical combination]"
}"""

        # Get the killing patent's claims
        killing_claims = []
        for gp in claim_0_result.gold_patents_data:
            if gp["patent_id"] == killing_nr.patent_id:
                killing_claims = gp.get("claims", [])[:3]
                break

        user_prompt = f"""Killing patent: {killing_nr.patent_id}
Title: {kr.title}
Patent claims: {" ".join(killing_claims)[:1000]}

Rejected claim elements found: {killing_nr.elements_found}
Arrangement disclosed: {killing_nr.arrangement_disclosed}"""

        response, _ = self.llm.chat(sys_prompt, user_prompt, temperature=0.0, max_tokens=800)
        data = self._extract_json_from_response(response)
        if data:
            kr.killing_elements = data.get("killing_elements", [])
            kr.killing_relationships = data.get("killing_relationships", [])
            kr.killing_arrangement = data.get("killing_arrangement", "")
            kr.what_was_already_disclosed = data.get("what_was_already_disclosed", "")
        else:
            kr.what_was_already_disclosed = response[:500]

        return kr

    def _extract_commercial_objective(self, claim_text: str, inv_id: str) -> CommercialObjective:
        """Extract the commercial objective that should be preserved."""
        sys_prompt = """Extract the commercial objective of this invention. Even though the claim was rejected, the underlying problem may still be valuable.

Return JSON:
{
  "customer_problem": "what problem does the buyer face?",
  "economic_value_hypothesis": "what economic value would the invention create?",
  "desired_technical_effect": "what technical effect is desired?"
}"""
        user_prompt = f"Invention: {inv_id}\nClaim: {claim_text[:1000]}"
        response, _ = self.llm.chat(sys_prompt, user_prompt, temperature=0.0, max_tokens=500)
        data = self._extract_json_from_response(response)
        if data:
            try:
                return CommercialObjective(**data)
            except TypeError:
                return CommercialObjective(
                    customer_problem=data.get("customer_problem", ""),
                    economic_value_hypothesis=data.get("economic_value_hypothesis", ""),
                    desired_technical_effect=data.get("desired_technical_effect", ""),
                )
        return CommercialObjective()

    def _generate_architectures(self, claim_0_text: str, killing_ref: KillingReference,
                                 commercial: CommercialObjective) -> List[ArchitectureAlternative]:
        """Generate 3 alternative architectures with material technical change."""
        sys_prompt = """You are a patent inventor. The current claim was rejected because prior art already discloses the technical combination.

Generate 3 ALTERNATIVE ARCHITECTURES that change a REAL technical property. Do NOT:
- Rename components
- Change dimensions arbitrarily
- Add meaningless parameters
- Change terminology

Each architecture MUST change one of:
- structure (how components are physically arranged)
- relationship (how components interact)
- mechanism (the underlying physical/chemical mechanism)
- operating condition (the conditions under which it operates)
- material/process interaction (how materials interact differently)
- control logic (how the system is controlled)

Each must preserve the commercial value while creating a MATERIAL technical distinction.

Return JSON:
{
  "architectures": [
    {
      "architecture_id": "V1",
      "technical_change_type": "structure|relationship|mechanism|operating_condition|material_process|control_logic",
      "description": "what the new architecture looks like",
      "material_difference": "what is materially different from the prior art",
      "new_technical_effect": "what new technical effect this creates",
      "preserves_commercial_value": true|false,
      "commercial_value_note": "how commercial value is preserved"
    },
    ... (3 total)
  ]
}"""

        user_prompt = f"""Rejected claim: {claim_0_text[:800]}

What was already disclosed: {killing_ref.what_was_already_disclosed[:500]}

Commercial objective:
- Problem: {commercial.customer_problem}
- Desired effect: {commercial.desired_technical_effect}"""

        response, _ = self.llm.chat(sys_prompt, user_prompt, temperature=0.3, max_tokens=1500)
        data = self._extract_json_from_response(response)
        if data:
            if isinstance(data, dict):
                archs = data.get("architectures", [])
            elif isinstance(data, list):
                archs = data
            else:
                archs = []
            result = []
            for a in archs[:3]:
                if isinstance(a, dict):
                    try:
                        result.append(ArchitectureAlternative(**a))
                    except TypeError:
                        result.append(ArchitectureAlternative(
                            architecture_id=a.get("architecture_id", ""),
                            technical_change_type=a.get("technical_change_type", ""),
                            description=a.get("description", ""),
                            material_difference=a.get("material_difference", ""),
                            new_technical_effect=a.get("new_technical_effect", ""),
                            preserves_commercial_value=a.get("preserves_commercial_value", False),
                            commercial_value_note=a.get("commercial_value_note", ""),
                        ))
            return result
        return []

    def _construct_claim(self, claim_0_text: str, killing_ref: KillingReference,
                          commercial: CommercialObjective,
                          architecture: Optional[ArchitectureAlternative],
                          version: int) -> str:
        """Construct a new independent claim around the material distinction."""
        if not architecture:
            return ""

        sys_prompt = f"""You are a patent claim drafter. Construct a new independent claim (Claim {version}) that:

1. Preserves the commercial value: {commercial.customer_problem}
2. Uses the material technical distinction: {architecture.material_difference}
3. Creates a new technical effect: {architecture.new_technical_effect}
4. Is NOT anticipated by the killing patent (which disclosed: {killing_ref.what_was_already_disclosed[:300]})
5. Does NOT merely rename components or change dimensions
6. Changes a real technical property: {architecture.technical_change_type}

Return ONLY the claim text (no preamble). Start with "A" or "An" or "A method".

The claim must be a valid patent claim with:
- A preamble
- Elements with structural/functional requirements
- Relationships between elements
- The material distinguishing feature"""

        user_prompt = f"""Rejected Claim 0: {claim_0_text[:500]}

Architecture {architecture.architecture_id}:
- Type: {architecture.technical_change_type}
- Description: {architecture.description}
- Material difference: {architecture.material_difference}
- New effect: {architecture.new_technical_effect}"""

        response, _ = self.llm.chat(sys_prompt, user_prompt, temperature=0.2, max_tokens=800)
        # Clean up
        claim = response.strip()
        # Remove any markdown
        claim = re.sub(r"^```[a-z]*\s*", "", claim)
        claim = re.sub(r"\s*```$", "", claim)
        # Must start with "A" or "An" or "A method"
        if not re.match(r'^(A |An |A method)', claim):
            claim = "A " + claim
        return claim[:2000]

    def _determine_resolution(self, result: RescueResult) -> Tuple[str, str]:
        """Determine the final resolution."""
        # Check if any claim survived
        for cv in [result.claim_1, result.claim_2]:
            if cv and cv.status == "SURVIVED_103":
                return "STRONG_CANDIDATE_FOR_ATTORNEY_REVIEW", f"Claim {cv.version} survived 102 and 103"
            if cv and cv.status == "SURVIVED_102":
                return "CLAIM_SURVIVES_102_REQUIRES_103_REVIEW", f"Claim {cv.version} survived 102 but 103 not fully evaluated"

        # Check if rescued but needs 103 review
        for cv in [result.claim_1, result.claim_2]:
            if cv and cv.status == "INSUFFICIENT_EVIDENCE":
                return "CLAIM_REJECTED_INVENTION_RESCUED", f"Claim {cv.version} constructed but insufficient GOLD evidence for attack"

        # All claims rejected or no claims constructed
        return "CLAIM_REJECTED_INVENTION_ABANDONED", "All claim versions rejected or could not be constructed"
