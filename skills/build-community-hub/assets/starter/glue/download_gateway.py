"""Authenticated attachment gateway: stable app path -> fresh OSS URL."""

from urllib.parse import quote

from config.settings import Settings
from libs.cloud import get_drive
from libs.download_links import known_public_bases
from libs.exceptions import FileDownloadException
from services.article_service import ArticleService
from services.contribution_service import ContributionService


class DownloadGateway:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.contributions = ContributionService(settings)
        self.articles = ArticleService(settings)

    async def attachment_url(self, oss_key: str) -> str:
        approved_key = self.contributions.approved_attachment_key(oss_key)
        if not approved_key and not self._is_legacy_public_reference(oss_key):
            raise FileDownloadException("资料不存在、尚未通过审核或不能下载")
        return await get_drive(self.settings).download_url(approved_key or oss_key)

    def _is_legacy_public_reference(self, oss_key: str) -> bool:
        """Keep already-published guides/articles readable during metadata repair."""
        if not oss_key.startswith("raw/"):
            return False
        bases = known_public_bases(self.settings.oss_bucket, self.settings.oss_endpoint,
                                   self.settings.oss_public_base or "",
                                   self.settings.oss_cdn_domain)
        urls = [f"{base}/{oss_key}" for base in bases]
        urls.extend(f"{base}/{quote(oss_key, safe='/')}" for base in bases)
        if any(url in article.body for article in self.articles.published() for url in urls):
            return True
        for path in self.settings.guides_dir.glob("*.md"):
            with open(path, "r", encoding="utf-8", newline="\n") as source:
                body = source.read()
            if any(url in body for url in urls):
                return True
        return False
