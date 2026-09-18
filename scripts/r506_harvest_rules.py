#!/usr/bin/env python3
"""
R506 HARVEST RULES — v1.0.0 (pre-registered BEFORE any battery terminal harvest)

Attaches the two audit-mandated rule sections to R506/YIELD_MEASUREMENT.json
WITHOUT touching the frozen instrument or the funnel numbers:

  1. SEED_CONTAMINATION_CREDIT_EXCLUSION (audit correction 2)
     nhtsa_complaints is a LIVE connector (failure_universe.py:66-167) and the
     6 battery seed ODIs are retrievable by the engine via complaintsByVehicle
     for the battery's own makes/years. Rule: any battery seed record id
     (nhtsa_odi:{odi}) present in a run's EVIDENCE SET cannot credit
     verification or mechanism grounding. Per-run verdict:
       CLEAN                  — no seed-like item in the credited evidence set
       SELF-EVIDENCE-EXCLUDED — seed-like items present and EXCLUDED from
                                credit; the credited evidence survives the
                                exclusion (or no credit was at stake: the
                                run's measured evidence_verified is false)
       CONTAMINATED           — the credited evidence set collapses when the
                                seed-like items are removed AND the run's
                                measured evidence_verified is true: the run's
                                verification/mechanism grounding DEPENDED on
                                its own seed; credit is withheld (typed
                                credit_adjustment), funnel bytes untouched
     EVIDENCE SET (pre-registered definition): the union of $.evidence items,
     $.evidence_ids, and provenance.record_ids_by_source values across the
     run's envelope_*.json + candidate_envelope.json durable bytes.
     SEED-LIKE: a literal seed record id, OR an evidence item whose text
     carries a >=12-word verbatim span of any seed narrative (CONTENT_OVERLAP
     — catches re-identification without the record id). A full byte scan of
     every run file for the seed tokens is the disclosure net
     (seed_token_files_anywhere): appearances outside the credited evidence
     set are disclosed and do not change the verdict.
     On CONTAMINATED the funnel row keeps the instrument's measured bytes
     (the frozen instrument is NEVER edited — any edit is a new version per
     the freeze rule); the credit adjustment lives in this section.

  2. CLARIFICATION_BLINDNESS_AUDIT (audit correction 3, R484 precedent)
     The harvest carries per-run clarification Q&A pairs with byte-proof of
     no-new-content: each answer's bytes are compared against the run's OWN
     submitted problem bytes (problem.json user_text; the manifest verbatim
     summary as fallback). Per-run verdict:
       BLINDNESS_INTACT_VERBATIM_SUBSET        — every answered pair is an
                                                 exact byte subset of the
                                                 submitted problem bytes
       BLINDNESS_DOWNGRADED_NEW_CONTENT        — some answered pair introduces
                                                 bytes not present in the
                                                 submitted problem (typed per
                                                 pair, with the new-content
                                                 preview + sha)
       CLARIFICATION_BYTES_ABSENT_IN_DURABLE_RECORD — no Q&A bytes found for
                                                 the session (typed absence)

MERGE CONTRACT: this script ONLY ADDS the sections contamination_audit,
clarification_audit, harvest_rules. It asserts rows+aggregate are
byte-identical before writing and records the pre-merge file sha256
(pre_merge_sha256) inside the merged document. It self-attests against the
pre-registered R506/HARVEST_RULES.json script_sha256 and fails closed (exit 2)
on any mismatch — the rules are frozen; any edit is a new rules version.

Usage:
  python3 scripts/r506_harvest_rules.py [--measurement R506/YIELD_MEASUREMENT.json]
      [--rules R506/HARVEST_RULES.json] [--worktree /home/z/my-project/r506_durable]
      [--sessions <worktree>/sessions.json] [--out FILE] [--check-only]

Scope guard: Art. VII harness/pre-registration only — no engine change, no
scored-set change, no tuning of any kind; the battery stays valid.
"""

import argparse
import hashlib
import json
import os
import sys

RULES_ID = "r506_harvest_rules"
RULES_VERSION = "1.0.0"
MEASUREMENT_DEFAULT = "R506/YIELD_MEASUREMENT.json"
RULES_DEFAULT = "R506/HARVEST_RULES.json"
WORKTREE_DEFAULT = "/home/z/my-project/r506_durable"

CONTENT_NGRAM_WORDS = 12

CONTAMINATION_VERDICTS = ("CLEAN", "SELF-EVIDENCE-EXCLUDED", "CONTAMINATED")
CLARIFICATION_VERDICTS = (
    "BLINDNESS_INTACT_VERBATIM_SUBSET",
    "BLINDNESS_DOWNGRADED_NEW_CONTENT",
    "CLARIFICATION_BYTES_ABSENT_IN_DURABLE_RECORD",
)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:  # utf-8 ALWAYS (the R505 lesson)
        return json.load(f)


def norm_tokens(text):
    out = []
    cur = []
    for ch in (text or "").lower():
        if ch.isalnum():
            cur.append(ch)
        elif cur:
            out.append("".join(cur))
            cur = []
    if cur:
        out.append("".join(cur))
    return out


def ngrams(tokens, n):
    return {" ".join(tokens[i:i + n]) for i in range(len(tokens) - n + 1)}


def iter_run_files(run_dir):
    for root, _dirs, files in os.walk(run_dir):
        for name in sorted(files):
            yield os.path.join(root, name)


def scan_tokens(run_dir, tokens):
    """Full byte scan: token -> sorted list of relpaths containing it."""
    hits = {t: [] for t in tokens}
    for path in iter_run_files(run_dir):
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
        except OSError:
            continue
        rel = os.path.relpath(path, run_dir)
        for t in tokens:
            if t in text:
                hits[t].append(rel)
    return {t: sorted(v) for t, v in hits.items() if v}


def collect_evidence_set(run_dir):
    """The pre-registered evidence set: envelope_*.json + candidate_envelope.json
    -> list of items {id, file, text}; also the flat id set."""
    items, ids = [], set()
    if not os.path.isdir(run_dir):
        return items, ids
    for name in sorted(os.listdir(run_dir)):
        if not (name.startswith("envelope_") or name == "candidate_envelope.json"):
            continue
        if not name.endswith(".json"):
            continue
        path = os.path.join(run_dir, name)
        try:
            doc = load_json(path)
        except (json.JSONDecodeError, OSError):
            continue
        seen_ids = []
        ev = doc.get("evidence")
        if isinstance(ev, list):
            for it in ev:
                if not isinstance(it, dict):
                    continue
                eid = it.get("id") or it.get("source_id")
                text = json.dumps(it, ensure_ascii=False)
                if eid:
                    seen_ids.append(str(eid))
                items.append({"id": str(eid) if eid else None,
                              "file": name, "text": text})
        elif isinstance(ev, dict):
            # some layouts key evidence by id
            for eid, it in ev.items():
                seen_ids.append(str(eid))
                items.append({"id": str(eid), "file": name,
                              "text": json.dumps(it, ensure_ascii=False)})
        eids = doc.get("evidence_ids")
        if isinstance(eids, list):
            for eid in eids:
                if eid is not None:
                    seen_ids.append(str(eid))
        # provenance.record_ids_by_source values on any dict
        def walk(o):
            if isinstance(o, dict):
                prov = o.get("provenance")
                if isinstance(prov, dict):
                    rbys = prov.get("record_ids_by_source")
                    if isinstance(rbys, dict):
                        for v in rbys.values():
                            if v is not None:
                                seen_ids.append(str(v))
                for v in o.values():
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
        walk(doc)
        ids.update(seen_ids)
    return items, ids


def content_overlap_ids(items, seed_gram_sets):
    """Items whose text carries a >=CONTENT_NGRAM_WORDS-word verbatim span of
    any seed narrative."""
    hits = set()
    detail = []
    for it in items:
        toks = norm_tokens(it.get("text") or "")
        grams = ngrams(toks, CONTENT_NGRAM_WORDS)
        matched = set()
        for seed_id, gs in seed_gram_sets.items():
            inter = grams & gs
            if inter:
                matched.add(seed_id)
        if matched:
            hits.add(it.get("id"))
            detail.append({"id": it.get("id"), "file": it.get("file"),
                           "seed_ids_matched": sorted(matched)})
    return hits, detail


def new_content_preview(baseline, answer):
    """Longest prefix of `answer` present in `baseline`; return (prefix_len,
    remainder). Typed disclosure for downgraded pairs."""
    lo, hi = 0, len(answer)
    best = 0
    while lo <= hi:
        mid = (lo + hi) // 2
        if answer[:mid] and answer[:mid] in baseline:
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return best, answer[best:]


def contamination_for_run(run_dir, seeds, seed_gram_sets, ev_ok_measured,
                          ms_measured):
    if not os.path.isdir(run_dir):
        return {"verdict": None,
                "typed": "RUN_BYTES_ABSENT_ON_DURABLE_WORKTREE",
                "note": "mid-flight or not yet committed (Art. LXXIV: "
                        "observation, never a terminal verdict)"}
    tokens = [s["seed_record_id"] for s in seeds]
    token_hits = scan_tokens(run_dir, tokens)
    items, credited_ids = collect_evidence_set(run_dir)
    seed_literal_ids = {s["seed_record_id"] for s in seeds} & credited_ids
    ov_ids, ov_detail = content_overlap_ids(items, seed_gram_sets)
    seed_like_ids = {str(i) for i in (seed_literal_ids | ov_ids) if i}
    remaining = credited_ids - seed_like_ids if credited_ids else set()
    ev_set_size = len(credited_ids)

    if not seed_like_ids:
        verdict = "CLEAN"
        note = ("no seed record id and no >=%d-word seed-narrative span in the "
                "credited evidence set" % CONTENT_NGRAM_WORDS)
    else:
        if remaining:
            verdict = "SELF-EVIDENCE-EXCLUDED"
            note = ("seed-like item(s) present in the credited evidence set and "
                    "EXCLUDED from credit; credited evidence survives the "
                    "exclusion (n_remaining=%d)" % len(remaining))
        elif ev_ok_measured:
            verdict = "CONTAMINATED"
            note = ("credited evidence collapses to seed-like item(s) and the "
                    "run's measured evidence_verified is true: verification "
                    "depended on its own seed — credit withheld")
        else:
            verdict = "SELF-EVIDENCE-EXCLUDED"
            note = ("credited evidence collapses to seed-like item(s) but the "
                    "run's measured evidence_verified is false — no credit was "
                    "at stake; exclusion recorded")

    credit = {
        "evidence_verified_credited": bool(ev_ok_measured) and verdict != "CONTAMINATED",
        "mechanisms_found_credited": bool(ms_measured) and verdict != "CONTAMINATED",
        "basis": ("MEASURED_CREDIT_STANDS_WITH_EXCLUSION"
                  if verdict in ("CLEAN", "SELF-EVIDENCE-EXCLUDED")
                  else "SEED_DEPENDENT_CREDIT_WITHHELD_PER_PREREGISTERED_RULE"),
    }
    return {
        "verdict": verdict,
        "note": note,
        "seed_tokens_scanned": tokens,
        "seed_token_files_anywhere": token_hits,
        "evidence_set_size": ev_set_size,
        "seed_record_ids_in_evidence_set": sorted(seed_literal_ids),
        "content_overlap_items": ov_detail,
        "seed_like_item_ids": sorted(seed_like_ids),
        "credited_ids_remaining_after_exclusion": len(remaining),
        "credit_adjustment": credit,
        "evidence_set_definition": (
            "$.evidence + $.evidence_ids + provenance.record_ids_by_source "
            "across envelope_*.json + candidate_envelope.json (pre-registered)"),
    }


def clarification_for_run(run_dir, session, baseline_text, problem_fallback):
    if session is None and not run_dir:
        return {"verdict": "CLARIFICATION_BYTES_ABSENT_IN_DURABLE_RECORD",
                "note": "no session record and no run bytes"}
    q = (session or {}).get("clarification")
    a = (session or {}).get("clarification_answer")
    pairs = []
    base = baseline_text if baseline_text is not None else problem_fallback
    if base is None:
        return {"verdict": "CLARIFICATION_BYTES_ABSENT_IN_DURABLE_RECORD",
                "note": "no Q&A bytes and no submitted-problem baseline bytes"}
    qlist = q if isinstance(q, list) else ([q] if isinstance(q, dict) else [])
    alist = a if isinstance(a, list) else ([a] if isinstance(a, dict) else [])
    if not qlist and not alist:
        return {"verdict": "CLARIFICATION_BYTES_ABSENT_IN_DURABLE_RECORD",
                "note": "session record carries no clarification bytes"}
    n_answered = 0
    for i in range(max(len(qlist), len(alist))):
        qd = qlist[i] if i < len(qlist) else {}
        ad = alist[i] if i < len(alist) else {}
        field = qd.get("field") or ad.get("field")
        question = qd.get("question")
        answer = ad.get("answer")
        pair = {
            "field": field,
            "question_sha256": (hashlib.sha256(
                (question or "").encode("utf-8")).hexdigest()[:16]
                if question else None),
            "answer_sha256": (hashlib.sha256(
                (answer or "").encode("utf-8")).hexdigest()
                if isinstance(answer, str) else None),
            "provenance": ad.get("provenance"),
            "applied_at": ad.get("applied_at"),
            "consumed_at": ad.get("consumed_at"),
            "merged_into": ad.get("merged_into"),
        }
        if isinstance(answer, str) and answer:
            n_answered += 1
            prefix_len, remainder = new_content_preview(base, answer)
            pair["answer_is_verbatim_subset_of_submitted_problem"] = (
                remainder == "" and prefix_len == len(answer))
            pair["submitted_bytes_overlap_chars"] = prefix_len
            pair["new_content_chars"] = len(remainder)
            if remainder:
                pair["new_content_preview"] = remainder[:160]
        else:
            pair["answer_is_verbatim_subset_of_submitted_problem"] = None
            pair["unanswered"] = True
        pairs.append(pair)
    downgraded = [p for p in pairs
                  if p.get("answer_is_verbatim_subset_of_submitted_problem")
                  is False]
    if downgraded:
        verdict = "BLINDNESS_DOWNGRADED_NEW_CONTENT"
        note = ("answer(s) for field(s) %s introduce bytes absent from the "
                "submitted problem — blindness explicitly downgraded per the "
                "pre-registered rule"
                % ",".join(str(p.get("field")) for p in downgraded))
    else:
        verdict = "BLINDNESS_INTACT_VERBATIM_SUBSET"
        note = ("every answered pair is an exact byte subset of the run's own "
                "submitted problem bytes (R484 precedent, byte-proof attached)")
    return {"verdict": verdict, "note": note, "pairs": pairs,
            "n_pairs": len(pairs), "n_answered": n_answered}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--measurement", default=MEASUREMENT_DEFAULT)
    ap.add_argument("--rules", default=RULES_DEFAULT)
    ap.add_argument("--worktree", default=WORKTREE_DEFAULT)
    ap.add_argument("--sessions", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--check-only", action="store_true",
                    help="compute verdicts; write nothing (observer mode)")
    args = ap.parse_args()

    rules_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "..", args.rules) if not os.path.exists(args.rules) \
        else args.rules
    rules_path = os.path.abspath(rules_path)

    # fail-closed self-attestation against the pre-registered rules
    if not os.path.exists(rules_path):
        print(f"FAIL-CLOSED: rules pre-registration absent: {rules_path}")
        return 2
    rules = load_json(rules_path)
    self_sha = sha256_file(os.path.abspath(__file__))
    if rules.get("script_sha256") != self_sha:
        print("FAIL-CLOSED: script sha mismatch vs pre-registered "
              f"{RULES_ID} ({rules.get('script_sha256', '')[:16]}… != "
              f"{self_sha[:16]}…) — the rules are frozen; any edit is a new "
              "rules version")
        return 2
    if rules.get("rules_id") != RULES_ID or rules.get("rules_version") != RULES_VERSION:
        print("FAIL-CLOSED: rules id/version mismatch")
        return 2

    meas_path = os.path.abspath(args.measurement)
    if not os.path.exists(meas_path):
        print(f"FAIL-CLOSED: measurement absent (harvest first): {meas_path}")
        return 2
    pre_merge_sha = sha256_file(meas_path)
    measurement = load_json(meas_path)

    sessions_path = args.sessions or os.path.join(args.worktree, "sessions.json")
    sessions = {}
    if os.path.exists(sessions_path):
        try:
            sessions = {s.get("session_id"): s
                        for s in load_json(sessions_path).get("sessions", [])
                        if isinstance(s, dict)}
        except (json.JSONDecodeError, OSError):
            sessions = {}

    seeds = rules["seeds"]
    seed_gram_sets = {}
    for s in seeds:
        grams = ngrams(norm_tokens(s.get("narrative_text") or ""),
                       CONTENT_NGRAM_WORDS)
        seed_gram_sets[s["seed_record_id"]] = grams

    cont_runs, clar_runs = {}, {}
    for row in measurement.get("rows", []):
        idx = row.get("problem_index")
        sid = row.get("session_id")
        slug = row.get("run_slug")
        inner = row.get("row") or {}
        label = f"problem_{idx}_{sid}"
        run_dir = os.path.join(args.worktree, "runs", slug) if slug else None

        ev_ok = bool((inner.get("evidence_verified") or {}).get("reached"))
        ms_ok = bool((inner.get("mechanisms_found") or {}).get("reached"))
        if run_dir:
            cont = contamination_for_run(run_dir, seeds, seed_gram_sets,
                                         ev_ok, ms_ok)
        else:
            cont = {"verdict": None,
                    "typed": "RUN_BYTES_ABSENT_ON_DURABLE_WORKTREE",
                    "note": "no run_slug harvested yet (Art. LXXIV observation)"}
        cont_runs[label] = {"problem_index": idx, "session_id": sid,
                            "run_slug": slug,
                            "declared_family": row.get("declared_family"),
                            **cont}

        session = sessions.get(sid)
        baseline, problem_fallback = None, None
        if run_dir and os.path.isdir(run_dir):
            pj = os.path.join(run_dir, "problem.json")
            if os.path.exists(pj):
                try:
                    baseline = load_json(pj).get("user_text")
                except (json.JSONDecodeError, OSError):
                    baseline = None
        if baseline is None:
            problem_fallback = s_gram = None
            for s in seeds:
                if s.get("problem_index") == idx:
                    problem_fallback = s.get("narrative_text")
                    break
        clar_runs[label] = {"problem_index": idx, "session_id": sid,
                            "run_slug": slug,
                            **clarification_for_run(run_dir, session,
                                                    baseline, problem_fallback)}

    merged = dict(measurement)
    merged["contamination_audit"] = {
        "rules": f"{RULES_ID}/{RULES_VERSION}",
        "rules_sha256": rules.get("rules_sha256"),
        "script_sha256": self_sha,
        "pre_merge_sha256": pre_merge_sha,
        "rule": rules["contamination_rule"]["statement"],
        "verdict_vocabulary": list(CONTAMINATION_VERDICTS),
        "runs": cont_runs,
    }
    merged["clarification_audit"] = {
        "rules": f"{RULES_ID}/{RULES_VERSION}",
        "rules_sha256": rules.get("rules_sha256"),
        "script_sha256": self_sha,
        "pre_merge_sha256": pre_merge_sha,
        "rule": rules["clarification_audit_rule"]["statement"],
        "verdict_vocabulary": list(CLARIFICATION_VERDICTS),
        "runs": clar_runs,
    }
    merged["harvest_rules"] = {
        "rules_id": RULES_ID,
        "rules_version": RULES_VERSION,
        "rules_sha256": rules.get("rules_sha256"),
        "script_sha256": self_sha,
        "pre_merge_sha256": pre_merge_sha,
        "merge_contract": "adds_sections_only; rows+aggregate asserted "
                          "byte-identical before write; frozen instrument "
                          "never edited",
    }

    # the funnel is never touched: assert before write
    if json.dumps(measurement.get("rows"), sort_keys=True) != \
       json.dumps(merged.get("rows"), sort_keys=True) or \
       json.dumps(measurement.get("aggregate"), sort_keys=True) != \
       json.dumps(merged.get("aggregate"), sort_keys=True):
        print("FAIL-CLOSED: rows/aggregate mutated — refusing to write")
        return 2

    summary = {lbl: (v.get("verdict") or v.get("typed"))
               for lbl, v in cont_runs.items()}
    summary_clar = {lbl: (v.get("verdict") or v.get("typed"))
                    for lbl, v in clar_runs.items()}
    print("contamination verdicts:", json.dumps(summary))
    print("clarification verdicts:", json.dumps(summary_clar))

    if args.check_only:
        print("check-only: nothing written")
        return 0
    out_path = os.path.abspath(args.out) if args.out else meas_path
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print(f"attached harvest rules -> {out_path} "
          f"(pre_merge_sha256={pre_merge_sha[:16]}…)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
