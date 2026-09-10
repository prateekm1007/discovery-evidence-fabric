#!/usr/bin/env python3
"""pqg_view.py — Package loading + parsing layer for the R439 PACKAGE_QUALITY_GATE.

The gate is an INDEPENDENT VERIFIER (R439-3): it must not call the factory's
own helper functions. Everything it needs it re-derives from the completed
package directory / ZIP plus (optionally) the canonical invention state.

Supported inputs:
  - a package directory containing PACKAGE_MANIFEST.json
  - a package ZIP (extracted to a temp dir)
  - canonical invention state (dict or JSON file) for identity/fidelity gates

No engine imports. Standard library + pypdf/fitz only.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import struct
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Optional

try:
    import fitz  # PyMuPDF
except ImportError:  # pragma: no cover
    fitz = None

BUYER_PDF_PATTERN = re.compile(r"^\d+_.*\.pdf$")
KNOWN_EVIDENCE_CLASSES = [
    "SOURCE_FACT", "EXTERNAL_PRECEDENT", "AI_INFERENCE",
    "COMPUTATIONAL_RESULT", "PHYSICAL_OBSERVATION", "UNKNOWN", "UNCLASSIFIED",
]
CANONICAL_ID_PATTERNS = [
    re.compile(r"\bEQ-\d+\b"),
    re.compile(r"\bDI-\d+\b"),
    re.compile(r"\bDO-\d+\b"),
    re.compile(r"\bFM-\d+\b"),
    re.compile(r"\bWP-\d+\b"),
    re.compile(r"\bV-\d+\b"),
    re.compile(r"\bEXT-\d+\b"),
    re.compile(r"\bU-\d+\b"),
    re.compile(r"\bP-\d+\b"),
    # bridge/elite factory identity vocabulary: invention ids (inv...),
    # run ids (ts_...), problem ids (ui_...) — structural linkage to the
    # canonical invention record in either factory's id scheme
    re.compile(r"\binv[a-z0-9_]{16,}\b"),
    re.compile(r"\bts_[a-z0-9]{8,}\b"),
    re.compile(r"\bui_[a-z0-9_]{12,}\b"),
]
# R439 Gate E: tokens that prove NOTHING about invention linkage (the #160
# lexical-coincidence vocabulary: 'decision', 'domain', 'evidence', ...).
WEAK_TOKENS = {
    "decision", "domain", "evidence", "recorded", "source", "engine",
    "engineering", "status", "audit", "model", "system", "data", "analysis",
    "design", "technology", "problem", "record", "records", "package",
    "transfer", "buyer", "value", "values", "process", "control",
    "structure", "component", "components", "requirement", "requirements",
    "governing", "support", "supported", "result", "results",
    "based", "defined", "definition", "established", "unknown",
    "market", "commercial", "manufacturing", "clinical", "technical",
}


class Finding:
    """One verifier finding. Severity: FAIL blocks the ZIP; WARN is recorded."""

    def __init__(self, code: str, message: str, severity: str = "FAIL",
                 evidence: Optional[dict] = None):
        self.code = code
        self.message = message
        self.severity = severity
        self.evidence = evidence or {}

    def as_dict(self) -> dict:
        return {"severity": self.severity, "code": self.code,
                "message": self.message, "evidence": self.evidence}


class GateResult:
    def __init__(self, gate: str, description: str):
        self.gate = gate
        self.description = description
        self.findings: list[Finding] = []

    def fail(self, code: str, message: str, evidence: Optional[dict] = None):
        self.findings.append(Finding(code, message, "FAIL", evidence))

    def warn(self, code: str, message: str, evidence: Optional[dict] = None):
        self.findings.append(Finding(code, message, "WARN", evidence))

    @property
    def verdict(self) -> str:
        if any(f.severity == "FAIL" for f in self.findings):
            return "FAIL"
        if any(f.severity == "WARN" for f in self.findings):
            return "PASS_WITH_WARNINGS"
        return "PASS"

    def as_dict(self) -> dict:
        return {"gate": self.gate, "description": self.description,
                "verdict": self.verdict,
                "findings": [f.as_dict() for f in self.findings]}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_glb_nodes(data: bytes) -> list[str]:
    """Parse GLB first JSON chunk and return node names (independent parse)."""
    try:
        magic, _ver, _length = struct.unpack_from("<III", data, 0)
        if magic != 0x46546C67:  # 'glTF'
            return []
        clen, ctype = struct.unpack_from("<II", data, 12)
        if ctype != 0x4E4F534A:  # 'JSON'
            return []
        j = json.loads(data[20: 20 + clen].decode("utf-8", errors="replace"))
        return [n.get("name") for n in j.get("nodes", []) if n.get("name")]
    except Exception:
        return []


class PackageView:
    """Read-only, independently-parsed view of a completed package."""

    def __init__(self, source: str | Path, workdir: Optional[Path] = None):
        self.source = Path(source)
        self._tmp: Optional[Path] = None
        if self.source.is_dir():
            self.root = self.source
        elif self.source.suffix == ".zip":
            self._tmp = Path(tempfile.mkdtemp(prefix="pqg_"))
            with zipfile.ZipFile(self.source) as zf:
                zf.extractall(self._tmp)
            top = [p for p in self._tmp.iterdir()]
            # handle a single wrapping directory inside the zip
            if len(top) == 1 and top[0].is_dir():
                self.root = top[0]
            else:
                self.root = self._tmp
        else:
            raise ValueError(f"unsupported package source: {self.source}")
        self.workdir = workdir
        self.manifest = self._load_json("PACKAGE_MANIFEST.json") or {}
        # normalize the two historical manifest schemas (portfolio packages
        # use {"file": ...}; the bridge/elite factory uses {"path": ...} —
        # a split-brain artifact the canonical compiler must unify)
        files = self.manifest.get("files")
        if isinstance(files, list):
            for e in files:
                if isinstance(e, dict) and not e.get("file") and e.get("path"):
                    e["file"] = e["path"]
        self.json_files: dict[str, Any] = {}
        for p in sorted(self.root.rglob("*.json")):
            rel = str(p.relative_to(self.root))
            try:
                self.json_files[rel] = json.loads(p.read_text())
            except Exception:
                self.json_files[rel] = {"__parse_error__": str(p)}
        self.pdfs: dict[str, list[str]] = {}
        for p in sorted(self.root.glob("*.pdf")):
            self.pdfs[p.name] = self._pdf_pages_text(p)
        self.glb_nodes: dict[str, list[str]] = {}
        for p in sorted(self.root.rglob("*.glb")):
            self.glb_nodes[str(p.relative_to(self.root))] = parse_glb_nodes(p.read_bytes())

    # ------------------------------------------------------------------ load
    def _load_json(self, rel: str) -> Optional[dict]:
        p = self.root / rel
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text())
        except Exception:
            return None

    def json(self, rel: str) -> Optional[dict]:
        return self.json_files.get(rel)

    def all_files(self) -> list[str]:
        return sorted(str(p.relative_to(self.root)) for p in self.root.rglob("*")
                      if p.is_file())

    def file_bytes(self, rel: str) -> bytes:
        return (self.root / rel).read_bytes()

    # ------------------------------------------------------------------ pdf
    @staticmethod
    def _pdf_pages_text(path: Path) -> list[str]:
        # primary: fitz gives page-aligned text (no formfeed artifacts)
        try:
            import fitz
            doc = fitz.open(str(path))
            pages = [page.get_text() for page in doc]
            doc.close()
            if any(p.strip() for p in pages):
                return pages
        except Exception:
            pass
        try:
            out = subprocess.run(["pdftotext", "-layout", str(path), "-"],
                                 capture_output=True, timeout=120)
            full = out.stdout.decode("utf-8", errors="replace")
            if out.returncode == 0 and full.strip():
                pages = full.split("\f")
                # a trailing empty element after the final form feed is an
                # artifact of the split, not a real page
                while pages and not pages[-1].strip():
                    pages.pop()
                return pages
        except Exception:
            pass
        # fallback: pypdf
        try:
            from pypdf import PdfReader
            r = PdfReader(str(path))
            return [(pg.extract_text() or "") for pg in r.pages]
        except Exception:
            return []

    def pdf_full_text(self, name: str) -> str:
        return "\n".join(self.pdfs.get(name, []))

    def buyer_pdf_names(self) -> list[str]:
        return [n for n in self.pdfs if BUYER_PDF_PATTERN.match(n)]

    # ---------------------------------------------------------- evidence pdf
    def parse_evidence_class_table(self) -> dict[str, int]:
        """Parse the EVIDENCE CLASS DISCIPLINE table from the evidence PDF.

        Handles both layout modes: count on the same line (pdftotext
        -layout) or on the following line (plain extraction).
        """
        counts = {}
        for name, pages in self.pdfs.items():
            text = "\n".join(pages).replace("\r", "")
            if "EVIDENCE CLASS" not in text.upper():
                continue
            for cls in KNOWN_EVIDENCE_CLASSES:
                m = (re.search(rf"{cls}[ \t]*\n[ \t]*(\d+)\b", text)
                     or re.search(rf"{cls}[ \t]{{2,}}(\d+)\b", text))
                if m:
                    counts[cls] = int(m.group(1))
        return counts

    def parse_evidence_sources(self) -> list[dict]:
        """Parse 'Source N: title / URL: ... / Source hash: ... / Excerpt: ...'."""
        sources = []
        for name, pages in self.pdfs.items():
            text = "\n".join(pages)
            if "Source hash" not in text and "URL:" not in text:
                continue
            pattern = re.compile(
                r"Source (\d+):\s*(?P<title>.+?)\s*\n"
                r"URL:\s*(?P<url>.+?)\s*\n\s*Source hash:\s*(?P<hash>[0-9a-f]{16,})\s*\n"
                r"Excerpt:\s*(?P<excerpt>.+?)(?=\n\s*Source \d+:|\n\s*\Z)",
                re.S)
            for m in pattern.finditer(text):
                url = re.sub(r"\s+", "", m.group("url"))  # unwrap wrapped URLs
                sources.append({"file": name, "index": int(m.group(1)),
                                "title": m.group("title").strip(),
                                "url": url,
                                "hash": m.group("hash"),
                                "excerpt": m.group("excerpt").strip()[:300]})
        return sources

    # ------------------------------------------------------------ identity
    def declared_identity(self) -> dict[str, list[dict]]:
        """Collect identity declarations from every machine JSON + PDF text.

        Returns {field: [{where, value}]}.
        """
        out: dict[str, list[dict]] = {}
        ID_FIELDS = ["package_id", "portfolio_number", "technology_name",
                     "domain_family", "run_id", "invention_id", "problem_id",
                     "mechanism_id", "engineering_state_id", "experiment_id"]
        for rel, data in self.json_files.items():
            if not isinstance(data, dict) or "__parse_error__" in data:
                continue
            for f in ID_FIELDS:
                if f in data and data[f] not in (None, ""):
                    out.setdefault(f, []).append(
                        {"where": rel, "value": str(data[f])})
                # one-level-deep nested declarations (e.g. PROVENANCE.
                # canonical_invention_state_identity.invention_id)
                for k, v in data.items():
                    if isinstance(v, dict) and f in v and v[f] not in (None, ""):
                        out.setdefault(f, []).append(
                            {"where": f"{rel}:{k}", "value": str(v[f])})
        # identity from buyer PDFs (header lines)
        for name, pages in self.pdfs.items():
            if not pages:
                continue
            head = pages[0][:600]
            m = re.search(r"Package\s+(P-[0-9A-Za-z\-]+)", head)
            if m:
                out.setdefault("package_id_pdf", []).append(
                    {"where": name, "value": m.group(1)})
            m = re.search(r"Portfolio\s+(\d+)\s+of\s+(\d+)", head)
            if m:
                out.setdefault("portfolio_number_pdf", []).append(
                    {"where": name, "value": m.group(1)})
        return out

    def canonical_domain(self, provided: Optional[str] = None) -> Optional[str]:
        """Infer the package's canonical domain, WITHOUT buyer PDF text.

        Priority: explicit domain_family field > technology_name vocabulary >
        MODEL machine layer (objects/roles). Buyer PDF text is deliberately
        excluded: contaminated text must not be able to redefine the domain
        (the #160 lesson — stale evidence must not hijack identity).
        """
        if provided:
            return provided
        for rel, data in self.json_files.items():
            if isinstance(data, dict):
                for key in ("domain_family", "canonical_domain"):
                    v = data.get(key)
                    if isinstance(v, str) and v.strip():
                        return v.strip()
        tech_name = str(self.manifest.get("technology_name") or "")
        d = _best_domain(tech_name)
        if d:
            return d
        mman = self.json("MODEL/MODEL_MANIFEST.json") or {}
        model_readme = self.json("MODEL/README.json") or {}
        broader = (tech_name + " " + json.dumps(mman.get("objects", [])) +
                   " " + json_dump_safe(model_readme) + " " +
                   json_dump_safe(self.json("MODEL/KEY_DIMENSIONS.json") or {}))
        return _best_domain(broader)

    def cleanup(self):
        if self._tmp and self._tmp.exists():
            shutil.rmtree(self._tmp, ignore_errors=True)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.cleanup()


# ----------------------------------------------------------------- domains
# Distinctive vocabulary per domain. Terms chosen to be domain-DISTINCTIVE
# (rarely shared across domains); generic science words are excluded.
DOMAIN_VOCAB: dict[str, list[str]] = {
    "medical": [
        "csf", "cerebrospinal", "shunt", "hydrocephalus", "catheter",
        "biocompatibility", "sterilization", "sterilisation", "fda",
        "gmlp", "clinical endpoint", "patient", "implant", "lumen",
        "surgical", "neuroradiology", "neurosurgery", "in vivo", "in vitro",
        "iso 10993", "pyrogen", "endotoxin", "sterile", "implantable",
        "ventriculoperitoneal", "ventricular", "cannula", "infusion",
    ],
    "vehicle": [
        "vehicle", "drivetrain", "powertrain", "aerodynamic drag",
        "chassis", "wheelbase", "curb weight", "highway speed",
        "passenger vehicle", "fuel economy", "l/100km", "mpg",
        "cabin", "wheel", "axle", "suspension", "steering",
    ],
    "software_ml": [
        "decision-support", "machine learning", "neural network",
        "classifier", "inference latency", "dataset", "software architecture",
        "api", "microservice", "training data", "model serving",
        "software system", "latency budget", "throughput",
    ],
    "mechanical": [
        "spindle", "bearing", "rotor", "runout", "tolerance band",
        "machining", "mill", "lathe", "tolerance stack", "gearbox",
        "shaft", "keyway",
    ],
    "electronics": [
        "pcb", "emi shielding", "enclosure", "thermal pad",
        "printed circuit", "solder", "conformal coating", "ip67",
    ],
    "energy": [
        "photovoltaic", "solar panel", "battery pack", "grid", "inverter",
        "kwh", "electrolyte", "anode", "cathode",
    ],
}


def domain_term_hits(text: str, domain: str) -> dict[str, int]:
    """Count occurrences of the given domain's distinctive terms in text."""
    low = " " + text.lower().replace("\n", " ") + " "
    hits: dict[str, int] = {}
    for term in DOMAIN_VOCAB.get(domain, []):
        n = low.count(" " + term + " ") or low.count(term)
        if n:
            hits[term] = n
    return hits


def _best_domain(text: str) -> Optional[str]:
    """Best-scoring domain by distinct-term hits, ties broken by count."""
    best, best_n, best_total = None, 0, 0
    for dom in DOMAIN_VOCAB:
        hits = domain_term_hits(text, dom)
        n, total = len(hits), sum(hits.values())
        if (n, total) > (best_n, best_total):
            best, best_n, best_total = dom, n, total
    return best


def distinctive_tokens(text: str, limit: int = 60) -> list[str]:
    """Tokens not in the weak/generic list — used for Gate E linkage test."""
    toks = re.findall(r"[A-Za-z][A-Za-z\-]{5,}", text.lower())
    seen: list[str] = []
    for t in toks:
        if t not in WEAK_TOKENS and t not in seen:
            seen.append(t)
        if len(seen) >= limit:
            break
    return seen


def json_dump_safe(obj) -> str:
    import json
    try:
        return json.dumps(obj, default=str)
    except Exception:
        return str(obj)
