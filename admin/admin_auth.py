
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from typing import List, Optional

from common.database import db_session
from common.models import Auth, Member
from lib.common import *

router = APIRouter()
templates = AdminTemplates()
templates.env.globals['subject_sort_link'] = subject_sort_link

AUTH_MENU_KEY = "100200"


@router.get("/auth_list")
async def auth_list(
    request: Request,
    db: db_session,
    search_params: dict = Depends(common_search_query_params)
):
    """
    관리자페이지 권한 목록
    """
    request.session["menu_key"] = AUTH_MENU_KEY

    result = select_query(
        request,
        Auth,
        search_params,
        same_search_fields=["mb_id"],
        default_sst=["mb_id", "au_menu"],
        default_sod="",
    )

    for row in result['rows']:
        row.mb_nick = row.member.mb_nick

    # JSON 파일에서 데이터 로드
    with open('admin/admin_menu_bbs.json', 'r', encoding='utf-8') as file:
        auth_menu = json.load(file)

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
        "auth_options": auth_options,
        "paging": get_paging(request, search_params['current_page'], result['total_count']),
    }
    return templates.TemplateResponse("auth_list.html", context)


@router.post("/auth_update", dependencies=[Depends(validate_token)])
async def auth_update(
    request: Request,
    db: db_session,
    mb_id: Optional[str] = Form(default=""),
    au_menu: Optional[str] = Form(default=""),
    r: Optional[str] = Form(default=""),
    w: Optional[str] = Form(default=""),
    d: Optional[str] = Form(default=""),
):
    """
    관리자페이지 권한 등록 및 수정
    """
    exists_member = db.scalar(select(Member).where(Member.mb_id == mb_id))
    if not exists_member:
        raise AlertException(f"{mb_id} : 회원이 존재하지 않습니다.")

    auth_values = [val for val in [r, w, d] if val]  # r, w, d 중 값이 있는 것만 선택
    auth_string = ','.join(auth_values)  # 선택된 값들을 쉼표로 구분하여 문자열 생성

    exists_auth = db.scalar(select(Auth).filter_by(mb_id=mb_id, au_menu=au_menu))
    if exists_auth:
        # 수정
        db.execute(
            update(Auth)
            .where(Auth.mb_id == mb_id, Auth.au_menu == au_menu)
            .values(au_auth=auth_string)
        )
        db.commit()
    else:
        # 추가
        auth = Auth(
            mb_id=mb_id,
            au_menu=au_menu,
            au_auth=auth_string,
        )
        db.add(auth)
        db.commit()

    return RedirectResponse(f"/admin/auth_list?{request.query_params}", status_code=303)


@router.post("/auth_list_delete", dependencies=[Depends(validate_token)])
async def auth_list_delete(
    request: Request,
    db: db_session,
    checks: List[int] = Form(..., alias="chk[]"),
    mb_id: List[str] = Form(..., alias="mb_id[]"),
    au_menu: List[str] = Form(..., alias="au_menu[]"),
):
    """
    관리자페이지 권한 삭제
    """
    for i in checks:
        db.execute(delete(Auth).filter_by(mb_id=mb_id[i], au_menu=au_menu[i]))
        db.commit()

    return RedirectResponse(f"/admin/auth_list?{request.query_params}", status_code=303)
