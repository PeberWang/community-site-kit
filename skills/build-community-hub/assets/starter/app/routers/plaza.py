# -*- coding: utf-8 -*-
"""Plaza router - 广场: free posting (no pre-review), observers read-only."""

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from app.deps import require_user, require_writer, svc
from app.templating import templates

router = APIRouter(prefix="/plaza")


@router.get("")
def index(request: Request):
    require_user(request)
    return templates.TemplateResponse(request, "plaza/index.html", {
        "request": request, "threads": svc("plaza").list_threads()})


@router.post("/post")
def post(request: Request, title: str = Form(...), body: str = Form(...)):
    user = require_writer(request)
    try:
        t = svc("plaza").post(user.id, title, body)
    except ValueError:
        return RedirectResponse("/plaza", status_code=303)
    return RedirectResponse(f"/plaza/{t.id}", status_code=303)


@router.get("/{tid}")
def thread(request: Request, tid: str):
    require_user(request)
    t = svc("plaza").get(tid)
    if not t or t.deleted:
        return RedirectResponse("/plaza", status_code=303)
    return templates.TemplateResponse(request, "plaza/thread.html",
                                      {"request": request, "thread": t})


@router.post("/{tid}/reply")
def reply(request: Request, tid: str, body: str = Form(...)):
    user = require_writer(request)
    try:
        svc("plaza").reply(tid, user.id, body)
    except ValueError:
        pass
    return RedirectResponse(f"/plaza/{tid}", status_code=303)


@router.post("/{tid}/delete-own")
def delete_own(request: Request, tid: str):
    user = require_writer(request)
    svc("plaza").delete_own_thread(tid, user.id)
    return RedirectResponse("/plaza", status_code=303)


@router.get("/{tid}/fragment")
def thread_fragment(request: Request, tid: str):
    """Thread content partial for the plaza modal (no page navigation)."""
    require_user(request)
    t = svc("plaza").get(tid)
    if not t or t.deleted:
        return RedirectResponse("/plaza", status_code=303)
    return templates.TemplateResponse(request, "plaza/_thread_fragment.html",
                                      {"thread": t})
