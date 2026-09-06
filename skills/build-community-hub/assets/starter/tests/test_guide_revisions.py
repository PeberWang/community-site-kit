# -*- coding: utf-8 -*-

import pytest

from config.settings import Settings
from libs.exceptions import GuideConflictException, GuideValidationException
from services.guide_service import GuideService, body_sha256


def guide_settings(tmp_path):
    return Settings(
        project_root=tmp_path,
        db_dir=tmp_path / "db",
        guides_dir=tmp_path / "guides",
        uploads_dir=tmp_path / "uploads",
        summary_dir=tmp_path / "summaries",
        cloud_stub_dir=tmp_path / "oss",
    )


def test_candidate_never_overwrites_a_new_human_edit(tmp_path):
    guides = GuideService(guide_settings(tmp_path))
    guides.ensure("course-demo", "course", "演示课", "demo")
    first = guides.save_body("course-demo", "## 学习路径\n人工正文", "admin")
    candidate = guides.create_candidate(
        "course-demo", "## 学习路径\n候选正文\n## 考核与复习\n待确认\n## 已知缺口\n暂无",
        "admin")
    guides.save_body("course-demo", "## 学习路径\n更新后的人工正文", "admin",
                     expected_body_sha256=first.body_sha256)

    with pytest.raises(GuideConflictException):
        guides.publish_candidate(candidate.id, "admin")

    assert guides.read_body("course-demo") == "## 学习路径\n更新后的人工正文"
    assert guides.get_candidate(candidate.id).status == "stale"


def test_history_names_are_unique_and_restore_creates_a_new_version(tmp_path):
    guides = GuideService(guide_settings(tmp_path))
    guides.ensure("course-demo", "course", "演示课", "demo")
    guides.save_body("course-demo", "第一版", "admin")
    second = guides.save_body("course-demo", "第二版", "admin")
    guides.save_body("course-demo", "第三版", "admin", expected_body_sha256=second.body_sha256)

    history = guides.list_history("course-demo")
    assert len(history) >= 2
    assert len(history) == len(set(history))
    restored = guides.restore_history("course-demo", history[0], "admin")
    assert restored.version == 4
    assert guides.read_body("course-demo")


def test_candidate_with_blocking_errors_cannot_publish(tmp_path):
    guides = GuideService(guide_settings(tmp_path))
    guides.ensure("course-demo", "course", "演示课", "demo")
    candidate = guides.create_candidate("course-demo", "不合格", "admin",
                                        validation_errors=["缺少必需章节"])

    with pytest.raises(GuideValidationException):
        guides.publish_candidate(candidate.id, "admin")


def test_body_hash_tracks_the_published_markdown(tmp_path):
    guides = GuideService(guide_settings(tmp_path))
    guides.ensure("course-demo", "course", "演示课", "demo")
    guide = guides.save_body("course-demo", "可追溯正文", "admin")

    assert guide.body_sha256 == body_sha256("可追溯正文")


def test_pending_candidates_only_returns_items_waiting_for_human_publish(tmp_path):
    guides = GuideService(guide_settings(tmp_path))
    guides.ensure("course-demo", "course", "演示课", "demo")
    waiting = guides.create_candidate("course-demo", "候选正文", "admin")
    discarded = guides.create_candidate("course-demo", "另一份候选", "admin")
    guides.discard_candidate(discarded.id)

    assert [item.id for item in guides.pending_candidates()] == [waiting.id]
