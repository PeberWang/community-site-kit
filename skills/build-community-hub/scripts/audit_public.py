#!/usr/bin/env python3
"""Conservative public-release scanner for credentials and identifying data."""

import argparse
import re
from pathlib import Path

SKIP_DIRS = {".git", ".venv", "venv", "data", "log", "skill_init", "__pycache__"}
BINARY_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".docx", ".zip", ".gz"}
PATTERNS = {
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "GitHub token": re.compile(r"\b(?:ghp|github_pat)_[A-Za-z0-9_]{20,}\b"),
    "cloud access key": re.compile(r"\b(?:AKIA|LTAI)[A-Za-z0-9]{12,}\b"),
    "API token": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "Chinese phone": re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),
    "email address": re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
    "absolute home path": re.compile(r"/(?:Users|home)/[^/\s]+/"),
    "hardcoded secret": re.compile(
        r"(?i)\b(?:session_secret|api_key|access_key_secret|app_secret|auth_token)\b"
        r"\s*=\s*['\"][^'\"]{12,}['\"]"
    ),
    "environment secret": re.compile(
        r"(?i)^(?:SESSION_SECRET|[A-Z0-9_]*API_KEY|[A-Z0-9_]*ACCESS_KEY_SECRET|"
        r"[A-Z0-9_]*TOKEN)=[^\s#]{12,}$"
    ),
}
PLACEHOLDERS = ("example", "placeholder", "xxxxxxxx", "yyyyyyyy", "change-me", "your-")


def iter_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file() or any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() in BINARY_SUFFIXES:
            continue
        yield path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".", type=Path)
    parser.add_argument("--deny-term", action="append", default=[])
    args = parser.parse_args()
    root = args.root.resolve()
    findings = []
    denied = {term.casefold() for term in args.deny_term}
    for path in iter_files(root):
        if path.resolve() == Path(__file__).resolve():
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, OSError):
            continue
        for number, line in enumerate(lines, 1):
            folded = line.casefold()
            if not any(marker in folded for marker in PLACEHOLDERS):
                for label, pattern in PATTERNS.items():
                    if pattern.search(line):
                        findings.append((path, number, label))
            for term in denied:
                if term in folded:
                    findings.append((path, number, f"source identity: {term}"))
    if findings:
        print("公开审计失败：")
        for path, number, label in findings:
            print(f"- {path.relative_to(root)}:{number} [{label}]")
        print("请人工核实并删除、替换；误报应记录人工判断。")
        return 1
    print(f"公开审计通过：{root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
