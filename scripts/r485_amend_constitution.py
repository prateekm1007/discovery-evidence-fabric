#!/usr/bin/env python3
"""[SUPERSEDED — race instance 6, see R485/LINEAGE_RECONCILIATION.json]
This is the SECOND LINE's certification of its own six-article v2.6.0
body (hash d1d6086e…), which the union RETIRED in favor of the
parallel line's landed single Article LXXIV (hash 17464afd…,
certified by scripts/r484_amend_constitution.py — the canonical chain).
Preserved as the honest history of the amendment race; running this
script against the current tree will FAIL by design (the six-article
body it certifies is no longer the law).

R485 constitutional amendment certification — Articles LXXIV–LXXIX
(the Sandbox/Execution Durability Principles).

Runs the normal constitutional certification chain for the v2.5.0 ->
v2.6.0 amendment (the r468/r419 pattern):

  1. verify the amendment document exists and carries the operator's
     directive verbatim (the A-M principles + FAIL CLOSED PROGRESS
     OPEN + the coder directives);
  2. verify each ratified article's normative language is verbatim in
     BOTH the amendment document and the Constitution body;
  3. verify the Constitution body parses to version 2.6.0 and each
     Article LXXIV-LXXIX section appears exactly once;
  4. verify the hash actually changed from the recorded v2.5.0 hash;
  5. re-run constitution_loader.acknowledge_constitution() (new hash
     and version bound into the acknowledgment capsule);
  6. run check_constitution_compliance() and require GREEN;
  7. write the AMENDMENT_RECORD.json verification trail (old/new
     hash);
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
    "version": "2.5.0",
    "sha256": "9730567afe1d29a96faec9a631bec965bc2e96be0dfe9f5af"
              "90b2a7b6921d362",
}

# the operator's 2026-09-17 directive, the binding fragments (the
# full text is verbatim in the amendment document; these fragments
# are the check surface — punctuation-insensitive per the r419
# normalization)
OPERATOR_DIRECTIVE_FRAGMENTS = (
    "If the orchestration depends on a local sandbox process "
    "remaining alive while the external AI computation continues, "
    "the execution model is fragile",
    "The lifetime of a caller, tool invocation, terminal session, "
    "polling process, or sandbox MUST NOT define the lifetime of an "
    "AI run",
    "Failure to observe a running operation MUST NOT be classified "
    "as failure of the operation itself",
    "A local background process MAY assist observation, diagnostics, "
    "or development, but MUST NOT be the sole authority for "
    "execution state, completion, artifacts, or provenance",
    "UNKNOWN must remain distinct from FAILED",
    "Polling MUST only observe durable state. Polling MUST NOT be "
    "required to keep computation alive",
    "Any client must be able to disconnect and later reconnect to "
    "the same run without loss of canonical execution state",
    "A completed run MUST be recoverable from durable server-side "
    "state without relying on the process that initiated or polled "
    "the run",
    "Toscanini MUST distinguish provider execution state from local "
    "execution environment state",
    "A retry after timeout, disconnect, or lost observation MUST NOT "
    "silently duplicate an external AI operation or corrupt "
    "canonical state",
    "Toscanini MUST NOT restart an expensive AI computation solely "
    "because the observer lost contact with it",
    "The system must fail closed with respect to truth, but remain "
    "open with respect to recoverable execution",
    "Do not introduce ENGINE_OPERATOR_KEY",
    "The permanent acceptance criterion is observer-independent "
    "execution",
)

# each article's normative opening (verbatim in body + amendment doc)
ARTICLES = {
    "LXXIV": "Execution Is Not Observation (Observer Independence)",
    "LXXV": "Remote Work Must Be Durable (the Server-Side Job "
            "Contract)",
    "LXXVI": "The Durable State Machine and Typed Timeouts",
    "LXXVII": "Provider Execution and Sandbox Execution Are Separate "
              "Boundaries",
    "LXXVIII": "Retry Must Be Idempotent",
    "LXXIX": "Fail Closed, Progress Open",
}

ARTICLE_LANGUAGE = {
    "LXXIV": (
        "The lifetime of a caller, tool invocation, terminal session, "
        "polling process, or sandbox MUST NOT define the lifetime of "
        "an AI run. A caller disappearing does not mean the run "
        "failed. A polling process disappearing does not mean the run "
        "failed. A sandbox being reaped does not mean the remote "
        "computation failed."
    ),
    "LXXV": (
        "Any operation capable of exceeding the execution "
        "environment's foreground/tool-call lifetime MUST be "
        "represented as a durable server-side job with a stable run "
        "identity."
    ),
    "LXXVI": (
        "UNKNOWN must remain distinct from FAILED — this reinforces "
        "Article XXV at the execution layer: the system that cannot "
        "determine an outcome records UNKNOWN and recovers "
        "observation; it never converts ignorance into failure."
    ),
    "LXXVII": (
        "Toscanini MUST distinguish provider execution state from "
        "local execution environment state."
    ),
    "LXXVIII": (
        "A retry after timeout, disconnect, or lost observation MUST "
        "NOT silently duplicate an external AI operation or corrupt "
        "canonical state."
    ),
    "LXXIX": (
        "The system must fail closed with respect to truth, but "
        "remain open with respect to recoverable execution."
    ),
}


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def main() -> int:
    failures = []
    body = (REPO / "EPISTEMIC_CONSTITUTION.md").read_text()
    amd = REPO / ("R485/constitution/"
                  "ARTICLES_LXXIV_LXXIX_SANDBOX_EXECUTION_"
                  "DURABILITY.md")
    if not amd.exists():
        print("FAIL: amendment document missing")
        return 1
    amd_text = amd.read_text()

    # 1. operator directive verbatim in the amendment document
    for i, frag in enumerate(OPERATOR_DIRECTIVE_FRAGMENTS, 1):
        if _norm(frag) not in _norm(amd_text):
            failures.append(f"operator directive fragment {i} not "
                            "verbatim in amendment document")
    # 2. each article's language verbatim in BOTH documents
    for art, lang in ARTICLE_LANGUAGE.items():
        if _norm(lang) not in _norm(body):
            failures.append(f"Article {art} language not verbatim in "
                            "Constitution body")
        if _norm(lang) not in _norm(amd_text):
            failures.append(f"Article {art} language not verbatim in "
                            "amendment document")

    # 3. version + article sections
    new_version = cl._parse_constitution_version()
    if new_version != "2.6.0":
        failures.append(f"version parses {new_version!r}, expected "
                        "2.6.0")
    for art, title in ARTICLES.items():
        n = body.count(f"## Article {art} —")
        if n != 1:
            failures.append(f"Article {art} section count {n} != 1 "
                            "in body")
        if f"## Article {art} — {title}" not in body:
            failures.append(f"Article {art} titled section missing "
                            "from body")

    new_hash = cl.compute_constitution_hash()
    if new_hash == OLD["sha256"]:
        failures.append("hash unchanged — body not actually amended")
    if new_hash == "":
        failures.append("hash empty — constitution missing")

    # 4. the verification trail record
    record = {
        "amendment": "Articles LXXIV–LXXIX — the Sandbox/Execution "
                     "Durability Principles",
        "round": "R485",
        "ratified": "2026-09-17",
        "sponsor": "operator directive 2026-09-17 (verbatim in the "
                   "amendment document; the Z.ai sandbox reaping "
                   "measured live — R485/ATTEMPT5_LIFECYCLE.json)",
        "old": OLD,
        "new": {
            "version": new_version,
            "sha256": new_hash,
        },
        "articles": {art: title for art, title in ARTICLES.items()},
        "principle_mapping": {
            "A/C/F/M": "LXXIV", "B/D/G/H/K": "LXXV",
            "E/J": "LXXVI", "I": "LXXVII", "L": "LXXVIII",
            "FAIL CLOSED, PROGRESS OPEN": "LXXIX",
        },
        "process": [
            "amendment document authored (R485/constitution/"
            "ARTICLES_LXXIV_LXXIX_SANDBOX_EXECUTION_DURABILITY.md)",
            "Constitution body amended: version header 2.5.0 -> "
            "2.6.0, amendment log line added, Articles LXXIV-LXXIX "
            "inserted between Article LXXIII and THE FOUR "
            "CONSTITUTIONAL LAYERS",
            "acknowledge_constitution() re-run — new hash + version "
            "bound into the acknowledgment capsule",
            "check_constitution_compliance() re-run — must be GREEN",
            "committed in the R485 code commit (no silent edit)",
        ],
        "checks": {},
    }

    # 5. re-acknowledge (the capsule re-binds to the amended bytes)
    ack = cl.acknowledge_constitution(
        agent=("R485 coder session: Constitution v2.5.0 read before "
               "coding; Articles LXXIV-LXXIX (the Sandbox/Execution "
               "Durability Principles) ratified through the formal "
               "amendment process per the operator's 2026-09-17 "
               "directive"),
        session="R485",
        intended_change=("ratify Articles LXXIV-LXXIX (observer-"
                         "independent execution); then the durable "
                         "execution contract + the observer-"
                         "independence E2E battery"),
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
        and state.constitution_version == "2.6.0"
        and state.constitution_hash == new_hash)
    record["checks"] = {
        "operator_directive_fragments_verbatim": (
            not any("operator directive fragment" in f
                    for f in failures)),
        "article_language_verbatim_in_body": (
            not any("not verbatim in Constitution body" in f
                    for f in failures)),
        "article_language_verbatim_in_amendment": (
            not any("not verbatim in amendment document" in f
                    for f in failures)),
        "version_parses": new_version,
        "all_six_article_sections_unique": (
            not any("section count" in f for f in failures)),
        "acknowledgment_rebound": (
            ack["constitution_hash"] == new_hash
            and ack["constitution_version"] == "2.6.0"),
        "compliance_check": compliant,
    }
    if not record["checks"]["acknowledgment_rebound"]:
        failures.append("acknowledgment did not re-bind to amended "
                        "bytes")
    if not compliant:
        failures.append("check_constitution_compliance() not GREEN")

    out = REPO / "R485/constitution/AMENDMENT_RECORD.json"
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
    print("AMENDMENT CERTIFIED: v2.6.0 (Articles LXXIV-LXXIX)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
