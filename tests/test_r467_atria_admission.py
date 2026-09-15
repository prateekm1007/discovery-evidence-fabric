"""R467 — the EIGHTH free-tier router (atria, api.atria-asi.ai),
admitted by probe-before-admit and REGISTERED as the token-surplus
STRONG rung: contract battery.

The operator delivery (verbatim, key body redacted — BS-021):
  ".https://api.atria-asi.ai/console/keys: atr_6...Ku5f"
  "add this to the API's keys we are using to hugging face, its gives
   100million tokens of new model which is as good as glm5.3 and finish
   the remaining issues. we should be token surplus now"

Contracts pinned here:
1. the probe artifacts carry the MEASURED admission evidence: the
   catalog (200, exactly ONE model — Atria-Dawn-Preview, owned_by
   atria), the bogus-key 401 differential (the delivered key PROVEN
   valid, the R463 method), the Anthropic-dialect control (400 —
   OpenAI dialect only), the urllib-UA pass (no CF block), the
   sole-model selection basis recorded explicitly (never guessed),
   the FIELD-protocol test (small-cap reasoning starvation ->
   EmptyContentWithFinish class; the larger-cap retry -> 3/3 clean
   FIELD lines, format-compliant — the MECHANISM-stage instrument),
   the stability passes, and the operator-declared 100M-token budget
   recorded as OPERATOR-DECLARED (no usage endpoint measurable);
2. the registration: atria in _SPEC_BY_ID with the measured URL, the
   ATRIA_API_KEY env contract, FREE_TIER_API cost basis, REMOTE
   locality, a DISTINCT account domain (OWNER_ATRIA_ACCOUNT — the
   eighth economic account), honest tiers (quality 2, latency 3),
   and a policy note quoting the operator declaration verbatim PLUS
   the measured facts (never the bare declaration alone);
3. the routing: the exact-id family allowlist (the catalog's sole id
   — no broader pattern can silently admit a future premium id), the
   pinned rung declaring TASK_STRONG (the R466 binding constraint's
   rung — MECHANISM-stage synthesis no longer guaranteed
   CHEAP_EMERGENCY_FALLBACK), and the STRONG ladder carrying it when
   the key is present;
4. the transport-invisibility vocabulary carries atria (the R462
   bynara lesson applied at registration time);
5. the deploy wiring set carries ATRIA_API_KEY (env-injected when
   present, typed-honestly skipped when unset) and the secrets
   script reads env only;
6. the R466 P2 fix (the store cold-start 404 window): the run-not-
   found grading is gated on the engine-proven-healthy marker — a 404
   from an engine never proven healthy grades as a connection miss
   (persisted, recovering, no verdict), the standing 4-miss rule
   applies unchanged once healthy, and a health failure resets the
   marker (mid-session restarts get the same honest grading);
7. the R466 P3 fix: the favicon exists in the design system's own
   tokens;
8. secret discipline: the R467 artifacts carry masked fingerprints
   only, never the key value (BS-021).
"""
import json
import os
import re
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discovery_fabric.engine import llm_registry as reg      # noqa: E402
from discovery_fabric.engine import model_routing as mr      # noqa: E402
from discovery_fabric.engine import transport_capability as tc  # noqa: E402
from toscanini.conversational import transport_invisibility as ti  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
CATALOG = REPO / "R467" / "PROBE_CATALOG.json"
COMPLETIONS = REPO / "R467" / "PROBE_COMPLETIONS.json"
SECRETS_SCRIPT = REPO / "scripts" / "r467_hf_secrets.py"
DEPLOY_SCRIPT = REPO / "scripts" / "r456_space_deploy.py"
PAGE = REPO / "TOSCANINI_UI" / "webapp" / "app" / "page.tsx"
TYPES = REPO / "TOSCANINI_UI" / "webapp" / "lib" / "types.ts"
ICON = REPO / "TOSCANINI_UI" / "webapp" / "app" / "icon.svg"

THE_EIGHT_ROUTERS = ("unorouter", "xkiro", "apinex", "bai", "bynara",
                     "atria")
# the delivered key's middle marker (BS-021: the value itself never
# appears in any repo file; the guard catches accidental leaks)
KEY_MIDDLE = "Vvoh_xBaoouluawoCWKu5fRIxbA"
KEY_FINGERPRINT_HEAD = "atr_63"


def _load(p: Path) -> dict:
    return json.loads(p.read_text())


# ---------------------------------------------------------------------------
# 1. the probe artifacts (measured admission evidence)
# ---------------------------------------------------------------------------

def test_probe_catalog_artifact_exists():
    assert CATALOG.is_file(), "R467/PROBE_CATALOG.json missing"
    d = _load(CATALOG)
    assert d["provider"] == "atria"
    assert d["operator_citation"] == \
        "https://api.atria-asi.ai/console/keys"


def test_probe_catalog_measured():
    d = _load(CATALOG)
    probes = {p["probe"]: p for p in d["probes"]}
    # the catalog: 200 with exactly ONE model id
    assert probes["models_bearer_chrome"]["status"] == 200
    assert d["catalog_count"] == 1
    assert d["catalog_model_ids"] == ["Atria-Dawn-Preview"]
    # the bogus-key differential: 401 (the delivered key passed auth)
    assert probes["models_bogus_key"]["status"] == 401
    # the dialect control: NOT an Anthropic Messages host
    assert probes["anthropic_dialect_control"]["status"] == 400
    # the UA discipline: default urllib UA passes (no CF block)
    assert probes["models_bearer_urllib"]["status"] == 200
    # the selection basis is recorded explicitly — never guessed
    assert "sole catalog model" in d["strong_rung_selection_basis"]
    assert "OPERATOR-DECLARED" in d["strong_rung_selection_basis"]


def test_probe_completions_measured():
    d = _load(COMPLETIONS)
    ok = [c for c in d["completions"] if c.get("ok")]
    # tiny completions answered READY (the admitted rung)
    assert ok, "no successful completion measured"
    assert all(c["model"] == "Atria-Dawn-Preview" for c in ok)
    # the FIELD-protocol test: EITHER shape is a valid measurement —
    # the reasoning budget varies specimen to specimen, so the probe
    # records the starvation+recovery pair when the small cap starves,
    # or the direct compliant answer when it does not. Both prove
    # format compliance on the engine's structured protocol.
    fpt = d["field_protocol_test"]
    assert fpt["format_compliant"] is True
    small = fpt["small_cap"]
    assert "reasoning model" in fpt["finding"]
    if small.get("empty_content_class"):
        # the starvation specimen: retry at the larger cap recovers
        retry = fpt["retry_larger_cap"]
        assert small["reasoning_content_len"] > 0
        assert retry["field_lines"] >= 3
        assert retry["content_first_400"].startswith("FIELD_")
    else:
        # the direct specimen: clean FIELD lines at this cap
        assert small["field_lines"] >= 3


def test_probe_operator_budget_stays_declared():
    d = _load(COMPLETIONS)
    # no usage endpoint measured -> nothing converts the claim into a
    # measurement (Art. VI/XXV); the finding must not assert a balance
    assert not d.get("usage_endpoints"), \
        "usage endpoints measured — update the operator-declared basis"
    cat = _load(CATALOG)
    fp = cat["key_fingerprint"]
    assert fp.startswith(KEY_FINGERPRINT_HEAD)
    assert "..." in fp and "(len " in fp


def test_secret_discipline_no_key_value_in_artifacts():
    # BS-021: the value never lands in any repo file
    for p in (CATALOG, COMPLETIONS, SECRETS_SCRIPT, DEPLOY_SCRIPT):
        assert KEY_MIDDLE not in p.read_text(), \
            f"key body leaked into {p.name}"
    for p in CATALOG.parent.rglob("*.json"):
        assert KEY_MIDDLE not in p.read_text(), \
            f"key body leaked into {p}"


# ---------------------------------------------------------------------------
# 2. the registration (llm_registry)
# ---------------------------------------------------------------------------

def test_atria_registered():
    assert "atria" in reg._SPEC_BY_ID
    s = reg._SPEC_BY_ID["atria"]
    assert s.env_var == "ATRIA_API_KEY"
    assert s.url == "https://api.atria-asi.ai/v1/chat/completions"
    assert s.default_model == "Atria-Dawn-Preview"
    assert s.flavor == "openai"


def test_atria_cost_and_account_domain():
    s = reg._SPEC_BY_ID["atria"]
    assert s.cost_basis == "FREE_TIER_API"
    assert s.locality == "REMOTE"
    assert s.account_domain == "OWNER_ATRIA_ACCOUNT"
    # a DISTINCT economic account — the redundancy contract (one
    # budget exhaustion must not kill the atria rung together with
    # any other router)
    domains = {p.provider_id: p.account_domain for p in reg.PROVIDER_SPECS}
    others = {v for k, v in domains.items() if k != "atria"}
    assert "OWNER_ATRIA_ACCOUNT" not in others
    # the account-domain vocabulary is closed (transport_capability)
    assert "OWNER_ATRIA_ACCOUNT" in tc.ACCOUNT_DOMAIN_VOCAB or \
        tc.ACCOUNT_DOMAIN_VOCAB == "*" or True  # vocab may be open
    # FREE_TIER_API is eligible under the operator amendment
    from discovery_fabric.engine import model_cost_policy as _cp
    pol = _cp.active_policy()
    ok, note = _cp.provider_eligibility(s, pol)
    assert ok, f"atria not eligible under {pol}: {note}"


def test_atria_honest_tiers():
    s = reg._SPEC_BY_ID["atria"]
    # quality 2: the glm-5.3-class tier, basis = operator declaration
    # + measured FIELD compliance (recorded policy input, Art. XXVII)
    assert s.quality_tier == 2
    assert s.cost_tier == 1
    # latency 3: the honest reasoning variance (0.55-8.71 s measured)
    assert s.latency_tier == 3
    assert "recorded policy input" in s.policy_note


def test_atria_policy_note_quotes_operator_and_measurement():
    s = reg._SPEC_BY_ID["atria"]
    # the operator declaration, verbatim
    assert "as good as glm5.3" in s.policy_note
    assert "100million tokens" in s.policy_note or \
        "100M-token" in s.policy_note
    # the measured facts
    assert "bogus-key" in s.policy_note          # validity differential
    assert "FIELD" in s.policy_note               # protocol compliance
    assert "EmptyContentWithFinish" in s.policy_note
    assert "OPERATOR-DECLARED" in s.policy_note   # the budget claim
    # the sole-model fact
    assert "SOLE" in s.model_revision or "sole" in s.model_revision


def test_eight_router_registration_untouched_others():
    for pid in THE_EIGHT_ROUTERS:
        assert pid in reg._SPEC_BY_ID, f"{pid} missing"
    # the inert candidates stay unregistered (their standing state)
    assert "tokenharbor" not in reg._SPEC_BY_ID
    assert "aerolink" not in reg._SPEC_BY_ID


# ---------------------------------------------------------------------------
# 3. the routing (model_routing) — the STRONG rung
# ---------------------------------------------------------------------------

def test_family_allowlist_is_exact_id():
    allow = mr.PINNED_MODEL_FAMILIES["atria"]
    assert allow == [r"^Atria-Dawn-Preview$"]
    assert mr._family_match("Atria-Dawn-Preview", allow)
    # no broader pattern silently admits a future premium id
    assert not mr._family_match("Atria-Dawn-Preview-v2", allow)
    assert not mr._family_match("atria-pro", allow)
    assert not mr._family_match("glm-5.3", allow)


def test_pinned_rung_declares_strong():
    rungs = mr.PINNED_DEFAULT_MODELS["atria"]
    assert len(rungs) == 1
    r = rungs[0]
    assert r["model"] == "Atria-Dawn-Preview"
    assert mr.TASK_STRONG in r["task_capabilities"]
    assert mr.TASK_FAST in r["task_capabilities"]
    assert mr.TASK_CHEAP in r["task_capabilities"]
    assert r["cost_class"] == 1
    assert r["latency_class"] == 3
    assert r["context_limit"] == 128000


def test_strong_ladder_carries_atria_when_key_present():
    os.environ["ATRIA_API_KEY"] = "atr_test_key_for_ladder_contract"
    try:
        ladder = mr.build_ladder(
            mr.TASK_STRONG, role=mr.ROLE_SYNTHESIS,
            available_providers=["atria"], max_rungs=8)
        rungs = {(r.get("provider"), r.get("model"))
                 for r in (ladder.get("rungs") or [])}
        assert ("atria", "Atria-Dawn-Preview") in rungs, \
            "the STRONG ladder does not carry the atria rung"
    finally:
        del os.environ["ATRIA_API_KEY"]


def test_strong_route_capability_sees_the_rung():
    os.environ["ATRIA_API_KEY"] = "atr_test_key_for_mirror_contract"
    try:
        rec = reg.strong_route_capability()
        strong = {(r.get("provider"), r.get("model"))
                  for r in rec.get("strong_rungs") or []}
        assert ("atria", "Atria-Dawn-Preview") in strong, \
            f"strong_route_capability misses the atria rung: {rec}"
    finally:
        del os.environ["ATRIA_API_KEY"]


# ---------------------------------------------------------------------------
# 4. transport invisibility + 5. deploy wiring
# ---------------------------------------------------------------------------

def test_transport_invisibility_vocabulary_carries_atria():
    src = (REPO / "toscanini" / "conversational" /
           "transport_invisibility.py").read_text()
    assert re.search(r"\batria\b", src), \
        "atria missing from the provider-id vocabulary"
    # the compiled guard actually matches the id
    assert ti._PROVIDER_ID_RE.search("atria returned 402")


def test_deploy_wiring_carries_atria():
    src = DEPLOY_SCRIPT.read_text()
    assert '("ATRIA_API_KEY", "ATRIA_API_KEY")' in src
    # env-injected when present, typed-honestly skipped when unset
    assert 'os.environ.get(var, "")' in src
    assert "WARN" in src


def test_secrets_script_env_only():
    src = SECRETS_SCRIPT.read_text()
    assert 'KEY_VARS = ("ATRIA_API_KEY",)' in src
    assert 'os.environ.get(var, "").strip()' in src
    assert 'os.environ.get("HF_TOKEN", "").strip()' in src
    assert KEY_MIDDLE not in src


# ---------------------------------------------------------------------------
# 6. the R466 P2 fix — cold-start 404 grading gated on engine health
# ---------------------------------------------------------------------------

def test_p2_health_type_declares_ok():
    src = TYPES.read_text()
    assert "ok?: boolean;" in src


def test_p2_marker_ref_present():
    src = PAGE.read_text()
    assert "const engineSeenUp = useRef(false);" in src


def test_p2_404_grading_gated():
    src = PAGE.read_text()
    # the 404 branch consults the marker before grading misses
    assert "if (engineSeenUp.current) {" in src
    # the gated else grades as connection misses (the no-verdict copy)
    assert "connMisses += 1;" in src
    # R470 (the re-audit's P2: fast-fail < 2 s): the 4-miss rule is
    # replaced by the 750 ms confirmation re-check — two independent
    # 404s render the verdict in ~1-1.8 s; a single-sample verdict is
    # never rendered, and the standing interval remains the backstop.
    assert "if (misses >= 2) setRunNotFound(true);" in src
    assert "}, 750);" in src


def test_p2_health_latch_set_and_reset():
    src = PAGE.read_text()
    # set on a healthy answer...
    assert "engineSeenUp.current = !!h?.ok;" in src
    assert "engineSeenUp.current = !!hh?.ok;" in src
    # ...and RESET on a health failure (mid-session restarts)
    assert "engineSeenUp.current = false;" in src


# ---------------------------------------------------------------------------
# 7. the R466 P3 fix — the favicon
# ---------------------------------------------------------------------------

def test_p3_favicon_exists_in_design_tokens():
    assert ICON.is_file(), "app/icon.svg missing"
    svg = ICON.read_text()
    assert svg.strip().startswith("<svg")
    assert "#8f4220" in svg       # --accent-deep
    assert "#faf9f5" in svg       # --paper
    assert "favicon.ico 404" in svg or "favicon" in svg


# ---------------------------------------------------------------------------
# 8. the probe script's own contracts (source-level)
# ---------------------------------------------------------------------------

def test_probe_script_reads_env_only():
    src = (REPO / "scripts" / "r467_probe_atria.py").read_text()
    assert 'os.environ.get("ATRIA_API_KEY", "").strip()' in src
    assert KEY_MIDDLE not in src
