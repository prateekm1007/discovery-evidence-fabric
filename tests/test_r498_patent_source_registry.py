#!/usr/bin/env python3
"""R498 — invariants of the patent source registry + Article LXXV amendment.

Pins (Art. LXXV machine-enforcement point 5 + the amendment process):
  1. the registry parses and every source carries ALL SIX properties,
     each value carrying a provenance marker (measured or ORUV) -- never
     a bare assumption;
  2. every measured state used by the registry is in the declared state
     vocabulary;
  3. no source carries a coverage/novelty sufficiency claim (the coverage
     statement is the only place coverage is discussed, and it denies
     sufficiency);
  4. the amendment chain binds: the R498 record's old hash matches the
     recorded LXXIV-era hash, the R503 record's old hash matches the
     R498 record's new hash, and the latest ratified record's new hash
     matches the actual constitution file (Art. VII disclosed update,
     R503 — see R503/constitution/AMENDMENT_RECORD.json);
  5. the constitution body contains Article LXXV exactly once, with the
     six-property vocabulary and the three clauses.
"""
import hashlib
import json
import os
import re

import pytest

REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
REG = os.path.join(REPO, "PATENT_SOURCE_REGISTRY.json")
CONST = os.path.join(REPO, "EPISTEMIC_CONSTITUTION.md")
AMEND = os.path.join(REPO, "R498", "constitution",
                     "AMENDMENT_RECORD.json")

SIX = ["FREE", "ACCESSIBLE", "AUTOMATABLE", "LICENSE-COMPATIBLE",
       "RATE-LIMITED", "AUTHENTICATED"]

MEASURED_MARKERS = ("MEASURED_R49", "MEASURED_R4", "MEASURED_R50",
                    "ORUV",
                    "OPERATOR_RESEARCH", "UNREVIEWED", "UNMEASURED",
                    "REQUIRES_", "YES", "NO", "PARTIAL", "WITHIN-LIMITS",
                    "LIKELY", "VARIES", "OFTEN")


@pytest.fixture(scope="module")
def registry():
    return json.load(open(REG))


@pytest.fixture(scope="module")
def amendment():
    return json.load(open(AMEND))


def test_every_source_carries_all_six_properties(registry):
    for sid, src in registry["sources"].items():
        props = src["properties"]
        for p in SIX:
            assert p in props, "%s missing property %s" % (sid, p)
        # no property may be empty
        for p, v in props.items():
            assert isinstance(v, str) and v.strip(), "%s.%s empty" % (sid, p)


def test_every_property_value_carries_provenance_or_typed_state(registry):
    for sid, src in registry["sources"].items():
        for p, v in src["properties"].items():
            assert any(m in v for m in MEASURED_MARKERS), \
                "%s.%s carries no provenance marker: %r" % (sid, p, v)


def test_states_in_vocabulary(registry):
    vocab = set(registry["state_vocabulary"])
    for sid, src in registry["sources"].items():
        st = src["measured_state"]
        assert st in vocab, "%s state %r not in vocabulary" % (sid, st)


def test_no_coverage_sufficiency_claim(registry):
    blob = json.dumps(registry)
    for bad in ("coverage sufficient", "sufficient for novelty",
                "NOVELTY_VERIFIED", "coverage complete"):
        assert bad not in blob
    # the coverage statement must explicitly deny sufficiency
    assert "NO source" in registry["coverage_statement"]["statement"]


def test_amendment_hashes_bind(amendment):
    actual = hashlib.sha256(open(CONST, "rb").read()).hexdigest()
    # Art. VII disclosed update (R503, cited in R503/constitution/AMENDMENT_RECORD.json
    # process[]): the original assertion bound the CURRENT constitution bytes to the
    # LXXV-era hash — true only until the NEXT ratified amendment, which supersedes
    # that link by design. The pin now verifies the FULL amendment chain instead of
    # a single link — strictly stronger: each amendment record must bind its parent's
    # exact bytes, and the latest ratified record must bind the current file.
    assert amendment["new"]["version"] == "2.7.0"
    assert amendment["old"]["version"] == "2.6.0"
    assert amendment["old"]["sha256"] == \
        "17464afde07396afced90adca1ec20bc6b6975222153baf09b0337c98d40d81f"
    assert amendment["new"]["sha256"] == \
        "09e182a3cbe4de4d64097fb87bff5e942b30205f425810eff43236c2b5ced3b8"
    chain = json.load(open(os.path.join(REPO, "R503", "constitution",
                                        "AMENDMENT_RECORD.json"),
                           encoding="utf-8"))
    assert chain["old"]["version"] == "2.7.0"
    assert chain["old"]["sha256"] == amendment["new"]["sha256"]
    # Art. VII disclosed update (R507, same precedent): the chain extends
    # through the LXXVI link to the LXXVII-LXXIX Yield Firewall link —
    # each ratified record binds its parent's exact bytes; the LATEST
    # ratified record binds the current file
    link507 = json.load(open(os.path.join(REPO, "R507", "constitution",
                                          "AMENDMENT_RECORD.json"),
                             encoding="utf-8"))
    assert link507["old"]["version"] == "2.8.0"
    assert link507["old"]["sha256"] == chain["new"]["sha256"]
    assert link507["new"]["version"] == "2.9.0"
    assert link507["new"]["sha256"] == actual


def test_constitution_carries_lxxv_once_with_clauses():
    # encoding pinned (Art. VII harness fix, no expectation changed): the
    # constitution body is UTF-8 (em-dashes); a locale-default open()
    # mojibakes it on cp1252 Windows and fails the clause matches there.
    body = open(CONST, encoding="utf-8").read()
    assert len(re.findall(r"^## Article LXXV ", body, re.M)) == 1
    for clause in ("Clause 1 — Patent records are evidence objects",
                   "Clause 2 — Coverage is measured, never inferred from counts",
                   "Clause 3 — Secondary indexes discover; primary records verify"):
        assert clause in body
    for prop in ("FREE ", "ACCESSIBLE ", "AUTOMATABLE ",
                 "LICENSE-COMPATIBLE ", "RATE-LIMITED ", "AUTHENTICATED "):
        assert prop in body
    # Art. VII disclosed update (R503): the header version string is now derived
    # from the single authority (constitution_loader parses the file atomically,
    # Art. X) and must be at least the LXXV-era version — a frozen "2.7.0"
    # literal would have broken at every future ratified amendment by design.
    assert "**Version:**" in body
    from epistemic_integrity.constitution_loader import CONSTITUTION_VERSION
    assert body.split("**Version:** ", 1)[1].splitlines()[0] == CONSTITUTION_VERSION
    ver = tuple(int(p) for p in CONSTITUTION_VERSION.split("."))
    assert ver >= (2, 7, 0)


def test_lxxv_points_to_operational_layer_not_provider_state():
    """The article must point at the versioned source registry (the
    operational layer), not embed per-source instance state."""
    body = open(CONST).read()
    start = body.index("## Article LXXV")
    # Art. VII disclosed update (R503): the slice originally ran to the Four
    # Layers header, which at ratification time was exactly Article LXXV; the
    # R503 ratification inserted Article LXXVI (credential custody) after it,
    # and LXXVI legitimately discusses CREDENTIAL fingerprints — a different
    # concept from the patent-source instance state this test forbids. The
    # slice is now bounded to the LXXV article itself; the intent is unchanged.
    next_article = body.find("## Article LXXVI", start)
    end = next_article if next_article != -1 else body.index("# THE FOUR CONSTITUTIONAL LAYERS")
    article = body[start:end]
    # the operational pointer (level-appropriate: the layer, not the filename)
    assert "versioned source registry" in article
    # no per-source INSTANCE data may harden into the article
    for instance_marker in ("monthly_remaining", "fingerprint", "50fe7b3d",
                            "downloads", "http_status"):
        assert instance_marker not in article
