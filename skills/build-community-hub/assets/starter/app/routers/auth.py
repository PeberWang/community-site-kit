# -*- coding: utf-8 -*-
"""Auth router - invite-code registration, login, logout."""

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from urllib.parse import urlsplit

from app.deps import login_response, svc
from app.templating import templates

router = APIRouter()


def safe_next(next_url: str) -> str:
    """Permit only an in-site relative redirect after login."""
    parsed = urlsplit(next_url or "")
    if (next_url.startswith("/") and not next_url.startswith("//") and "\\" not in next_url
            and not parsed.scheme and not parsed.netloc):
        return next_url
    return "/"


@router.get("/login")
def login_page(request: Request, next: str = ""):
    if request.state.user:
        return RedirectResponse(safe_next(next), status_code=303)
    return templates.TemplateResponse(request, "auth/login.html", {
        "request": request, "error": "", "next_url": safe_next(next)})


@router.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...),
          next_url: str = Form("")):
    user = svc("users").authenticate(username, password)
    if not user:
        return templates.TemplateResponse(request, "auth/login.html", {
            "request": request, "error": "用户名或密码错误",
            "next_url": safe_next(next_url)})
    return login_response(RedirectResponse(safe_next(next_url), status_code=303), user.id)


@router.get("/register")
def register_page(request: Request):
    if request.state.user:
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(request, "auth/register.html", {"request": request, "error": ""})


@router.post("/register")
def register(request: Request, username: str = Form(...), password: str = Form(...),
             display_name: str = Form(""), invite_code: str = Form(...)):
    try:
        user = svc("users").register(username, password, display_name, invite_code)
    except ValueError as e:
        return templates.TemplateResponse(request, "auth/register.html", {
            "request": request, "error": str(e)})
    return login_response(RedirectResponse("/", status_code=303), user.id)


@router.get("/logout")
def logout():
    resp = RedirectResponse("/login", status_code=303)
    resp.delete_cookie("community_site_session")
    return resp
