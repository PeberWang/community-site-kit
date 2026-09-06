# -*- coding: utf-8 -*-
"""Upload service - attachment/article-body storage: local uploads dir + cloud (OSS/stub).

Pointers in JSON keep only oss_key + public url; heavy bytes live in OSS (or stub dir in dev).
"""

import hashlib
import uuid
from pathlib import Path
from typing import Tuple

from config.settings import Settings
from libs.cloud import get_drive
from libs.storage_keys import raw_key, article_key

ALLOWED_EXT = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".md", ".txt", ".zip", ".png", ".jpg", ".jpeg", ".epub",
}


class UploadService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.max_bytes = settings.max_upload_mb * 1024 * 1024
        self.uploads_dir = Path(settings.uploads_dir)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)

    def _validate(self, filename: str, size: int,
                  enforce_limit: bool = True) -> None:
        ext = Path(filename).suffix.lower()
        if ext not in ALLOWED_EXT:
            raise ValueError(f"不支持的文件类型: {ext}")
        if enforce_limit and size > self.max_bytes:
            raise ValueError(f"文件超过 {self.settings.max_upload_mb}MB 上限")

    async def save_attachment(self, filename: str, data: bytes,
                              tag: str, enforce_limit: bool = True
                              ) -> Tuple[str, str, int, str, str]:
        """Save an attachment and return key, URL, size, immutable ID and digest.

        enforce_limit=False only for trusted bulk imports (e.g. wiki export);
        web uploads always keep the 100MB cap.
        """
        self._validate(filename, len(data), enforce_limit=enforce_limit)
        attachment_id = uuid.uuid4().hex
        content_sha256 = hashlib.sha256(data).hexdigest()
        key = raw_key(tag, filename, attachment_id, content_sha256)
        local = self.uploads_dir / key
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_bytes(data)
        drive = get_drive(self.settings)
        await drive.upload(str(local), key)
        url = await drive.download_url(key)
        return key, url, len(data), attachment_id, content_sha256

    async def save_text(self, text: str, slug: str) -> Tuple[str, str]:
        """Save article body markdown -> cloud; returns (oss_key, url)."""
        local = self.uploads_dir / article_key(slug)
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_text(text, encoding="utf-8")
        drive = get_drive(self.settings)
        key = article_key(slug)
        await drive.upload(str(local), key)
        url = await drive.download_url(key)
        return key, url

    async def upload_markdown(self, text: str, key: str) -> str:
        """Upload arbitrary markdown content under an explicit key; returns url."""
        local = self.uploads_dir / key
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_text(text, encoding="utf-8")
        drive = get_drive(self.settings)
        await drive.upload(str(local), key)
        return await drive.download_url(key)
