# -*- coding: utf-8 -*-
"""Format service - LLM 排版层: normalize pasted text into clean markdown.

Pasted content from Word / phone notes is not valid markdown; this layer
guarantees everything persisted is well-formed. Degrades to raw text when
LLM is not configured.
"""

import structlog
from jinja2 import Environment, FileSystemLoader
from pathlib import Path

from config.settings import Settings
from libs.llm_adapter import LLMAdapter

logger = structlog.get_logger()
_TEMPLATE_DIR = Path(__file__).parent.parent / "config" / "prompts"


class FormatService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.env = Environment(loader=FileSystemLoader(str(_TEMPLATE_DIR)))

    async def normalize_markdown(self, title: str, body: str) -> str:
        """Pasted text -> clean markdown. Returns raw body if LLM unavailable."""
        if not self.settings.llm_api_key:
            logger.warning("LLM 未配置，跳过排版规范化")
            return body
        prompt = self.env.get_template("article_format.j2").render(title=title, body=body)
        llm = LLMAdapter(self.settings)
        try:
            return await llm.generate_completion(prompt=prompt, max_tokens=8000,
                                                 temperature=0.2)
        except Exception as e:
            logger.warning("LLM 排版失败，保留原文", error=str(e))
            return body
        finally:
            await llm.close()
