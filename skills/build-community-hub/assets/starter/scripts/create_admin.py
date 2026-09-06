#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成一个管理员邀请码（首个账号用它注册即为管理员）。

用法: python scripts/create_admin.py [note]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import settings
from services.user_service import UserService


def main():
    note = sys.argv[1] if len(sys.argv) > 1 else "首个管理员"
    invite = UserService(settings).create_invite("admin", created_by="script", note=note)
    print(f"管理员邀请码: {invite.code}")
    print("到 /register 用它注册，即成为管理员。")


if __name__ == "__main__":
    main()
