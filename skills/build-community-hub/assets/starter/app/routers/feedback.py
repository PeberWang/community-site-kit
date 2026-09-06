# -*- coding: utf-8 -*-
"""Feedback router - likes & comments on guides/articles."""

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from app.deps import require_writer, svc

router = APIRouter(prefix="/feedback")


@router.post("/like")
def like(request: Request, target: str = Form(...), back: str = Form("/")):
    user = require_writer(request)
    svc("feedback").toggle_like(target, user.id)
    return RedirectResponse(back, status_code=303)


@router.post("/comment")
def comment(request: Request, target: str = Form(...),
            body: str = Form(...), back: str = Form("/")):
    user = require_writer(request)
    try:
        svc("feedback").comment(target, user.id, body)
    except ValueError:
        pass
    return RedirectResponse(back, status_code=303)
