"""
equations.py — R371 Phase 6: typeset engineering mathematics.

Builds a per-package EQUATION_REGISTRY.json:
  equation_id, equation (canonical ASCII, verbatim), typeset (mathtext),
  variables (from critical parameters where recorded), units, applicability
  (governing-model boundary conditions), assumptions, source.

Rendering: canonical ASCII equations are converted DETERMINISTICALLY to
matplotlib mathtext and rendered to PNG at 300 dpi, embedded in the buyer
PDFs. The machine-readable JSON retains the canonical ASCII equation
verbatim. The PDF is the readable rendering, never the source of truth
(CEO Phase 6).

Deterministic conversion only (Art. II — no semantic rewriting):
  - greek letter names -> mathtext symbols
  - '*' -> centered dot; standalone '|' -> relation divider; '~' -> sim
  - '_seg' subscripts; multi-segment identifiers (k_cat_obs) render the
    subscript segments joined with commas (k_{cat,obs}) — every character
    of the canonical symbol is preserved
  - trailing '[description]' annotations and 'Label:' prefixes are split
    off as captions (the math is never altered)
  - mid-string bracket groups ([S] concentration notation) render literally
  - strings containing prose connectives fall back to verbatim monospace
  - corrupted canonical strings are preserved verbatim with a rendering
    note — never repaired (Art. VI: unknown stays unknown)
"""

import re

GREEK = {
    "alpha": r"\alpha", "beta": r"\beta", "gamma": r"\gamma",
    "delta": r"\delta", "epsilon": r"\epsilon", "eta": r"\eta",
    "theta": r"\theta", "lambda": r"\lambda", "mu": r"\mu",
    "nu": r"\nu", "pi": r"\pi", "rho": r"\rho", "sigma": r"\sigma",
    "tau": r"\tau", "phi": r"\phi", "omega": r"\omega",
}

FUNCTIONS = {"sum", "exp", "log", "ln", "min", "max", "sqrt",
             "sin", "cos", "tan", "det", "argmin", "argmax"}

# Prose connectives: if any appear (as words) the string is a sentence,
# not an equation -> verbatim fallback.
_PROSE_WORDS = re.compile(
    r"\b(for|in|via|with|and|or|over|under|at which|where|if|updated|via)\b"
)


def _is_annotation_group(group: str) -> bool:
    """Is a TRAILING bracket group a prose annotation (strip it) or
    math notation (keep it)? Deterministic, corpus-verified rules:

    KEEP as math notation:
      [S] / [A]            single short symbol (len <= 3)
      [Phage] / [Bacteria] single CAPITALIZED token (species/symbol)
      [t_critical]         underscore-bearing identifier
      [0] / [1, 2]         numeric intervals
    STRIP as annotation (prose):
      [parallel conductance]           multi-word phrase (any plain word
                                       >= 3 chars without underscore)
      [laminar if Re < 2300]           condition note (multi-word)
      [proposed controller law, MODELLED]  comma-bearing prose
      [Starling/Kedem-Katchalsky]      model-name citation (single token
                                       with '/', len >= 8)
      [prediction]                     single lowercase prose word
    """
    segs = group.split()
    if not segs:
        return False
    if len(segs) == 1:
        s = segs[0]
        if len(s) <= 3:
            return False                       # [S], [A], [B2]
        if "_" in s:
            return False                       # [t_critical]
        if s.replace(",", "").replace(".", "").isdigit():
            return False                       # [0], [1]
        if any(c.isdigit() for c in s):
            return False                       # numeric-bearing
        if s[0].isupper() and "/" not in s:
            return False                       # [Phage], [Bacteria]
        if "/" in s and len(s) >= 8:
            return True                        # [Starling/Kedem-Katchalsky]
        return s.isalpha() and s[0].islower()  # [prediction]
    # multi-segment: annotation iff it contains a plain prose word
    for s in segs:
        w = s.strip(",.").rstrip(";:")
        if len(w) >= 3 and w.isalpha() and not w[0].isupper():
            return True                        # 'parallel', 'enzyme', ...
        if len(w) >= 4 and w.isalpha() and w[0].isupper() \
                and "_" not in w and w not in ("Re",):
            # capitalized prose words in multi-word phrases ('MODELLED',
            # 'Hagen' in 'Hagen-Poiseuille per segment') — annotation only
            # when the segment count >= 3 (a phrase, not symbol pairs)
            if len(segs) >= 3:
                return True
    return False


def split_annotation(eq: str):
    """Split trailing bracketed ANNOTATIONS from an equation string.

    Canonical strings carry trailing descriptions such as
    'dP_damper = c_h * Q [hydraulic damping]' — and P-07's EQ-3 carried
    TWO ('G_total = G_primary + G_floor [parallel conductance] [P-07 …]'),
    which left an annotation inside the math expression and broke the
    structural parse (found live by the R394 CEO audit). P-02's EQ-4
    carried a comma-bearing prose annotation; P-26 a model-name
    citation. Rule (recorded, deterministic): a TRAILING bracket group
    is stripped iff it is a PROSE annotation per _is_annotation_group;
    math notation ([S] concentration, [0, t_critical] intervals) is
    never stripped. Multiple trailing annotations are stripped
    iteratively.

    Where the recorded string is corrupted (e.g. a missing opening
    bracket), the tail is returned as annotation with a corruption note
    — never silently repaired (Art. VI).
    """
    eq = eq.strip()
    annotations = []
    while True:
        m = re.search(r"\s*\[([^\]]*)\]\s*$", eq)
        if not m:
            break
        group = m.group(1)
        if not _is_annotation_group(group):
            break  # math notation (concentration / interval) — keep it
        annotations.insert(0, group)
        eq = eq[: m.start()].rstrip()
    if annotations:
        return eq, " ".join(a.strip() for a in annotations if a.strip()), None
    if "]" in eq and "[" not in eq.split("]")[0]:
        # CORRUPTED canonical data: the math/annotation boundary cannot be
        # recovered without guessing (Art. II/VI). The whole string is
        # returned untouched and rendered VERBATIM.
        return eq, "", "CORRUPTED_CANONICAL_STRING_RENDERED_VERBATIM"
    return eq, "", None


def split_label(math_part: str):
    """Split a 'Label:' prefix (e.g. 'Settling time: tau = I_h / c_h')."""
    if ":" in math_part:
        idx = math_part.index(":")
        left, right = math_part[:idx].strip(), math_part[idx + 1 :].strip()
        # only treat as label if the left side has no math operators
        # ('-' excluded: hyphenated words like 'Beer-Lambert' are labels)
        if left and not re.search(r"[=<>*/+]", left):
            return left, right
    return "", math_part


def _ident_to_mathtext(name: str) -> str:
    """Convert an ASCII identifier (possibly multi-underscore) to mathtext."""
    if name in GREEK:
        return GREEK[name]
    if "_" in name:
        base, *segs = name.split("_")
        base_r = _ident_to_mathtext(base) if base else ""
        sub = ",".join(s for s in segs if s)
        return f"{base_r}_{{{sub}}}"
    m = re.fullmatch(r"([A-Za-z]+[a-z]*?)(\d+)", name)
    if m:
        return f"{m.group(1)}_{{{m.group(2)}}}"
    return name


def _tokenize(s: str):
    """Yield tokens: identifiers (incl. underscore segments and scripts),
    numbers, bracket groups, and single symbols."""
    pos, n = 0, len(s)
    while pos < n:
        ch = s[pos]
        if ch.isspace():
            pos += 1
            continue
        if ch == "[":
            close = s.find("]", pos)
            if close == -1:
                yield ("SYM", "[")
                pos += 1
                continue
            yield ("BRACKET", s[pos + 1 : close])
            pos = close + 1
            continue
        m = re.match(r"[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)*", s[pos:])
        if m:
            yield ("IDENT", m.group(0))
            pos += m.end()
            continue
        m = re.match(r"\d+\.?\d*", s[pos:])
        if m:
            yield ("NUM", m.group(0))
            pos += m.end()
            continue
        if s[pos] in "^_":
            m2 = re.match(r"\^\{[^}]*\}|_\{[^}]*\}|\^[A-Za-z0-9]+|_[A-Za-z0-9]+", s[pos:])
            if m2:
                yield ("SCRIPT", m2.group(0))
                pos += m2.end()
                continue
        yield ("SYM", ch)
        pos += 1


def ascii_to_mathtext(eq_ascii: str):
    """Deterministic ASCII -> mathtext conversion.

    Returns (mathtext, note). note is None on success.
    Only syntactic transformation — never semantic.
    """
    s = eq_ascii.strip()
    if not s:
        return None, "EMPTY"
    if re.search(r"[;]", s) or re.search(r"\s{2,}", s):
        return None, "CONTAINS_PROSE"
    if _PROSE_WORDS.search(s):
        return None, "CONTAINS_PROSE"
    out = []
    tokens = list(_tokenize(s))
    i = 0
    while i < len(tokens):
        kind, val = tokens[i]
        if kind == "IDENT":
            rendered = (
                r"\mathrm{" + val + "}" if val in FUNCTIONS
                else _ident_to_mathtext(val)
            )
            # attach immediately-following script tokens
            while i + 1 < len(tokens) and tokens[i + 1][0] == "SCRIPT":
                i += 1
                sc = tokens[i][1]
                op, arg = sc[0], sc[1:].strip("{}")
                arg = _ident_to_mathtext(arg) if arg in GREEK else arg
                rendered += f"{op}{{{arg}}}"
            out.append(rendered)
        elif kind == "NUM":
            out.append(val)
        elif kind == "BRACKET":
            inner = ascii_to_mathtext(val)
            if inner[0] is None:
                return None, f"UNCONVERTIBLE_BRACKET:{val}"
            body = inner[0].strip("$")
            grp = f"\\left[ {body} \\right]"
            while i + 1 < len(tokens) and tokens[i + 1][0] == "SCRIPT":
                i += 1
                sc = tokens[i][1]
                op, arg = sc[0], sc[1:].strip("{}")
                grp += f"{op}{{{arg}}}"
            out.append(grp)
        elif kind == "SCRIPT":
            return None, "SCRIPT_WITHOUT_BASE"
        else:  # SYM
            if val == "(":
                out.append(r"\left(")
            elif val == ")":
                out.append(r"\right)")
            elif val == "*":
                out.append(r"\cdot")
            elif val == "|":
                out.append(r"\mid")
            elif val == "~":
                out.append(r"\sim")
            elif val in ("+", "-", "=", "<", ">", ",", ".", "/", "%"):
                out.append(val)
            elif val == "^" or val == "_":
                # script operator directly (e.g. cm^-1)
                m2 = re.match(r"[A-Za-z0-9{}]+|\{[^}]*\}", s)  # next token read below
                if i + 1 < len(tokens):
                    nk, nv = tokens[i + 1]
                    if nk in ("IDENT", "NUM"):
                        arg = _ident_to_mathtext(nv) if nk == "IDENT" and nv in GREEK else nv
                        if out:
                            out[-1] += f"{val}{{{arg}}}"
                            i += 1
                        else:
                            return None, "SCRIPT_WITHOUT_BASE"
                    else:
                        return None, f"DANGLING_SCRIPT:{val}"
                else:
                    return None, f"DANGLING_SCRIPT:{val}"
            elif val == "^" :
                return None, "DANGLING_SCRIPT"
            else:
                return None, f"UNCONVERTIBLE_SYMBOL:{val}"
        i += 1
    if not out:
        return None, "EMPTY"
    return "$" + " ".join(out) + "$", None


def render_equation_png(mathtext: str, out_path: str, dpi: int = 300) -> str:
    """Render a mathtext string to a tightly-cropped PNG."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig = plt.figure(figsize=(8, 0.7))
    fig.patch.set_facecolor("white")
    fig.text(0.5, 0.5, mathtext, ha="center", va="center", fontsize=15)
    fig.savefig(out_path, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return out_path


#: equation typeset source font size (points) — used by the R375 measured
#: embed to compute the EFFECTIVE glyph size after scaling.
EQ_SOURCE_FONTSIZE = 15.0
EQ_SOURCE_DPI = 300


def measured_equation_image(png_path: str, frame_pt: float = 504.0,
                            floor_pt: float = 8.0):
    """R375-3/7: embed an equation PNG at a MEASURED size.

    The PNG was rendered at EQ_SOURCE_FONTSIZE pt glyphs. Its natural
    width in points is px / dpi * 72. The embed width is the natural size
    capped at frame_pt — but if capping would push the effective glyph
    size below floor_pt, the equation is too long for a readable one-line
    image and (None, note) is returned so the caller falls back to the
    verbatim canonical string as wrapping monospace text. Equations are
    never shipped unreadably shrunken.
    """
    from PIL import Image as _PILImage
    from reportlab.platypus import Image as _RLImage

    with _PILImage.open(png_path) as im:
        px_w = im.size[0]
    natural_pt = px_w / EQ_SOURCE_DPI * 72.0
    embed_pt = min(natural_pt, frame_pt)
    effective = EQ_SOURCE_FONTSIZE * embed_pt / natural_pt
    if effective < floor_pt:
        return None, (f"effective glyph size {effective:.1f}pt would fall "
                      f"below the {floor_pt:.0f}pt floor at page width")
    return _RLImage(png_path, width=embed_pt,
                    height=embed_pt * _pil_height_ratio(png_path)), None


def _pil_height_ratio(png_path: str) -> float:
    from PIL import Image as _PILImage
    with _PILImage.open(png_path) as im:
        w, h = im.size
    return h / w


def build_equation_registry(pkg) -> dict:
    """EQUATION_REGISTRY.json content for one package."""
    from .canonical_source import apply_mutations
    entries = []
    assumptions = pkg.gm.get("assumptions", [])
    boundary = pkg.gm.get("boundary_conditions", [])
    # R373-5 fix: the registry is a BUYER-SHIPPED JSON — its rendered prose
    # carries the V2 state (the R373 chain audit caught the stale V1
    # 'Neuromorphic ML predictor' summary here). The equation strings
    # themselves stay verbatim canonical.
    summary = apply_mutations(pkg.gm.get("summary", ""), pkg.addendum)

    for i, eq in enumerate(pkg.equations, start=1):
        math_part, annotation, corrupt_note = split_annotation(eq)
        if corrupt_note:
            # corrupted canonical string: VERBATIM rendering, no typesetting
            mathtext, conv_note = None, corrupt_note
        else:
            label, math_part = split_label(math_part)
            mathtext, conv_note = ascii_to_mathtext(math_part)
        captions = " ".join(x for x in (annotation,) if x)
        entry = {
            "equation_id": f"EQ-{i}",
            "equation_canonical": eq,  # verbatim, never rewritten
            "math_expression": math_part,
            "caption": captions,
            "typeset": mathtext,
            "rendering": "TYPESET_MATHEXT" if mathtext else "VERBATIM_MONOSPACE",
            "rendering_note": corrupt_note or conv_note,
            "variables": _variables_for(math_part, pkg),
            "units": _units_for(pkg),
            "applicability": boundary,
            "assumptions": assumptions,
            "source": {
                "origin": "governing_model.equations (R370Q canonical "
                          "export; V2-mutation-aware rendering)",
                "summary": summary,
            },
        }
        entries.append(entry)

    return {
        "package_id": pkg.pkg_id,
        "portfolio_number": pkg.num,
        "equation_count": len(entries),
        "discipline": (
            "Canonical equation strings are retained verbatim; the PDF "
            "renders a typeset form generated deterministically from them. "
            "Where a canonical string carries a corrupted annotation tail, it "
            "is preserved verbatim with a rendering note — never repaired."
        ),
        "model_summary": summary,
        "equations": entries,
    }


def _variables_for(expr: str, pkg) -> list:
    """Match recorded critical parameters to symbols appearing in the
    expression. Only recorded parameters are listed — no invention."""
    found = []
    compact = expr.replace(" ", "")
    for cp in pkg.critical_parameters:
        name = (cp.get("name") or "").strip()
        for sym in re.findall(r"\b([A-Za-z][A-Za-z0-9_]{0,14})\b", name):
            base = sym.split("_")[0]
            if base and base in compact:
                found.append(
                    {
                        "symbol": sym,
                        "recorded_name": name,
                        "value": cp.get("value"),
                        "unit": cp.get("unit"),
                        "basis": cp.get("basis"),
                    }
                )
                break
    return found


def _units_for(pkg) -> list:
    units = []
    for cp in pkg.critical_parameters:
        u = cp.get("unit")
        if u and u not in units:
            units.append(u)
    return units
