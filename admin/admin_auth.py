from typing import List, Optional

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select, update

from core.database import db_session
from core.exception import AlertException
from core.models import Auth, Member
from core.template import AdminTemplates
from lib.dependencies import (
    common_search_query_params, validate_token, validate_captcha
)
from lib.common import *
from lib.template_functions import get_paging

router = APIRouter()
templates = AdminTemplates()
templates.env.globals['captcha_widget'] = captcha_widget

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

    # JSON 파일에서 데이터 로드
    auth_menu = get_admin_menus()
    # 자식메뉴의 id, name 값만 추출
    auth_child_menu = {}
    for menu_items in auth_menu.values():
        auth_child_menu.update({
            item.get('id', ''): item.get('name', '')
            for item in menu_items
        })

    # 닉네임, 권한이름 추가
    for row in result['rows']:
        row.mb_nick = row.member.mb_nick
        row.au_name = auth_child_menu.get(row.au_menu, '')

    # 권한 옵션 생성
    auth_options = []
    for id, name in auth_child_menu.items():
        # id와 name 값이 비어 있지 않은 경우 그들을 옵션으로 출력
        if id and name and id[-3:] != '000':
            auth_options.append(f'<option value="{id}">{id} {name}</option>')

    context = {
        "request": request,
        "config": request.state.config,
        "rows": result['rows'],
        "total_count": result['total_count'],
        "auth_options": auth_options,
        "paging": get_paging(request, search_params['current_page'], result['total_count']),
    }
    return templates.TemplateResponse("auth_list.html", context)


@router.post("/auth_update", dependencies=[Depends(validate_token), Depends(validate_captcha)])
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

    url = "/admin/auth_list"
    query_params = request.query_params
    return RedirectResponse(set_url_query_params(url, query_params), 303)


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

    url = "/admin/auth_list"
    query_params = request.query_params
    return RedirectResponse(set_url_query_params(url, query_params), 303)
