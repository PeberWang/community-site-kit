# -*- coding: utf-8 -*-
"""GLM-OCR 适配器：PDF 智能分批 → 逐批 OCR（带断点续传）→ 组装 markdown。

GLM layout_parsing 硬限制：PDF ≤50MB 且 ≤100页。因此分批必须同时卡
页数与字节数（大页数小图的书按页切没问题，扫描大书按页切会撞字节上限）。

可靠性设计：
  - 分批：先按 max_pages 切页范围，超过 max_bytes 的范围递归二分，直到双达标
  - 内存：页范围规划与字节构造分离；批次 bytes 逐批构造、用完即释放，
    绝不整册驻留内存（2GB 内存服务器上 500MB 级 PDF 可安全处理）
  - 重试：5xx/网络错误指数退避（最多 4 次）；4xx 立即失败（重试无意义）
  - 断点续传：每批结果落 cache_dir/batch_{i}.md，重跑跳过已完成批次
  - 日志：每批开始/完成/失败均输出（批次号、大小、耗时），杜绝"静默卡死"
"""

import asyncio
import base64
import gc
import io
import json
import time
import zipfile
from pathlib import Path
from typing import List, Tuple
from xml.etree import ElementTree as ET

import httpx
import structlog
from pypdf import PdfReader, PdfWriter

logger = structlog.get_logger()

MAX_PAGES = 80                 # GLM 上限 100 页，留余量
MAX_BYTES = 45 * 1024 * 1024   # GLM 上限 50MB，留余量


def _write_pages(reader: PdfReader, indexes: List[int]) -> bytes:
    writer = PdfWriter()
    for i in indexes:
        writer.add_page(reader.pages[i])
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _write_pages_range(pdf_path: str, start: int, end: int) -> bytes:
    """用独立 PdfReader 只构造 [start, end) 页的字节，用完即释放。

    不复用 reader 是为了避免 pypdf 解析对象缓存随访问页数无限累积
    （800 页大书全量访问会把 reader 缓存撑到数百 MB）。
    """
    reader = PdfReader(pdf_path)
    try:
        return _write_pages(reader, list(range(start, end)))
    finally:
        reader.stream.close()


def _plan_ranges(pdf_path: str, max_pages: int = MAX_PAGES,
                 max_bytes: int = MAX_BYTES) -> List[Tuple[int, int]]:
    """按页数+字节双约束规划批次页范围；超限范围递归二分。

    测量阶段每块用独立 reader 构造字节（局部变量，用完即弃），
    只保留页范围列表，不保留任何批次字节。
    """
    reader = PdfReader(pdf_path)
    total = len(reader.pages)
    reader.stream.close()

    ranges: List[Tuple[int, int]] = []

    def emit(start: int, end: int) -> None:
        size = len(_write_pages_range(pdf_path, start, end))
        if size > max_bytes and end - start > 1:
            mid = (start + end) // 2
            emit(start, mid)
            emit(mid, end)
        else:
            ranges.append((start, end))

    for start in range(0, total, max_pages):
        emit(start, min(start + max_pages, total))
    return ranges


async def _ocr_batch(client: httpx.AsyncClient, pdf_bytes: bytes,
                     api_key: str, ocr_url: str, tag: str,
                     attempts: int = 6, base_sleep: float = 5.0) -> str:
    """单批 OCR：429/5xx/网络错误退避重试，其余 4xx 立即抛出。

    429 是限流，等待窗口重置后可恢复，用更长的固定阶梯（20/40/80/160s）。
    """
    payload = {"model": "glm-ocr",
               "file": f"data:application/pdf;base64,{base64.b64encode(pdf_bytes).decode()}"}
    headers = {"Authorization": api_key, "Content-Type": "application/json"}
    last_err: Exception = RuntimeError("unknown")
    for i in range(attempts):
        try:
            resp = await client.post(ocr_url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            return data.get("md_results") or json.dumps(data, ensure_ascii=False)
        except (httpx.HTTPStatusError, httpx.TransportError) as e:
            last_err = e
            status = e.response.status_code if isinstance(e, httpx.HTTPStatusError) else None
            if status and status != 429 and status < 500:
                raise
            wait = 20 * (2 ** i) if status == 429 else base_sleep * (2 ** i)
            logger.warning("批次重试", batch=tag, attempt=i + 1,
                           status=status, wait_s=wait)
            await asyncio.sleep(wait)
    raise last_err


async def _ocr_pages(client: httpx.AsyncClient, pdf_path: str,
                     start: int, end: int,
                     api_key: str, ocr_url: str, tag: str,
                     sub_dir: Path, depth: int = 0, max_depth: int = 3) -> str:
    """OCR [start, end) 页区间；毒页（400/反复5xx）递归二分绕开。

    叶子级断点续传：每个页区间的成果（含毒页占位）按绝对页码落盘到
    sub_dir/sub_{start}_{end}.md。重跑时整段复用，已成功页绝不重扫；
    拼装顺序即页码顺序，毒页占位始终留在原位（归位而非丢弃）。
    """
    leaf_cache = sub_dir / f"sub_{start:05d}_{end:05d}.md"
    if leaf_cache.exists() and leaf_cache.stat().st_size > 0:
        logger.info("子区间复用缓存", batch=tag, pages=f"{start + 1}-{end}")
        return leaf_cache.read_text(encoding="utf-8")
    sub_dir.mkdir(parents=True, exist_ok=True)

    pdf_bytes = _write_pages_range(pdf_path, start, end)
    try:
        md = await _ocr_batch(client, pdf_bytes, api_key, ocr_url, tag)
    except httpx.HTTPStatusError as e:
        status = e.response.status_code
        poison = status >= 500 or status == 400
        if not poison:
            raise
        if end - start <= 1 or depth >= max_depth:
            if status != 400:
                raise
            logger.warning("毒页兜底占位", batch=tag, pages=f"{start + 1}-{end}")
            label = f"第 {start + 1} 页" if end - start == 1 else f"第 {start + 1}-{end} 页"
            md = f"\n\n（{label} OCR 失败，已跳过）\n\n"
        else:
            mid = (start + end) // 2
            logger.warning("批次疑似毒页，二分绕开", batch=tag, status=status,
                           depth=depth + 1)
            parts = []
            for j, (s, e) in enumerate(((start, mid), (mid, end))):
                parts.append(await _ocr_pages(client, pdf_path, s, e,
                                              api_key, ocr_url,
                                              f"{tag}.{j + 1}", sub_dir,
                                              depth + 1, max_depth))
                await asyncio.sleep(3)
            md = "\n\n".join(parts)
    finally:
        del pdf_bytes
        gc.collect()
    leaf_cache.write_text(md, encoding="utf-8", newline="\n")
    return md


def _extract_text_layer(pdf_path: str, min_chars_per_page: int = 30) -> str:
    """原生 PDF（有文本层）直接抽文本，跳过 GLM。

    采样前 10 页判断：平均每页字符数达标即视为 born-digital，
    全量抽取返回；否则返回空串走 GLM-OCR。
    """
    reader = PdfReader(pdf_path)
    try:
        total = len(reader.pages)
        sample_idx = list(range(min(10, total)))
        sample = "".join(reader.pages[i].extract_text() or "" for i in sample_idx)
        if len(sample) < len(sample_idx) * min_chars_per_page:
            return ""
        parts = []
        for i, page in enumerate(reader.pages):
            parts.append(f"\n\n--- 第 {i + 1} 页 ---\n\n")
            parts.append(page.extract_text() or "")
        return "".join(parts).strip()
    finally:
        reader.stream.close()


async def run_ocr(pdf_path: str, api_key: str, ocr_url: str,
                  cache_dir: Path, concurrency: int = 1,
                  max_pages: int = MAX_PAGES, max_bytes: int = MAX_BYTES) -> str:
    """PDF → GLM-OCR 全量 markdown（逐批流式 + 断点续传）。

    cache_dir 下每批一个 batch_{i:03d}.md；已完成批次重跑直接复用。
    批次字节逐批构造、用完即释放；concurrency 参数保留兼容，实际按
    低内存服务器设计固定串行。
    """
    t0 = time.monotonic()
    text_layer = _extract_text_layer(pdf_path)
    if text_layer:
        logger.info("文本层直出（跳过 GLM）", file=Path(pdf_path).name,
                    chars=len(text_layer))
        return text_layer
    ranges = _plan_ranges(pdf_path, max_pages, max_bytes)
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    n = len(ranges)
    total_pages = ranges[-1][1] if ranges else 0
    logger.info("OCR 开始", file=Path(pdf_path).name, batches=n,
                pages=total_pages,
                size_mb=round(Path(pdf_path).stat().st_size / 1024 / 1024, 1))

    sub_dir = cache_dir / "sub"
    sub_dir.mkdir(parents=True, exist_ok=True)

    parts: List[str] = []
    async with httpx.AsyncClient(timeout=600) as client:
        for i, (start, end) in enumerate(ranges):
            cache_file = cache_dir / f"batch_{i:03d}.md"
            if cache_file.exists() and cache_file.stat().st_size > 0:
                logger.info("批次复用缓存", batch=f"{i + 1}/{n}")
                parts.append(cache_file.read_text(encoding="utf-8"))
                continue
            if i > 0:
                await asyncio.sleep(1.5)  # 批次间隔，温和对限流
            bt = time.monotonic()
            try:
                md = await _ocr_pages(client, pdf_path, start, end,
                                      api_key, ocr_url,
                                      tag=f"{i + 1}/{n}", sub_dir=sub_dir)
            except Exception as e:
                logger.error("批次失败", batch=f"{i + 1}/{n}", error=str(e)[:200])
                raise RuntimeError(
                    f"批次 {i + 1}/{n} 失败: {e}（此前批次与子区间缓存已保留，可重跑续传）"
                ) from e
            cache_file.write_text(md, encoding="utf-8", newline="\n")
            logger.info("批次完成", batch=f"{i + 1}/{n}",
                        elapsed_s=round(time.monotonic() - bt, 1),
                        chars=len(md))
            parts.append(md)

    logger.info("OCR 完成", file=Path(pdf_path).name,
                elapsed_s=round(time.monotonic() - t0, 1),
                total_chars=sum(len(p) for p in parts))
    return "\n\n".join(parts)


def extract_epub_text(epub_path: str, max_chars: int = 200_000) -> str:
    """EPUB → 纯文本（zip 内 xhtml 正文按出现顺序拼接）。

    纯文本抽取即可，不需要 OCR；后续由 LLM 做结构化摘要。
    """
    chapters = []
    with zipfile.ZipFile(epub_path) as z:
        names = [n for n in z.namelist()
                 if n.lower().endswith((".xhtml", ".html", ".htm"))]
        for n in names:
            try:
                with z.open(n) as f:
                    root = ET.fromstring(f.read())
            except ET.ParseError:
                continue
            texts = [t.strip() for t in root.itertext() if t.strip()]
            if texts:
                chapters.append("\n".join(texts))
    return "\n\n".join(chapters)[:max_chars]
