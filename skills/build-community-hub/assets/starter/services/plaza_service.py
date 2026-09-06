# -*- coding: utf-8 -*-
"""Plaza service - 广场: free posting (no pre-review), post-hoc moderation by admins."""

from typing import List, Optional

from config.schema import Reply, Thread
from config.settings import Settings
from services.store import JsonStore, new_id, now_iso


class PlazaService:
    def __init__(self, settings: Settings):
        self.store = JsonStore(settings.db_dir, "plaza", Thread, key=lambda t: t.id)

    def post(self, author: str, title: str, body: str) -> Thread:
        title, body = title.strip(), body.strip()
        if not title or not body:
            raise ValueError("标题与内容不能为空")
        t = Thread(id=new_id(), author=author,
                   title=title, body=body, created_at=now_iso())
        self.store.put(t)
        return t

    def reply(self, tid: str, author: str, body: str) -> Reply:
        t = self.store.get(tid)
        if not t or t.deleted:
            raise ValueError("帖子不存在")
        body = body.strip()
        if not body:
            raise ValueError("回复不能为空")
        r = Reply(id=new_id(), author=author,
                  body=body, created_at=now_iso())
        t.replies.append(r)
        self.store.put(t)
        return r

    def get(self, tid: str) -> Optional[Thread]:
        return self.store.get(tid)

    def list_threads(self, include_deleted: bool = False) -> List[Thread]:
        threads = [t for t in self.store.all() if include_deleted or not t.deleted]
        return sorted(threads, key=lambda t: t.created_at, reverse=True)

    # ---- moderation (admin) ----

    def edit_thread(self, tid: str, title: str, body: str) -> None:
        t = self.store.get(tid)
        if t:
            t.title, t.body = title.strip(), body.strip()
            self.store.put(t)

    def delete_thread(self, tid: str) -> None:
        t = self.store.get(tid)
        if t:
            t.deleted = True
            self.store.put(t)

    def delete_reply(self, tid: str, rid: str) -> None:
        t = self.store.get(tid)
        if t:
            for r in t.replies:
                if r.id == rid:
                    r.deleted = True
            self.store.put(t)

    def delete_own_thread(self, tid: str, user_id: str) -> bool:
        t = self.store.get(tid)
        if t and t.author == user_id:
            t.deleted = True
            self.store.put(t)
            return True
        return False
