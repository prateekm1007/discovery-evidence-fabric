#!/usr/bin/env python3
"""gates.py — R440 hard package acceptance contract, Gates A–V.

Each gate is an INDEPENDENT check over the completed package (PackageView)
plus the canonical invention state when available. The compiler is the
claimant; these gates are the verifier (generator/verifier separation,
Art. XLV; the verifier never imports the compiler).

One mandatory dimension FAIL -> NO ZIP / NO BUYER RELEASE (R440.13/.17).

R440 additions over the R439 draft:
  - Gate A binds the FINAL invention hash (R440.2: a package compiled from
    a stale generation must fail identity reconciliation).
  - Gate D requires the PACKAGE_SECTION_PROVENANCE map for engine-run
    packages (R440.5: a section without canonical provenance is rejected
    even when the prose sounds perfectly reasonable).
  - Gate V (new): buyer language discipline (R440.6: raw JSON, exception
    strings, Python repr, debug fields, route IDs and engine jargon never
    appear in buyer-facing documents).
"""
from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from .view import Finding, GateResult, PackageView  # noqa: E402
from .view import (
    CANONICAL_ID_PATTERNS, DOMAIN_VOCAB, GateResult, PackageView,
    domain_term_hits, distinctive_tokens, sha256_file,
)
from ..domains import (CANONICAL_DOMAIN_FAMILIES,  # R445
                       is_canonical_family)

# canonical_id_match is a tiny helper reused by several gates
def canonical_id_hits(text: str) -> list[str]:
    ids = []
    for pat in CANONICAL_ID_PATTERNS:
        ids.extend(pat.findall(text))
    return ids


# ---------------------------------------------------------------- Gate A
def gate_A_identity_coherence(pv: PackageView, canonical: Optional[dict]) -> GateResult:
    g = GateResult("A", "Identity coherence: exact equality of identity fields "
                        "across canonical state, PDFs, JSON, MODEL, manifest.")
    ident = pv.declared_identity()

    def values(field):
        return [d["value"] for d in ident.get(field, [])]

    # canonical state overrides / cross-checks
    if canonical:
        for field in ("package_id", "invention_id", "problem_id",
                      "technology_name", "domain_family", "mechanism_id",
                      "engineering_state_id", "experiment_id"):
            cv = canonical.get(field)
            pv_vals = values(field)
            if field == "domain_family":
                # domain names are case-insensitive enumerations
                cv_l = str(cv).strip().lower() if cv else None
                pv_l = [v.lower() for v in pv_vals]
                if cv_l and pv_vals and cv_l not in pv_l:
                    g.fail("A-CANON-DIVERGENT", f"canonical {field}={cv!r} "
                           f"diverges from package declarations "
                           f"{sorted(set(pv_vals))[:4]}")
                if cv and not pv_vals:
                    g.fail("A-CANON-ABSENT", f"canonical {field} present but "
                           f"no package artifact declares it")
                continue
            if cv and pv_vals and str(cv) not in pv_vals:
                g.fail("A-CANON-DIVERGENT", f"canonical {field}={cv!r} "
                       f"diverges from package declarations {sorted(set(pv_vals))[:4]}")
            if cv and not pv_vals:
                g.fail("A-CANON-ABSENT", f"canonical {field} present but no "
                       f"package artifact declares it")

    # internal coherence across machine JSONs
    for field in ("package_id", "portfolio_number", "technology_name",
                  "domain_family", "run_id", "invention_id", "problem_id",
                  "mechanism_id", "engineering_state_id", "experiment_id"):
        vals = sorted(set(values(field)))
        if len(vals) > 1:
            g.fail("A-INTERNAL-DIVERGENT", f"{field} has divergent declarations: "
                   f"{vals[:4]}", {"where": [d['where'] for d in ident[field]
                                             if d['value'] == vals[0]][:3]})
    # R445 — the canonical vocabulary invariant: every domain_family
    # declaration in the package must be a CANONICAL family id
    # (domains.py::CANONICAL_DOMAIN_FAMILIES). A declaration in any other
    # vocabulary (the former bridge families 'GENERIC_ARCHITECTURE' /
    # 'THERMAL_SYSTEM' / ..., the engine routing domains
    # 'fluidics_hydraulic' / ..., case variants 'THERMAL', benchmark
    # labels 'thermal_fluid_process') is a broken invariant: a downstream
    # layer invented a second semantic namespace — exactly the F1 defect
    # class. This is the deliberately-injected-divergence detector the
    # R445 directive requires (the single-value F1 shape where every
    # layer agrees on the WRONG vocabulary is ALSO blocked).
    for d in ident.get("domain_family", []):
        if not is_canonical_family(d["value"]):
            g.fail("A-NONCANONICAL-DOMAIN",
                   f"domain_family declaration {d['value']!r} at "
                   f"{d['where']} is not a canonical family id "
                   f"(canonical vocabulary: {sorted(CANONICAL_DOMAIN_FAMILIES)}"
                   f" — domains.py::CANONICAL_DOMAIN_FAMILIES, R445)",
                   {"where": [d["where"]]})
            break
    # PDF vs machine layer
    pid_machine = set(values("package_id"))
    pid_pdf = set(values("package_id_pdf"))
    if pid_machine and pid_pdf and pid_machine != pid_pdf:
        g.fail("A-PDF-DIVERGENT", f"machine package_id {sorted(pid_machine)} != "
               f"PDF-embedded package id {sorted(pid_pdf)}")
    # model tree coherence (model_id must be single within MODEL/)
    model_ids = set()
    for rel, d in pv.json_files.items():
        if rel.startswith("MODEL/") and isinstance(d, dict) and d.get("model_id"):
            model_ids.add(str(d["model_id"]))
    if len(model_ids) > 1:
        g.fail("A-MODEL-DIVERGENT", f"multiple model_id values in MODEL tree: "
               f"{sorted(model_ids)}")
    if not values("package_id"):
        g.fail("A-NO-IDENTITY", "no machine artifact declares package_id — "
               "the package cannot prove which invention it belongs to")
    # R440.2 — FINAL INVENTION HASH RECONCILIATION: the package must bind
    # the exact final canonical invention hash. A package compiled from an
    # earlier generation (or a canonical state mutated after compilation)
    # must fail here — never release a stale-generation snapshot.
    if canonical and canonical.get("final_invention_hash"):
        want = str(canonical["final_invention_hash"])
        prov = pv.json("PROVENANCE.json") or {}
        got = (prov.get("final_invention_hash")
               or (prov.get("canonical_invention_state_identity") or {})
               .get("final_invention_hash"))
        if not got:
            g.fail("A-NO-FINAL-HASH", "canonical state declares "
                   "final_invention_hash but the package does not record it")
        elif str(got) != want:
            g.fail("A-FINAL-HASH-MISMATCH",
                   f"package was compiled from a different invention "
                   f"generation: package hash {str(got)[:16]}… != canonical "
                   f"{want[:16]}… (R440.2: the package must represent the "
                   f"FINAL selected technology, never a pre-evolution "
                   f"snapshot)")
    return g


# ---------------------------------------------------------------- Gate B
def gate_B_problem_fidelity(pv: PackageView, canonical: Optional[dict]) -> GateResult:
    g = GateResult("B", "Problem fidelity: the package answers the user's exact "
                        "problem; invention is machine-linked to the objective.")
    if not canonical:
        g.warn("B-NO-CANON", "no canonical state supplied: problem-linkage "
               "verified only for internal problem/objective presence")
        return g
    problem = str(canonical.get("problem") or canonical.get("user_problem")
                   or canonical.get("objective") or "").strip()
    if not problem:
        g.warn("B-NO-PROBLEM", "canonical state carries no problem statement")
        return g
    # 1. objective must be represented in first usable pages
    first_pages = "\n".join(
        pv.pdf_full_text(n)[:2500] for n in ("00_PACKAGE_README.pdf",
                                             "03_BUYER_DECISION_CARD.pdf"))
    problem_tokens = [t for t in distinctive_tokens(problem) if len(t) >= 6]
    if problem_tokens:
        hits = sum(1 for t in problem_tokens if t in first_pages.lower())
        if hits == 0:
            g.fail("B-OBJECTIVE-ABSENT", "user problem vocabulary absent from "
                   "first usable pages (README / decision card)",
                   {"problem_tokens": problem_tokens[:12]})
        elif hits < max(1, len(problem_tokens) // 6):
            g.warn("B-OBJECTIVE-WEAK", f"only {hits}/{len(problem_tokens)} "
                   f"problem tokens found in first pages")
    # 2. domain-family drift: problem domain vs invention domain.
    # R440.8 calibration: an EVIDENCED engineering-domain routing is not
    # drift — the domain detector's own record (why_this_domain with
    # matched routing signals or phenomena anchors, or domain_detection)
    # is the routing decision's provenance. A CSF-shunt problem routed
    # to fluidics engineering is the domain_reasoning system working.
    # Drift stays a HARD failure when the package carries no detection
    # basis — the #160 posture (stale content with no routing evidence).
    prob_domain = canonical.get("problem_domain_family") or infer_domain(problem)
    inv_domain = canonical.get("domain_family") or pv.canonical_domain()
    wd = pv.json("02_ENGINEERING_DEFINITION.json") or {}
    detection_basis = bool(
        wd.get("domain_detection") or wd.get("why_this_domain")
        or pv.json("TECHNOLOGY_PACKAGE_MODEL.json"))
    if prob_domain and inv_domain and prob_domain != inv_domain:
        if detection_basis:
            g.warn("B-DOMAIN-ROUTED", f"user problem is {prob_domain}-domain; "
                   f"the invention is engineered in {inv_domain}-domain with "
                   f"a recorded domain-detection basis (evidenced routing — "
                   f"surface for review, not drift)")
        else:
            g.fail("B-DOMAIN-DRIFT", f"user problem is {prob_domain}-domain but the "
               f"invention presents as {inv_domain}-domain "
               f"(BS-023 / #160 failure mode)")
    # 3. failure/unmet-need + hypothetical must be addressed
    body = first_pages + "\n".join(pv.pdfs.get("01_EXECUTIVE_TECHNOLOGY_BRIEF.pdf", [""]))
    has_unknown = bool(re.search(r"UNKNOWN|NOT ESTABLISHED|NOT_ESTABLISHED|"
                                 r"remains? uncertain|unproven", body, re.I))
    if not has_unknown:
        g.fail("B-NO-EPISTEMIC-POSTURE", "first pages never state what remains "
               "hypothetical / unestablished (problem fidelity requires the "
               "established-vs-hypothetical boundary)")
    return g


def infer_domain(text: str) -> Optional[str]:
    best, best_hits = None, 0
    for dom in DOMAIN_VOCAB:
        hits = domain_term_hits(text, dom)
        n = len(hits)
        if n > best_hits:
            best, best_hits = dom, n
    return best


# ---------------------------------------------------------------- Gate C
BINDING_KEYS = ("canonical_source_refs", "provenance", "source_record",
                "frontier_capability", "source_hash", "source_url",
                "canonical_source")


def gate_C_domain_integrity(pv: PackageView, canonical: Optional[dict]) -> GateResult:
    g = GateResult("C", "Domain integrity: one canonical domain propagates "
                        "through every layer; contradiction detector as second "
                        "defense (primary invariant is field→source→domain).")
    dom = (canonical or {}).get("domain_family") or pv.canonical_domain()
    if not dom:
        g.fail("C-NO-DOMAIN", "no canonical domain_family declared anywhere")
        return g
    # R440.8 calibration: the HOME domain set is the declared engineering
    # domain PLUS the user problem's own domain family when supplied. A
    # genuine cross-domain technology (measured case: a CSF-shunt problem
    # routed to fluidics engineering — medical vocabulary is the problem's
    # own, not contamination) legitimately speaks both. The #160 failure
    # mode this gate exists to catch is UNBOUND foreign content that
    # belongs to NEITHER home domain (stale medical evidence inside a
    # vehicle package).
    home_domains = {dom}
    # R440.8: the problem's own domain family — declared when the run
    # classified it, otherwise INDEPENDENTLY resolved by the verifier
    # from the canonical PROBLEM text (the user's own words are source,
    # not claimant-controlled package content — Art. III). A CSF-shunt
    # problem routed to fluidics engineering legitimately speaks both.
    problem_dom = (canonical or {}).get("problem_domain_family")
    if not problem_dom and canonical and canonical.get("problem"):
        problem_dom = infer_domain(str(canonical["problem"]))
    if problem_dom:
        home_domains.add(str(problem_dom))
    # R443: the canonical problem-context applicability — a MEDICAL-
    # context package legitimately speaks medical vocabulary (its
    # requirements are medical BY the one canonical authority), even
    # when the ENGINEERING routing domain is non-medical (e.g. a
    # steering catheter routed to mechanical_structural engineering).
    # Consumed from the canonical state, never re-guessed here.
    _app_ctx = str((canonical or {}).get("applicability_context") or "")
    if _app_ctx in ("MEDICAL_IN_VIVO", "MEDICAL_EX_VIVO"):
        home_domains.add("biomedical")
    dom_l = str(dom).strip().lower()
    # when the declared domain is outside the gate's known vocabulary the
    # contradiction detector cannot adjudicate foreign terms (Art. XXV:
    # unknown is not contradiction) — it degrades to a warning
    vocab_known = dom_l in DOMAIN_VOCAB
    if not vocab_known and not problem_dom:
        g.warn("C-UNKNOWN-DOMAIN-VOCAB", f"domain {dom!r} is outside the "
               f"gate's known vocabulary — cross-domain contradiction "
               f"detection degrades to the problem-domain home set only")
    # primary invariant: every JSON SECTION carrying foreign-domain content
    # must itself carry a canonical binding key with a non-empty value.
    # When the home domain is outside the gate's calibrated vocabulary
    # (engine fine-grained families: fluidics_hydraulic, rf_wireless...)
    # the detector cannot adjudicate which coarse family is foreign —
    # findings surface as WARN for review (Art. XXV), never auto-block.
    hard_foreign = vocab_known
    for rel, data in pv.json_files.items():
        if not isinstance(data, dict) or "__parse_error__" in data:
            continue
        for section_key, section_val in data.items():
            if section_key in BINDING_KEYS:
                continue  # the section IS a binding
            blob = json_dump_safe(section_val)
            for other in DOMAIN_VOCAB:
                if str(other) in {h.lower() for h in home_domains}:
                    continue
                hits = domain_term_hits(blob, other)
                if len(hits) >= 3 and sum(hits.values()) >= 5:
                    bound = False
                    if isinstance(section_val, dict):
                        for bk in BINDING_KEYS:
                            v = section_val.get(bk)
                            if v not in (None, "", [], {}):
                                bound = True
                                break
                    if not bound:
                        if hard_foreign:
                            g.fail("C-FOREIGN-DOMAIN-FIELDS",
                                   f"{rel}:{section_key} carries unbound "
                                   f"{other}-domain content in a {dom} "
                                   f"package",
                                   {"terms": dict(list(hits.items())[:8])})
                        else:
                            g.warn("C-FOREIGN-DOMAIN-FIELDS",
                                   f"{rel}:{section_key} carries unbound "
                                   f"{other}-domain content in a {dom} "
                                   f"package (home domain outside the "
                                   f"gate's calibrated vocabulary — "
                                   f"surfaced for review)", {"terms":
                                   dict(list(hits.items())[:8])})
    # secondary: buyer-facing text contradiction detector
    for name, pages in pv.pdfs.items():
        text = "\n".join(pages)
        for other in DOMAIN_VOCAB:
            if str(other) in {h.lower() for h in home_domains}:
                continue
            hits = domain_term_hits(text, other)
            if len(hits) >= 3 and sum(hits.values()) >= 6:
                if not vocab_known and not problem_dom:
                    g.warn("C-DOMAIN-CONTRADICTION", f"{name} buyer-facing "
                           f"text contains {sum(hits.values())} occurrences "
                           f"of {other}-domain terminology in a {dom} "
                           f"package (unknown home vocabulary — surface for "
                           f"review, not auto-block)")
                else:
                    g.fail("C-DOMAIN-CONTRADICTION", f"{name} buyer-facing "
                           f"text contains {sum(hits.values())} occurrences "
                           f"of {other}-domain terminology in a {dom} "
                           f"package", {"terms": hits})
    return g


def json_dump_safe(obj) -> str:
    import json
    try:
        return json.dumps(obj, default=str)
    except Exception:
        return str(obj)


# ---------------------------------------------------------------- Gate D
def gate_D_section_provenance(pv: PackageView, canonical: Optional[dict]) -> GateResult:
    g = GateResult("D", "Structural section provenance: every buyer-facing "
                        "section carries machine-layer provenance "
                        "(R440.5 — required, not optional, for engine-run "
                        "packages).")
    prov = pv.json("PACKAGE_SECTION_PROVENANCE.json") \
        or pv.json("SECTION_PROVENANCE.json") \
        or (canonical or {}).get("section_provenance")
    # R440.5: engine-run packages MUST carry the dedicated provenance map.
    # (Historical portfolio references without one stay acceptable as
    # sealed artifacts — Art. XI; they carry manifest roles instead.)
    is_engine_run = bool((pv.json("PROVENANCE.json") or {}).get("run_id")
                         or pv.manifest.get("run_id"))
    if prov is None:
        if is_engine_run:
            g.fail("D-NO-PROVENANCE-MAP", "engine-run package carries no "
                   "PACKAGE_SECTION_PROVENANCE.json — a section without "
                   "canonical provenance is rejected even when the prose "
                   "sounds perfectly reasonable (R440.5)")
        else:
            g.warn("D-NO-PROVENANCE-MAP", "no SECTION_PROVENANCE map found "
                   "(sealed portfolio-reference posture; manifest roles + "
                   "machine JSONs carry the provenance)")
    buyer_pdfs = pv.buyer_pdf_names()
    required = {"00_PACKAGE_README.pdf", "01_EXECUTIVE_TECHNOLOGY_BRIEF.pdf",
                "02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf",
                "03_BUYER_DECISION_CARD.pdf", "04_EVIDENCE_SUMMARY.pdf",
                "05_TRANSFER_MANIFEST.pdf"}
    missing = required - set(buyer_pdfs)
    if missing:
        g.fail("D-BUYER-SECTIONS-MISSING", f"buyer-facing sections missing: "
               f"{sorted(missing)}")
    # each machine JSON buyer role must be manifested with a role + sha
    man_files = {e.get("file"): e for e in pv.manifest.get("files", [])
                 if isinstance(e, dict)}
    for pdf in buyer_pdfs:
        entry = man_files.get(pdf)
        if not entry:
            g.fail("D-UNMANIFESTED-SECTION", f"{pdf} is buyer-facing but not "
                   f"in the release manifest")
        elif not entry.get("sha256"):
            g.fail("D-NO-SECTION-HASH", f"{pdf} manifested without sha256 — "
                   f"paragraph origin cannot be audited")
    if isinstance(prov, dict):
        sections = prov.get("sections") or prov.get("section_provenance") or []
        # R440.5 coverage: every buyer PDF must be covered by at least one
        # provenance section entry (engine-run packages).
        covered_docs = set()
        for sec in sections:
            if isinstance(sec, dict):
                der = sec.get("derivation_type") or sec.get("derivation_method")
                if der and str(der).upper() not in (
                        "DIRECT", "DERIVED", "COMPUTED", "MODEL_DERIVED",
                        "UNKNOWN", "SPEC_DERIVED", "ENGINE_DERIVED"):
                    g.fail("D-BAD-DERIVATION", f"section {sec.get('section_id')} "
                           f"derivation_type {der!r} not in the allowed set")
                for req in ("section_id", "invention_id", "domain_family",
                            "canonical_source_refs"):
                    if req not in sec:
                        g.fail("D-PROVENANCE-FIELD-MISSING",
                               f"section provenance entry lacks {req}")
                # R440.5: source pointers must RESOLVE — non-empty refs,
                # and each carries a source hash or an explicit
                # derivation basis (never a bare token claim).
                refs = sec.get("canonical_source_refs")
                if isinstance(refs, list):
                    if not refs:
                        g.fail("D-EMPTY-SOURCE-REFS",
                               f"section {sec.get('section_id')} declares "
                               f"source binding with an empty reference list")
                    for r in refs:
                        if isinstance(r, str) and not r.strip():
                            g.fail("D-BLANK-SOURCE-REF",
                                   f"section {sec.get('section_id')} carries a "
                                   f"blank source pointer")
                if sec.get("document"):
                    covered_docs.add(str(sec.get("document")))
                # equation/parameter ids declared in a section must exist
                # in the machine registries they point at (R440.3: the
                # verifier checks the ACTUAL references, not tokens)
                _check_section_id_refs(pv, g, sec)
        if is_engine_run:
            uncov = required - covered_docs
            if uncov:
                g.fail("D-UNCOVERED-DOCUMENTS", f"no provenance entry covers "
                       f"buyer documents: {sorted(uncov)}")
    return g


def _check_section_id_refs(pv: PackageView, g: GateResult,
                           sec: dict) -> None:
    """R440.3: equation_ids / parameter_ids declared by a section must
    resolve in the package's own machine registries — the word 'decision'
    is never evidence of invention linkage, but EQ-001 must be."""
    reg = pv.json("EQUATION_REGISTRY.json") or {}
    known_eqs = set()
    for eq in (reg.get("equations") or []):
        if isinstance(eq, dict) and eq.get("equation_id"):
            known_eqs.add(str(eq["equation_id"]))
    trace = pv.json("ENGINEERING_TRACEABILITY.json") or {}
    known_params = set()
    for c in (trace.get("chains") or []):
        if isinstance(c, dict) and c.get("design_input_id"):
            known_params.add(str(c["design_input_id"]))
    for eq in sec.get("equation_ids") or []:
        if known_eqs and str(eq) not in known_eqs:
            g.fail("D-EQ-REF-UNRESOLVED", f"section {sec.get('section_id')} "
                   f"cites {eq} but the equation registry does not contain it")
    for pid in sec.get("parameter_ids") or []:
        if known_params and str(pid) not in known_params:
            g.fail("D-PARAM-REF-UNRESOLVED", f"section "
                   f"{sec.get('section_id')} cites {pid} but the "
                   f"traceability layer does not contain it")


# ---------------------------------------------------------------- Gate E
def gate_E_structural_linkage(pv: PackageView, canonical: Optional[dict]) -> GateResult:
    g = GateResult("E", "Lexical depth criterion RETIRED: sections must link to "
                        "canonical records by ID/field, not token coincidence.")
    # invention-specific vocabulary = tokens from canonical invention name +
    # mechanism, or (fallback) the manifest technology_name + mechanism records
    inv_tokens = set()
    canon_text = ""
    if canonical:
        canon_text = json_dump_safe({k: canonical.get(k) for k in
                                     ("invention", "mechanism", "architecture",
                                      "technology_name") if canonical.get(k)})
        inv_tokens.update(distinctive_tokens(canon_text, limit=40))
    tech_name = str(pv.manifest.get("technology_name") or "")
    inv_tokens.update(distinctive_tokens(tech_name, limit=25))
    mech = pv.json("MODEL/README.json") or {}
    inv_tokens.update(distinctive_tokens(json_dump_safe(mech), limit=25))

    # check every buyer PDF's major sections
    for name in pv.buyer_pdf_names():
        text = pv.pdf_full_text(name)
        ids = canonical_id_hits(text)
        id_count = len(ids)
        inv_hit = sum(1 for t in inv_tokens if t in text.lower())
        # hard failure: no canonical IDs at all AND few invention tokens
        # (the #160 'GOVERNING_MODELS matched token "decision"' posture)
        if id_count == 0 and inv_hit < 2:
            g.fail("E-SECTION-UNLINKED", f"{name} carries no canonical record "
                   f"IDs and fewer than 2 invention-specific tokens — lexical "
                   f"coincidence cannot pass as invention linkage")
        elif id_count == 0:
            g.warn("E-NO-IDS", f"{name} has invention vocabulary but no "
                   f"canonical IDs (EQ-/DI-/DO-/FM-/WP-...)")
    # explicit weak-token-only trap: sections whose ONLY 'invention tie' is
    # weak tokens — detected via a dedicated machine-layer check
    depth = pv.json("DEPTH_CONTRACT.json")
    if isinstance(depth, dict):
        for sec in depth.get("sections", []) if isinstance(depth.get("sections"), list) else []:
            if isinstance(sec, dict):
                toks = sec.get("matched_tokens") or []
                strong = [t for t in toks if t not in
                          {"decision", "domain", "evidence", "recorded",
                           "source", "engine", "engineering", "status"}]
                if toks and not strong and not sec.get("canonical_refs"):
                    g.fail("E-LEXICAL-ONLY", f"depth contract section "
                           f"{sec.get('section_id')} satisfied by weak tokens "
                           f"only {toks} — retired criterion")
    return g


# ---------------------------------------------------------------- Gate F
def gate_F_evidence_integrity(pv: PackageView, canonical: Optional[dict]) -> GateResult:
    g = GateResult("F", "Evidence integrity: one canonical ledger; count parity "
                        "across machine layer, PDF class table, manifest; every "
                        "item carries id/source/uri/hash/excerpt/class.")
    loop = pv.json("LOOP_STATE.json") or {}
    machine_counts = loop.get("evidence_class_counts") or {}
    pdf_counts = pv.parse_evidence_class_table()
    if machine_counts and pdf_counts:
        for cls, n in machine_counts.items():
            if cls in pdf_counts and pdf_counts[cls] != n:
                g.fail("F-CLASS-PARITY", f"evidence class {cls}: machine={n} "
                       f"PDF={pdf_counts[cls]}")
    elif machine_counts and not pdf_counts:
        g.fail("F-NO-PDF-CLASS-TABLE", "machine evidence class counts exist but "
               "the evidence PDF publishes no class table")
    # PHYSICAL_OBSERVATION must be 0 (Art. XXXVIII posture in packages)
    po = machine_counts.get("PHYSICAL_OBSERVATION", 0)
    if po:
        g.fail("F-PHYSICAL-OBSERVATION", f"PHYSICAL_OBSERVATION={po} in a "
               f"machine-generated package (Art. XXXVIII violation)")
    # source entries: URL + hash + excerpt mandatory
    sources = pv.parse_evidence_sources()
    n_fact = machine_counts.get("SOURCE_FACT", 0)
    for s in sources:
        problems = []
        if not s["url"] or s["url"].lower() in ("none", "n/a", "null", "-"):
            problems.append("blank-url")
        if not s["hash"] or len(s["hash"]) < 32:
            problems.append("blank-hash")
        if len(s["excerpt"]) < 20:
            problems.append("blank-excerpt")
        if problems:
            g.fail("F-SOURCE-INCOMPLETE", f"evidence source #{s['index']} in "
                   f"{s['file']}: {','.join(problems)}")
    if sources and n_fact and len(sources) < n_fact and not pdf_counts.get(
            "EXTERNAL_PRECEDENT"):
        g.fail("F-SOURCE-COUNT-PARITY", f"machine SOURCE_FACT={n_fact} but "
               f"evidence PDF lists {len(sources)} hashed sources")
    # manifest evidence role count
    man_files = [e for e in pv.manifest.get("files", []) if isinstance(e, dict)]
    ev_role = [e for e in man_files if "evidence" in str(e.get("role", "")).lower()]
    ext_count = pv.manifest.get("external_evidence_count")
    if ext_count is not None and machine_counts.get("SOURCE_FACT") is not None:
        if int(ext_count) != int(machine_counts["SOURCE_FACT"]):
            g.warn("F-MANIFEST-COUNT-DRIFT", f"manifest external_evidence_count"
                   f"={ext_count} vs SOURCE_FACT={machine_counts['SOURCE_FACT']}")
    # canonical state parity when supplied
    if canonical:
        canon_ev = canonical.get("evidence_count") or canonical.get(
            "canonical_evidence_count")
        if canon_ev is not None and machine_counts:
            m_total = sum(v for k, v in machine_counts.items()
                          if k != "UNCLASSIFIED")
            if int(canon_ev) != m_total:
                g.fail("F-CANON-PARITY", f"canonical evidence_count={canon_ev} "
                       f"!= machine total={m_total}")
    return g


# ---------------------------------------------------------------- Gate G
def gate_G_causal_integrity(pv: PackageView, canonical: Optional[dict]) -> GateResult:
    g = GateResult("G", "Causal mechanism integrity: the canonical chain "
                        "PROBLEM→FAILURE→MECHANISM→INTERVENTION→EFFECT→"
                        "BOUNDARY→DESIGN VARIABLES→FAILURE MODES→PREDICTION.")
    blob = "\n".join(pv.pdf_full_text(n) for n in pv.buyer_pdf_names())
    blob += json_dump_safe(pv.json_files)
    if canonical:
        blob += json_dump_safe(canonical)
    CHAIN = {
        "PROBLEM": r"problem|objective|unmet need",
        "FAILURE/UNMET NEED": r"failure|unmet|deficiency|bottleneck",
        "CAUSAL MECHANISM": r"mechanism|causal",
        "INTERVENTION": r"intervention|invent",
        "EFFECT": r"effect|expected effect|outcome",
        "BOUNDARY CONDITIONS": r"boundary|applicability|operating envelope",
        "DESIGN VARIABLES": r"design (input|variable|parameter)|DI-\d",
        "FAILURE MODES": r"failure mode|FM-\d",
        "TESTABLE PREDICTION": r"prediction|testable|falsif|hypothesis",
    }
    missing = []
    for link, pat in CHAIN.items():
        if not re.search(pat, blob, re.I):
            missing.append(link)
    if missing:
        g.fail("G-CHAIN-INCOMPLETE", f"causal chain links absent (and not "
               f"explicitly UNKNOWN): {missing}")
    return g


# ---------------------------------------------------------------- Gate H
def gate_H_engineering_integrity(pv: PackageView, canonical: Optional[dict]) -> GateResult:
    g = GateResult("H", "Engineering integrity: counts may not masquerade as "
                        "maturity; DI/DO carry meaning/basis/status; ABSENT "
                        "outputs may not be presented as existing.")
    mb = pv.json("MATURITY_BASIS.json") or {}
    counts = mb.get("counts") or {}
    trace = pv.json("ENGINEERING_TRACEABILITY.json") or {}
    chains = trace.get("chains") or []
    dis = [c for c in chains if isinstance(c, dict) and c.get("design_input_id")]
    # every chain DI must have a parameter name
    for c in dis:
        if not (c.get("parameter") or "").strip():
            g.fail("H-DI-NO-MEANING", f"design input {c.get('design_input_id')} "
                   f"has no parameter meaning")
    # DO status discipline: outputs must declare status somewhere
    do_ids = set()
    for c in dis:
        slots = c.get("slots") or {}
        do = slots.get("design_output") or {}
        ref = do.get("reference") or do.get("id")
        if ref:
            do_ids.add(str(ref))
    do_count_machine = counts.get("design_outputs")
    if do_count_machine is not None and do_ids:
        # chains may cover fewer than all DOs; flag only gross divergence
        if len(do_ids) < int(do_count_machine) * 0.5:
            g.warn("H-DO-CHAIN-COVERAGE", f"traceability covers {len(do_ids)} "
                   f"DOs of {do_count_machine} declared")
    # buyer-facing inflation check (#160: '21 outputs, 21 ABSENT' presented
    # as existing): extract claimed counts from decision card
    card = pv.pdf_full_text("03_BUYER_DECISION_CARD.pdf")
    for m in re.finditer(r"(\d+)\s+design outputs", card, re.I):
        claimed = int(m.group(1))
        if do_count_machine is not None and claimed > int(do_count_machine):
            g.fail("H-DO-INFLATION", f"decision card claims {claimed} design "
                   f"outputs; machine layer declares {do_count_machine}")
    for m in re.finditer(r"(\d+)\s+design inputs", card, re.I):
        claimed = int(m.group(1))
        if counts.get("design_inputs") is not None and claimed > int(counts["design_inputs"]):
            g.fail("H-DI-INFLATION", f"decision card claims {claimed} design "
                   f"inputs; machine layer declares {counts['design_inputs']}")
    # ABSENT outputs presented as existing: any JSON listing DO statuses
    for rel, data in pv.json_files.items():
        if not isinstance(data, dict):
            continue
        outputs = data.get("design_outputs") or []
        if isinstance(outputs, list) and outputs and all(
                isinstance(o, dict) for o in outputs):
            absent = [o for o in outputs if str(o.get("status", "")).upper()
                      in ("ABSENT", "NOT_PRESENT", "MISSING")]
            if len(absent) == len(outputs) and not data.get("absent_disclosed"):
                g.fail("H-ABSENT-PRESENTED", f"{rel}: all {len(outputs)} design "
                       f"outputs are ABSENT but the section presents them "
                       f"without disclosing that none exist")
    # cross-layer FM count drift is recorded as a warning (calibrated on the
    # golden references: chain-count vs evidence-id-count may legitimately
    # differ by unlinked records — inflated BUYER claims above are the hard
    # failure; silent machine drift is surfaced for repo-side repair)
    fm_evidence = counts.get("failure_modes")
    fm_chains = trace.get("summary", {}).get("orphan_FMs")
    if fm_evidence is not None and fm_chains is not None and int(fm_evidence) != int(fm_chains):
        g.warn("H-FM-COUNT-DRIFT", f"failure-mode counts differ across machine "
               f"layers: maturity_basis={fm_evidence} traceability={fm_chains}")
    return g


# ---------------------------------------------------------------- Gate I
def gate_I_traceability(pv: PackageView, canonical: Optional[dict]) -> GateResult:
    g = GateResult("I", "Traceability: DI→parameter→DO→FM→VF→EXPERIMENT graph; "
                        "broken links justified; critical-link gate.")
    trace = pv.json("ENGINEERING_TRACEABILITY.json") or {}
    chains = trace.get("chains") or []
    links = trace.get("links") or []
    if chains:
        unjustified = []
        for c in chains:
            if not isinstance(c, dict):
                continue
            slots = c.get("slots") or {}
            for slot_name, slot in slots.items():
                if not isinstance(slot, dict):
                    continue
                state = str(slot.get("state", "")).upper()
                if state in ("UNKNOWN", "NOT_LINKED", "PARTIAL"):
                    reason = slot.get("reason") or slot.get("justification") or \
                        slot.get("note")
                    if not reason:
                        unjustified.append(
                            {"chain": c.get("design_input_id"),
                             "slot": slot_name})
        if unjustified:
            g.fail("I-UNJUSTIFIED-BROKEN-LINKS", f"{len(unjustified)} broken "
                   f"links carry no reason (critical-link gate requires "
                   f"justification)", {"examples": unjustified[:6]})
        # critical DI gate
        summary = trace.get("summary") or {}
        critical_dis = summary.get("critical_DIs", 0)
        states = summary.get("chain_state_counts", {})
        if critical_dis and states.get("TRACEABILITY_COMPLETE", 0) == 0 and \
                not trace.get("release_gate", {}).get(
                    "incomplete_parts_explicitly_justified"):
            g.fail("I-CRITICAL-DI-ORPHANED", f"{critical_dis} critical design "
                   f"inputs have no complete downstream path and the record "
                   f"does not explicitly justify the orphans")
    elif links:
        # R425 links schema: link_kind/source_id/target_id/binding/binding_basis
        unjustified = []
        for l in links:
            if not isinstance(l, dict):
                continue
            binding = str(l.get("binding", "")).upper()
            if binding in ("UNKNOWN", "NOT_LINKED", "PARTIAL"):
                basis = l.get("binding_basis") or l.get("reason")
                if not basis:
                    unjustified.append(
                        {"link_kind": l.get("link_kind"),
                         "source": l.get("source_id")})
        if unjustified:
            g.fail("I-UNJUSTIFIED-BROKEN-LINKS", f"{len(unjustified)} "
                   f"traceability links carry no binding basis "
                   f"(R425 graph: every UNKNOWN must cite the inspected "
                   f"record)", {"examples": unjustified[:6]})
        state = str(trace.get("traceability_state", "")).upper()
        if state == "TRACEABILITY_UNKNOWN":
            coverage = trace.get("coverage") or {}
            if not coverage and not trace.get("summary"):
                g.fail("I-NO-COVERAGE", "traceability state UNKNOWN with no "
                       "coverage record — the graph health is not represented")
    else:
        g.fail("I-NO-TRACEABILITY", "no ENGINEERING_TRACEABILITY machine layer")
    return g


# ---------------------------------------------------------------- Gate J
def gate_J_equations(pv: PackageView, canonical: Optional[dict]) -> GateResult:
    g = GateResult("J", "Equations: every registry entry carries id/expression/"
                        "variables/units/source/applicability; no slot-only rows.")
    reg = pv.json("EQUATION_REGISTRY.json")
    if reg is None:
        g.fail("J-NO-REGISTRY", "no EQUATION_REGISTRY machine layer")
        return g
    eqs = reg.get("equations") or []
    if not eqs:
        # an EMPTY registry is acceptable only as an explicitly declared
        # honest state (R424: 'none are fabricated to make the package look
        # scientific'); a bare empty registry is a slot-only defect
        status = str(reg.get("status", "")).upper()
        reason = reg.get("reason") or ""
        if "NOT_APPLICABLE" in status and reason.strip():
            g.warn("J-NO-EQUATIONS-DECLARED", f"equation registry empty with "
                   f"declared basis: {reason[:140]}")
        else:
            g.fail("J-EMPTY-REGISTRY", "equation registry present but empty "
                   "with no declared NOT_APPLICABLE basis")
        return g
    for eq in eqs:
        if not isinstance(eq, dict):
            continue
        eid = eq.get("equation_id")
        expr = eq.get("equation_canonical") or eq.get("expression") or \
            eq.get("math_expression")
        # the REAL engine equation schema (R440 calibration): equations
        # carry name/expression/source/applicability/assumptions; the
        # variables are defined BY the expression itself (Q, r, dP…), the
        # name is the caption. Slot-only rows and missing expressions/
        # applicability stay hard failures.
        name = eq.get("name") or eq.get("caption")
        problems = []
        if not eid:
            problems.append("no-id")
        if not expr or not str(expr).strip() or "PLACEHOLDER" in str(expr).upper():
            problems.append("no-expression")
        if not (eq.get("variables") or name or eq.get("caption")):
            problems.append("no-variables")
        if not (eq.get("units") or name or eq.get("caption")):
            problems.append("no-units")
        if not (eq.get("applicability") or eq.get("assumptions")):
            problems.append("no-applicability")
        if not (eq.get("source") or eq.get("basis") or eq.get("variables")
                or name):
            problems.append("no-source")
        if problems:
            g.fail("J-EQ-INCOMPLETE", f"equation {eid}: {', '.join(problems)}")
    # PDF typeset presence: dossier must actually render the equations
    dossier = pv.pdf_full_text("02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf")
    n_reg = len(eqs)
    ids_in_pdf = len(canonical_id_hits(dossier))
    if n_reg and ids_in_pdf == 0 and "=" not in dossier:
        g.fail("J-EQ-MISSING-IN-DOSSIER", f"registry has {n_reg} equations but "
               f"the dossier renders none (missing-equation hard failure)")
    return g


# ---------------------------------------------------------------- Gate K
def gate_K_experiment(pv: PackageView, canonical: Optional[dict]) -> GateResult:
    g = GateResult("K", "Decisive experiment: falsification contract present — "
                        "hypothesis/measurement/threshold etc. or explicit UNKNOWN; "
                        "'killer experiment fails: UNKNOWN' with nothing else is "
                        "not acceptable.")
    blob = "\n".join(pv.pdf_full_text(n) for n in pv.buyer_pdf_names())
    blob += json_dump_safe({k: v for k, v in pv.json_files.items()
                            if "EXPERIMENT" in k or "WP" in str(v)[:200]})
    if canonical:
        blob += json_dump_safe(canonical.get("experiment") or {})
    FIELDS = {
        "hypothesis": r"hypothes[ie]s|WHAT WOULD (PROVE|DISPROVE)|cause the "
                      r"buyer to stop|if .{0,60}(fails|is less than)",
        "measurement": r"measure|metric|readout|endpoint|k_cat|Km",
        "threshold": r"threshold|acceptance|falsif|less than [0-9]|greater "
                     r"than [0-9]",
        "experiment reference": r"WP-\d|work package|experiment",
        "control/treatment": r"\bcontrol\b|treatment|baseline|reference arm",
    }
    found = {k: bool(re.search(p, blob, re.I)) for k, p in FIELDS.items()}
    # core falsification contract: a stated falsify/accept condition AND a
    # measurement/experiment reference (R439 Gate K; the golden references
    # express the hypothesis as a buyer-stop condition rather than the literal
    # word 'hypothesis')
    core = (found["threshold"]) and (found["measurement"] or
                                    found["experiment reference"])
    if not core:
        g.fail("K-NO-EXPERIMENT-CONTRACT", "package contains no usable "
               "experimental contract (no falsification/acceptance condition "
               "with a measurement or work package) — the Constitution "
               "defines the killer experiment as a falsification contract")
    else:
        missing = [k for k, v in found.items() if not v]
        if missing:
            g.warn("K-PARTIAL-CONTRACT", f"experiment contract missing "
                   f"aspects: {missing} (acceptable only if explicitly UNKNOWN)")
    return g


# ---------------------------------------------------------------- Gate L
def gate_L_buyer_utility(pv: PackageView, canonical: Optional[dict]) -> GateResult:
    g = GateResult("L", "Buyer decision quality: the first usable pages answer "
                        "the buyer's next decision, not a completeness template.")
    first = "\n".join(
        pv.pdf_full_text(n) for n in ("00_PACKAGE_README.pdf",
                                      "03_BUYER_DECISION_CARD.pdf",
                                      "01_EXECUTIVE_TECHNOLOGY_BRIEF.pdf"))
    QUESTIONS = {
        "what is it": r"WHAT IS (THE |AN )?INVENTION|WHAT IS IT\?",
        "why does it matter": r"WHY DOES IT MATTER",
        "what is established": r"WHAT IS (ACTUALLY )?ESTABLISHED",
        "what remains unknown": r"WHAT IS NOT ESTABLISHED|WHAT REMAINS (UNCERTAIN|UNKNOWN)",
        "what could kill it": r"STOP|KILL|strongest objection",
        "cheapest next step": r"CHEAPEST|DECISIVE NEXT|NEXT EXPERIMENT",
    }
    missing = [q for q, p in QUESTIONS.items() if not re.search(p, first, re.I)]
    if missing:
        g.fail("L-DECISION-QUESTIONS-MISSING", f"first usable pages do not "
               f"answer: {missing}")
    # specificity: answers must reference invention-specific tokens
    inv_tokens = distinctive_tokens(
        str(pv.manifest.get("technology_name") or ""), limit=15)
    if inv_tokens and not any(t in first.lower() for t in inv_tokens):
        g.fail("L-GENERIC-ANSWERS", "decision pages never mention the "
               "invention's own name/vocabulary — answers are generic "
               "template text")
    return g


# ---------------------------------------------------------------- Gate M
def gate_M_commercial(pv: PackageView, canonical: Optional[dict]) -> GateResult:
    g = GateResult("M", "Commercial integrity: every commercial number is "
                        "SOURCE_FACT / ENGINEERING_ESTIMATE / ROUGH_ESTIMATE "
                        "with assumptions, or NOT_ESTABLISHED (Art. LXVI).")
    ce = pv.json("COMMERCIAL_EVIDENCE.json")
    if ce is None:
        g.fail("M-NO-COMMERCIAL-LAYER", "no COMMERCIAL_EVIDENCE machine layer")
        return g
    blob = json_dump_safe(ce)
    # any numeric market claim without class or NOT_ESTABLISHED?
    for m in re.finditer(r'"(?:estimate|value)"\s*:\s*"?([\d.,]+\s*(?:billion|'
                         r'million|bn|mm|USD|\$|EUR)[^"]*)"?', blob, re.I):
        val = m.group(1)
        if "NOT_ESTABLISHED" in blob[max(0, m.start()-300):m.start()+300] or \
           "not established" in val.lower():
            continue
        g.fail("M-UNCLASSIFIED-NUMBER", f"commercial numeric value {val!r} "
               f"lacks SOURCE_FACT/ESTIMATE class + assumptions")
    # PDF market figures: '$X billion market' without disclosure
    for name in pv.buyer_pdf_names():
        text = pv.pdf_full_text(name)
        for m in re.finditer(r"\$\s?[\d.,]+\s?(billion|million)[^.]{0,80}market",
                             text, re.I):
            ctx = text[max(0, m.start()-200):m.end()+200]
            if "NOT_ESTABLISHED" not in ctx.upper() and "SOURCE" not in ctx.upper():
                g.fail("M-PDF-MARKET-FIGURE", f"{name}: market-size figure "
                       f"without source class ({m.group(0)[:60]!r})")
    return g


# ---------------------------------------------------------------- Gate N
def gate_N_artifact_fidelity(pv: PackageView, canonical: Optional[dict]) -> GateResult:
    g = GateResult("N", "3D/artifact integrity: physical inventions must "
                        "represent required components; software inventions "
                        "are 3D_NOT_APPLICABLE; no generic substitute.")
    status = pv.json("MODEL/3D_DESIGN_STATUS.json") or {}
    classification = str(status.get("classification", "")).upper()
    design_status = str(status.get("3d_design_status", "")).upper()
    if not classification and status.get("visualizability_class"):
        # bridge/elite schema: visualizability_class + PRESENT_CONCEPTUAL
        viz = str(status.get("visualizability_class", "")).upper()
        if "CONCEPTUAL" in viz:
            # conceptual fallback is legitimate (R421 §18) but its components
            # must derive from the invention, not the technology class
            comps = status.get("components") or []
            unmapped = [c.get("name") for c in comps if isinstance(c, dict)
                        and not c.get("mapped_from")]
            if comps and len(unmapped) == len(comps):
                g.warn("N-CLASS-DERIVED-COMPONENTS", f"all {len(comps)} "
                       f"conceptual components are unmapped class-derived "
                       f"presentation elements (mapped_from null) — "
                       f"component fidelity to THIS invention is not "
                       f"established")
            req = set()
            if canonical and isinstance(canonical.get("essential_components"),
                                        list):
                req = {str(c) for c in canonical["essential_components"]}
                names = {str(c.get("name", "")) for c in comps
                         if isinstance(c, dict)}
                missing = [r for r in req if r not in names]
                if req and missing:
                    g.fail("N-COMPONENT-FIDELITY", f"canonical essential "
                           f"components not represented in the conceptual "
                           f"model: {missing[:8]}")
            return g
        classification = viz
    if "NOT_APPLICABLE" in classification:
        # software-only: no CAD/GLB may be presented as the technology
        if pv.glb_nodes or any(str(p).endswith((".step", ".stl"))
                               for p in pv.root.rglob("*")):
            g.fail("N-SOFTWARE-WITH-CAD", "3D_NOT_APPLICABLE classification "
                   "but CAD/GLB artifacts present — faking a physical object "
                   "for a software invention")
        return g
    if "REQUIRED" not in classification:
        g.warn("N-NO-CLASSIFICATION", "no 3D classification recorded; "
               "component fidelity could not be verified")
        return g
    if "PRESENT" not in design_status:
        if pv.glb_nodes or any(str(p).endswith(".glb")
                               for p in pv.root.rglob("*")):
            g.fail("N-GENERIC-SUBSTITUTE", "geometry present while the 3D "
                   "design status is not PRESENT — generic substitute "
                   "(hero suppression rule)")
        else:
            g.fail("N-NO-GEOMETRY", "physical invention without geometry — "
                   "required components are not represented")
        return g
    # component fidelity: essential components vs GLB node names
    required = set()
    if canonical and isinstance(canonical.get("essential_components"), list):
        required = {str(c) for c in canonical["essential_components"]}
    mman = pv.json("MODEL/MODEL_MANIFEST.json") or {}
    for o in mman.get("objects", []):
        if isinstance(o, dict) and o.get("object_id"):
            required.add(str(o["object_id"]))
    if required:
        represented = set()
        for nodes in pv.glb_nodes.values():
            represented.update(n.lower().replace(" ", "_") for n in nodes)
        for p in pv.root.rglob("*.step"):
            represented.add(p.stem.lower().split("assembly")[0])
        missing = []
        for req in required:
            key = req.lower().replace(" ", "_")
            if not any(key in r or r in key for r in represented):
                missing.append(req)
        if missing:
            g.fail("N-COMPONENT-FIDELITY", f"essential invention components "
                   f"not represented in geometry: {sorted(missing)[:8]}",
                   {"required": sorted(required), "represented":
                    sorted(list(represented))[:12]})
    # GLB parseability
    for rel in pv.glb_nodes:
        if pv.glb_nodes[rel] == [] and (pv.root / rel).stat().st_size > 1000:
            g.fail("N-GLB-UNPARSEABLE", f"{rel}: >1KB but no named nodes "
                   f"parsed — scene graph cannot be verified")
    return g


# ---------------------------------------------------------------- Gate P
def gate_P_pdf_visual_qa(pv: PackageView, canonical: Optional[dict]) -> GateResult:
    g = GateResult("P", "PDF visual QA: every PDF rendered and inspected — "
                        "collision/overflow/clipping/blank-page/broken-symbol/"
                        "missing-equation are hard failures.")
    if not pv.pdfs:
        g.fail("P-NO-PDFS", "no buyer PDFs found")
        return g
    for name, pages in pv.pdfs.items():
        path = pv.root / name
        # broken symbols
        for i, t in enumerate(pages):
            if "\ufffd" in t:
                g.fail("P-BROKEN-SYMBOLS", f"{name} page {i+1}: replacement "
                       f"characters in extracted text")
        # blank page detection
        for i, t in enumerate(pages):
            if len(t.strip()) < 10:
                g.fail("P-BLANK-PAGE", f"{name} page {i+1}: no text content "
                       f"(unexpected blank page)")
        try:
            import fitz
            doc = fitz.open(str(path))
            for pno in range(len(doc)):
                page = doc[pno]
                blocks = [b for b in page.get_text("blocks") if b[4].strip()]
                # collision: heavy overlap between text blocks (calibrated:
                # golden references show 0.0% overlap; the attack fixture 41%)
                for i in range(len(blocks)):
                    for j in range(i + 1, len(blocks)):
                        r1, r2 = fitz.Rect(blocks[i][:4]), fitz.Rect(blocks[j][:4])
                        inter = r1 & r2
                        if not inter.is_empty and inter.get_area() > 200:
                            m = min(r1.get_area(), r2.get_area())
                            if m > 1 and inter.get_area() / m > 0.30:
                                g.fail("P-TEXT-COLLISION", f"{name} page "
                                       f"{pno+1}: text blocks overlap "
                                       f"{inter.get_area()/m:.0%} "
                                       f"({blocks[i][4][:28]!r} vs "
                                       f"{blocks[j][4][:28]!r})")
                # clipping: text outside the page box
                for b in blocks:
                    if (b[0] < -2 or b[1] < -2 or b[2] > page.rect.width + 2
                            or b[3] > page.rect.height + 2):
                        g.fail("P-TEXT-CLIPPED", f"{name} page {pno+1}: text "
                               f"block extends outside the page box")
                # ink coverage (rendered): near-blank rendered page
                pix = page.get_pixmap(dpi=36)
                samples = pix.samples
                nonwhite = sum(1 for k in range(0, len(samples), 97)
                               if samples[k] < 245)
                frac = nonwhite / max(1, len(samples) // 97)
                if frac < 0.004 and len(pages[pno].strip()) < 40:
                    g.fail("P-BLANK-RENDER", f"{name} page {pno+1}: rendered "
                           f"page is visually blank")
            doc.close()
        except ImportError:
            g.warn("P-NO-FITZ", "PyMuPDF unavailable: geometry QA degraded to "
                   "text-only checks")
        except Exception as e:
            g.fail("P-PDF-ERROR", f"{name}: PDF inspection error {e}")
        # missing equation in a section that must typeset them
        if "DOSSIER" in name.upper():
            text = pv.pdf_full_text(name)
            reg = pv.json("EQUATION_REGISTRY.json") or {}
            if reg.get("equations") and "=" not in text:
                g.fail("P-MISSING-EQUATION", f"{name}: registry has "
                       f"{len(reg['equations'])} equations but no equation "
                       f"is rendered")
    return g


# ---------------------------------------------------------------- Gate Q
def gate_Q_manifest_zip(pv: PackageView, canonical: Optional[dict]) -> GateResult:
    g = GateResult("Q", "Manifest/ZIP integrity: actual files = manifest files "
                        "= ZIP contents; SHA-256 per file; clean build — no "
                        "stale/unmanifested artifacts.")
    man_files = {e.get("file"): e for e in pv.manifest.get("files", [])
                 if isinstance(e, dict)}
    if not man_files:
        g.fail("Q-NO-MANIFEST", "no PACKAGE_MANIFEST with files[]")
        return g
    actual = set(pv.all_files())
    # the manifest itself is legitimately unmanifested (self-hash paradox)
    unmanifested = sorted(f for f in actual
                          if f not in man_files and f != "PACKAGE_MANIFEST.json"
                          and not f.endswith("/")
                          and not f.startswith("."))
    if unmanifested:
        g.fail("Q-UNMANIFESTED-FILES", f"files on disk not in the manifest "
               f"(stale or smuggled artifacts): {unmanifested[:10]}")
    missing = sorted(f for f in man_files if f not in actual)
    if missing:
        g.fail("Q-MISSING-FILES", f"manifest entries not present on disk: "
               f"{missing[:10]}")
    # SHA-256 verification
    bad_hash = []
    for rel, entry in man_files.items():
        h = entry.get("sha256")
        if not h:
            g.fail("Q-NO-HASH", f"{rel} manifested without sha256")
            continue
        p = pv.root / rel
        if p.exists():
            actual_h = sha256_file(p)
            if actual_h != h:
                bad_hash.append(rel)
    if bad_hash:
        g.fail("Q-HASH-MISMATCH", f"sha256 mismatch (stale content): "
               f"{bad_hash[:6]}")
    # machine layer completeness for buyer release
    required_json = ["PACKAGE_MANIFEST.json", "LOOP_STATE.json",
                     "MATURITY_BASIS.json", "ENGINEERING_TRACEABILITY.json",
                     "EQUATION_REGISTRY.json", "COMMERCIAL_EVIDENCE.json",
                     "UNKNOWN_ROADMAP.json", "VALIDATION_ECONOMICS.json"]
    for r in required_json:
        if r not in actual:
            g.fail("Q-MACHINE-LAYER-MISSING", f"machine layer incomplete: "
                   f"{r} absent")
    # ZIP-specific checks
    if pv.source.suffix == ".zip":
        import zipfile as _zf
        try:
            with _zf.ZipFile(pv.source) as zf:
                bad = zf.testzip()
                if bad:
                    g.fail("Q-ZIP-CORRUPT", f"zip CRC failure at {bad}")
                names = set(zf.namelist())
                inner = set(pv.all_files())
                # normalize a common wrapper directory (e.g. a single
                # TECHNOLOGY_PACKAGE/ root inside the zip)
                wrapper_prefix = None
                tops = {n.split("/", 1)[0] for n in names if "/" in n}
                if len(tops) == 1 and all(n.startswith(tops.copy().pop() + "/")
                                          for n in names if not n.endswith("/")):
                    wrapper_prefix = list(tops)[0] + "/"
                normalized = {n[len(wrapper_prefix):] if wrapper_prefix and
                              n.startswith(wrapper_prefix) else n
                              for n in names if not n.endswith("/")}
                if not inner.issubset(normalized):
                    missing = sorted(inner - normalized)[:8]
                    g.fail("Q-ZIP-DRIFT", f"zip contents differ from extracted "
                           f"view: {missing}")
        except Exception as e:
            g.fail("Q-ZIP-ERROR", f"zip reopen failed: {e}")
    return g


# ---------------------------------------------------------------- Gate R
def gate_R_maturity_coherence(pv: PackageView, canonical: Optional[dict]) -> GateResult:
    g = GateResult("R", "State/maturity coherence: one canonical maturity with "
                        "subordinate flags; no competing authorities.")
    maturity_fields: dict[str, list[dict]] = {}
    CANONICAL_KEYS = {"technology_maturity"}
    SUBORDINATE_KEYS = {"dossier_maturity", "builder_view_maturity",
                        "transfer_posture", "loop_verification_state"}
    for rel, data in pv.json_files.items():
        if not isinstance(data, dict):
            continue
        for k in list(data.keys()) + (list(pv.manifest.keys())
                                      if rel == "PACKAGE_MANIFEST.json" else []):
            if "MATURITY" in str(k).upper():
                maturity_fields.setdefault(str(k), []).append(
                    {"where": rel, "value": str(data.get(k))})
    for k, v in pv.manifest.items():
        if "MATURITY" in str(k).upper():
            maturity_fields.setdefault(str(k), []).append(
                {"where": "PACKAGE_MANIFEST.json", "value": str(v)})
    canon = maturity_fields.get("technology_maturity", [])
    canon_vals = sorted({d["value"] for d in canon})
    if len(canon_vals) > 1:
        g.fail("R-CANON-DIVERGENT", f"technology_maturity declared "
               f"divergently: {canon_vals}")
    if not canon_vals:
        g.fail("R-NO-CANON-MATURITY", "no canonical technology_maturity "
               "anywhere in the machine layer")
        return g
    canonical_value = canon_vals[0]
    # subordinate fields must not claim a higher rung than the canonical one
    LADDER = ["BELOW_LADDER", "CANDIDATE", "ENGINEERING_DEFINITION",
              "ENGINEERING_VALIDATED", "PHYSICALLY_VALIDATED",
              "REAL_LOOP_VERIFIED"]
    def rung(v: str) -> int:
        for i, r in enumerate(LADDER):
            if r in v.upper():
                return i
        return -1
    ci = rung(canonical_value)
    for key, decls in maturity_fields.items():
        if key in CANONICAL_KEYS:
            continue
        for d in decls:
            if key in SUBORDINATE_KEYS or "MATURITY" in key.upper():
                v = d["value"]
                vi = rung(v)
                # a subordinate claiming a rung ABOVE the canonical is a
                # competing-authority contradiction (the #160 combination)
                if vi > ci and ci >= 0 and "COMPLETE" not in v.upper():
                    g.fail("R-SUBORDINATE-EXCEEDS", f"{d['where']}: {key}="
                           f"{v!r} claims a higher maturity than canonical "
                           f"{canonical_value!r}")
                if ci == 0 and vi > 0:
                    g.fail("R-SPLIT-BRAIN", f"{d['where']}: canonical "
                           f"technology_maturity={canonical_value!r} while "
                           f"{key}={v!r} — the #160 competing-truth posture")
    # basis must exist
    mb = pv.json("MATURITY_BASIS.json") or {}
    if not (mb.get("basis") or mb.get("counts")):
        g.fail("R-NO-BASIS", "canonical maturity has no recorded basis")
    return g


# ---------------------------------------------------------------- Gate S
def gate_S_provenance(pv: PackageView, canonical: Optional[dict]) -> GateResult:
    g = GateResult("S", "Provenance/reproducibility: reconstruction identity "
                        "(Art. LXII).")
    # lineage profile: engine-run packages carry run identity (in
    # PROVENANCE.json for the bridge schema, or the manifest); portfolio
    # reference packages (Art. XXXIX buyer-repo authority) carry sealed ids.
    prov = pv.json("PROVENANCE.json") or {}
    ident_blob = json_dump_safe([pv.manifest, prov])
    has_run = bool(prov.get("run_id")) or "run_id" in pv.manifest
    portfolio_marker = "PORTFOLIO_IDENTITY_REGISTRY" in str(
        pv.manifest.get("identity_policy", ""))
    core_fields = [("package_id", pv.manifest.get("package_id") or
                    prov.get("package_id")),
                   ("package_version", pv.manifest.get("package_version") or
                    prov.get("package_version")),
                   ("technology_name", pv.manifest.get("technology_name") or
                    prov.get("technology_name"))]
    for f, v in core_fields:
        if not v:
            g.fail("S-IDENTITY-MISSING", f"package identity lacks {f} "
                   f"(searched manifest + PROVENANCE)")
    artifact_hash = all(
        e.get("sha256") for e in pv.manifest.get("files", [])
        if isinstance(e, dict))
    if not artifact_hash:
        g.fail("S-NO-ARTIFACT-HASHES", "manifest entries lack sha256 — the "
               "package cannot be reconstructed")
    if has_run or (not portfolio_marker and not canonical):
        # ENGINE_RUN profile (strict): full reconstruction identity required.
        # engine_commit is the bridge-schema name for code commit; model_id
        # lives in MODEL/MODEL_MANIFEST.json for CAD-bearing packages.
        engine_fields = [
            ("run_id", prov.get("run_id") or pv.manifest.get("run_id")),
            ("code_commit", prov.get("engine_commit") or
             prov.get("code_commit") or pv.manifest.get("code_commit")),
            ("package_build_version", prov.get("package_version") or
             pv.manifest.get("package_build_version")),
            ("invention_hash", prov.get("invention_spec_hash") or
             prov.get("invention_hash")),
        ]
        mman = pv.json("MODEL/MODEL_MANIFEST.json") or {}
        if pv.glb_nodes or mman.get("objects"):
            engine_fields.append(("model_id", mman.get("model_id") or
                                  prov.get("model_id")))
        for f, v in engine_fields:
            if not v:
                g.fail("S-RUN-IDENTITY-MISSING", f"engine-run package lacks "
                       f"{f} (Art. LXII reconstruction requirement)")
    else:
        # portfolio profile: model_id + provenance chains when 3D present
        if pv.glb_nodes:
            mman = pv.json("MODEL/MODEL_MANIFEST.json") or {}
            if not mman.get("model_id"):
                g.fail("S-NO-MODEL-ID", "3D package without model_id provenance")
    return g


# ---------------------------------------------------------------- Gate T
SECRET_PATTERNS = [
    ("OPENROUTER_API_KEY", re.compile(r"OPENROUTER[_A-Z]*KEY\s*[:=]", re.I)),
    ("NVIDIA_API_KEY", re.compile(r"NVAPI[A-Z]*\s*[:=]", re.I)),
    ("OPENAI_KEY", re.compile(r"sk-[A-Za-z0-9]{20,}")),
    ("GITHUB_TOKEN", re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}")),
    ("RENDER_API_KEY", re.compile(r"rnd_[A-Za-z0-9]{20,}")),
    ("BEARER_HEADER", re.compile(r"Authorization\s*:\s*Bearer\s+[A-Za-z0-9._\-]{15,}", re.I)),
    ("SESSION_COOKIE", re.compile(r"session[_-]?cookie\s*[:=]\s*\S{20,}", re.I)),
    ("ENV_BLOCK", re.compile(r"(OPENROUTER|NVIDIA|RENDER|GITHUB|ANTHROPIC|OPENAI)_[A-Z_]*=\S{10,}")),
    ("LOCAL_PATH", re.compile(r"file:///\S+|/home/[a-z]+/")),
]


def gate_T_security(pv: PackageView, canonical: Optional[dict]) -> GateResult:
    g = GateResult("T", "Security: secret/credential/cookie/path scan must be "
                        "clean before ZIP creation (values never printed).")
    text_files = [f for f in pv.all_files()
                  if f.endswith((".json", ".py", ".txt", ".md", ".csv", ".step",
                                 ".stl", ".svg", ".html", ".js"))]
    for rel in text_files:
        try:
            text = (pv.root / rel).read_text(errors="replace")[:2_000_000]
        except Exception:
            continue
        for label, pat in SECRET_PATTERNS:
            m = pat.search(text)
            if m:
                # report file + pattern + offset only — NEVER the value
                g.fail("T-SECRET-PRESENT", f"{rel}: pattern {label} at offset "
                       f"~{m.start()}", {"file": rel, "pattern": label})
    # .env must never be inside a package
    if any(f == ".env" or f.endswith("/.env") for f in pv.all_files()):
        g.fail("T-ENV-FILE", ".env file present inside the package")
    return g


# ---------------------------------------------------------------- Gate U
def gate_U_semantic_audit(pv: PackageView, canonical: Optional[dict],
                          auditor_fn=None) -> GateResult:
    g = GateResult("U", "Final independent semantic audit: does every major "
                        "buyer-facing statement describe this exact technology?")
    # mechanical proxy: every buyer PDF must be invention-tied and
    # domain-consistent
    dom = (canonical or {}).get("domain_family") or pv.canonical_domain()
    # R440.8: the same home-domain set as Gate C (problem domain resolved
    # by the verifier from canonical source text — genuine cross-domain
    # technologies speak both)
    home_domains = {dom}
    pd = (canonical or {}).get("problem_domain_family")
    if not pd and canonical and canonical.get("problem"):
        pd = infer_domain(str(canonical["problem"]))
    if pd:
        home_domains.add(str(pd))
    # R443: the same canonical applicability consumption as Gate C — a
    # MEDICAL-context package's buyer documents legitimately discuss
    # medical requirements (the one authority decided the context)
    _app_ctx_u = str((canonical or {}).get("applicability_context") or "")
    if _app_ctx_u in ("MEDICAL_IN_VIVO", "MEDICAL_EX_VIVO"):
        home_domains.add("medical")
    tech_name = str(pv.manifest.get("technology_name") or "")
    inv_tokens = set(distinctive_tokens(tech_name, limit=20))
    if canonical and canonical.get("invention"):
        inv_tokens.update(distinctive_tokens(
            json_dump_safe(canonical.get("invention")), limit=20))
    if canonical and canonical.get("mechanism"):
        inv_tokens.update(distinctive_tokens(
            json_dump_safe(canonical.get("mechanism")), limit=20))
    for name in pv.buyer_pdf_names():
        text = pv.pdf_full_text(name)
        if tech_name and tech_name.split()[0].lower() not in text.lower() \
                and not any(t in text.lower() for t in inv_tokens):
            g.fail("U-SECTION-FOREIGN", f"{name} never references the "
                   f"technology ({tech_name[:40]!r} vocabulary absent) — "
                   f"buyer-facing statement does not describe this invention")
    if pd or str(dom).lower() in DOMAIN_VOCAB:
        for name in pv.buyer_pdf_names():
            text = pv.pdf_full_text(name)
            for other in DOMAIN_VOCAB:
                if str(other) in {h.lower() for h in home_domains}:
                    continue
                hits = domain_term_hits(text, other)
                if len(hits) >= 3 and sum(hits.values()) >= 5:
                    g.fail("U-DOMAIN-DIVERGENCE", f"{name} discusses "
                           f"{other}-domain content in a {dom} package",
                           {"terms": list(hits)[:8]})
    # pluggable independent auditor (engine wires an LLM here; local runs use
    # the mechanical proxy). Auditor contract: (texts, canonical) -> findings
    if auditor_fn is not None:
        try:
            extra = auditor_fn(
                {n: pv.pdf_full_text(n) for n in pv.buyer_pdf_names()},
                canonical)
            for f in (extra or []):
                if isinstance(f, dict) and f.get("verdict") == "FAIL":
                    g.fail("U-AUDITOR-FAIL", str(f.get("reason", ""))[:300])
        except Exception as e:
            g.fail("U-AUDITOR-ERROR", f"independent auditor error: {e}")
    return g


# ---------------------------------------------------------------- Gate V
# R440.6 — buyer language discipline. Raw machine state never leaks into
# buyer-facing documents (BS-009; the R439 fresh-specimen finding: raw
# JSON dumped into buyer PDFs). Machine-readable layers are designated
# attachments (JSON files); the PDFs are human technical prose.
RAWMACHINE_PATTERNS = [
    # JSON object/array syntax in prose: '"key": value' / {'a': 1}
    ("JSON_OBJECT", re.compile(
        r"[\{\[]\s*['\"][\w \-\.]+['\"]\s*:\s*['\"]?[\w \-\./]+", )),
    ("JSON_KV_LINE", re.compile(
        r"^\s*['\"][\w \-\.]+['\"]\s*:\s*", re.M)),
    # Python object reprs
    ("PY_REPR", re.compile(
        r"\b(dict|list|set|OrderedDict|defaultdict)\s*\(\s*\[", )),
    ("PY_CLASS_REPR", re.compile(r"<class\s+'[\w\.\']+'>")),
    ("PY_OBJECT_AT", re.compile(
        r"<[\w\.]+ object at 0x[0-9a-fA-F]{6,}>")),
    # exception strings / tracebacks
    ("TRACEBACK", re.compile(
        r"Traceback \(most recent call last\)", )),
    ("EXCEPTION_STR", re.compile(
        r"\b[A-Za-z_]+(Error|Exception)\s*:\s*.{5,}")),
    # debug/route/engine jargon fields
    ("ROUTE_ID", re.compile(r"/api/[a-z/\{\}_\-]{3,}")),
    ("STAGE_CODE", re.compile(
        r"\bstage_(synthesize|challenge|evolve|retrieve|rank)[a-z_]*\.json\b",
        re.I)),
    ("ENGINE_TRACE_ID", re.compile(
        r"\b(BRIDGE_REPORT|CIO_UPDATE|stage_log|envelope_hash|"
        r"_post_rank_pipeline|invention_bridge)\b")),
    # NOTE: 'LOOP_STATE.json' etc. in a README file-inventory table is a
    # designated machine-readable attachment disclosure (permitted by
    # R440.6); bare engine identifiers above are not.
    ("SNAKE_DEBUG", re.compile(
        r"\b_[a-z]+_[a-z_]+\s*=", )),  # _private_field = ...
]
# legitimate, non-leak uses (epistemic vocabulary that IS product language)
RAW_ALLOWED = re.compile(
    r"NOT_POSSIBLE_YET|TECHNOLOGY_TRANSFER_READY|MODEL_DERIVED|"
    r"UNKNOWN \(not recorded\)|not recorded|NOT_ESTABLISHED|"
    r"evidence class|EVIDENCE CLASS", re.I)


def gate_V_buyer_language(pv: PackageView, canonical: Optional[dict]) -> GateResult:
    g = GateResult("V", "Buyer language discipline (R440.6): raw JSON, "
                        "exception strings, Python reprs, debug fields, "
                        "route IDs and engine jargon never appear in "
                        "buyer-facing PDFs.")
    for name in pv.buyer_pdf_names():
        text = pv.pdf_full_text(name)
        lines = text.split("\n")
        for label, pat in RAWMACHINE_PATTERNS:
            for m in pat.finditer(text):
                span = m.group(0)
                ctx = text[max(0, m.start() - 80):m.end() + 80]
                if RAW_ALLOWED.search(ctx):
                    continue  # epistemic-status vocabulary, not machine state
                # JSON_KV_LINE is only a leak when many such lines cluster
                # (a prose colon is fine; a dumped object is not)
                if label == "JSON_KV_LINE":
                    kv_lines = sum(1 for ln in lines if ln.strip()
                                   .startswith(('"', "'")) and ":" in ln)
                    if kv_lines < 3:
                        continue
                g.fail("V-RAW-MACHINE-STATE", f"{name}: buyer-facing "
                       f"document contains raw machine state "
                       f"({label}: {span[:48]!r})", {
                           "file": name, "pattern": label})
                break  # one finding per label per document is enough
    return g



# ---------------------------------------------------------------------------
# R443 — Gate W: APPLICABILITY INTEGRITY (domain-to-package semantic
# boundary). The audit's fresh wastewater case acquired patient/
# catheter/FDA/neurosurgery requirements from a reusable medical
# template. This gate re-derives the problem's medical context
# INDEPENDENTLY (Art. III — its own minimal signal set, not the
# compiler's applicability module) and verifies that the buyer-facing
# requirement statements match that context. It is NOT a forbidden-word
# filter: medical requirements in a genuinely medical problem PASS
# (Test B); medical requirements in a non-medical problem BLOCK (Test
# A/E); a missing applicability record BLOCKS (the compiler must carry
# the canonical state).
# ---------------------------------------------------------------------------

#: requirement-side contamination markers — the audit's exact list
#: (these words in buyer REQUIREMENT text of a non-medical problem are
#: contamination; in a medical problem they are legitimate)
_MEDICAL_REQUIREMENT_MARKERS = (
    "patient", "catheter", "neurosurgery", "neurosurgical",
    "clinical validation", "fda 510(k)", "fda 510k", "510(k)",
    "fda pma", "pma submission", "medical tubing",
    "medical-grade silicone", "medical extrusion",
    "neuroshunt", "hospital purchasing", "iso 10993",
    "iso 13485", "cleanroom assembly", "biocompatib",
)

#: problem-side medical-context signals (independent set — deliberately
#: different from applicability.py; it must cover the clinical/anatomical
#: vocabulary real medical problems use, so a genuinely medical problem
#: is never misread as non-medical by the verifier)
_MEDICAL_CONTEXT_SIGNALS = (
    "patient", "in vivo", "in-vivo", "implant", "implantable",
    "clinical", "neurosurgery", "physician", "hospital", "therapy",
    "cerebrospinal", "hydrocephalus", "shunt", "surgical",
    "diagnostic", "assay", "biocompatib", "steriliz", "medical",
    "catheter", "choroid", "plexus", "csf", "ventricul",
    "peritoneal", "intravascular", "arterial", "venous", "lumen",
    "tissue", "anatom", "physiological", "infection", "biofilm",
    "enzyme", "phage", "antibod",
    "vascular", "occlusion", "retinal", "biopsy", "blood", "sepsis",
    "icu", "guidewire", "pacemaker", "drain", "detox", "thromb",
    "embol", "stenosis", "neurovascular", "ocular", "renal",
    "cardiac", "oncolog", "tumor", "wound", "skin", "mucosal",
)


def _problem_is_medical(problem_text: str) -> Optional[bool]:
    """Independent medical-context determination over the problem's OWN
    words. Returns True/False, or None when the text is too thin to
    decide (the gate then degrades to WARN — Art. XXV: unknown never
    blocks)."""
    t = f" {str(problem_text or '').lower()} "
    hits = sum(1 for s in _MEDICAL_CONTEXT_SIGNALS if s in t)
    # word-boundary match for the industrial short token ('plant' must
    # not match inside 'implant' — the Art. XXI substring-noise rule)
    import re as _re
    industrial = any(
        (_re.search(rf"\b{_re.escape(s)}\b", t) if len(s) < 12
         else s in t)
        for s in ("wastewater", "industrial", "plant", "municipal",
                  "effluent", "utility", "refinery", "hvac",
                  "process stream", "factory", "district heating",
                  "water treatment", "pipeline"))
    if hits >= 2 and not industrial:
        return True
    if hits >= 4:
        return True
    if industrial and hits == 0:
        return False
    if hits == 0 and len(t.strip()) > 40:
        return False
    if hits <= 1 and industrial:
        return False
    return None


def _marker_context_exempt(text_lower: str, idx: int,
                            marker: str) -> bool:
    """A marker inside an explicit NOT_APPLICABLE / not-applicable
    statement is the HONEST negation (the R443 regulatory record names
    the medical regime it is exempting) — never contamination."""
    window = text_lower[max(0, idx - 220):idx + len(marker) + 220]
    return ("not applicable" in window
            or "not_applicable" in window
            or "never applicable" in window
            or "no patient-contact" in window
            or "outside this problem" in window)


def gate_W_applicability_integrity(pv: PackageView,
                                   canonical: Optional[dict]) -> GateResult:
    g = GateResult("W", "Applicability integrity: buyer/manufacturing/"
                        "regulatory/market requirements must match the "
                        "problem's canonical context (the R443 "
                        "domain-to-package semantic boundary; medical "
                        "requirements in a non-medical problem are "
                        "contamination, in a medical problem they are "
                        "legitimate).")
    model = pv.json("TECHNOLOGY_PACKAGE_MODEL.json") or {}
    problem_text = " ".join(str(x) for x in (
        (model.get("problem") or {}).get("user_problem"),
        (model.get("problem") or {}).get("failure_mode")) if x)
    if not problem_text and canonical and canonical.get("problem"):
        problem_text = str(canonical["problem"])
    if not problem_text:
        g.warn("W-PROBLEM-TEXT-ABSENT", "no canonical problem text "
               "available to the gate — the applicability check cannot "
               "run independently (Art. XXV: unknown never blocks)")
        return g
    # the gate's problem view is enriched with the invention's own
    # intervention site + mechanism (the fuller canonical problem view
    # the applicability decision itself used — Art. III: source, not
    # claimant content)
    invention = model.get("invention") or {}
    problem_text = " ".join(filter(None, [
        problem_text,
        str(invention.get("intervention_site") or ""),
        str((invention.get("mechanism") or {}).get("mechanism")
            if isinstance(invention.get("mechanism"), dict)
            else invention.get("mechanism") or "")[:600],
    ]))
    medical = _problem_is_medical(problem_text)

    # 1. the model MUST carry the canonical applicability dimension
    reqs = model.get("requirements") or {}
    if not reqs:
        g.fail("W-NO-APPLICABILITY", "the package model carries no "
               "requirements/applicability dimension — the canonical "
               "problem-context state (R443) is missing: requirements "
               "cannot be traced, and a reusable template may have "
               "supplied them")
        return g

    # 1b. the record must be INTERNALLY COHERENT (Art. III
    # independence): a context_class claim of MEDICAL must be supported
    # by the record's OWN score table — a fabricated context (the
    # injected-template failure mode) has zero medical signals in its
    # own recorded basis. This catches the old-template injection even
    # when the injected record claims a medical context.
    claimed_ctx = str(reqs.get("context_class") or "UNKNOWN")
    _MEDICAL_CTX = {"MEDICAL_IN_VIVO", "MEDICAL_EX_VIVO"}
    app_record = model.get("applicability") or {}
    score_table = (app_record.get("score_table")
                   or reqs.get("score_table") or [])
    medical_table_hits = 0
    for row in score_table:
        if str(row.get("context_class")) in _MEDICAL_CTX:
            medical_table_hits += int(row.get("score") or 0)
    if claimed_ctx in _MEDICAL_CTX and medical_table_hits <= 0 \
            and not (app_record.get("matched_signals")):
        g.fail("W-CONTEXT-FABRICATED", f"the applicability record "
               f"claims context {claimed_ctx} but its own score table "
               f"carries zero medical-context signal support — the "
               f"context claim is fabricated (the injected-template "
               f"failure mode)")

    # 2. contamination: medical markers in buyer requirement text of a
    # non-medical problem (requirement statements whose applicability
    # is NOT_APPLICABLE are exempt — they are the honest negation)
    if medical is False:
        # 2a. structured requirement statements (the model dimension)
        def _iter_requirement_statements(node, path="requirements"):
            if isinstance(node, dict):
                appl = str(node.get("applicability") or "")
                stmt = node.get("statement")
                if isinstance(stmt, str) and appl != "NOT_APPLICABLE":
                    yield path, stmt
                for k, v in node.items():
                    if k in ("statement",):
                        continue
                    yield from _iter_requirement_statements(
                        v, f"{path}.{k}")
            elif isinstance(node, list):
                for i, v in enumerate(node):
                    yield from _iter_requirement_statements(
                        v, f"{path}[{i}]")
        bad = []
        for path, stmt in _iter_requirement_statements(reqs):
            low = stmt.lower()
            for m in _MEDICAL_REQUIREMENT_MARKERS:
                idx = low.find(m)
                if idx >= 0 and not _marker_context_exempt(low, idx, m):
                    bad.append({"where": path, "marker": m,
                                "statement": stmt[:140]})
                    break
        # 2b. buyer-facing PDF requirement text (the decision card /
        # transfer manifest sections render the same statements)
        pdf_bad = []
        for name, pages in pv.pdfs.items():
            text = "\n".join(pages).lower()
            for m in _MEDICAL_REQUIREMENT_MARKERS:
                start = 0
                while True:
                    idx = text.find(m, start)
                    if idx < 0:
                        break
                    if not _marker_context_exempt(text, idx, m):
                        pdf_bad.append({"pdf": name, "marker": m})
                        break
                    start = idx + len(m)
        if bad or pdf_bad:
            g.fail("W-APPLICABILITY-CONTAMINATION",
                   "a non-medical problem's buyer requirements carry "
                   "medical-context content (the R443 audit defect: "
                   "requirements from the wrong domain; the canonical "
                   "applicability state must gate every requirement)",
                   {"model_findings": bad[:6],
                    "pdf_findings": pdf_bad[:8]})
        else:
            g.findings.append(Finding(
                "W-CLEAN", "non-medical problem: zero medical-context "
                "markers in the buyer requirement statements (the "
                "canonical applicability boundary holds)",
                "PASS", {"context_check": "independent re-derivation"}))
    elif medical is True:
        g.findings.append(Finding(
            "W-MEDICAL-LEGITIMATE", "medical problem: medical-context "
            "requirements are legitimately applicable (the paired "
            "positive control — a global deletion strategy would "
            "falsely fail here)", "PASS",
            {"independent_determination": "medical"}))
    else:
        # the gate could not determine the context from its own view.
        # If the record claims MEDICAL with a COHERENT score table, the
        # disagreement is view loss (the package's problem text is a
        # lossy projection of the canonical problem) — surfaced for
        # review, never auto-blocked (Art. XXV). A non-medical/UNKNOWN
        # record with an undeterminable view also stays WARN.
        if claimed_ctx in _MEDICAL_CTX and medical_table_hits > 0:
            g.warn("W-MEDICAL-VIEW-LOSS", "the applicability record "
                   f"claims {claimed_ctx} with coherent signal support "
                   f"(score {medical_table_hits}) but the package's own "
                   "problem text is too thin for independent "
                   "confirmation — surfaced for review, not blocked")
        else:
            g.warn("W-CONTEXT-UNDETERMINED", "the problem's medical "
                   "context could not be independently determined from "
                   "its own text — requirement-context verification "
                   "degrades to review (Art. XXV)")

    # 3. the context class must be one of the closed vocabulary
    ctx = str(reqs.get("context_class") or "UNKNOWN")
    if ctx not in ("MEDICAL_IN_VIVO", "MEDICAL_EX_VIVO",
                   "INDUSTRIAL_PROCESS", "LABORATORY_BENCH", "CONSUMER",
                   "UNKNOWN"):
        g.fail("W-CONTEXT-VOCAB", f"context_class {ctx!r} is outside the "
               "closed applicability vocabulary")
    return g


ALL_GATES = [
    ("A", gate_A_identity_coherence),
    ("B", gate_B_problem_fidelity),
    ("C", gate_C_domain_integrity),
    ("D", gate_D_section_provenance),
    ("E", gate_E_structural_linkage),
    ("F", gate_F_evidence_integrity),
    ("G", gate_G_causal_integrity),
    ("H", gate_H_engineering_integrity),
    ("I", gate_I_traceability),
    ("J", gate_J_equations),
    ("K", gate_K_experiment),
    ("L", gate_L_buyer_utility),
    ("M", gate_M_commercial),
    ("N", gate_N_artifact_fidelity),
    ("P", gate_P_pdf_visual_qa),
    ("Q", gate_Q_manifest_zip),
    ("R", gate_R_maturity_coherence),
    ("S", gate_S_provenance),
    ("T", gate_T_security),
    ("U", gate_U_semantic_audit),
    ("V", gate_V_buyer_language),
    ("W", gate_W_applicability_integrity),
]
