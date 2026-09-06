# -*- coding: utf-8 -*-
"""Pure helpers that turn approved submissions into stable guide source cards."""

import hashlib
from pathlib import Path
from typing import Callable, Iterable, List

from config.schema import Article, Contribution


def build_source_catalog(contributions: Iterable[Contribution], articles: Iterable[Article],
                         display_name: Callable[[str], str]) -> List[dict]:
    """Keep one resource card per file while retaining every contributor credit."""
    cards = []
    by_storage_key = {}
    for contribution in contributions:
        contributor = display_name(contribution.contributor) or "匿名"
        for index, attachment in enumerate(contribution.attachments):
            source_id = attachment.id or f"attachment:{contribution.id}:{index}"
            storage_key = attachment.oss_key or attachment.url or source_id
            if storage_key in by_storage_key:
                by_storage_key[storage_key]["contributors"].append(contributor)
                continue
            title = contribution.text.splitlines()[0].strip().strip("*") if contribution.text else ""
            card = {
                "id": source_id, "kind": "attachment", "storage_key": storage_key,
                "contribution_id": contribution.id,
                "title": title or attachment.filename, "filename": attachment.filename,
                "file_type": Path(attachment.filename).suffix.lstrip(".").upper(),
                "url": attachment.url, "material_type": attachment.material_type,
                "contributors": [contributor], "created_at": contribution.created_at,
                "summary_ready": bool(attachment.summary_oss_key),
                "summary_oss_key": attachment.summary_oss_key,
                "content_sha256": attachment.content_sha256,
                "reason": contribution.text,
            }
            cards.append(card)
            by_storage_key[storage_key] = card
        if not contribution.attachments and contribution.text:
            cards.append({
                "id": f"note:{contribution.id}", "kind": "note", "storage_key": contribution.id,
                "contribution_id": contribution.id,
                "title": "同学经验", "filename": "", "url": "", "material_type": "心得",
                "file_type": "",
                "contributors": [contributor], "created_at": contribution.created_at,
                "summary_ready": True, "summary_oss_key": "", "reason": contribution.text,
            })
    for article in articles:
        cards.append({
            "id": f"article:{article.id}", "kind": "article", "storage_key": article.id,
            "contribution_id": "",
            "title": article.title, "filename": "", "url": f"/articles/{article.id}",
            "file_type": "", "material_type": "相关文章",
            "contributors": [display_name(article.author) or "匿名"],
            "created_at": article.published_at or article.created_at, "summary_ready": True,
            "summary_oss_key": "", "reason": article.summary or article.body[:500],
        })
    return cards


def source_fingerprint(cards: List[dict]) -> str:
    """Fingerprint all visible evidence, not only its filename or storage location."""
    parts = [
        "|".join((card["id"], card["storage_key"], card.get("content_sha256", ""),
                  card.get("summary_oss_key", ""), card.get("reason", "")))
        for card in cards
    ]
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()
