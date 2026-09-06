# -*- coding: utf-8 -*-

from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

import app.deps as deps
from app.main import app
from config.schema import Invite, User
from config.settings import Settings
from services.user_service import UserService


def user_settings(tmp_path):
    return Settings(
        project_root=tmp_path,
        db_dir=tmp_path / "db",
        guides_dir=tmp_path / "guides",
        uploads_dir=tmp_path / "uploads",
        summary_dir=tmp_path / "summaries",
        cloud_stub_dir=tmp_path / "oss",
    )


def test_invite_allows_its_configured_number_of_registrations(tmp_path):
    service = UserService(user_settings(tmp_path))
    invite = service.create_invite("user", "admin-one", max_uses=2)

    first = service.register("first", "password-one", "小李", invite.code)
    second = service.register("second", "password-two", "小王", invite.code)
    stored = service.invites.get(invite.code)

    assert stored.max_uses == 2
    assert stored.used_count == 2
    assert stored.used_by == first.id
    assert stored.used_by_ids == [first.id, second.id]
    with pytest.raises(ValueError, match="使用次数上限"):
        service.register("third", "password-three", "小周", invite.code)


def test_simultaneous_registration_cannot_exceed_invite_capacity(tmp_path):
    service = UserService(user_settings(tmp_path))
    invite = service.create_invite("user", "admin-one", max_uses=1)

    def register_one(number):
        try:
            return service.register(f"user-{number}", "password", f"同学{number}", invite.code)
        except ValueError:
            return None

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(register_one, range(2)))

    assert len([user for user in results if user]) == 1
    assert service.invites.get(invite.code).used_count == 1


def test_legacy_used_invite_stays_full_and_cannot_be_deleted(tmp_path):
    service = UserService(user_settings(tmp_path))
    service.invites.put(Invite(code="legacy-code", used_by="legacy-user"))
    stored = service.invites.get("legacy-code")

    assert service.invite_usage_count(stored) == 1
    assert not service.delete_invite(stored.code)
    with pytest.raises(ValueError, match="使用次数上限"):
        service.register("new-user", "password", "新用户", stored.code)


def test_account_search_matches_invite_note_and_user_identity_or_role(tmp_path):
    service = UserService(user_settings(tmp_path))
    service.invites.put(Invite(code="class-committee", note="23级班委", created_at="2026-01-01"))
    service.invites.put(Invite(code="teacher-review", note="学院老师审核", created_at="2026-01-02"))
    service.users.put(User(username="lin", id="user-one", display_name="小林", role="admin",
                           created_at="2026-01-01"))
    service.users.put(User(username="wang", id="user-two", display_name="王同学", role="observer",
                           created_at="2026-01-02"))
    service.users.put(User(username="zhao", id="user-three", display_name="赵同学", role="user",
                           created_at="2026-01-03"))

    assert [item.code for item in service.search_invites("班委")] == ["class-committee"]
    assert [item.code for item in service.search_invites("teacher")] == ["teacher-review"]
    assert [item.username for item in service.search_users("小林")] == ["lin"]
    assert [item.username for item in service.search_users("wang")] == ["wang"]
    assert [item.username for item in service.search_users("管理员")] == ["lin"]
    assert [item.username for item in service.search_users("观察员")] == ["wang"]


def test_account_page_limits_default_lists_and_keeps_search_results(tmp_path, monkeypatch):
    settings = user_settings(tmp_path)
    service = UserService(settings)
    admin = User(username="admin", id="admin-one", display_name="管理员", role="admin",
                 created_at="2026-01-01")
    service.users.put(admin)
    for number in range(1, 7):
        service.invites.put(Invite(code=f"invite-{number}", note=f"purpose-{number}",
                                   created_at=f"2026-02-{number:02d}"))
        service.users.put(User(username=f"member-{number}", id=f"user-{number}",
                               display_name=f"同学{number}", created_at=f"2026-03-{number:02d}"))
    monkeypatch.setattr(deps, "app_settings", settings)
    deps._serializer = None
    deps._services.clear()
    try:
        client = TestClient(app)
        client.cookies.set(deps.SESSION_COOKIE, deps.serializer().dumps(admin.id))
        default_page = client.get("/admin/accounts")
        searched_page = client.get("/admin/accounts?invite_query=purpose-1&user_query=管理员")
    finally:
        deps._serializer = None
        deps._services.clear()

    assert default_page.status_code == 200
    assert "最近 5 条" in default_page.text
    assert "invite-6" in default_page.text
    assert "invite-1" not in default_page.text
    assert "member-6" in default_page.text
    assert "member-1" not in default_page.text
    assert searched_page.status_code == 200
    assert "invite-1" in searched_page.text
    assert "invite-6" not in searched_page.text
    assert "@admin" in searched_page.text
    assert "@member-6" not in searched_page.text


def test_role_search_shows_the_newest_fifty_results_at_most(tmp_path, monkeypatch):
    settings = user_settings(tmp_path)
    service = UserService(settings)
    admin = User(username="admin", id="admin-one", display_name="管理员", role="admin",
                 created_at="2026-01-01")
    service.users.put(admin)
    for number in range(1, 52):
        service.users.put(User(username=f"member-{number}", id=f"user-{number}",
                               display_name=f"同学{number}", created_at=f"2026-04-{number:02d}"))
    monkeypatch.setattr(deps, "app_settings", settings)
    deps._serializer = None
    deps._services.clear()
    try:
        client = TestClient(app)
        client.cookies.set(deps.SESSION_COOKIE, deps.serializer().dumps(admin.id))
        page = client.get("/admin/accounts?user_query=一般用户")
    finally:
        deps._serializer = None
        deps._services.clear()

    assert page.status_code == 200
    assert "匹配 51，显示最近 50" in page.text
    assert "@member-51" in page.text
    assert "@member-1</span>" not in page.text
