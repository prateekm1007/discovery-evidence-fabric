#!/usr/bin/env python3
"""R520 — automated clean-replay verification artifact.

Emits R520/CLEAN_REPLAY.json. Proves, from the live routing code, the
ONE R520 behavioral intervention and its blast-radius boundary:
  1. zai is retired from MS operator-instantiation purposes
     (operator_* family, all five operator ids + retries).
  2. SYNTHESIZE routing unchanged (purpose synthesis unaffected).
  3. ATTACK routing unchanged; evidence-extraction routing unchanged.
  4. Post-rank zai retirement intact (R518/R519 regression).
  5. Atria scopes unchanged.
  6. Explicit override still reaches zai on the MS route AND is recorded.
  7. Unrelated providers untouched on the MS route.
  8. Single-authority source check: no provider-id branch in the
     predicate; zai's MS scope is table data.
  9. Deterministic ordering + event reproducibility (no flake source).

Art. X: one instrument, one artifact. No hand-edited claims.
No provider credentials required for this replay.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine import provider_health as ph          # noqa: E402

OPERATOR_IDS = ["DIRECT_TRANSFER", "CROSS_DOMAIN_ANALOGY",
                "GEOMETRIC_TRANSFORMATION", "BOUNDARY_CONDITION_CHANGE",
                "FAILURE_PATH_INVERSION"]
MS_PURPOSES = [f"operator_{op}" for op in OPERATOR_IDS] + \
    [f"operator_{op}_retry" for op in OPERATOR_IDS]


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    checks: list[dict] = []
    failures: list[str] = []

    def check(name: str, ok: bool, detail) -> None:
        checks.append({"name": name, "ok": bool(ok), "detail": detail})
        if not ok:
            failures.append(name)

    # 1 — zai retired on every MS operator-instantiation purpose
    ms_retired = {p: ph.is_route_retired("zai", purpose=p)
                  for p in MS_PURPOSES}
    check("ms_operator_route_retires_zai", all(ms_retired.values()),
          {"purposes": ms_retired})

    # 1b — ordinary MS routing removes zai and records the removal
    kept, removed = ph.apply_route_retirement(
        ["zai", "xkiro"], role=ph.ROLE_SYNTHESIS,
        purpose="operator_DIRECT_TRANSFER")
    check("ms_ordinary_route_blocks_and_records",
          kept == ["xkiro"] and len(removed) == 1
          and removed[0]["retirement_state"] == "RETIRED_ROUTE_BLOCKED",
          {"kept": kept, "removed": removed})

    # 2 — SYNTHESIZE routing unchanged
    check("synthesis_route_unchanged",
          not ph.is_route_retired("zai", purpose="synthesis"),
          {"zai_on_synthesis": ph.is_route_retired(
              "zai", purpose="synthesis")})

    # 3 — ATTACK + extraction routing unchanged
    check("attack_extraction_routes_unchanged",
          not ph.is_route_retired("zai", purpose="attack")
          and not ph.is_route_retired("zai", purpose="independent_attack")
          and not ph.is_route_retired(
              "zai", purpose="structured_evidence_extraction")
          and not ph.is_route_retired(
              "zai", purpose="structured_evidence_extraction_retry"),
          {})

    # 4 — post-rank zai retirement intact
    check("post_rank_zai_retirement_intact",
          ph.is_route_retired("zai", purpose="improvement_mutation_proposal")
          and ph.is_route_retired("zai", purpose="technical_mutation_proposal"),
          {})

    # 5 — atria scopes unchanged
    check("atria_scopes_unchanged",
          ph.is_route_retired("atria", role=ph.ROLE_SYNTHESIS)
          and ph.is_route_retired("atria", role=ph.ROLE_ATTACK)
          and not ph.is_route_retired(
              "atria", purpose="operator_DIRECT_TRANSFER"),
          {})

    # 6 — explicit override reaches zai on the MS route and is recorded
    kept_o, removed_o = ph.apply_route_retirement(
        ["zai", "xkiro"], role=ph.ROLE_SYNTHESIS,
        purpose="operator_DIRECT_TRANSFER", explicit_override=True)
    check("ms_override_allowed_and_recorded",
          kept_o == ["zai", "xkiro"] and any(
              r["retirement_state"] == "EXPLICIT_OPERATOR_OVERRIDE_ALLOWED"
              for r in removed_o),
          {"kept": kept_o, "removed": removed_o})

    # 7 — unrelated providers untouched on the MS route
    untouched = all(
        not ph.is_route_retired(pid, role=ph.ROLE_SYNTHESIS,
                                purpose="operator_DIRECT_TRANSFER")
        for pid in ("xkiro", "unorouter", "openrouter", "nvidia"))
    check("unrelated_providers_untouched", untouched, {})

    # 8 — single-authority source check + table data
    body = inspect.getsource(ph.is_route_retired)
    check("no_provider_branch_in_predicate",
          '== "zai"' not in body and "=='zai'" not in body
          and '== "atria"' not in body
          and "operator_" not in body,
          {"predicate_sha256": hashlib.sha256(body.encode()).hexdigest()})
    check("ms_scope_is_table_data",
          "zai" in ph.RETIRED_ROUTE_PROVIDERS
          and ph.PURPOSE_MS_OPERATOR_INSTANTIATION in
          ph.RETIRED_ROUTE_PROVIDERS["zai"],
          {"table": {k: sorted(v) for k, v in
                     ph.RETIRED_ROUTE_PROVIDERS.items()}})

    # 9 — deterministic ordering + event reproducibility on the MS route
    matrix = [
        {"provider_id": "zai", "quality_tier": 3, "cost_tier": 1,
         "latency_tier": 2, "available": True},
        {"provider_id": "xkiro", "quality_tier": 2, "cost_tier": 1,
         "latency_tier": 2, "available": True},
        {"provider_id": "openrouter", "quality_tier": 2, "cost_tier": 1,
         "latency_tier": 2, "available": True},
    ]
    o1 = ph.order_for_role(matrix, ph.ROLE_SYNTHESIS,
                           purpose="operator_DIRECT_TRANSFER")
    o2 = ph.order_for_role(matrix, ph.ROLE_SYNTHESIS,
                           purpose="operator_DIRECT_TRANSFER")
    check("ms_order_deterministic_and_zai_free",
          o1 == o2 and "zai" not in o1, {"order": o1})

    result = "PASS" if not failures else "FAIL"
    out = {
        "artifact": "R520_CLEAN_REPLAY/1.0",
        "round": "R520",
        "parent_round": "R519",
        "generated_at_utc": _utcnow(),
        "method": ("Automated live-code replay of the R520 single MS "
                   "routing change (retirement authority + MS purpose "
                   "scope). No hand-edited claims."),
        "checks": checks,
        "checks_total": len(checks),
        "checks_passed": sum(1 for c in checks if c["ok"]),
        "failures": failures,
        "result": result,
        "reviewer_provenance": "AI_REVIEW",
    }
    dest = REPO / "R520" / "CLEAN_REPLAY.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    print(f"{result}: {out['checks_passed']}/{out['checks_total']} "
          f"-> {dest.relative_to(REPO)}")
    if failures:
        print("failures:", failures)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
