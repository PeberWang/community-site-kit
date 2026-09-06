# -*- coding: utf-8 -*-
"""Contribute router - 贡献: tag + 心得/理由 + 附件 (text & files not both empty)."""

from fastapi import APIRouter, Form, Request, UploadFile
from fastapi.responses import RedirectResponse

from config.schema import Attachment
from app.deps import require_user, require_writer, svc
from app.templating import templates

router = APIRouter(prefix="/contribute")


@router.get("")
def form_page(request: Request, course_slug: str = "", topic_slug: str = ""):
    require_writer(request)
    tags = svc("tags")
    course = tags.get_course(course_slug) if course_slug else None
    topic = tags.get_topic(topic_slug) if topic_slug else None
    preset_label = f"{course.name}（{course.semester}）" if course else (topic.title if topic else "")
    preset_choice = f"course:{course.slug}" if course else (f"topic:{topic.slug}" if topic else "")
    return templates.TemplateResponse(request, "contribute/form.html", {
        "request": request, "error": "",
        "topics": tags.list_topics(), "courses": tags.courses.all(),
        "preset_label": preset_label, "preset_choice": preset_choice})


@router.post("")
async def submit(request: Request, tag_choice: str = Form(...),
                 new_tag_name: str = Form(""), text: str = Form(""),
                 material_type: str = Form("其他"),
                 files: list[UploadFile] = None):
    user = require_writer(request)
    tags = svc("tags")
    def err_page(message: str):
        return templates.TemplateResponse(request, "contribute/form.html", {
            "request": request, "error": message,
            "topics": tags.list_topics(), "courses": tags.courses.all(),
            "preset_label": "", "preset_choice": ""})

    course_slug = topic_slug = ""
    if tag_choice.startswith("course:"):
        course_slug = tag_choice.split(":", 1)[1]
    elif tag_choice.startswith("topic:"):
        topic_slug = tag_choice.split(":", 1)[1]
    elif tag_choice == "new" and new_tag_name.strip():
        pass  # admin confirms at review
    else:
        return err_page("请选择归属的课程/人生课，或创建新 tag")

    attachments = []
    for f in (files or []):
        if not f or not f.filename:
            continue
        data = await f.read()
        if not data:
            continue
        tag_for_key = course_slug or topic_slug or new_tag_name.strip() or "misc"
        try:
            key, url, size, attachment_id, content_sha256 = await svc("uploads").save_attachment(
                f.filename, data, tag_for_key)
        except (ValueError, OSError) as e:
            return err_page(str(e))
        attachments.append(Attachment(id=attachment_id, filename=f.filename, oss_key=key, url=url,
                                      size=size, material_type=material_type,
                                      content_sha256=content_sha256))

    try:
        svc("contributions").submit(user.id,
                                    course_slug=course_slug, topic_slug=topic_slug,
                                    new_tag_name=new_tag_name, text=text,
                                    attachments=attachments)
    except ValueError as e:
        return err_page(str(e))
    return RedirectResponse("/contribute/mine?submitted=1", status_code=303)


@router.get("/mine")
def mine(request: Request, submitted: int = 0):
    user = require_user(request)
    return templates.TemplateResponse(request, "contribute/mine.html", {
        "request": request,
        "contributions": svc("contributions").by_user(user.id),
        "submitted": submitted, "tags": svc("tags")})
