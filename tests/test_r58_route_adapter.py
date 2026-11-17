"""tests/test_r58_route_adapter.py — the R58 lane's CI pins (claim
c-0079): the typed route adapter, the evaluator v1.1.0 amendment, and
the pre-registered winner-selection rule.

Zero external network: the transport test runs against a loopback
http server (localhost only — no packet leaves the machine); every
other test is pure-function.
"""
from __future__ import annotations

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from discovery_fabric.engine import route_adapter as ra  # noqa: E402
from r53_p2_ablation_criteria import evaluate  # noqa: E402
from r58_p2_ablation_driver import (  # noqa: E402
    load_dev_problems, load_population, select_winner,
    challenger_prob)


# ---------------------------------------------------------------- registry
def test_route_registry_typed_facts():
    reg = ra.ROUTE_REGISTRY
    assert reg["registered"]["model"] == "glm-4-plus"
    assert "R36" in reg["registered"]["provenance"]
    names = {a["name"] for a in reg["alternates"]}
    assert names == {"xkiro", "agnes"}
    for a in reg["alternates"]:
        assert a["vault_key_name"] in ("XKIRO_API_KEY", "AGNES_API_KEY")
        assert a["transport_facts"], "every alternate carries its facts"
    xk = [a for a in reg["alternates"] if a["name"] == "xkiro"][0]
    assert any("User-Agent" in f for f in xk["transport_facts"])
    ag = [a for a in reg["alternates"] if a["name"] == "agnes"][0]
    assert any("REASONING_HEADROOM" in f or "reasoning" in f
               for f in ag["transport_facts"])
    dead = {d["name"] for d in reg["dead"]}
    assert dead == {"deepai", "nvidia"}


def test_require_registered_model_guard():
    ra.require_registered_model("glm-4-plus")  # the registered id
    try:
        ra.require_registered_model("mistralai/ministral-14b")
        raise AssertionError("silent model swap must be refused")
    except ra.RouteRefused as e:
        assert e.kind == "unregistered_route"


# ------------------------------------------------------------------ vault
def test_resolve_vault_key_typed_absence(tmp_path):
    # a temp vault: resolution is by NAME; absence is typed None
    ra.VAULT = tmp_path / "vault"
    ra.VAULT.write_text("XKIRO_API_KEY=test-key-value\n"
                        "# comment\nAGNES_API_KEY=another\n")
    assert ra.resolve_vault_key("XKIRO_API_KEY") == "test-key-value"
    assert ra.resolve_vault_key("AGNES_API_KEY") == "another"
    assert ra.resolve_vault_key("NVIDIA_API_KEY") is None
    ra.VAULT = tmp_path / "absent"
    assert ra.resolve_vault_key("XKIRO_API_KEY") is None


# -------------------------------------------------------------- transports
def test_post_chat_headers_and_typing_loopback():
    """Loopback transport test (zero external network): the browser UA
    (the Cloudflare-1010 fact) and the Bearer auth actually reach the
    wire; an empty completion is a typed refusal carrying the agnes
    reasoning-budget hint."""
    seen = {}

    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            seen["path"] = self.path
            seen["ua"] = self.headers.get("User-Agent")
            seen["auth"] = self.headers.get("Authorization")
            n = int(self.headers.get("Content-Length") or 0)
            seen["body"] = json.loads(self.rfile.read(n))
            if seen["body"]["model"] == "empty-model":
                content, finish = "", "length"
            else:
                content, finish = "ok", "stop"
            resp = json.dumps({"model": seen["body"]["model"],
                               "choices": [{"finish_reason": finish,
                                            "message": {"role":
                                                        "assistant",
                                                        "content":
                                                        content}}],
                               "usage": {}}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(resp)))
            self.end_headers()
            self.wfile.write(resp)

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", 0), H)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        url = f"http://127.0.0.1:{srv.server_port}/v1"
        out = ra._post_chat(url, "k-test", [{"role": "user",
                                             "content": "hi"}],
                            "m-1", 8, 5.0, ra.BROWSER_UA, "loopback")
        assert out["content"] == "ok"
        assert seen["path"] == "/v1/chat/completions"
        assert seen["ua"] == ra.BROWSER_UA
        assert seen["ua"] != "Python-urllib/3.12"  # the 1010 ban
        assert seen["auth"] == "Bearer k-test"
        # empty completion -> typed refusal, never silent
        try:
            ra._post_chat(url, "k-test", [{"role": "user",
                                           "content": "hi"}],
                          "empty-model", 8, 5.0, ra.BROWSER_UA,
                          "loopback")
            raise AssertionError("empty completion must be refused")
        except ra.RouteRefused as e:
            assert e.kind == "transport"
            assert "REASONING_HEADROOM" in e.detail
        # missing key -> typed missing_key (never a bare call)
        try:
            ra._post_chat(url, "", [{"role": "user",
                                     "content": "hi"}],
                          "m-1", 8, 5.0, ra.BROWSER_UA, "loopback")
            raise AssertionError("missing key must be refused")
        except ra.RouteRefused as e:
            assert e.kind == "missing_key"
    finally:
        srv.shutdown()
        srv.server_close()


def test_agnes_budget_sizing():
    # the measured c-0078 fact: max_tokens must exceed the visible
    # target by the reasoning headroom
    assert ra.REASONING_HEADROOM >= 256
    # (the sizing itself is applied inside agnes_chat; the arithmetic
    # pin lives here so a silent headroom removal fails CI)


# --------------------------------------------- evaluator v1.1.0 amendment
def _ev(cand, base):
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        c = Path(td) / "c.json"
        b = Path(td) / "b.json"
        c.write_text(json.dumps(cand))
        b.write_text(json.dumps(base))
        return evaluate(c, b)


def test_evaluator_deferred_verdict_on_unmeasurable():
    out = _ev({"p1": {"mean_score": None,
                      "measure_classes": ["configuration"],
                      "allowed_row_outside": 0}},
              {"p1": {"mean_score": None,
                      "measure_classes": ["x"],
                      "allowed_row_outside": 0}})
    assert out["record"] == "R53_P2_ABLATION_CRITERIA/1.1.0"
    assert out["criteria"][0]["met"] and out["criteria"][1]["met"]
    assert out["criteria"][2]["value"] == "UNMEASURABLE"
    # the R58 amendment: NEVER a DELETE on no measurement
    assert out["verdict"] == ("ADOPTION_DEFERRED_"
                              "CRITERION_3_UNMEASURABLE")


def test_evaluator_measured_paths_unchanged():
    base = {"p1": {"mean_score": 3.0, "measure_classes": ["x"],
                   "allowed_row_outside": 0}}
    assert _ev({"p1": {"mean_score": 3.2,
                       "measure_classes": ["geometry"],
                       "allowed_row_outside": 0}}, base)[
        "verdict"] == "ADOPT"
    assert _ev({"p1": {"mean_score": 2.8,
                       "measure_classes": ["geometry"],
                       "allowed_row_outside": 0}}, base)[
        "verdict"] == "DELETE"
    assert _ev({"p1": {"mean_score": 3.2,
                       "measure_classes": ["duty_cycle"],
                       "allowed_row_outside": 0}}, base)[
        "verdict"].startswith("INCOMPLETE")
    assert _ev({"p1": {"mean_score": 3.2,
                       "measure_classes": ["geometry"],
                       "allowed_row_outside": 2}}, base)[
        "verdict"].startswith("INCOMPLETE")


def test_evaluator_refuses_no_overlap():
    out = _ev({"p1": {"mean_score": None,
                      "measure_classes": ["geometry"],
                      "allowed_row_outside": 0}},
              {"p2": {"mean_score": None,
                      "measure_classes": ["x"],
                      "allowed_row_outside": 0}})
    assert out["verdict"] == "EVALUATION_REFUSED"


# ------------------------------------------------- winner selection rule
def test_winner_rule_deterministic():
    plans = [
        {"operator_id": "A", "measure_class": "duty_cycle",
         "principle_id": "P1", "signals_used": [],
         "contract_satisfied": True},
        {"operator_id": "B", "measure_class": "geometry",
         "principle_id": "P2", "signals_used": [],
         "contract_satisfied": True},
        {"operator_id": "C", "measure_class": "boundary",
         "principle_id": "P3", "signals_used": [],
         "contract_satisfied": False},
    ]
    w, rule = select_winner(list(plans))
    assert w["operator_id"] == "B" and rule == "non_schedule_first"
    # all-duty_cycle -> first satisfied
    plans[1]["measure_class"] = "duty_cycle"
    w, rule = select_winner(list(plans))
    assert w["operator_id"] == "A" and rule == "schedule_fallback"
    # none satisfied -> first plan, typed
    for p in plans:
        p["contract_satisfied"] = False
    w, rule = select_winner(list(plans))
    assert w["operator_id"] == "A" and rule == "none_satisfied_fallback"


def test_population_winner_drycheck():
    problems = load_dev_problems()
    pop = load_population()
    assert len(problems) == 36
    rules = {}
    for p in problems:
        w, rule = select_winner(pop[p["problem_id"]]["plans"])
        rules[rule] = rules.get(rule, 0) + 1
        cp = challenger_prob(p, w, rule)
        assert cp["typed_plan"]["measure_class"] == w["measure_class"]
        assert "typed_plan" not in p  # no mutation of the baseline dict
    assert rules.get("non_schedule_first") == 36
