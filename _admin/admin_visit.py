import math
from fastapi import APIRouter, Depends, Query, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session
from database import get_db, engine
import models 
from common import *
from typing import List, Optional
from dataclassform import BoardForm


router = APIRouter()
templates = Jinja2Templates(directory=ADMIN_TEMPLATES_DIR)
templates.env.globals['getattr'] = getattr
templates.env.globals['get_selected'] = get_selected
templates.env.globals['option_selected'] = option_selected
templates.env.globals['get_skin_select'] = get_skin_select
templates.env.globals['get_group_select'] = get_group_select
templates.env.globals['get_editor_select'] = get_editor_select
templates.env.globals['get_member_level_select'] = get_member_level_select
templates.env.globals['subject_sort_link'] = subject_sort_link
templates.env.globals['get_admin_menus'] = get_admin_menus
templates.env.globals["generate_one_time_token"] = generate_one_time_token
templates.env.globals["get_paging"] = get_paging

VISIT_MENU_KEY = "200800"

@router.get("/visit_list")
def visit_list(request: Request, db: Session = Depends(get_db),
        current_page: int = Query(default=1, alias="page"), # 페이지
        fr_date: str = Query(default=""), # 시작일
        to_date: str = Query(default=""), # 종료일
        ):
    '''
    접속자집계 목록
    '''
    request.session["menu_key"] = VISIT_MENU_KEY

    if fr_date:
        fr_date = re.sub(r'[^0-9 :\-]', '', fr_date)
    if to_date:
        to_date = re.sub(r'[^0-9 :\-]', '', to_date)

    if fr_date == "":
        fr_date = TIME_YMD
    if to_date == "":
        to_date = TIME_YMD
    
    # 초기 쿼리 설정
    query = db.query(models.Visit)
    records_per_page = request.state.config.cf_page_rows

    # 페이지 번호에 따른 offset 계산
    offset = (current_page - 1) * records_per_page

    # 최종 쿼리 결과를 가져옵니다.
    visits = query.offset(offset).limit(records_per_page).all()

    # 전체 레코드 개수 계산
    total_records = query.count()
    
    query_string = f"fr_date={fr_date}&to_date={to_date}"
    
    context = {
        "request": request,
        "visits": visits,
        "total_records": total_records,
        "paging": get_paging(request, current_page, total_records, f"/admin/visit_list?{query_string}&page="),
        "fr_date": fr_date,
        "to_date": to_date,
    }
    return templates.TemplateResponse("visit_list.html", context)


@router.get("/visit_domain")
def visit_domain(request: Request, db: Session = Depends(get_db),
        current_page: int = Query(default=1, alias="page"), # 페이지
        fr_date: str = Query(default=""), # 시작일
        to_date: str = Query(default=""), # 종료일
        ):
    '''
    도메인별 접속자집계 목록
    '''
    request.session["menu_key"] = VISIT_MENU_KEY

    if fr_date:
        fr_date = re.sub(r'[^0-9 :\-]', '', fr_date)
    if to_date:
        to_date = re.sub(r'[^0-9 :\-]', '', to_date)

    if fr_date == "":
        fr_date = TIME_YMD
    if to_date == "":
        to_date = TIME_YMD
    
    # 초기 쿼리 설정
    query = db.query(models.Visit)
    records_per_page = request.state.config.cf_page_rows

    # 페이지 번호에 따른 offset 계산
    offset = (current_page - 1) * records_per_page

    # 최종 쿼리 결과를 가져옵니다.
    visits = query.offset(offset).limit(records_per_page).all()

    # 전체 레코드 개수 계산
    total_records = query.count()
    
    query_string = f"fr_date={fr_date}&to_date={to_date}"
    
    context = {
        "request": request,
        "visits": visits,
        "total_records": total_records,
        "paging": get_paging(request, current_page, total_records, f"/admin/visit_list?{query_string}&page="),
        "fr_date": fr_date,
        "to_date": to_date,
    }
    return templates.TemplateResponse("visit_domain.html", context)
