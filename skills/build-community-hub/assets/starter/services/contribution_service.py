# -*- coding: utf-8 -*-
"""Contribution service - 贡献 (tag + 心得/理由 + 附件), review gate.

Rules (product decisions):
  - tag required (course or topic; may propose a new tag, admin confirms)
  - text and attachments must not both be empty
  - admin review = approve / reject / fix tag; no routing judgement
"""

from typing import List, Optional

from config.schema import Attachment, Contribution
from config.settings import Settings
from services.store import JsonStore, new_id, now_iso


class ContributionService:
    def __init__(self, settings: Settings):
        self.store = JsonStore(settings.db_dir, "contributions",
                               Contribution, key=lambda c: c.id)

    def submit(self, contributor: str,
               course_slug: str = "", topic_slug: str = "",
               new_tag_name: str = "", text: str = "",
               attachments: Optional[List[Attachment]] = None) -> Contribution:
        text = (text or "").strip()
        attachments = attachments or []
        if not text and not attachments:
            raise ValueError("心得/理由与附件不能全空")
        if not (course_slug or topic_slug or new_tag_name.strip()):
            raise ValueError("必须选择或创建一个归属 tag")
        c = Contribution(id=new_id(), contributor=contributor,
                         course_slug=course_slug, topic_slug=topic_slug,
                         new_tag_name=new_tag_name.strip(), text=text,
                         attachments=attachments, created_at=now_iso())
        self.store.put(c)
        return c

    def get(self, cid: str) -> Optional[Contribution]:
        return self.store.get(cid)

    def pending(self) -> List[Contribution]:
        return sorted(self.store.find(lambda c: c.review_status == "pending"),
                      key=lambda c: c.created_at)

    def approved_for(self, course_slug: str = "", topic_slug: str = "") -> List[Contribution]:
        return sorted(
            self.store.find(lambda c: c.review_status == "approved"
                            and ((course_slug and c.course_slug == course_slug)
                                 or (topic_slug and c.topic_slug == topic_slug))),
            key=lambda c: c.created_at)

    def by_user(self, user_id: str) -> List[Contribution]:
        return sorted(self.store.find(lambda c: c.contributor == user_id),
                      key=lambda c: c.created_at, reverse=True)

    def approved_attachment_key(self, oss_key: str) -> str:
        """Return a registered, approved storage key or an empty string."""
        for contribution in self.store.all():
            if contribution.review_status != "approved":
                continue
            if any(attachment.oss_key == oss_key for attachment in contribution.attachments):
                return oss_key
        return ""

    def review(self, cid: str, approve: bool, reviewer: str,
               course_slug: str = "", topic_slug: str = "") -> Contribution:
        c = self.store.get(cid)
        if not c:
            raise ValueError("贡献不存在")
        c.review_status = "approved" if approve else "rejected"
        c.reviewed_by = reviewer
        c.reviewed_at = now_iso()
        if course_slug or topic_slug:  # admin may fix tag at review time
            c.course_slug, c.topic_slug = course_slug, topic_slug
            c.new_tag_name = ""
        self.store.put(c)
        return c

    def attach_summary(self, cid: str, attachment_index: int,
                       summary_oss_key: str, ocr_oss_key: str = "") -> None:
        c = self.store.get(cid)
        if c and 0 <= attachment_index < len(c.attachments):
            c.attachments[attachment_index].summary_oss_key = summary_oss_key
            c.attachments[attachment_index].ocr_oss_key = ocr_oss_key
            self.store.put(c)

    def mark_queued(self, contribution_ids: List[str]) -> None:
        self._set_guide_state(contribution_ids, "queued")

    def mark_waiting(self, contribution_ids: List[str]) -> None:
        """Return approved work to the visible, non-public waiting state."""
        self._set_guide_state(contribution_ids, "not_queued")

    def mark_candidate_ready(self, contribution_ids: List[str], candidate_id: str) -> None:
        self._set_guide_state(contribution_ids, "candidate_ready", candidate_id=candidate_id)

    def mark_published(self, contribution_ids: List[str], version: int) -> None:
        self._set_guide_state(contribution_ids, "published", version=version)

    def _set_guide_state(self, contribution_ids: List[str], state: str,
                         candidate_id: str = "", version: int = 0) -> None:
        for contribution_id in set(contribution_ids):
            contribution = self.store.get(contribution_id)
            if not contribution or contribution.review_status != "approved":
                continue
            contribution.guide_state = state
            contribution.guide_candidate_id = candidate_id
            contribution.guide_published_version = version
            contribution.guide_updated_at = now_iso()
            self.store.put(contribution)
