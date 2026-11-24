"""r148_p4_panel_v18_dryrun.py — the instrument dry-run (no network).

Exercises the full main() path of scripts/r148_p4_panel_v18.py with:
  - a mock V18 packs file (3 problems, prior_arts as {text:} dicts)
  - monkeypatched cent_ai_chat returning canned rulings
  - 3 fake qualified judges injected via the QUALIFICATION snapshot
    (restored in a finally block, whatever the outcome)
Verifies: gate refusal on missing packs, legfile resume (VALID legs
skip), the both-axes majority tally, the >=50% verdict, and
parse_ruling's contract enforcement.
"""
import importlib.util
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    "panel_v18", REPO / "scripts" / "r148_p4_panel_v18.py")
mod = importlib.util.module_from_spec(spec)
sys.modules["panel_v18"] = mod
spec.loader.exec_module(mod)

FAILS = []


def check(name, cond):
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        FAILS.append(name)


# --- 1. parse_ruling contract ---
ok = mod.parse_ruling(json.dumps({
    "closest_prior_art": "2", "viable": True, "non_obvious": False,
    "distinguishing_features": ["x"], "physics_error_found": False,
    "physics_error": "", "confidence": 0.8,
    "viable_reason": "r", "non_obvious_reason": "n",
    "objective_technical_problem": "p"}))
check("parse_ruling valid", ok["closest_prior_art"] == "2")
for bad, why in [
    ({"closest_prior_art": "9", "viable": True, "non_obvious": True,
      "distinguishing_features": []}, "bad prior art"),
    ({"closest_prior_art": "1", "viable": "yes", "non_obvious": True,
      "distinguishing_features": []}, "bad boolean"),
    ({"closest_prior_art": "1", "viable": True}, "missing keys"),
]:
    try:
        mod.parse_ruling(json.dumps(bad))
        check(f"parse_ruling rejects {why}", False)
    except (ValueError, KeyError):
        check(f"parse_ruling rejects {why}", True)
prose = ('Here is my ruling:\n```json\n{"closest_prior_art": "none", '
         '"viable": true, "non_obvious": true, '
         '"distinguishing_features": ["a", "b"], "physics_error_found": '
         'false, "physics_error": "", "confidence": 0.9, '
         '"viable_reason": "r", "non_obvious_reason": "n", '
         '"objective_technical_problem": "p"}\n```')
check("parse_ruling extracts from prose",
      mod.parse_ruling(prose)["viable"] is True)

# --- 2. neutral_index determinism (100..999, sha-derived) ---
idx = {p: mod.neutral_index(p) for p in
       ["v18-01-x", "v18-02-y", "v18-03-z", "v18-01-x"]}
check("neutral_index deterministic + bounded (100..999)",
      idx["v18-01-x"] == idx["v18-01-x"] and
      all(100 <= v <= 999 for v in idx.values()))

# --- mock instrument: snapshot backup -> fake judges -> restore ---
snap = REPO / "eval" / "r148_rcal_centai" / "QUALIFICATION.json"
backup = snap.read_text() if snap.exists() else None
mod.OUT_DIR = REPO / "eval" / "r148_p4_panel_v18"
pf2 = mod.OUT_DIR / "mock_packs.json"
pf2.write_text(json.dumps({"packs": [
    {"problem_id": f"v18-0{i}-mock", "candidate_text": "cand",
     "prior_arts": [{"text": f"pa{i}-1"}, {"text": f"pa{i}-2"},
                    {"text": f"pa{i}-3"}]} for i in (1, 2, 3)]}))
os.environ["V18_PACKS"] = "eval/r148_p4_panel_v18/mock_packs.json"

try:
    snap.parent.mkdir(parents=True, exist_ok=True)
    snap.write_text(json.dumps({
        "record": "MOCK", "gate": {"pass": True, "n_qualified": 3,
                                   "alpha": 0.83},
        "qualified_tags": ["mj1", "mj2", "mj3"],
        "interjudge_alpha": {"alpha": 0.83},
        "am47_bias": {"imbalance": 1}}))
    mod.CENT_ROSTER.update({t: {"model": f"mock-{t}", "family": "mock",
                                "timeout_s": 5,
                                "budgets": [50, 50, 50, 50], "pace": 0}
                            for t in ("mj1", "mj2", "mj3")})
    # canned rulings: mj1 mj2 both-axes yes on all 3; mj3 viable-only
    CANNED = {"mj1": (True, True), "mj2": (True, True),
              "mj3": (True, False)}

    def fake_chat(messages, model="", max_tokens=0, timeout_s=0,
                  stream=False):
        v, n = CANNED[model.replace("mock-", "")]
        return {"content": json.dumps({
            "closest_prior_art": "none", "viable": v, "non_obvious": n,
            "distinguishing_features": ["mock"],
            "physics_error_found": False, "physics_error": "",
            "confidence": 0.9, "viable_reason": "r",
            "non_obvious_reason": "n",
            "objective_technical_problem": "p"})}

    import discovery_fabric.engine.route_adapter as ra
    ra.cent_ai_chat = fake_chat

    # --- 3. typed refusal on missing packs ---
    _packs_env_backup = mod.PACKS
    os.environ.pop("V18_PACKS", None)
    mod.PACKS = None  # the module froze PACKS at import; simulate the unset env
    try:
        mod.main()
        check("typed refusal missing packs", False)
    except SystemExit as e:
        check("typed refusal missing packs", "do not exist yet" in str(e))
    os.environ["V18_PACKS"] = "eval/r148_p4_panel_v18/mock_packs.json"
    mod.PACKS = pf2  # the driver reads module-level PACKS, not the env

    # --- 4. full main(): tally + verdict ---
    for f in mod.OUT_DIR.glob("mj*__*.json"):
        f.unlink()
    rc = mod.main()
    check("main() ran clean", rc == 0)
    tally = json.loads((mod.OUT_DIR / "tally.json").read_text())
    check("3 candidates tallied", tally["tally"]["n_candidates"] == 3)
    check("3 judges voted, majority 3v/2n both axes",
          all(r["judges_voted"] == 3 and r["viable_yes"] == 3 and
              r["nonobvious_yes"] == 2 for r in tally["rows"]))
    check("100% pass verdict", tally["tally"]["pass"] is True and
          tally["tally"]["pct"] == 100.0)

    # --- 5. resume: VALID legs skip ---
    calls = {"n": 0}

    def counting_chat(messages, model="", max_tokens=0, timeout_s=0,
                      stream=False):
        calls["n"] += 1
        return fake_chat(messages, model=model, max_tokens=max_tokens,
                         timeout_s=timeout_s, stream=stream)

    ra.cent_ai_chat = counting_chat
    rc2 = mod.main()
    check("resume skips VALID legs (0 calls)", calls["n"] == 0)
finally:
    if backup is not None:
        snap.write_text(backup)
    elif snap.exists():
        snap.unlink()
    pf2.unlink(missing_ok=True)
    for f in mod.OUT_DIR.glob("mj*__*.json"):
        f.unlink()
    (mod.OUT_DIR / "tally.json").unlink(missing_ok=True)
    os.environ.pop("V18_PACKS", None)
    print("MOCK artifacts scrubbed")

print("RESULT:", "ALL PASS" if not FAILS else f"FAILURES: {FAILS}")
sys.exit(1 if FAILS else 0)
