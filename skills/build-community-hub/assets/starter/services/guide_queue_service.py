"""Persistent, coalescing queue for guide candidate preparation."""

from datetime import datetime, timedelta
from typing import List, Optional

from config.schema import GuideCompileJob
from config.settings import Settings
from libs.json_io import path_lock
from services.store import JsonStore, new_id, now_iso


class GuideQueueService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.store = JsonStore(settings.db_dir, "guide_compile_jobs", GuideCompileJob,
                               key=lambda job: job.id)

    def enqueue(self, guide_slug: str, contribution_id: str) -> GuideCompileJob:
        with path_lock(self.store.path, exclusive=True):
            jobs = self.store._all_unlocked()
            queued = next((job for job in jobs if job.guide_slug == guide_slug
                           and job.status == "queued"), None)
            due_at = (datetime.now().astimezone() + timedelta(
                minutes=self.settings.guide_compile_delay_minutes)).isoformat(timespec="seconds")
            if queued:
                queued.contribution_ids = list(dict.fromkeys(
                    [*queued.contribution_ids, contribution_id]))
                queued.run_after = due_at
                self.store._dump_unlocked(jobs)
                return queued
            job = GuideCompileJob(id=new_id(), guide_slug=guide_slug,
                                  contribution_ids=[contribution_id], requested_at=now_iso(),
                                  run_after=due_at)
            jobs.append(job)
            self.store._dump_unlocked(jobs)
            return job

    def claim_due(self) -> Optional[GuideCompileJob]:
        now = datetime.now().astimezone()
        with path_lock(self.store.path, exclusive=True):
            jobs = self.store._all_unlocked()
            for job in jobs:
                self._recover_expired_claim(job, now)
                if job.status == "queued" and self._is_due(job, now):
                    job.status = "running"
                    job.started_at = now.isoformat(timespec="seconds")
                    self.store._dump_unlocked(jobs)
                    return job
        return None

    def _is_due(self, job: GuideCompileJob, now: datetime) -> bool:
        try:
            return datetime.fromisoformat(job.run_after) <= now
        except ValueError:
            job.run_after = now.isoformat(timespec="seconds")
            return True

    def _recover_expired_claim(self, job: GuideCompileJob, now: datetime) -> None:
        if job.status != "running":
            return
        try:
            started = datetime.fromisoformat(job.started_at)
        except ValueError:
            started = now - timedelta(minutes=self.settings.guide_worker_timeout_minutes + 1)
        if started + timedelta(minutes=self.settings.guide_worker_timeout_minutes) <= now:
            job.status = "queued"
            job.started_at = ""
            job.run_after = now.isoformat(timespec="seconds")

    def complete(self, job_id: str, candidate_id: str) -> None:
        self._finish(job_id, "completed", candidate_id=candidate_id)

    def fail(self, job_id: str, error: Exception) -> None:
        self._finish(job_id, "failed", error=str(error)[:300])

    def _finish(self, job_id: str, status: str, candidate_id: str = "", error: str = "") -> None:
        job = self.store.get(job_id)
        if job:
            job.status, job.candidate_id, job.error = status, candidate_id, error
            self.store.put(job)

    def pending_for(self, guide_slug: str) -> List[GuideCompileJob]:
        return self.store.find(lambda job: job.guide_slug == guide_slug and job.status == "queued")

    def list_for(self, guide_slug: str) -> List[GuideCompileJob]:
        return sorted(self.store.find(lambda job: job.guide_slug == guide_slug),
                      key=lambda job: job.requested_at, reverse=True)

    def complete_queued_for_guide(self, guide_slug: str, candidate_id: str) -> None:
        """Prevent a manual candidate run from being duplicated by a waiting job."""
        with path_lock(self.store.path, exclusive=True):
            jobs = self.store._all_unlocked()
            changed = False
            for job in jobs:
                if job.guide_slug == guide_slug and job.status == "queued":
                    job.status = "completed"
                    job.candidate_id = candidate_id
                    changed = True
            if changed:
                self.store._dump_unlocked(jobs)
