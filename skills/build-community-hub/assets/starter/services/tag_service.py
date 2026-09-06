# -*- coding: utf-8 -*-
"""Tag service - courses (专业课) & topics (人生课), grouped for navigation."""

import re
from typing import Dict, List, Optional

from config.schema import Course, Topic, YEARS, SEMESTERS, COURSE_TYPES, EXAM_TYPES
from config.settings import Settings
from services.store import JsonStore, now_iso

_SLUG_RE = re.compile(r"[^a-z0-9\-]+")


def slugify(text: str) -> str:
    """URL-safe slug from any text; falls back to pinyin-less hash."""
    base = text.strip().lower()
    base = _SLUG_RE.sub("-", base).strip("-")
    if base:
        return base[:60]
    import hashlib
    return "t" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:10]


class TagService:
    def __init__(self, settings: Settings):
        self.courses = JsonStore(settings.db_dir, "courses", Course, key=lambda c: c.slug)
        self.topics = JsonStore(settings.db_dir, "topics", Topic, key=lambda t: t.slug)

    # ---- courses ----

    def add_course(self, name: str, semester: str, teacher: str = "",
                   course_type: str = "专业必修课", exam: str = "其他") -> Course:
        if semester not in SEMESTERS:
            raise ValueError(f"非法学期: {semester}")
        if course_type not in COURSE_TYPES:
            raise ValueError(f"非法课程类型: {course_type}")
        if exam not in EXAM_TYPES:
            raise ValueError(f"非法考试形式: {exam}")
        name = name.strip()
        if not name:
            raise ValueError("课程名不能为空")
        for c in self.courses.all():
            if c.name == name:
                raise ValueError(f"课程已存在: {name}")
        year = semester[:2] if semester else ""
        slug = slugify(name)
        if self.courses.get(slug):
            slug = f"{slug}-{len(self.courses.all())}"
        course = Course(slug=slug, name=name, teacher=teacher.strip(),
                        year=year, semester=semester, course_type=course_type,
                        exam=exam, guide_slug=f"course-{slug}", created_at=now_iso())
        self.courses.put(course)
        return course

    def get_course(self, slug: str) -> Optional[Course]:
        return self.courses.get(slug)

    def update_course_meta(self, slug: str, teacher: str, exam: str,
                           course_type: str) -> Course:
        """Admin edits course meta (老师/考核/类型会随学期变动，必须可修正)."""
        course = self.get_course(slug)
        if not course:
            raise ValueError("课程不存在")
        if exam not in EXAM_TYPES:
            raise ValueError(f"非法考试形式: {exam}")
        if course_type not in COURSE_TYPES:
            raise ValueError(f"非法课程类型: {course_type}")
        course.teacher = teacher.strip()
        course.exam = exam
        course.course_type = course_type
        self.courses.put(course)
        return course

    def courses_by_year_semester(self) -> Dict[str, Dict[str, List[Course]]]:
        """{year: {semester: [courses]}} for 学年→学期→课程 navigation."""
        tree: Dict[str, Dict[str, List[Course]]] = {y: {} for y in YEARS}
        for course in sorted(self.courses.all(), key=lambda c: (c.semester, c.name)):
            tree.setdefault(course.year or "其他", {}).setdefault(course.semester, []).append(course)
        return tree

    def find_course_by_name(self, name: str) -> Optional[Course]:
        for c in self.courses.all():
            if c.name == name.strip():
                return c
        return None

    # ---- topics ----

    def add_topic(self, title: str, description: str = "",
                  created_by: str = "") -> Topic:
        title = title.strip()
        if not title:
            raise ValueError("主题名不能为空")
        for t in self.topics.all():
            if t.title == title:
                raise ValueError(f"主题已存在: {title}")
        slug = slugify(title)
        if self.topics.get(slug):
            slug = f"{slug}-{len(self.topics.all())}"
        topic = Topic(slug=slug, title=title, description=description.strip(),
                      guide_slug=f"topic-{slug}", created_by=created_by,
                      created_at=now_iso())
        self.topics.put(topic)
        return topic

    def get_topic(self, slug: str) -> Optional[Topic]:
        return self.topics.get(slug)

    def list_topics(self) -> List[Topic]:
        return sorted(self.topics.all(), key=lambda t: t.created_at)

    def find_topic_by_title(self, title: str) -> Optional[Topic]:
        for t in self.topics.all():
            if t.title == title.strip():
                return t
        return None

    def tag_display(self, course_slug: str = "", topic_slug: str = "") -> str:
        if course_slug:
            c = self.get_course(course_slug)
            return f"专业内容 · {c.name}" if c else "未知专业内容"
        if topic_slug:
            t = self.get_topic(topic_slug)
            return f"成长主题 · {t.title}" if t else "未知成长主题"
        return "未标记"
