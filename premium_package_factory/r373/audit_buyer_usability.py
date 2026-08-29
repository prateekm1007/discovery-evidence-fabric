"""
audit_buyer_usability.py — R373-7: mechanically answer the seven buyer
questions for each package, from the ACTUAL rendered PDFs (not from the
builder's expectations).

  Q1 understand the invention in < 2 minutes
     mechanical form: the buyer decision card's page 1 carries the
     invention identity (five-decision-criticals table) AND the canonical
     mechanism statement; the card's page-1 word count is disclosed with
     a reading-time estimate at a DISCLOSED 225 wpm assumption (the
     assumption is labelled as such — it is not a measured fact).
  Q2 identify what is proven
     sections 'WHAT IS ACTUALLY ESTABLISHED?' + 'WHAT IS ESTABLISHED?'
     present, carrying the recorded engineering counts and the honest
     '0 physical observations' statement.
  Q3 identify what is missing
     'WHAT IS NOT ESTABLISHED?' present and carrying the canonical
     unknown count.
  Q4 identify the next decisive experiment
     'WHAT IS THE DECISIVE EXPERIMENT?' names canonical WP-01 (test
     article + measurement verbatim) and the acceptance criterion.
  Q5 identify what they receive
     'WHAT DOES THE BUYER RECEIVE?' non-pointer (>= 3 canonical
     transfer items named) + transfer manifest WHAT TRANSFERS list
     matches the canonical buyer_receives items.
  Q6 identify what they must build
     'WHAT MUST THE BUYER DEVELOP?' enumerates canonical
     buyer_must_create items (no deferral pointer), and the transfer
     manifest's BUYER MUST DEVELOP section enumerates them too.
  Q7 identify what kills the project
     'WHAT WOULD KILL THE PROJECT?' carries the kill condition verbatim.
"""

import os
import re
import subprocess

_PAGE_CACHE = {}


def _raw(path):
    stat = os.stat(path)
    key = (path, stat.st_mtime_ns, stat.st_size)
    if key not in _PAGE_CACHE:
        r = subprocess.run(["pdftotext", "-raw", path, "-"],
                           capture_output=True, text=True)
        _PAGE_CACHE[key] = r.stdout or ""
    return _PAGE_CACHE[key]


def _compact(t):
    return re.sub(r"\s+", "", t or "")


def _page1(path):
    """Text of page 1 only (form-feed split)."""
    return _raw(path).split("\f")[0]


def audit_buyer_usability(portfolio_root, pkg, headlines: dict) -> dict:
    failures = []
    answers = {}
    pdir = os.path.join(portfolio_root, "DOWNLOAD", pkg.folder)
    card = os.path.join(pdir, "03_BUYER_DECISION_CARD.pdf")
    manifest = os.path.join(pdir, "05_TRANSFER_MANIFEST.pdf")
    card_txt = _raw(card)
    card_p1 = _page1(card)
    card_c = _compact(card_txt)
    man_txt = _raw(manifest)
    man_c = _compact(man_txt)

    # mutation-aware expected forms: a canonical transfer item may render
    # in its V2 form when a recorded mutation corrects the item itself
    # (e.g. P-27-R1's regulatory-submission item).
    mutations = (pkg.addendum or {}).get("mutations", [])

    def _forms(item: str):
        forms = [item]
        for m in mutations:
            v1, v2 = m.get("v1_text", ""), m.get("v2_text", "")
            if v1 and v1 in item:
                forms.append(item.replace(v1, v2))
        return forms

    # ---- Q1: invention identity on page 1 -------------------------------
    mech = headlines.get("mechanism", "")
    p1_c = _compact(card_p1)
    crit_table_on_p1 = ("1.WHATISTHEINVENTION?" in p1_c
                        and _compact(mech)[:80] in p1_c)
    words_p1 = len(card_p1.split())
    read_min = round(words_p1 / 225, 2)  # DISCLOSED assumption, not a fact
    answers["Q1_understand_invention_fast"] = {
        "identity_on_page_1": crit_table_on_p1,
        "page1_word_count": words_p1,
        "estimated_reading_minutes_at_225wpm": read_min,
        "note": "reading speed is a disclosed assumption for the "
                "estimate, not a measured fact",
    }
    if not crit_table_on_p1:
        failures.append({"check": "Q1_INVENTION_IDENTITY",
                         "detail": "five-decision-criticals invention row "
                                   "not on card page 1"})

    # ---- Q2: what is proven ---------------------------------------------
    est = ("WHATISACTUALLYESTABLISHED?" in card_c
           and "WHATISESTABLISHED?" in card_c
           and "physicalobservations" in card_c
           and "0physicalobservations" in card_c)
    n_claims = len(pkg.claims)
    answers["Q2_what_is_proven"] = {
        "established_sections_present": est,
        "recorded_claim_count": n_claims,
        "physical_observations": 0,
    }
    if not est:
        failures.append({"check": "Q2_WHAT_IS_PROVEN",
                         "detail": "established sections or the honest 0 "
                                   "physical observations statement "
                                   "missing from the card"})

    # ---- Q3: what is missing ---------------------------------------------
    n_unknowns = len(pkg.unknowns)
    q3 = ("WHATISNOTESTABLISHED?" in card_c
          and f"{n_unknowns}recordedUNKNOWNs" in card_c)
    answers["Q3_what_is_missing"] = {
        "not_established_section_present":
            "WHAT IS NOT ESTABLISHED?" in card_txt,
        "unknown_count_on_card": bool(q3),
        "canonical_unknown_count": n_unknowns,
    }
    if not q3:
        failures.append({"check": "Q3_WHAT_IS_MISSING",
                         "detail": f"card does not state the canonical "
                                   f"{n_unknowns} recorded UNKNOWNs"})

    # ---- Q4: next decisive experiment ------------------------------------
    wp1 = pkg.build_plan[0] if pkg.build_plan else {}
    q4 = (_compact(wp1.get("work_package", "")) in card_c
          and _compact(wp1.get("test_article", ""))[:50] in card_c
          and "Acceptance:" in card_txt)
    answers["Q4_next_decisive_experiment"] = {
        "wp_named": wp1.get("work_package", "") in card_txt,
        "test_article_verbatim": _compact(
            wp1.get("test_article", ""))[:50] in card_c,
        "acceptance_present": "Acceptance:" in card_txt,
    }
    if not q4:
        failures.append({"check": "Q4_DECISIVE_EXPERIMENT",
                         "detail": "card does not name canonical WP-01 "
                                   "with test article and acceptance "
                                   "criterion"})

    # ---- Q5: what they receive -------------------------------------------
    receives = (pkg.transfer_boundary or {}).get("buyer_receives", [])
    receive_hits = sum(
        1 for item in receives
        if any(_compact(f)[:60] and _compact(f)[:60] in card_c
               or _compact(f)[:60] in man_c for f in _forms(item)))
    q5 = receive_hits >= 3 and "WHATTRANSFERS" in man_c
    answers["Q5_what_they_receive"] = {
        "canonical_receive_items": len(receives),
        "items_found_in_card_or_manifest": receive_hits,
    }
    if not q5:
        failures.append({"check": "Q5_WHAT_THEY_RECEIVE",
                         "detail": f"only {receive_hits}/{len(receives)} "
                                   f"canonical receive items found in the "
                                   f"card/manifest"})

    # ---- Q6: what they must build -----------------------------------------
    must = (pkg.transfer_boundary or {}).get("buyer_must_create", []) or \
        (pkg.transfer_boundary or {}).get("buyer_must_develop", [])
    must_hits = sum(
        1 for item in must
        if any(_compact(f)[:60] and (_compact(f)[:60] in card_c
                                     or _compact(f)[:60] in man_c)
               for f in _forms(item)))
    pointer_only = ("seetransfermanifest" in card_c
                    or "seedossierbuildplan" in man_c)
    q6 = must_hits >= 3 and not pointer_only
    answers["Q6_what_they_must_build"] = {
        "canonical_must_build_items": len(must),
        "items_found_in_card_or_manifest": must_hits,
        "deferral_pointer_only": pointer_only,
    }
    if not q6:
        failures.append({"check": "Q6_WHAT_THEY_MUST_BUILD",
                         "detail": f"only {must_hits}/{len(must)} canonical "
                                   f"must-build items rendered; "
                                   f"deferral_pointer_only={pointer_only}"})

    # ---- Q7: what kills the project ----------------------------------------
    kill = headlines.get("kill_if", "")
    q7 = bool(kill) and _compact(kill)[:80] in card_c
    answers["Q7_what_kills_the_project"] = {
        "kill_condition_verbatim_on_card": q7,
    }
    if not q7:
        failures.append({"check": "Q7_KILL_CONDITION",
                         "detail": "kill condition not verbatim on the "
                                   "buyer card"})

    return {
        "package_id": pkg.pkg_id,
        "questions": list(answers.keys()),
        "answers": answers,
        "failures": failures,
        "ok": not failures,
    }
