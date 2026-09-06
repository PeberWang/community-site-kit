# -*- coding: utf-8 -*-
"""Deterministic, explainable checks for guide candidates."""

import re
from dataclasses import dataclass, field
from typing import Iterable, List

_LOCKED = re.compile(r"<!--\s*human-lock:start\s*-->(.*?)<!--\s*human-lock:end\s*-->", re.S)
_UNSUPPORTED_PRECISION = re.compile(r"题型预计|大概率|每周.{0,8}\d+.{0,3}小时|考前.{0,8}\d+天")


@dataclass
class ValidationReport:
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def visible_length(markdown: str) -> int:
    text = re.sub(r"\]\([^)]*\)", "]", markdown)
    return len(re.sub(r"[\s#>*|`_-]", "", text))


def locked_blocks(markdown: str) -> Iterable[str]:
    return (block.strip() for block in _LOCKED.findall(markdown) if block.strip())


def validate_candidate(body: str, kind: str, current_body: str) -> ValidationReport:
    report = ValidationReport()
    required = ("## 学习路径", "## 考核与复习", "## 已知缺口")
    minimum, preferred_minimum, preferred_maximum = 1200, 2500, 3200
    if kind == "topic":
        required = ("## 先看结论", "## 行动地图", "## 经验与分歧")
        minimum, preferred_minimum, preferred_maximum = 1000, 1800, 3000
    for heading in required:
        if heading not in body:
            report.errors.append(f"缺少必需章节：{heading}")
    if re.search(r"^#\s+", body, re.M):
        report.errors.append("正文不能包含一级标题，页面标题由网页统一提供。")
    if re.search(r"https?://", body):
        report.errors.append("正文不能直接写下载链接，请把资料放进资料库。")
    length = visible_length(body)
    if length > 4000:
        report.errors.append(f"正文过长：{length} 字，超过 4000 字上限。")
    elif length < minimum:
        report.errors.append(f"正文过短：{length} 字，无法形成可执行路径。")
    elif length < preferred_minimum or length > preferred_maximum:
        report.warnings.append(
            f"正文为 {length} 字，超出默认 {preferred_minimum} 至 {preferred_maximum} 字范围。")
    for block in locked_blocks(current_body):
        if block not in body:
            report.errors.append("候选稿遗漏了一段人工锁定内容。")
            break
    if kind == "course" and _UNSUPPORTED_PRECISION.search(body):
        report.errors.append("出现了无来源的题型、学习时长或冲刺天数式精确建议。")
    return report
