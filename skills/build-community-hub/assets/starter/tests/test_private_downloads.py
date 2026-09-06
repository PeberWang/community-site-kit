# -*- coding: utf-8 -*-

import asyncio

import pytest
from fastapi.testclient import TestClient

import app.deps as deps
from app.main import app
from app.routers.auth import safe_next
from config.schema import Attachment, Contribution
from config.settings import Settings
from glue.download_gateway import DownloadGateway
from libs.download_links import known_public_bases, rewrite_legacy_download_urls
from libs.exceptions import FileDownloadException
from libs.markdown_lib import render_guide_markdown, render_inline_markdown
from services.contribution_service import ContributionService


def download_settings(tmp_path):
    return Settings(
        project_root=tmp_path,
        db_dir=tmp_path / "db",
        guides_dir=tmp_path / "guides",
        uploads_dir=tmp_path / "uploads",
        summary_dir=tmp_path / "summaries",
        cloud_stub_dir=tmp_path / "oss",
        cloud_drive_backend="local_stub",
    )


def test_legacy_oss_markdown_link_becomes_a_stable_in_site_download_link():
    bases = known_public_bases("example-private-bucket", "https://oss-region.example.com")
    text = "请看[课程大纲](https://example-private-bucket.oss-region.example.com/raw/demo/课程大纲.pdf)。"

    rewritten = rewrite_legacy_download_urls(text, bases)

    assert "oss-cn-beijing" not in rewritten
    assert "/downloads/objects/raw/demo/%E8%AF%BE%E7%A8%8B%E5%A4%A7%E7%BA%B2.pdf" in rewritten
    assert "课程大纲" in render_guide_markdown(text, bases)


def test_inline_markdown_renders_source_emphasis_without_raw_asterisks():
    rendered = render_inline_markdown("**2025秋课程大纲与课件**")

    assert rendered == "<strong>2025秋课程大纲与课件</strong>"
    assert "**" not in rendered


def test_download_gateway_issues_a_link_only_for_an_approved_attachment(tmp_path):
    settings = download_settings(tmp_path)
    key = "raw/demo/attachment.pdf"
    contribution = Contribution(
        id="contribution-one", contributor="user-one", course_slug="demo",
        review_status="approved", attachments=[Attachment(id="attachment-one", oss_key=key)])
    ContributionService(settings).store.put(contribution)

    url = asyncio.run(DownloadGateway(settings).attachment_url(key))

    assert url == f"/files/{key}"


def test_pending_or_unknown_attachment_cannot_receive_a_download_url(tmp_path):
    settings = download_settings(tmp_path)
    key = "raw/demo/pending.pdf"
    contribution = Contribution(
        id="contribution-two", contributor="user-one", course_slug="demo",
        review_status="pending", attachments=[Attachment(id="attachment-two", oss_key=key)])
    ContributionService(settings).store.put(contribution)

    with pytest.raises(FileDownloadException):
        asyncio.run(DownloadGateway(settings).attachment_url(key))


def test_legacy_link_in_a_published_guide_remains_downloadable_after_acl_change(tmp_path):
    settings = download_settings(tmp_path)
    settings.oss_bucket = "example-private-bucket"
    settings.oss_endpoint = "https://oss-region.example.com"
    key = "raw/demo/legacy.pdf"
    settings.guides_dir.mkdir(parents=True, exist_ok=True)
    (settings.guides_dir / "course-demo.md").write_text(
        f"[旧资料](https://example-private-bucket.oss-region.example.com/{key})",
        encoding="utf-8", newline="\n")

    url = asyncio.run(DownloadGateway(settings).attachment_url(key))

    assert url == f"/files/{key}"


def test_login_return_path_stays_on_this_site():
    assert safe_next("/downloads/objects/raw/demo/file.pdf") == "/downloads/objects/raw/demo/file.pdf"
    assert safe_next("https://attacker.example/") == "/"
    assert safe_next("//attacker.example/") == "/"
    assert safe_next("/\\attacker.example/") == "/"


def test_unsigned_download_request_returns_to_the_same_file_after_login(tmp_path, monkeypatch):
    settings = download_settings(tmp_path)
    monkeypatch.setattr(deps, "app_settings", settings)
    deps._serializer = None
    deps._services.clear()
    try:
        response = TestClient(app).get("/downloads/objects/raw/demo/file.pdf",
                                       follow_redirects=False)
    finally:
        deps._serializer = None
        deps._services.clear()

    assert response.status_code == 303
    assert response.headers["location"] == "/login?next=/downloads/objects/raw/demo/file.pdf"
