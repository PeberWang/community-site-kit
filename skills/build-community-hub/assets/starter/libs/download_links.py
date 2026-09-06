"""Stable in-site download paths and one-time migration of legacy OSS links."""

import re
from typing import Iterable, List
from urllib.parse import quote, unquote, urlsplit


def attachment_download_path(key: str) -> str:
    """Keep permanent page links inside the app; never expose a storage URL."""
    return f"/downloads/objects/{quote(key, safe='/')}"


def known_public_bases(bucket: str, endpoint: str, public_base: str = "",
                       cdn_domain: str = "") -> List[str]:
    """Recognize legacy direct links after the bucket becomes private."""
    bases = [public_base.strip().rstrip("/")]
    host = urlsplit(endpoint).netloc or endpoint.removeprefix("https://").removeprefix("http://")
    if bucket and host:
        bases.append(f"https://{bucket}.{host}".rstrip("/"))
    if cdn_domain.strip():
        bases.append(f"https://{cdn_domain.strip().rstrip('/')}".rstrip("/"))
    return sorted({base for base in bases if base}, key=len, reverse=True)


def rewrite_legacy_download_urls(text: str, public_bases: Iterable[str]) -> str:
    """Replace only legacy OSS raw-object URLs, retaining their Markdown labels."""
    rewritten = text or ""
    for base in public_bases:
        pattern = re.compile(re.escape(base.rstrip("/")) + r"/(raw/[^\s<>\[\]\(\)\"']+)")

        def replace(match: re.Match) -> str:
            key = unquote(match.group(1).split("?", 1)[0].split("#", 1)[0])
            return attachment_download_path(key)

        rewritten = pattern.sub(replace, rewritten)
    return rewritten
