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

@router.get("/visit_search")
def visit_search(request: Request, db: Session = Depends(get_db),
        sst: str = Query(default=""), # sort field (정렬 필드)
        sod: str = Query(default=""), # search order (검색 오름, 내림차순)
        sfl: str = Query(default=""), # search field (검색 필드)
        stx: str = Query(default=""), # search text (검색어)
        current_page: int = Query(default=1, alias="page"), # 페이지
        ):
    '''
    접속자 검색
    '''
    request.session["menu_key"] = "200810"
    
    # 초기 쿼리 설정
    query = db.query(models.Visit)
    records_per_page = request.state.config.cf_page_rows
    query_string = generate_query_string(request)

    # sod가 제공되면, 해당 열을 기준으로 정렬을 추가합니다.
    if sst is not None and sst != "":
        if sod == "desc":
            query = query.order_by(desc(getattr(models.Visit, sst)))
        else:
            query = query.order_by(asc(getattr(models.Visit, sst)))

    # sfl과 stx가 제공되면, 해당 열과 값으로 추가 필터링을 합니다.
    if sfl is not None and stx is not None:
        if hasattr(models.Visit, sfl):  # sfl이 models.Board에 존재하는지 확인
            if sfl in ["vi_ip", "vi_date"]:
                query = query.filter(getattr(models.Visit, sfl).like(f"{stx}%"))
            else:
                query = query.filter(getattr(models.Visit, sfl).like(f"%{stx}%"))
            
    # 페이지 번호에 따른 offset 계산
    offset = (current_page - 1) * records_per_page

    # 전체 레코드 개수 계산
    total_records = query.count()
    # 최종 쿼리 결과를 가져옵니다.
    result = query.offset(offset).limit(records_per_page).all()
    
    visits = []
    for i, row in enumerate(result):
        referer = row.vi_referer[:255] if row.vi_referer else ""
        title = referer.replace("<", "&lt;").replace(">", "&gt;")
        link = f'<a href="{row.vi_referer}" target="_blank" title="{title}">'
        visits.append({
            "browser": row.vi_browser,
            "os": row.vi_os,
            "device": row.vi_device,
            "referer": referer,
            "title": title,
            "link": link,
            "ip": row.vi_ip,
            "date": row.vi_date,
            "time": row.vi_time,
        })
    
    context = {
        "request": request,
        "visits": visits,
        "total_records": total_records,
        "paging": get_paging(request, current_page, total_records, f"/admin/visit_search?{query_string}&page="),
    }
    return templates.TemplateResponse("visit_search.html", context)
    

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
