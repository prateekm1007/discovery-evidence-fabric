"""discovery_fabric/engine/error_critic.py — the LLM error critic
(owner merged-and-locked DIR 3; builder-r190s1).

PURPOSE: the mechanism-level error class the deterministic tools cannot
see (the consultant's DEV audit: 71% of candidate texts carry serious
errors, 23/34 of them mechanism-level — physics/chemistry and internal
logic the citation/falsification and unit/arithmetic layers are blind
to). The critic returns TYPED flags with a one-line reason each:

  PHYS       a mechanism or quantity claim contrary to physical law,
             materially wrong in direction or magnitude at the stated
             scale
  CONSTR     violates the problem's own stated hard constraints
  LOGIC      internal contradiction, inverted causality, or a
             falsification test that does not test the claimed
             mechanism
  INCOMPLETE the deliverable contract is missing (no mechanism, no
             falsification test, no stated prediction)

MODEL-FAMILY INDEPENDENCE (Art. 26 / AM54): the critic families are
hunyuan (hy4-flash via cent-ai) and qwen (qwen3.8-max via xkiro) —
both DISTINCT from the agnes generator. The transport is INJECTED
(no network at import; the engine contract).

VARIANTS (the four the owner named, calibrated on the committed label
set; the best is kept by F1 — the bar: recall >= 60% on serious
errors, <= 25% false flags on clean texts, registered as a typed
amendment in eval/r190s1_critic_prereg.json BEFORE any calibration
byte):
  checklist      single-pass 4-class checklist, one family
  decomposition  per-claim decomposition then per-claim flagging, one
                 family (two calls)
  union          checklist on BOTH families; the union of the flags
  intersection   checklist on BOTH families; the intersection

A flag nobody raised = no flag. The critic NEVER edits, rejects or
gates on its own: selection policy (DIR 4) consumes the flags.
"""
from __future__ import annotations

import json
import re
from typing import Any, Callable, Dict, List, Optional

FLAG_CLASSES = ("PHYS", "CONSTR", "LOGIC", "INCOMPLETE")

SEATS: Dict[str, Dict[str, Any]] = {
    "hy4-flash-centai": {
        "base": "https://api.cent-ai.dev/v1",
        "key_env": "CENT_AI_API_KEY",
        "model": "hy4-flash:free",
        "family": "hunyuan",
        # 4000 (the r135/r184 measured reasoning-burn fix): at 2000
        # hy4 burns the budget on reasoning_content and returns
        # 200-with-EMPTY content on long prompts.
        "max_tokens": 4000,
    },
    "qwen3.8-max-xkiro": {
        "base": "https://api.xkiro.com/v1",
        "key_env": "XKIRO_API_KEY",
        "model": "qwen/qwen3.8-max:free",
        "family": "qwen",
        "max_tokens": 3000,
    },
}

Transport = Callable[[str, str, str, int], str]
"""transport(base_url, api_key, model, user_prompt, max_tokens) ->
content text. Raises on failure; the CALLER owns the retry ladder."""


def _packet_block(problem: Dict[str, Any]) -> str:
    return (
        f"DEVICE: {problem.get('device', '')}\n"
        f"FAILURE (the plateau to beat): {problem.get('failure', '')}\n"
        f"HARD CONSTRAINTS (must hold): {problem.get('constraint', '')}\n"
        f"TASK: {problem.get('question', '')}"
    )


def _checklist_prompt(problem: Dict[str, Any], text: str) -> str:
    return (
        "You are a hostile engineering reviewer. Audit the PROPOSAL "
        "below against the PROBLEM PACKET. Flag ONLY serious, "
        "defensible errors — the classes:\n"
        "PHYS: a mechanism or quantity claim contrary to physical law, "
        "or materially wrong in direction/magnitude at the stated "
        "scale.\n"
        "CONSTR: violates the problem's own stated hard constraints.\n"
        "LOGIC: internal contradiction, inverted causality, or a "
        "falsification test that does not test the claimed mechanism.\n"
        "INCOMPLETE: missing deliverable contract (no mechanism, no "
        "falsification test, no stated prediction).\n"
        "Do NOT flag style, brevity, optimism or missing detail beyond "
        "those classes. A correct-but-unexciting proposal gets NO "
        "flags.\n\n"
        f"PROBLEM PACKET:\n{_packet_block(problem)}\n\n"
        f"PROPOSAL:\n{text}\n\n"
        "Answer with ONLY this JSON (no prose):\n"
        '{"flags": [{"class": "PHYS|CONSTR|LOGIC|INCOMPLETE", '
        '"reason": "one line"}, ...]}\n'
        'Use {"flags": []} when the proposal has no serious error.'
    )


def _decompose_prompt(problem: Dict[str, Any], text: str) -> str:
    return (
        "Decompose the PROPOSAL below into its ATOMIC checkable claims "
        "(mechanism steps, quantities, constraint statements, the "
        "falsification test). Output ONLY this JSON (no prose):\n"
        '{"claims": ["...", "..."]}\n\n'
        f"PROBLEM PACKET (context only):\n{_packet_block(problem)}\n\n"
        f"PROPOSAL:\n{text}"
    )


def _claim_flag_prompt(problem: Dict[str, Any], text: str,
                       claim: str) -> str:
    return (
        "You are a hostile engineering reviewer. Audit ONE claim from "
        "the proposal against the PROBLEM PACKET. Flag ONLY serious, "
        "defensible errors, one class per finding:\n"
        "PHYS: contrary to physical law / materially wrong direction or "
        "magnitude at the stated scale.\n"
        "CONSTR: violates the problem's stated hard constraints.\n"
        "LOGIC: contradicts the proposal's own other claims or inverts "
        "causality.\n"
        "INCOMPLETE: the claim asserts a deliverable the proposal never "
        "actually provides.\n"
        "No flag for style or optimism.\n\n"
        f"PROBLEM PACKET:\n{_packet_block(problem)}\n\n"
        f"FULL PROPOSAL (context):\n{text}\n\n"
        f"CLAIM TO AUDIT: {claim}\n\n"
        "Answer with ONLY this JSON:\n"
        '{"flags": [{"class": "...", "reason": "one line"}]}\n'
        'or {"flags": []} if the claim is sound.'
    )


def _parse_flags(raw: str) -> List[Dict[str, str]]:
    """Tolerant JSON flag parse (the verdict-parse discipline: one
    defensible reading, never a guess)."""
    if not raw:
        return []
    m = re.search(r"\{[\s\S]*\}", raw)
    if not m:
        return []
    try:
        doc = json.loads(m.group(0))
    except json.JSONDecodeError:
        return []
    out: List[Dict[str, str]] = []
    for f in doc.get("flags") or []:
        if not isinstance(f, dict):
            continue
        cls = str(f.get("class", "")).strip().upper()
        if cls not in FLAG_CLASSES:
            continue
        reason = str(f.get("reason", "")).strip()[:200]
        if not reason:
            reason = "(no reason given)"
        out.append({"class": cls, "reason": reason})
    return out


def _merge_flags(*flag_lists: List[Dict[str, str]],
                 op: str = "union") -> List[Dict[str, str]]:
    if op == "union":
        seen: Dict[str, Dict[str, str]] = {}
        for fl in flag_lists:
            for f in fl:
                k = f["class"] + "|" + f["reason"]
                seen.setdefault(k, f)
        return sorted(seen.values(), key=lambda f: f["class"])
    # intersection: a class survives only if EVERY list raised it
    classes: Optional[set] = None
    keep: Dict[str, Dict[str, str]] = {}
    for fl in flag_lists:
        cls_here = {f["class"] for f in fl}
        classes = (cls_here if classes is None
                   else (classes & cls_here))
    if not classes:
        return []
    for fl in flag_lists:
        for f in fl:
            if f["class"] in classes:
                keep.setdefault(f["class"] + "|" + f["reason"], f)
    return sorted(keep.values(), key=lambda f: f["class"])


def critic_checklist(problem: Dict[str, Any], text: str,
                     transport: Transport, base: str, key: str,
                     model: str,
                     max_tokens: int) -> List[Dict[str, str]]:
    raw = transport(base + "/chat/completions", key, model,
                    _checklist_prompt(problem, text), max_tokens)
    return _parse_flags(raw)


def critic_decomposition(problem: Dict[str, Any], text: str,
                         transport: Transport, base: str, key: str,
                         model: str,
                         max_tokens: int) -> List[Dict[str, str]]:
    raw = transport(base + "/chat/completions", key, model,
                    _decompose_prompt(problem, text), max_tokens)
    m = re.search(r"\{[\s\S]*\}", raw or "")
    claims: List[str] = []
    if m:
        try:
            claims = [str(c) for c in
                      (json.loads(m.group(0)).get("claims") or [])][:12]
        except json.JSONDecodeError:
            claims = []
    if not claims:
        # typed fallback: decomposition failed -> one whole-text pass
        # (never silent, never a re-roll)
        return critic_checklist(problem, text, transport, base,
                                key, model, max_tokens)
    out: List[Dict[str, str]] = []
    for c in claims:
        raw2 = transport(base + "/chat/completions", key, model,
                        _claim_flag_prompt(problem, text, c),
                        max_tokens)
        out.extend(_parse_flags(raw2))
    return _merge_flags(out, op="union")


def run_critic(variant: str, problem: Dict[str, Any], text: str,
               transport: Transport, keys: Dict[str, str],
               family: str = "hy4-flash-centai") -> Dict[str, Any]:
    """Run one critic variant. Returns the typed record (never raises
    through to the caller — a transport failure is a typed REFUSED
    record; the caller decides the retry)."""
    seat = SEATS.get(family)
    if seat is None or not keys.get(seat["key_env"]):
        return {"variant": variant, "status": "REFUSED",
                "reason": "unknown seat or missing key", "flags": [],
                "serious": False}
    base, key, mt = seat["base"], keys[seat["key_env"]], seat["max_tokens"]
    try:
        if variant == "checklist":
            flags = critic_checklist(problem, text, transport,
                                     base, key, seat["model"], mt)
        elif variant == "decomposition":
            flags = critic_decomposition(problem, text, transport,
                                        base, key, seat["model"], mt)
        elif variant in ("union", "intersection"):
            if not all(keys.get(SEATS[s]["key_env"])
                       for s in ("hy4-flash-centai",
                                 "qwen3.8-max-xkiro")):
                return {"variant": variant, "status": "REFUSED",
                        "reason": "two-family variant needs both keys",
                        "flags": [], "serious": False}
            fl_a = critic_checklist(problem, text, transport, base,
                                    key, seat["model"], mt)
            s2 = SEATS["qwen3.8-max-xkiro"]
            fl_b = critic_checklist(problem, text, transport,
                                    s2["base"],
                                    keys[s2["key_env"]],
                                    s2["model"],
                                    s2["max_tokens"])
            flags = _merge_flags(fl_a, fl_b,
                                 op=("union" if variant == "union"
                                     else "intersection"))
        else:
            return {"variant": variant, "status": "REFUSED",
                    "reason": f"unknown variant {variant}", "flags": [],
                    "serious": False}
    except Exception as e:  # noqa: BLE001
        return {"variant": variant, "status": "TRANSPORT_FAILED",
                "reason": f"{type(e).__name__}: {str(e)[:160]}",
                "flags": [], "serious": False}
    return {
        "variant": variant,
        "status": "OK",
        "family": seat["family"] if variant in ("checklist",
                                                "decomposition")
        else ["hunyuan", "qwen"],
        "flags": flags,
        "n_flags": len(flags),
        "flag_classes": sorted({f["class"] for f in flags}),
        "serious": bool(flags),
    }
