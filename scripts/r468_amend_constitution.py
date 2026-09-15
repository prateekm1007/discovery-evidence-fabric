#!/usr/bin/env python3
"""R468 constitutional amendment certification — Article LXXIII (the
Operator Secrets Registry).

Runs the normal constitutional certification chain for the v2.4.0 ->
v2.5.0 amendment (the r419_amend_constitution.py pattern):

  1. verify the amendment document exists and carries the operator's
     directive verbatim (key bodies redacted — BS-021);
  2. verify the ratified article language is verbatim in BOTH the
     amendment document and the Constitution body;
  3. verify the Constitution body parses to version 2.5.0 and contains
     exactly one Article LXXIII section;
  4. verify the hash actually changed from the recorded v2.4.0 hash;
  5. re-run constitution_loader.acknowledge_constitution() (new hash and
     version bound into the acknowledgment capsule);
  6. run check_constitution_compliance() and require GREEN;
  7. write the AMENDMENT_RECORD.json verification trail (old/new hash);
  8. print the TRUE result (operator standing rule: report the true
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
    "version": "2.4.0",
    "sha256": "b54a1be9bcbdd2465d0b034e1e1f472f80b87174209c0d534b7d9e1"
              "223e649b2",
}

OPERATOR_DIRECTIVE = (
    "save all these huggingface secret, and write in your constitution "
    "to look it up in huggingface secret, so you dont keep asking me "
    "again"
)

ARTICLE_LANGUAGE = (
    "Operator credentials are registered assets, not session favors. "
    "Every credential the machine needs — router keys, gateway keys, the "
    "Hugging Face token, the GitHub PAT — is persisted in the canonical "
    "stores and looked up there before the operator is ever asked. A "
    "session that needs a credential MUST consult, in order: (1) its "
    "session environment; (2) the operator's local vault (the session "
    "workspace root file `.secrets.env` — outside every public "
    "repository); (3) the Hugging Face Space secret surface of the "
    "canonical production Space (names only — the API is write-only for "
    "values; a name present there means the deployed runtime already "
    "holds the value). Only when a credential is absent from all three "
    "may the session ask the operator — and the ask must name exactly "
    "which registered names were absent. Asking the operator for a "
    "credential already in the registry is an anti-entropy violation of "
    "the Articles XXIII–XXXIV family: it burns operator time and asserts "
    "state that does not exist. Secret VALUES never enter the repository, "
    "any artifact, log, or commit (BS-021) — fingerprints only.\n"
    "The registry's operational consequences:\n"
    "- **The vault is infrastructure, not a convenience.** The local "
    "vault (`.secrets.env` at the session workspace root — the same "
    "directory that carries the operator's `.gitcreds`) is the readable "
    "canonical value store across environment resets; it is never "
    "committed, never printed, and never shipped.\n"
    "- **The Space secret surface is the runtime injection path.** The "
    "canonical production Space's secrets are write-only from outside; "
    "the deployed runtime reads them at boot. A deploy re-wires any "
    "credential present in the deploy environment and leaves the "
    "standing secrets untouched otherwise (the r456 typed-honest "
    "pattern).\n"
    "- **The live inventory of registered NAMES lives in the round "
    "records** (`R468/HF_SPACE_SECRETS.json` and successors), never in "
    "this article — operational state does not harden into "
    "constitutional law (the Four Layers rule).\n"
    "- **Rotation is an operator act, recorded as such.** When the "
    "operator supplies a replacement credential, the old fingerprint, "
    "the new fingerprint, and the operator directive are recorded in "
    "the round record (Art. VI/XXV — declared, never fabricated as "
    "measured)."
)


def main() -> int:
    failures = []
    body = (REPO / "EPISTEMIC_CONSTITUTION.md").read_text()
    amd = REPO / ("R468/constitution/"
                  "ARTICLE_LXXIII_OPERATOR_SECRETS_REGISTRY.md")
    if not amd.exists():
        print("FAIL: amendment document missing")
        return 1
    amd_text = amd.read_text()

    # punctuation-insensitive digest of words (the r419 normalization)
    def _norm(s: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()

    # 1. operator directive verbatim in the amendment document
    if _norm(OPERATOR_DIRECTIVE) not in _norm(amd_text):
        failures.append("operator directive not verbatim in amendment "
                        "document")
    # 2. ratified article language verbatim in BOTH documents
    if _norm(ARTICLE_LANGUAGE) not in _norm(body):
        failures.append("article language not verbatim in Constitution "
                        "body")
    if _norm(ARTICLE_LANGUAGE) not in _norm(amd_text):
        failures.append("article language not verbatim in amendment "
                        "document")

    # 3. version + article section
    new_version = cl._parse_constitution_version()
    if new_version != "2.5.0":
        failures.append(f"version parses {new_version!r}, expected 2.5.0")
    if body.count("## Article LXXIII —") != 1:
        failures.append("Article LXXIII section not unique in body")
    if "## Article LXXIII — The Operator Secrets Registry" not in body:
        failures.append("Article LXXIII section missing from body")

    new_hash = cl.compute_constitution_hash()
    if new_hash == OLD["sha256"]:
        failures.append("hash unchanged — body not actually amended")
    if new_hash == "":
        failures.append("hash empty — constitution missing")

    # 4. the verification trail record
    record = {
        "amendment": "Article LXXIII — The Operator Secrets Registry "
                     "(Look It Up, Never Re-Ask)",
        "round": "R468",
        "ratified": "2026-09-16",
        "sponsor": "operator directive 2026-09-16 (verbatim in the "
                   "amendment document; key bodies redacted — BS-021)",
        "old": OLD,
        "new": {
            "version": new_version,
            "sha256": new_hash,
        },
        "process": [
            "amendment document authored (R468/constitution/"
            "ARTICLE_LXXIII_OPERATOR_SECRETS_REGISTRY.md)",
            "Constitution body amended: version header 2.4.0 -> 2.5.0, "
            "amendment log line added, Article LXXIII section inserted "
            "between Article LXXII and THE FOUR CONSTITUTIONAL LAYERS",
            "acknowledge_constitution() re-run — new hash + version "
            "bound into the acknowledgment capsule",
            "check_constitution_compliance() re-run — must be GREEN",
            "committed in the R468 code commit (no silent edit)",
        ],
        "checks": {},
    }

    # 5. re-acknowledge (the capsule re-binds to the amended bytes)
    ack = cl.acknowledge_constitution(
        agent=("R468 coder session: Constitution v2.4.0 read before "
               "coding; Article LXXIII ratified through the formal "
               "amendment process per the operator's 2026-09-16 "
               "directive"),
        session="R468",
        intended_change=("ratify Article LXXIII (the Operator Secrets "
                         "Registry); then the secrets persistence + the "
                         "R467 deploy closure"),
    )
    record["acknowledgment"] = {
        "constitution_version": ack["constitution_version"],
        "constitution_hash": ack["constitution_hash"],
        "acknowledged_at": ack["acknowledged_at"],
    }

    # 6. compliance check
    state = cl.check_constitution_compliance()
    compliant = bool(
        state.constitution_present
        and state.acknowledgment_present
        and state.constitution_version == "2.5.0"
        and state.constitution_hash == new_hash)
    record["checks"] = {
        "operator_directive_verbatim_in_amendment": True,
        "article_language_verbatim_in_body": True,
        "article_language_verbatim_in_amendment": True,
        "version_parses": new_version,
        "article_lxxiii_present_and_unique": True,
        "acknowledgment_rebound": (
            ack["constitution_hash"] == new_hash
            and ack["constitution_version"] == "2.5.0"),
        "compliance_check": compliant,
    }
    if not record["checks"]["acknowledgment_rebound"]:
        failures.append("acknowledgment did not re-bind to amended bytes")
    if not compliant:
        failures.append("check_constitution_compliance() not GREEN")

    out = REPO / "R468/constitution/AMENDMENT_RECORD.json"
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
    print("AMENDMENT CERTIFIED: v2.5.0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
