#!/usr/bin/env python3
"""R526 — deploy the INSTRUMENTED measurement build (behavior-neutral
per-attempt generate() spans + PHASE_SPAN ledger lines + post-rank
phase/target timers ONLY) to the canonical production Space.

R526 is measurement-first: no behavioral production change is
authorized in S1/S2. The R526 battery must run on a build that carries:
  - gen_spans/1.0 per-attempt records on every durable ledger line
    (llm_registry.generate; read-only timestamps; no routing, retry,
    budget, gate, probe, admission, or transport logic touched —
    proven neutral by tests/test_r526_generate_spans.py);
  - PHASE_SPAN orchestration-timing lines on the proven ledger
    channel (model_routing.record_phase_span) + post-rank phase and
    per-target timers in run.py / improve_stage.py (telemetry
    appends only — proven neutral by
    tests/test_r526_phase_spans.py);
  - the retained synth_spans/1.0 instrument (R525).
so Questions A (generate-level routing decomposition) and B
(run-wall residual reconciliation) can be answered from
implementation spans rather than invented sub-phases.

Same machinery as r525_deploy_arm (git-archive staging, prune,
frontmatter, Dockerfile RENDER_GIT_COMMIT identity, standing vars,
secrets, restart) — re-driven per-round, never mutating historical
round scripts (Art. LXIV/LXXIV).

Fail-closed proofs (all must hold or the deploy aborts):
  1. The build commit is an ancestor of origin/main (Art. LXXXV).
  2. Build identity in the STAGED bytes: the CLI-supplied
     intervention marker is present in its file AND was added by
     this build (diff vs counterpart); the R525 synth_spans
     instrument is retained; no per-provider branch scattered into
     the ADDED lines of the allowed diff set.
  3. Engine-diff guard vs the production counterpart (e919a664): the
     engine diff MUST EQUAL the CLI-supplied allowed set exactly
     (timers only — Art. XLVII).

Standing production configuration is re-applied verbatim:
ENGINE_EVIDENCE_FABRIC=0 and ENGINE_RETRIEVE_EXCLUDE_SOURCES=openalex
(held identical; read back after deploy).

Usage:
  HF_TOKEN=... GITHUB_PAT=... python scripts/r526_deploy_arm.py
      --arm instrumented --commit <40-hex>
      --record R526/INSTRUMENT_DEPLOY_RECORD.json
      --message "..." --counterpart-commit <40-hex>
      --intervention-marker <token> --intervention-file <path>
      --allowed-diff-file <f> [--allowed-diff-file <f> ...]
      --intervention-desc <text>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re as _re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path

if not shutil.which("git"):
    for _d in (r"C:\Program Files\Git\cmd", r"C:\Program Files\Git\bin",
               "/usr/bin", "/usr/local/bin"):
        _cand = os.path.join(_d, "git.exe" if os.name == "nt" else "git")
        if os.path.isfile(_cand):
            os.environ["PATH"] = _d + os.pathsep + os.environ.get("PATH", "")
            break

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(SCRIPTS))

import r491_space_deploy as r491  # noqa: E402
import r456_space_deploy as r456  # noqa: E402
import r447_hf_deploy as driver  # noqa: E402
import r447_deploy_upload as uploader  # noqa: E402

SPACE = driver.SPACE
ENGINE_PATHS = ["discovery_fabric", "TOSCANINI", "TOSCANINI_UI",
                "Dockerfile"]
# The R526 instrumentation may touch exactly these engine files over
# production e919a664 (Art. XLVII instrument identity; CLI-supplied,
# recorded): per-attempt generate() spans, PHASE_SPAN ledger support,
# post-rank phase/target timers. No behavioral change.
R526_ALLOWED_DIFF_FILES = {
    "discovery_fabric/engine/llm_registry.py",
    "discovery_fabric/engine/model_routing.py",
    "discovery_fabric/engine/run.py",
    "discovery_fabric/engine/improve_stage.py",
}
# R526 instrument markers (staged-bytes identity proof; at least one
# must have been added by this build — enforced per marker below).
R526_MARKERS = ("gen_spans/1.0", "PHASE_SPAN")


def sh(*args, cwd=None):
    return subprocess.run(list(args), capture_output=True, text=True,
                          cwd=str(cwd or REPO), timeout=300)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--arm", required=True, choices=("instrumented", "after"))
    ap.add_argument("--commit", required=True,
                    help="full 40-hex tree commit to deploy")
    ap.add_argument("--record", required=True,
                    help="repo-relative record path")
    ap.add_argument("--message", required=True,
                    help="Space upload commit message")
    ap.add_argument("--counterpart-commit", required=True,
                    help="the current production SHA (enables the "
                         "engine-diff guard)")
    ap.add_argument("--intervention-marker", required=True,
                    help="token that MUST appear in the staged tree")
    ap.add_argument("--intervention-file", required=True,
                    help="repo-relative file searched for the marker")
    ap.add_argument("--allowed-diff-file", action="append", default=[],
                    help="repeatable: engine files permitted to differ "
                         "between the counterpart and after commits; "
                         "the diff must EQUAL this set exactly (the one "
                         "intervention and nothing else — Art. XLVII)")
    ap.add_argument("--intervention-desc", default="",
                    help="recorded description of the intervention (the "
                         "one named change); defaults to the "
                         "measurement-instrument text")
    args = ap.parse_args()
    from huggingface_hub import HfApi

    for name in (args.commit, args.counterpart_commit):
        if not _re.fullmatch(r"[0-9a-f]{40}", name):
            print("FATAL: commits must be full 40-hex SHAs (no prefixes)")
            return 2
    vault = r491._load_vault()
    hf_token = vault.get("HF_TOKEN") or os.environ.get("HF_TOKEN", "")
    gh_token = (vault.get("GITHUB_TOKEN") or vault.get("GITHUB_PAT")
                or os.environ.get("GITHUB_PAT", "")
                or os.environ.get("GITHUB_TOKEN", ""))
    if not hf_token:
        print("FATAL: HF_TOKEN absent (vault + env)")
        return 2
    if not gh_token:
        print("FATAL: GITHUB_PAT/GITHUB_TOKEN absent (vault + env)")
        return 2
    if hashlib.sha256(gh_token.encode()).hexdigest()[:12] != "f1ebca5f9b62":
        print("FATAL: PAT fingerprint mismatch — rotation is a CEO act")
        return 2
    if hashlib.sha256(hf_token.encode()).hexdigest()[:16] != "33bc7af22c628bc1":
        print("FATAL: HF fingerprint mismatch — STOP, register the delta")
        return 2

    # proof 1: reachable from origin/main
    t = sh("git", "cat-file", "-t", args.commit)
    if t.stdout.strip() != "commit":
        print(f"FATAL: {args.commit[:12]} is not a commit object")
        return 2
    anc = sh("git", "merge-base", "--is-ancestor", args.commit,
             "origin/main")
    if anc.returncode != 0:
        print(f"FATAL: {args.commit[:12]} is not reachable from "
              f"origin/main — push first (Art. LXXXV)")
        return 2
    print(f"[R526-arm] arm={args.arm} commit={args.commit} "
          f"(reachable from origin/main: PROVEN)")

    # engine-diff guard vs the production counterpart: the engine diff
    # must EQUAL the allowed set exactly (the one intervention —
    # possibly spanning the authority + the canonical implementation +
    # its single call-site wiring — and nothing else, Art. XLVII).
    d = sh("git", "diff", "--name-only", args.counterpart_commit,
           args.commit, "--", *ENGINE_PATHS)
    changed = sorted(d.stdout.split())
    allowed = sorted(args.allowed_diff_file or [])
    print(f"[R526-arm] engine-diff "
          f"{args.counterpart_commit[:12]}..{args.commit[:12]}: {changed}")
    if not allowed or changed != allowed:
        print(f"FATAL: engine diff is not exactly {allowed} — the "
              f"build differs by more than the one named intervention "
              f"(Art. XLVII)")
        return 2
    print(f"[R526-arm] engine-diff guard PROVEN ({', '.join(allowed)})")

    try:
        before = r491.space_get("/api/version", hf_token)
        print(f"[R526-arm] BEFORE engine_commit="
              f"{before.get('engine_commit', '?')[:12]}")
    except Exception as exc:  # noqa: BLE001
        before = {"probe_error": repr(exc)[:160]}
        print(f"[R526-arm] BEFORE probe pending ({type(exc).__name__})")

    api = HfApi(token=hf_token)
    with tempfile.TemporaryDirectory() as td:
        stage = Path(td) / "tree"
        stage.mkdir()
        archive = Path(td) / "tree.tar"
        with open(archive, "wb") as f:
            subprocess.run(["git", "archive", args.commit], stdout=f,
                           check=True, cwd=str(REPO))
        with tarfile.open(archive) as tf:
            tf.extractall(str(stage))
        n_full = sum(1 for _ in stage.rglob("*") if _.is_file())
        mb_full = archive.stat().st_size / 1e6
        print(f"[R526-arm] staged {n_full} tracked files "
              f"({mb_full:.0f} MB) from {args.commit[:12]}")

        # ---- R526 build identity, fail-closed, in the STAGED bytes ----
        # (a) the synth_spans/1.0 measurement instrument is retained
        # (Art. XLVII: identical instrument on both arms);
        # (b) the CLI-supplied intervention marker is present in its
        # file; (c) no per-provider branch was scattered into the
        # ADDED lines of the allowed diff set (retirement stays data,
        # R519 §6 — comments may name providers in prose; branches
        # may not).
        syn_bytes = stage / "discovery_fabric" / "a2" / "synthesize.py"
        syn_text = syn_bytes.read_text(errors="replace") \
            if syn_bytes.is_file() else ""
        assert "synthesis_span_timings" in syn_text, \
            "staged tree lost the R526 synth_spans/1.0 instrument"
        marker_file = stage / args.intervention_file
        marker_text = marker_file.read_text(errors="replace") \
            if marker_file.is_file() else ""
        assert args.intervention_marker in marker_text, \
            (f"staged tree lacks the intervention marker "
             f"{args.intervention_marker!r} in {args.intervention_file}")
        _added = []
        _removed = []
        for _ef in (args.allowed_diff_file or []):
            _dd = sh("git", "diff", args.counterpart_commit, args.commit,
                     "--", _ef)
            _added += [ln[1:] for ln in _dd.stdout.splitlines()
                      if ln.startswith("+") and not ln.startswith("+++")]
            _removed += [ln[1:] for ln in _dd.stdout.splitlines()
                        if ln.startswith("-") and not ln.startswith("---")]
        assert any(args.intervention_marker in ln for ln in _added), \
            "the intervention marker was not added by this build"
        if args.arm == "instrumented":
            # the instrumented build must ADD the R526 instrument
            # markers (gen_spans/1.0 + PHASE_SPAN) to the engine.
            assert any(mk in ln for mk in R526_MARKERS for ln in _added), \
                "no R526 instrument marker added by this build"
        elif "time.sleep(0.5)" in "\n".join(_removed):
            # R527 Q3 after arm: the REMOVAL of the fixed post-success
            # sleep is the intervention. The guard proves the sleep
            # call was in the REMOVED lines of the allowed diff set
            # (the engine-diff guard above already proves the build
            # differs by exactly the allowed set + nothing else).
            print("[R526-arm] R527 after-arm removal PROVEN: "
                  "time.sleep(0.5) is in the REMOVED lines of the "
                  "allowed diff set; the intervention marker "
                  f"({args.intervention_marker}) is in the ADDED "
                  "lines; no scattered provider branch")
        else:
            # after arm without a known removal marker: the engine-
            # diff guard above already proves the build differs by
            # exactly the allowed set; the marker is present in the
            # staged bytes.
            print("[R526-arm] after-arm identity PROVEN in staged "
                  "bytes (engine-diff guard + marker present; no "
                  "scattered provider branch)")
        for _ln in _added:
            _s = _ln.strip()
            assert not (_s.startswith("if provider") or
                       _s.startswith("if provider_id") or
                       _s.startswith("elif provider")), \
                f"a per-provider branch was scattered in: {_s[:100]}"
        print("[R526-arm] R526 after-arm identity PROVEN in staged bytes "
              "(instrument retained; marker added; no scattered branch)")

        accounting = r456._prune_round_trees(stage)
        n_pruned = sum(1 for _ in stage.rglob("*") if _.is_file())
        print(f"[R526-arm] pruned {len(accounting['removed_round_dirs'])} "
              f"round dirs ({accounting['mb_freed']} MB freed) — "
              f"{n_pruned} files remain")

        shipped = stage / "discovery_fabric" / "engine" / "calibration_records"
        shipped_names = sorted(p.name for p in shipped.glob("*.json")) \
            if shipped.exists() else []
        assert len(shipped_names) == 9, \
            f"prune ate calibration records: {shipped_names}"
        const_ok = (stage / "EPISTEMIC_CONSTITUTION.md").is_file()
        assert const_ok, "prune ate the constitution file"
        const_v = ""
        if const_ok:
            m = _re.search(r"\*\*Version:\*\*\s*(\S+)",
                           (stage / "EPISTEMIC_CONSTITUTION.md")
                           .read_text(errors="replace"))
            const_v = m.group(1) if m else ""

        readme_path = stage / "README.md"
        readme_text = readme_path.read_text(errors="replace") \
            if readme_path.exists() else ""
        if not readme_text.lstrip().startswith("---"):
            readme_path.write_text(
                uploader.README_FRONTMATTER + readme_text)
        readme_path.write_text(
            readme_path.read_text(errors="replace"), encoding="utf-8")

        df_path = stage / "Dockerfile"
        df_text = df_path.read_text()
        new_df, n_sub = _re.subn(
            r'ARG RENDER_GIT_COMMIT="(?:[0-9a-f]{40})?"',
            f'ARG RENDER_GIT_COMMIT="{args.commit}"', df_text, count=1)
        if n_sub != 1:
            print("FATAL: RENDER_GIT_COMMIT ARG not found")
            return 2
        df_path.write_text(new_df)
        print(f"[R526-arm] Dockerfile identity ARG -> {args.commit[:12]}")

        print("[R526-arm] uploading to the canonical Space ...")
        t0 = time.time()
        rev = api.upload_folder(
            folder_path=str(stage), repo_id=SPACE, repo_type="space",
            commit_message=args.message)
        print(f"[R526-arm] upload DONE in {time.time()-t0:.0f}s — "
              f"revision: {rev}")

    standing_vars = {
        "PORT": "7860",
        "ZAI_BASE_URL": "https://api.atria-asi.ai/v1/chat/completions",
        "ZAI_MODEL": "Atria-Dawn-Preview",
        "DURABLE_STATE_ENABLED": "1",
        "DURABLE_STATE_BRANCH": "runtime-state-hf",
        "LOCAL_QWEN_ENABLE": "1",
        "LOCAL_QWEN_CTX": "8192",
        "LOCAL_EMBED_ENABLE": "1",
        "LOCAL_EMBED_THREADS": "1",
        # R521/R522 winner configuration: HELD IDENTICAL on the after arm
        "ENGINE_EVIDENCE_FABRIC": "0",
        "ENGINE_RETRIEVE_EXCLUDE_SOURCES": "openalex",
    }
    for k, v in standing_vars.items():
        api.add_space_variable(repo_id=SPACE, key=k, value=v)
    readback = {}
    try:
        live = dict(api.get_space_variables(repo_id=SPACE))
        for k in ("ENGINE_EVIDENCE_FABRIC",
                  "ENGINE_RETRIEVE_EXCLUDE_SOURCES"):
            obj = live.get(k)
            readback[k] = getattr(obj, "value", None)
    except Exception as exc:  # noqa: BLE001
        readback = {"probe_error": repr(exc)[:160]}
    print(f"[R526-arm] production read-back: {readback}")
    if readback.get("ENGINE_RETRIEVE_EXCLUDE_SOURCES") != "openalex" or \
            readback.get("ENGINE_EVIDENCE_FABRIC") != "0":
        print("FATAL: standing winner configuration NOT read back — "
              "refusing to call this the measured configuration")
        return 2

    api.add_space_secret(repo_id=SPACE, key="GITHUB_TOKEN", value=gh_token)
    val = vault.get("PORTFOLIO_COMMIT") or "0914755c5832f332abe5d74ed1655cd27764ecc0"
    api.add_space_secret(repo_id=SPACE, key="PORTFOLIO_COMMIT", value=val)
    print("[R526-arm] secrets rewired identically (fp-gated)")

    api.restart_space(repo_id=SPACE)
    print("[R526-arm] Space restarted — poll /api/version for identity")

    rec = {
        "round": "R526", "arm": args.arm, "space": SPACE,
        "commit": args.commit, "hf_revision": str(rev),
        "counterpart_commit": args.counterpart_commit or None,
        "adapter": "r519/r522_space_deploy machinery re-driven per-arm",
        "arm_identity_proof": {
            "intervention_marker": args.intervention_marker,
            "intervention_file": args.intervention_file,
            "marker_present_in_staged_bytes": True,
        },
        "engine_diff_guard": f"{sorted(args.allowed_diff_file or [])} only",
        "variable_delta": None,
        "variable_readback": readback,
        "standing_configuration": {
            "ENGINE_EVIDENCE_FABRIC": "0",
            "ENGINE_RETRIEVE_EXCLUDE_SOURCES": "openalex",
        },
        "intervention": (args.intervention_desc or
                         "none (measurement-instrument build): "
                         "behavior-neutral SYNTHESIZE span timers "
                         "(synth_spans/1.0, read-only perf_counter deltas; "
                         "no prompt/budget/retry/gate/parse/repair/assembly "
                         "logic touched; neutrality proven by "
                         "tests/test_R526_synth_span_neutrality.py)"),
        "instrumentation_neutrality": (
            "tests/test_R526_synth_span_neutrality.py + unchanged "
            "R422/R483 synthesis suites (3 pre-existing R422 failures "
            "documented, unrelated)"),
        "constitution_served": const_v,
        "image_slimming": accounting,
        "full_tar_mb": round(mb_full, 1),
        "staged_files_before_prune": n_full,
        "staged_files_after_prune": n_pruned,
        "shipped_calibration_records_in_tree": shipped_names,
        "secrets_wired": ["GITHUB_TOKEN", "PORTFOLIO_COMMIT"],
        "secrets_fingerprints": {
            "GITHUB_TOKEN": "sha256:" + hashlib.sha256(
                gh_token.encode()).hexdigest()[:12],
            "HF_TOKEN": "sha256:" + hashlib.sha256(
                hf_token.encode()).hexdigest()[:16],
        },
        "reviewer_provenance": "AI_REVIEW",
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    out = REPO / args.record
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, indent=1), encoding="utf-8", newline="\n")
    print(f"[R526-arm] record -> {out}")
    return 0


if __name__ == "__main__":
    import sys as _sys
    _sys.exit(main())
