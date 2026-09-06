# -*- coding: utf-8 -*-
"""Public, non-secret community identity and feature configuration."""

from pydantic import BaseModel, Field


class SiteIdentity(BaseModel):
    name: str
    short_name: str
    community_name: str
    tagline: str
    description: str
    system_name: str = "社区助手"
    locale: str = "zh-CN"


class FeatureConfig(BaseModel):
    home: bool = True
    guides: bool = True
    articles: bool = True
    events: bool = True
    plaza: bool = False
    contributions: bool = True
    feedback: bool = True


class NavigationLabels(BaseModel):
    home: str = "首页"
    guides: str = "指南"
    articles: str = "文章"
    events: str = "活动"
    plaza: str = "广场"
    contributions: str = "贡献"
    admin: str = "审核"
    structured_items: str = "专业内容"
    open_topics: str = "成长主题"


class ThemeConfig(BaseModel):
    primary: str = "#355070"
    accent: str = "#b56576"


class CommunityConfig(BaseModel):
    site: SiteIdentity
    features: FeatureConfig = Field(default_factory=FeatureConfig)
    labels: NavigationLabels = Field(default_factory=NavigationLabels)
    theme: ThemeConfig = Field(default_factory=ThemeConfig)
