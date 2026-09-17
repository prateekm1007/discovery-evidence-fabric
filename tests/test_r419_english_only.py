"""R419 — Article LXX enforcement guard: English-only authorship.

Constitution v2.2.0 (Article LXX — Operational Language Rule): every
artifact the project AUTHORS is English. This test scans the artifacts
authored in the R419 round (and the constitution/amendment records) for
authorship in non-Latin scripts (CJK, Hangul, Kana, Cyrillic, Arabic,
Devanagari, Thai, Hebrew), with an explicit allowlist:

  - retrieved evidence / data fixtures (evidence spans are sources,
    Art. II forbids mutating them, including by translation);
  - quoted operator text inside disclosed directive records;
  - proper nouns in comments are still flagged unless allowlisted —
    the rule is operational language, and the guard is deliberately
    strict so violations are conscious decisions.

The guard checks a CLOSED list of R419-authored paths, not the whole
repository: pre-R419 artifacts are historical records (Art. XI) and are
never retroactively rewritten.
"""
from pathlib import Path
import re
import unicodedata

REPO = Path(__file__).resolve().parents[1]

# The R419-authored artifacts this guard covers (append as the round grows;
# historical artifacts are out of scope by design).
R419_AUTHORED = [
    "R419/constitution/ARTICLE_LXX_OPERATIONAL_LANGUAGE_RULE.md",
    "R419/constitution/AMENDMENT_RECORD.json",
    "scripts/r419_amend_constitution.py",
    "tests/test_r419_english_only.py",
]

# Script blocks the guard treats as non-English authorship. Latin, Greek
# letters used in math (allowed via symbol class), digits, punctuation,
# and common symbols pass; the blocks below are human-language scripts.
NON_LATIN_BLOCKS = (
    "CJK",      # Han / Hiragana-like entries begin with 'CJK' or script
    "HIRAGANA",
    "KATAKANA",
    "HANGUL",
    "CYRILLIC",
    "ARABIC",
    "DEVANAGARI",
    "THAI",
    "HEBREW",
    "BENGALI",
    "TAMIL",
    "GEORGIAN",
    "ARMENIAN",
)


def _is_non_latin(ch: str) -> bool:
    try:
        name = unicodedata.name(ch)
    except ValueError:
        return False
    return any(name.startswith(b) for b in NON_LATIN_BLOCKS)


def _violations(text: str) -> list:
    """Return (line_no, excerpt) for every line with non-Latin authorship."""
    out = []
    for i, line in enumerate(text.splitlines(), 1):
        hits = [ch for ch in line if _is_non_latin(ch)]
        if hits:
            excerpt = line.strip()[:90]
            out.append((i, excerpt))
    return out


def test_r419_amendment_record_exists_and_certified():
    rec = REPO / "R419/constitution/AMENDMENT_RECORD.json"
    assert rec.exists(), "AMENDMENT_RECORD.json missing"
    import json
    record = json.loads(rec.read_text())
    assert record["new"]["version"] == "2.2.0"
    assert record["old"]["version"] == "2.1.0"
    assert record["old"]["sha256"] == (
        "50ace8b30efeb72a90e5caa1af1913a74b8f9874327dc4ba1ac09b0537b92997")
    assert record["checks"]["compliance_check"] is True
    assert record["checks"]["acknowledgment_rebound"] is True


def test_constitution_v220_parses_and_acknowledged():
    # R441: the constitution amended to v2.3.0 (Article LXXII); R447:
    # amended again to v2.4.0 (Article LXXI, the deployed-production-URL
    # delivery standard); R468: amended to v2.5.0 (Article LXXIII, the
    # Operator Secrets Registry); R484: v2.6.0 (LXXIV, durable execution);
    # R498: v2.7.0 (LXXV, patent evidence is not patent truth); R503:
    # v2.8.0 (LXXVI, credential custody) — the loader must parse the
    # RATIFIED version, whatever it now is. Art. VII disclosed update
    # (R503): the frozen "2.5.0" literal is replaced by the loader's own
    # atomic derivation (single authority, Art. X), floored at the
    # LXX-era version this test was written for.
    from epistemic_integrity import constitution_loader as cl
    parsed = cl._parse_constitution_version()
    assert tuple(int(p) for p in parsed.split(".")) >= (2, 2, 0)
    state = cl.check_constitution_compliance()
    assert state.constitution_version == parsed
    assert state.constitution_present
    assert state.acknowledgment_present, (
        "acknowledgment must be re-bound to the amended constitution bytes")


def test_r419_authored_artifacts_are_english_only():
    problems = []
    for rel in R419_AUTHORED:
        p = REPO / rel
        if not p.exists():
            problems.append(f"{rel}: MISSING")
            continue
        for line_no, excerpt in _violations(p.read_text()):
            problems.append(f"{rel}:{line_no}: non-Latin authorship: {excerpt}")
    assert not problems, "Article LXX violations (true report):\n" + \
        "\n".join(problems)


def test_article_lxx_section_is_unique_and_verbatim():
    body = (REPO / "EPISTEMIC_CONSTITUTION.md").read_text()
    # prefix-safe: LXXII contains the LXX substring (R441 amendment)
    assert body.count("## Article LXX ") + body.count("## Article LXX\n") == 1
    # the rule's key sentence is present (punctuation-insensitive)
    norm = re.sub(r"[^a-z0-9]+", " ", body.lower())
    assert "shall be written in english unless the operator explicitly" in norm
    assert "does not alter the epistemic authority of sources in other languages" \
        in norm
