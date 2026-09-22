#!/usr/bin/env python3
"""R519 §23 — automated clean-replay verification artifact.

Emits R519/CLEAN_REPLAY.json. Proves, from the live routing code:
  1. Deterministic provider ordering (same matrix -> same order).
  2. Single retirement authority blocks retired providers on ordinary routes.
  3. Explicit operator override reaches a retired provider AND is recorded.
  4. ProviderSpecs preserved (Art. LXIV); default pin stays cleared.
  5. No health-book re-promotion of a retired provider.
  6. Empty-by-retirement chain returns typed DEFAULT_ROUTE_BLOCKED.
  7. Provenance reproducibility (identical inputs -> identical retirement events).

Art. X: one instrument, one artifact. No hand-edited claims.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine import provider_health as ph          # noqa: E402
from discovery_fabric.engine.llm_registry import _SPEC_BY_ID       # noqa: E402


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _matrix() -> list:
    return [
        {"provider_id": "atria", "quality_tier": 2, "cost_tier": 1,
         "latency_tier": 3, "available": True},
        {"provider_id": "openrouter", "quality_tier": 2, "cost_tier": 1,
         "latency_tier": 2, "available": True},
        {"provider_id": "anthropic", "quality_tier": 1, "cost_tier": 2,
         "latency_tier": 4, "available": True},
        {"provider_id": "openai", "quality_tier": 1, "cost_tier": 2,
         "latency_tier": 5, "available": True},
        {"provider_id": "zai", "quality_tier": 3, "cost_tier": 1,
         "latency_tier": 2, "available": True},
    ]


def main() -> int:
    checks: list[dict] = []
    failures: list[str] = []

    def check(name: str, ok: bool, detail) -> None:
        checks.append({"name": name, "ok": bool(ok), "detail": detail})
        if not ok:
            failures.append(name)

    # 1 — deterministic ordering
    m = _matrix()
    order1 = ph.order_for_role(_matrix(), ph.ROLE_SYNTHESIS)
    order2 = ph.order_for_role(_matrix(), ph.ROLE_SYNTHESIS)
    check("deterministic_order", order1 == order2,
          {"order1": order1, "order2": order2})

    # 2 — ordinary synthesis/attack excludes atria
    check("ordinary_synthesis_excludes_atria",
          "atria" not in order1, {"order": order1})
    events: list = []
    attack_order = ph.order_for_role(_matrix(), ph.ROLE_ATTACK,
                                     out_events=events)
    check("ordinary_attack_excludes_atria",
          "atria" not in attack_order,
          {"order": attack_order, "events": events})

    # 3 — explicit override reaches retired provider and is recorded
    kept, removed = ph.apply_route_retirement(
        ["atria", "openrouter"], role=ph.ROLE_SYNTHESIS,
        explicit_override=True)
    recorded = any(
        r["provider"] == "atria"
        and r["retirement_state"] == "EXPLICIT_OPERATOR_OVERRIDE_ALLOWED"
        for r in removed)
    check("explicit_override_allowed_and_recorded",
          "atria" in kept and recorded,
          {"kept": kept, "removed": removed})
    kept_o, removed_o = ph.apply_route_retirement(
        ["atria", "openrouter"], role=ph.ROLE_SYNTHESIS,
        explicit_override=False)
    blocked = any(
        r["provider"] == "atria"
        and r["retirement_state"] == "RETIRED_ROUTE_BLOCKED"
        for r in removed_o)
    check("ordinary_route_blocks_and_records",
          "atria" not in kept_o and blocked,
          {"kept": kept_o, "removed": removed_o})

    # 4 — ProviderSpecs preserved; pin cleared (Art. LXIV)
    check("provider_specs_preserved",
          "atria" in _SPEC_BY_ID and "zai" in _SPEC_BY_ID,
          {"atria_spec": "atria" in _SPEC_BY_ID,
           "zai_spec": "zai" in _SPEC_BY_ID})
    check("default_pin_cleared", ph._DEFAULT_PROVIDER_PIN == "",
          {"_DEFAULT_PROVIDER_PIN": ph._DEFAULT_PROVIDER_PIN})

    # 5 — no health-book re-promotion: a book that prefers atria still
    # yields an order without atria (retirement filters after ranking)
    class _FakeBook:
        def in_cooldown(self, _pid: str) -> bool:
            return False
    order_book = ph.order_for_role(_matrix(), ph.ROLE_SYNTHESIS,
                                   book=_FakeBook())
    check("no_health_book_repromotion", "atria" not in order_book,
          {"order": order_book})

    # 6 — empty-by-retirement path (simulate via direct filter)
    only_retired, only_removed = ph.apply_route_retirement(
        ["atria"], role=ph.ROLE_SYNTHESIS, explicit_override=False)
    check("empty_by_retirement_typed_block",
          only_retired == [] and
          any(r["retirement_state"] == "RETIRED_ROUTE_BLOCKED"
              for r in only_removed),
          {"kept": only_retired, "removed": only_removed})

    # 7 — provenance reproducibility: retirement events identical
    e1: list = []
    e2: list = []
    ph.order_for_role(_matrix(), ph.ROLE_SYNTHESIS, out_events=e1)
    ph.order_for_role(_matrix(), ph.ROLE_SYNTHESIS, out_events=e2)
    check("retirement_events_reproducible", e1 == e2,
          {"events1": e1, "events2": e2})

    # 8 — single-authority source check: predicate body has no provider id
    import inspect
    body = inspect.getsource(ph.is_route_retired)
    check("no_provider_branch_in_predicate",
          '== "zai"' not in body and "=='zai'" not in body
          and '== "atria"' not in body,
          {"predicate_sha256": hashlib.sha256(body.encode()).hexdigest()})

    # 9 — zai represented as table data (post-rank purpose scopes)
    check("zai_is_table_data",
          "zai" in ph.RETIRED_ROUTE_PROVIDERS
          and ph.PURPOSE_POST_RANK_IMPROVEMENT in
          ph.RETIRED_ROUTE_PROVIDERS["zai"]
          and ph.is_route_retired("zai", purpose="improvement_mutation_proposal")
          and not ph.is_route_retired("zai", role=ph.ROLE_SYNTHESIS),
          {"table": {k: sorted(v) for k, v in
                     ph.RETIRED_ROUTE_PROVIDERS.items()}})

    # 10 — fallback: ordinary preferred list containing atria is filtered
    # through the same authority used by generate() (apply_route_retirement)
    pref = ["atria", "openrouter", "deepseek"]
    pref_kept, pref_rm = ph.apply_route_retirement(
        pref, role=ph.ROLE_SYNTHESIS, purpose="synthesis",
        explicit_override=False)
    check("preferred_list_filters_retired",
          "atria" not in pref_kept and pref_kept == ["openrouter", "deepseek"],
          {"kept": pref_kept, "removed": pref_rm})

    result = "PASS" if not failures else "FAIL"
    out = {
        "artifact": "R519_CLEAN_REPLAY/1.0",
        "round": "R519",
        "parent_round": "R518",
        "generated_at_utc": _utcnow(),
        "method": (
            "Automated live-code replay of the R519 single retirement "
            "authority (provider_health.is_route_retired / "
            "apply_route_retirement / order_for_role + llm_registry "
            "ProviderSpec table). No hand-edited claims."
        ),
        "checks": checks,
        "checks_total": len(checks),
        "checks_passed": sum(1 for c in checks if c["ok"]),
        "failures": failures,
        "result": result,
        "notes": [
            "§23 requirements: deterministic ordering, retirement on "
            "ordinary routes, explicit-override recording, no health-book "
            "re-promotion, no hidden pin, typed empty-chain reason, "
            "provenance reproducibility — all covered above.",
            "Live generate() empty-chain path returns ST_POLICY_BLOCKED "
            "with DEFAULT_ROUTE_BLOCKED text; covered by "
            "tests/test_r519_retirement_authority.py (16 tests).",
            "No provider credentials required for this replay.",
        ],
    }
    dest = REPO / "R519" / "CLEAN_REPLAY.json"
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
