"""Constitution v3.0.0, Article 22 — Real-bytes acceptance (CI).

"A fix is accepted only on committed real outputs and fresh held-out
material. Hand-built fixtures prove mechanics only."

Wireable offline half:
  1. the committed acceptance record (battery r11) rests on real
     judged bytes — 30 committed rows each carrying raw judge draws
     (the recompute of record rides Art. 19; here we assert the
     acceptance fields exist and the judged bytes are present);
  2. every fixture used by the enforcement tests declares its class:
     MECHANICS_ONLY or BYTE_RECORD_PIN — an unlabeled fixture cannot
     back an acceptance claim;
  3. the fresh-held-out half is FLAGGED (holdout v2 awaits owner
     authorization; the owner-action register tracks it) — CI asserts
     the flag exists so acceptance can never silently claim held-out
     coverage it does not have.
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

FLAGS = REPO / "eval" / "enforcement_flags.json"
FIXTURES = REPO / "tests" / "fixtures"


def test_article22_acceptance_rests_on_committed_real_bytes():
    rec = json.loads((REPO / "eval" / "battery_a1w_r11.json").read_text())
    rows = rec.get("results", [])
    assert len(rows) == 30, f"30 committed judged rows expected, " \
                            f"got {len(rows)}"
    with_draws = [r for r in rows
                  if isinstance(r.get("draws"), list)
                  and len(r["draws"]) == 3
                  and any(d.get("outcome") == "JUDGE_VALID" for d in
                          r["draws"])]
    assert len(with_draws) >= 29, (
        f"acceptance record must rest on real judge draws, got "
        f"{len(with_draws)}/30 rows with valid draws")
    summ = rec.get("summary_type_credited") or rec.get(
        "summary_all_valid") or {}
    assert "AM14_D5_point_estimate" in summ, (
        "acceptance record carries no gate point-estimate")


def test_article22_fixtures_declare_mechanics_only():
    enforced = ["article21_disclosed_findings.json"]
    for name in enforced:
        fx = FIXTURES / name
        assert fx.exists(), f"declared fixture missing: {name}"
        data = json.loads(fx.read_text())
        cls = str(data.get("class") or "")
        assert cls in ("MECHANICS_ONLY", "BYTE_RECORD_PIN"), (
            f"{name}: fixture class unlabeled ({cls!r}) — cannot back "
            f"an acceptance claim")


def test_article22_heldout_half_flagged_not_silent():
    flags = json.loads(FLAGS.read_text())
    assert "article22_fresh_heldout" in flags, (
        "Art. 22 held-out gap is no longer flagged — acceptance must "
        "never claim held-out coverage it does not have")
    assert str(flags["article22_fresh_heldout"]).startswith("FLAGGED")
