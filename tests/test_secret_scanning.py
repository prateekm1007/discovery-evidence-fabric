#!/usr/bin/env python3
"""
Secret scanning regression test.

Fails if known key prefixes or credential literals occur in source code.
This test was added after V1 had hard-coded Mistral and NVIDIA API keys.
"""
import os, re, pytest
from pathlib import Path

REPO = Path(__file__).parent.parent

# Known key prefixes that must NEVER appear in source code
SECRET_PATTERNS = [
    (r'nvapi-[A-Za-z0-9_-]{20,}', 'NVIDIA API key'),
    (r'UsFQXJwSnuO9jaWJLw9eNKyStuwZ0BDs', 'Mistral API key (literal)'),
    (r'ghp_[A-Za-z0-9]{30,}', 'GitHub PAT'),
    (r'sk-or-v1-[A-Za-z0-9]{30,}', 'OpenRouter API key'),
    (r'sk-[A-Za-z0-9]{40,}', 'OpenAI-style API key'),
    (r'csk-[A-Za-z0-9]{30,}', 'Cerebras API key'),
    (r'AKIA[0-9A-Z]{16}', 'AWS access key'),
]

# File extensions to scan
SCAN_EXTENSIONS = {'.py', '.js', '.ts', '.json', '.md', '.yaml', '.yml', '.sh', '.env'}

# Directories to skip (dependencies, git, etc.)
SKIP_DIRS = {'.git', 'node_modules', '__pycache__', '.pytest_cache', 'venv', 'audit'}

# Files that are allowed to contain key references (test files, docs about secrets)
ALLOWED_FILES = {'tests/test_secret_scanning.py'}


def scan_file(path: Path) -> list:
    """Scan a single file for secrets. Returns list of findings."""
    findings = []
    try:
        content = path.read_text(errors='ignore')
    except Exception:
        return findings

    for pattern, description in SECRET_PATTERNS:
        matches = re.findall(pattern, content)
        if matches:
            # Check if this file is allowed
            rel_path = str(path.relative_to(REPO))
            if rel_path in ALLOWED_FILES:
                continue
            for match in matches:
                findings.append({
                    "file": rel_path,
                    "pattern": description,
                    "match": match[:20] + "..." if len(match) > 20 else match,
                })
    return findings


class TestSecretScanning:
    """Ensure no hard-coded secrets exist in source code."""

    def test_no_hardcoded_secrets(self):
        """Scan all source files for known secret patterns."""
        all_findings = []
        for root, dirs, files in os.walk(REPO):
            # Skip directories
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for fname in files:
                ext = Path(fname).suffix
                if ext not in SCAN_EXTENSIONS:
                    continue
                fpath = Path(root) / fname
                findings = scan_file(fpath)
                all_findings.extend(findings)

        if all_findings:
            error_msg = "HARD-CODED SECRETS FOUND:\n"
            for f in all_findings:
                error_msg += f"  {f['file']}: {f['pattern']} ({f['match']})\n"
            pytest.fail(error_msg)

    def test_engine_v2_no_secrets(self):
        """Specifically check engine/invention_synthesis_v2.py for secrets."""
        v2_path = REPO / "engine" / "invention_synthesis_v2.py"
        if not v2_path.exists():
            pytest.skip("V2 engine not found")
        findings = scan_file(v2_path)
        assert findings == [], f"Secrets found in V2 engine: {findings}"

    def test_engine_v1_secrets_removed(self):
        """Check that V1 engine has secrets removed (or is deleted)."""
        v1_path = REPO / "engine" / "invention_synthesis.py"
        if not v1_path.exists():
            pytest.skip("V1 engine not found (may have been removed)")
        findings = scan_file(v1_path)
        # V1 should have secrets removed too
        assert findings == [], f"Secrets still in V1 engine: {findings}"

    def test_env_keys_not_in_source(self):
        """Ensure environment variable names are used, not literal keys."""
        for py_file in (REPO / "engine").glob("*.py"):
            content = py_file.read_text()
            # Should use os.environ.get, not literal keys as defaults
            assert 'os.environ.get(' in content or 'os.environ[' in content, \
                f"{py_file.name}: should read keys from environment"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
