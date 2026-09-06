#!/usr/bin/env python3
"""Validate a generated Knowledge Common Kit project without starting the server."""

import argparse
import json
from pathlib import Path

MODULES = {"home", "guides", "articles", "events", "plaza", "contributions", "feedback"}
REQUIRED_DIRS = ("app", "config", "glue", "libs", "services", "tests")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", nargs="?", default=".", type=Path)
    root = parser.parse_args().project.resolve()
    errors = []
    for name in REQUIRED_DIRS:
        if not (root / name).is_dir():
            errors.append(f"缺少目录：{name}")
    path = root / "config" / "community.json"
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"community.json 无法读取：{exc}")
        config = {}
    site = config.get("site", {})
    if not str(site.get("name", "")).strip():
        errors.append("site.name 不能为空")
    features = config.get("features", {})
    unknown = set(features) - MODULES
    if unknown:
        errors.append(f"未知模块：{', '.join(sorted(unknown))}")
    if not any(bool(features.get(name)) for name in MODULES):
        errors.append("至少启用一个模块")
    if errors:
        print("项目验证失败：")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"项目验证通过：{root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
