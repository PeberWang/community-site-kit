# -*- coding: utf-8 -*-

from config.settings import Settings
from services.announce_service import AnnounceService
from services.article_service import ArticleService
from services.event_service import EventService


def content_settings(tmp_path):
    return Settings(
        project_root=tmp_path, db_dir=tmp_path / "db", guides_dir=tmp_path / "guides",
        uploads_dir=tmp_path / "uploads", summary_dir=tmp_path / "summaries",
        cloud_stub_dir=tmp_path / "oss",
    )


def test_admin_can_edit_and_soft_withdraw_article(tmp_path):
    service = ArticleService(content_settings(tmp_path))
    article = service.submit("author", "旧标题", "旧正文", course_slug="demo")
    service.review(article.id, approve=True, reviewer="admin")

    service.update_published(article.id, "新标题", "新正文", "admin")
    service.withdraw(article.id, "admin")

    saved = service.get(article.id)
    assert saved.title == "新标题"
    assert saved.body == "新正文"
    assert saved.withdrawn and saved.withdrawn_by == "admin"
    assert service.published() == []
    assert service.managed()[0].id == article.id


def test_admin_can_edit_and_soft_withdraw_event(tmp_path):
    service = EventService(content_settings(tmp_path))
    event = service.submit("author", "旧活动", "offline", "2026-10-01T10:00",
                           "旧地点", "旧理由", "2026-10-01T11:00")
    service.review(event.id, approve=True, reviewer="admin")

    service.update_published(event.id, "新活动", "online", "2026-10-02T10:00",
                             "2026-10-02T11:00", "https://example.test/room",
                             "新理由", "新详情", "admin")
    service.withdraw(event.id, "admin")

    saved = service.get(event.id)
    assert saved.mode == "online" and saved.place.endswith("room")
    assert saved.withdrawn and saved.withdrawn_by == "admin"
    assert service.published() == []


def test_event_sections_use_start_and_end_boundaries(tmp_path, monkeypatch):
    service = EventService(content_settings(tmp_path))
    monkeypatch.setattr("services.event_service.now_iso", lambda: "2026-10-01T12:00:00+08:00")
    for title, start, end in (
        ("预告", "2026-10-01T13:00", "2026-10-01T14:00"),
        ("进行中", "2026-10-01T11:00", "2026-10-01T13:00"),
        ("往期", "2026-10-01T09:00", "2026-10-01T10:00"),
    ):
        event = service.submit("author", title, "offline", start, "地点", "理由", end)
        service.review(event.id, approve=True, reviewer="admin")

    assert [e.title for e in service.upcoming()] == ["预告"]
    assert [e.title for e in service.ongoing()] == ["进行中"]
    assert [e.title for e in service.past()] == ["往期"]


def test_event_end_time_is_required_and_must_follow_start(tmp_path):
    service = EventService(content_settings(tmp_path))

    try:
        service.submit("author", "缺结束时间", "offline", "2026-10-01T10:00", "地点", "理由")
    except ValueError as error:
        assert "结束时间" in str(error)
    else:
        raise AssertionError("missing end time should be rejected")

    try:
        service.submit("author", "顺序错误", "offline", "2026-10-01T11:00", "地点", "理由",
                       "2026-10-01T10:00")
    except ValueError as error:
        assert "晚于" in str(error)
    else:
        raise AssertionError("end before start should be rejected")


def test_announcement_edit_and_withdraw_keep_record(tmp_path):
    service = AnnounceService(content_settings(tmp_path))
    announcement = service.publish("旧标题", "旧内容", "admin")

    service.update(announcement.id, "新标题", "新内容", "admin")
    service.withdraw(announcement.id, "admin")

    saved = service.store.get(announcement.id)
    assert saved.title == "新标题" and saved.deleted
    assert saved.deleted_by == "admin"
    assert service.list_active() == []
    assert service.managed()[0].id == announcement.id


def test_admin_content_search_matches_titles(tmp_path):
    settings = content_settings(tmp_path)
    announcements = AnnounceService(settings)
    articles = ArticleService(settings)
    announcements.publish("迎新安排", "内容", "admin")
    announcements.publish("课程安排", "内容", "admin")
    article = articles.submit("author", "伦理学导论笔记", "正文", course_slug="demo")
    articles.review(article.id, approve=True, reviewer="admin")

    assert [item.title for item in announcements.search_managed("迎新")] == ["迎新安排"]
    assert [item.title for item in articles.search_managed("伦理学")] == ["伦理学导论笔记"]
