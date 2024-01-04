
from typing import List

import bleach
from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func

from core.database import db_session
from core.exception import AlertException
from core.models import Board, Content, Group, Menu
from core.template import AdminTemplates
from lib.common import *
from lib.dependencies import validate_token

router = APIRouter()
templates = AdminTemplates()

MENU_KEY = "100290"


@router.get("/menu_list")
async def menu_list(request: Request, db: db_session):
    """
    메뉴 목록
    """
    request.session["menu_key"] = MENU_KEY

    menus = db.scalars(select(Menu).order_by(Menu.me_code)).all()

    # me_code의 길이가 4이상 데이터는 subclass 속성을 추가.
    for menu in menus:
        if len(menu.me_code) >= 4:
            menu.subclass = True
        else:
            menu.subclass = False

    context = {"request": request, "menus": menus}
    return templates.TemplateResponse("menu_list.html", context)


@router.get("/menu_form")
async def menu_form(
    request: Request,
    code: str = Query(...),
    action: str = Query(None)
):
    """
    메뉴 추가 팝업 페이지
    """
    if action == "new" or code is None:
        me_code_10 = base36_to_base10(code)
        me_code_10 += 36
        code = base10_to_base36(me_code_10)

    context = {
        "request": request,
        "code": code,
        "action": action
    }
    return templates.TemplateResponse("menu_form.html", context)


@router.post("/menu_form_search", response_class=HTMLResponse)
async def menu_form_search(
    request: Request,
    db: db_session,
    type: str = Form(None)
):
    """
    메뉴 추가 팝업 레이아웃
    """
    # type별 model 선언
    datas = []
    if type == "group":
        datas = db.execute(
            select(Group.gr_id.label('id'), Group.gr_subject.label('subject'))
            .order_by(Group.gr_order, Group.gr_id)
        ).all()
    elif type == "board":
        datas = db.execute(
            select(Board.bo_table.label('id'), Board.bo_subject.label('subject'), Board.gr_id)
            .order_by(Board.bo_order, Board.bo_table)
        ).all()
    elif type == "content":
        datas = db.execute(
            select(Content.co_id.label('id'), Content.co_subject.label('subject'))
            .order_by(Content.co_id)
        ).all()
    else:
        type = "input"

    context = {
        "request": request,
        "type": type,
        "datas": datas
    }
    return templates.TemplateResponse(f"menu_search_{type}.html", context)


@router.post("/menu_list_update", dependencies=[Depends(validate_token)])
async def menu_list_update(
    request: Request,
    db: db_session,
    parent_code: List[str] = Form(None, alias="code[]"),
    me_name: List[str] = Form(None, alias="me_name[]"),
    me_link: List[str] = Form(None, alias="me_link[]"),
    me_target: List[str] = Form(None, alias="me_target[]"),
    me_order: List[int] = Form(None, alias="me_order[]"),
    me_use: List[int] = Form(None, alias="me_use[]"),
    me_mobile_use: List[int] = Form(None, alias="me_mobile_use[]")
):
    """
    메뉴 수정
    """
    try:
        # 메뉴 전체 삭제
        db.execute(delete(Menu))

        # 새로운 메뉴 등록
        if parent_code:
            length = len(parent_code)
            group_code = None

            for i in range(0, length):
                insert_me_name = re.sub(r'<.*?>', '', me_name[i])
                insert_me_link = bleach.clean(me_link[i])

                if group_code == parent_code[i]:
                    max_sub_code = db.scalar(
                        select(func.max(func.substr(Menu.me_code, 3, 2)))
                        .where(func.substr(Menu.me_code, 1, 2) == group_code)
                    )
                    max_sub_code_10 = base36_to_base10(max_sub_code)
                    max_sub_code_10 += 36
                    insert_me_code = group_code + base10_to_base36(max_sub_code_10)
                else:
                    max_code = db.scalar(
                        select(func.max(func.substr(Menu.me_code, 1, 2)))
                        .where(func.length(Menu.me_code) == 2)
                    )
                    max_code_10 = base36_to_base10(max_code)
                    max_code_10 += 36
                    insert_me_code = base10_to_base36(max_code_10)
                    group_code = parent_code[i]

                menu = Menu(
                    me_code=insert_me_code,
                    me_name=insert_me_name,
                    me_link=insert_me_link,
                    me_target=me_target[i],
                    me_order=me_order[i],
                    me_use=me_use[i],
                    me_mobile_use=me_mobile_use[i],
                )
                db.add(menu)
                db.commit()
        else:
            db.commit()

        # 기존캐시 삭제
        lfu_cache.update({"menus": None})

    except Exception as e:
        db.rollback()
        raise AlertException(f"Error: {e}", 400)

    return RedirectResponse(f"/admin/menu_list", status_code=303)


def base36_to_base10(number: str = None):
    """36진수 => 10진수 변환

    Args:
        number (str): 36진수

    Raises:
        ValueError: number가 36진수가 아닐 경우

    Returns:
        int: 10진수
    """
    return int(number or "0", 36)


def base10_to_base36(number: int):
    """10진수 => 36진수 변환

    Args:
        number (int): 10진수

    Raises:
        ValueError: number가 음수일 경우

    Returns:
        str: 36진수
    """
    if number < 0:
        raise ValueError("Number must be a non-negative integer.")
    if number == 0:
        return "0"

    charset = "0123456789abcdefghijklmnopqrstuvwxyz"
    base36_string = ""

    while number > 0:
        number, remainder = divmod(number, 36)
        base36_string = charset[remainder] + base36_string

    return base36_string
