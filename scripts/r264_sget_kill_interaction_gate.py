"""
Round 264 — SGET Kill Acceptance + Interaction-Prior-Art Gate + Unexpected-Effect Proof

CEO R264 directive:
  P0: Accept SGET kill. Synergy ≠ novelty, synergy ≠ commercial moat.
  P1: Add INTERACTION-PRIOR-ART GATE. Search for A alone, B alone, A+B,
      interaction law, emergent effect, same effect via different mechanism,
      same interaction in aerospace/industrial/MEMS/semiconductor.
  P2: Add "unexpected effect" proof. Pre-register quantitative effect that
      could NOT be predicted from A and B independently. Then prove it.

Output:
  CANONICAL_STATE/R264_SGET_KILL_INTERACTION_GATE.json
"""
import json
from pathlib import Path
from datetime import datetime, timezone

OUTPUT_PATH = Path(
    "/home/z/my-project/discovery-evidence-fabric/CANONICAL_STATE/"
    "R264_SGET_KILL_INTERACTION_GATE.json"
)


# ===========================================================================
# P0 — SGET Kill Acceptance
# ===========================================================================

SGET_KILL = {
    "candidate": "SGET (Strain-Gated Electrochemical Transduction)",
    "r263_verdict": "KILLED (Gate H + Gate I)",
    "r264_ceo_verdict": "KILLED / CLOSED AS A CANDIDATE",
    "ceo_reason": (
        "Synergy ≠ novelty and synergy ≠ commercial moat. SGET had genuine "
        "functional interaction (synergy score 2) but the interaction itself "
        "sits in a very crowded technical neighborhood:"
    ),
    "ceo_found_prior_art": [
        {
            "source": "ScienceDirect (electrochemical impedance depth profiling)",
            "what_it_covers": "Electrochemical impedance sensing already used for depth profiling of biological tissue, including multilayer porcine tissue.",
            "threatens": "The 'depth profiling via electrochemistry' emergent effect",
        },
        {
            "source": "PubMed 34045731 (miniaturized vibratory actuator + strain sensor)",
            "what_it_covers": "Miniaturized devices combining vibratory actuator + strain sensor characterize tissue at 1-8mm depth and produce depth-wise tissue maps.",
            "threatens": "Both the A+B combination AND the depth-sensing emergent effect",
        },
        {
            "source": "PubMed 32632992 (stretchable electrochemical sensors)",
            "what_it_covers": "Stretchable electrochemical sensors monitor chemical information from mechanically deformed biological tissue and vascular tissue.",
            "threatens": "The strain+electrochemistry interaction in tissue",
        },
        {
            "source": "Nature Materials 2026 (implantable mechanical+chemical+neural platform)",
            "what_it_covers": "2026 implantable platform integrates mechanical sensing + chemical monitoring + neural modulation, including closed-loop operation.",
            "threatens": "The implantable multi-modal sensing architecture",
        },
        {
            "source": "CN121647794A patent (orthopedic implant mechanical/electrochemical monitoring)",
            "what_it_covers": "2026 implantable bioelectronics patent describing combined mechanical/electrochemical sensing and closed-loop therapeutic response.",
            "threatens": "The implant-surface mechanical+electrochemical combination",
        },
    ],
    "the_lesson": (
        "SGET taught us that functional interaction is NECESSARY but NOT "
        "SUFFICIENT. The interaction itself must survive prior art. The "
        "emergent effect (depth profiling) was already demonstrated by "
        "existing systems using different but functionally equivalent "
        "approaches. Synergy without novelty = engineering, not invention.\n\n"
        "The new standard: A changes B → unexpected effect → the INTERACTION "
        "ITSELF survives prior art → produces a reproducible technical "
        "advantage → cannot be cheaply reproduced → creates buyer value."
    ),
    "cemetery_entry": "CE-022",
    "epistemic_class": "VALIDATED_NEGATIVE — synergy without novelty",
}


# ===========================================================================
# P1 — INTERACTION-PRIOR-ART GATE (new mandatory gate)
# ===========================================================================

INTERACTION_GATE = {
    "gate_name": "INTERACTION-PRIOR-ART GATE (Gate M)",
    "position_in_pipeline": "Gate 13 of 13 (after synergy Gate L)",
    "the_problem": (
        "R263 searched for A (strain) and B (electrochemistry) separately, "
        "but did NOT search for the INTERACTION itself — the specific causal "
        "relationship 'strain gates electrochemical sampling volume.' The "
        "CEO found 5 sources where this interaction (or a functional "
        "equivalent) already exists. The search missed them because it "
        "searched components, not the interaction law."
    ),
    "the_gate": {
        "mandatory_searches": [
            {
                "search": "A alone",
                "question": "What does A (strain/mechanical actuation) do independently? Is this known?",
                "purpose": "Establish A's independent capability baseline",
            },
            {
                "search": "B alone",
                "question": "What does B (electrochemical sensing) do independently? Is this known?",
                "purpose": "Establish B's independent capability baseline",
            },
            {
                "search": "A+B (literal combination)",
                "question": "Has anyone combined A and B before?",
                "purpose": "Check if the combination exists",
            },
            {
                "search": "The interaction law",
                "question": "Has anyone described the specific causal mechanism by which A changes B's operating state?",
                "purpose": "Check if the interaction LAW is disclosed",
                "example_for_SGET": "Search: 'strain-induced fluid displacement electrochemical gradient', 'mechanical gating electrochemical sensing', 'poroelastic electrochemical coupling'",
            },
            {
                "search": "The resulting emergent effect",
                "question": "Has anyone achieved the emergent effect (depth-resolved chemistry) through ANY mechanism?",
                "purpose": "Check if the EMERGENT EFFECT exists via any approach",
                "example_for_SGET": "Search: 'depth-resolved tissue chemistry', 'tissue chemical depth profiling', 'volumetric analyte sensing'",
            },
            {
                "search": "Same effect via different physical mechanism",
                "question": "Can the emergent effect be achieved through a completely different physical approach?",
                "purpose": "Check if the effect is truly novel or just the mechanism",
                "example_for_SGET": "Microdialysis at different depths, optical coherence tomography spectroscopy, MRI spectroscopy — all achieve depth-resolved chemistry via different mechanisms",
            },
            {
                "search": "Same interaction in aerospace/industrial/MEMS/semiconductor",
                "question": "Does the same interaction law exist in any non-medical field?",
                "purpose": "Cross-domain collision on the INTERACTION, not just the components",
                "example_for_SGET": "Search: 'strain-gated electrochemistry' in corrosion monitoring, 'mechanical perturbation electrochemistry' in battery research, 'pressure-modulated sensing' in process control",
            },
        ],
        "pass_condition": (
            "The INTERACTION ITSELF (not just A and B) must survive all 7 "
            "searches. If the interaction law, the emergent effect, or a "
            "functional equivalent is found in ANY domain → the interaction "
            "is prior-art threatened."
        ),
        "fail_condition": (
            "If ANY of the 7 searches finds the interaction law, the emergent "
            "effect, or a functional equivalent → FAIL. The candidate is "
            "killed regardless of synergy score."
        ),
    },
    "retroactive_application_to_SGET": {
        "A_alone": "KNOWN — strain/mechanical actuation for tissue characterization is standard (elastography)",
        "B_alone": "KNOWN — electrochemical sensing of tissue is standard (CGM, oxygen sensors)",
        "A+B": "KNOWN — CEO found PubMed 34045731 (vibratory actuator + strain sensor for tissue), PubMed 32632992 (stretchable electrochemical sensors on deformed tissue), Nature Materials 2026 (mechanical+chemical implantable platform)",
        "interaction_law": "PARTIALLY KNOWN — poroelastic-electrochemical coupling is derivable from Biot + Nernst. Not explicitly disclosed as 'interaction law' but the physics is established.",
        "emergent_effect": "KNOWN — ScienceDirect shows electrochemical impedance depth profiling of tissue. PubMed 34045731 shows 1-8mm depth tissue characterization. The 'depth-resolved chemistry' effect EXISTS via multiple mechanisms.",
        "same_effect_different_mechanism": "KNOWN — microdialysis at multiple depths, OCT spectroscopy, MRI spectroscopy all achieve depth-resolved tissue chemistry",
        "same_interaction_cross_domain": "PARTIALLY — sonoelectrochemistry (ultrasound+electrochemistry) is the same interaction class in analytical chemistry",
        "verdict": "FAIL — the interaction itself is prior-art threatened. 5/7 searches found the interaction or its emergent effect.",
    },
}


# ===========================================================================
# P2 — Unexpected-Effect Proof
# ===========================================================================

UNEXPECTED_EFFECT_PROOF = {
    "the_problem": (
        "R263 claimed 'depth profiling is unexpected' but did not quantify "
        "the effect or compare against the best existing baseline. Without "
        "quantitative comparison, 'unexpected' is a story, not evidence."
    ),
    "the_fix": {
        "mandatory_pre_registration": (
            "Before any novelty search, the candidate MUST pre-register:\n"
            "1. What quantitative effect could NOT reasonably be predicted "
            "   from A and B independently?\n"
            "2. What is the BEST existing baseline that achieves a similar "
            "   effect?\n"
            "3. What is the predicted quantitative advantage over that "
            "   baseline?\n"
            "4. Why is this advantage NOT derivable from A and B's "
            "   independent properties?"
        ),
        "mandatory_proof": (
            "After pre-registration, the candidate MUST demonstrate (via "
            "killer experiment) that the predicted advantage is real. The "
            "experiment must compare against the STRONGEST baseline, not "
            "a weak one."
        ),
        "example_for_SGET": {
            "what_should_have_been_pre_registered": (
                "Quantitative effect: SGET's depth sensitivity (mm) vs "
                "best existing mechanically-assisted tissue sensing baseline. "
                "Specifically: can SGET resolve analyte concentration at "
                "specific depths (e.g., 1mm, 3mm, 5mm) with resolution X, "
                "when the best existing baseline (vibratory tissue "
                "characterization, PubMed 34045731) achieves Y?"
            ),
            "what_should_have_been_compared_against": (
                "Best baseline: miniaturized vibratory actuator + strain "
                "sensor for deep tissue characterization (PubMed 34045731, "
                "1-8mm depth). NOT just 'static electrochemical sensor' "
                "(which is a weak baseline)."
            ),
            "what_was_missing": (
                "R263 did not identify this baseline. It compared against "
                "'static electrochemical sensor' (weak) instead of "
                "'mechanically-assisted tissue sensing' (strong). The "
                "47% improvement claim from R263-era logic would have "
                "been against the weak baseline."
            ),
        },
    },
    "the_rule": (
        "Synergy claims without quantitative comparison against the STRONGEST "
        "baseline are STORIES, not evidence. The unexpected-effect proof "
        "requires: (1) pre-registered quantitative prediction, (2) strongest "
        "baseline identified, (3) killer experiment comparing against that "
        "baseline, (4) result that could NOT be predicted from A and B "
        "independently."
    ),
}


# ===========================================================================
# Updated Level 2: 13 Sub-Gates
# ===========================================================================

LEVEL_2_UPDATED = {
    "total_gates": 13,
    "gates": [
        "A. Variable novelty",
        "B. Transduction novelty",
        "C. Architecture novelty",
        "D. Functional equivalence (10+ terms, 5 domains)",
        "E. Cross-domain (all 5 clear)",
        "F. Old-art (< 20-30 years)",
        "G. Combination obviousness",
        "H. Commercial substitution (<$50K/$250K/6mo)",
        "I. Triple saturation (term + domain + reference)",
        "J. §102 (no single reference, all elements)",
        "K. §103 (no motivation + expectation to combine)",
        "L. Synergy (score ≥ 2, functional interaction)",
        "M. INTERACTION-PRIOR-ART (interaction law + emergent effect survive) [NEW]",
    ],
    "new_gate_M_description": (
        "Gate M searches for the INTERACTION ITSELF, not just the components. "
        "7 mandatory searches: A alone, B alone, A+B, interaction law, "
        "emergent effect, same effect via different mechanism, same "
        "interaction cross-domain. The interaction itself must survive."
    ),
    "the_full_standard": (
        "A candidate reaches Level 2 ONLY when ALL 13 gates pass, including:\n"
        "- Synergy ≥ 2 (functional interaction, Gate L)\n"
        "- Interaction itself survives prior art (Gate M)\n"
        "- Unexpected effect is quantified and proven against strongest baseline\n"
        "- Triple saturation achieved\n"
        "- Not reproducible for <$250K (or escape clause with unexpected effect)\n"
        "This is the standard for a genuine invention, not just a clever combination."
    ),
}


# ===========================================================================
# Updated Discovery Chain
# ===========================================================================

UPDATED_CHAIN = {
    "chain": (
        "unobservable problem → physical mechanism A → physical mechanism B → "
        "FUNCTIONAL INTERACTION (A changes B) → predicted UNEXPECTED EFFECT "
        "(quantified, pre-registered) → functional-equivalence collision → "
        "old-art shock → cross-domain collision → INTERACTION-PRIOR-ART "
        "collision (7 searches) → closest-prior-art §103 attack → §102 "
        "single-reference check → synergy test → triple saturation → "
        "engineer reproduction attack → killer experiment (vs STRONGEST "
        "baseline) → economic attack"
    ),
    "what_changed_from_R263": (
        "Added INTERACTION-PRIOR-ART collision (7 searches on the interaction "
        "itself) and UNEXPECTED-EFFECT proof (quantified prediction vs "
        "strongest baseline). The chain now requires the interaction to "
        "survive independently, not just the components."
    ),
}


# ===========================================================================
# Assemble output
# ===========================================================================

output = {
    "schema_version": "1.0.0",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "generated_by": "Round 264 — SGET Kill + Interaction Gate + Unexpected-Effect Proof",
    "ceo_directive_round_264": (
        "P0: accept SGET kill (synergy ≠ novelty). P1: add interaction-"
        "prior-art gate. P2: add unexpected-effect proof."
    ),
    "p0_sget_kill": SGET_KILL,
    "p1_interaction_prior_art_gate": INTERACTION_GATE,
    "p2_unexpected_effect_proof": UNEXPECTED_EFFECT_PROOF,
    "level_2_updated": LEVEL_2_UPDATED,
    "updated_discovery_chain": UPDATED_CHAIN,
    "summary": {
        "p0": "SGET KILLED/CLOSED. Synergy ≠ novelty. 5 CEO-found sources show the interaction (strain+electrochemistry for tissue depth profiling) already exists in crowded neighborhood. Added to cemetery as CE-022.",
        "p1": "INTERACTION-PRIOR-ART GATE (Gate M) added. 7 mandatory searches: A alone, B alone, A+B, interaction law, emergent effect, same effect different mechanism, same interaction cross-domain. The INTERACTION ITSELF must survive, not just components.",
        "p2": "Unexpected-effect proof added. Must pre-register: quantitative effect NOT predictable from A+B independently + strongest baseline + predicted advantage + why not derivable. Then prove via killer experiment vs strongest baseline.",
        "level_2": "13 sub-gates (was 12). Gate M added: interaction-prior-art. The interaction law and emergent effect must survive all 7 searches.",
        "key_lesson": (
            "The invention problem has a new layer: A changes B → unexpected "
            "effect → the INTERACTION ITSELF survives prior art → reproducible "
            "technical advantage → cannot be cheaply reproduced → buyer value. "
            "Synergy is necessary but not sufficient. The interaction must be "
            "novel, not just the components. And the unexpected effect must "
            "be QUANTIFIED against the strongest baseline, not asserted."
        ),
        "the_progression": {
            "new_application": "❌ killed (NC-05, NC-01-04)",
            "new_information_channel": "❌ killed (IB-01, IB-02, IB-03)",
            "new_component": "❌ killed (all CC candidates)",
            "component_combination": "❌ killed (MSVED, CC-04, CC-08)",
            "functional_interaction": "✅ achieved (SGET synergy=2) but ❌ killed (interaction not novel)",
            "next_frontier": "A previously unknown functional interaction that produces a quantitatively unexpected technical effect AND survives functional-equivalence prior art",
        },
        "portfolio": "0 Level 2, 0 sellable, 0 transactions. Cemetery: 22 entries (CE-022 SGET). Discovery machine ~85%.",
    },
}

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

if OUTPUT_PATH.exists():
    print(f"[OK] Output: {OUTPUT_PATH} ({OUTPUT_PATH.stat().st_size} bytes)")

print("\n=== R264 SUMMARY ===")
print("SGET: KILLED/CLOSED. Synergy ≠ novelty. 5 sources show interaction already exists.")
print("Gate M (INTERACTION-PRIOR-ART): 7 searches on the interaction itself. NEW mandatory gate.")
print("Unexpected-effect proof: quantified prediction vs strongest baseline. Then prove it.")
print("Level 2: 13 sub-gates. Discovery chain: interaction collision + unexpected-effect proof added.")
print("Cemetery: 22 entries (CE-022 SGET). 0 sellable. 0 transactions.")
