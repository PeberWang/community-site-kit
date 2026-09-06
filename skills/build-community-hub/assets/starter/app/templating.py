# -*- coding: utf-8 -*-
"""Shared Jinja2 templates instance."""

import hashlib
from pathlib import Path

from fastapi.templating import Jinja2Templates

from config.settings import settings
from libs.community_config import load_community

templates = Jinja2Templates(directory=Path(__file__).resolve().parent / "templates")

_STATIC_DIR = Path(__file__).resolve().parent / "static"
_static_cache = {"mtime": None, "hash": None}


def display_name(user_id: str) -> str:
    """Jinja global: resolve user id -> current display name (lazy to avoid circular import)."""
    from app.deps import svc
    return svc("users").display_name(user_id)


def static_version() -> str:
    """Jinja global: style.css 内容哈希前 8 位，改动即变，浏览器缓存自动失效。

    以文件 mtime 作缓存键：mtime 未变直接复用已算哈希（每次请求零重算）。
    """
    css = _STATIC_DIR / "style.css"
    mtime = css.stat().st_mtime
    if _static_cache["mtime"] != mtime:
        _static_cache["hash"] = hashlib.md5(css.read_bytes()).hexdigest()[:8]
        _static_cache["mtime"] = mtime
    return _static_cache["hash"]


templates.env.globals["display_name"] = display_name
templates.env.globals["static_version"] = static_version
templates.env.globals["community"] = load_community(str(settings.community_config))
