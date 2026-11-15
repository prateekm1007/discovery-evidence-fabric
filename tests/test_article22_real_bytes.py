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
  3. the fresh-held-out half is MEASURED (AM24 D4 wiring): the holdout
     v2 one-shot generation (12 records + generation record) is
     committed on this branch and the verifier instrument recomputes
     generation integrity from those bytes in-CI (zero LLM); the 0-4
     SCORING stays auditor-custody (Art. 4 CI-pinned flag), and the
     legacy held-out flag key stays visible carrying the MEASURED state
     (history is evidence, never silently deleted).
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


def test_article22_fresh_heldout_half_measured():
    """AM24 D4 wiring: the fresh-held-out half of Art. 22 is MEASURED.
    The holdout v2 one-shot generation is committed on this branch as
    12 per-problem records + the generation record (custody sha,
    selection sha, one-shot discipline, no-rubric access all on the
    record), and the verifier instrument recomputes generation
    integrity from those bytes with ZERO LLM calls — this test runs it
    as a subprocess and fails closed on any non-zero exit. The 0-4
    SCORING of the sealed set remains auditor-custody (Art. 4
    CI-pinned flag on the audit branch); the builder-side gate is the
    committed generation bytes + verifier recompute. The legacy flag
    key must STAY present in enforcement_flags.json carrying the
    MEASURED state text (history visible, never silently deleted)."""
    gen_dir = REPO / "eval" / "holdout_v2_generation"
    pairs = sorted(gen_dir.glob("HO2-*.json"))
    assert len(pairs) == 12, (
        f"fresh-held-out half expects the 12 holdout v2 one-shot "
        f"records committed, found {len(pairs)}")
    rec = json.loads((gen_dir / "holdout_v2_generation_record.json")
                     .read_text(encoding="utf-8"))
    custody = rec.get("custody") or {}
    assert custody.get("private_rubric_accessed") is False, (
        "the generation record must carry the no-rubric-access custody "
        "assertion (rubric PRIVATE)")
    assert custody.get("problems_sha256_16"), (
        "generation record must carry the received-problems sha (the "
        "custody basis of the fresh-held-out half)")
    assert rec.get("work_id") == "holdout-v2-generation"
    # the verifier instrument recomputes from bytes, zero LLM (Art. 13)
    import subprocess
    r = subprocess.run(
        [sys.executable, "-B", str(REPO / "scripts" /
                                   "r23_verify_holdout.py")],
        capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, (
        "holdout v2 generation integrity does NOT recompute from "
        f"committed bytes (exit {r.returncode}): "
        f"{(r.stdout + r.stderr).strip()[-400:]}")
    # the legacy flag stays present with the MEASURED state text
    flags = json.loads(FLAGS.read_text())
    legacy = flags.get("legacy_flags", {})
    flags_all = {**flags, **legacy}
    assert "article22_fresh_heldout" in flags_all, (
        "the Art. 22 held-out flag history was deleted — corrections "
        "stay visible (Art. XI: history is evidence too)")
    assert str(flags_all["article22_fresh_heldout"]).startswith(
        "MEASURED"), (
        "the held-out flag text must carry the MEASURED state (the "
        "half is measured; keep the history, update the state)")
