"""컨텐츠 Template Router"""
from typing_extensions import Annotated

from fastapi import APIRouter, Depends, Path, Request

from core.template import UserTemplates
from lib.common import get_head_tail_img
from service.content_service import ContentService

router = APIRouter()
templates = UserTemplates()


@router.get("/content/{co_id}")
async def content_view(
    request: Request,
    content_service: Annotated[ContentService, Depends()],
    co_id: str = Path(..., title="컨텐츠 ID"),
):
    """
    컨텐츠 페이지 조회
    """
    content = content_service.read_content(co_id)
    head_img = get_head_tail_img('content', content.co_id + '_h')
    tail_img = get_head_tail_img('content', content.co_id + '_t')

    context = {
        "request": request,
        "title": content.co_subject,
        "content": content,
        "co_himg_url": head_img['url'],
        "co_timg_url": tail_img['url'],
    }
    return templates.TemplateResponse(f"/content/{content.co_skin}/content.html", context)
