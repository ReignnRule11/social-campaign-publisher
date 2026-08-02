#!/usr/bin/env python3
"""Scan repository or staged files for webhook-like URLs and fail if found.

Usage:
  python scripts/check_secrets.py [--staged]

In CI run without --staged to scan entire repo. Locally pre-commit will call with --staged.
"""
import re
import sys
import subprocess
from pathlib import Path

# Patterns to detect (common webhook URLs)
PATTERNS = [
    # common webhook URL patterns
    re.compile(r"https?://hooks\.slack\.com/services/[0-9A-Za-z/_-]+", re.IGNORECASE),
    re.compile(r"https?://(?:canary\.)?discord(?:app)?\.com/api/webhooks/[0-9A-Za-z/_-]+", re.IGNORECASE),
    re.compile(r"https?://api\.telegram\.org/bot[0-9A-Za-z:_-]+", re.IGNORECASE),
    # common API/key patterns
    re.compile(r"AKIA[0-9A-Z]{16}"),  # AWS access key id
    re.compile(r"(?i)ssh-rsa [A-Za-z0-9+/=]{100,}"),  # SSH public key blob
    re.compile(r"(?:[A-Za-z0-9-_]{20,}:){0,1}[A-Za-z0-9-_]{40,}"),  # long token-like strings
    re.compile(r"xox[baprs]-[A-Za-z0-9-]+"),  # Slack tokens
]

EXCLUDE_DIRS = {'.git', 'node_modules', '.venv', 'venv', '.github'}


def get_staged_files():
    try:
        out = subprocess.check_output(['git', 'diff', '--cached', '--name-only'], text=True)
        return [p for p in out.splitlines() if p]
    except subprocess.CalledProcessError:
        return []


def get_all_tracked_files():
    try:
        out = subprocess.check_output(['git', 'ls-files'], text=True)
        return [p for p in out.splitlines() if p]
    except subprocess.CalledProcessError:
        return []


def is_text_file(path: Path) -> bool:
    try:
        data = path.read_bytes()
        # simple heuristic: if null byte present, treat as binary
        return b"\x00" not in data
    except Exception:
        return False


def _shannon_entropy(data: str) -> float:
    # simple Shannon entropy estimation for a string
    from collections import Counter
    if not data:
        return 0.0
    counts = Counter(data)
    import math
    entropy = 0.0
    length = len(data)
    for c in counts.values():
        p = c / length
        entropy -= p * (math.log(p, 2))
    return entropy


def scan_files(files):
    violations = []
    for f in files:
        p = Path(f)
        if any(part in EXCLUDE_DIRS for part in p.parts):
            continue
        if not p.exists():
            continue
        if p.is_dir():
            continue
        if not is_text_file(p):
            continue
        try:
            txt = p.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            continue
        # regex checks
        for regex in PATTERNS:
            m = regex.search(txt)
            if m:
                snippet = m.group(0)
                violations.append((str(p), snippet))
                # continue scanning for more issues in this file
        # entropy check: look for long base64-like strings
        for token in re.findall(r"[A-Za-z0-9+/=]{40,}", txt):
            ent = _shannon_entropy(token)
            if ent > 4.5:
                violations.append((str(p), f"high-entropy-string:{token[:40]}... (entropy={ent:.2f})"))
    return violations


def main():
    staged = '--staged' in sys.argv
    files = get_staged_files() if staged else get_all_tracked_files()
    violations = scan_files(files)
    if violations:
        print('\nPotential webhook URL(s) or secret-like strings detected:')
        for path, snippet in violations:
            print(f" - {path}: {snippet}")
        print('\nRemove or replace secrets with environment variables or Docker secrets. Aborting commit/CI.')
        return 1
    print('No webhook-like URLs detected.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
