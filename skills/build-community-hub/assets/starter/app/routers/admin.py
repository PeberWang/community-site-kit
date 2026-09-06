# -*- coding: utf-8 -*-
"""Admin router - review queues, guide candidates and account moderation."""

from urllib.parse import quote

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from app.deps import require_admin, svc
from app.templating import templates
from config.schema import COURSE_TYPES, EXAM_TYPES
from libs.exceptions import GuideConflictException, GuideValidationException
from libs.guide_diff import build_unified_diff

router = APIRouter(prefix="/admin")
ACCOUNT_PREVIEW_LIMIT = 5
ACCOUNT_SEARCH_LIMIT = 50
CONTENT_PREVIEW_LIMIT = 5
CONTENT_SEARCH_LIMIT = 50


@router.get("")
def dashboard(request: Request):
    require_admin(request)
    guides = svc("guides")
    candidate_reviews = [
        {"candidate": candidate, "guide": guides.get(candidate.guide_slug)}
        for candidate in guides.pending_candidates()
    ]
    return templates.TemplateResponse(request, "admin/dashboard.html", {
        "request": request,
        "pending_contributions": svc("contributions").pending(),
        "pending_articles": svc("articles").pending(),
        "candidate_reviews": [item for item in candidate_reviews if item["guide"]],
        "tags": svc("tags"),
    })


# ---- announcements (公告: 首页置顶, 下线前不过期) ----

@router.get("/announcements")
def announcements_page(request: Request, query: str = ""):
    require_admin(request)
    query = query.strip()
    records = svc("announcements").search_managed(query)
    is_searching = bool(query)
    return templates.TemplateResponse(request, "admin/announcements.html", {
        "request": request,
        "announcements": records[:CONTENT_SEARCH_LIMIT] if is_searching
        else records[:CONTENT_PREVIEW_LIMIT],
        "announcement_total": len(records),
        "announcement_limited": is_searching and len(records) > CONTENT_SEARCH_LIMIT,
        "announcement_query": query,
    })


@router.post("/announcements")
def publish_announcement(request: Request, title: str = Form(...),
                         body: str = Form(...)):
    admin = require_admin(request)
    try:
        svc("announcements").publish(title, body, created_by=admin.id)
    except ValueError:
        pass
    return RedirectResponse("/admin/announcements", status_code=303)


@router.post("/announcements/{aid}/delete")
def delete_announcement(request: Request, aid: str):
    admin = require_admin(request)
    svc("announcements").withdraw(aid, admin.id)
    return RedirectResponse("/admin/announcements", status_code=303)


@router.post("/announcements/{aid}/edit")
def edit_announcement(request: Request, aid: str,
                      title: str = Form(...), body: str = Form(...)):
    admin = require_admin(request)
    try:
        svc("announcements").update(aid, title, body, admin.id)
    except ValueError:
        pass
    return RedirectResponse("/admin/announcements", status_code=303)


@router.post("/announcements/{aid}/restore")
def restore_announcement(request: Request, aid: str):
    admin = require_admin(request)
    svc("announcements").restore(aid, admin.id)
    return RedirectResponse("/admin/announcements", status_code=303)


# ---- contribution review ----

@router.post("/contributions/{cid}/review")
def review_contribution(request: Request, cid: str, action: str = Form(...),
                        tag_choice: str = Form("")):
    admin = require_admin(request)
    course_slug = topic_slug = ""
    if tag_choice.startswith("course:"):
        course_slug = tag_choice.split(":", 1)[1]
    elif tag_choice.startswith("topic:"):
        topic_slug = tag_choice.split(":", 1)[1]
    contribution = svc("contributions").review(
        cid, approve=(action == "approve"), reviewer=admin.id,
        course_slug=course_slug, topic_slug=topic_slug)
    if action == "approve":
        svc("guide_lifecycle").queue_contribution(contribution)
    return RedirectResponse("/admin", status_code=303)


# ---- article review ----

@router.post("/articles/{aid}/review")
def review_article(request: Request, aid: str, action: str = Form(...)):
    admin = require_admin(request)
    svc("articles").review(aid, approve=(action == "approve"),
                           reviewer=admin.id)
    return RedirectResponse("/admin", status_code=303)


@router.get("/articles")
def articles_page(request: Request, query: str = ""):
    require_admin(request)
    query = query.strip()
    records = svc("articles").search_managed(query)
    is_searching = bool(query)
    return templates.TemplateResponse(request, "admin/articles.html", {
        "request": request,
        "articles": records[:CONTENT_SEARCH_LIMIT] if is_searching
        else records[:CONTENT_PREVIEW_LIMIT],
        "article_total": len(records),
        "article_limited": is_searching and len(records) > CONTENT_SEARCH_LIMIT,
        "article_query": query,
    })


@router.get("/articles/{aid}/edit")
def edit_article_page(request: Request, aid: str):
    require_admin(request)
    article = svc("articles").get(aid)
    if not article or article.review_status != "approved":
        return RedirectResponse("/admin/articles", status_code=303)
    return templates.TemplateResponse(request, "admin/edit_article.html", {
        "request": request, "article": article,
        "tags": svc("tags"), "error": request.query_params.get("error", "")})


@router.post("/articles/{aid}/edit")
async def edit_article(request: Request, aid: str, title: str = Form(...),
                       body: str = Form(...)):
    admin = require_admin(request)
    article = svc("articles").get(aid)
    if not article or article.review_status != "approved":
        return RedirectResponse("/admin/articles", status_code=303)
    try:
        key, _url = await svc("uploads").save_text(body, article.slug)
        svc("articles").update_published(aid, title, body, admin.id)
        svc("articles").update_body(aid, body, body_oss_key=key)
    except ValueError as error:
        return RedirectResponse(f"/admin/articles/{aid}/edit?error={quote(str(error))}",
                                status_code=303)
    return RedirectResponse("/admin/articles", status_code=303)


@router.post("/articles/{aid}/withdraw")
def withdraw_article(request: Request, aid: str):
    admin = require_admin(request)
    svc("articles").withdraw(aid, admin.id)
    return RedirectResponse("/admin/articles", status_code=303)


@router.post("/articles/{aid}/restore")
def restore_article(request: Request, aid: str):
    admin = require_admin(request)
    svc("articles").restore(aid, admin.id)
    return RedirectResponse("/admin/articles", status_code=303)


# ---- event review + direct publish ----

@router.get("/events")
def events_page(request: Request):
    require_admin(request)
    return templates.TemplateResponse(request, "admin/events.html", {
        "request": request,
        "pending_events": svc("events").pending(),
        "managed_events": svc("events").managed(),
    })


@router.post("/events/{eid}/review")
def review_event(request: Request, eid: str, action: str = Form(...)):
    admin = require_admin(request)
    svc("events").review(eid, approve=(action == "approve"),
                         reviewer=admin.id)
    return RedirectResponse("/admin/events", status_code=303)


@router.get("/events/{eid}/edit")
def edit_event_page(request: Request, eid: str):
    require_admin(request)
    event = svc("events").get(eid)
    if not event or event.review_status != "approved":
        return RedirectResponse("/admin/events", status_code=303)
    return templates.TemplateResponse(request, "admin/edit_event.html", {
        "request": request, "event": event, "error": request.query_params.get("error", "")})


@router.post("/events/{eid}/edit")
def edit_event(request: Request, eid: str, title: str = Form(...), mode: str = Form(...),
               start_time: str = Form(...), end_time: str = Form(...),
               place: str = Form(...), reason: str = Form(...),
               description: str = Form("")):
    admin = require_admin(request)
    try:
        svc("events").update_published(eid, title, mode, start_time, end_time,
                                        place, reason, description, admin.id)
    except ValueError as error:
        return RedirectResponse(f"/admin/events/{eid}/edit?error={quote(str(error))}",
                                status_code=303)
    return RedirectResponse("/admin/events", status_code=303)


@router.post("/events/{eid}/withdraw")
def withdraw_event(request: Request, eid: str):
    admin = require_admin(request)
    svc("events").withdraw(eid, admin.id)
    return RedirectResponse("/admin/events", status_code=303)


@router.post("/events/{eid}/restore")
def restore_event(request: Request, eid: str):
    admin = require_admin(request)
    svc("events").restore(eid, admin.id)
    return RedirectResponse("/admin/events", status_code=303)


@router.post("/events/publish")
def publish_event(request: Request, title: str = Form(...), mode: str = Form(...),
                  start_time: str = Form(...), end_time: str = Form(...),
                  place: str = Form(...), reason: str = Form(...),
                  description: str = Form("")):
    admin = require_admin(request)
    try:
        e = svc("events").submit(admin.id, title, mode,
                                 start_time, place, reason,
                                 end_time=end_time, description=description)
        svc("events").review(e.id, approve=True, reviewer=admin.id)
    except ValueError:
        pass
    return RedirectResponse("/admin/events", status_code=303)


# ---- guide editing (human will is supreme) + LLM evolution ----

@router.get("/guides/{slug}/edit")
def edit_guide(request: Request, slug: str):
    require_admin(request)
    guides = svc("guides")
    guide = guides.get(slug)
    if not guide:
        return RedirectResponse("/guides", status_code=303)
    course = (svc("tags").get_course(guide.ref_slug)
              if guide.kind == "course" else None)
    return templates.TemplateResponse(request, "admin/edit_guide.html", {
        "request": request, "guide": guide,
        "body": guides.read_body(slug),
        "history": guides.list_history(slug),
        "candidates": guides.list_candidates(slug),
        "revisions": guides.list_revisions(slug),
        "compile_jobs": svc("guide_queue").list_for(slug),
        "course": course,
        "exam_types": EXAM_TYPES,
        "course_types": COURSE_TYPES,
        "error": request.query_params.get("error", ""),
    })


@router.post("/courses/{slug}/meta")
def save_course_meta(request: Request, slug: str, teacher: str = Form(""),
                     exam: str = Form(...), course_type: str = Form(...),
                     back: str = Form("/admin")):
    require_admin(request)
    try:
        svc("tags").update_course_meta(slug, teacher, exam, course_type)
    except ValueError:
        pass
    return RedirectResponse(back, status_code=303)


@router.post("/guides/{slug}/edit")
def save_guide(request: Request, slug: str, body: str = Form(...),
               base_body_sha256: str = Form(""), change_summary: str = Form("")):
    admin = require_admin(request)
    try:
        svc("guides").save_body(slug, body, updated_by=admin.id,
                                expected_body_sha256=base_body_sha256,
                                change_summary=change_summary.strip())
    except GuideConflictException as error:
        return RedirectResponse(f"/admin/guides/{slug}/edit?error={quote(str(error))}", status_code=303)
    guide = svc("guides").get(slug)
    return RedirectResponse(f"/guides/{guide.kind}/{guide.ref_slug}", status_code=303)


@router.post("/guides/{slug}/evolve")
async def evolve_guide(request: Request, slug: str):
    admin = require_admin(request)
    try:
        candidate = await svc("guide_lifecycle").generate_candidate(slug, actor=admin.id)
    except (ValueError, GuideValidationException) as error:
        return RedirectResponse(f"/admin/guides/{slug}/edit?error={quote(str(error))}", status_code=303)
    return RedirectResponse(f"/admin/guides/{slug}/candidates/{candidate.id}", status_code=303)


@router.get("/guides/{slug}/candidates/{candidate_id}")
def review_candidate(request: Request, slug: str, candidate_id: str):
    require_admin(request)
    guides = svc("guides")
    guide = guides.get(slug)
    candidate = guides.get_candidate(candidate_id)
    if not guide or not candidate or candidate.guide_slug != slug:
        return RedirectResponse(f"/admin/guides/{slug}/edit", status_code=303)
    body = guides.read_candidate(candidate_id)
    return templates.TemplateResponse(request, "admin/guide_candidate.html", {
        "request": request, "guide": guide, "candidate": candidate,
        "body": body, "diff_rows": build_unified_diff(guides.read_body(slug), body),
        "error": request.query_params.get("error", ""),
    })


@router.post("/guides/{slug}/candidates/{candidate_id}/edit")
def update_candidate(request: Request, slug: str, candidate_id: str, body: str = Form(...)):
    require_admin(request)
    candidate = svc("guides").get_candidate(candidate_id)
    if not candidate or candidate.guide_slug != slug:
        return RedirectResponse(f"/admin/guides/{slug}/edit", status_code=303)
    try:
        svc("compilation").update_candidate(candidate_id, body)
    except (ValueError, GuideValidationException) as error:
        return RedirectResponse(
            f"/admin/guides/{slug}/candidates/{candidate_id}?error={quote(str(error))}", status_code=303)
    return RedirectResponse(f"/admin/guides/{slug}/candidates/{candidate_id}", status_code=303)


@router.post("/guides/{slug}/candidates/{candidate_id}/publish")
def publish_candidate(request: Request, slug: str, candidate_id: str):
    admin = require_admin(request)
    candidate = svc("guides").get_candidate(candidate_id)
    if not candidate or candidate.guide_slug != slug:
        return RedirectResponse(f"/admin/guides/{slug}/edit", status_code=303)
    try:
        guide = svc("guide_lifecycle").publish_candidate(candidate_id, admin.id)
    except (ValueError, GuideConflictException, GuideValidationException) as error:
        return RedirectResponse(
            f"/admin/guides/{slug}/candidates/{candidate_id}?error={quote(str(error))}", status_code=303)
    return RedirectResponse(f"/guides/{guide.kind}/{guide.ref_slug}", status_code=303)


@router.post("/guides/{slug}/candidates/{candidate_id}/discard")
def discard_candidate(request: Request, slug: str, candidate_id: str):
    require_admin(request)
    candidate = svc("guides").get_candidate(candidate_id)
    if candidate and candidate.guide_slug == slug:
        svc("guide_lifecycle").discard_candidate(candidate_id)
    return RedirectResponse(f"/admin/guides/{slug}/edit", status_code=303)


@router.post("/guides/{slug}/history/{history_name}/restore")
def restore_history(request: Request, slug: str, history_name: str):
    admin = require_admin(request)
    try:
        guide = svc("guides").restore_history(slug, history_name, admin.id)
    except ValueError as error:
        return RedirectResponse(f"/admin/guides/{slug}/edit?error={quote(str(error))}", status_code=303)
    return RedirectResponse(f"/guides/{guide.kind}/{guide.ref_slug}", status_code=303)


# ---- plaza moderation ----

@router.get("/plaza")
def plaza_moderation(request: Request):
    require_admin(request)
    return templates.TemplateResponse(request, "admin/plaza.html", {
        "request": request,
        "threads": svc("plaza").list_threads(include_deleted=True)})


@router.post("/plaza/{tid}/edit")
def plaza_edit(request: Request, tid: str, title: str = Form(...),
               body: str = Form(...)):
    require_admin(request)
    svc("plaza").edit_thread(tid, title, body)
    return RedirectResponse("/admin/plaza", status_code=303)


@router.post("/plaza/{tid}/delete")
def plaza_delete(request: Request, tid: str):
    require_admin(request)
    svc("plaza").delete_thread(tid)
    return RedirectResponse("/admin/plaza", status_code=303)


@router.post("/plaza/{tid}/replies/{rid}/delete")
def plaza_delete_reply(request: Request, tid: str, rid: str):
    require_admin(request)
    svc("plaza").delete_reply(tid, rid)
    return RedirectResponse("/admin/plaza", status_code=303)


# ---- invites & users ----

def accounts_location(invite_query: str = "", user_query: str = "") -> str:
    parameters = []
    if invite_query.strip():
        parameters.append(f"invite_query={quote(invite_query.strip(), safe='')}")
    if user_query.strip():
        parameters.append(f"user_query={quote(user_query.strip(), safe='')}")
    return "/admin/accounts" + (f"?{'&'.join(parameters)}" if parameters else "")


@router.get("/accounts")
def accounts(request: Request, invite_query: str = "", user_query: str = ""):
    require_admin(request)
    user_service = svc("users")
    matching_invites = user_service.search_invites(invite_query)
    matching_users = user_service.search_users(user_query)
    invite_is_searching = bool(invite_query.strip())
    user_is_searching = bool(user_query.strip())
    return templates.TemplateResponse(request, "admin/accounts.html", {
        "request": request,
        "invites": matching_invites[:ACCOUNT_SEARCH_LIMIT] if invite_is_searching
        else matching_invites[:ACCOUNT_PREVIEW_LIMIT],
        "invite_total": len(matching_invites),
        "invite_limited": invite_is_searching and len(matching_invites) > ACCOUNT_SEARCH_LIMIT,
        "invite_query": invite_query.strip(),
        "users": matching_users[:ACCOUNT_SEARCH_LIMIT] if user_is_searching
        else matching_users[:ACCOUNT_PREVIEW_LIMIT],
        "user_total": len(matching_users),
        "user_limited": user_is_searching and len(matching_users) > ACCOUNT_SEARCH_LIMIT,
        "user_query": user_query.strip()})


@router.post("/invites")
def create_invite(request: Request, role: str = Form("user"),
                  note: str = Form(""), max_uses: int = Form(1),
                  invite_query: str = Form(""), user_query: str = Form("")):
    admin = require_admin(request)
    try:
        svc("users").create_invite(role, created_by=admin.id, note=note, max_uses=max_uses)
    except ValueError:
        pass
    return RedirectResponse(accounts_location(invite_query, user_query), status_code=303)


@router.post("/users/{username}/role")
def set_role(request: Request, username: str, role: str = Form(...),
             invite_query: str = Form(""), user_query: str = Form("")):
    admin = require_admin(request)
    if username != admin.username:  # never demote yourself by accident
        try:
            svc("users").set_role(username, role)
        except ValueError:
            pass
    return RedirectResponse(accounts_location(invite_query, user_query), status_code=303)


@router.post("/users/{username}/delete")
def delete_user(request: Request, username: str, invite_query: str = Form(""),
                user_query: str = Form("")):
    admin = require_admin(request)
    if username != admin.username:  # never delete yourself
        svc("users").delete_user(username)
    return RedirectResponse(accounts_location(invite_query, user_query), status_code=303)


@router.post("/invites/{code}/delete")
def delete_invite(request: Request, code: str, invite_query: str = Form(""),
                  user_query: str = Form("")):
    require_admin(request)
    svc("users").delete_invite(code)
    return RedirectResponse(accounts_location(invite_query, user_query), status_code=303)


# ---- courses & topics ----

@router.post("/courses")
def add_course(request: Request, name: str = Form(...), semester: str = Form(...),
               teacher: str = Form(""), course_type: str = Form("专业必修课"),
               exam: str = Form("其他")):
    require_admin(request)
    try:
        svc("tags").add_course(name, semester, teacher, course_type, exam)
    except ValueError:
        pass
    return RedirectResponse("/admin/tags", status_code=303)


@router.post("/topics")
def add_topic(request: Request, title: str = Form(...),
              description: str = Form("")):
    admin = require_admin(request)
    try:
        svc("tags").add_topic(title, description, created_by=admin.id)
    except ValueError:
        pass
    return RedirectResponse("/admin/tags", status_code=303)


@router.get("/tags")
def tags_page(request: Request):
    require_admin(request)
    return templates.TemplateResponse(request, "admin/tags.html", {
        "request": request,
        "tree": svc("tags").courses_by_year_semester(),
        "topics": svc("tags").list_topics()})
