from fastapi import APIRouter, Depends, Request, Form, Path
from fastapi.responses import RedirectResponse
from typing import List

from core.database import db_session
from core.exception import AlertException
from core.models import Board, Group, GroupMember
from core.formclass import GroupForm
from core.template import AdminTemplates
from lib.common import *
from lib.dependencies import common_search_query_params, validate_token

router = APIRouter()
templates = AdminTemplates()

BOARDGROUP_MENU_KEY = "300200"


@router.get("/boardgroup_list")
async def boardgroup_list(
    request: Request,
    db: db_session,
    search_params: dict = Depends(common_search_query_params)
):
    """
    게시판그룹관리 목록
    """
    request.session["menu_key"] = BOARDGROUP_MENU_KEY

    result = select_query(
        request,
        Group,
        search_params,
    )

    for group in result['rows']:
        group.board_count = len(group.boards)
        group.access_member_count = len(group.members)

    context = {
        "request": request,
        "groups": result['rows'],
    }
    return templates.TemplateResponse("boardgroup_list.html", context)


@router.post("/boardgroup_list_update", dependencies=[Depends(validate_token)])
async def boardgroup_list_update(
    request: Request,
    db: db_session,
    checks: List[int] = Form(None, alias="chk[]"),
    gr_id: List[str] = Form(None, alias="gr_id[]"),
    gr_subject: List[str] = Form(None, alias="gr_subject[]"),
    gr_admin: List[str] = Form(None, alias="gr_admin[]"),
    gr_use_access: List[int] = Form(None, alias="gr_use_access[]"),
    gr_order: List[int] = Form(None, alias="gr_order[]"),
    gr_device: List[str] = Form(None, alias="gr_device[]"),
):
    """
    게시판그룹 일괄 수정
    """
    for i in checks:
        group = db.get(Group, gr_id[i])
        if group:
            group.gr_id = gr_id[i]
            group.gr_subject = gr_subject[i]
            group.gr_admin = gr_admin[i]
            group.gr_use_access = get_from_list(gr_use_access, i, 0)
            group.gr_order = gr_order[i]
            group.gr_device = gr_device[i]
            db.commit()

    url = "/admin/boardgroup_list"
    query_params = request.query_params
    return RedirectResponse(set_url_query_params(url, query_params), 303)


@router.post("/boardgroup_list_delete", dependencies=[Depends(validate_token)])
async def boardgroup_list_delete(
    request: Request,
    db: db_session,
    checks: List[int] = Form(None, alias="chk[]"),
    gr_id: List[str] = Form(None, alias="gr_id[]"),
):
    """
    게시판그룹 일괄 삭제
    """
    for i in checks:
        exists_board = db.scalar(
            exists(Board.bo_table)
            .where(Board.gr_id == gr_id[i])
            .select()
        )
        if not exists_board:
            db.execute(delete(Group).where(Group.gr_id == gr_id[i]))
            db.execute(delete(GroupMember).where(GroupMember.gr_id == gr_id[i]))
        else:
            raise AlertException(f"{gr_id[i]} 게시판그룹에 속한 게시판이 존재합니다. (삭제불가)", 403)

    db.commit()

    url = "/admin/boardgroup_list"
    query_params = request.query_params
    return RedirectResponse(set_url_query_params(url, query_params), 303)


@router.get("/boardgroup_form")
async def boardgroup_form(request: Request):
    """
    게시판그룹 등록 폼
    """
    context = {"request": request, "group": None}
    return templates.TemplateResponse("boardgroup_form.html", context)


@router.get("/boardgroup_form/{gr_id}")
async def boardgroup_form(
    request: Request,
    db: db_session,
    gr_id: str = Path(...)
):
    """
    게시판그룹 수정 폼
    """
    group = db.get(Group, gr_id)
    if not group:
        raise AlertException(f"{gr_id} 게시판그룹이 존재하지 않습니다", 404)

    context = {
        "request": request,
        "group": group,
        "member_count": len(group.members)
    }
    return templates.TemplateResponse("boardgroup_form.html", context)


@router.post("/boardgroup_form_update", dependencies=[Depends(validate_token)])
async def boardgroup_form_update(
    request: Request,
    db: db_session,
    action: str = Form(...),
    gr_id: str = Form(...),
    form_data: GroupForm = Depends(),
):
    """
    게시판그룹 등록/수정 처리
    """
    if action == "w":
        existing_group = db.get(Group, gr_id)
        if existing_group:
            raise AlertException(f"{gr_id} 게시판그룹 아이디가 이미 존재합니다. (등록불가)", 400)

        new_group = Group(gr_id=gr_id, **form_data.__dict__)
        db.add(new_group)
        db.commit()

    elif action == "u":
        existing_group = db.get(Group, gr_id)
        if not existing_group:
            raise AlertException(f"{gr_id} 게시판그룹 아이디가 존재하지 않습니다. (수정불가)", 400)

        # 폼 데이터 반영 후 commit
        for field, value in form_data.__dict__.items():
            setattr(existing_group, field, value)
        db.commit()

    else:
        raise AlertException("잘못된 접근입니다.", 400)

    url = f"/admin/boardgroup_form/{gr_id}"
    query_params = request.query_params
    return RedirectResponse(set_url_query_params(url, query_params), 303)
