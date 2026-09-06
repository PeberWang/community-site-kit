# -*- coding: utf-8 -*-
"""LocalStubDrive - dev-time cloud stub.

Files are copied under stub_dir mirroring the key layout.
download_url returns an app-relative /files/<key> path, which the web app
serves (login required). Swap backend to aliyun_oss in production with no
code change.
"""

import shutil
from pathlib import Path

from libs.cloud.base import CloudDriveAdapter


class LocalStubDrive(CloudDriveAdapter):
    def __init__(self, stub_dir: Path):
        self.stub_dir = Path(stub_dir)
        self.stub_dir.mkdir(parents=True, exist_ok=True)

    async def upload(self, src_path: str, dest_name: str = "") -> str:
        name = dest_name or Path(src_path).name
        dest = self.stub_dir / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_path, dest)
        return name

    async def download_url(self, key: str) -> str:
        return f"/files/{key}"
