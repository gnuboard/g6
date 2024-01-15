from fastapi import APIRouter, Path, Request

from core.database import db_session
from core.exception import AlertException
from core.models import Content
from core.template import UserTemplates
from lib.common import *

router = APIRouter()
templates = UserTemplates()


@router.get("/content/{co_id}")
async def content_view(
    request: Request,
    db: db_session,
    co_id: str = Path(...),
):
    """
    컨텐츠 페이지 조회
    """
    content = db.get(Content, co_id)
    if not content:
        raise AlertException(f"{co_id} : 내용 아이디가 존재하지 않습니다.", 404)

    head_img = get_head_tail_img('content', content.co_id + '_h')
    tail_img = get_head_tail_img('content', content.co_id + '_t')

    context = {
        "request": request,
        "title": content.co_subject,
        "content": content,
        "co_himg_url": head_img['img_url'] if head_img['img_exists'] else "",
        "co_timg_url": tail_img['img_url'] if tail_img['img_exists'] else "",
    }
    return templates.TemplateResponse(f"/content/{content.co_skin}/content.html", context)
