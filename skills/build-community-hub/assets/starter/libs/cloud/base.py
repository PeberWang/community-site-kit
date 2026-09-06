# -*- coding: utf-8 -*-
"""CloudDriveAdapter 抽象接口 - 热插拔云盘后端的契约。"""

from abc import ABC, abstractmethod


class CloudDriveAdapter(ABC):
    """云盘适配器：upload → key；download_url(key) → url。"""

    @abstractmethod
    async def upload(self, src_path: str, dest_name: str = "") -> str:
        """上传文件到云盘，返回可用于 download_url 查询的 key。"""
        ...

    @abstractmethod
    async def download_url(self, key: str) -> str:
        """由 key 返回可访问的下载 URL（本地存根返回本地路径）。"""
        ...
