"""A2 verify — evidence verification.

R470 rationale (the 2026-09-15 external re-audit's named last promotion
gate): the evidence-span citation contract — a mechanism must carry a
span that appears VERBATIM in the evidence abstract it cites. Free-tier
proposers frequently ground their mechanism in the abstract but fail to
emit the verbatim quote (or cite the wrong rotation paper), which the
R452 fix honestly typed as INFRASTRUCTURE_CAPABILITY (never a
scientific rejection) — the run then ended unpromoted. The audit's
sanctioned closure path is a VERIFIER-ASSIST pass, implemented here:

  A. SOURCE-BOUND VERIFICATION (bug fix): the mechanism span is checked
     against the candidate's OWN cited source first (by source_id),
     then every evidence abstract — the pre-R470 code checked
     evidence[0] only, mis-firing whenever synthesis rotation served a
     later paper.
  B. VERIFIER-ASSIST (runs only when a span issue fired):
     1. DETERMINISTIC — the longest word-aligned verbatim overlap
        between the mechanism text and each abstract (>= 80 chars);
        the abstract-side substring is adopted, rebinding the citation
        to the matching source when it differs (recorded, never
        silent).
     2. LLM QUOTE — one recorded call asking for the single verbatim
        supporting sentence; the returned quote is HARD-CHECKED
        verbatim before adoption (a non-verbatim or refused quote is
        assist-failed).
  C. The verbatim requirement is UNCHANGED by the assist: an adopted
     span is always evidence text, never a paraphrase. The extraction
     provenance is always disclosed ("PROPOSER_CITED" when the
     proposer's own span passed untouched; the assist method name when
     the verifier located the span). When both assist methods fail,
     the honest typed failure stands exactly as before — classify.py's
     INFRASTRUCTURE_CAPABILITY path decides downstream.
"""
from __future__ import annotations
import re

_WS = re.compile(r"\s+")

SPAN_ISSUES = frozenset({
    "missing_source_span", "mechanism_span_not_verbatim",
    "missing_mechanism_span",
})


def _norm(text: str) -> str:
    """Collapse runs of whitespace (spaces/newlines) to one space."""
    return _WS.sub(" ", text or "").strip()


def _clean_span(span: str) -> str:
    """Strip surrounding whitespace and one or more layers of quotes."""
    s = (span or "").strip()
    for _ in range(3):
        nxt = s.strip('"').strip("'").strip()
        if nxt == s:
            break
        s = nxt
    return s


def _verbatim_in_abstract(span: str, abstract: str) -> bool:
    """Whitespace-normalized membership, case-insensitive as fallback."""
    if not span or not abstract:
        return False
    ns, na = _norm(span), _norm(abstract)
    if not ns:
        return False
    if ns in na:
        return True
    return ns.lower() in na.lower()


#: terminal punctuation an LLM quote may add/drop at its end (a sentence
#: quote ending '.' where the abstract continues ','). Interior text is
#: NEVER touched — the span must still be a contiguous verbatim run.
_TERMINAL_PUNCT = ".,;:!?\u201d\u2019\"'"


def _span_verbatim(span: str, abstract: str) -> bool:
    """Span membership with TERMINAL-punctuation tolerance only: the
    span must be a contiguous verbatim substring of the abstract after
    whitespace normalization (case-insensitive fallback); if that
    fails, one retry with the span's trailing punctuation stripped.
    The R468 production specimen (mechanism_span_not_verbatim on an
    otherwise-quote span) included exactly this class — a terminal
    period is not a paraphrase, and the strict interior check still
    holds (Art. XXV: verbatim means verbatim, not punctuation-locked)."""
    if _verbatim_in_abstract(span, abstract):
        return True
    stripped = (span or "").rstrip(_TERMINAL_PUNCT).strip()
    if stripped and len(stripped) >= 10:
        return _verbatim_in_abstract(stripped, abstract)
    return False


def _resolve_source(evidence: list, cited_id: str):
    """Index of the evidence item matching the cited source_id, else None."""
    if not cited_id or not evidence:
        return None
    for idx, item in enumerate(evidence):
        if item.get("id") == cited_id:
            return idx
    return None


def _word_tokens(text: str) -> list:
    """(word, start, end) for each whitespace-separated token."""
    return [(m.group(0), m.start(), m.end())
            for m in re.finditer(r"\S+", text or "")]


def _longest_verbatim_overlap(mechanism: str, abstract: str):
    """Longest word-aligned verbatim overlap (case-insensitive).

    Returns the abstract-side substring of the longest run of
    consecutive words that matches the mechanism word-for-word, or None
    when no words match. Classic DP over token lists (mechanisms are
    ~50 tokens, abstracts ~200 — trivial cost).
    """
    mt = _word_tokens(mechanism)
    at = _word_tokens(abstract)
    n, m = len(mt), len(at)
    if n == 0 or m == 0:
        return None
    mw = [t[0].lower() for t in mt]
    aw = [t[0].lower() for t in at]
    prev = [0] * (m + 1)
    best_len = 0
    best_abs_end = 0  # exclusive token index into at
    for i in range(1, n + 1):
        cur = [0] * (m + 1)
        mi = mw[i - 1]
        for j in range(1, m + 1):
            if mi == aw[j - 1]:
                v = prev[j - 1] + 1
                cur[j] = v
                if v > best_len:
                    best_len = v
                    best_abs_end = j
        prev = cur
    if best_len == 0:
        return None
    start_tok = at[best_abs_end - best_len]
    end_tok = at[best_abs_end - 1]
    return abstract[start_tok[1]:end_tok[2]]


def _rebind_source(src: dict, item: dict, adopted_span: str) -> None:
    """Rebind source_evidence onto the matching evidence item (in place).

    Untouched keys (e.g. retrieval_timestamp) survive; missing item
    fields fall back so the span contract stays honest.
    """
    src["source_id"] = item.get("id", "")
    src["source_hash"] = (item.get("content_hash")
                          or item.get("source_hash") or "")
    src["source_title"] = item.get("title") or item.get("source_title") or ""
    src["source_span"] = item.get("abstract", "")[:2000] or adopted_span


def _llm_quote_assist(mechanism: str, abstract: str):
    """Assist 2: ask the LLM to quote a supporting sentence, then
    HARD-CHECK the quote verbatim. Returns (quote, provider_meta,
    failure_reason); quote is non-None only when it verified. Never
    raises; a missing/unavailable transport degrades to assist-failed.
    """
    try:
        import discovery_fabric.a2.synthesize as _synth
        from discovery_fabric.a2.synthesize import llm_chat
    except Exception as exc:  # noqa: BLE001 — env-safe degradation
        return None, None, f"llm_chat unavailable: {str(exc)[:160]}"

    system = "You are a strict evidence auditor."
    prompt = (
        f"Mechanism claim:\n{mechanism}\n\n"
        f"Abstract:\n{abstract}\n\n"
        "Quote the single verbatim sentence from the ABSTRACT that most "
        "directly supports the mechanism claim. Output ONLY the quote, or "
        "NO_SPAN if no sentence supports it."
    )
    try:
        # CTO correction of the engineer draft: llm_chat's signature is
        # (prompt, system="") — prompt FIRST (the draft inverted them).
        reply = llm_chat(prompt, system=system)
    except Exception as exc:  # noqa: BLE001 — env-safe degradation
        return None, None, f"llm_chat call failed: {str(exc)[:160]}"

    meta = getattr(_synth, "_LAST_PROVIDER_META", None)
    quote = (reply or "").strip().strip('"').strip()
    low = quote.lower()
    if not quote or quote.upper() == "NO_SPAN":
        return None, meta, "llm returned NO_SPAN or empty"
    if low.startswith(("i can't", "i cannot", "i'm not able", "i'm sorry",
                       "i apologize", "sorry", "as an ai")):
        return None, meta, "llm refused to quote"
    if _verbatim_in_abstract(quote, abstract):
        return quote, meta, None
    # terminal-punctuation tolerance: adopt the stripped verbatim run
    stripped = quote.rstrip(_TERMINAL_PUNCT).strip()
    if stripped and len(stripped) >= 10 \
            and _verbatim_in_abstract(stripped, abstract):
        return stripped, meta, None
    return None, meta, "llm quote not verbatim in abstract"


def verify_evidence(candidate: dict, evidence: list[dict]) -> dict:
    """Step 4: Verify that every assertion has source_id + source_hash +
    exact span. Source-bound verification first (the candidate's own
    cited source, then all evidence), then the verifier-assist pass when
    a span issue fired. Mutates the candidate in place when an assist
    adopts/rebinds a span, and records the assist provenance in the
    result (R470).
    """
    evidence = evidence or []
    issues = []
    src = candidate.get("source_evidence") or {}
    # CTO correction of the engineer draft: when the candidate carries NO
    # source_evidence dict (the mechanism_space path), attach ours so
    # assist rebinds propagate to the candidate downstream.
    if "source_evidence" not in candidate:
        candidate["source_evidence"] = src
    cited_id = src.get("source_id", "")

    if not cited_id:
        issues.append("missing_source_id")
    if not src.get("source_hash"):
        issues.append("missing_source_hash")

    span = src.get("source_span", "")
    if not span or len(span) < 10:
        issues.append("missing_source_span")

    # R470 parallel-line reconciliation: the sibling R470-C2 line
    # independently fixed the evidence[0] mis-alignment (their R469
    # source-alignment note — the span verified against the candidate's
    # OWN claimed source). This rewrite carries that alignment forward
    # in _resolve_source + the scan-all fallback, and adds the
    # verifier-assist pass (the audit's sanctioned P0-1 closure path).
    mech_span_raw = candidate.get("mechanism_source_span", "")
    mech_span_clean = _clean_span(mech_span_raw)

    span_issue_fired = "missing_source_span" in issues
    verbatim_ok = False
    match_index = None

    if not mech_span_clean or mech_span_raw == "NO_SPAN":
        issues.append("missing_mechanism_span")
        span_issue_fired = True
    else:
        # R470 parallel-line reconciliation (the sibling's span
        # contract, tests/test_r469_span_contract.py): the span is
        # verified against the CITED source ONLY — a span verbatim in a
        # DIFFERENT paper than the one claimed is a MISATTRIBUTION and
        # fails byte-exact here (this line's earlier scan-all fallback
        # was too lenient and is removed). The honest recovery for a
        # grounded-but-misattributed candidate is the verifier-assist's
        # REBIND below — adopted only with the citation rebound to the
        # matching source and the whole recovery on the record.
        own_idx = _resolve_source(evidence, cited_id)
        if own_idx is not None and _span_verbatim(
                mech_span_clean, evidence[own_idx].get("abstract", "")):
            verbatim_ok = True
            match_index = own_idx
        if not verbatim_ok:
            issues.append("mechanism_span_not_verbatim")
            span_issue_fired = True

    # ------------------------------------------------------------------
    # R470: the verifier-assist pass (only when a span issue fired).
    # ------------------------------------------------------------------
    assist_record = None
    extraction = "PROPOSER_CITED"
    attempted = []
    rebound = False
    rebound_index = None
    failure_reason = ""

    if span_issue_fired:
        # NOTE (the parallel-line reconciliation): a MISATTRIBUTED span
        # (verbatim in a different paper than the one cited) is NOT
        # repaired here — the sibling R470-C2 contract keeps verify a
        # pure gate for citation integrity (the claimant-side
        # repair_mechanism_span owns that recovery before verify runs).
        # The assist below adopts a span ONLY when the MECHANISM itself
        # is verbatim-grounded in real evidence (the audit's sanctioned
        # closure path), and every adoption is recorded.

        # --- Assist 1: deterministic longest verbatim overlap -----------
        attempted.append("LONGEST_VERBATIM_OVERLAP")
        best = None  # (chars, index, abstract-side substring)
        mechanism = candidate.get("mechanism", "")
        for idx, item in enumerate(evidence):
            abstract = item.get("abstract", "")
            if not abstract:
                continue
            sub = _longest_verbatim_overlap(mechanism, abstract)
            if sub and (best is None or len(sub) > best[0]):
                best = (len(sub), idx, sub)

        if best is not None and best[0] >= 80:
            adopted = best[2]
            match_index = best[1]
            item = evidence[best[1]]
            if item.get("id") and item.get("id") != cited_id:
                rebound = True
                rebound_index = best[1]
                _rebind_source(src, item, adopted)
            elif not src.get("source_span") or \
                    len(src.get("source_span", "")) < 10:
                src["source_span"] = adopted
            candidate["mechanism_source_span"] = adopted
            extraction = "LONGEST_VERBATIM_OVERLAP"
            assist_record = {
                "method": "LONGEST_VERBATIM_OVERLAP",
                "attempted": list(attempted),
                "success": True,
                "source_index": best[1],
                "rebound": rebound,
                "overlap_chars": best[0],
                "span_text": adopted[:300],
                "note": ("span located by the verifier (deterministic "
                         "overlap of the MECHANISM text against the "
                         "evidence); the proposer did not emit a "
                         "verbatim span itself"),
            }
        else:
            found = best[0] if best else 0
            failure_reason = (f"longest verbatim overlap {found} chars "
                              "< 80")

        # --- Assist 2: LLM quote auditor (only if assist 1 failed) ------
        if assist_record is None:
            if rebound_index is not None:
                abs_idx = rebound_index
            else:
                abs_idx = _resolve_source(evidence, cited_id)
                if abs_idx is None and evidence:
                    abs_idx = 0
            if abs_idx is None:
                failure_reason = ("no source abstract available for the "
                                  "llm assist")
            else:
                attempted.append("LLM_QUOTE_VERIFIED_VERBATIM")
                abstract_text = evidence[abs_idx].get("abstract", "")
                quote, meta, reason = _llm_quote_assist(
                    candidate.get("mechanism", ""), abstract_text)
                if quote is not None:
                    if not src.get("source_span") or \
                            len(src.get("source_span", "")) < 10:
                        src["source_span"] = quote
                    candidate["mechanism_source_span"] = quote
                    match_index = abs_idx
                    extraction = "LLM_QUOTE_VERIFIED_VERBATIM"
                    assist_record = {
                        "method": "LLM_QUOTE_VERIFIED_VERBATIM",
                        "attempted": list(attempted),
                        "success": True,
                        "source_index": abs_idx,
                        "rebound": False,
                        "llm_model": (meta or {}).get("model"),
                        "llm_provider": (meta or {}).get("provider"),
                        "span_text": quote[:300],
                        "note": ("deterministic overlap failed; span "
                                 "located by the verifier's LLM quote "
                                 "auditor and hard-checked verbatim in "
                                 "the abstract; the proposer did not "
                                 "emit a verbatim span itself"),
                    }
                else:
                    failure_reason = reason or "llm quote assist failed"

        # --- Close out the assist ----------------------------------------
        if assist_record is not None and assist_record.get("success"):
            issues = [i for i in issues if i not in SPAN_ISSUES]
            if rebound and rebound_index is not None:
                item = evidence[rebound_index]
                if item.get("id") and item.get("content_hash"):
                    issues = [i for i in issues if i not in (
                        "missing_source_id", "missing_source_hash")]
            candidate["mechanism_span_extraction"] = extraction
        else:
            assist_record = {
                "method": attempted[-1] if attempted else "NONE",
                "attempted": list(attempted),
                "success": False,
                "source_index": None,
                "rebound": False,
                "failure_reason": failure_reason[:200],
                "note": ("verifier assist failed to locate a verbatim "
                         "span; the proposer's span issue stands"),
            }
            extraction = "NONE"

    if assist_record is not None and assist_record.get("success"):
        span_present = True
        mechanism_span_verbatim = True
    else:
        span_present = bool(span)
        mechanism_span_verbatim = verbatim_ok

    result = {
        "verified": len(issues) == 0,
        "evidence_class": "SUPPORTED" if not issues else "UNSUPPORTED",
        "issues": issues,
        "source_id": src.get("source_id", ""),
        "source_hash": src.get("source_hash", ""),
        "span_present": span_present,
        "mechanism_span_verbatim": mechanism_span_verbatim,
        "verifier_assist": assist_record,
        "span_extraction": extraction,
        "span_match_index": match_index,
    }
    print(f"  [verify] verified={result['verified']} "
          f"class={result['evidence_class']} issues={issues}")
    return result
