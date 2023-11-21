import math
from fastapi import APIRouter, Depends, Query, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session
from common.database import get_db, engine
import common.models as models 
from common.common import *
from typing import List, Optional
from common.dataclassform import BoardForm
from lib.plugin.service import get_admin_plugin_menus, get_all_plugin_module_names

router = APIRouter()
templates = Jinja2Templates(directory=ADMIN_TEMPLATES_DIR)
templates.env.globals['getattr'] = getattr
templates.env.globals["get_admin_plugin_menus"] = get_admin_plugin_menus
templates.env.globals["get_all_plugin_module_names"] = get_all_plugin_module_names
templates.env.globals['get_selected'] = get_selected
templates.env.globals['option_selected'] = option_selected
templates.env.globals['get_skin_select'] = get_skin_select
templates.env.globals['get_group_select'] = get_group_select
templates.env.globals['get_editor_select'] = get_editor_select
templates.env.globals['get_member_level_select'] = get_member_level_select
templates.env.globals['subject_sort_link'] = subject_sort_link
templates.env.globals['get_admin_menus'] = get_admin_menus
templates.env.globals["generate_token"] = generate_token
templates.env.globals["format"] = format


@router.get("/point_list")
def point_list(request: Request, db: Session = Depends(get_db), search_params: dict = Depends(common_search_query_params)):
        # sst: str = Query(default=""), # sort field (정렬 필드)
        # sod: str = Query(default=""), # search order (검색 오름, 내림차순)
        # sfl: str = Query(default=""), # search field (검색 필드)
        # stx: str = Query(default=""), # search text (검색어)
        # current_page: int = Query(default=1, alias="page"), # 페이지
        # ):
    '''
    포인트 목록
    '''
    request.session["menu_key"] = "200200"
    
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
                models.Point, 
                search_params, 
                same_search_fields = ["mb_id"], 
                default_sst = "po_id",
                default_sod = "desc",
            )
    
    for row in result['rows']:
        mb = db.query(Member.mb_name, Member.mb_nick).filter_by(mb_id=row.mb_id).first()
        if mb:
            row.mb_name = mb.mb_name
            row.mb_nick = mb.mb_nick
    
    sum_point = db.query(func.sum(Point.po_point)).scalar()
   
    context = {
        "request": request,
        "config": request.state.config,
        "points": result['rows'],
        "total_count": result['total_count'],
        "sum_point": sum_point,
        "paging": get_paging(request, search_params['current_page'], result['total_count']),
    }
    return templates.TemplateResponse("point_list.html", context)


@router.post("/point_update")
async def point_update(request: Request, db: Session = Depends(get_db),
        search_params: dict = Depends(common_search_query_params),
        token: Optional[str] = Form(...),
        mb_id: Optional[str] = Form(default=""),
        po_content: Optional[str] = Form(default=""),
        po_point: Optional[str] = Form(default="0"),
        po_expire_term: Optional[int] = Form(None),
        ):
    if not compare_token(request, token, 'point_list'):
        return templates.TemplateResponse("alert.html", {"request": request, "errors": ["토큰이 유효하지 않습니다."]})
    
    try:
        # po_point 값을 정수로 변환합니다.
        po_point = int(po_point)
    except ValueError:
        return templates.TemplateResponse("alert.html", {"request": request, "errors": [f"{po_point} : 포인트를 숫자(정수)로 입력하세요."]})
    
    query_string = generate_query_string(request)
    
    exist_member = db.query(Member).filter_by(mb_id=mb_id).first()
    if not exist_member:
        return templates.TemplateResponse("alert.html", {"request": request, "errors": [f"{mb_id} : 회원이 존재하지 않습니다."], "goto_url": f"/admin/point_list?{query_string}"})
    
    if (po_point < 0) and ((po_point * -1) > exist_member.mb_point): 
        return templates.TemplateResponse("alert.html", {"request": request, "errors": [f"{mb_id} : 포인트를 깍는 경우 현재 포인트보다 작으면 안됩니다."], "goto_url": f"/admin/point_list?{query_string}"})
    
    rel_action = exist_member.mb_id + '-' + str(uuid.uuid4())
    expire = po_expire_term if po_expire_term else 0
    
    insert_point(request, mb_id, po_point, po_content, "@passive", mb_id, rel_action, expire)

    return RedirectResponse(f"/admin/point_list?{query_string}", status_code=303)


@router.post("/point_list_delete")
async def point_list_delete(request: Request, db: Session = Depends(get_db),
        search_params: dict = Depends(common_search_query_params),
        token: Optional[str] = Form(...),
        checks: Optional[List[int]] = Form(None, alias="chk[]"),
        po_id: Optional[List[int]] = Form(None, alias="po_id[]"),
        ):
    if not compare_token(request, token, 'point_list'):
        return templates.TemplateResponse("alert.html", {"request": request, "errors": ["토큰이 유효하지 않습니다."]})

    query_string = generate_query_string(request)

    for i in checks:
        point = db.query(models.Point).filter(models.Point.po_id == po_id[i]).first()
        if point:
            if point.po_point < 0:
                abs_po_point = abs(point.po_point)
            
                if point.po_rel_table == "@expire":
                    delete_expire_point(request, point.mb_id, abs_po_point)
                else:
                    delete_use_point(request, point.mb_id, abs_po_point)
        elif point.po_use_point > 0:
            insert_use_point(request, point.mb_id, point.po_use_point, point.po_id)
                
        # 포인트 내역 삭제
        db.delete(point)
        db.commit()
        
        # po_mb_point에 반영
        db.query(Point).filter(Point.mb_id == point.mb_id, Point.po_id > point.po_id).update({Point.po_mb_point: Point.po_mb_point - point.po_point}, synchronize_session=False)
        db.commit()

        # 포인트 UPDATE        
        sum_point = get_point_sum(request, point.mb_id)
        db.query(Member).filter(Member.mb_id == point.mb_id).update({Member.mb_point: sum_point}, synchronize_session=False)
        db.commit()
        
    return RedirectResponse(f"/admin/point_list?{query_string}", status_code=303)
