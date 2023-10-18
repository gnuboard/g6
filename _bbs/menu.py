from common import *
from database import get_db
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

import models

import cachetools

router = APIRouter()
templates = Jinja2Templates(directory=TEMPLATES_DIR)
# 파이썬 함수 및 변수를 jinja2 에서 사용할 수 있도록 등록
templates.env.globals["now"] = now
templates.env.globals['getattr'] = getattr


@router.post("/list/", response_class=HTMLResponse)
def get_menu_list(request: Request, db: Session = Depends(get_db)):
    """
    메뉴 데이터 조회 레이아웃
    """
    # TODO: 캐싱 처리 추가

    menus = []
    # 부모메뉴 조회
    parent_menus = db.query(models.Menu).filter(func.length(models.Menu.me_code) == 2).order_by(models.Menu.me_order).all()
    
    for menu in parent_menus:
        parent_code = menu.me_code

        # 자식 메뉴 조회
        child_menus = db.query(models.Menu).filter(
            func.length(models.Menu.me_code) == 4,
            func.substring(models.Menu.me_code, 1, 2) == parent_code
        ).order_by(models.Menu.me_order).all()

        menu.sub = child_menus
        menus.append(menu)

    return templates.TemplateResponse(
        "bbs/menu.html", {"request": request, "menus": menus}
    )