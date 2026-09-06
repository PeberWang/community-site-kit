"""Authenticated download routes; storage URLs are never rendered as permanent links."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.deps import require_user, svc
from libs.exceptions import FileDownloadException

router = APIRouter(prefix="/downloads")


@router.get("/objects/{oss_key:path}", include_in_schema=False)
async def download_attachment(request: Request, oss_key: str):
    require_user(request)
    try:
        url = await svc("download_gateway").attachment_url(oss_key)
    except FileDownloadException:
        return HTMLResponse("资料不存在、尚未通过审核或不能下载", status_code=404)
    return RedirectResponse(url, status_code=302)
