"""Contribution-to-guide lifecycle: queue candidates automatically, publish manually."""

from typing import Optional

from config.settings import Settings
from glue.guide_compilation import GuideCompilation
from services.contribution_service import ContributionService
from services.guide_queue_service import GuideQueueService
from services.guide_service import GuideService
from services.tag_service import TagService


class GuideLifecycle:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.compilation = GuideCompilation(settings)
        self.contributions = ContributionService(settings)
        self.guides = GuideService(settings)
        self.queue = GuideQueueService(settings)
        self.tags = TagService(settings)

    def queue_contribution(self, contribution) -> Optional[str]:
        if contribution.review_status != "approved":
            return None
        guide_slug = self._ensure_target_guide(contribution)
        if not guide_slug:
            return None
        self.contributions.mark_queued([contribution.id])
        return self.queue.enqueue(guide_slug, contribution.id).id

    async def generate_candidate(self, guide_slug: str, actor: str):
        candidate = await self.compilation.generate_candidate(guide_slug, actor)
        self.contributions.mark_candidate_ready(candidate.contribution_ids, candidate.id)
        if actor != "guide-worker":
            self.queue.complete_queued_for_guide(guide_slug, candidate.id)
        return candidate

    async def process_due_jobs(self) -> int:
        completed = 0
        for _ in range(self.settings.guide_worker_batch_size):
            job = self.queue.claim_due()
            if not job:
                break
            try:
                candidate = await self.generate_candidate(job.guide_slug, "guide-worker")
                self.queue.complete(job.id, candidate.id)
                completed += 1
            except Exception as error:
                self.queue.fail(job.id, error)
                self.contributions.mark_waiting(job.contribution_ids)
        return completed

    def publish_candidate(self, candidate_id: str, approved_by: str):
        candidate = self.guides.get_candidate(candidate_id)
        if not candidate:
            raise ValueError("候选稿不存在")
        fingerprint = self.compilation.current_source_fingerprint(candidate.guide_slug)
        guide = self.guides.publish_candidate(candidate_id, approved_by, fingerprint)
        self.contributions.mark_published(candidate.contribution_ids, guide.version)
        return guide

    def discard_candidate(self, candidate_id: str) -> None:
        candidate = self.guides.get_candidate(candidate_id)
        if not candidate:
            return
        self.guides.discard_candidate(candidate_id)
        self.contributions.mark_waiting(candidate.contribution_ids)

    def _ensure_target_guide(self, contribution) -> str:
        if contribution.course_slug:
            course = self.tags.get_course(contribution.course_slug)
            if not course:
                return ""
            self.guides.ensure(course.guide_slug, "course", f"{course.name} 学习指南", course.slug)
            return course.guide_slug
        if contribution.topic_slug:
            topic = self.tags.get_topic(contribution.topic_slug)
            if not topic:
                return ""
            self.guides.ensure(topic.guide_slug, "topic", topic.title, topic.slug)
            return topic.guide_slug
        return ""
