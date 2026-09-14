"""discovery_fabric/engine/transport_capability.py — R451-C1.2.

Operator directive (transport capability & resilience layer, 2026-09-13):

    Build a provider/model capability and resilience layer, not another
    hardcoded fallback list. The implementation must:

    [ ] distinguish MODEL from PROVIDER from ACCOUNT
    [ ] distinguish FREE-CATALOG from FREE-TO-OUR-ACCOUNT
    [ ] probe each route before admitting it
    [ ] classify CREDIT_EXHAUSTED / RATE_LIMITED / MODEL_NOT_FOUND /
        AUTH_FAILED / INVALID_RESPONSE / PROVIDER_UNAVAILABLE
    [ ] support independent provider failure domains
    [ ] support self-hosted/open-weight emergency route
    [ ] record model/provider/route provenance
    [ ] record exact transport outcome
    [ ] never retry a permanently invalid model identifier
    [ ] never represent a different provider as redundant when it
        shares the same economic account
    [ ] preserve deterministic downstream processing

This module implements the CAPABILITY side of that directive. The
failure-classification side lives in provider_health.py (which gained
MODEL_NOT_FOUND this round) and the routing side in model_routing.py /
llm_registry.py (which gained account_domain on every rung, ledger
line, and cost-provenance record).

The four resource classes (operator's diagram, 2026-09-13):

    HF Router credits        one economic account, many serving
                             providers; monthly included credits;
                             measured 402-depleted (R450 record)
    ZeroGPU compute          a SEPARATE quota budget (HF Spaces GPU
                             minutes); not consumable from this coding
                             environment
    External APIs            account-dependent (owner keys)
    Self-hosted open weights local compute, no inference bill —
                             the strategic escape from the account-
                             failure class; the R451 baseline

Constitutional contract (Art. III, V, VI, XVII, XXI.3, XXV, XXVII, LXI):
  - A catalog row is a CATALOG claim, never an entitlement: admission
    requires a MEASURED probe through THIS account's transport. A
    $0.00 catalog price does not admit a route (the OVHcloud row on
    Qwen/Qwen3.8-27B advertises 0.00/0.00 while is_free=False — the
    canonical FREE-CATALOG-vs-FREE-TO-ACCOUNT specimen).
  - Probes are MEASUREMENTS, not engine routing: the engine's call
    path is llm_registry.generate (cost-policy-filtered). This module
    never routes a discovery call; it measures whether a route COULD.
  - Every probe outcome is classified onto the same closed failure
    taxonomy as real calls (provider_health.classify_failure) and
    persisted — a probe failure is never absence (Art. XXI.3).
  - MODEL, PROVIDER, ACCOUNT are three distinct failure domains: the
    matrix records all three per route, and REDUNDANCY is counted
    across ACCOUNT domains only — two providers that bill the same
    account are one failure domain wearing two names.
  - Deterministic downstream processing is untouched: this module
    adds no generation path, mutates no gate, and its state lives in
    ENGINE_RUNS/transport_capability/ (runtime telemetry, same class
    as the routing ledger).
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .provider_health import classify_failure

REPO_ROOT = Path(__file__).resolve().parents[2]
CAPABILITY_DIR = REPO_ROOT / "ENGINE_RUNS" / "transport_capability"
MATRIX_PATH = CAPABILITY_DIR / "probes.jsonl"

# ---------------------------------------------------------------------------
# The account-domain vocabulary (closed; Art. XXVII — a declared policy
# input, one entry per ECONOMIC failure domain, not per vendor)
# ---------------------------------------------------------------------------
ACCOUNT_DOMAIN_VOCAB = (
    "LOCAL_COMPUTE",              # self-hosted weights: no account, no bill
    "HF_ACCOUNT_CREDITS",         # the HF router's per-account included
    #                              # credits — EVERY serving provider
    #                              # reached through router.huggingface.co
    #                              # bills THIS one domain (R450: 402 on
    #                              # every model with the token valid)
    "ZERO_GPU_QUOTA",             # HF Spaces GPU minutes — a separate
    #                              # budget from inference credits
    "SANDBOX_ENVIRONMENT_GRANT",  # the coding sandbox's embedded grant
    "OWNER_TOKENROUTER_ACCOUNT",  # the owner's Token Router key
    "OWNER_OPENROUTER_ACCOUNT",
    "OWNER_NVIDIA_ACCOUNT",
    "OWNER_ANTHROPIC_ACCOUNT",
    "OWNER_GOOGLE_ACCOUNT",
    "OWNER_OPENAI_ACCOUNT",
    "OWNER_ALIBABA_ACCOUNT",
    "OWNER_DEEPSEEK_ACCOUNT",
    "OWNER_MISTRAL_ACCOUNT",
    # R456-A3: the operator's free-tier router quartet — four DISTINCT
    # economic accounts (the operator's rotation rule: token exhaustion
    # on one advances the cascade to the next; genuine redundancy
    # because the accounts do not share a billing domain)
    "OWNER_UNOROUTER_ACCOUNT",
    "OWNER_XKIRO_ACCOUNT",
    "OWNER_APINEX_ACCOUNT",
    "OWNER_BAI_ACCOUNT",
    "UNDECLARED",                 # honest unknown — never guessed
)

#: the resource classes of the operator's diagram
RESOURCE_CLASSES = (
    "HF_ROUTER_CREDITS",
    "ZERO_GPU_QUOTA",
    "EXTERNAL_API",
    "SELF_HOSTED_OPEN_WEIGHTS",
)

TRANSPORT_CAPABILITY_VERSION = "transport_capability/1.0.0"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z"


# ---------------------------------------------------------------------------
# RouteSpec — MODEL (model) x PROVIDER (serving provider) x ACCOUNT
# (account_domain) as three DISTINCT fields, plus the transport and the
# CATALOG claims (kept visibly separate from the measured facts)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class RouteSpec:
    route_id: str
    provider: str                       # the SERVING provider (novita...)
    model: str                          # the MODEL id as called
    transport: str                      # the HTTP endpoint actually called
    credential_env: str                 # the env var the route needs
    account_domain: str                 # the ECONOMIC account (vocabulary)
    cost_basis: str                     # model_cost_policy vocabulary
    locality: str                       # LOCAL | REMOTE
    resource_class: str                 # RESOURCE_CLASSES vocabulary
    # ---- CATALOG claims (declared inputs — NEVER admission evidence) ---
    catalog_pricing: str = "UNDECLARED"
    catalog_declares_free: Optional[bool] = None
    catalog_supports_tools: Optional[bool] = None
    catalog_supports_structured_output: Optional[bool] = None
    note: str = ""


# ---------------------------------------------------------------------------
# THE route catalog (operator probe matrix, 2026-09-13, verbatim order:
# Qwen3.8-27B/Novita, Qwen3.8-27B/DeepInfra, GLM-5.3-Flash/Together,
# GLM-5.3-Flash/Fireworks, Gemma-4-26B-A4B/DeepInfra, Qwen3-14B/DeepInfra,
# Qwen3-4B-Thinking/self-hosted — plus the resource-class completeness
# rows). Catalog fields below were read LIVE from
# https://router.huggingface.co/v1/models on 2026-09-13 (public endpoint,
# no auth) — recorded inputs, not account measurements.
# ---------------------------------------------------------------------------
HF_ROUTER = "https://router.huggingface.co"

ROUTE_CATALOG: Tuple[RouteSpec, ...] = (
    RouteSpec(
        route_id="hf:Qwen/Qwen3.8-27B@novita",
        provider="novita", model="Qwen/Qwen3.8-27B",
        transport=f"{HF_ROUTER}/novita/v1/chat/completions",
        credential_env="HF_TOKEN",
        account_domain="HF_ACCOUNT_CREDITS", cost_basis="PAID_API",
        locality="REMOTE", resource_class="HF_ROUTER_CREDITS",
        catalog_pricing="novita $0.42/$3.00 per M tokens (live catalog "
                        "2026-09-13); is_free=False",
        catalog_supports_tools=True,
        catalog_supports_structured_output=True,
        note="operator probe-matrix row 1"),
    RouteSpec(
        route_id="hf:Qwen/Qwen3.8-27B@deepinfra",
        provider="deepinfra", model="Qwen/Qwen3.8-27B",
        transport=f"{HF_ROUTER}/deepinfra/v1/chat/completions",
        credential_env="HF_TOKEN",
        account_domain="HF_ACCOUNT_CREDITS", cost_basis="PAID_API",
        locality="REMOTE", resource_class="HF_ROUTER_CREDITS",
        catalog_pricing="deepinfra $0.40/$3.00 per M tokens (live "
                        "catalog 2026-09-13); is_free=False",
        catalog_supports_tools=True,
        catalog_supports_structured_output=True,
        note="operator probe-matrix row 2 — SAME economic account as "
             "row 1 (provider diversity is NOT account redundancy)"),
    RouteSpec(
        route_id="hf:zai-org/GLM-5.3-Flash@together",
        provider="together", model="zai-org/GLM-5.3-Flash",
        transport=f"{HF_ROUTER}/together/v1/chat/completions",
        credential_env="HF_TOKEN",
        account_domain="HF_ACCOUNT_CREDITS", cost_basis="PAID_API",
        locality="REMOTE", resource_class="HF_ROUTER_CREDITS",
        catalog_pricing="together $0.15/$0.50 per M tokens (live "
                        "catalog 2026-09-13); is_free=False",
        catalog_supports_tools=True,
        catalog_supports_structured_output=False,
        note="operator probe-matrix row 3"),
    RouteSpec(
        route_id="hf:zai-org/GLM-5.3-Flash@fireworks-ai",
        provider="fireworks-ai", model="zai-org/GLM-5.3-Flash",
        transport=f"{HF_ROUTER}/fireworks-ai/v1/chat/completions",
        credential_env="HF_TOKEN",
        account_domain="HF_ACCOUNT_CREDITS", cost_basis="PAID_API",
        locality="REMOTE", resource_class="HF_ROUTER_CREDITS",
        catalog_pricing="fireworks-ai pricing not listed on the row "
                        "(live catalog 2026-09-13); is_free=False",
        catalog_supports_tools=True,
        catalog_supports_structured_output=True,
        note="operator probe-matrix row 4"),
    RouteSpec(
        route_id="hf:google/gemma-4-26B-A4B-it@deepinfra",
        provider="deepinfra", model="google/gemma-4-26B-A4B-it",
        transport=f"{HF_ROUTER}/deepinfra/v1/chat/completions",
        credential_env="HF_TOKEN",
        account_domain="HF_ACCOUNT_CREDITS", cost_basis="PAID_API",
        locality="REMOTE", resource_class="HF_ROUTER_CREDITS",
        catalog_pricing="deepinfra $0.07/$0.34 per M tokens (live "
                        "catalog 2026-09-13); is_free=False",
        catalog_supports_tools=True,
        catalog_supports_structured_output=True,
        note="operator probe-matrix row 5 — the operator audit's "
             "Gemma-4-26B-A4B middle-weight route"),
    RouteSpec(
        route_id="hf:Qwen/Qwen3-14B@deepinfra",
        provider="deepinfra", model="Qwen/Qwen3-14B",
        transport=f"{HF_ROUTER}/deepinfra/v1/chat/completions",
        credential_env="HF_TOKEN",
        account_domain="HF_ACCOUNT_CREDITS", cost_basis="PAID_API",
        locality="REMOTE", resource_class="HF_ROUTER_CREDITS",
        catalog_pricing="deepinfra $0.12/$0.24 per M tokens (live "
                        "catalog 2026-09-13); is_free=False",
        catalog_supports_tools=True,
        catalog_supports_structured_output=False,
        note="operator probe-matrix row 6 — the constrained-hardware "
             "serious-reasoning candidate"),
    RouteSpec(
        route_id="hf:Qwen/Qwen3-4B-Thinking-2507@nscale",
        provider="nscale", model="Qwen/Qwen3-4B-Thinking-2507",
        transport=f"{HF_ROUTER}/nscale/v1/chat/completions",
        credential_env="HF_TOKEN",
        account_domain="HF_ACCOUNT_CREDITS", cost_basis="PAID_API",
        locality="REMOTE", resource_class="HF_ROUTER_CREDITS",
        catalog_pricing="nscale $0.01/$0.03 per M tokens (live catalog "
                        "2026-09-13); is_free=False",
        catalog_supports_tools=True,
        catalog_supports_structured_output=True,
        note="operator probe-matrix row 7's HOSTED half — the "
             "self-hosted/open-weight half of the same row is the "
             "localqwen route below"),
    # --- the self-hosted open-weight route (the emergency route) -------
    RouteSpec(
        route_id="local:qwen3-1.7b@localqwen",
        provider="localqwen", model="qwen3-1.7b",
        transport="http://127.0.0.1:8790/v1/chat/completions",
        credential_env="LOCAL_QWEN_BASE_URL",
        account_domain="LOCAL_COMPUTE",
        cost_basis="ZERO_PAID_COST_SELF_HOSTED",
        locality="LOCAL", resource_class="SELF_HOSTED_OPEN_WEIGHTS",
        catalog_pricing="self-hosted weights (Qwen/Qwen3-1.7B, "
                        "apache-2.0, GGUF sha256 pinned in the provider "
                        "spec): no inference bill by construction",
        catalog_supports_tools=None,
        catalog_supports_structured_output=None,
        note="the R451 zero-paid baseline: llama.cpp llama-server b10930 "
             "on local CPU; the operator's open-weight inference proof "
             "(LOCAL_PROVIDER_READY six-rung chain)"),
    # --- resource-class completeness rows (external API class) ---------
    RouteSpec(
        route_id="api:z-ai/glm-5.3-free@tokenrouter",
        provider="tokenrouter", model="z-ai/glm-5.3-free",
        transport="https://api.tokenrouter.com/v1/chat/completions",
        credential_env="TOKEN_ROUTER_API_KEY",
        account_domain="OWNER_TOKENROUTER_ACCOUNT",
        cost_basis="FREE_TIER_API", locality="REMOTE",
        resource_class="EXTERNAL_API",
        catalog_pricing="z-ai free tier (owner statement 2026-09-05: "
                        "'GLM 5.3 is free to use'); measured healthy at "
                        "wiring time — free is NOT permanent, "
                        "re-measured per probe",
        catalog_supports_tools=None,
        catalog_supports_structured_output=None,
        note="the external-API resource class probe row"),
    RouteSpec(
        route_id="api:zai-org/GLM-5.3@sandbox-gateway",
        provider="zai", model="zai-org/GLM-5.3",
        transport="http://127.0.0.1:8787/v1/chat/completions",
        credential_env="ZAI_API_KEY",
        account_domain="SANDBOX_ENVIRONMENT_GRANT",
        cost_basis="ENVIRONMENT_GRANT", locality="LOCAL",
        resource_class="EXTERNAL_API",
        catalog_pricing="the sandbox's embedded grant — no operator "
                        "bill, but NOT self-hosted weights",
        catalog_supports_tools=None,
        catalog_supports_structured_output=None,
        note="the sandbox gateway row (env grant; ineligible under "
             "ZERO_PAID_COST — the distinction is recorded, "
             "never blurred)"),
)

#: The ZeroGPU budget — a SEPARATE quota from inference credits (HF
#: docs; operator states 40 min available). It is consumable only
#: inside an HF Space (the @spaces.GPU quota), never from this coding
#: environment — recorded honestly as a resource class, never probed,
#: never claimed (Art. XXV).
ZERO_GPU_BUDGET_NOTE = {
    "resource_class": "ZERO_GPU_QUOTA",
    "account_domain": "ZERO_GPU_QUOTA",
    "operator_stated_budget": "40 minutes (separate from inference "
                              "credits)",
    "separate_budget_rule": ("HF's ZeroGPU is a compute quota, not "
                             "inference-provider credit — the two are "
                             "tracked as separate budgets in any "
                             "resource plan (operator directive "
                             "2026-09-13)"),
    "state": "NOT_ACCESSIBLE_FROM_THIS_CODING_ENVIRONMENT",
    "why": ("ZeroGPU minutes are consumed inside HF Spaces via the "
            "@spaces.GPU decorator; this coding sandbox has no Space "
            "execution path. The open-weight self-hosted inference "
            "proof therefore runs on LOCAL_COMPUTE (the localqwen "
            "route), which is the same billing-resilience class: no "
            "inference bill (honest substitution, recorded — not a "
            "claim that ZeroGPU was used)"),
}


# ---------------------------------------------------------------------------
# The probe — ONE tiny structured-output completion through the route's
# REAL transport with THIS environment's credential state. Measures the
# 11 operator-required fields. The probe is a MEASUREMENT: it never
# routes a discovery call and never bypasses the cost policy for the
# engine's call path.
# ---------------------------------------------------------------------------
PROBE_SCHEMA = ("MECHANISM", "FALSIFIER")
_PROBE_PROMPT = (
    "Transport capability probe. Reply with exactly two lines, "
    "nothing else:\n"
    "MECHANISM: a catheter wall resists kinking when the septum is "
    "thick enough\n"
    "FALSIFIER: measure the collapse pressure of the septum"
)


def _field_lines(content: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for line in (content or "").splitlines():
        m = re.match(r"^\s*(MECHANISM|FALSIFIER)\s*:\s*(.+)$",
                     line.strip(), re.IGNORECASE)
        if m:
            out[m.group(1).upper()] = m.group(2).strip()
    return out


def probe_route(route: RouteSpec, timeout_s: int = 45,
                max_tokens: int = 96) -> Dict[str, Any]:
    """Probe ONE route. Returns the 11-field record:

        provider, model, http_status, latency_ms, token_usage,
        tool_support, structured_output_support, response_validity,
        failure_class, quota_credit_behavior, timestamp

    plus the route's identity triple (provider/model/account_domain —
    MODEL vs PROVIDER vs ACCOUNT as three distinct fields) and the
    catalog claims kept SEPARATE from the measured facts.

    Failure classification uses the SAME closed taxonomy as real calls
    (provider_health.classify_failure) — a probe failure is a typed
    transport fact, never absence (Art. XXI.3). Unknown stays UNKNOWN.
    """
    rec: Dict[str, Any] = {
        "probe_version": TRANSPORT_CAPABILITY_VERSION,
        "route_id": route.route_id,
        "provider": route.provider,
        "model": route.model,
        "account_domain": route.account_domain,
        "resource_class": route.resource_class,
        "transport": route.transport,
        "credential_env": route.credential_env,
        "credential_present": bool(
            os.environ.get(route.credential_env, "").strip()),
        "cost_basis": route.cost_basis,
        "locality": route.locality,
        "catalog_claims": {
            "pricing": route.catalog_pricing,
            "declares_free": route.catalog_declares_free,
            "supports_tools": route.catalog_supports_tools,
            "supports_structured_output":
                route.catalog_supports_structured_output,
            "class": "CATALOG_CLAIM — never admission evidence",
        },
        "note": route.note,
    }
    key = os.environ.get(route.credential_env, "").strip()
    if route.credential_env != "LOCAL_QWEN_BASE_URL" and not key:
        # no credential in THIS environment: the honest typed state is
        # PROVIDER_UNAVAILABLE (the registry's own vocabulary for a
        # missing key — the directive's required class) — the route was
        # NOT called, so AUTH_FAILED would be a false measurement claim
        rec.update({
            "http_status": None,
            "latency_ms": None,
            "token_usage": None,
            "tool_support": "UNMEASURED (no credential — catalog "
                            "declaration only)",
            "structured_output_support": "UNMEASURED (no credential)",
            "response_validity": "NOT_PROBED",
            "failure_class": "PROVIDER_UNAVAILABLE",
            "quota_credit_behavior": (
                "credential absent in this environment — the account "
                "state cannot be measured from here; PRIOR recorded "
                "account state (R450 round record): the HF account's "
                "router answered HTTP 402 'You have depleted your "
                "monthly included credits' for EVERY probed model "
                "while the token itself authenticated"),
            "timestamp": utc_now(),
            "probe_success": False,
        })
        return rec

    payload = {
        "model": route.model,
        "messages": [
            {"role": "system", "content":
                "RESPOND IN ENGLISH ONLY. Follow the requested output "
                "format exactly; no preamble, no markdown fences."},
            {"role": "user", "content": _PROBE_PROMPT},
        ],
        "temperature": 0.0,
        "max_tokens": max_tokens,
    }
    headers = {"Content-Type": "application/json"}
    if key and route.credential_env != "LOCAL_QWEN_BASE_URL":
        headers["Authorization"] = f"Bearer {key}"
    if route.provider == "localqwen":
        # the local llama-server's thinking-mode disable (measured:
        # thinking leaks meta-commentary into FIELD lines) — same
        # transport extra the provider spec carries
        payload["chat_template_kwargs"] = {"enable_thinking": False}

    t0 = time.time()
    http_status: Optional[int] = None
    body: Dict[str, Any] = {}
    err: Optional[BaseException] = None
    try:
        req = urllib.request.Request(
            route.transport, data=json.dumps(payload).encode("utf-8"),
            headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            http_status = resp.status
            body = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        http_status = exc.code
        err = exc
        try:
            body = json.loads(exc.read() or b"{}")
        except Exception:  # noqa: BLE001 — body is best-effort context
            body = {}
    except Exception as exc:  # noqa: BLE001 — typed below
        err = exc
    latency_ms = int((time.time() - t0) * 1000)

    # the 200-with-error-body envelope (the HF router's measured shape:
    # a stale model id answers model_not_found inside HTTP 200)
    body_err = body.get("error") if isinstance(body, dict) else None
    if isinstance(body_err, dict):
        body_err = body_err.get("message") or str(body_err)
    content = ""
    usage = None
    if isinstance(body, dict) and not body_err:
        try:
            content = ((body.get("choices") or [{}])[0]
                       .get("message", {}).get("content", "")) or ""
            usage = body.get("usage")
        except Exception:  # noqa: BLE001
            content = ""

    fields = _field_lines(content)
    ftype: str
    if err is not None:
        ftype = classify_failure(err, http_status=http_status,
                                 body_snippet=str(body_err or body)[:400])
    elif body_err:
        ftype = classify_failure(
            RuntimeError(f"error body: {str(body_err)[:300]}"),
            http_status=http_status)
    elif not content:
        ftype = "MODEL_FAILURE"
    elif not fields:
        ftype = "INVALID_RESPONSE"
    else:
        ftype = "OK"

    quota_note = "N/A (successful completion — no quota signal)"
    if body_err or err is not None:
        quota_note = str(body_err or err)[:400]
    rec.update({
        "http_status": http_status,
        "latency_ms": latency_ms,
        "token_usage": ({k: usage.get(k) for k in
                         ("prompt_tokens", "completion_tokens",
                          "total_tokens")} if isinstance(usage, dict)
                        else None),
        # tool support is a CATALOG declaration here — an honest
        # UNMEASURED, never a fabricated measurement (Art. XXV); the
        # measured fields are completion + FIELD-line protocol
        "tool_support": (
            ("CATALOG_DECLARED:" +
             ("yes" if route.catalog_supports_tools else
              ("no" if route.catalog_supports_tools is False
               else "UNDECLARED"))) + " — probe does not exercise tool "
            "calling (measurement honesty: UNMEASURED by this probe)"),
        "structured_output_support": (
            "MEASURED_FIELD_LINES"
            if fields else "MEASURED_ABSENT"),
        "response_validity": (
            "VALID_FIELD_LINES" if fields else
            ("CONTENT_NO_FIELD_LINES" if content else "NO_CONTENT")),
        "failure_class": ftype,
        "quota_credit_behavior": quota_note,
        "timestamp": utc_now(),
        "probe_success": ftype == "OK" and bool(fields),
        "field_lines_found": sorted(fields),
    })
    return rec


# ---------------------------------------------------------------------------
# Admission — probe-before-admit (the operator's rule: "probe each route
# before admitting it"; "distinguish FREE-CATALOG from
# FREE-TO-OUR-ACCOUNT")
# ---------------------------------------------------------------------------
def route_admission(route: RouteSpec, probe: Optional[Dict[str, Any]],
                    policy: Optional[str] = None
                    ) -> Tuple[bool, str]:
    """Admission decision for one route, given its probe.

    Rules (closed; every refusal carries its reason — never silent):
      1. NO PROBE -> NOT ADMITTED. A catalog row is never admission
         (FREE-CATALOG is not FREE-TO-OUR-ACCOUNT).
      2. FAILED PROBE -> NOT ADMITTED, with the typed failure class.
      3. The ACTIVE cost policy applies on top of probe success: under
         ZERO_PAID_COST only ZERO_PAID_COST_SELF_HOSTED routes are
         admitted (a probing-successful paid route stays measured-but-
         refused — fail-closed, Art. IV/VII).
    """
    from . import model_cost_policy as _cp
    p = policy or _cp.active_policy()
    if probe is None:
        return False, ("NEVER_PROBED — catalog presence is not "
                       "admission (FREE-CATALOG is not "
                       "FREE-TO-OUR-ACCOUNT)")
    if not probe.get("probe_success"):
        fc = probe.get("failure_class") or "UNKNOWN"
        return False, (f"PROBE_FAILED class={fc} — "
                       f"{str(probe.get('quota_credit_behavior')
                                     or '')[:160]}")
    if route.cost_basis not in _cp.COST_BASIS_VOCAB:
        return False, (f"cost basis {route.cost_basis!r} outside the "
                       f"closed vocabulary — ineligible")
    if route.cost_basis not in _cp.eligible_bases(p):
        return False, (f"probe succeeded but cost basis "
                       f"{route.cost_basis} is policy-ineligible under "
                       f"{p} — measured capability, refused routing "
                       f"(fail-closed)")
    return True, (f"probe succeeded and cost basis {route.cost_basis} "
                  f"eligible under {p}")


# ---------------------------------------------------------------------------
# Economic redundancy — counted ACROSS ACCOUNT DOMAINS ONLY
# ---------------------------------------------------------------------------
def economic_redundancy(admitted_routes: List[RouteSpec]
                        ) -> Dict[str, Any]:
    """Redundancy across INDEPENDENT ECONOMIC DOMAINS.

    The operator's rule: "never represent a different provider as
    redundant when it shares the same economic account." Providers are
    counted per account domain; routes within one domain are listed as
    one failure domain's members. Redundancy = distinct domains (and
    distinct providers inside them are resilience WITHIN a domain —
    model/provider-level, not account-level)."""
    by_domain: Dict[str, List[str]] = {}
    for r in admitted_routes:
        by_domain.setdefault(r.account_domain, []).append(r.provider)
    return {
        "rule": ("redundancy is counted across ACCOUNT domains — "
                 "providers sharing an economic account are ONE "
                 "failure domain (operator directive 2026-09-13)"),
        "distinct_economic_domains": len(by_domain),
        "domains": {
            dom: {"providers": sorted(set(provs)),
                  "provider_count": len(set(provs))}
            for dom, provs in sorted(by_domain.items())},
        "shared_domain_warning": (
            [f"{dom}: {sorted(set(provs))} share ONE economic account"
             for dom, provs in by_domain.items()
             if len(set(provs)) > 1] or None),
    }


# ---------------------------------------------------------------------------
# The capability matrix
# ---------------------------------------------------------------------------
def capability_matrix(route_specs: Optional[List[RouteSpec]] = None,
                      probes: Optional[Dict[str, Dict[str, Any]]] = None,
                      persist: bool = True) -> Dict[str, Any]:
    """Assemble the transport capability matrix: every route with its
    catalog claims, its measured probe, its admission decision, and the
    economic-redundancy computation over the ADMITTED set only."""
    routes = list(route_specs or ROUTE_CATALOG)
    probe_map = probes or {}
    rows: List[Dict[str, Any]] = []
    admitted: List[RouteSpec] = []
    for r in routes:
        probe = probe_map.get(r.route_id)
        ok, why = route_admission(r, probe)
        if ok:
            admitted.append(r)
        rows.append({
            "route_id": r.route_id,
            "provider": r.provider,
            "model": r.model,
            "account_domain": r.account_domain,
            "resource_class": r.resource_class,
            "catalog_claims": {
                "pricing": r.catalog_pricing,
                "declares_free": r.catalog_declares_free,
                "supports_tools": r.catalog_supports_tools,
                "supports_structured_output":
                    r.catalog_supports_structured_output,
            },
            "probe": probe,
            "admitted": ok,
            "admission_reason": why,
        })
    matrix = {
        "artifact_type": "TRANSPORT_CAPABILITY_MATRIX",
        "version": TRANSPORT_CAPABILITY_VERSION,
        "round": "R451-C1.2",
        "rule": ("admission = measured probe success AND active cost "
                 "policy eligibility; catalog claims never admit a "
                 "route (FREE-CATALOG is not FREE-TO-OUR-ACCOUNT)"),
        "routes": rows,
        "admitted_routes": [r.route_id for r in admitted],
        "economic_redundancy": economic_redundancy(admitted),
        "zero_gpu_budget": ZERO_GPU_BUDGET_NOTE,
        "built_at": utc_now(),
    }
    if persist:
        _persist_probes(probe_map)
    return matrix


def _persist_probes(probe_map: Dict[str, Dict[str, Any]]) -> None:
    """Append-only probe ledger (one jsonl line per probe, replayable
    from committed bytes — same discipline as the routing ledger)."""
    try:
        CAPABILITY_DIR.mkdir(parents=True, exist_ok=True)
        with open(MATRIX_PATH, "a") as fh:
            for route_id, probe in sorted(probe_map.items()):
                if probe:
                    fh.write(json.dumps(
                        {"route_id": route_id, **probe},
                        sort_keys=True, default=str) + "\n")
    except Exception:  # noqa: BLE001 — best-effort telemetry
        pass
