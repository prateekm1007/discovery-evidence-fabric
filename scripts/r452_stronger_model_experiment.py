#!/usr/bin/env python3
"""scripts/r452_stronger_model_experiment.py — R452: the STRONGER MODEL
EXPERIMENT (Constitution v2.5.0 Article LXXI — capability identity and
model provenance).

THE QUESTION (operator directive item 8/9): a transport repair silently
reduced the engine to a weak emergency model while the product ambition
stayed unchanged. Can a STRONGER model materially raise the MEASURED
capability tier — and can the tier now be recorded honestly, with model
identity + revision/hash + provider as scientific provenance?

DESIGN (Art. LXXI: tiers are MEASURED, never asserted):

  For each candidate model configuration:
    1. resolve model identity + revision sha from the provider API
    2. run the five capability probes (TIER_2..TIER_6), each scored by
       DETERMINISTIC code (regex/string checks — no LLM judging LLM;
       reviewer_provenance=AI_REVIEW disclosed for the harness itself)
    3. measure the tier with capability_tier.measure_capability_tier
    4. record the Article LXXI experiment identity tuple

  Baseline: the engine's current operative transport (the sandbox zai
  gateway serving glm-4-plus). Candidates: stronger open models via the
  Hugging Face router (operator-provided HF token), preference order
  Qwen3-14B > Qwen3-32B > Qwen2.5-72B-Instruct (the audit's degraded
  state was Qwen3-1.7B; each candidate is a materially larger model of
  the same family, so the comparison is family-controlled).

  HONESTY RULES: a transport failure is a typed TRANSPORT_UNAVAILABLE
  record, never a failed probe (Art. LXI). A probe that cannot run
  counts as failed for tier purposes (fail-closed, Art. V) AND is
  disclosed as not-measured. No capability claim above the measured
  tier anywhere in the output (Art. LXXI machine-checked at the end).
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

OUT_DIR = REPO_ROOT / "R452"
HF_TOKEN_ENV = "HF_TOKEN"
HF_ROUTER = "https://router.huggingface.co/v1/chat/completions"
HF_MODEL_API = "https://huggingface.co/api/models/"

HF_CANDIDATES = [
    "Qwen/Qwen3-14B",
]
ZAI_GATEWAY = "http://127.0.0.1:8787/v1/chat/completions"

# ---------------------------------------------------------------------------
# The five capability probes (deterministic scoring)
# ---------------------------------------------------------------------------

P2_PASSAGE = (
    "Experiment record: the cold plate maintained a base temperature of "
    "45.2 C at a 300 W heat load with a 2.5 mm thick copper substrate "
    "and 12 mm internal channels."

)

PROBES = [
    {
        "probe": "evidence_citation",
        "tier": "TIER_2_EVIDENCE_CAPABLE",
        "prompt": (
            "You are an evidence extraction engine. From the passage "
            "below, extract the substrate thickness. Answer with EXACTLY "
            "one line in this format and nothing else:\n"
            "span=<the exact verbatim substring of the passage that "
            "contains the thickness> | value=<number> | unit=<unit>\n\n"
            f"PASSAGE: {P2_PASSAGE}"),
        "score": None,  # bound below (deterministic scorer)
    },
    {
        "probe": "causal_chain_completion",
        "tier": "TIER_3_REASONING_CAPABLE",
        "prompt": (
            "You are a causal mechanism engine. Device: fanless sealed "
            "electronics chassis. Failure: sustained load heat "
            "accumulation throttles the processor. Answer with EXACTLY "
            "one line per field, format 'field=value', fields: "
            "mechanism, intervention, effect, boundary. Each value must "
            "be a concrete physical statement (>= 8 words). No other "
            "text."),
        "score": None,  # bound below
    },
    {
        "probe": "attack_execution",
        "tier": "TIER_4_ADVERSARIAL_SCIENTIFIC",
        "prompt": (
            "You are a hostile invention attacker. Candidate mechanism: "
            "a passive radiative cooling coating that reflects 96% of "
            "solar irradiance and emits in the 8-13 um atmospheric "
            "window, applied to a sealed outdoor enclosure. Produce at "
            "least 2 objections. Format per objection (one line each): "
            "objection=<substantive text> | class=<one of CAUSAL_INVALIDITY,"
            "BOUNDARY_CONDITION, EVIDENCE_CONTRADICTION, BASELINE_EQUIVALENCE,"
            "IMPLEMENTATION_IMPOSSIBILITY, SCALING_FAILURE, SAFETY_FAILURE> | "
            "severity=<HIGH|MEDIUM|LOW>. No other text."),
        "score": None,  # bound below
    },
    {
        "probe": "parameterized_engineering_synthesis",
        "tier": "TIER_5_ENGINEERING",
        "prompt": (
            "You are a parametric engineering synthesizer. Design inside "
            "these declared envelopes ONLY: panel_width [80,400] mm, "
            "panel_length [80,400] mm, substrate_t [0.5,10] mm. Answer "
            "with EXACTLY one line per parameter, format "
            "'param=<name> | value=<number> | unit=mm', values strictly "
            "inside their envelopes. No other text."),
        "score": None,  # bound below
    },
    {
        "probe": "closed_loop_learning",
        "tier": "TIER_6_EXPERIMENT_REALITY_LOOP",
        "prompt": (
            "You are a causal learning engine. Prior hypothesis: 'a 3 mm "
            "substrate is sufficient to keep the base below 60 C at 300 "
            "W.' NEW OBSERVATION (external measurement): at 300 W the "
            "base reached 71 C with the 3 mm substrate. Answer with "
            "EXACTLY two lines, format 'belief_update=<text>' then "
            "'successor_change=<text>': the update must reference the "
            "observed 71 C and the successor must change a concrete "
            "design parameter. No other text."),
        "score": None,  # bound below
    },
]


def score_evidence_citation(reply: str) -> bool:
    m = re.search(r"span=(.*?)\s*\|\s*value=(.*?)\s*\|\s*unit=(.*)",
                  reply, re.I)
    if not m:
        return False
    span, value, unit = (m.group(1).strip(), m.group(2).strip(),
                         m.group(3).strip())
    if span not in P2_PASSAGE:
        return False
    try:
        return abs(float(value) - 2.5) < 1e-9 and unit.lower() == "mm"
    except ValueError:
        return False


def score_causal_chain(reply: str) -> bool:
    fields = {}
    for line in reply.splitlines():
        m = re.match(r"\s*(mechanism|intervention|effect|boundary)=(.+)",
                     line.strip(), re.I)
        if m:
            fields[m.group(1).lower()] = m.group(2).strip()
    if set(fields) != {"mechanism", "intervention", "effect", "boundary"}:
        return False
    if any(len(v.split()) < 8 for v in fields.values()):
        return False
    return fields["mechanism"].lower() != fields["intervention"].lower()


def score_attack_execution(reply: str) -> bool:
    objections = re.findall(
        r"objection=(.+?)\s*\|\s*class=(\w+)", reply, re.I)
    classes = {"CAUSAL_INVALIDITY", "BOUNDARY_CONDITION",
               "EVIDENCE_CONTRADICTION", "BASELINE_EQUIVALENCE",
               "IMPLEMENTATION_IMPOSSIBILITY", "SCALING_FAILURE",
               "SAFETY_FAILURE"}
    if len(objections) < 2:
        return False
    for text, cls in objections:
        if len(text.split()) < 10:
            return False
        if cls.strip().upper() not in classes:
            return False
    return True


def score_engineering_synthesis(reply: str) -> bool:
    got = {}
    for line in reply.splitlines():
        m = re.match(r"\s*param=(.*?)\s*\|\s*value=(.*?)\s*\|\s*unit=(.*)",
                     line.strip(), re.I)
        if m:
            try:
                got[m.group(1).strip().lower()] = float(m.group(2))
            except ValueError:
                return False
    envs = {"panel_width": (80, 400), "panel_length": (80, 400),
            "substrate_t": (0.5, 10)}
    if set(got) != set(envs):
        return False
    return all(lo < v < hi for v, (lo, hi) in
               ((got[k], envs[k]) for k in envs))


def score_closed_loop_learning(reply: str) -> bool:
    upd = re.search(r"belief_update=(.+)", reply, re.I)
    suc = re.search(r"successor_change=(.+)", reply, re.I)
    if not upd or not suc:
        return False
    update_text = upd.group(1).lower()
    successor_text = suc.group(1).lower()
    return ("71" in update_text and "substrate" in update_text
            and re.search(r"\b(mm|thickness|substrate|parameter)\b",
                          successor_text) is not None)


PROBES[0]["score"] = score_evidence_citation
PROBES[1]["score"] = score_causal_chain
PROBES[2]["score"] = score_attack_execution
PROBES[3]["score"] = score_engineering_synthesis
PROBES[4]["score"] = score_closed_loop_learning


# ---------------------------------------------------------------------------
# Transports
# ---------------------------------------------------------------------------

def _post_json(url: str, payload: dict, headers: dict,
               timeout_s: int = 90) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST")
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        return json.loads(resp.read().decode("utf-8"))


def hf_chat(model_id: str, prompt: str, token: str) -> dict:
    data = _post_json(HF_ROUTER, {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 700,
        "temperature": 0.0,
    }, {"Authorization": f"Bearer {token}"})
    return {"reply": data["choices"][0]["message"]["content"] or ""}


def zai_chat(prompt: str, key: str, model: str = "glm-4-plus") -> dict:
    data = _post_json(ZAI_GATEWAY, {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
    }, {"Authorization": f"Bearer {key}"}, timeout_s=75)
    return {"reply": data["choices"][0]["message"]["content"] or ""}


def hf_model_revision(model_id: str, token: str) -> dict:
    req = urllib.request.Request(
        HF_MODEL_API + model_id,
        headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        info = json.loads(resp.read().decode("utf-8"))
    return {"sha": info.get("sha"), "pipeline_tag": info.get("pipeline_tag"),
            "downloads": info.get("downloads"),
            "library": info.get("library_name")}


# ---------------------------------------------------------------------------
# The experiment
# ---------------------------------------------------------------------------

def run_probe_battery(chat_fn, model_label: str) -> dict:
    results = {}
    transcripts = {}
    for probe in PROBES:
        t0 = time.time()
        try:
            out = chat_fn(probe["prompt"])
            reply = out["reply"]
            passed = bool(probe["score"](reply))
            results[probe["probe"]] = passed
            transcripts[probe["probe"]] = {
                "reply_head": reply[:400],
                "elapsed_s": round(time.time() - t0, 1),
                "verdict": "PASS" if passed else "FAIL",
            }
        except Exception as exc:  # noqa: BLE001 — typed transport record
            results[probe["probe"]] = False
            transcripts[probe["probe"]] = {
                "error": f"{type(exc).__name__}: {exc}",
                "elapsed_s": round(time.time() - t0, 1),
                "verdict": "TRANSPORT_UNAVAILABLE",
            }
    return {"probe_results": results, "transcripts": transcripts}


def main() -> int:
    from discovery_fabric.engine import capability_tier as ct

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    record = {
        "experiment": "R452_STRONGER_MODEL_EXPERIMENT",
        "constitution": "v2.5.0 Article LXXI (capability identity and "
                        "model provenance)",
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "reviewer_provenance": "AI_REVIEW (deterministic mechanical "
                               "scoring; no LLM judged another LLM's "
                               "output)",
        "design": {
            "question": ("does a materially stronger model raise the "
                         "MEASURED capability tier of the engine's "
                         "model-derived stages?"),
            "baseline": "sandbox zai gateway (glm-4-plus) — the engine's "
                        "current operative transport",
            "candidates": HF_CANDIDATES,
            "family_control": ("the audit's degraded state was Qwen3-1.7B; "
                               "the candidates are materially larger "
                               "models of the same/control families"),
            "probes": [p["probe"] for p in PROBES],
            "honesty": ("transport failures are typed "
                        "TRANSPORT_UNAVAILABLE records, never failed "
                        "probes; unmeasured probes count as failed for "
                        "tier purposes (fail-closed) and are disclosed"),
        },
        "runs": [],
    }

    # --- baseline: the zai gateway --------------------------------------
    gw_key = ""
    env_file = Path("/home/z/my-project/.zai_gateway_env")
    if env_file.exists():
        gw_key = env_file.read_text().strip()
        # tolerate both bare-key and KEY=value formats
        gw_key = (gw_key.split("=", 1)[1].strip()
                  if gw_key.startswith("ZAI_GATEWAY_KEY=") else gw_key)
    # the gateway must already be alive (run under scripts/zai_gw_run.sh
    # or with the gateway started); probe health first
    import urllib.request as _u
    gateway_alive = False
    try:
        with _u.urlopen("http://127.0.0.1:8787/healthz", timeout=5) as r:
            gateway_alive = r.status == 200
    except Exception:  # noqa: BLE001
        gateway_alive = False

    if gateway_alive and gw_key:
        battery = run_probe_battery(
            lambda p: zai_chat(p, gw_key), "zai:glm-4-plus")
        measured = ct.measure_capability_tier(
            model_id="glm-4-plus", provider="zai-sandbox-gateway",
            probe_results=battery["probe_results"])
        record["runs"].append({
            "label": "BASELINE (current operative transport)",
            "model_id": "glm-4-plus",
            "model_revision": None,
            "provider": "zai-sandbox-gateway",
            "gateway_health": gateway_alive,
            **battery,
            "measured_tier": measured,
        })
    else:
        record["runs"].append({
            "label": "BASELINE (current operative transport)",
            "model_id": "glm-4-plus",
            "provider": "zai-sandbox-gateway",
            "gateway_health": gateway_alive,
            "status": "TRANSPORT_UNAVAILABLE",
            "note": ("the sandbox gateway was not alive during the "
                     "experiment — a typed absence, not a failed probe "
                     "(Art. LXI); the baseline tier is NOT measured here"),
        })

    # --- HF candidates ----------------------------------------------------
    token = os.environ.get(HF_TOKEN_ENV) or _read_hf_token_from_env_keys()
    if not token:
        record["hf_token_state"] = "ABSENT (no capability claim possible)"
    else:
        record["hf_token_state"] = "present (from env / .env.keys)"
        for model_id in HF_CANDIDATES:
            try:
                revision = hf_model_revision(model_id, token)
            except Exception as exc:  # noqa: BLE001
                record["runs"].append({
                    "label": f"HF candidate {model_id}",
                    "model_id": model_id,
                    "status": "MODEL_UNAVAILABLE",
                    "error": f"{type(exc).__name__}: {exc}",
                })
                continue
            battery = run_probe_battery(
                lambda p, mid=model_id: hf_chat(mid, p, token),
                model_id)
            measured = ct.measure_capability_tier(
                model_id=model_id, provider="hf-router",
                probe_results=battery["probe_results"],
                model_revision=revision.get("sha"))
            ident = ct.capability_identity(
                model_id=model_id, provider="hf-router",
                constitution_version="2.5.0",
                model_revision=revision.get("sha"),
                capability_tier=measured["tier"])
            record["runs"].append({
                "label": f"HF candidate {model_id}",
                "model_id": model_id,
                "model_revision": revision.get("sha"),
                "provider": "hf-router",
                "revision_info": revision,
                **battery,
                "measured_tier": measured,
                "capability_identity": ident,
            })

    # --- machine-checked Art. LXXI conclusion ----------------------------
    measured_runs = [r for r in record["runs"] if "measured_tier" in r]
    unmeasured = [r for r in record["runs"]
                  if r.get("status") == "TRANSPORT_UNAVAILABLE"
                  or any(t.get("verdict") == "TRANSPORT_UNAVAILABLE"
                         for t in (r.get("transcripts") or {}).values())]
    top_tier = (max((r["measured_tier"]["tier"] for r in measured_runs),
                    key=lambda t: ct.TIER_ORDER.index(t))
                if measured_runs else ct.TIER_1)
    record["conclusion"] = {
        "runs_measured": len(measured_runs),
        "runs_transport_unavailable": len(unmeasured),
        "tiers": {r.get("model_id"): r["measured_tier"]["tier"]
                  for r in measured_runs},
        "capability_claims_allowed": [
            {"claim": c,
             **ct.evaluate_capability_claim(top_tier, c)}
            for c in ("evidence-grounded synthesis",
                      "causal mechanism reasoning",
                      "adversarial attack execution",
                      "parameterized engineering synthesis")
        ] if measured_runs else [],
        "note": ("the engine's OPERATIVE tier is bounded by its current "
                 "transport configuration; this experiment measures "
                 "candidate configurations for the operator's capacity "
                 "decision — no claim above the measured tier is made "
                 "anywhere in this record (Art. LXXI)"),
    }
    out = OUT_DIR / "STRONGER_MODEL_EXPERIMENT.json"
    out.write_text(json.dumps(record, indent=2))
    print(json.dumps({
        "written": str(out),
        "runs": [
            {"label": r.get("label"),
             "tier": (r.get("measured_tier") or {}).get("tier"),
             "probes": r.get("probe_results"),
             "status": r.get("status")}
            for r in record["runs"]],
        "conclusion": record["conclusion"]["tiers"],
    }, indent=1))
    return 0


def _read_hf_token_from_env_keys() -> str:
    p = REPO_ROOT / ".env.keys"
    if not p.exists():
        return ""
    for line in p.read_text().splitlines():
        line = line.strip()
        if line.startswith("HF_TOKEN=") or line.startswith("HF_API_KEY="):
            return line.split("=", 1)[1].strip()
    return ""


if __name__ == "__main__":
    sys.exit(main())
