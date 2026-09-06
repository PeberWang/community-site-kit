# -*- coding: utf-8 -*-
"""Event service - 活动栏: online (meeting link) / offline (place), reason required, review gate."""

from typing import List, Optional

from config.schema import Event, EVENT_MODES
from config.settings import Settings
from services.store import JsonStore, new_id, now_iso


class EventService:
    def __init__(self, settings: Settings):
        self.store = JsonStore(settings.db_dir, "events", Event, key=lambda e: e.id)

    def submit(self, organizer: str, title: str,
               mode: str, start_time: str, place: str, reason: str,
               end_time: str = "", description: str = "") -> Event:
        if mode not in EVENT_MODES:
            raise ValueError(f"非法活动形式: {mode}")
        title, place, reason = title.strip(), place.strip(), reason.strip()
        self._validate_times(start_time, end_time)
        if not title or not start_time or not place or not reason:
            raise ValueError("标题、开始时间、结束时间、地点/链接、发起理由均为必填")
        e = Event(id=new_id(), title=title, mode=mode, start_time=start_time,
                  end_time=end_time.strip(), place=place,
                  description=description.strip(), reason=reason,
                  organizer=organizer,
                  created_at=now_iso())
        self.store.put(e)
        return e

    def get(self, eid: str) -> Optional[Event]:
        return self.store.get(eid)

    def pending(self) -> List[Event]:
        return sorted(self.store.find(lambda e: e.review_status == "pending"),
                      key=lambda e: e.created_at)

    def published(self) -> List[Event]:
        return sorted(self.store.find(lambda e: e.review_status == "approved"
                                      and not e.withdrawn),
                      key=lambda e: e.start_time)

    def managed(self) -> List[Event]:
        """All approved records, including withdrawn items, for administrators."""
        return sorted(self.store.find(lambda e: e.review_status == "approved"),
                      key=lambda e: e.start_time)

    def upcoming(self) -> List[Event]:
        now = now_iso()[:16]
        return [e for e in self.published() if e.start_time > now]

    def ongoing(self) -> List[Event]:
        now = now_iso()[:16]
        return [e for e in self.published() if e.start_time <= now < e.end_time]

    def past(self) -> List[Event]:
        now = now_iso()[:16]
        return sorted([e for e in self.published() if e.end_time <= now],
                      key=lambda e: e.start_time, reverse=True)

    @staticmethod
    def _validate_times(start_time: str, end_time: str) -> None:
        start_time, end_time = start_time.strip(), end_time.strip()
        if not start_time or not end_time:
            raise ValueError("开始时间和结束时间均为必填")
        if end_time <= start_time:
            raise ValueError("结束时间必须晚于开始时间")

    def review(self, eid: str, approve: bool, reviewer: str) -> Event:
        e = self.store.get(eid)
        if not e:
            raise ValueError("活动不存在")
        e.review_status = "approved" if approve else "rejected"
        e.reviewed_by = reviewer
        if approve and not e.published_at:
            e.published_at = now_iso()
        self.store.put(e)
        return e

    def update_published(self, eid: str, title: str, mode: str,
                         start_time: str, end_time: str, place: str,
                         reason: str, description: str, editor: str) -> Event:
        e = self.store.get(eid)
        if not e or e.review_status != "approved":
            raise ValueError("只有已发布活动可以编辑")
        if mode not in EVENT_MODES:
            raise ValueError(f"非法活动形式: {mode}")
        title, place, reason = title.strip(), place.strip(), reason.strip()
        self._validate_times(start_time, end_time)
        if not title or not start_time or not place or not reason:
            raise ValueError("标题、开始时间、结束时间、地点/链接、发起理由均为必填")
        e.title, e.mode, e.start_time, e.end_time = title, mode, start_time, end_time.strip()
        e.place, e.reason, e.description = place, reason, description.strip()
        e.updated_at, e.updated_by = now_iso(), editor
        self.store.put(e)
        return e

    def withdraw(self, eid: str, actor: str) -> Event:
        e = self.store.get(eid)
        if not e or e.review_status != "approved":
            raise ValueError("只有已发布活动可以下线")
        e.withdrawn, e.withdrawn_at, e.withdrawn_by = True, now_iso(), actor
        self.store.put(e)
        return e

    def restore(self, eid: str, actor: str) -> Event:
        e = self.store.get(eid)
        if not e or e.review_status != "approved":
            raise ValueError("活动不存在或尚未发布")
        e.withdrawn, e.withdrawn_at, e.withdrawn_by = False, "", ""
        e.updated_at, e.updated_by = now_iso(), actor
        self.store.put(e)
        return e
