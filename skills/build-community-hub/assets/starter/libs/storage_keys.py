# -*- coding: utf-8 -*-
"""OSS key naming conventions - pure functions.

Layout on OSS:
  raw/<tag>/<filename>        attachment originals
  articles/<slug>.md          article bodies
  ocr/<name>_ocr.md           OCR fulltext
  summary/<name>.md           LLM summaries
"""

import re

_SAFE_RE = re.compile(r"[^\w\u4e00-\u9fff.\-]+")


def _safe(name: str) -> str:
    return _SAFE_RE.sub("_", (name or "").strip())[:80] or "untitled"


def raw_key(tag: str, filename: str, attachment_id: str = "", content_sha256: str = "") -> str:
    """Return a collision-resistant attachment key while retaining a readable filename."""
    if not attachment_id:
        return f"raw/{_safe(tag)}/{_safe(filename)}"  # legacy import compatibility
    digest = _safe(content_sha256)[:12] or "unknown"
    return f"raw/{_safe(tag)}/{_safe(attachment_id)}_{digest}_{_safe(filename)}"


def article_key(slug: str) -> str:
    return f"articles/{_safe(slug)}.md"


def ocr_key(source_id: str) -> str:
    return f"ocr/{_safe(source_id)}.md"


def summary_key(source_id: str) -> str:
    return f"summary/{_safe(source_id)}.md"
