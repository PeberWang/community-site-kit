# -*- coding: utf-8 -*-
"""Events router - 活动栏: upcoming/ongoing/past + reviewed submission."""

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from app.deps import require_user, require_writer, svc
from app.templating import templates

router = APIRouter(prefix="/events")


@router.get("")
def list_events(request: Request):
    require_user(request)
    events = svc("events")
    return templates.TemplateResponse(request, "events/list.html", {
        "request": request,
        "upcoming": events.upcoming(),
        "ongoing": events.ongoing(),
        "past": events.past(),
    })


@router.get("/submit")
def submit_page(request: Request):
    require_writer(request)
    return templates.TemplateResponse(request, "events/submit.html",
                                      {"request": request, "error": ""})


@router.post("/submit")
def submit(request: Request, title: str = Form(...), mode: str = Form(...),
           start_time: str = Form(...), end_time: str = Form(...),
           place: str = Form(...), reason: str = Form(...),
           description: str = Form("")):
    user = require_writer(request)
    try:
        svc("events").submit(user.id, title, mode,
                             start_time, place, reason,
                             end_time=end_time, description=description)
    except ValueError as e:
        return templates.TemplateResponse(request, "events/submit.html",
                                          {"request": request, "error": str(e)})
    return RedirectResponse("/events?submitted=1", status_code=303)
