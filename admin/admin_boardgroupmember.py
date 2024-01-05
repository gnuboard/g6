from fastapi import APIRouter, Depends, Path, Request, Form
from fastapi.responses import RedirectResponse
from sqlalchemy import desc
from typing import List

from core.database import db_session
from core.exception import AlertException
from core.models import Group, GroupMember, Member
from core.template import AdminTemplates
from lib.common import *
from lib.dependencies import common_search_query_params, validate_token
from lib.template_functions import get_paging

router = APIRouter()
templates = AdminTemplates()


@router.get("/boardgroupmember_list/{gr_id}")
async def boardgroupmember_list(
    request: Request,
    db: db_session,
    gr_id: str = Path(...),
    search_params: dict = Depends(common_search_query_params)
):
    """
    그룹별 접근회원 목록
    """
    config = request.state.config

    sfl = search_params['sfl']
    stx = search_params['stx']
    sst = search_params['sst']
    sod = search_params['sod']
    current_page = search_params['current_page']
    records_per_page = getattr(config, "cf_page_rows", 10)

    # 그룹 정보
    group = db.get(Group, gr_id)
    if not group:
        raise AlertException(f"{gr_id} 그룹이 존재하지 않습니다.", 404)

    # 그룹회원 목록
    query = select().where(GroupMember.gr_id == gr_id)
    # 검색 조건
    if sfl and stx:
        query = query.where(getattr(GroupMember, sfl).like(f"%{stx}%"))
    # 정렬 조건
    if sst:
        if sod == "desc":
            query = query.order_by(desc(getattr(GroupMember, sst)))
        else:
            query = query.order_by(getattr(GroupMember, sst))
    else:
        query = query.order_by(GroupMember.gm_id)

    # 페이지 번호에 따른 offset 계산
    offset = (current_page - 1) * records_per_page
    # 전체 레코드 개수 계산
    total_count = db.scalar(query.add_columns(func.count(GroupMember.gm_id)).order_by(None))
    # 최종 쿼리 결과를 가져옵니다.
    group_members = db.scalars(
        query.add_columns(GroupMember).offset(offset).limit(records_per_page)
    ).all()

    for group_member in group_members:
        group_member.member_info = group_member.member
        group_member.group_count = len(group_member.member.groups)

    context = {
        "request": request,
        "group": group,
        "group_members": group_members,
        "total_count": total_count,
        "current_page": current_page,
        "paging": get_paging(request, current_page, total_count, records_per_page),
    }
    return templates.TemplateResponse("boardgroupmember_list.html", context)


@router.get("/boardgroupmember_form/{mb_id}")
async def board_form(
    request: Request,
    db: db_session,
    mb_id: str = Path(...)
):
    """
    회원별 접근가능한 게시판 그룹 목록
    """
    exists_member = db.scalar(select(Member).filter_by(mb_id=mb_id))
    if not exists_member:
        raise AlertException(f"{mb_id} 회원이 존재하지 않습니다.", 404)

    query_groups = select(Group).filter_by(gr_use_access = 1).order_by(Group.gr_id)
    query_allow_groups = select(Group, GroupMember).join(GroupMember).where(GroupMember.mb_id == mb_id).order_by(desc(Group.gr_id))
    # 본인이 관리하는 그룹만 조회
    if not request.state.is_super_admin:
        query_groups = query_groups.filter_by(gr_admin=mb_id)
        query_allow_groups = query_allow_groups.where(Group.gr_admin == mb_id)

    groups = db.scalars(query_groups).all()
    allow_groups = db.execute(query_allow_groups).all()

    context = {
        "request": request,
        "member": exists_member,
        "groups": groups,
        "allow_groups": allow_groups,
    }
    return templates.TemplateResponse("boardgroupmember_form.html", context)


@router.post("/boardgroupmember_insert", dependencies=[Depends(validate_token)])
async def boardgroupmember_insert(
    request: Request,
    db: db_session,
    mb_id: str = Form(...),
    gr_id: str = Form(...),
):
    """
    접근가능한 그룹회원 추가
    """
    exists_member = db.scalar(select(Member).filter_by(mb_id=mb_id))
    if not exists_member:
        raise AlertException(f"{mb_id} 회원이 존재하지 않습니다.", 404)

    exists_group = db.get(Group, gr_id)
    if not exists_group:
        raise AlertException(f"{gr_id} 그룹이 존재하지 않습니다.", 404)

    exists_group_member = db.scalar(select(GroupMember).filter_by(mb_id = mb_id, gr_id = gr_id))
    if exists_group_member:
        raise AlertException(f"{mb_id} 회원은 이미 {gr_id} 그룹에 등록되어 있습니다.", 409)

    group_member = GroupMember(
        gr_id=gr_id,
        mb_id=mb_id,
        gm_datetime=datetime.now(),
    )
    db.add(group_member)
    db.commit()

    return RedirectResponse(f"/admin/boardgroupmember_form/{mb_id}", status_code=303)


@router.post("/boardgroupmember_delete", dependencies=[Depends(validate_token)])
async def boardgroupmember_delete(
    request: Request,
    db: db_session,
    checks: List[int] = Form(None, alias="chk[]"),
    mb_id: str = Form(None),
    gr_id: str = Form(None),
):
    """
    접근가능한 그룹회원 삭제
    """
    db.execute(delete(GroupMember).where(GroupMember.gm_id.in_(checks)))
    db.commit()

    if mb_id:
        url = f"/admin/boardgroupmember_form/{mb_id}"
    else:
        url = f"/admin/boardgroupmember_list/{gr_id}"
    query_params = request.query_params
    return RedirectResponse(set_url_query_params(url, query_params), 303)
