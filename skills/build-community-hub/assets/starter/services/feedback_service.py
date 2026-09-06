# -*- coding: utf-8 -*-
"""Feedback service - likes & comments on guides and articles."""

from typing import List

from config.schema import Comment, Feedback
from config.settings import Settings
from services.store import JsonStore, new_id, now_iso


class FeedbackService:
    def __init__(self, settings: Settings):
        self.store = JsonStore(settings.db_dir, "feedback", Feedback, key=lambda f: f.target)

    def _get_or_create(self, target: str) -> Feedback:
        fb = self.store.get(target)
        if not fb:
            fb = Feedback(target=target)
        return fb

    def toggle_like(self, target: str, user_id: str) -> int:
        """Like/unlike; returns new like count."""
        fb = self._get_or_create(target)
        if user_id in fb.likes:
            fb.likes.remove(user_id)
        else:
            fb.likes.append(user_id)
        self.store.put(fb)
        return len(fb.likes)

    def comment(self, target: str, author: str, body: str) -> Comment:
        body = body.strip()
        if not body:
            raise ValueError("留言不能为空")
        fb = self._get_or_create(target)
        c = Comment(id=new_id(), author=author,
                    body=body, created_at=now_iso())
        fb.comments.append(c)
        self.store.put(fb)
        return c

    def get(self, target: str) -> Feedback:
        return self._get_or_create(target)

    def recent_comments(self, limit: int = 50) -> List[dict]:
        """All comments across targets, newest first (for product reflection)."""
        out = []
        for fb in self.store.all():
            for c in fb.comments:
                out.append({"target": fb.target, **c.model_dump()})
        out.sort(key=lambda x: x["created_at"], reverse=True)
        return out[:limit]
