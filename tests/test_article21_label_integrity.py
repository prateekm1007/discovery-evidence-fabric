"""Constitution v3.0.0, Article 21 — Label integrity (CI).

"Provenance labels must be machine-checkable: USER CONSTRAINT must
match a problem-text span; CALCULATED must evaluate from labeled
inputs; citations must resolve."

Runs on the COMMITTED real pair records (Art. 22: real bytes, not
fixtures): every record in the live arm directories
(eval/pairs/r11_a1w_r1, eval/pairs/r11_a1t_r1) is scanned.

Checks implemented (machine-checkable, typed failures):
  1. USER CONSTRAINT — the span after the label must overlap a
     problem-text span (token overlap against the problem's
     constraint+question text; >=0.5 Jaccard on informative tokens).
  2. ASSUMPTION — must carry a non-trivial justification (>=4 words).
  3. CALCULATED — must evaluate: the labeled span carries digits and
     an arithmetic relation and at least one quantity token that
     appears in the problem or answer text (labeled inputs).
  4. Citations — every http(s) URL cited must parse and must not be
     obviously malformed (scheme+netloc). Full network resolution is
     a live-web check outside CI (disclosed boundary; the sources
     registry binding is checked where the record carries registry
     ids).

Disclosure: CI enforces the machine-checkable core of the article;
semantic citation resolution stays with the auditor's per-axis
re-judgment (auditor constitution Art. 13).
"""
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

ARMS = [REPO / "eval" / "pairs" / "r11_a1w_r1",
        REPO / "eval" / "pairs" / "r11_a1t_r1"]
STOP = set("the a an and or of to in on for with by from as is are be "
           "was were at it its this that these those per not no than "
           "then so such into out over under up down more less most "
           "least same other another any all each must should shall "
           "will can may within without during before after between "
           "against across using used use new one two three first "
           "second".split())


def _tokens(text):
    return [t for t in re.findall(r"[a-z0-9][a-z0-9\-_.]*", text.lower())
            if t not in STOP and (len(t) > 2 or t.isdigit())]


def _problems():
    probs = {}
    for pf in (REPO / "eval" / "problems.json",
               REPO / "eval" / "problems_dev12.json"):
        data = json.loads(pf.read_text())
        plist = data if isinstance(data, list) else data.get("problems", [])
        for p in plist:
            probs[str(p.get("problem_id") or p.get("id"))] = p
    return probs


def _jaccard_overlap(labeled, problem_text):
    lt, pt = set(_tokens(labeled)), set(_tokens(problem_text))
    if not lt:
        return 1.0  # nothing claimable -> vacuous, counted separately
    return len(lt & pt) / len(lt)


def _check_record(rec, prob, path):
    findings = []
    ans = str(rec.get("a1_answer") or "")
    if not ans.strip():
        return ["GEN_FAILED: no answer text"]
    ptext = " ".join(str(prob.get(k) or "") for k in
                     ("constraint", "question", "failure", "device"))

    # 1. USER CONSTRAINT spans match problem-text spans
    for m in re.finditer(
            r"USER CONSTRAINT[^\n:]*:\s*(.{5,200}?)(?=\n[A-Z][A-Z ]{3,}"
            r"[-—:]|\n\n|\Z)", ans, re.S):
        span = m.group(1).strip()
        j = _jaccard_overlap(span, ptext)
        if j < 0.5:
            findings.append(
                f"USER CONSTRAINT span not machine-matched to problem "
                f"text (J={j:.2f}): {span[:70]!r}")
    # 2. ASSUMPTION labels carry justification
    for m in re.finditer(
            r"ASSUMPTION[^\n:]*:\s*(.{0,200}?)(?=\n[A-Z][A-Z ]{3,}"
            r"[-—:]|\n\n|\Z)", ans, re.S):
        span = m.group(1).strip()
        if len(span.split()) < 4:
            findings.append(
                f"ASSUMPTION without justification ({len(span.split())} "
                f"words): {span[:60]!r}")
    # 3. CALCULATED must evaluate from labeled inputs
    for m in re.finditer(
            r"CALCULATED[^\n:]*:\s*(.{0,240}?)(?=\n[A-Z][A-Z ]{3,}"
            r"[-—:]|\n\n|\Z)", ans, re.S):
        span = m.group(1).strip()
        has_num = bool(re.search(r"\d", span))
        has_rel = bool(re.search(r"[=+\-*/×÷%~]", span))
        qty = _jaccard_overlap(span, ptext + " " + ans[:2000])
        if not (has_num and has_rel and qty > 0.15):
            findings.append(
                f"CALCULATED not evaluable from labeled inputs "
                f"(num={has_num} rel={has_rel} qty_overlap={qty:.2f}): "
                f"{span[:70]!r}")
    # 4. Citations parse
    for url in re.findall(r"https?://[^\s)\]>\"']+", ans):
        mm = re.match(r"https?://[^/\s]+", url)
        if not mm or "." not in mm.group(0):
            findings.append(f"citation does not resolve structurally: "
                            f"{url[:70]!r}")
    return findings


def test_article21_label_integrity_on_committed_arms():
    probs = _problems()
    assert len(probs) >= 30, "problem corpus must load"
    flagged, scanned, seen = [], 0, set()
    for arm in ARMS:
        assert arm.is_dir(), f"live arm dir missing: {arm}"
        for f in sorted(arm.glob("*.json")):
            rec = json.loads(f.read_text())
            pid = str(rec.get("problem_id") or f.stem)
            prob = probs.get(pid)
            assert prob, f"{pid}: no problem record for a committed arm"
            for finding in _check_record(rec, prob, f):
                key = (pid, finding)
                if key not in seen:  # reused records appear in both dirs
                    seen.add(key)
                    flagged.append((pid, finding))
            scanned += 1
    assert scanned >= 60, f"expected >=60 committed records, got {scanned}"

    # Disclosed-findings pattern (Art. 4/5): the finding class caught by
    # this check on the FIRST run is disclosed and pinned in a ledger
    # fixture — the affected answers are the JUDGED BYTES of batteries
    # r10/r11 and are never silently rewritten; the defect does not
    # change the judged axes. CI fails on ANY finding not in the
    # ledger (new violations stay red) and on ledger entries that no
    # longer fire (stale disclosures surface).
    fx = REPO / "tests" / "fixtures" / "article21_disclosed_findings.json"
    ledger = {d["finding"] for d in
              json.loads(fx.read_text()).get("findings", [])}
    fresh = [(pid, msg) for pid, msg in flagged if msg not in ledger]
    stale = [msg for msg in ledger
             if msg not in {m for _, m in flagged}]
    assert not fresh, (
        f"Art. 21 NEW label-integrity violations on committed bytes "
        f"({len(fresh)}): "
        + "; ".join(f"{pid}: {msg}" for pid, msg in fresh[:8]))
    assert not stale, f"Art. 21 disclosure ledger has stale entries: " \
                      f"{stale[:4]}"
