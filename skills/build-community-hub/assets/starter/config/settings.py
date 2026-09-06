# -*- coding: utf-8 -*-
"""Knowledge Common Kit settings (pydantic-settings, .env driven)."""

from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore")

    # Web
    session_secret: str = "change-me-in-production"
    site_name: str = "共同生长知识站"
    web_host: str = "127.0.0.1"
    web_port: int = 8790
    environment: str = "development"
    session_max_age: int = 60 * 60 * 24 * 30
    session_cookie_secure: bool = False
    guide_compile_delay_minutes: int = 15
    guide_worker_batch_size: int = 3
    guide_worker_timeout_minutes: int = 30

    # LLM (OpenAI-compatible; guide evolution / article formatting / summaries)
    llm_api_key: str = ""
    llm_base_url: str = "https://api.example.com/v1"
    llm_model: str = "your-model-name"

    # OCR (Zhipu GLM-OCR layout_parsing)
    glm_api_key: str = ""
    glm_ocr_url: str = "https://ocr.example.com/v1/layout_parsing"

    # Cloud storage: local_stub (dev) | aliyun_oss (prod)
    cloud_drive_backend: str = "local_stub"
    cloud_stub_dir: Path = Path("./data/oss_stub")
    oss_bucket: str = ""
    oss_endpoint: str = ""
    oss_access_key_id: str = ""
    oss_access_key_secret: str = ""
    oss_presigned_ttl: int = 3600
    oss_auth_mode: str = "access_key"
    oss_role_arn: str = ""
    oss_role_session_name: str = "community-site"
    oss_cdn_domain: str = ""
    oss_public_base: Optional[str] = None

    # 单附件大小上限（MB，Web 上传；离线可信导入不受限）
    max_upload_mb: int = 200

    # Paths (relative to project root)
    db_dir: Path = Path("./data/db")
    guides_dir: Path = Path("./data/guides")
    uploads_dir: Path = Path("./data/uploads")
    summary_dir: Path = Path("./data/summaries")
    community_config: Path = Path("./config/community.json")

    # Logging
    log_level: str = "INFO"

    project_root: Path = Field(default_factory=lambda: Path(__file__).parent.parent)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.environment.lower() == "production":
            if self.session_secret == "change-me-in-production" or len(self.session_secret) < 32:
                raise ValueError("生产环境必须设置至少 32 位的 SESSION_SECRET")
            if not self.session_cookie_secure:
                raise ValueError("生产环境必须设置 SESSION_COOKIE_SECURE=true")
        for attr in ("db_dir", "guides_dir", "uploads_dir", "summary_dir", "cloud_stub_dir",
                     "community_config"):
            setattr(self, attr, self._resolve(getattr(self, attr)))

    def _resolve(self, path: Path) -> Path:
        if path.is_absolute():
            return path.resolve()
        return (self.project_root / path).resolve()


settings = Settings()
