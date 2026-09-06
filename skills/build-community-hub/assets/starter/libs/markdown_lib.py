# -*- coding: utf-8 -*-
"""Markdown -> HTML rendering (markdown-it-py)."""

import re

from markdown_it import MarkdownIt

from libs.download_links import rewrite_legacy_download_urls

_md = MarkdownIt("commonmark", {"html": False, "linkify": True, "breaks": True}).enable("table")


def _is_delimiter(line: str) -> bool:
    s = line.strip()
    return "-" in s and all(c in "-|: " for c in s)


def _is_row(line: str) -> bool:
    s = line.strip()
    return s.startswith("|") and s.count("|") >= 2


def heal_tables(text: str) -> str:
    """Insert missing `| --- |` delimiter rows so LLM/human tables always render."""
    lines = text.split("\n")
    out = []
    for i, line in enumerate(lines):
        out.append(line)
        if not _is_row(line) or _is_delimiter(line):
            continue
        prev = lines[i - 1].strip() if i > 0 else ""
        nxt = lines[i + 1].strip() if i + 1 < len(lines) else ""
        header_candidate = (not _is_row(prev)) and _is_row(nxt) and not _is_delimiter(nxt)
        if header_candidate:
            cols = line.strip().strip("|").count("|") + 1
            out.append("| " + " | ".join(["---"] * cols) + " |")
    return "\n".join(out)


def render_markdown(text: str) -> str:
    return _md.render(heal_tables(text or ""))


def render_inline_markdown(text: str) -> str:
    """Render a short Markdown snippet without a paragraph wrapper."""
    return _md.renderInline(text or "")


def guide_callout(text: str) -> str:
    """Extract the first short quote for the guide page hero without trusting HTML."""
    match = re.search(r"^>\s*(?:\*\*)?(?:一句话学法|一句话行动)(?:\*\*)?\s*(.*)$", text, re.M)
    return match.group(1).strip() if match else ""


def render_guide_markdown(text: str, legacy_download_bases=()) -> str:
    """The page owns H1, so legacy Markdown cannot create a second title."""
    body = re.sub(r"^#\s+.*\n+", "", text or "", count=1)
    return render_markdown(rewrite_legacy_download_urls(body, legacy_download_bases))
