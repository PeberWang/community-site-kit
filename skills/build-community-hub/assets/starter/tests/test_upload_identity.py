import asyncio

import pytest

from config.schema import Attachment, Contribution
from config.settings import Settings
from libs.guide_sources import build_source_catalog, source_fingerprint
from services.upload_service import UploadService


def test_same_filename_gets_distinct_storage_keys(tmp_path):
    settings = Settings(
        db_dir=tmp_path / "db", guides_dir=tmp_path / "guides",
        uploads_dir=tmp_path / "uploads", cloud_stub_dir=tmp_path / "oss",
        cloud_drive_backend="local_stub")
    service = UploadService(settings)
    first = asyncio.run(service.save_attachment("notes.pdf", b"first", "politics"))
    second = asyncio.run(service.save_attachment("notes.pdf", b"second", "politics"))
    assert first[0] != second[0]
    assert first[3] != second[3]
    assert (settings.cloud_stub_dir / first[0]).read_bytes() == b"first"
    assert (settings.cloud_stub_dir / second[0]).read_bytes() == b"second"


def test_source_fingerprint_changes_when_evidence_changes():
    contribution = Contribution(
        id="contribution-1", contributor="user-1", course_slug="politics", text="先读讲义。",
        review_status="approved", attachments=[Attachment(
            id="upload-1", filename="notes.pdf", oss_key="raw/politics/upload-1.pdf",
            content_sha256="a" * 64)])
    first = build_source_catalog([contribution], [], lambda _: "同学")
    contribution.text = "先整理概念，再读讲义。"
    second = build_source_catalog([contribution], [], lambda _: "同学")
    assert source_fingerprint(first) != source_fingerprint(second)


def test_source_catalog_exposes_file_type_for_same_named_materials():
    contribution = Contribution(
        id="c1", contributor="u1", course_slug="demo", review_status="approved",
        text="**2025秋课程大纲与课件**",
        attachments=[
            Attachment(id="a1", filename="课程大纲.docx", oss_key="raw/demo/a.docx"),
            Attachment(id="a2", filename="课程课件.pptx", oss_key="raw/demo/b.pptx"),
        ],
    )

    cards = build_source_catalog([contribution], [], lambda _: "同学")

    assert [card["file_type"] for card in cards] == ["DOCX", "PPTX"]


def test_production_rejects_unsafe_session_configuration(tmp_path):
    with pytest.raises(ValueError, match="SESSION_COOKIE_SECURE"):
        Settings(
            environment="production", session_secret="a" * 32, session_cookie_secure=False,
            db_dir=tmp_path / "db", guides_dir=tmp_path / "guides")
    settings = Settings(
        environment="production", session_secret="a" * 32, session_cookie_secure=True,
        db_dir=tmp_path / "db", guides_dir=tmp_path / "guides")
    assert settings.session_cookie_secure is True
