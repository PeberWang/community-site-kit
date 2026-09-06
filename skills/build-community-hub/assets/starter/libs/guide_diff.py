# -*- coding: utf-8 -*-
"""Small, mobile-friendly unified diff representation for guide review."""

from difflib import unified_diff
from typing import List


def build_unified_diff(before: str, after: str, context: int = 2) -> List[dict]:
    rows = []
    for line in unified_diff(before.splitlines(), after.splitlines(), n=context, lineterm=""):
        if line.startswith(("---", "+++", "@@")):
            continue
        kind = "same"
        text = line
        if line.startswith("+"):
            kind, text = "added", line[1:]
        elif line.startswith("-"):
            kind, text = "removed", line[1:]
        elif line.startswith(" "):
            text = line[1:]
        rows.append({"kind": kind, "text": text})
    return rows
