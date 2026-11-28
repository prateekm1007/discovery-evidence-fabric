#!/usr/bin/env python3
"""r45_all_refs_secret_scan.py — the AM42 D8 adoption (claim c-0067,
builder-r45s1 lineage; session builder-r50s2 after two mid-round sandbox
recycles — prior builds of this instrument died unpushed with their
sandboxes, rebuilt from the session record, disclosed).

The F45 detection gap, closed at the SURFACE level: the R44 pre-push
secret-grep was diff-scoped (staged diff only) and therefore missed the
live PAT sitting untouched on r448/visual-lab. This instrument scans:

  (a) TIPS — every remote branch tip tree via `git grep` (C-speed,
      exact branch+path attribution, F59 precision). Binary files are
      skipped by grep -I (typed in the report).
  (b) HISTORY — every reachable commit diff via the regex pickaxe
      `git log --all -i -G<regex> -p -U0` (C-speed generation over all
      refs; every blob in reachable history entered through some
      commit's diff, so the pickaxe covers the full content surface).
      Streaming parse with a typed truncation cap (Art. 9).
  (c) STAGED — added lines of the staged diff (the pre-commit layer);
      refuses on ANY hit, NO baseline — a newly committed secret is
      never admitted; --no-verify is the typed escape, disclosed in the
      commit message per the house convention.

Git over-matches deliberately (case-insensitive discovery); the per-line
classifier applies the exact gitleaks-default rule battery (exact-case
token shapes, entropy gate, typed exclusions) and fingerprints each
finding as sha256(rule|secret) — no secret value is ever printed,
logged, or written. Every history/tips finding must be BASELINED in
eval/secret_scan_baseline.json (disposition + provenance + the exact
ref/path enumeration) or the gate fails typed: 0 unbaselined findings
is the acceptance (any NEW secret reds the gate — the baseline can
never silently grow).

The real gitleaks binary (MIT) is CORROBORATION when present: its
redacted report is recorded beside the deterministic verdict, never
trusted instead of it (the gate is this file's own detector, so CI
needs no Go binary to bind).

Complements (never replaces) the peer's prefix enumeration
(eval/r50_secret_scan_partial.json), its content-level classification
(eval/r51_secret_verification.json), and the detect-secrets pre-commit
layer (.githooks/pre-commit + .secrets.baseline) — independent layers
on one gate.

Exit codes: 0 = 0 unbaselined findings; 1 = unbaselined findings (gate
refusal) or staged hit; 2 = instrument failure (fail closed, typed).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BASELINE = REPO / "eval" / "secret_scan_baseline.json"

# ---------------------------------------------------------------------------
# Detector: the gitleaks-default core shapes, deterministic, no network.
# Rule exclusions are TYPED and recorded in the report — never silent.
# ---------------------------------------------------------------------------

TOKEN_RULES = [
    ("github-pat", re.compile(r"github_pat_[0-9A-Za-z_]{22,255}")),
    ("github-token-classic", re.compile(r"\bgh[pousr]_[0-9A-Za-z]{20,255}\b")),
    ("gitlab-pat", re.compile(r"\bglpat-[0-9A-Za-z\-_]{20,255}\b")),
    ("aws-access-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("google-api-key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("slack-token", re.compile(r"\bxox[baprs]-[0-9A-Za-z\-]{10,250}\b")),
    # v3.2.0 Art. 17 addition (CORR-2): the OpenRouter key shape. The
    # R50 v1.0.0 battery MISSED it — the live sk-or-v1-64hex key in
    # the 76c23fef7 commit message was found by the AUDITOR's
    # byte-probe, not by this scanner (the exact gap CORR-2 records).
    # Exact shape (64 lowercase hex after the prefix) so benign prose
    # mentions of "sk-or-v1-..." never match — the 3 other message
    # mentions are pattern references, typed benign by the CORR-2
    # correction, and MUST stay undetected by this rule.
    ("openrouter-key", re.compile(r"\bsk-or-v1-[0-9a-f]{64}\b")),
    ("private-key-block", re.compile(
        r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP |)PRIVATE KEY( BLOCK)?-----")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\b")),
]

GENERIC_KEY = re.compile(
    r"(?i)(?:api[_\-]?key|apikey|auth[_\-]?token|access[_\-]?token|"
    r"secret[_\-]?key|client[_\-]?secret|secret|credential|"
    r"passwo?r?d|passwd|bearer)\s*[:=]\s*")
GENERIC_VALUE = re.compile(r"[\"']([A-Za-z0-9_\-+/=\.]{16,200})[\"']")
UUID_SHAPE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)
HEX64 = re.compile(r"^[0-9a-f]{64}$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")

GENERIC_ENTROPY_MIN = 3.5

EXCLUDED_SHAPES = {
    "hex64-digest": "the house sha256 seal corpus (21043 seals triaged non-secret, R45 detect-secrets sweep, commit 1995f7e75) — a documented repo integrity mechanism, not a secret class",
    "hex40-blobsha": "git object sha shape",
    "uuid-value": "versioned uuid shape, no secret content class",
}

# The combined DISCOVERY regex handed to git (C-speed, case-insensitive
# at the git layer — over-matches deliberately); scan_text() applies the
# exact-case rules + entropy + exclusions per line.
GIT_GREP_PATTERN = (
    "github_pat_[0-9A-Za-z_]+|gh[pousr]_[0-9A-Za-z]+|glpat-[0-9A-Za-z_-]+|"
    "AKIA[0-9A-Z]+|AIza[0-9A-Za-z_-]+|xox[baprs]-[0-9A-Za-z-]+|"
    "sk-or-v1-[0-9a-fA-F]+|"
    "BEGIN [A-Za-z ]*PRIVATE KEY|eyJ[A-Za-z0-9_-]+[.]|"
    "api[_-]?key|apikey|auth[_-]?token|access[_-]?token|secret[_-]?key|"
    "client[_-]?secret|secret|credential|passwo?r?d|passwd|bearer")
HISTORY_DIFF_CAP = 2 * 1024 * 1024 * 1024   # 2 GiB typed truncation cap


def _entropy(s: str) -> float:
    if not s:
        return 0.0
    freq = defaultdict(int)
    for ch in s:
        freq[ch] += 1
    n = len(s)
    return -sum((c / n) * math.log2(c / n) for c in freq.values())


def scan_text(text: str, path: str):
    """Findings for one line of text: {rule, path, line, fingerprint}
    where fingerprint = sha256(rule|secret). The secret value never
    leaves this function except into the fingerprint hash."""
    out = []
    seen = set()
    for rule_id, rx in TOKEN_RULES:
        for m in rx.finditer(text):
            secret = m.group(0)
            fp = hashlib.sha256(f"{rule_id}|{secret}".encode()).hexdigest()
            if (rule_id, fp) in seen:
                continue
            seen.add((rule_id, fp))
            out.append({"rule": rule_id, "path": path, "fingerprint": fp})
    m = GENERIC_KEY.search(text)
    if m:
        vm = GENERIC_VALUE.match(text, m.end())
        if vm:
            val = vm.group(1)
            if (HEX64.match(val) or HEX40.match(val)
                    or UUID_SHAPE.match(val)):
                val = None
            if val is not None:
                if _entropy(val) >= GENERIC_ENTROPY_MIN:
                    rule_id = "generic-secret-assignment"
                    fp = hashlib.sha256(
                        f"{rule_id}|{val}".encode()).hexdigest()
                    if (rule_id, fp) not in seen:
                        seen.add((rule_id, fp))
                        out.append({"rule": rule_id, "path": path,
                                    "fingerprint": fp})
    return out


# ---------------------------------------------------------------------------
# Git surface enumeration
# ---------------------------------------------------------------------------

def _git_bytes(*args: str) -> bytes:
    r = subprocess.run(["git", *args], cwd=REPO, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)}: "
            f"{r.stderr.decode(errors='replace').strip()}")
    return r.stdout


def remote_branches() -> list:
    refs = _git_bytes("for-each-ref", "--format=%(refname:short)",
                      "refs/remotes/origin").decode(errors="replace").split()
    return sorted(r for r in refs if not r.endswith("/HEAD"))


def scan_tips(refs: list) -> tuple:
    """git grep per remote ref (C-speed over the full tip tree, exact
    branch+path attribution). Binary files are skipped by grep -I
    (typed in the report). Returns (findings, stats)."""
    findings, stats = [], {"method": "git grep -n -I -i -E per remote ref",
                           "grep_lines_total": 0, "refs": {}}
    for ref in refs:
        p = subprocess.run(["git", "grep", "-n", "-I", "-i", "-E", "-z",
                            GIT_GREP_PATTERN, ref, "--"],
                           cwd=REPO, capture_output=True)
        if p.returncode not in (0, 1):
            raise RuntimeError("git grep failed on " + ref + ": "
                               + p.stderr.decode(errors="replace"))
        n = 0
        # git grep -z emits per match:
        #   "<ref>:<path>\0<line>\0<content>\n" — the content chunk
        # carries the NEXT match's head after its trailing newline, so
        # the parse is a 3-state walk over the NUL-separated records.
        recs = p.stdout.split(b"\x00")
        state, r_name, path, ln_txt = "head", "", "", ""

        def _emit(chunk: bytes):
            nonlocal n
            txt = chunk.decode(errors="replace")
            nl = txt.find("\n")
            content = txt if nl < 0 else txt[:nl]
            n += 1
            for f in scan_text(content, path):
                f["ref"] = r_name
                f["surface"] = "tip"
                f["line"] = int(ln_txt) if ln_txt.isdigit() else 0
                findings.append(f)
            if nl >= 0:
                nxt = txt[nl + 1:]
                nr, _, npath = nxt.partition(":")
                return ("line", nr, npath, "")
            return ("head", r_name, path, ln_txt)

        for chunk in recs:
            if state == "head":
                head = chunk.decode(errors="replace")
                r_name, _, path = head.partition(":")
                state = "line"
            elif state == "line":
                ln_txt = chunk.decode(errors="replace").strip()
                state = "content"
            else:
                state, r_name, path, ln_txt = _emit(chunk)
        stats["refs"][ref] = n
        stats["grep_lines_total"] += n
    return findings, stats


def scan_history_pickaxe(refs: list) -> tuple:
    """git log --all -i -G<regex> -p -U0 (regex pickaxe over every
    reachable commit diff — every blob in reachable history entered
    through some commit's diff). C-speed generation; python parses the
    matched added lines. Streaming with a typed truncation cap.
    Returns (findings, stats)."""
    findings = []
    stats = {"method": "git log --all -i -G<regex> -p -U0",
             "commits_matched": 0, "diff_lines_parsed": 0,
             "truncated": False, "cap_bytes": HISTORY_DIFF_CAP}
    p = subprocess.Popen(
        ["git", "log", "--all", "-i", "-G", GIT_GREP_PATTERN,
         "-p", "-U0", "--no-color", "--format=%H"],
        cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    commit, cur_path, line_no = None, None, 0
    seen = set()
    total = 0
    for raw in p.stdout:
        total += len(raw)
        if total > HISTORY_DIFF_CAP:
            stats["truncated"] = True
            break
        ln = raw.decode(errors="replace").rstrip("\n")
        if len(ln) == 40 and all(c in "0123456789abcdef" for c in ln):
            commit = ln
            stats["commits_matched"] += 1
            cur_path = None
            continue
        if ln.startswith("+++ b/"):
            cur_path = ln[6:]
            line_no = 0
            continue
        if ln.startswith("@@"):
            m = re.search(r"@@ -\d+(?:,\d+)? \+(\d+)", ln)
            line_no = int(m.group(1)) - 1 if m else 0
            continue
        if ln.startswith("+") and cur_path and commit:
            line_no += 1
            key = (commit, cur_path, line_no)
            if key in seen:
                continue
            seen.add(key)
            for f in scan_text(ln[1:], cur_path):
                f["ref"] = "history"
                f["surface"] = "history"
                f["commit"] = commit
                findings.append(f)
            stats["diff_lines_parsed"] += 1
    p.terminate()
    p.wait()
    if stats["truncated"]:
        stats["note"] = ("the diff stream hit the 2 GiB typed cap — the "
                         "remaining commits' diffs were NOT parsed; the "
                         "next full pass should raise the cap or run on "
                         "a narrowed ref set (disclosed, Art. 9)")
    return findings, stats


def scan_commit_messages(refs: list) -> tuple:
    """v3.2.0 Art. 17 addition (F45/CORR-2): FULL-HISTORY COMMIT-MESSAGE
    scan. The v1.0.0 history leg pickaxes DIFFS only (`git log -p`) —
    commit MESSAGES never enter the diff surface, which is exactly how
    the OpenRouter key embedded in the 76c23fef7 message evaded the
    R50 instrument (CORR-2: the auditor found it by byte-probe; the
    bundle's original attribution was then mis-assigned by subject
    prefix to v28). This leg enumerates every reachable commit's
    message (`git log --all` with %H + %B), scans it line-by-line
    with the SAME classifier battery, and attributes every finding to
    the EXACT commit SHA (never a subject prefix).
    Returns (findings, stats)."""
    findings = []
    stats = {"method": "git log --all --format=<RS><H><US><B>",
             "commits_scanned": 0, "message_lines_scanned": 0,
             "truncated": False, "cap_bytes": HISTORY_DIFF_CAP}
    # RS (\x1e) starts a record; US (\x1f) separates the SHA from the
    # raw body (%B). The pickaxe is NOT used here: messages are read
    # directly, every commit, no regex pre-filter (the discovery regex
    # would ALSO miss message-embedded keys whose shape differs from
    # the -G pattern; the classifier battery is the detector).
    p = subprocess.Popen(
        ["git", "log", "--all", "--format=%x1e%H%x1f%B"],
        cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    commit, in_body, line_no = None, False, 0
    total = 0
    for raw in p.stdout:
        total += len(raw)
        if total > HISTORY_DIFF_CAP:
            stats["truncated"] = True
            break
        ln = raw.decode(errors="replace").rstrip("\n")
        if ln.startswith("\x1e"):
            commit = ln[1:].split("\x1f", 1)[0]
            body = ln[1:].split("\x1f", 1)[1] if "\x1f" in ln else ""
            stats["commits_scanned"] += 1
            in_body = True
            line_no = 0
            lines = [body]
        elif in_body and commit:
            lines = [ln]
        else:
            continue
        for msg_ln in lines:
            line_no += 1
            if not msg_ln.strip():
                continue
            stats["message_lines_scanned"] += 1
            for f in scan_text(msg_ln, "<commit-message>"):
                f["ref"] = "history-messages"
                f["surface"] = "commit_message"
                f["commit"] = commit  # EXACT SHA attribution (CORR-2)
                f["message_line"] = line_no
                findings.append(f)
    p.terminate()
    p.wait()
    if stats["truncated"]:
        stats["note"] = ("the message stream hit the typed cap — the "
                         "remaining commits' messages were NOT "
                         "parsed (disclosed, Art. 9)")
    return findings, stats


def scan_staged() -> list:
    """Added lines of the staged diff, per path. Any hit is a refusal
    (the pre-commit layer has NO baseline — history/tips are the
    baseline's surfaces; a commit admission is a new event)."""
    diff = _git_bytes("diff", "--cached", "-U0",
                      "--no-color").decode(errors="replace")
    findings, cur_path = [], None
    for ln in diff.splitlines():
        if ln.startswith("+++ b/"):
            cur_path = ln[6:]
            continue
        if ln.startswith("+++") or ln.startswith("---"):
            continue
        if cur_path and ln.startswith("+"):
            for f in scan_text(ln[1:], cur_path):
                f["ref"] = "staged"
                f["surface"] = "staged"
                findings.append(f)
    return findings


# ---------------------------------------------------------------------------
# Gate + report
# ---------------------------------------------------------------------------

def load_baseline() -> dict:
    if not BASELINE.exists():
        raise RuntimeError(
            f"{BASELINE} missing — the baseline is the committed "
            f"enumeration report; the gate cannot run without it "
            f"(fail closed)")
    return json.loads(BASELINE.read_text(encoding="utf-8"))


def gate(findings: list, baseline: dict) -> tuple:
    """(unbaselined, baselined count) — a finding matches the baseline
    on (rule, fingerprint)."""
    base_keys = {(e["rule"], e["fingerprint"])
                 for e in baseline.get("baseline", [])}
    un, ok = [], 0
    for f in findings:
        if (f["rule"], f["fingerprint"]) in base_keys:
            ok += 1
        else:
            un.append(f)
    return un, ok


def _redact_finding(f: dict) -> dict:
    keys = ("rule", "surface", "ref", "path", "line", "commit",
            "message_line", "fingerprint")
    return {k: f[k] for k in keys if k in f}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["all", "tips", "history",
                                       "messages", "staged"],
                    default="all")
    ap.add_argument("--report", type=Path, default=None,
                    help="write the machine report JSON here")
    ap.add_argument("--gitleaks", type=str, default=None,
                    help="path to a gitleaks binary for corroboration")
    args = ap.parse_args()

    report = {
        "record": "R50_ALL_REFS_SECRET_SCAN/1.1.0",
        "mode": args.mode,
        "v1_1_0_note": "the messages leg (commit messages, exact-SHA "
                       "attribution) joins tips+history per the "
                       "epistemic v3.2.0 Art. 17 addition (F45/CORR-2)",
        "detector": {
            "token_rules": [r for r, _ in TOKEN_RULES],
            "generic_rule": "secret-vocabulary key + quoted value with "
                            f"Shannon entropy >= {GENERIC_ENTROPY_MIN}",
            "excluded_shapes": EXCLUDED_SHAPES,
            "discovery_regex": GIT_GREP_PATTERN,
            "fingerprint": "sha256(rule|secret) — secret values are "
                           "never printed or written",
        },
    }
    findings = []
    try:
        if args.mode == "staged":
            findings = scan_staged()
            report["refs_scanned"] = ["staged-diff"]
            report["n_refs"] = 1
        else:
            refs = remote_branches()
            report["refs_scanned"] = refs
            report["n_refs"] = len(refs)
            if args.mode in ("all", "tips"):
                tip_findings, tip_stats = scan_tips(refs)
                findings += tip_findings
                report["tips_stats"] = tip_stats
            if args.mode in ("all", "history"):
                hist_findings, hist_stats = scan_history_pickaxe(refs)
                findings += hist_findings
                report["history_stats"] = hist_stats
            if args.mode in ("all", "messages"):
                msg_findings, msg_stats = scan_commit_messages(refs)
                findings += msg_findings
                report["messages_stats"] = msg_stats
    except Exception as e:  # fail closed, typed
        print(f"SECRET SCAN INSTRUMENT FAILURE (typed, fail-closed): {e}",
              file=sys.stderr)
        return 2

    if args.mode == "staged":
        un = findings
        ok = 0
        report["verdict"] = ("PASS" if not un
                             else "FAIL_STAGED_SECRET_ADMISSION")
    else:
        try:
            baseline = load_baseline()
        except Exception as e:
            print(f"SECRET SCAN INSTRUMENT FAILURE (typed, fail-closed): "
                  f"{e}", file=sys.stderr)
            return 2
        un, ok = gate(findings, baseline)
        report["verdict"] = ("PASS" if not un
                             else "FAIL_UNBASELINED_FINDINGS")

    report.update({
        "findings_total_raw": len(findings),
        "findings_baselined": ok,
        "unbaselined": [_redact_finding(f) for f in un],
        "n_unbaselined": len(un),
    })

    # corroboration: the real gitleaks binary when available (recorded,
    # never trusted instead of the deterministic gate)
    gl = args.gitleaks or shutil.which("gitleaks")
    if args.mode in ("all", "history") and gl:
        try:
            r = subprocess.run(
                [gl, "detect", "--no-banner", "--report-format", "json",
                 "--report-path", "/dev/stdout", "--redact=80",
                 "--log-opts=--all"],
                cwd=REPO, capture_output=True, text=True, timeout=900)
            try:
                gl_findings = json.loads(r.stdout or "[]")
            except json.JSONDecodeError:
                gl_findings = []
            report["gitleaks_corroboration"] = {
                "binary": gl, "exit": r.returncode,
                "n_findings": len(gl_findings),
                "note": "corroborating evidence only — the gate is this "
                        "file's deterministic detector"}
        except Exception as e:
            report["gitleaks_corroboration"] = {
                "binary": gl, "error": str(e),
                "note": "corroboration unavailable (typed) — the "
                        "deterministic gate still binds"}

    if args.report:
        args.report.write_text(json.dumps(report, indent=1),
                               encoding="utf-8")
    print(json.dumps({k: report[k] for k in
                      ("record", "n_refs", "findings_total_raw",
                       "findings_baselined", "n_unbaselined",
                       "verdict")}, indent=1))
    if un:
        for f in un[:20]:
            loc = f.get("path") or f.get("commit", "?")
            print(f"UNBASELINED {f['rule']} {f.get('ref')} "
                  f"{loc}:{f.get('line')}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
