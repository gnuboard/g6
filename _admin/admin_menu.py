from dataclasses import dataclass
from fastapi import APIRouter, Depends, Request, Form, HTTPException, UploadFile, File, Query
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from database import get_db
import models
import datetime
from common import *

router = APIRouter()
templates = Jinja2Templates(directory=ADMIN_TEMPLATES_DIR)
# 파이썬 함수 및 변수를 jinja2 에서 사용할 수 있도록 등록
# templates.env.globals['today'] = SERVER_TIME.strftime("%Y%m%d")
templates.env.globals["now"] = now
templates.env.globals['getattr'] = getattr
templates.env.globals["get_admin_menus"] = get_admin_menus
templates.env.globals["get_head_tail_img"] = get_head_tail_img
templates.env.globals['get_selected'] = get_selected
templates.env.globals["get_skin_select"] = get_skin_select
templates.env.globals["generate_one_time_token"] = generate_one_time_token


MENU_KEY = "100290"


@router.get("/menu_list")
def menu_list(request: Request, db: Session = Depends(get_db)):
    """
    메뉴 목록
    """
    request.session["menu_key"] = MENU_KEY

    menus = db.query(models.Menu).all()
    return templates.TemplateResponse(
        "menu_list.html", {"request": request, "menus": menus}
    )