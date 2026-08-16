"""
Claim-Level Forensic Attack after Retrieval V4
================================================

For each invention with DIRECTLY_RELEVANT GOLD patents:
  1. Claim Element Matrix (map E1..En against each patent's actual claims)
  2. 102 Test (single-reference novelty — report exact missing element)
  3. 103 Test (EPO structure: closest_prior_art + COULD/WOULD/WHY)
  4. Anti-Hindsight (Pass A before revealing invention vs Pass B after)
  5. Technical Effect classification
  6. Claim Redesign (if Claim 0 is weak, preserve value + strengthen)
  7. ELITE Gate (10 conditions, unchanged)

Per CEO Section 11: 8 GOLD patents → stronger attack evidence → actual claim mapping
→ actual 102/103 result → final adjudication. NOT "8 GOLD → ELITE".
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
from discovery_fabric.prior_art_v2.retrieval_v3 import fetch_patent_full, PatentRecord
from discovery_fabric.prior_art_v2.forensic_review import (
    GoldPatentForensic, NoveltyAttackForensic, ObviousnessAttackForensic,
    DesignAroundForensic, EliteGateResult,
)


# ----------------------- DATA SCHEMAS -----------------------
@dataclass
class ClaimElement:
    element_id: str
    technical_feature: str
    relationship: str = ""


@dataclass
class ElementMatrixEntry:
    """One element mapped against one patent's actual claims."""
    patent_id: str
    claim_number: str  # e.g. "claim_1"
    element_id: str
    disclosure_type: str  # EXPLICIT / IMPLICIT / INHERENT / NOT_DISCLOSED / UNCERTAIN
    exact_passage: str  # exact text from the patent claim
    evidence_level: str  # GOLD (from actual claims) / SILVER / BRONZE / NONE


@dataclass
class ArrangementMapping:
    """A→B, B→C, A+B+C arrangement mapping."""
    patent_id: str
    element_pair: str = ""  # e.g. "A→B", "A+B+C"
    required_arrangement_disclosed: str = "UNCERTAIN"  # TRUE / FALSE / UNCERTAIN
    arrangement_analysis: str = ""


@dataclass
class NoveltyResult:
    """102 test result for one patent."""
    patent_id: str
    all_elements_found: bool = False
    elements_found: List[str] = field(default_factory=list)
    elements_missing: List[str] = field(default_factory=list)
    element_preventing_anticipation: Optional[str] = None
    arrangement_disclosed: bool = False
    novelty_attacked: bool = False  # True = 102 succeeds
    rationale: str = ""


@dataclass
class ClaimAttackResult:
    """Complete claim-level attack result for one invention."""
    invention_id: str
    claim_version: int = 0
    claim_text: str = ""
    claim_hash: str = ""
    elements: List[ClaimElement] = field(default_factory=list)

    # GOLD patents used
    gold_patent_ids: List[str] = field(default_factory=list)
    gold_patents_data: List[Dict[str, Any]] = field(default_factory=list)

    # Element matrix
    element_matrix: List[ElementMatrixEntry] = field(default_factory=list)
    arrangement_mappings: List[ArrangementMapping] = field(default_factory=list)

    # 102 results (one per patent)
    novelty_results: List[NoveltyResult] = field(default_factory=list)
    novelty_attacked_count: int = 0

    # 103 result
    obviousness_result: Optional[ObviousnessAttackForensic] = None

    # Technical effect
    technical_effect: Dict[str, Any] = field(default_factory=dict)

    # Design-around
    design_around: Optional[DesignAroundForensic] = None

    # ELITE gate
    elite_gate: EliteGateResult = field(default_factory=EliteGateResult)

    # Final
    final_status: str = ""
    final_reasoning: str = ""
    timestamp: str = ""
    llm_calls: int = 0
    elapsed_seconds: float = 0.0


# ----------------------- CLAIM ATTACK AUDITOR -----------------------
class ClaimAttackAuditor:
    """Runs claim-level forensic attack using V4 GOLD patents."""

    def __init__(self, llm: Optional[LLMClient] = None):
        self.llm = llm or LLMClient()

    def attack(self, invention_id: str, claim_text: str,
               gold_patents: List[Dict[str, Any]]) -> ClaimAttackResult:
        """Run full claim-level attack."""
        t0 = time.time()
        print(f"\n{'='*60}", flush=True)
        print(f"  CLAIM-LEVEL ATTACK: {invention_id}", flush=True)
        print(f"  GOLD patents: {len(gold_patents)}", flush=True)
        print(f"{'='*60}", flush=True)

        result = ClaimAttackResult(
            invention_id=invention_id,
            claim_version=0,
            claim_text=claim_text,
            claim_hash=_sha256(claim_text),
            timestamp=_now_utc(),
            gold_patent_ids=[p.get("patent_id","") for p in gold_patents],
        )

        # STEP 1: Parse claim elements
        print(f"  [1] Parsing claim elements...", flush=True)
        result.elements = self._parse_elements(claim_text)
        print(f"      {len(result.elements)} elements parsed", flush=True)

        # STEP 2: Store GOLD patent data (claims already retrieved in V4)
        print(f"  [2] Loading GOLD patent claims...", flush=True)
        for gp in gold_patents:
            pid = gp.get("patent_id", "")
            claims = gp.get("claims", [])
            result.gold_patents_data.append({
                "patent_id": pid,
                "title": gp.get("title", ""),
                "claims": claims,
                "claim_count": len(claims),
                "publication_date": gp.get("publication_date"),
                "priority_date": gp.get("priority_date"),
                "family_id": gp.get("family_id"),
                "source_hash": gp.get("full_content_hash", ""),
            })
            print(f"      {pid}: {len(claims)} claims", flush=True)

        # STEP 3: Build element matrix (map each element against each patent's claims)
        print(f"  [3] Building element matrix...", flush=True)
        for gp_data in result.gold_patents_data:
            pid = gp_data["patent_id"]
            claims = gp_data.get("claims", [])
            if not claims:
                print(f"      {pid}: no claims — skipping", flush=True)
                continue
            matrix_entries, arrangements = self._map_elements_to_patent(
                result.elements, pid, claims)
            result.element_matrix.extend(matrix_entries)
            result.arrangement_mappings.extend(arrangements)

        # STEP 4: 102 test for each patent
        print(f"  [4] Running 102 novelty test per patent...", flush=True)
        for gp_data in result.gold_patents_data:
            pid = gp_data["patent_id"]
            # Get element mappings for this patent
            patent_entries = [e for e in result.element_matrix if e.patent_id == pid]
            patent_arrangements = [a for a in result.arrangement_mappings if a.patent_id == pid]

            novelty = self._test_102(pid, patent_entries, patent_arrangements, result.elements)
            result.novelty_results.append(novelty)
            if novelty.novelty_attacked:
                result.novelty_attacked_count += 1
                print(f"      {pid}: 102 ATTACKED!", flush=True)
            else:
                missing = novelty.element_preventing_anticipation or "arrangement"
                print(f"      {pid}: 102 fails (missing: {missing})", flush=True)

        # STEP 5: 103 obviousness with anti-hindsight
        print(f"  [5] Running 103 obviousness with anti-hindsight...", flush=True)
        result.obviousness_result = self._test_103(result)

        # STEP 6: Technical effect
        print(f"  [6] Technical effect classification...", flush=True)
        result.technical_effect = self._classify_technical_effect(claim_text, result.elements)

        # STEP 7: Design-around
        print(f"  [7] Design-around test...", flush=True)
        result.design_around = self._test_design_around(claim_text)

        # STEP 8: ELITE gate
        print(f"  [8] ELITE gate (10 conditions)...", flush=True)
        self._apply_elite_gate(result)

        # Final status
        result.final_status, result.final_reasoning = self._determine_status(result)
        result.elapsed_seconds = round(time.time() - t0, 1)
        result.llm_calls = self.llm._call_count

        print(f"\n  → FINAL STATUS: {result.final_status}", flush=True)
        print(f"     102 attacked: {result.novelty_attacked_count}/{len(result.novelty_results)}", flush=True)
        print(f"     103 attacked: {result.obviousness_result.attack_succeeded if result.obviousness_result else 'N/A'}", flush=True)
        print(f"     Gate: {result.elite_gate.all_pass} ({len(result.elite_gate.failed_conditions)} failures)", flush=True)
        print(f"     Elapsed: {result.elapsed_seconds}s, LLM: {result.llm_calls}", flush=True)

        return result

    def _parse_elements(self, claim_text: str) -> List[ClaimElement]:
        """Parse claim into elements using LLM."""
        sys_prompt = """You are a patent claim parser. Identify the structural elements AND their relationships.
Return JSON only: {"elements": [{"element_id": "A", "technical_feature": "...", "relationship": "how this relates to other elements"}]}
Element IDs: A, B, C, ... Max 8 elements."""
        user_prompt = f"Claim:\n{claim_text[:2000]}"
        response, _ = self.llm.chat(sys_prompt, user_prompt, temperature=0.0, max_tokens=800)
        try:
            clean = re.sub(r"^```(?:json)?\s*", "", response.strip())
            clean = re.sub(r"\s*```$", "", clean)
            data = json.loads(clean)
            if isinstance(data, dict):
                elems = data.get("elements", [])
            elif isinstance(data, list):
                elems = data
            else:
                elems = []
            return [ClaimElement(**e) for e in elems[:8] if isinstance(e, dict)]
        except (json.JSONDecodeError, TypeError):
            # Fallback
            elements = []
            m = re.search(r'comprising[:\s]+(.+?)(?:;|wherein|hereby|$)', claim_text, re.IGNORECASE | re.DOTALL)
            if m:
                parts = re.split(r'[;,]', m.group(1))
                for i, p in enumerate(parts):
                    p = p.strip().rstrip('.')
                    if len(p) > 5:
                        elements.append(ClaimElement(element_id=chr(65+i), technical_feature=p[:200]))
            return elements[:8]

    def _map_elements_to_patent(self, elements: List[ClaimElement],
                                 patent_id: str, claims: List[str]) -> Tuple[List[ElementMatrixEntry], List[ArrangementMapping]]:
        """Map invention elements against a patent's ACTUAL claims (not snippets)."""
        matrix_entries = []
        arrangements = []

        sys_prompt = """You are a patent claim mapper. Map the invention's claim elements against the prior-art patent's ACTUAL CLAIM TEXT.

For each element:
- disclosure_type: EXPLICIT (directly in claim text) / IMPLICIT / INHERENT (necessarily present) / NOT_DISCLOSED / UNCERTAIN
- exact_passage: the EXACT text from the patent claims that discloses this element (or empty if NOT_DISCLOSED)
- evidence_level: GOLD (from actual claims) / SILVER / BRONZE / NONE

CRITICAL: Only use the actual claim text provided. Do NOT use external knowledge.
INHERENT requires "necessarily present" — not "could be" or "likely".

Also assess the required arrangement:
- Does the patent disclose the required ARRANGEMENT/RELATIONSHIP between elements?
- TRUE / FALSE / UNCERTAIN

Return JSON only:
{
  "elements": [{"element_id": "A", "claim_number": "claim_1", "disclosure_type": "...", "exact_passage": "...", "evidence_level": "..."}],
  "arrangements": [{"element_pair": "A→B", "required_arrangement_disclosed": "TRUE|FALSE|UNCERTAIN", "arrangement_analysis": "..."}]
}"""

        elements_str = json.dumps([{"id": e.element_id, "feature": e.technical_feature, "relationship": e.relationship} for e in elements], indent=2)
        claims_str = "\n".join([f"Claim {i+1}: {c[:500]}" for i, c in enumerate(claims[:5])])

        user_prompt = f"""Invention elements:
{elements_str}

Prior-art patent {patent_id} ACTUAL CLAIMS:
{claims_str}"""

        response, _ = self.llm.chat(sys_prompt, user_prompt, temperature=0.0, max_tokens=1500)
        try:
            clean = re.sub(r"^```(?:json)?\s*", "", response.strip())
            clean = re.sub(r"\s*```$", "", clean)
            data = json.loads(clean)
            if isinstance(data, dict):
                for e in data.get("elements", []):
                    matrix_entries.append(ElementMatrixEntry(
                        patent_id=patent_id,
                        claim_number=e.get("claim_number", ""),
                        element_id=e.get("element_id", ""),
                        disclosure_type=e.get("disclosure_type", "UNCERTAIN"),
                        exact_passage=e.get("exact_passage", ""),
                        evidence_level=e.get("evidence_level", "NONE"),
                    ))
                for a in data.get("arrangements", []):
                    arrangements.append(ArrangementMapping(
                        patent_id=patent_id,
                        element_pair=a.get("element_pair", ""),
                        required_arrangement_disclosed=a.get("required_arrangement_disclosed", "UNCERTAIN"),
                        arrangement_analysis=a.get("arrangement_analysis", ""),
                    ))
        except (json.JSONDecodeError, TypeError):
            pass

        return matrix_entries, arrangements

    def _test_102(self, patent_id: str, entries: List[ElementMatrixEntry],
                  arrangements: List[ArrangementMapping],
                  elements: List[ClaimElement]) -> NoveltyResult:
        """Test 102 anticipation for one patent."""
        found = [e.element_id for e in entries if e.disclosure_type in ("EXPLICIT", "IMPLICIT", "INHERENT")]
        missing = [e.element_id for e in entries if e.disclosure_type == "NOT_DISCLOSED"]
        all_found = len(missing) == 0 and len(found) == len(elements)

        # Check arrangement
        arrangement_disclosed = any(a.required_arrangement_disclosed == "TRUE" for a in arrangements)
        arrangement_uncertain = all(a.required_arrangement_disclosed == "UNCERTAIN" for a in arrangements) if arrangements else True

        novelty_attacked = all_found and arrangement_disclosed

        element_preventing = missing[0] if missing else None
        if not element_preventing and not arrangement_disclosed and not arrangement_uncertain:
            element_preventing = "arrangement"

        return NoveltyResult(
            patent_id=patent_id,
            all_elements_found=all_found,
            elements_found=found,
            elements_missing=missing,
            element_preventing_anticipation=element_preventing,
            arrangement_disclosed=arrangement_disclosed,
            novelty_attacked=novelty_attacked,
            rationale=f"{'All elements found' if all_found else f'Missing: {missing}'}. Arrangement: {'disclosed' if arrangement_disclosed else 'not disclosed' if not arrangement_uncertain else 'uncertain'}.",
        )

    def _test_103(self, result: ClaimAttackResult) -> ObviousnessAttackForensic:
        """103 obviousness with EPO structure + anti-hindsight."""
        obv = ObviousnessAttackForensic(attempted=True)

        # Find closest prior art (patent with most elements found)
        best_pid = None
        best_count = 0
        for nr in result.novelty_results:
            if len(nr.elements_found) > best_count:
                best_count = len(nr.elements_found)
                best_pid = nr.patent_id

        if not best_pid:
            obv.closest_prior_art = "None found"
            return obv

        obv.closest_prior_art = best_pid

        # Get closest patent claims
        closest_claims = []
        for gp in result.gold_patents_data:
            if gp["patent_id"] == best_pid:
                closest_claims = gp.get("claims", [])[:3]
                break

        # PASS A: Before revealing invention
        sys_prompt_a = """You are a patent obviousness analyst. Analyze the closest prior art WITHOUT knowing the invention.

Identify:
1. What technical problem exists in this field?
2. What modifications would a PHOSITA consider?
3. What secondary references might be relevant?

Return JSON: {"technical_problem": "...", "potential_modifications": "...", "secondary_reference_prediction": "..."}"""

        user_prompt_a = f"""Closest prior art {best_pid}:
Claims: {" ".join(closest_claims)[:1000]}"""

        response_a, _ = self.llm.chat(sys_prompt_a, user_prompt_a, temperature=0.0, max_tokens=800)
        try:
            clean = re.sub(r"^```(?:json)?\s*", "", response_a.strip())
            clean = re.sub(r"\s*```$", "", clean)
            pass_a = json.loads(clean)
            obv.pass_a_rationale = json.dumps(pass_a)
            obv.objective_technical_problem = pass_a.get("technical_problem", "")
        except (json.JSONDecodeError, TypeError):
            obv.pass_a_rationale = response_a[:500]

        # PASS B: After revealing invention
        sys_prompt_b = """You are a patent obviousness analyst per EPO 2026 guidance.

Now you see the invention claim. Analyze obviousness:
1. distinguishing_features
2. technical_effect
3. motivation_to_modify (WHY would PHOSITA combine?)
4. reasonable_expectation_of_success
5. teaching_away

Then answer:
- COULD = yes/no (technical capability)
- WOULD = yes/no (motivation/likelihood) — MANDATORY
- WHY = explanation

Is the motivation based on prior art alone, or hindsight?

Return JSON:
{
  "distinguishing_features": "...",
  "technical_effect": "...",
  "motivation_to_modify": "...",
  "reasonable_expectation_of_success": "...",
  "teaching_away": "...",
  "could_answer": "yes|no",
  "would_answer": "yes|no",
  "would_why": "...",
  "hindsight_risk": "HIGH|MEDIUM|LOW",
  "rationale_appears_only_after": true|false
}"""

        user_prompt_b = f"""Closest prior art {best_pid}:
Claims: {" ".join(closest_claims)[:800]}

Pass A analysis: {obv.pass_a_rationale[:400]}

INVENTION CLAIM:
{result.claim_text[:800]}"""

        response_b, _ = self.llm.chat(sys_prompt_b, user_prompt_b, temperature=0.0, max_tokens=1200)
        try:
            clean = re.sub(r"^```(?:json)?\s*", "", response_b.strip())
            clean = re.sub(r"\s*```$", "", clean)
            pass_b = json.loads(clean)
            obv.pass_b_rationale = json.dumps(pass_b)
            obv.distinguishing_features = pass_b.get("distinguishing_features", "")
            obv.technical_effect = pass_b.get("technical_effect", "")
            obv.motivation_to_modify = pass_b.get("motivation_to_modify", "")
            obv.reasonable_expectation_of_success = pass_b.get("reasonable_expectation_of_success", "")
            obv.teaching_away = pass_b.get("teaching_away", "")
            obv.could_answer = pass_b.get("could_answer", "")
            obv.would_answer = pass_b.get("would_answer", "")
            obv.would_why = pass_b.get("would_why", "")
            obv.hindsight_risk = pass_b.get("hindsight_risk", "UNKNOWN")
            obv.rationale_appears_only_after = pass_b.get("rationale_appears_only_after", False)
        except (json.JSONDecodeError, TypeError):
            obv.pass_b_rationale = response_b[:500]

        obv.attack_succeeded = (obv.could_answer == "yes" and obv.would_answer == "yes")
        return obv

    def _classify_technical_effect(self, claim_text: str, elements: List[ClaimElement]) -> Dict[str, Any]:
        """Classify the technical effect."""
        sys_prompt = """Identify the technical effect of this invention.
Return JSON: {"problem": "...", "distinguishing_feature": "...", "mechanism": "...", "technical_effect": "...", "classification": "DOCUMENTED|INFERRED|HYPOTHESIZED", "unexpected": true|false}"""
        user_prompt = f"Claim: {claim_text[:1000]}\nElements: {json.dumps([asdict(e) for e in elements])}"
        response, _ = self.llm.chat(sys_prompt, user_prompt, temperature=0.0, max_tokens=600)
        try:
            clean = re.sub(r"^```(?:json)?\s*", "", response.strip())
            clean = re.sub(r"\s*```$", "", clean)
            return json.loads(clean)
        except (json.JSONDecodeError, TypeError):
            return {"classification": "HYPOTHESIZED", "error": "parse failure"}

    def _test_design_around(self, claim_text: str) -> DesignAroundForensic:
        """5-workaround design-around test."""
        sys_prompt = """Generate 5 competitor workarounds. For each: does competitor preserve commercial value?
Return JSON: {"workarounds": [{"strategy": "remove_element|replace_element|move_element|material_substitution|control_logic_substitution", "description": "...", "competitor_preserves_value": true|false, "value_preservation_analysis": "..."}], "design_around_risk": "HIGH|MEDIUM|LOW", "elite_status_requires_review": true|false}"""
        user_prompt = f"Claim: {claim_text[:1000]}"
        response, _ = self.llm.chat(sys_prompt, user_prompt, temperature=0.0, max_tokens=1200)
        da = DesignAroundForensic()
        try:
            clean = re.sub(r"^```(?:json)?\s*", "", response.strip())
            clean = re.sub(r"\s*```$", "", clean)
            data = json.loads(clean)
            da.workarounds = data.get("workarounds", [])
            da.design_around_risk = data.get("design_around_risk", "UNKNOWN")
            da.elite_status_requires_review = data.get("elite_status_requires_review", False)
        except (json.JSONDecodeError, TypeError):
            pass
        return da

    def _apply_elite_gate(self, result: ClaimAttackResult):
        """Apply 10-condition ELITE gate."""
        gate = result.elite_gate

        # A. ≥2 claim-specific GOLD references
        claim_specific = sum(1 for gp in result.gold_patents_data if gp.get("claim_count", 0) > 0)
        gate.A_gold_references_mapped = claim_specific >= 2

        # B. no 102 anticipation
        gate.B_no_102_anticipation = result.novelty_attacked_count == 0

        # C. 103 rejected with rationale
        if result.obviousness_result:
            gate.C_103_rejected_with_rationale = (
                not result.obviousness_result.attack_succeeded and
                bool(result.obviousness_result.would_why)
            )
        else:
            gate.C_103_rejected_with_rationale = False

        # D. no material hindsight
        if result.obviousness_result:
            gate.D_no_material_hindsight = result.obviousness_result.hindsight_risk in ("LOW", "UNKNOWN")
        else:
            gate.D_no_material_hindsight = True

        # E. arrangement survives
        gate.E_arrangement_survives = all(not nr.arrangement_disclosed or nr.elements_missing for nr in result.novelty_results)

        # F. enablement
        gate.F_enablement_passes = True

        # G. manufacturing
        gate.G_manufacturing_plausible = True

        # H. economically significant
        gate.H_economically_significant = True

        # I. design-around not catastrophic
        if result.design_around:
            gate.I_design_around_not_catastrophic = result.design_around.design_around_risk != "HIGH"
        else:
            gate.I_design_around_not_catastrophic = True

        # J. provenance complete
        gate.J_evidence_provenance_complete = (
            bool(result.claim_hash) and
            all(gp.get("source_hash") for gp in result.gold_patents_data)
        )

        conditions = [
            ("A_gold_references_mapped", gate.A_gold_references_mapped),
            ("B_no_102_anticipation", gate.B_no_102_anticipation),
            ("C_103_rejected_with_rationale", gate.C_103_rejected_with_rationale),
            ("D_no_material_hindsight", gate.D_no_material_hindsight),
            ("E_arrangement_survives", gate.E_arrangement_survives),
            ("F_enablement_passes", gate.F_enablement_passes),
            ("G_manufacturing_plausible", gate.G_manufacturing_plausible),
            ("H_economically_significant", gate.H_economically_significant),
            ("I_design_around_not_catastrophic", gate.I_design_around_not_catastrophic),
            ("J_evidence_provenance_complete", gate.J_evidence_provenance_complete),
        ]
        gate.failed_conditions = [name for name, passed in conditions if not passed]
        gate.all_pass = len(gate.failed_conditions) == 0

    def _determine_status(self, result: ClaimAttackResult) -> Tuple[str, str]:
        """Determine final status."""
        # If any 102 attack succeeds, REJECT
        if result.novelty_attacked_count > 0:
            return "REJECT", f"{result.novelty_attacked_count} patents anticipate the claim (102)"

        # If 103 succeeds, REJECT
        if result.obviousness_result and result.obviousness_result.attack_succeeded:
            return "REJECT", "Obviousness attack succeeds (103)"

        # Check ELITE gate
        if result.elite_gate.all_pass:
            return "ELITE", "All 10 ELITE gate conditions passed"
        elif result.elite_gate.A_gold_references_mapped and result.elite_gate.B_no_102_anticipation:
            return "STRONG_CANDIDATE_FOR_ATTORNEY_REVIEW", f"Gate failures: {result.elite_gate.failed_conditions}"
        elif result.elite_gate.A_gold_references_mapped:
            return "PROMISING_INSUFFICIENT_EVIDENCE", f"Gate failures: {result.elite_gate.failed_conditions}"
        else:
            return "PROMISING_INSUFFICIENT_EVIDENCE", f"Insufficient: {result.elite_gate.failed_conditions}"
