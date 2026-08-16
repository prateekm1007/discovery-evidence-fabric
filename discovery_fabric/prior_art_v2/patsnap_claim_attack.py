"""
PatSnap Claim Attack Framework
================================

Uses PatSnap claim-data to retrieve ACTUAL patent claims and run
real 102/103 attacks against invention claims.

ARCHITECTURE:
  1. Take invention claim + known patent IDs (from V4 retrieval)
  2. Retrieve claims via PatSnap claim-data endpoint
  3. Build element matrix (map E1..En against actual claims)
  4. Map relationships (A→B, B→C, A+B+C arrangement)
  5. Run 102 (single-reference novelty)
  6. Run 103 (EPO obviousness with COULD/WOULD/WHY + anti-hindsight)
  7. Claim redesign if rejected

FIREWALLS:
  - PatSnap search-count ≠ evidence
  - Claim hash must match for every mapping (no stale claims)
  - Element mapping uses ACTUAL claim text, not keywords
  - INHERENT requires necessity, not probability
  - 102 = single reference only
  - No hindsight in 103
"""
from __future__ import annotations
import os, sys, json, time, hashlib, re
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

THIS_DIR = Path(__file__).resolve().parent
REPO_ROOT = THIS_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.prior_art_v2.patsnap_claims import (
    fetch_patsnap_claims, PatSnapClaimRecord, _strip_html,
    _parse_claims_from_html,
)
from discovery_fabric.prior_art_v2.elite_v3 import LLMClient, _now_utc, _sha256


@dataclass
class PatentEvidence:
    """A patent with actual claims retrieved from PatSnap."""
    patent_number: str
    patsnap_patent_id: str
    title: str = ""
    claim_count: int = 0
    independent_claim_count: int = 0
    claims: List[str] = field(default_factory=list)
    claim_hash: str = ""  # hash of normalized claim text
    source: str = "PATSNAP"
    source_url: str = ""
    retrieved_at_utc: str = ""
    content_hash: str = ""
    is_valid: bool = False  # TRUE only if all required fields exist

    def validate(self):
        """Per CEO Section 3: all required fields must exist."""
        required = {
            "patent_number": bool(self.patent_number),
            "patsnap_patent_id": bool(self.patsnap_patent_id),
            "claims": len(self.claims) > 0,
            "content_hash": bool(self.content_hash),
        }
        self.is_valid = all(required.values())
        return self.is_valid


@dataclass
class ElementMapping:
    """One element mapped against one patent's actual claims."""
    patent_number: str
    claim_hash: str  # references the patent's claim hash
    element_id: str
    disclosure_type: str  # EXPLICIT / IMPLICIT / INHERENT / NOT_DISCLOSED / UNCERTAIN
    exact_passage: str
    claim_number: str = ""
    reasoning: str = ""


@dataclass
class ArrangementMapping:
    """A→B, B→C, A+B+C arrangement mapping."""
    patent_number: str
    claim_hash: str
    element_pair: str
    required_arrangement_disclosed: str  # TRUE / FALSE / UNCERTAIN
    arrangement_analysis: str = ""


@dataclass
class NoveltyResult:
    """102 test result for one patent."""
    patent_number: str
    all_elements_found: bool = False
    elements_found: List[str] = field(default_factory=list)
    elements_missing: List[str] = field(default_factory=list)
    element_preventing_anticipation: Optional[str] = None
    arrangement_disclosed: bool = False
    novelty_attacked: bool = False
    rationale: str = ""


@dataclass
class ClaimAttackResult:
    """Complete PatSnap claim attack result."""
    invention_id: str
    claim_version: int
    claim_text: str
    claim_hash: str
    elements: List[Dict[str, str]] = field(default_factory=list)
    patent_evidence: List[Dict[str, Any]] = field(default_factory=list)
    element_matrix: List[ElementMapping] = field(default_factory=list)
    arrangement_mappings: List[ArrangementMapping] = field(default_factory=list)
    novelty_results: List[NoveltyResult] = field(default_factory=list)
    novelty_attacked_count: int = 0
    obviousness_result: Optional[Dict[str, Any]] = None
    final_status: str = ""
    final_reasoning: str = ""
    timestamp: str = ""
    llm_calls: int = 0
    elapsed_seconds: float = 0.0


class PatSnapClaimAttacker:
    """Runs claim-level attacks using PatSnap claim data."""

    def __init__(self, llm: Optional[LLMClient] = None):
        self.llm = llm or LLMClient()

    def attack(self, invention_id: str, claim_text: str,
               patent_numbers: List[str]) -> ClaimAttackResult:
        """Run full PatSnap claim attack."""
        t0 = time.time()
        print(f"\n{'='*60}", flush=True)
        print(f"  PATSNAP CLAIM ATTACK: {invention_id}", flush=True)
        print(f"  Patents to test: {len(patent_numbers)}", flush=True)
        print(f"{'='*60}", flush=True)

        result = ClaimAttackResult(
            invention_id=invention_id,
            claim_version=0,
            claim_text=claim_text,
            claim_hash=_sha256(claim_text),
            timestamp=_now_utc(),
        )

        # STEP 1: Parse claim elements
        print(f"  [1] Parsing claim elements...", flush=True)
        result.elements = self._parse_elements(claim_text)
        print(f"      {len(result.elements)} elements", flush=True)

        # STEP 2: Retrieve claims from PatSnap
        print(f"  [2] Retrieving claims from PatSnap...", flush=True)
        for pn in patent_numbers:
            print(f"      {pn}...", flush=True)
            record = fetch_patsnap_claims(pn)
            if record and record.claims:
                # Compute claim hash
                normalized = " ".join(record.claims).lower().strip()
                claim_hash = _sha256(normalized)

                pe = PatentEvidence(
                    patent_number=record.patent_number,
                    patsnap_patent_id=record.patsnap_patent_id,
                    claim_count=record.claim_count,
                    independent_claim_count=record.independent_claim_count,
                    claims=record.claims,
                    claim_hash=claim_hash,
                    source="PATSNAP",
                    source_url=record.source_url,
                    retrieved_at_utc=record.retrieved_at_utc,
                    content_hash=record.content_hash,
                )
                pe.validate()
                if pe.is_valid:
                    result.patent_evidence.append(asdict(pe))
                    print(f"        → VALID: {pe.claim_count} claims, hash={claim_hash[:12]}...", flush=True)
                else:
                    print(f"        → INVALID: missing fields", flush=True)
            else:
                print(f"        → FAILED: no claims retrieved", flush=True)

        if not result.patent_evidence:
            result.final_status = "INSUFFICIENT_EVIDENCE"
            result.final_reasoning = "No valid patent evidence from PatSnap"
            result.elapsed_seconds = round(time.time() - t0, 1)
            return result

        # STEP 3: Build element matrix
        print(f"  [3] Building element matrix...", flush=True)
        for pe in result.patent_evidence:
            mappings, arrangements = self._map_elements(
                result.elements, pe)
            result.element_matrix.extend(mappings)
            result.arrangement_mappings.extend(arrangements)

        # STEP 4: 102 test per patent
        print(f"  [4] Running 102 novelty test...", flush=True)
        for pe in result.patent_evidence:
            pn = pe["patent_number"]
            entries = [e for e in result.element_matrix if e.patent_number == pn]
            arms = [a for a in result.arrangement_mappings if a.patent_number == pn]
            novelty = self._test_102(pn, entries, arms, result.elements)
            result.novelty_results.append(novelty)
            if novelty.novelty_attacked:
                result.novelty_attacked_count += 1
                print(f"      {pn}: 102 ATTACKED!", flush=True)
            else:
                missing = novelty.element_preventing_anticipation or "arrangement"
                print(f"      {pn}: 102 fails (missing: {missing})", flush=True)

        # STEP 5: 103 if 102 survives
        if result.novelty_attacked_count == 0:
            print(f"  [5] Running 103 obviousness...", flush=True)
            result.obviousness_result = self._test_103(result)
        else:
            print(f"  [5] Skipping 103 (102 already killed)", flush=True)

        # Final status
        result.final_status, result.final_reasoning = self._determine_status(result)
        result.elapsed_seconds = round(time.time() - t0, 1)
        result.llm_calls = self.llm._call_count

        print(f"\n  → FINAL: {result.final_status}", flush=True)
        print(f"     102 attacked: {result.novelty_attacked_count}/{len(result.novelty_results)}", flush=True)
        print(f"     Elapsed: {result.elapsed_seconds}s, LLM: {result.llm_calls}", flush=True)

        return result

    def _parse_elements(self, claim_text: str) -> List[Dict[str, str]]:
        """Parse claim into elements."""
        sys_prompt = """Parse this patent claim into elements. Return JSON: {"elements": [{"element_id":"A","technical_feature":"...","relationship":"..."}]}"""
        response, _ = self.llm.chat(sys_prompt, f"Claim: {claim_text[:1500]}", max_tokens=800)
        try:
            clean = re.sub(r"^```(?:json)?\s*", "", response.strip())
            clean = re.sub(r"\s*```$", "", clean)
            data = json.loads(clean)
            if isinstance(data, dict):
                return data.get("elements", [])[:8]
            elif isinstance(data, list):
                return data[:8]
        except:
            pass
        return [{"element_id": "A", "technical_feature": claim_text[:200]}]

    def _map_elements(self, elements: List[Dict], pe: Dict) -> Tuple[List[ElementMapping], List[ArrangementMapping]]:
        """Map invention elements against patent's ACTUAL claims."""
        sys_prompt = """You are a patent claim mapper. Map invention elements against the prior-art patent's ACTUAL CLAIM TEXT.

For each element:
- EXPLICIT: directly stated in the claim text
- IMPLICIT: necessarily implied
- INHERENT: necessarily present (requires necessity, not probability)
- NOT_DISCLOSED: not taught
- UNCERTAIN: cannot determine

Also check: does the patent disclose the required ARRANGEMENT/RELATIONSHIP?

Return JSON:
{
  "elements": [{"element_id":"A","disclosure_type":"...","exact_passage":"exact quote from claims","claim_number":"1","reasoning":"..."}],
  "arrangements": [{"element_pair":"A→B","required_arrangement_disclosed":"TRUE|FALSE|UNCERTAIN","arrangement_analysis":"..."}]
}"""
        claims_text = "\n".join([f"Claim {i+1}: {c[:500]}" for i, c in enumerate(pe["claims"][:5])])
        user_prompt = f"""Invention elements: {json.dumps(elements)}
Patent {pe['patent_number']} ACTUAL CLAIMS:
{claims_text}"""
        response, _ = self.llm.chat(sys_prompt, user_prompt, max_tokens=1500)

        mappings = []
        arrangements = []
        try:
            clean = re.sub(r"^```(?:json)?\s*", "", response.strip())
            clean = re.sub(r"\s*```$", "", clean)
            data = json.loads(clean)
            if isinstance(data, dict):
                for e in data.get("elements", []):
                    mappings.append(ElementMapping(
                        patent_number=pe["patent_number"],
                        claim_hash=pe["claim_hash"],
                        element_id=e.get("element_id", ""),
                        disclosure_type=e.get("disclosure_type", "UNCERTAIN"),
                        exact_passage=e.get("exact_passage", ""),
                        claim_number=e.get("claim_number", ""),
                        reasoning=e.get("reasoning", ""),
                    ))
                for a in data.get("arrangements", []):
                    arrangements.append(ArrangementMapping(
                        patent_number=pe["patent_number"],
                        claim_hash=pe["claim_hash"],
                        element_pair=a.get("element_pair", ""),
                        required_arrangement_disclosed=a.get("required_arrangement_disclosed", "UNCERTAIN"),
                        arrangement_analysis=a.get("arrangement_analysis", ""),
                    ))
        except:
            pass
        return mappings, arrangements

    def _test_102(self, pn: str, entries: List[ElementMapping],
                  arms: List[ArrangementMapping], elements: List[Dict]) -> NoveltyResult:
        """Single-reference 102 test."""
        found = [e.element_id for e in entries if e.disclosure_type in ("EXPLICIT", "IMPLICIT", "INHERENT")]
        missing = [e.element_id for e in entries if e.disclosure_type == "NOT_DISCLOSED"]
        all_found = len(missing) == 0 and len(found) == len(elements)

        arrangement_disclosed = any(a.required_arrangement_disclosed == "TRUE" for a in arms)
        novelty_attacked = all_found and arrangement_disclosed

        return NoveltyResult(
            patent_number=pn,
            all_elements_found=all_found,
            elements_found=found,
            elements_missing=missing,
            element_preventing_anticipation=missing[0] if missing else (None if arrangement_disclosed else "arrangement"),
            arrangement_disclosed=arrangement_disclosed,
            novelty_attacked=novelty_attacked,
            rationale=f"{'All found' if all_found else f'Missing: {missing}'}. Arrangement: {'yes' if arrangement_disclosed else 'no'}.",
        )

    def _test_103(self, result: ClaimAttackResult) -> Dict[str, Any]:
        """103 with EPO structure + anti-hindsight."""
        # Find closest prior art
        best_pn = None
        best_count = 0
        for nr in result.novelty_results:
            if len(nr.elements_found) > best_count:
                best_count = len(nr.elements_found)
                best_pn = nr.patent_number

        if not best_pn:
            return {"closest_prior_art": "none"}

        # Get closest patent claims
        closest_claims = []
        for pe in result.patent_evidence:
            if pe["patent_number"] == best_pn:
                closest_claims = pe["claims"][:3]
                break

        # Pass A: before revealing invention
        sys_a = """Analyze the closest prior art WITHOUT knowing the invention. What technical problem exists? What modifications would a PHOSITA consider?
Return JSON: {"technical_problem":"...","potential_modifications":"..."}"""
        resp_a, _ = self.llm.chat(sys_a, f"Patent {best_pn} claims: {' '.join(closest_claims)[:800]}", max_tokens=600)
        pass_a = self._extract_json(resp_a) or {"raw": resp_a[:300]}

        # Pass B: after revealing invention
        sys_b = """You are a patent obviousness analyst per EPO 2026. Now you see the invention. Analyze:
- distinguishing_features
- technical_effect
- motivation_to_modify (WHY?)
- reasonable_expectation_of_success
- teaching_away
- could_answer (yes/no)
- would_answer (yes/no) — MANDATORY
- would_why
- hindsight_risk (HIGH/MEDIUM/LOW)
- rationale_appears_only_after (true/false)

Return JSON."""
        resp_b, _ = self.llm.chat(sys_b,
            f"Closest prior art {best_pn}:\n{' '.join(closest_claims)[:600]}\n\nPass A: {json.dumps(pass_a)[:300]}\n\nINVENTION:\n{result.claim_text[:600]}",
            max_tokens=1200)
        pass_b = self._extract_json(resp_b) or {"raw": resp_b[:300]}

        attack_succeeded = pass_b.get("could_answer") == "yes" and pass_b.get("would_answer") == "yes"

        return {
            "closest_prior_art": best_pn,
            "pass_a": pass_a,
            "pass_b": pass_b,
            "attack_succeeded": attack_succeeded,
            "hindsight_risk": pass_b.get("hindsight_risk", "UNKNOWN"),
        }

    def _extract_json(self, response: str) -> Optional[dict]:
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

    def _determine_status(self, result: ClaimAttackResult) -> Tuple[str, str]:
        # If element matrix is empty, the attack was not actually performed
        if not result.element_matrix:
            return "INSUFFICIENT_EVIDENCE", "Element mapping failed — no actual claim-level analysis performed"
        # If ALL mappings are UNCERTAIN, the analysis is insufficient
        all_uncertain = all(e.disclosure_type == "UNCERTAIN" for e in result.element_matrix)
        if all_uncertain:
            return "INSUFFICIENT_EVIDENCE", "All element mappings are UNCERTAIN — no actual disclosure determination made"
        if result.novelty_attacked_count > 0:
            killed_by = [nr.patent_number for nr in result.novelty_results if nr.novelty_attacked]
            return "REJECTED_102", f"Anticipated by: {', '.join(killed_by)}"
        if result.obviousness_result and result.obviousness_result.get("attack_succeeded"):
            return "REJECTED_103", "Obviousness attack succeeds"
        if result.obviousness_result:
            return "SURVIVES_102_AND_103", "Survived both 102 and 103 with actual claim evidence"
        return "SURVIVES_102", "Survived 102 with actual claim evidence (103 not run)"
