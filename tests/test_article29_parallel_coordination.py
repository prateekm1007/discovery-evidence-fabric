"""Constitution v3.1.0, Article 29 — Parallel builders: claim, execute,
verify (CI).

Owner decision (F25, seven measured duplicate-run instances): two builder
sessions run CONCURRENTLY — they catch each other's errors — and no
duplicate entries. The mechanism makes duplication structurally impossible
rather than merely discouraged: claim-before-work with the git push as the
mutex, one executor per work item, and an independent verifier that
recomputes from committed bytes (Art. 13) and never re-runs.

Registry: eval/work_claims.json — {"schema": "work-claims/v1",
"sessions": {...}, "claims": [...]}.

CI checks (the Article 29 CI line, plus owner direction 3):
  1. registry schema valid; an EMPTY registry passes (the lawful
     adoption-time state);
  2. no two live EXECUTOR claims per work_id — a second EXECUTOR claim on
     the same work_id must reference the dead lease it takes over
     (Art. 29(b)/(d));
  3. one-shot work has exactly one generation — EXECUTOR claims on a
     one_shot work_id form a single non-branching takeover chain rooted in
     one claim (resumptions continue the generation; free-standing
     duplicates and branching chains fail);
  4. each DONE measurement (and one-shot work) has a verifier record — a
     VERIFIER-role claim on the same work_id (Art. 29(c));
  5. every commit after the adoption commit carries Session:/Work-Id:
     trailers (100% of new commits, owner direction 3);
  6. commits touching canonical measurement artifacts match an EXECUTOR
     claim in that commit's own registry snapshot — claim-before-work is
     enforced, not asked for (Art. 29(b)/(e)).
"""
import json
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
REG = REPO / "eval" / "work_claims.json"
CONST = REPO / "EPISTEMIC_CONSTITUTION.md"

ROLES = ("EXECUTOR", "VERIFIER")
KINDS = ("measurement", "one_shot", "task")
STATUSES = ("OPEN", "DONE", "EXPIRED", "TAKEN_OVER")
DEAD = ("EXPIRED", "TAKEN_OVER")
# canonical measurement artifacts (Art. 29(e) canonical-path ownership):
# judged battery records, generated pair records, sealed holdout runs, and
# filed verification records — the quota-consuming / evidence-bearing bytes
CANONICAL = ("eval/pairs/", "eval/battery_", "eval/holdout_",
             "eval/verifications/")


def _git(*args: str) -> str:
    r = subprocess.run(["git", "-C", str(REPO), *args],
                       capture_output=True, text=True)
    assert r.returncode == 0, (
        f"git {' '.join(args)} failed: {r.stderr.strip()}")
    return r.stdout


def _validate_registry(reg, where: str, kind_violations=None,
                       status_violations=None):
    """Schema validation for work-claims/v1 (Art. 29 CI line: registry
    schema valid). Returns (sessions, claims).

    F42 (AM29) forward-only disclosure path: a claim whose `kind` is
    outside the enum may exist in an IMMUTABLE HISTORICAL snapshot only
    if it is REGISTERED in the CURRENT registry's claim_kind_violations[]
    (claim_id, wrong_kind, correct_kind in KINDS, status="remediated").
    The CURRENT registry itself is always validated strictly (callers
    that omit kind_violations) — the tip must be clean; history may
    carry only disclosed, remediated violations. Fix the instrument,
    never rewrite history (Art. 4)."""
    assert isinstance(reg, dict), f"{where}: registry must be an object"
    assert reg.get("schema") == "work-claims/v1", \
        f"{where}: schema must be work-claims/v1"
    sessions = reg.get("sessions")
    claims = reg.get("claims")
    assert isinstance(sessions, dict), \
        f"{where}: sessions must be an object ({{}} allowed)"
    assert isinstance(claims, list), \
        f"{where}: claims must be an array ([] allowed)"
    registered_kinds = {}
    if kind_violations is not None:
        assert isinstance(kind_violations, list), \
            f"{where}: claim_kind_violations must be an array"
        for v in kind_violations:
            assert isinstance(v, dict) and v.get("claim_id"), \
                f"{where}: kind violation entries need claim_id"
            assert v.get("correct_kind") in KINDS, (
                f"{where}: kind violation for {v.get('claim_id')} must "
                "name the correct_kind")
            assert v.get("wrong_kind") and \
                v.get("wrong_kind") not in KINDS, (
                f"{where}: kind violation for {v.get('claim_id')} must "
                "name the out-of-enum wrong_kind")
            assert v.get("status") == "remediated", (
                f"{where}: kind violation for {v.get('claim_id')} must "
                "be remediated (forward-only disclosure)")
            registered_kinds[v["claim_id"]] = v
    registered_statuses = {}
    if status_violations is not None:
        assert isinstance(status_violations, list), \
            f"{where}: claim_status_violations must be an array"
        for v in status_violations:
            assert isinstance(v, dict) and v.get("claim_id"), \
                f"{where}: status violation entries need claim_id"
            assert v.get("correct_status") in STATUSES, (
                f"{where}: status violation for {v.get('claim_id')} must "
                "name the correct_status")
            assert v.get("wrong_status") and \
                v.get("wrong_status") not in STATUSES, (
                f"{where}: status violation for {v.get('claim_id')} must "
                "name the out-of-enum wrong_status")
            assert v.get("status") == "remediated", (
                f"{where}: status violation for {v.get('claim_id')} must "
                "be remediated (forward-only disclosure)")
            registered_statuses[v["claim_id"]] = v
    for sid, s in sessions.items():
        assert isinstance(sid, str) and sid.strip(), \
            f"{where}: session id must be a non-empty string"
        assert isinstance(s, dict), \
            f"{where}: session {sid} must be an object"
        assert str(s.get("role") or "").strip(), \
            f"{where}: session {sid} needs a role"
    by_id = {}
    for c in claims:
        cid = c.get("claim_id")
        assert isinstance(cid, str) and cid, f"{where}: claim_id required"
        assert cid not in by_id, f"{where}: duplicate claim_id {cid}"
        by_id[cid] = c
        assert c.get("role") in ROLES, f"{cid}: role must be one of {ROLES}"
        if c.get("kind") not in KINDS:
            regd = registered_kinds.get(cid)
            assert regd and regd.get("wrong_kind") == c.get("kind"), (
                f"{cid}: kind must be one of {KINDS} (F42: an "
                "out-of-enum kind in an immutable historical snapshot "
                "must be REGISTERED in claim_kind_violations[] with the "
                "correct kind named — forward-only disclosure; history "
                "rewrites are not a remedy, Art. 4)")
        if c.get("status") not in STATUSES:
            regd_s = registered_statuses.get(cid)
            assert regd_s and regd_s.get("wrong_status") == c.get("status"), (
                f"{cid}: status must be one of {STATUSES} (F42: an "
                "out-of-enum status in an immutable HISTORICAL snapshot "
                "must be REGISTERED in claim_status_violations[] with the "
                "correct status named — forward-only disclosure; the "
                "current-registry tip is always strict; history rewrites "
                "are not a remedy, Art. 4)")
        assert isinstance(c.get("session_id"), str) and \
            c["session_id"].strip(), f"{cid}: session_id required"
        assert c["session_id"] in sessions, (
            f"{cid}: session {c['session_id']} is not registered "
            "(Art. 29(a): identity on first push)")
        assert isinstance(c.get("work_id"), str) and c["work_id"].strip(), \
            f"{cid}: work_id required"
        assert isinstance(c.get("base_sha"), str) and \
            len(c["base_sha"]) >= 7, f"{cid}: base_sha required"
        assert isinstance(c.get("claimed_at"), str) and \
            c["claimed_at"].strip(), f"{cid}: claimed_at required"
        assert isinstance(c.get("lease_expiry"), str) and \
            c["lease_expiry"].strip(), f"{cid}: lease_expiry required"
        arts = c.get("artifact_paths")
        assert isinstance(arts, list) and arts and all(
            isinstance(p, str) and p.strip() for p in arts), \
            f"{cid}: artifact_paths must be a non-empty list of paths"
    # takeover references must point at an earlier EXECUTOR claim on the
    # same work_id whose lease is dead (Art. 29(d))
    for c in claims:
        t = c.get("takes_over")
        if t:
            assert t in by_id, \
                f"{c['claim_id']}: takes_over {t} is not a known claim"
            prev = by_id[t]
            assert prev["work_id"] == c["work_id"], \
                f"{c['claim_id']}: takeover across work_ids"
            assert prev["role"] == "EXECUTOR", \
                f"{c['claim_id']}: takeover of a non-EXECUTOR claim"
            assert prev["status"] in DEAD, \
                f"{c['claim_id']}: takeover of a live lease " \
                f"({prev['status']})"
    return sessions, claims


def _executor_claims_by_work(claims):
    by_work = {}
    for c in claims:
        if c["role"] == "EXECUTOR":
            by_work.setdefault(c["work_id"], []).append(c)
    return by_work


def test_empty_registry_passes():
    """The explicit acceptance: an empty registry is a VALID registry
    (adoption state — identity may be registered, no claims filed yet)."""
    sessions, claims = _validate_registry(
        {"schema": "work-claims/v1", "sessions": {}, "claims": []},
        "literal-empty")
    assert sessions == {} and claims == []


def test_registry_schema_valid():
    reg = json.loads(REG.read_text(encoding="utf-8"))
    sessions, claims = _validate_registry(reg, "eval/work_claims.json")
    if not claims:
        # adoption registry committed WITH the claim protocol: identity
        # must already be registered even though no claims exist yet
        assert sessions, (
            "adoption registry must register at least one session "
            "identity (Art. 29(a))")


def test_no_two_live_executor_claims_per_work_id():
    reg = json.loads(REG.read_text(encoding="utf-8"))
    _, claims = _validate_registry(reg, "eval/work_claims.json")
    for work, exs in _executor_claims_by_work(claims).items():
        exs = sorted(exs, key=lambda c: (c.get("claimed_at") or "",
                                         c["claim_id"]))
        for prev, cur in zip(exs, exs[1:]):
            assert cur.get("takes_over") == prev["claim_id"], (
                f"work {work}: EXECUTOR claim {cur['claim_id']} does not "
                f"take over {prev['claim_id']} — two live executors on one "
                "work item (Art. 29(b): the push is the mutex; a second "
                "executor must reference the dead lease, Art. 29(d))")


def test_one_shot_work_has_exactly_one_generation():
    reg = json.loads(REG.read_text(encoding="utf-8"))
    _, claims = _validate_registry(reg, "eval/work_claims.json")
    taken_over = {}
    for c in claims:
        t = c.get("takes_over")
        if t:
            taken_over[t] = taken_over.get(t, 0) + 1
    for cid, n in taken_over.items():
        assert n == 1, (
            f"claim {cid} is taken over {n} times — a branching chain "
            "means a duplicate execution (Art. 29(c))")
    for work, exs in _executor_claims_by_work(claims).items():
        if any(c["kind"] == "one_shot" for c in exs):
            roots = [c for c in exs if not c.get("takes_over")]
            assert len(roots) == 1, (
                f"one_shot work {work} has {len(roots)} chain roots — "
                "exactly one generation is required (Art. 29(c)); "
                "resumptions continue the same chain via takes_over")
            for c in exs:
                assert c["kind"] == "one_shot", (
                    f"work {work}: mixed kinds on a one_shot work item")


def test_each_done_measurement_has_a_verifier_record():
    reg = json.loads(REG.read_text(encoding="utf-8"))
    _, claims = _validate_registry(reg, "eval/work_claims.json")
    verified = {c["work_id"] for c in claims if c["role"] == "VERIFIER"}
    for c in claims:
        if c["role"] == "VERIFIER":
            exs = [x for x in claims if x["work_id"] == c["work_id"]
                   and x["role"] == "EXECUTOR"]
            assert exs, (
                f"{c['claim_id']}: VERIFIER record on {c['work_id']} with "
                "no executor claim — verification attributes to a claim")
        if c["status"] == "DONE" and c["kind"] in ("measurement", "one_shot"):
            assert c["work_id"] in verified, (
                f"{c['claim_id']} (work {c['work_id']}): DONE measurement "
                "without a VERIFIER record — the independent check "
                "(recompute from committed bytes, Art. 13; never re-run) "
                "is part of the work item (Art. 29(c))")


def _post_adoption_commits():
    """Commits after the one that added eval/work_claims.json, with their
    trailers and touched files. Requires full history (the queue workflow
    checks out with fetch-depth: 0)."""
    heads = _git("log", "--reverse", "--diff-filter=A", "--format=%H",
                 "--", "eval/work_claims.json").split()
    assert heads, "eval/work_claims.json was never committed"
    rng = f"{heads[0]}..HEAD"
    shas = _git("log", "--format=%H", rng).split()
    trailers, files = {}, {}
    for block in _git("log", rng,
                      "--format=%x1e%H%x1f%(trailers)").split("\x1e"):
        block = block.lstrip("\n")
        if not block.strip():
            continue
        sha, _, tr = block.partition("\x1f")
        trailers[sha.strip()] = tr
    for block in _git("log", rng, "--name-only",
                      "--format=%x1e%H%x1f").split("\x1e"):
        block = block.lstrip("\n")
        if not block.strip():
            continue
        sha, _, rest = block.partition("\x1f")
        files[sha.strip()] = [ln.strip() for ln in rest.splitlines()
                              if ln.strip()]
    return shas, trailers, files


def _trailer(tr, key):
    m = re.search(rf"^{key}:\s*(\S+)\s*$", tr or "", re.M)
    return m.group(1) if m else None


def test_post_adoption_commits_carry_session_and_work_id_trailers():
    shas, trailers, _ = _post_adoption_commits()
    # F36 typed allowance (fail-closed the OTHER way): a trailer-less
    # commit must be REGISTERED in eval/work_claims.json
    # (trailer_violations[]) with session attribution and remediation
    # status — violations can never hide silently, and the register
    # itself is CI-gated. Unregistered trailer-less commits still fail.
    reg = json.loads(REG.read_text(encoding="utf-8"))
    disclosed = [str(v.get("sha") or "")
                 for v in (reg.get("trailer_violations") or [])]
    for sha in shas:
        tr = trailers.get(sha, "")
        sess = _trailer(tr, "Session")
        wid = _trailer(tr, "Work-Id")
        if not (sess and wid):
            assert any(sha.startswith(s) for s in disclosed if s), (
                f"commit {sha[:12]} lacks Session:/Work-Id: trailers AND "
                "is not registered in trailer_violations — every "
                "violation must be typed with session attribution "
                "(Art. 29(a) + F36 discipline; 100% of compliant "
                "post-adoption commits carry both)")


def test_canonical_measurement_commits_match_a_claim():
    shas, trailers, files = _post_adoption_commits()
    for sha in shas:
        canon = [f for f in files.get(sha, []) if f.startswith(CANONICAL)]
        if not canon:
            continue
        tr = trailers.get(sha, "")
        sess = _trailer(tr, "Session")
        wid = _trailer(tr, "Work-Id")
        assert sess and wid, (
            f"commit {sha[:12]} touches canonical measurement bytes "
            f"{canon} without Session:/Work-Id: trailers (Art. 29(a))")
        snap = json.loads(_git("show", f"{sha}:eval/work_claims.json"))
        cur = json.loads(REG.read_text(encoding="utf-8"))
        _, claims = _validate_registry(
            snap, f"{sha[:12]}:registry",
            kind_violations=cur.get("claim_kind_violations"),
            status_violations=cur.get("claim_status_violations"))
        matching = [
            c for c in claims
            if c["role"] == "EXECUTOR"
            and c["session_id"] == sess
            and c["work_id"] == wid
            and any(f == p or (p.endswith("/") and f.startswith(p))
                    for p in c.get("artifact_paths", []) for f in canon)
        ]
        if not matching:
            # F36-pattern typed allowance (fail-closed the OTHER way): a
            # canonical-touching commit whose trailers do not match a
            # covering EXECUTOR claim must be REGISTERED in
            # canonical_claim_violations[] with the correct work_id
            # named — unregistered mismatches still fail.
            reg = json.loads(REG.read_text(encoding="utf-8"))
            disclosed = [str(v.get("sha") or "")
                         for v in (reg.get("canonical_claim_violations")
                                   or [])]
            assert any(sha.startswith(s) for s in disclosed if s), (
                f"commit {sha[:12]} touches canonical measurement bytes "
                f"{canon} without a covering EXECUTOR claim and is not "
                "registered in canonical_claim_violations (claim-"
                "before-work is enforced, not asked for)")


def test_kind_enum_errors_have_forward_only_disclosure_path():
    """F42 (AM29): an out-of-enum kind in an immutable historical
    snapshot passes ONLY when registered in claim_kind_violations[]
    (correct kind named, remediated). The current registry is always
    strict. The remedy for a schema mistake is a forward-only
    disclosure commit, never a history rewrite (Art. 4)."""
    base = {"schema": "work-claims/v1",
            "sessions": {"builder-t": {"role": "EXECUTOR"}},
            "claims": [{
                "claim_id": "c-x", "role": "EXECUTOR",
                "kind": "one-shot-sealed-generation",
                "status": "DONE", "session_id": "builder-t",
                "work_id": "w", "base_sha": "abc1234",
                "claimed_at": "2026-11-16T00:00:00Z",
                "lease_expiry": "2026-11-16T04:00:00Z",
                "artifact_paths": ["eval/x/"]}]}
    regd = dict(base, claim_kind_violations=[{
        "claim_id": "c-x",
        "wrong_kind": "one-shot-sealed-generation",
        "correct_kind": "one_shot", "status": "remediated",
        "session_id": "builder-t",
        "note": "self-caught post-push; fixed forward in the next "
                "commit"}])
    # (a) registered -> passes (forward-only disclosure)
    s, c = _validate_registry(regd, "hist", kind_violations=regd[
        "claim_kind_violations"])
    assert c[0]["claim_id"] == "c-x"
    # (b) unregistered -> fails (violations can never hide silently)
    try:
        _validate_registry(base, "hist", kind_violations=[])
        raise SystemExit("unregistered kind violation must fail")
    except AssertionError:
        pass
    # (c) current registry is strict even with a registration present
    try:
        _validate_registry(regd, "current")
        raise SystemExit("the tip registry must always be enum-clean")
    except AssertionError:
        pass
    # (d) a registration naming a wrong_kind that IS in the enum (i.e.
    # not a real violation) is invalid instrument use
    bad = dict(base, claim_kind_violations=[{
        "claim_id": "c-x", "wrong_kind": "task",
        "correct_kind": "one_shot", "status": "remediated"}])
    try:
        _validate_registry(bad, "hist", kind_violations=bad[
            "claim_kind_violations"])
        raise SystemExit("registration must name an out-of-enum kind")
    except AssertionError:
        pass


def test_constitution_carries_article_29():
    text = CONST.read_text(encoding="utf-8")
    heads = re.findall(r"^### Article (\d+)\b", text, re.M)
    assert "29" in heads, "Article 29 missing from the constitution"
    assert "Parallel builders" in text, "Article 29 title missing"
    assert "claim" in text and "VERIFIER" in text, \
        "Article 29 claim/execute/verify mechanism missing"
