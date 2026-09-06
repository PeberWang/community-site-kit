# -*- coding: utf-8 -*-

import asyncio

from config.settings import Settings
from glue.guide_lifecycle import GuideLifecycle
from services.contribution_service import ContributionService
from services.tag_service import TagService


def lifecycle_settings(tmp_path):
    return Settings(
        project_root=tmp_path,
        db_dir=tmp_path / "db",
        guides_dir=tmp_path / "guides",
        uploads_dir=tmp_path / "uploads",
        summary_dir=tmp_path / "summaries",
        cloud_stub_dir=tmp_path / "oss",
        guide_compile_delay_minutes=0,
        guide_worker_batch_size=3,
    )


def approved_contribution(settings, course_slug, contributor):
    contributions = ContributionService(settings)
    contribution = contributions.submit(contributor, course_slug=course_slug,
                                        text="建议先完成课后练习，再复盘错题。")
    return contributions.review(contribution.id, approve=True, reviewer="admin")


def test_approved_contributions_coalesce_then_publish_only_after_admin_action(tmp_path):
    settings = lifecycle_settings(tmp_path)
    course = TagService(settings).add_course("演示课", "大一上")
    first = approved_contribution(settings, course.slug, "user-one")
    second = approved_contribution(settings, course.slug, "user-two")
    lifecycle = GuideLifecycle(settings)

    first_job = lifecycle.queue_contribution(first)
    second_job = lifecycle.queue_contribution(second)

    assert first_job == second_job
    assert lifecycle.guides.get(course.guide_slug).version == 0
    assert lifecycle.contributions.get(first.id).guide_state == "queued"

    async def fake_generate(guide_slug, actor):
        candidate = lifecycle.guides.create_candidate(
            guide_slug, "## 学习路径\n先完成练习。", actor,
            contribution_ids=[first.id, second.id])
        lifecycle.contributions.mark_candidate_ready(candidate.contribution_ids, candidate.id)
        return candidate

    lifecycle.generate_candidate = fake_generate
    assert asyncio.run(lifecycle.process_due_jobs()) == 1

    candidate = lifecycle.guides.list_candidates(course.guide_slug)[0]
    assert lifecycle.guides.get(course.guide_slug).version == 0
    assert lifecycle.contributions.get(first.id).guide_state == "candidate_ready"
    assert lifecycle.contributions.get(second.id).guide_state == "candidate_ready"

    lifecycle.compilation.current_source_fingerprint = lambda _slug: ""
    published = lifecycle.publish_candidate(candidate.id, "admin")

    assert published.version == 1
    assert lifecycle.contributions.get(first.id).guide_state == "published"
    assert lifecycle.contributions.get(first.id).guide_published_version == 1


def test_discarded_candidate_returns_contributions_to_waiting_state(tmp_path):
    settings = lifecycle_settings(tmp_path)
    course = TagService(settings).add_course("另一门演示课", "大一上")
    contribution = approved_contribution(settings, course.slug, "user-one")
    lifecycle = GuideLifecycle(settings)
    lifecycle.queue_contribution(contribution)
    candidate = lifecycle.guides.create_candidate(
        course.guide_slug, "## 学习路径\n候选内容。", "admin",
        contribution_ids=[contribution.id])
    lifecycle.contributions.mark_candidate_ready([contribution.id], candidate.id)

    lifecycle.discard_candidate(candidate.id)

    assert lifecycle.guides.get_candidate(candidate.id).status == "discarded"
    assert lifecycle.contributions.get(contribution.id).guide_state == "not_queued"
