import math
from fastapi import APIRouter, Depends, Query, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session
from common.database import get_db, engine
import common.models as models
from lib.common import *
from typing import List, Optional
from common.formclass import BoardForm
from lib.plugin.service import get_admin_plugin_menus, get_all_plugin_module_names

router = APIRouter()
templates = AdminTemplates(directory=ADMIN_TEMPLATES_DIR)
templates.env.globals['getattr'] = getattr
templates.env.globals['get_selected'] = get_selected
templates.env.globals['option_selected'] = option_selected
templates.env.globals["get_admin_plugin_menus"] = get_admin_plugin_menus
templates.env.globals["get_all_plugin_module_names"] = get_all_plugin_module_names
templates.env.globals['get_skin_select'] = get_skin_select
templates.env.globals['get_group_select'] = get_group_select
templates.env.globals['get_editor_select'] = get_editor_select
templates.env.globals['get_member_level_select'] = get_member_level_select
templates.env.globals['subject_sort_link'] = subject_sort_link
templates.env.globals['get_admin_menus'] = get_admin_menus
templates.env.globals["format"] = format

@router.get("/auth_list")
def auth_list(request: Request, db: Session = Depends(get_db), search_params: dict = Depends(common_search_query_params)):
        # sst: str = Query(default=""), # sort field (정렬 필드)
        # sod: str = Query(default=""), # search order (검색 오름, 내림차순)
        # sfl: str = Query(default=""), # search field (검색 필드)
        # stx: str = Query(default=""), # search text (검색어)
        # current_page: int = Query(default=1, alias="page"), # 페이지
        # ):
    '''
    포인트 목록
    '''
    request.session["menu_key"] = "100200"
    
    # # 초기 쿼리 설정
    # query = db.query(models.Board)
    # records_per_page = request.state.config.cf_page_rows

    # # sod가 제공되면, 해당 열을 기준으로 정렬을 추가합니다.
    # if sst is not None and sst != "":
    #     if sod == "desc":
    #         query = query.order_by(desc(getattr(models.Board, sst)))
    #     else:
    #         query = query.order_by(asc(getattr(models.Board, sst)))

    # # sfl과 stx가 제공되면, 해당 열과 값으로 추가 필터링을 합니다.
    # if sfl is not None and stx is not None:
    #     if hasattr(models.Board, sfl):  # sfl이 models.Board에 존재하는지 확인
    #         if sfl in ["gr_id", "bo_table"]:
    #             query = query.filter(getattr(models.Board, sfl) == stx)
    #         else:
    #             query = query.filter(getattr(models.Board, sfl).like(f"%{stx}%"))
            
    # # 페이지 번호에 따른 offset 계산
    # offset = (current_page - 1) * records_per_page

    # # 최종 쿼리 결과를 가져옵니다.
    # boards = query.offset(offset).limit(records_per_page).all()
    # # 전체 레코드 개수 계산
    # total_records = query.count()
    # global config
   
    result = select_query(
                request,
                models.Auth, 
                search_params, 
                same_search_fields = ["mb_id"], 
                default_sst = ["mb_id", "au_menu"],
                default_sod = "",
            )
    
    for row in result['rows']:
        mb = db.query(Member.mb_nick).filter_by(mb_id=row.mb_id).first()
        if mb:
            row.mb_nick = mb.mb_nick
    
    sum_point = db.query(func.sum(Point.po_point)).scalar()
    
    # JSON 파일에서 데이터 로드
    with open('admin/admin_menu_bbs.json', 'r', encoding='utf-8') as file:
        auth_menu = json.load(file)
        # print(auth_menu)
        
    # 사전의 각 키-값 쌍을 확인
    auth_options = []
    # 사전의 각 메뉴 항목을 순회
    for menu_items in auth_menu.values():
        # 메뉴의 각 항목을 순회
        for item in menu_items:
            # id와 name 값을 가져옴
            id_value = item.get('id', '')
            name_value = item.get('name', '')
            # id와 name 값이 비어 있지 않은 경우 그들을 옵션으로 출력
            if id_value and name_value and id_value[-3:] != '000':
                # print(id_value, name_value)
                auth_options.append(f'<option value="{id_value}">{id_value} {name_value}</option>')    
                
    context = {
        "request": request,
        "config": request.state.config,
        "rows": result['rows'],
        "total_count": result['total_count'],
        "sum_point": sum_point,
        "auth_options": auth_options,
        "paging": get_paging(request, search_params['current_page'], result['total_count']),
    }
    return templates.TemplateResponse("auth_list.html", context)


@router.post("/auth_update")
async def auth_update(request: Request, db: Session = Depends(get_db),
        search_params: dict = Depends(common_search_query_params),
        token: Optional[str] = Form(...),
        mb_id: Optional[str] = Form(default=""),
        au_menu: Optional[str] = Form(default=""),
        r: Optional[str] = Form(default=""),
        w: Optional[str] = Form(default=""),
        d: Optional[str] = Form(default=""),
        ):
    
    if not check_token(request, token):
        raise AlertException("토큰이 유효하지 않습니다.")
    
    exists_member = db.query(models.Member).filter_by(mb_id=mb_id).first()
    if not exists_member:
        return templates.TemplateResponse("alert.html", {"request": request, "errors": [f"{mb_id} : 회원이 존재하지 않습니다."], "goto_url": f"/admin/point_list?{query_string}"})
    
    auth_values = [val for val in [r, w, d] if val]  # r, w, d 중 값이 있는 것만 선택
    auth_string = ','.join(auth_values)  # 선택된 값들을 쉼표로 구분하여 문자열 생성
    
    exists_auth = db.query(models.Auth).filter_by(mb_id=mb_id, au_menu=au_menu).first()
    if exists_auth:
        # 수정
        db.query(models.Auth).filter_by(mb_id=mb_id, au_menu=au_menu).update({
            models.Auth.au_auth: auth_string
        })
        db.commit()
    else:
        # 추가
        auth = models.Auth(
            mb_id=mb_id,
            au_menu=au_menu,
            au_auth=auth_string,
        )
        db.add(auth)
        db.commit()

    return RedirectResponse(f"/admin/auth_list?{query_string(request)}", status_code=303)


@router.post("/auth_list_delete")
async def auth_list_delete(request: Request, db: Session = Depends(get_db),
        search_params: dict = Depends(common_search_query_params),
        token: Optional[str] = Form(...),
        checks: List[int] = Form(..., alias="chk[]"),
        mb_id: List[str] = Form(..., alias="mb_id[]"),
        au_menu: List[str] = Form(..., alias="au_menu[]"),
        ):
    
    if not check_token(request, token):
        raise AlertException("토큰이 유효하지 않습니다.")

    for i in checks:
        exists_auth = db.query(models.Auth).filter_by(mb_id=mb_id[i], au_menu=au_menu[i]).first()
        if exists_auth:
            db.delete(exists_auth)
            db.commit()

    return RedirectResponse(f"/admin/auth_list?{query_string(request)}", status_code=303)
