# -*- coding: utf-8 -*-
"""Web dependencies - session auth, role guards, service singletons."""

from typing import Optional
from urllib.parse import quote

from fastapi import HTTPException, Request
from fastapi.responses import RedirectResponse
from itsdangerous import BadSignature, URLSafeTimedSerializer

from config.schema import User
from config.settings import Settings, settings as app_settings
from services.announce_service import AnnounceService
from services.article_service import ArticleService
from services.contribution_service import ContributionService
from services.event_service import EventService
from services.feedback_service import FeedbackService
from services.format_service import FormatService
from services.guide_service import GuideService
from services.guide_queue_service import GuideQueueService
from services.plaza_service import PlazaService
from services.tag_service import TagService
from services.upload_service import UploadService
from services.user_service import UserService
from glue.guide_compilation import GuideCompilation
from glue.download_gateway import DownloadGateway
from glue.guide_lifecycle import GuideLifecycle

SESSION_COOKIE = "community_site_session"

_serializer: Optional[URLSafeTimedSerializer] = None
_services: dict = {}


def get_settings() -> Settings:
    return app_settings


def serializer() -> URLSafeTimedSerializer:
    global _serializer
    if _serializer is None:
        _serializer = URLSafeTimedSerializer(app_settings.session_secret, salt="community-site-session")
    return _serializer


def svc(name: str):
    """Lazily-built service singletons (services hold no per-request state)."""
    if name not in _services:
        cls = {
            "users": UserService, "tags": TagService,
            "announcements": AnnounceService,
            "contributions": ContributionService, "articles": ArticleService,
            "events": EventService, "plaza": PlazaService,
            "feedback": FeedbackService, "guides": GuideService,
            "guide_queue": GuideQueueService,
            "uploads": UploadService, "format": FormatService,
            "compilation": GuideCompilation,
            "download_gateway": DownloadGateway,
            "guide_lifecycle": GuideLifecycle,
        }[name]
        _services[name] = cls(app_settings)
    return _services[name]


# ---- auth ----

def current_user(request: Request) -> Optional[User]:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    try:
        user_id = serializer().loads(token, max_age=app_settings.session_max_age)
    except BadSignature:
        return None
    return svc("users").get_by_id(user_id)


def require_user(request: Request) -> User:
    user = current_user(request)
    if not user:
        destination = request.url.path
        if request.url.query:
            destination = f"{destination}?{request.url.query}"
        raise HTTPException(status_code=303,
                            headers={"Location": f"/login?next={quote(destination, safe='/')}"})
    return user


def require_admin(request: Request) -> User:
    user = require_user(request)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user


def require_writer(request: Request) -> User:
    """admin + user can write (submit/post/comment); observer is read-only."""
    user = require_user(request)
    if user.role == "observer":
        raise HTTPException(status_code=403, detail="观察员账号为只读")
    return user


def login_response(response: RedirectResponse, user_id: str) -> RedirectResponse:
    response.set_cookie(
        SESSION_COOKIE, serializer().dumps(user_id), httponly=True, samesite="lax",
        secure=app_settings.session_cookie_secure, max_age=app_settings.session_max_age,
    )
    return response
