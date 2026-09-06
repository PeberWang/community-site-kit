# -*- coding: utf-8 -*-

from fastapi.testclient import TestClient

import app.deps as deps
from app.main import app
from config.schema import User
from config.settings import Settings


def admin_settings(tmp_path):
    return Settings(
        project_root=tmp_path, db_dir=tmp_path / "db", guides_dir=tmp_path / "guides",
        uploads_dir=tmp_path / "uploads", summary_dir=tmp_path / "summaries",
        cloud_stub_dir=tmp_path / "oss",
    )


def test_admin_pages_separate_daily_management_from_review_queue(tmp_path, monkeypatch):
    settings = admin_settings(tmp_path)
    monkeypatch.setattr(deps, "app_settings", settings)
    deps._serializer = None
    deps._services.clear()
    try:
        admin = User(username="admin", id="admin-one", display_name="管理员", role="admin",
                     created_at="2026-01-01")
        deps.svc("users").users.put(admin)
        announcements = deps.svc("announcements")
        for number in range(1, 7):
            announcement = announcements.publish(f"公告 {number}", "公告内容", admin.id)
            announcement.created_at = f"2026-01-{number:02d}T00:00:00"
            announcements.store.put(announcement)
        announcements.publish("迎新公告", "公告内容", admin.id)
        article = deps.svc("articles").submit("author", "已发布文章", "正文", course_slug="demo")
        deps.svc("articles").review(article.id, approve=True, reviewer=admin.id)
        guide = deps.svc("guides").ensure("course-demo", "course", "演示课", "demo")
        candidate = deps.svc("guides").create_candidate(guide.slug, "候选正文", admin.id)

        client = TestClient(app)
        client.cookies.set(deps.SESSION_COOKIE, deps.serializer().dumps(admin.id))
        review_page = client.get("/admin")
        default_announcement_page = client.get("/admin/announcements")
        announcement_page = client.get("/admin/announcements?query=迎新")
        event_page = client.get("/admin/events")
        article_page = client.get("/admin/articles")
    finally:
        deps._serializer = None
        deps._services.clear()

    assert review_page.status_code == 200
    assert "待发布指南候选稿" in review_page.text
    assert f"/admin/guides/{guide.slug}/candidates/{candidate.id}" in review_page.text
    assert "公告管理" in review_page.text and "活动管理" in review_page.text
    assert "发布公告" not in review_page.text and "直接发布活动" not in review_page.text
    assert default_announcement_page.status_code == 200
    assert "公告 6" in default_announcement_page.text
    assert "公告 1" not in default_announcement_page.text
    assert default_announcement_page.text.index("发布公告") < default_announcement_page.text.index("已上线与已下线公告")
    assert '<details class="collapse-block"' in default_announcement_page.text
    assert announcement_page.status_code == 200 and "迎新公告" in announcement_page.text
    assert "发布公告" in announcement_page.text
    assert event_page.status_code == 200 and "直接发布活动" in event_page.text
    assert article_page.status_code == 200 and "已发布文章" in article_page.text
