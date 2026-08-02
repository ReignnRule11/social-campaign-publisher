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
    re.compile(r"https?://hooks\.slack\.com/services/[0-9A-Za-z/_-]+", re.IGNORECASE),
    re.compile(r"https?://(?:canary\.)?discord(?:app)?\.com/api/webhooks/[0-9A-Za-z/_-]+", re.IGNORECASE),
    re.compile(r"https?://api\.telegram\.org/bot[0-9A-Za-z:_-]+", re.IGNORECASE),
]

EXCLUDE_DIRS = {'.git', 'node_modules', '.venv', 'venv'}


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
        for regex in PATTERNS:
            m = regex.search(txt)
            if m:
                # capture a short snippet
                snippet = m.group(0)
                violations.append((str(p), snippet))
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
