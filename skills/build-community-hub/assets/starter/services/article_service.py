# -*- coding: utf-8 -*-
"""Article service - 文章栏目: original long-form, LLM-formatted markdown, review gate."""

from typing import List, Optional

from config.schema import Article
from config.settings import Settings
from services.store import JsonStore, new_id, now_iso
from services.tag_service import slugify


class ArticleService:
    def __init__(self, settings: Settings):
        self.store = JsonStore(settings.db_dir, "articles", Article, key=lambda a: a.id)

    def submit(self, author: str, title: str, body: str,
               course_slug: str = "", topic_slug: str = "",
               body_oss_key: str = "") -> Article:
        title = (title or "").strip()
        body = (body or "").strip()
        if not title or not body:
            raise ValueError("标题与正文不能为空")
        if not (course_slug or topic_slug):
            raise ValueError("文章必须归属一门人生课或专业课")
        a = Article(id=new_id(), slug=slugify(title), title=title,
                    author=author,
                    course_slug=course_slug, topic_slug=topic_slug,
                    body=body, body_oss_key=body_oss_key, created_at=now_iso())
        self.store.put(a)
        return a

    def get(self, aid: str) -> Optional[Article]:
        return self.store.get(aid)

    def pending(self) -> List[Article]:
        return sorted(self.store.find(lambda a: a.review_status == "pending"),
                      key=lambda a: a.created_at)

    def published(self) -> List[Article]:
        return sorted(self.store.find(lambda a: a.review_status == "approved"
                                      and not a.withdrawn),
                      key=lambda a: a.published_at, reverse=True)

    def managed(self) -> List[Article]:
        """All approved records, including withdrawn items, for administrators."""
        return sorted(self.store.find(lambda a: a.review_status == "approved"),
                      key=lambda a: a.published_at, reverse=True)

    def search_managed(self, query: str = "") -> List[Article]:
        """Approved records filtered by title, newest first."""
        query = query.strip().casefold()
        return [item for item in self.managed() if query in item.title.casefold()]

    def published_for(self, course_slug: str = "", topic_slug: str = "") -> List[Article]:
        return [a for a in self.published()
                if (course_slug and a.course_slug == course_slug)
                or (topic_slug and a.topic_slug == topic_slug)]

    def by_user(self, user_id: str) -> List[Article]:
        return sorted(self.store.find(lambda a: a.author == user_id),
                      key=lambda a: a.created_at, reverse=True)

    def review(self, aid: str, approve: bool, reviewer: str) -> Article:
        a = self.store.get(aid)
        if not a:
            raise ValueError("文章不存在")
        a.review_status = "approved" if approve else "rejected"
        a.reviewed_by = reviewer
        if approve and not a.published_at:
            a.published_at = now_iso()
        self.store.put(a)
        return a

    def update_published(self, aid: str, title: str, body: str,
                         editor: str) -> Article:
        a = self.store.get(aid)
        if not a or a.review_status != "approved":
            raise ValueError("只有已发布文章可以编辑")
        title, body = title.strip(), body.strip()
        if not title or not body:
            raise ValueError("标题与正文不能为空")
        a.title, a.body = title, body
        a.updated_at, a.updated_by = now_iso(), editor
        self.store.put(a)
        return a

    def withdraw(self, aid: str, actor: str) -> Article:
        a = self.store.get(aid)
        if not a or a.review_status != "approved":
            raise ValueError("只有已发布文章可以下线")
        a.withdrawn, a.withdrawn_at, a.withdrawn_by = True, now_iso(), actor
        self.store.put(a)
        return a

    def restore(self, aid: str, actor: str) -> Article:
        a = self.store.get(aid)
        if not a or a.review_status != "approved":
            raise ValueError("文章不存在或尚未发布")
        a.withdrawn, a.withdrawn_at, a.withdrawn_by = False, "", ""
        a.updated_at, a.updated_by = now_iso(), actor
        self.store.put(a)
        return a

    def update_body(self, aid: str, body: str, body_oss_key: str = "") -> None:
        a = self.store.get(aid)
        if a:
            a.body = body
            if body_oss_key:
                a.body_oss_key = body_oss_key
            self.store.put(a)
