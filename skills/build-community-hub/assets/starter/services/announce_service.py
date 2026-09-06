# -*- coding: utf-8 -*-
"""Announcement service - admin-published site notices pinned on home.

Unlike the 48h feed, announcements stay on home until an admin takes
them down (soft delete, same convention as plaza threads).
"""

from typing import List

from config.schema import Announcement
from config.settings import Settings
from services.store import JsonStore, new_id, now_iso


class AnnounceService:
    def __init__(self, settings: Settings):
        self.store = JsonStore(settings.db_dir, "announcements", Announcement,
                               key=lambda a: a.id)

    def publish(self, title: str, body: str, created_by: str) -> Announcement:
        title = title.strip()
        body = body.strip()
        if not title:
            raise ValueError("公告标题不能为空")
        if not body:
            raise ValueError("公告内容不能为空")
        a = Announcement(id=new_id(), title=title, body=body,
                         created_by=created_by, created_at=now_iso())
        self.store.put(a)
        return a

    def list_active(self, limit: int = 20) -> List[Announcement]:
        """Visible announcements, newest first."""
        actives = [a for a in self.store.all() if not a.deleted]
        return sorted(actives, key=lambda a: a.created_at, reverse=True)[:limit]

    def managed(self) -> List[Announcement]:
        """All announcements, including soft-deleted records, for admins."""
        return sorted(self.store.all(), key=lambda a: a.created_at, reverse=True)

    def search_managed(self, query: str = "") -> List[Announcement]:
        """Admin records filtered by title, newest first."""
        query = query.strip().casefold()
        records = self.managed()
        return [item for item in records if query in item.title.casefold()]

    def take_down(self, aid: str) -> bool:
        return self.withdraw(aid, "")

    def withdraw(self, aid: str, actor: str) -> bool:
        a = self.store.get(aid)
        if not a or a.deleted:
            return False
        a.deleted = True
        a.deleted_at, a.deleted_by = now_iso(), actor
        self.store.put(a)
        return True

    def update(self, aid: str, title: str, body: str, editor: str) -> Announcement:
        a = self.store.get(aid)
        if not a or a.deleted:
            raise ValueError("公告不存在或已下线")
        title, body = title.strip(), body.strip()
        if not title or not body:
            raise ValueError("公告标题和内容不能为空")
        a.title, a.body = title, body
        a.updated_at, a.updated_by = now_iso(), editor
        self.store.put(a)
        return a

    def restore(self, aid: str, actor: str) -> bool:
        a = self.store.get(aid)
        if not a:
            return False
        a.deleted, a.deleted_at, a.deleted_by = False, "", ""
        a.updated_at, a.updated_by = now_iso(), actor
        self.store.put(a)
        return True
