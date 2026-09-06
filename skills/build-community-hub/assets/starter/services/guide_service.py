# -*- coding: utf-8 -*-
"""Guide truth source, candidates, immutable revision records and recovery."""

import hashlib
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, List, Optional

from config.schema import Guide, GuideCandidate, GuideRevision
from config.settings import Settings
from libs.exceptions import GuideConflictException, GuideValidationException, StoreException
from libs.json_io import atomic_write_text, path_lock
from services.store import JsonStore, now_iso

_PLACEHOLDER = "（本课程还没有指南。欢迎贡献资料、心得或文章，有贡献后将自动生成本课指南。）"


def body_sha256(body: str) -> str:
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


class GuideService:
    """Keep Markdown as the published truth while preserving every change."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.index = JsonStore(settings.db_dir, "guides", Guide, key=lambda guide: guide.slug)
        self.candidates = JsonStore(settings.db_dir, "guide_candidates", GuideCandidate,
                                    key=lambda candidate: candidate.id)
        self.revisions = JsonStore(settings.db_dir, "guide_revisions", GuideRevision,
                                   key=lambda revision: revision.id)
        self.dir = Path(settings.guides_dir)
        self.history_dir = self.dir / "history"
        self.revision_dir = self.history_dir / "revisions"
        self.candidate_dir = self.dir / "candidates"
        self.lock_dir = self.dir / ".locks"
        for directory in (self.dir, self.history_dir, self.revision_dir,
                          self.candidate_dir, self.lock_dir):
            directory.mkdir(parents=True, exist_ok=True)

    def _path(self, slug: str) -> Path:
        return self.dir / f"{slug}.md"

    def _candidate_path(self, candidate_id: str) -> Path:
        return self.candidate_dir / f"{candidate_id}.md"

    @contextmanager
    def _guide_lock(self, slug: str) -> Iterator[None]:
        with path_lock(self.lock_dir / f"{slug}.guide", exclusive=True):
            yield

    def _read_text(self, path: Path) -> str:
        try:
            with open(path, "r", encoding="utf-8", newline="\n") as source:
                return source.read()
        except FileNotFoundError:
            return ""
        except OSError as error:
            raise StoreException(f"无法读取指南正文 {path}: {error}") from error

    def read_body(self, slug: str) -> str:
        return self._read_text(self._path(slug))

    def _new_revision_id(self) -> str:
        return f"rev-{uuid.uuid4().hex[:16]}"

    def _archive_current(self, guide: Guide, body: str) -> None:
        if not body:
            return
        digest = body_sha256(body)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
        archive_name = f"{guide.slug}.{stamp}.{digest[:10]}.{uuid.uuid4().hex[:8]}.md"
        archive_path = self.history_dir / archive_name
        atomic_write_text(archive_path, body)
        revision_id = guide.revision_id or self._new_revision_id()
        if not self.revisions.get(revision_id):
            self.revisions.put(GuideRevision(
                id=revision_id, guide_slug=guide.slug, version=guide.version,
                body_sha256=digest, body_path=str(archive_path.relative_to(self.dir)),
                parent_revision_id="", created_at=guide.updated_at or now_iso(),
                created_by=guide.updated_by, approved_by=guide.updated_by,
                change_summary=guide.change_summary, status="archived"))

    def _prepare_guide(self, slug: str) -> Guide:
        guide = self.index.get(slug)
        if not guide:
            raise ValueError("指南不存在")
        current_hash = body_sha256(self.read_body(slug))
        if guide.body_sha256 != current_hash:
            guide.body_sha256 = current_hash
            self.index.put(guide)
        return guide

    def ensure(self, slug: str, kind: str, title: str, ref_slug: str) -> Guide:
        with self._guide_lock(slug):
            guide = self.index.get(slug)
            if guide:
                return self._prepare_guide(slug)
            atomic_write_text(self._path(slug), _PLACEHOLDER)
            guide = Guide(slug=slug, kind=kind, title=title, ref_slug=ref_slug,
                          updated_at=now_iso(), updated_by="system", version=0,
                          body_sha256=body_sha256(_PLACEHOLDER))
            self.index.put(guide)
            return guide

    def get(self, slug: str) -> Optional[Guide]:
        guide = self.index.get(slug)
        if guide and not guide.body_sha256:
            with self._guide_lock(slug):
                return self._prepare_guide(slug)
        return guide

    def save_body(self, slug: str, body: str, updated_by: str,
                  expected_body_sha256: str = "", change_summary: str = "",
                  source_ids: Optional[List[str]] = None) -> Guide:
        """Publish a human edit only when it started from the current body."""
        with self._guide_lock(slug):
            guide = self._prepare_guide(slug)
            if expected_body_sha256 and guide.body_sha256 != expected_body_sha256:
                raise GuideConflictException("正式版已在你编辑期间更新，请刷新后再保存。")
            return self._publish_locked(guide, body, updated_by, change_summary,
                                        source_ids or [], approved_by=updated_by)

    def _publish_locked(self, guide: Guide, body: str, updated_by: str,
                        change_summary: str, source_ids: List[str],
                        approved_by: str) -> Guide:
        previous_body = self.read_body(guide.slug)
        self._archive_current(guide, previous_body)
        revision_id = self._new_revision_id()
        revision_path = self.revision_dir / f"{guide.slug}.v{guide.version + 1}.{revision_id}.md"
        atomic_write_text(revision_path, body)
        revision = GuideRevision(
            id=revision_id, guide_slug=guide.slug, version=guide.version + 1,
            body_sha256=body_sha256(body), body_path=str(revision_path.relative_to(self.dir)),
            parent_revision_id=guide.revision_id, created_at=now_iso(),
            created_by=updated_by, approved_by=approved_by,
            change_summary=change_summary, source_ids=source_ids, status="prepared")
        self.revisions.put(revision)
        atomic_write_text(self._path(guide.slug), body)
        guide.updated_at = now_iso()
        guide.updated_by = updated_by
        guide.version += 1
        guide.body_sha256 = revision.body_sha256
        guide.revision_id = revision_id
        guide.review_status = "verified" if approved_by else "unverified"
        guide.change_summary = change_summary
        self.index.put(guide)
        revision.status = "published"
        self.revisions.put(revision)
        return guide

    def create_candidate(self, slug: str, body: str, created_by: str,
                         source_ids: Optional[List[str]] = None,
                         contribution_ids: Optional[List[str]] = None,
                         source_fingerprint: str = "",
                         validation_errors: Optional[List[str]] = None,
                         validation_warnings: Optional[List[str]] = None,
                         change_summary: str = "") -> GuideCandidate:
        with self._guide_lock(slug):
            guide = self._prepare_guide(slug)
            candidate_id = f"candidate-{uuid.uuid4().hex[:16]}"
            path = self._candidate_path(candidate_id)
            atomic_write_text(path, body)
            candidate = GuideCandidate(
                id=candidate_id, guide_slug=slug, base_version=guide.version,
                base_body_sha256=guide.body_sha256, body_path=str(path.relative_to(self.dir)),
                created_at=now_iso(), created_by=created_by, source_ids=source_ids or [],
                contribution_ids=contribution_ids or [],
                source_fingerprint=source_fingerprint,
                validation_errors=validation_errors or [],
                validation_warnings=validation_warnings or [], change_summary=change_summary)
            self.candidates.put(candidate)
            return candidate

    def get_candidate(self, candidate_id: str) -> Optional[GuideCandidate]:
        return self.candidates.get(candidate_id)

    def read_candidate(self, candidate_id: str) -> str:
        candidate = self.get_candidate(candidate_id)
        if not candidate:
            return ""
        return self._read_text(self.dir / candidate.body_path)

    def list_candidates(self, slug: str) -> List[GuideCandidate]:
        return sorted(self.candidates.find(lambda item: item.guide_slug == slug),
                      key=lambda item: item.created_at, reverse=True)

    def pending_candidates(self) -> List[GuideCandidate]:
        """Candidates that passed generation and still require human approval."""
        return sorted(self.candidates.find(lambda item: item.status == "ready"),
                      key=lambda item: item.created_at, reverse=True)

    def publish_candidate(self, candidate_id: str, approved_by: str,
                          current_source_fingerprint: str = "") -> Guide:
        initial = self.get_candidate(candidate_id)
        if not initial:
            raise ValueError("候选稿不存在")
        with self._guide_lock(initial.guide_slug):
            candidate = self.get_candidate(candidate_id)
            if not candidate:
                raise ValueError("候选稿不存在")
            guide = self._prepare_guide(candidate.guide_slug)
            if candidate.status != "ready":
                raise GuideValidationException("该候选稿已不能发布。")
            if candidate.validation_errors:
                raise GuideValidationException("候选稿未通过自动检查，不能发布。")
            if (candidate.source_fingerprint and current_source_fingerprint and
                    candidate.source_fingerprint != current_source_fingerprint):
                candidate.status = "stale"
                self.candidates.put(candidate)
                raise GuideConflictException("候选稿生成后来源已变化，请重新生成。")
            if (guide.version != candidate.base_version or
                    guide.body_sha256 != candidate.base_body_sha256):
                candidate.status = "stale"
                self.candidates.put(candidate)
                raise GuideConflictException("正式版或来源已更新，请重新生成候选稿。")
            published = self._publish_locked(
                guide, self._read_text(self.dir / candidate.body_path), "llm",
                candidate.change_summary, candidate.source_ids, approved_by=approved_by)
            candidate.status = "published"
            self.candidates.put(candidate)
            return published

    def discard_candidate(self, candidate_id: str) -> None:
        candidate = self.get_candidate(candidate_id)
        if candidate and candidate.status == "ready":
            candidate.status = "discarded"
            self.candidates.put(candidate)

    def update_candidate(self, candidate_id: str, body: str, validation_errors: List[str],
                         validation_warnings: List[str]) -> GuideCandidate:
        candidate = self.get_candidate(candidate_id)
        if not candidate:
            raise ValueError("候选稿不存在")
        with self._guide_lock(candidate.guide_slug):
            if candidate.status != "ready":
                raise GuideValidationException("只有待审核候选稿可以编辑。")
            atomic_write_text(self.dir / candidate.body_path, body)
            candidate.validation_errors = validation_errors
            candidate.validation_warnings = validation_warnings
            self.candidates.put(candidate)
            return candidate

    def restore_history(self, slug: str, history_name: str, actor: str) -> Guide:
        source = self.history_dir / Path(history_name).name
        if not source.exists():
            raise ValueError("历史版本不存在")
        return self.save_body(slug, self._read_text(source), actor,
                              change_summary=f"从历史版本 {source.name} 恢复")

    def list_history(self, slug: str) -> List[str]:
        return sorted((path.name for path in self.history_dir.glob(f"{slug}.*.md")), reverse=True)

    def list_revisions(self, slug: str) -> List[GuideRevision]:
        return sorted(self.revisions.find(lambda item: item.guide_slug == slug),
                      key=lambda item: (item.version, item.created_at), reverse=True)

    def recently_updated(self, limit: int = 20) -> List[Guide]:
        return sorted(self.index.all(), key=lambda guide: guide.updated_at, reverse=True)[:limit]
