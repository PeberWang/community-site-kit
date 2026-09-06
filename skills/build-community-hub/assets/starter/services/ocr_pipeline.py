# -*- coding: utf-8 -*-
"""OCR pipeline - approved contribution attachments -> OCR fulltext + LLM summary -> OSS.

Flow per attachment: local file -> (Office->PDF via LibreOffice if needed)
-> GLM-OCR fulltext -> upload ocr/ key -> LLM summary -> upload summary/ key
-> write pointers back onto the contribution.

Degrades gracefully: no GLM key / no LibreOffice -> skipped with warning.
"""

import asyncio
import json
import os
import shutil
import structlog
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Optional

from config.settings import Settings
from libs import ocr_adapter
from libs.cloud import get_drive
from libs.llm_adapter import LLMAdapter
from libs.storage_keys import ocr_key, summary_key
from services.contribution_service import ContributionService

logger = structlog.get_logger()

_PDF_EXT = {".pdf"}
_EPUB_EXT = {".epub"}
_OFFICE_EXT = {".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"}
_TEXT_EXT = {".md", ".txt"}


def _find_soffice() -> Optional[str]:
    found = shutil.which("soffice") or shutil.which("libreoffice")
    if found:
        return found
    mac = "/Applications/LibreOffice.app/Contents/MacOS/soffice"
    return mac if os.path.exists(mac) else None


async def _office_to_pdf(soffice: str, src: str, out_dir: str, timeout: int = 120) -> str:
    cmd = [soffice, "--headless", "--convert-to", "pdf", "--outdir", out_dir, src]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(f"LibreOffice 转换失败: {stderr.decode('utf-8', 'ignore')[:200]}")
    pdf = os.path.join(out_dir, Path(src).stem + ".pdf")
    if not os.path.exists(pdf):
        raise RuntimeError("LibreOffice 未产出 PDF")
    return pdf


class OcrPipeline:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.contributions = ContributionService(settings)
        self._soffice = _find_soffice()

    async def run_pending(self) -> Dict[str, Any]:
        """OCR all approved attachments lacking a summary pointer."""
        if not self.settings.glm_api_key:
            return {"status": "skipped", "reason": "未配置 GLM_API_KEY"}
        done, failed, skipped = 0, 0, 0
        supported = _TEXT_EXT | _EPUB_EXT | _OFFICE_EXT | _PDF_EXT
        deadletter_path = Path(self.settings.uploads_dir) / "ocr_deadletter.json"
        deadletter = set()
        if deadletter_path.exists():
            deadletter = set(json.loads(deadletter_path.read_text(encoding="utf-8")))
        for c in self.contributions.store.find(lambda x: x.review_status == "approved"):
            for idx, att in enumerate(c.attachments):
                if att.summary_oss_key or not att.oss_key:
                    continue
                ext = Path(att.filename).suffix.lower()
                if ext not in supported or att.oss_key in deadletter:
                    if att.oss_key not in deadletter:
                        deadletter.add(att.oss_key)
                        logger.info("不支持的类型，登记永久跳过", file=att.filename)
                    skipped += 1
                    continue
                t0 = time.monotonic()
                logger.info("开始处理附件", file=att.filename,
                            size_mb=round(att.size / 1024 / 1024, 1))
                try:
                    await self._process_one(c.id, idx, att.oss_key, att.filename,
                                            att.id or f"legacy-{c.id}-{idx}")
                    done += 1
                    logger.info("附件完成", file=att.filename,
                                elapsed_s=round(time.monotonic() - t0, 1))
                except Exception as e:
                    logger.warning("附件失败（可重跑补齐）", file=att.filename,
                                   error=str(e)[:300])
                    failed += 1
        deadletter_path.write_text(json.dumps(sorted(deadletter), ensure_ascii=False),
                                   encoding="utf-8")
        return {"status": "ok", "processed": done, "failed": failed,
                "skipped_unsupported": skipped}

    def _cache_dir(self, oss_k: str, size: int) -> Path:
        """断点续传缓存目录：按 oss key + 文件大小定位。"""
        stem = Path(oss_k).stem
        return Path(self.settings.uploads_dir) / "ocr_cache" / f"{stem}_{size}"

    async def _process_one(self, cid: str, idx: int, oss_k: str, filename: str,
                           source_id: str) -> None:
        local_src = self.settings.uploads_dir / oss_k
        if not local_src.exists():
            raise FileNotFoundError(str(local_src))
        ext = Path(filename).suffix.lower()
        drive = get_drive(self.settings)
        llm = LLMAdapter(self.settings)
        cache_dir = self._cache_dir(oss_k, local_src.stat().st_size)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                if ext in _TEXT_EXT:
                    fulltext = local_src.read_text(encoding="utf-8",
                                                   errors="replace")
                elif ext in _EPUB_EXT:
                    fulltext = ocr_adapter.extract_epub_text(str(local_src))
                elif ext in _OFFICE_EXT:
                    if not self._soffice:
                        raise RuntimeError("未安装 LibreOffice，跳过 Office 文件")
                    target = await _office_to_pdf(self._soffice, str(local_src), tmp)
                    fulltext = await ocr_adapter.run_ocr(
                        target, self.settings.glm_api_key,
                        self.settings.glm_ocr_url, cache_dir)
                elif ext in _PDF_EXT:
                    fulltext = await ocr_adapter.run_ocr(
                        str(local_src), self.settings.glm_api_key,
                        self.settings.glm_ocr_url, cache_dir)
                else:
                    raise RuntimeError(f"不支持 OCR 的类型: {ext}")
            ocr_storage_key = ocr_key(source_id)
            summary_storage_key = summary_key(source_id)
            ocr_local = self.settings.uploads_dir / ocr_storage_key
            ocr_local.parent.mkdir(parents=True, exist_ok=True)
            ocr_local.write_text(fulltext, encoding="utf-8")
            await drive.upload(str(ocr_local), ocr_storage_key)

            summary = await llm.summarize(fulltext, title=Path(filename).stem)
            sum_local = self.settings.uploads_dir / summary_storage_key
            sum_local.parent.mkdir(parents=True, exist_ok=True)
            sum_local.write_text(summary, encoding="utf-8")
            await drive.upload(str(sum_local), summary_storage_key)

            self.contributions.attach_summary(cid, idx, summary_storage_key, ocr_storage_key)
        finally:
            await llm.close()
