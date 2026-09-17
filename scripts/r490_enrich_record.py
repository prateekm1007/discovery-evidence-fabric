#!/usr/bin/env python3
"""R490 — enrich CROSSDOMAIN_ATTEMPT2.json with the byte-precise
envelope facts read directly from the durable branch (the driver's
generic route-reader reported the CANDIDATE's provider for the attack
envelope; the attack's OWN transport lives in attack_results.transport
— the enrichment separates the two honestly)."""
import json
import subprocess
from pathlib import Path

REPO = Path("/home/z/my-project/hf_space")
OUT = REPO / "R490" / "CROSSDOMAIN_ATTEMPT2.json"
RD = "toscanini_ui_ui_flat_faced_cam_follower_surface_fatigue_sp_640895"


def show(path):
    p = subprocess.run(["git", "show", f"origin/runtime-state-hf:{path}"],
                       cwd=str(REPO), capture_output=True, text=True,
                       timeout=60)
    return json.loads(p.stdout) if p.returncode == 0 else None


atk = show(f"runs/{RD}/envelope_ATTACK.json")
cls = show(f"runs/{RD}/envelope_CLASSIFY.json")
col = show(f"runs/{RD}/envelope_COLLISION.json")
lin = show(f"runs/{RD}/INVENTION_LINEAGE.json")
ss = show(f"runs/{RD}/SURVIVOR_GATE.json")

ar = atk.get("attack_results") or {}
syn_rc = (atk.get("mechanism_map") or {}).get("raw_candidate") or {}
g1 = (lin.get("generations") or [{}])[0]
ch = g1.get("challenge") or {}

envelope_facts = {
    "attack_stage": {
        "what": "the conductor ATTACK stage — the A2 adversarial gauntlet "
                "(a2/adversarial.py; the R490 decision's uncalibrated "
                "attacker)",
        "overall": ar.get("overall"),
        "killed_dimensions": [k for k, v in (ar.get("attacks") or {}).items()
                              if "KILLED" in str(v).upper()
                              and "ADVERSARIAL_INVALID" not in str(v).upper()],
        "dimension_verdicts": ar.get("attacks"),
        "transport": ar.get("transport"),
        "transport_ring_note": (
            "the attack leg was served by xkiro/qwen3.8-max:free — the "
            "ring's free leg (the same substitution pattern R489 "
            "recorded); the preferred_providers policy prefers atria "
            "first, so atria was unavailable/failed for THIS call at "
            "that moment — the substitution is recorded, never silent "
            "(Art. IV)"),
        "calibration_scope_annotation_present": "calibration_scope" in ar,
        "annotation_absence_note": (
            "the deployed build 7d38eb4e predates the R490 annotation "
            "commit; the annotation rides the next behavior deploy "
            "(declared in R490/A2_CALIBRATION_SCOPE.json)"),
        "v4_prior_art_firewall": (
            (ar.get("attacks") or {}).get("prior_art")),
    },
    "candidate_classify": {
        "candidate_id": (cls.get("candidate_id")),
        "final_status": ((cls.get("epistemic_state") or {}).get("final_status")),
        "reason": ((cls.get("epistemic_state") or {}).get("reason")),
        "authority": "a2/classify.py assembles this terminal reason "
                     "(the R489 composition finding, re-confirmed live)",
    },
    "synthesis_stage": {
        "provider": syn_rc.get("provider"),
        "model": syn_rc.get("model"),
        "source_id": ((syn_rc.get("source_evidence") or {}).get("source_id")),
        "source_span_chars": len(
            (syn_rc.get("source_evidence") or {}).get("source_span") or ""),
        "ring_note": "atria served synthesis (Atria-Dawn-Preview) — the "
                     "healthy leg, unlike the R489 attempt",
    },
    "evolution_layer": {
        "n_generations": lin.get("n_generations"),
        "n_evolution_generations": lin.get("n_evolution_generations"),
        "survivor_reached": lin.get("survivor_reached"),
        "gen1": {
            "invention_id": g1.get("invention_id"),
            "origin": g1.get("origin"),
            "state": g1.get("state"),
            "maturity": g1.get("maturity"),
            "challenge_attack_overall": ch.get("attack_overall"),
            "challenge_killed": ch.get("killed"),
            "challenge_kill_reason": ch.get("kill_reason"),
            "challenge_kill_source": (
                "gen['challenge'] carries the run's own candidate-level "
                "adversarial verdict (run.py evolution gen assembly: "
                "attack_overall = env.attack_results.overall; kill_reason "
                "= the candidate final_state reason) — the A2 gauntlet's "
                "kill travels into the lineage record"),
        },
    },
    "survivor_gate": {k: ss.get(k) for k in
                      ("stage", "final_status", "resolution")},
    "ring_observation": {
        "synthesis_leg": "atria / Atria-Dawn-Preview (HEALTHY — atria "
                         "served, no substitution)",
        "attack_leg": "xkiro/qwen3.8-max:free (free-leg substitution — "
                      "NOT the healthy leg; the R488 rules-x-ring "
                      "finding's leg)",
        "collision_leg": "10/10 mandatory pairs failed (5 x google_patents "
                         "HTTP 503 + 5 x lens_patent LENS_API_TOKEN not "
                         "configured) — searches did NOT complete",
        "verdict": "PARTIALLY_HEALTHY_RING — the directive's desired "
                   "healthy-ring state (atria serving, collision searches "
                   "completing) was only PARTIALLY observed: atria served "
                   "synthesis; the attack leg substituted to the free "
                   "leg; the collision searches cannot complete while the "
                   "Lens token is absent server-side (no Lens token "
                   "exists in any vault this session can reach — a "
                   "disclosed limitation, never fixed by assertion)",
    },
}

rec = json.loads(OUT.read_text())
rec["envelope_facts"] = envelope_facts
# the run's API-level completion vs the candidate-level rejection:
rec["status_disambiguation"] = {
    "api_final_status": rec.get("final_status"),
    "final_state_final_status": (
        rec["durable"]["final_state"]["final_status"]),
    "candidate_level_final_status":
        envelope_facts["candidate_classify"]["final_status"],
    "note": ("the RUN completed (INVENTION_UNDER_DEVELOPMENT — GEN 1 "
             "presented at maturity EVIDENCE_SUPPORTED with the honest "
             "line 'none yet survived the full challenge gauntlet', stop "
             "reason DIRECTIONAL_PROPOSAL_TRANSPORT) while the "
             "CANDIDATE was REJECTED at the adversarial gauntlet; the "
             "improve stage deferred to the kill point (delta_real "
             "false), so no CHILDREN_ADMITTED exists and the committed "
             "typing conditions apply verbatim"),
}
OUT.write_text(json.dumps(rec, indent=1, default=str))
print("enriched ->", OUT)
print("attack transport:", json.dumps(ar.get("transport"))[:120])
print("ring verdict:", envelope_facts["ring_observation"]["verdict"][:80])
