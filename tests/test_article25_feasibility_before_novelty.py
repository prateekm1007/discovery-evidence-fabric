"""Constitution v3.0.0, Article 25 — Feasibility before novelty (CI).

"Delivered ideas need a physics/scope/premise check and a targeted
disconfirming-evidence search."

Runs on the COMMITTED real bytes of the live arms (60 records).
Wireable offline half: every DELIVERED answer carries a non-empty
PHYSICS CHECK section grounded in a governing relation / premise /
scope statement. The disconfirming-search-record half has NO artifact
in the current contract — flagged (see eval/enforcement_flags.json);
CI asserts the flag exists so the gap cannot silently disappear.
"""
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

ARMS = [REPO / "eval" / "pairs" / "r11_a1w_r1",
        REPO / "eval" / "pairs" / "r11_a1t_r1"]
FLAGS = REPO / "eval" / "enforcement_flags.json"
TYPED_STATES = {"KILL", "GEN_FAILED", "CRITIC_KILL", "KILLED"}
GROUNDING = re.compile(
    r"govern|premise|scope|relation|equation|principle|physics|"
    r"thermodynamic|kinetic|mechanic|electrochem|flux|conserv", re.I)


def test_article25_physics_scope_premise_on_delivered_ideas():
    flagged, delivered = [], 0
    for arm in ARMS:
        for f in sorted(arm.glob("*.json")):
            rec = json.loads(f.read_text())
            pid = str(rec.get("problem_id") or f.stem)
            verdict = str(rec.get("critic_verdict") or "")
            if any(t in verdict.upper() for t in TYPED_STATES):
                continue
            ans = str(rec.get("a1_answer") or "")
            # Art. 25 demands a physics/scope/premise check as
            # CONTENT: a PHYSICS CHECK section (the standardized
            # contract; separators vary: ':' or ' — ' across
            # contract eras) or inline grounding in a free-prose
            # answer.
            m = re.search(
                r"PHYSICS CHECK\s*[-—:]\s*(.+?)(?=\n[A-Z][A-Z][A-Z ]+"
                r"\s*[-—:]|\Z)", ans, re.S)
            probe = m.group(1) if m and m.group(1).strip() else ans
            if not (GROUNDING.search(probe)
                    and re.search(r"\d", probe)):
                flagged.append(f"{pid}: delivered idea without "
                               f"physics/premise grounding (no "
                               f"PHYSICS CHECK section and no inline "
                               f"governing-relation statement)")
            delivered += 1
    assert delivered >= 55, f"expected >=55 delivered ideas, " \
                            f"got {delivered}"
    assert not flagged, ("Art. 25 physics/premise violations: "
                         + "; ".join(flagged[:8]))


def test_article25_disconfirming_search_flag_is_live():
    """The un-wired half of Art. 25 (targeted disconfirming-evidence
    search record) must stay FLAGGED, not silent."""
    flags = json.loads(FLAGS.read_text())
    assert "article25_disconfirming_search" in flags, (
        "Art. 25 disconfirming-search gap is no longer flagged — "
        "either wire the check or restore the flag")
    assert str(flags["article25_disconfirming_search"]).startswith(
        "FLAGGED")
