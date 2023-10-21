from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import datetime
from common import *
from database import get_db
import models
import hashlib

router = APIRouter()
templates = Jinja2Templates(directory=TEMPLATES_DIR)
templates.env.globals["get_popular_list"] = get_popular_list

@router.get("/{co_id}")
def content_view(request: Request, co_id: str, db: Session = Depends(get_db)):
    '''
    컨텐츠 보기
    '''
    content = db.query(models.Content).filter(models.Content.co_id == co_id).first()
    if not content:
        raise HTTPException(status_code=404, detail=f"{co_id} is not found.")
    
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
    
    return templates.TemplateResponse(f"content/pc/{content.co_skin}/content.html", context)

