# -*- coding: utf-8 -*-
"""Knowledge Common Kit web app - FastAPI + Jinja2 SSR entry."""

from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.deps import current_user, get_settings
from app.templating import templates
from app.routers import admin, articles, auth, contribute, downloads, events, feedback, guides, home, plaza
from libs.community_config import load_community

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title=get_settings().site_name, docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


@app.middleware("http")
async def inject_user(request: Request, call_next):
    request.state.user = current_user(request)
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        origin = request.headers.get("origin")
        if origin:
            forwarded = request.headers.get("x-forwarded-host")
            expected_host = forwarded or request.headers.get("host", "")
            if urlsplit(origin).netloc != expected_host:
                return HTMLResponse("invalid request origin", status_code=403)
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    return response


@app.get("/health/live", include_in_schema=False)
def health_live():
    return {"status": "ok"}


@app.get("/health/ready", include_in_schema=False)
def health_ready():
    required = (get_settings().db_dir, get_settings().guides_dir)
    if not all(path.exists() and path.is_dir() for path in required):
        return HTMLResponse("not ready", status_code=503)
    return {"status": "ready"}



# ---- dev-time cloud-stub file serving (OSS replaced in production) ----

@app.get("/files/{path:path}")
def serve_file(path: str, request: Request):
    settings = get_settings()
    if not request.state.user:
        return RedirectResponse("/login", status_code=303)
    root = settings.cloud_stub_dir.resolve()
    target = (root / path).resolve()
    if not str(target).startswith(str(root)) or not target.exists():
        return HTMLResponse("not found", status_code=404)
    return FileResponse(target)


community = load_community(str(get_settings().community_config))
app.include_router(auth.router)
app.include_router(home.router)
app.include_router(admin.router)
if community.features.guides:
    app.include_router(guides.router)
    app.include_router(downloads.router)
if community.features.articles:
    app.include_router(articles.router)
if community.features.events:
    app.include_router(events.router)
if community.features.plaza:
    app.include_router(plaza.router)
if community.features.contributions:
    app.include_router(contribute.router)
if community.features.feedback:
    app.include_router(feedback.router)


@app.exception_handler(403)
async def forbidden(request: Request, exc):
    return templates.TemplateResponse(request, "error.html", {
        "request": request, "code": 403,
        "message": getattr(exc, "detail", "没有权限"),
    }, status_code=403)


def run():
    import uvicorn
    settings = get_settings()
    uvicorn.run("app.main:app", host=settings.web_host,
                port=settings.web_port, reload=False)


if __name__ == "__main__":
    run()
