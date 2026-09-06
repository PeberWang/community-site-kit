# -*- coding: utf-8 -*-

from libs.guide_validator import validate_candidate


def test_validator_preserves_human_lock_and_rejects_unsupported_precision():
    current = "<!-- human-lock:start -->\n人工结论\n<!-- human-lock:end -->"
    body = """## 学习路径
候选路径。
## 考核与复习
题型预计是简答，每周投入 3 小时。
## 已知缺口
待补充。
"""

    report = validate_candidate(body, "course", current)

    assert any("人工锁定" in item for item in report.errors)
    assert any("无来源" in item for item in report.errors)


def test_validator_accepts_a_complete_topic_shape():
    body = """## 先看结论
    """ + "建议行动。" * 120 + """
## 行动地图
""" + "尝试、反馈、调整。" * 120 + """
## 经验与分歧
""" + "经验要看条件。" * 120 + """
## 已知缺口
暂未记录已知缺口。
"""

    report = validate_candidate(body, "topic", "")

    assert not report.errors
