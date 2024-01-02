from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from lib.common import *
from common.database import db_session
from common.models import Content

router = APIRouter()
templates = UserTemplates()


@router.get("/content/{co_id}")
async def content_view(request: Request, co_id: str, db: db_session):
    '''
    컨텐츠 보기
    '''
    content = db.scalar(select(Content).where(Content.co_id==co_id))
    if not content:
        raise AlertException(status_code=404, detail=f"{co_id} : 내용 아이디가 존재하지 않습니다.")
    
    # 상단 이미지가 있으면 상단 이미지를 출력하고 없으면 내용의 첫번째 이미지를 출력한다.
    co_himg_url = ""
    img_data = get_head_tail_img('content', content.co_id + '_h')
    if (img_data['img_exists']):
        co_himg_url = img_data['img_url']
    co_timg_url = ""
    img_data = get_head_tail_img('content', content.co_id + '_t')
    if (img_data['img_exists']):
        co_timg_url = img_data['img_url']
    
    context = {
        "request": request,
        "title": f"{content.co_subject}",
        "content": content,
        "co_himg_url": co_himg_url,
        "co_timg_url": co_timg_url,
    }
    
    return templates.TemplateResponse(f"{request.state.device}/content/{content.co_skin}/content.html", context)

