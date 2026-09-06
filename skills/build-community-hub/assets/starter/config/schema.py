# -*- coding: utf-8 -*-
"""Knowledge Common Kit data models (pydantic).

Truth sources:
  data/db/*.json     - light metadata (courses/topics/contributions/announcements/...)
  data/guides/*.md   - guide documents (themselves the truth, LLM-evolved, human-editable)
  OSS                - heavy payloads (attachments / article bodies / OCR fulltext / summaries)
"""

from typing import List
from pydantic import BaseModel, Field


# ---------- enums (plain lists, validated in services) ----------

ROLES = ["admin", "user", "observer"]
REVIEW_STATUS = ["pending", "approved", "rejected"]
EVENT_MODES = ["online", "offline"]
YEARS = ["大一", "大二", "大三", "大四"]
SEMESTERS = ["大一上", "大一下", "大二上", "大二下", "大三上", "大三下", "大四上", "大四下"]
COURSE_TYPES = ["专业必修课", "非专业必修课"]
EXAM_TYPES = ["闭卷", "开卷", "论文", "其他"]
MATERIAL_TYPES = ["PPT", "笔记", "真题", "阅读材料", "教材", "复习大纲", "练习题", "其他"]


# ---------- tags (courses = 专业课; topics = 人生课) ----------

class Course(BaseModel):
    slug: str                      # url-safe id, e.g. "gailvlun"
    name: str                      # 课程全称
    teacher: str = ""
    year: str = ""                 # 大一..大四 (derived from semester, kept for grouping)
    semester: str = ""             # 大一上..大四下
    course_type: str = "专业必修课"
    exam: str = "其他"
    guide_slug: str = ""           # data/guides/<guide_slug>.md
    created_at: str = ""


class Topic(BaseModel):
    """人生课主题专辑：职业规划 / 技术适应 / 社会观察 / 生活体验 ..."""
    slug: str
    title: str
    description: str = ""
    guide_slug: str = ""
    created_by: str = ""
    created_at: str = ""


# ---------- contributions (贡献: tag + 心得/理由 + 附件) ----------

class Attachment(BaseModel):
    id: str = ""                  # immutable upload identity; older records are migrated lazily
    filename: str = ""
    oss_key: str = ""              # raw/... on OSS (or stub path)
    url: str = ""                  # public download url (pointer)
    size: int = 0
    material_type: str = "其他"
    summary_oss_key: str = ""      # pointer to LLM summary md on OSS
    ocr_oss_key: str = ""          # pointer to OCR fulltext md on OSS
    content_sha256: str = ""       # detects duplicate names and preserves source identity


class Contribution(BaseModel):
    id: str
    contributor: str = ""          # user id (foreign key -> User.id)
    course_slug: str = ""          # tag: a course ...
    topic_slug: str = ""           # ... or a topic (exactly one set)
    new_tag_name: str = ""         # proposed new tag (admin confirms at review)
    text: str = ""                 # 心得 / 推荐理由 (may be empty if attachments present)
    attachments: List[Attachment] = Field(default_factory=list)
    review_status: str = "pending"
    reviewed_by: str = ""
    reviewed_at: str = ""
    guide_state: str = "not_queued"  # not_queued | queued | candidate_ready | published
    guide_candidate_id: str = ""
    guide_published_version: int = 0
    guide_updated_at: str = ""
    created_at: str = ""


# ---------- articles (文章: original long-form, standalone pages) ----------

class Article(BaseModel):
    id: str
    slug: str = ""
    title: str = ""
    author: str = ""               # user id
    course_slug: str = ""
    topic_slug: str = ""
    body_oss_key: str = ""         # articles/<slug>.md on OSS
    body: str = ""                 # markdown body (cached copy when OSS stub)
    summary: str = ""
    review_status: str = "pending"
    reviewed_by: str = ""
    created_at: str = ""
    published_at: str = ""
    updated_at: str = ""
    updated_by: str = ""
    withdrawn: bool = False
    withdrawn_at: str = ""
    withdrawn_by: str = ""


# ---------- guides (综述文档, metadata index; bodies in data/guides/) ----------

class Guide(BaseModel):
    slug: str                      # "course-<course_slug>" | "topic-<topic_slug>"
    kind: str = "course"           # course | topic
    title: str = ""
    ref_slug: str = ""             # course_slug or topic_slug
    updated_at: str = ""
    updated_by: str = ""           # user id | "llm"
    version: int = 0
    body_sha256: str = ""
    revision_id: str = ""
    review_status: str = "unverified"  # unverified | verified
    change_summary: str = ""
    known_gaps: List[str] = Field(default_factory=list)


class GuideRevision(BaseModel):
    """Immutable record for a published guide body or preserved history body."""
    id: str
    guide_slug: str
    version: int
    body_sha256: str
    body_path: str
    parent_revision_id: str = ""
    created_at: str = ""
    created_by: str = ""
    approved_by: str = ""
    change_summary: str = ""
    source_ids: List[str] = Field(default_factory=list)
    status: str = "published"      # prepared | published | archived


class GuideCandidate(BaseModel):
    """LLM output waiting for deterministic checks and human approval."""
    id: str
    guide_slug: str
    base_version: int
    base_body_sha256: str
    body_path: str
    created_at: str = ""
    created_by: str = ""
    status: str = "ready"          # ready | published | discarded | stale | failed
    source_ids: List[str] = Field(default_factory=list)
    contribution_ids: List[str] = Field(default_factory=list)
    source_fingerprint: str = ""
    validation_errors: List[str] = Field(default_factory=list)
    validation_warnings: List[str] = Field(default_factory=list)
    change_summary: str = ""


class GuideCompileJob(BaseModel):
    """Coalesced background request to prepare, never publish, a guide candidate."""
    id: str
    guide_slug: str
    contribution_ids: List[str] = Field(default_factory=list)
    requested_at: str = ""
    run_after: str = ""
    status: str = "queued"       # queued | running | completed | failed
    started_at: str = ""
    candidate_id: str = ""
    error: str = ""


# ---------- events (活动) ----------

class Event(BaseModel):
    id: str
    title: str = ""
    mode: str = "offline"          # online | offline
    start_time: str = ""           # ISO datetime
    end_time: str = ""
    place: str = ""                # online: meeting link; offline: physical location
    description: str = ""
    reason: str = ""               # 发起/推介理由 (required)
    organizer: str = ""            # user id
    review_status: str = "pending"
    reviewed_by: str = ""
    created_at: str = ""
    published_at: str = ""
    updated_at: str = ""
    updated_by: str = ""
    withdrawn: bool = False
    withdrawn_at: str = ""
    withdrawn_by: str = ""


# ---------- plaza (广场: free posting, post-hoc moderation) ----------

class Reply(BaseModel):
    id: str
    author: str = ""               # user id
    body: str = ""
    created_at: str = ""
    deleted: bool = False


class Thread(BaseModel):
    id: str
    author: str = ""               # user id
    title: str = ""
    body: str = ""
    created_at: str = ""
    replies: List[Reply] = Field(default_factory=list)
    deleted: bool = False


# ---------- announcements (公告: admin 发布, 首页置顶展示, 下线前不过期) ----------

class Announcement(BaseModel):
    id: str
    title: str = ""                # 首页公告栏只展示标题
    body: str = ""                 # 点击标题后浮窗展示全文
    created_by: str = ""           # user id (admin)
    created_at: str = ""
    deleted: bool = False
    updated_at: str = ""
    updated_by: str = ""
    deleted_at: str = ""
    deleted_by: str = ""


# ---------- feedback (点赞 + 留言 on guides / articles) ----------

class Comment(BaseModel):
    id: str
    author: str = ""               # user id
    body: str = ""
    created_at: str = ""


class Feedback(BaseModel):
    target: str                    # "guide:<slug>" | "article:<id>"
    likes: List[str] = Field(default_factory=list)      # user ids
    comments: List[Comment] = Field(default_factory=list)


# ---------- users & invites ----------

class User(BaseModel):
    username: str
    id: str = ""                   # immutable short id; all foreign keys point here
    password_hash: str = ""
    display_name: str = ""         # 届别+署名, e.g. "22级小赵"
    role: str = "user"             # admin | user | observer
    created_at: str = ""


class Invite(BaseModel):
    code: str
    role: str = "user"
    note: str = ""                 # who it's for
    max_uses: int = 1               # total registrations permitted by this invite
    used_count: int = 0             # registrations recorded after multi-use support
    used_by: str = ""              # first user id (legacy compatibility)
    used_by_ids: List[str] = Field(default_factory=list)  # complete audit trail
    used_at: str = ""
    created_by: str = ""           # user id
    created_at: str = ""
