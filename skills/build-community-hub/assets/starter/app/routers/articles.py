# -*- coding: utf-8 -*-
"""Articles router - 文章栏目: list / detail / submit (paste or file, LLM-formatted)."""

from fastapi import APIRouter, Form, Request, UploadFile
from fastapi.responses import RedirectResponse

from app.deps import get_settings, require_user, require_writer, svc
from libs.download_links import known_public_bases, rewrite_legacy_download_urls
from app.templating import templates
from libs.markdown_lib import render_markdown

router = APIRouter(prefix="/articles")


@router.get("")
def list_articles(request: Request):
    require_user(request)
    return templates.TemplateResponse(request, "articles/list.html", {
        "request": request,
        "articles": svc("articles").published(),
        "tags": svc("tags"),
    })


@router.get("/submit")
def submit_page(request: Request):
    require_writer(request)
    tags = svc("tags")
    return templates.TemplateResponse(request, "articles/submit.html", {
        "request": request, "error": "",
        "topics": tags.list_topics(),
        "courses": tags.courses.all(),
    })


@router.post("/submit")
async def submit(request: Request, title: str = Form(...),
                 body: str = Form(""), file: UploadFile = None,
                 course_slug: str = Form(""), topic_slug: str = Form("")):
    user = require_writer(request)
    raw = (body or "").strip()
    if file and file.filename:
        content = await file.read()
        try:
            raw = content.decode("utf-8")
        except UnicodeDecodeError:
            return templates.TemplateResponse(request, "articles/submit.html", {
                "request": request,
                "error": "上传的文件需要是 UTF-8 文本（.md/.txt）；Word/PDF 请直接粘贴正文",
                "topics": svc("tags").list_topics(), "courses": svc("tags").courses.all()})
    if not raw:
        return templates.TemplateResponse(request, "articles/submit.html", {
            "request": request, "error": "请粘贴正文或上传文件",
            "topics": svc("tags").list_topics(), "courses": svc("tags").courses.all()})
    try:
        formatted = await svc("format").normalize_markdown(title, raw)
        article = svc("articles").submit(user.id,
                                         title, formatted,
                                         course_slug=course_slug,
                                         topic_slug=topic_slug)
        key, _url = await svc("uploads").save_text(article.body, article.slug)
        svc("articles").update_body(article.id, article.body, body_oss_key=key)
    except ValueError as e:
        return templates.TemplateResponse(request, "articles/submit.html", {
            "request": request, "error": str(e),
            "topics": svc("tags").list_topics(), "courses": svc("tags").courses.all()})
    return RedirectResponse("/articles/mine?submitted=1", status_code=303)


@router.get("/mine")
def mine(request: Request, submitted: int = 0):
    user = require_writer(request)
    return templates.TemplateResponse(request, "articles/mine.html", {
        "request": request,
        "articles": svc("articles").by_user(user.id),
        "submitted": submitted,
    })


@router.get("/{aid}")
def detail(request: Request, aid: str):
    user = require_user(request)
    article = svc("articles").get(aid)
    if not article or article.review_status != "approved" or article.withdrawn:
        return RedirectResponse("/articles", status_code=303)
    fb = svc("feedback").get(f"article:{aid}")
    settings = get_settings()
    legacy_bases = known_public_bases(settings.oss_bucket, settings.oss_endpoint,
                                      settings.oss_public_base or "", settings.oss_cdn_domain)
    return templates.TemplateResponse(request, "articles/detail.html", {
        "request": request, "article": article,
        "body_html": render_markdown(rewrite_legacy_download_urls(article.body, legacy_bases)),
        "tag_display": svc("tags").tag_display(article.course_slug, article.topic_slug),
        "feedback": fb, "like_count": len(fb.likes),
        "liked": user.id in fb.likes,
    })
