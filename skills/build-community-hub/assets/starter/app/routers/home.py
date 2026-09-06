# -*- coding: utf-8 -*-
"""Home router - 推送式首页: highlights feed of what's new/updated.

时效规则：feed 只保留最近 FEED_WINDOW_HOURS 小时内产生/更新的条目，
超龄条目自动从首页下架（数据本身不受影响）。
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app.deps import svc
from app.templating import templates
from config.settings import settings
from libs.community_config import load_community

router = APIRouter()

FEED_WINDOW_HOURS = 48


def _within_window(stamp: str, cutoff: datetime) -> bool:
    try:
        return datetime.fromisoformat(stamp) >= cutoff
    except ValueError:
        return False


@router.get("/")
def home(request: Request):
    if not request.state.user:
        return RedirectResponse("/login", status_code=303)

    cutoff = datetime.now().astimezone() - timedelta(hours=FEED_WINDOW_HOURS)

    community = load_community(str(settings.community_config))
    feed = []
    for g in svc("guides").recently_updated(20) if community.features.guides else []:
        if g.version <= 0 or not _within_window(g.updated_at, cutoff):
            continue
        feed.append({
            "time": g.updated_at, "kind": "guide",
            "label": "指南更新" if g.version > 1 else "指南上线",
            "title": g.title,
            "url": f"/guides/{g.kind}/{g.ref_slug}",
            "actor": community.site.system_name if g.updated_by in ("llm", "system") else g.updated_by,
        })
    for a in svc("articles").published() if community.features.articles else []:
        if not _within_window(a.published_at, cutoff):
            continue
        feed.append({
            "time": a.published_at, "kind": "article",
            "label": "新文章", "title": a.title,
            "url": f"/articles/{a.id}", "actor": svc("users").display_name(a.author),
        })
    events = svc("events")
    visible_events = events.upcoming() + events.ongoing() if community.features.events else []
    for e in visible_events:
        if not _within_window(e.published_at, cutoff):
            continue
        feed.append({
            "time": e.published_at, "kind": "event",
            "label": "新活动", "title": e.title,
            "url": "/events", "actor": svc("users").display_name(e.organizer),
        })
    feed.sort(key=lambda x: x["time"], reverse=True)

    return templates.TemplateResponse(request, "home.html", {
        "request": request, "feed": feed[:30],
        "announcements": svc("announcements").list_active()})
