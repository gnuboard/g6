
import bleach
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func
from sqlalchemy.orm import aliased, Session
from typing import List

from common.common import *
from common.database import get_db
from lib.plugin.service import get_admin_plugin_menus, get_all_plugin_module_names
from common.models import Board, Content, Group, Menu

router = APIRouter()
admin_templates = MyTemplates(directory=ADMIN_TEMPLATES_DIR)
admin_templates.env.globals["get_admin_plugin_menus"] = get_admin_plugin_menus
admin_templates.env.globals["get_all_plugin_module_names"] = get_all_plugin_module_names
MENU_KEY = "100290"


@router.get("/menu_list")
def menu_list(request: Request, db: Session = Depends(get_db)):
    """
    메뉴 목록
    """
    request.session["menu_key"] = MENU_KEY
    # 메뉴 목록 조회
    menus = db.query(Menu).order_by(Menu.me_code.asc()).all()

    # me_code의 길이가 4이상 데이터는 subclass 속성을 추가.
    for menu in menus:
        if len(menu.me_code) >= 4:
            menu.subclass = True
        else:
            menu.subclass = False

    return admin_templates.TemplateResponse(
        "menu_list.html", {"request": request, "menus": menus}
    )


@router.get("/menu_form")
def menu_form(request: Request, code: str = Query(None), new: str = Query(None)):
    """
    메뉴 추가 팝업 페이지
    """
    if new == 'new' or code is None:
        me_code_10 = base36_to_base10(code)
        me_code_10 += 36
        code = base10_to_base36(me_code_10)

    return admin_templates.TemplateResponse(
        "menu_form.html", {"request": request, "code": code, "new": new}
    )


@router.post("/menu_form_search", response_class=HTMLResponse)
def menu_form_search(request: Request, db: Session = Depends(get_db), type: str = Form(None)):
    """
    메뉴 추가 팝업 레이아웃
    """
    # type별 model 선언
    datas = []
    if type == "group":
        alias = aliased(Group)
        datas = db.query(alias.gr_id.label('id'), alias.gr_subject.label('subject')).order_by(alias.gr_order, alias.gr_id).all()
    elif type == "board":
        alias = aliased(Board)
        datas = db.query(alias.bo_table.label('id'), alias.bo_subject.label('subject'), alias.gr_id).order_by(alias.bo_order, alias.bo_table).all()
    elif type == "content":
        alias = aliased(Content)
        datas = db.query(alias.co_id.label('id'), alias.co_subject.label('subject')).order_by(alias.co_id).all()
    else:
        type = "input"

    return admin_templates.TemplateResponse(
        f"menu_search_{type}.html", {"request": request, "type": type, "datas": datas}
    )


@router.post("/menu_list_update")
def menu_list_update(
    request: Request,
    db: Session = Depends(get_db),
    token: str = Form(...),
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
    if not compare_token(request, token, 'menu_list_update'):
        raise AlertException("토큰이 유효하지 않습니다", 403)

    try:
        # 메뉴 전체 삭제
        db.query(Menu).delete()

        # 새로운 메뉴 등록
        if parent_code:
            length = len(parent_code)
            group_code = None

            for i in range(0, length):
                insert_me_name = re.sub(r'<.*?>', '', me_name[int(i)])
                insert_me_link = bleach.clean(me_link[int(i)])
                if group_code == parent_code[int(i)]:
                    max_me_code = db.query(func.max(func.substring(Menu.me_code, 3, 2))).filter(func.substring(Menu.me_code, 1, 2) == group_code).scalar()
                    max_me_code_10 = base36_to_base10(max_me_code)
                    max_me_code_10 += 36
                    insert_me_code = group_code + base10_to_base36(max_me_code_10)
                    
                else:
                    max_me_code = db.query(func.max(func.substring(Menu.me_code, 1, 2))).filter(func.length(Menu.me_code) == 2).scalar()
                    max_me_code_10 = base36_to_base10(max_me_code)
                    max_me_code_10 += 36
                    insert_me_code = base10_to_base36(max_me_code_10)

                    group_code = parent_code[int(i)]

                db.add(
                    Menu(
                        me_code=insert_me_code,
                        me_name=insert_me_name,
                        me_link=insert_me_link,
                        me_target=me_target[int(i)],
                        me_order=me_order[int(i)],
                        me_use=me_use[int(i)],
                        me_mobile_use=me_mobile_use[int(i)],
                    )
                )
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