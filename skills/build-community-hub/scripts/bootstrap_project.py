#!/usr/bin/env python3
"""Copy the bundled starter and apply safe first-run community settings."""

import argparse
import json
import shutil
from pathlib import Path

MODULES = {"home", "guides", "articles", "events", "plaza", "contributions", "feedback"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", required=True, type=Path)
    parser.add_argument("--name", required=True)
    parser.add_argument("--community", required=True)
    parser.add_argument("--modules", default="guides,contributions,feedback")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    destination = args.destination.expanduser().resolve()
    if destination.exists() and any(destination.iterdir()):
        raise SystemExit(f"拒绝覆盖非空目录：{destination}")

    enabled = {item.strip() for item in args.modules.split(",") if item.strip()}
    unknown = enabled - MODULES
    if unknown:
        raise SystemExit(f"未知模块：{', '.join(sorted(unknown))}")
    if enabled - {"home"}:
        enabled.add("home")

    starter = Path(__file__).resolve().parent.parent / "assets" / "starter"
    shutil.copytree(
        starter,
        destination,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns(
            "__pycache__", ".pytest_cache", ".ruff_cache", "*.pyc", ".DS_Store"
        ),
    )
    config_path = destination / "config" / "community.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["site"]["name"] = args.name.strip()
    config["site"]["short_name"] = args.name.strip()
    config["site"]["community_name"] = args.community.strip()
    for module in MODULES:
        config["features"][module] = module in enabled
    with config_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(config, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(f"已创建：{destination}")
    print("下一步：确认 config/community.json，再运行 bash setup.sh")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
