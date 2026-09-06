# -*- coding: utf-8 -*-
"""
Knowledge Common Kit - OpenAI-compatible LLM adapter
封装OpenAI SDK，对接 DeepSeek 等兼容OpenAI格式的API
"""

import structlog
from openai import AsyncOpenAI
from typing import Dict, Any, Optional
import json

from config.settings import Settings
from libs.exceptions import LLMServiceException

logger = structlog.get_logger()


class LLMAdapter:
    """LLM服务适配器"""

    def __init__(self, settings: Settings):
        """初始化LLM客户端"""
        self.settings = settings
        self.client = AsyncOpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url
        )

    async def generate_completion(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        model: Optional[str] = None
    ) -> str:
        """生成文本补全"""
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            budget = max_tokens
            for attempt in range(3):
                response = await self.client.chat.completions.create(
                    model=model or self.settings.llm_model,
                    messages=messages,
                    max_tokens=budget,
                    temperature=temperature
                )
                choice = response.choices[0]
                content = choice.message.content
                if content:
                    return content
                finish = choice.finish_reason
                if finish == "length" and budget < 32768:
                    budget = min(budget * 2, 32768)
                    logger.warning("LLM空内容自适应重试（推理耗尽预算）",
                                   attempt=attempt + 1, new_budget=budget)
                    continue
                raise LLMServiceException(
                    f"LLM返回空内容 (finish_reason={finish}, max_tokens={budget})")
            raise LLMServiceException(
                f"LLM返回空内容 (自适应重试耗尽, max_tokens={budget})")

        except Exception as e:
            logger.error("LLM生成异常", prompt=prompt[:100], error=str(e))
            raise LLMServiceException(f"LLM生成失败: {str(e)}")

    async def generate_with_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_schema: Optional[Dict[str, Any]] = None,
        max_tokens: int = 4000
    ) -> Dict[str, Any]:
        """生成结构化JSON内容"""
        try:
            # 构建支持JSON的prompt
            json_prompt = prompt
            if json_schema:
                json_prompt += f"\n\n请返回JSON格式，遵循以下schema：\n```json\n{json.dumps(json_schema, indent=2, ensure_ascii=False)}\n```"

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": json_prompt})

            response = await self.client.chat.completions.create(
                model=self.settings.llm_model,
                messages=messages,
                response_format={"type": "json_object"},
                max_tokens=max_tokens
            )

            content = response.choices[0].message.content
            if not content:
                raise LLMServiceException("LLM返回空内容")

            # 解析JSON
            try:
                result = json.loads(content)
            except json.JSONDecodeError as e:
                raise LLMServiceException(f"JSON解析失败: {str(e)}\n原始内容: {content}")

            return result

        except Exception as e:
            logger.error("LLM生成JSON异常", prompt=prompt[:100], error=str(e))
            raise

    async def summarize(
        self,
        full_text: str,
        title: str = "",
        max_chars: int = 40000,
    ) -> str:
        """将 OCR 全文压缩成 markdown 摘要（供飞书摘要集 + 知识助手检索）。

        full_text 可能高达数十万字符，按 max_chars 截断后再压缩。
        """
        clipped = full_text[:max_chars]
        system_prompt = (
            "你是一名严谨的学术资料编目助手。请将给定资料压缩成结构化的 markdown 摘要，"
            "保留核心论点、关键概念、章节脉络，便于检索与问答。不要编造原文没有的内容。"
        )
        prompt = (
            f"资料标题：{title}\n\n"
            f"请输出 markdown 摘要，包含：一句话简介、核心主题（要点列表）、章节脉络。\n\n"
            f"=== 资料正文（可能已截断）===\n{clipped}"
        )
        return await self.generate_completion(
            prompt=prompt, system_prompt=system_prompt, max_tokens=12000, temperature=0.3
        )

    async def close(self):
        """关闭客户端"""
        await self.client.close()
