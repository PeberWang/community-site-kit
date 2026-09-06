# -*- coding: utf-8 -*-
"""Guides router - 指南: 人生课 (topics) + 专业课 (year -> semester -> course -> guide)."""

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app.deps import get_settings, require_user, svc
from app.templating import templates
from libs.download_links import attachment_download_path, known_public_bases
from libs.guide_sources import build_source_catalog
from libs.markdown_lib import guide_callout, render_guide_markdown, render_inline_markdown

router = APIRouter(prefix="/guides")


@router.get("")
def guides_index(request: Request):
    require_user(request)
    tags = svc("tags")
    guides = svc("guides")

    # 指南跟着贡献创建：没有正式指南（version>=1）的课程/主题不出现在指南页
    def has_guide(guide_slug: str) -> bool:
        g = guides.get(guide_slug)
        return bool(g and g.version >= 1)

    tree = {}
    for year, semesters in tags.courses_by_year_semester().items():
        for semester, courses in semesters.items():
            kept = [c for c in courses if has_guide(c.guide_slug)]
            if kept:
                tree.setdefault(year, {})[semester] = kept
    topics = [t for t in tags.list_topics() if has_guide(t.guide_slug)]
    return templates.TemplateResponse(request, "guides/index.html", {
        "request": request,
        "tree": tree,
        "topics": topics,
    })


def _render_guide_page(request, guide_slug: str, title: str, back_url: str,
                       contributions, articles, description: str = "", course=None, topic=None):
    guides = svc("guides")
    guide = guides.get(guide_slug)
    body_md = guides.read_body(guide_slug)
    fb = svc("feedback").get(f"guide:{guide_slug}")
    catalog = build_source_catalog(contributions, articles, svc("users").display_name)
    for source in catalog:
        if source["kind"] == "attachment":
            source["url"] = attachment_download_path(source["storage_key"])
        source["reason_html"] = render_inline_markdown(source.get("reason", "")[:180])
    settings = get_settings()
    legacy_bases = known_public_bases(settings.oss_bucket, settings.oss_endpoint,
                                      settings.oss_public_base or "", settings.oss_cdn_domain)
    return templates.TemplateResponse(request, "guides/guide.html", {
        "request": request,
        "title": title,
        "back_url": back_url,
        "guide": guide,
        "guide_slug": guide_slug,
        "course": course,
        "topic": topic,
        "description": description,
        "guide_callout": guide_callout(body_md),
        "body_html": render_guide_markdown(body_md, legacy_bases),
        "sources": catalog,
        "contributions": contributions,
        "articles": articles,
        "feedback": fb,
        "like_count": len(fb.likes),
        "liked": request.state.user.id in fb.likes,
    })


@router.get("/course/{slug}")
def course_guide(request: Request, slug: str):
    require_user(request)
    tags = svc("tags")
    course = tags.get_course(slug)
    if not course:
        return RedirectResponse("/guides", status_code=303)
    contribs = svc("contributions").approved_for(course_slug=slug)
    arts = svc("articles").published_for(course_slug=slug)
    return _render_guide_page(request, course.guide_slug,
                              f"{course.name} 学习指南", "/guides", contribs, arts,
                              course=course)


@router.get("/topic/{slug}")
def topic_guide(request: Request, slug: str):
    require_user(request)
    tags = svc("tags")
    topic = tags.get_topic(slug)
    if not topic:
        return RedirectResponse("/guides", status_code=303)
    contribs = svc("contributions").approved_for(topic_slug=slug)
    arts = svc("articles").published_for(topic_slug=slug)
    return _render_guide_page(request, topic.guide_slug,
                              topic.title, "/guides", contribs, arts,
                              description=topic.description, topic=topic)
