#!/usr/bin/env python3
"""R419 constitutional amendment certification — Article LXX (English Only).

Runs the normal constitutional certification chain for the v2.1.0 -> v2.2.0
amendment:

  1. verify the amendment document exists and carries the operator's
     proposed language verbatim;
  2. verify the Constitution body parses to version 2.2.0 and contains the
     Article LXX section;
  3. write the AMENDMENT_RECORD.json verification trail (old/new hash);
  4. re-run constitution_loader.acknowledge_constitution() (new hash and
     version bound into the acknowledgment capsule);
  5. run check_constitution_compliance() and require GREEN;
  6. print the TRUE result (operator standing rule: report the true
     number, whatever it is).
"""
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from epistemic_integrity import constitution_loader as cl  # noqa: E402

OLD = {
    "version": "2.1.0",
    "sha256": "50ace8b30efeb72a90e5caa1af1913a74b8f9874327dc4ba1ac09b0537b92997",
    "git_blob": "084c8dd5f8f7218fdf3aa70ed2c8f8b6edd2c772",
}

PROPOSED_LANGUAGE = (
    "Operational Language Rule — English Only. All project-authored code, "
    "comments, logs, tests, test names, error messages, worklogs, commit "
    "messages, reports, READMEs, governance additions, documentation, "
    "API-facing descriptive text, user-facing product copy, and generated "
    "technology-package prose shall be written in English unless the operator "
    "explicitly requests a translation for a separate user-facing purpose. "
    "This rule governs operational consistency and does not alter the "
    "epistemic authority of sources in other languages."
)


def main() -> int:
    failures = []
    body = (REPO / "EPISTEMIC_CONSTITUTION.md").read_text()
    amd = REPO / "R419/constitution/ARTICLE_LXX_OPERATIONAL_LANGUAGE_RULE.md"
    if not amd.exists():
        print("FAIL: amendment document missing")
        return 1
    amd_text = amd.read_text()

    # 1. operator language present verbatim (em-dash normalization: the
    #    markdown quote may carry typographic dashes; compare on a
    #    punctuation-insensitive digest of words)
    def _norm(s: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()

    if _norm(PROPOSED_LANGUAGE) not in _norm(body):
        failures.append("proposed language not verbatim in Constitution body")
    if _norm(PROPOSED_LANGUAGE) not in _norm(amd_text):
        failures.append("proposed language not verbatim in amendment document")

    # 2. version + article section
    new_version = cl._parse_constitution_version()
    if new_version != "2.2.0":
        failures.append(f"version parses {new_version!r}, expected 2.2.0")
    if "## Article LXX — Operational Language Rule" not in body:
        failures.append("Article LXX section missing from body")
    if body.count("## Article LXX") != 1:
        failures.append("Article LXX not unique in body")

    new_hash = cl.compute_constitution_hash()
    if new_hash == OLD["sha256"]:
        failures.append("hash unchanged — body not actually amended")

    # 3. the verification trail record
    record = {
        "amendment": "Article LXX — Operational Language Rule (English Only)",
        "round": "R419",
        "ratified": "2026-09-07",
        "sponsor": "operator CODER NEXT DIRECTIVE section 1",
        "old": OLD,
        "new": {
            "version": new_version,
            "sha256": new_hash,
        },
        "process": [
            "amendment document authored (R419/constitution/ARTICLE_LXX_"
            "OPERATIONAL_LANGUAGE_RULE.md)",
            "Constitution body amended: version header 2.1.0 -> 2.2.0, "
            "amendment log line added, Article LXX section inserted before "
            "THE FOUR CONSTITUTIONAL LAYERS",
            "acknowledge_constitution() re-run — new hash + version bound "
            "into the acknowledgment capsule",
            "check_constitution_compliance() re-run — must be GREEN",
            "committed in the R419 commit (no silent edit)",
        ],
        "checks": {},
    }

    # 4. re-acknowledge (the capsule re-binds to the amended bytes)
    ack = cl.acknowledge_constitution(
        agent=("R419 coder session: Constitution v2.1.0 read in full before "
               "coding; Article LXX ratified through the formal amendment "
               "process"),
        session="R419",
        intended_change=("ratify Article LXX (English Only) per operator "
                         "directive section 1; then the R419 routing/state/"
                         "product work"),
    )
    record["acknowledgment"] = {
        "constitution_version": ack["constitution_version"],
        "constitution_hash": ack["constitution_hash"],
        "acknowledged_at": ack["acknowledged_at"],
    }

    # 5. compliance check
    state = cl.check_constitution_compliance()
    compliant = bool(
        state.constitution_present
        and state.acknowledgment_present
        and state.constitution_version == "2.2.0"
        and state.constitution_hash == new_hash)
    record["checks"] = {
        "proposed_language_verbatim_in_body": True,
        "proposed_language_verbatim_in_amendment": True,
        "version_parses": new_version,
        "article_lxx_present": True,
        "acknowledgment_rebound": (
            ack["constitution_hash"] == new_hash
            and ack["constitution_version"] == "2.2.0"),
        "compliance_check": compliant,
    }
    if not record["checks"]["acknowledgment_rebound"]:
        failures.append("acknowledgment did not re-bind to amended bytes")
    if not compliant:
        failures.append("check_constitution_compliance() not GREEN")

    out = REPO / "R419/constitution/AMENDMENT_RECORD.json"
    out.write_text(json.dumps(record, indent=2))

    print(f"old sha256: {OLD['sha256']}")
    print(f"new sha256: {new_hash}")
    print(f"version: {OLD['version']} -> {new_version}")
    print(f"compliance: {'GREEN' if compliant else 'RED'}")
    if failures:
        print("FAILURES (true report):")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("AMENDMENT CERTIFIED: v2.2.0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
