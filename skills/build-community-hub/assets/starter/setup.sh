#!/usr/bin/env bash
# Community Site Kit local setup for macOS and Linux.
set -euo pipefail

if command -v python3 >/dev/null 2>&1; then
    task_python=python3
elif command -v python >/dev/null 2>&1; then
    task_python=python
else
    echo "需要 Python 3.10 或更高版本：https://www.python.org/downloads/"
    exit 1
fi

if ! "$task_python" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"; then
    echo "当前 Python 版本低于 3.10，请先升级。"
    exit 1
fi

if [ ! -d "venv" ]; then
    "$task_python" -m venv venv
fi

venv/bin/python -m pip install --upgrade pip
venv/bin/python -m pip install -r requirements.txt

if [ ! -f ".env" ]; then
    cp .env.example .env
fi

mkdir -p data/db data/guides/history data/guides/candidates data/uploads data/summaries data/oss_stub

echo "安装完成。下一步："
echo "  1. 检查 config/community.json"
echo "  2. 运行 venv/bin/python scripts/create_admin.py"
echo "  3. 运行 venv/bin/python run.py"
echo "  4. 打开 http://127.0.0.1:8790"
