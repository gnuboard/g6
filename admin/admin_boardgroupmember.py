from fastapi import APIRouter, Depends, Path, Request, Form
from fastapi.responses import RedirectResponse
from sqlalchemy import desc
from sqlalchemy.orm import Session, aliased
from common.database import get_db
from common.models import Group, GroupMember, Member
from lib.common import *
from typing import List
from lib.plugin.service import get_admin_plugin_menus, get_all_plugin_module_names

router = APIRouter()
templates = AdminTemplates(directory=[ADMIN_TEMPLATES_DIR])
templates.env.globals["get_admin_plugin_menus"] = get_admin_plugin_menus
templates.env.globals["get_all_plugin_module_names"] = get_all_plugin_module_names


@router.get("/boardgroupmember_list/{gr_id}")
def boardgroupmember_list(
    request: Request,
    db: Session = Depends(get_db),
    gr_id: str = Path(...),
    search_params: dict = Depends(common_search_query_params)
):
    """
    그룹별 접근회원 목록
    """
    sfl = search_params['sfl']
    stx = search_params['stx']
    sst = search_params['sst']
    sod = search_params['sod']
    current_page = search_params['current_page']
    records_per_page = request.state.config.cf_page_rows

    # 그룹 정보
    group = db.get(Group, gr_id)
    if not group:
        raise AlertException(f"{gr_id} 그룹이 존재하지 않습니다.", 404)

    # 그룹회원 목록
    query = db.query(GroupMember).filter_by(gr_id = gr_id)
    # 검색 조건
    if sfl and stx:
        query = query.filter(getattr(GroupMember, sfl).like(f"%{stx}%"))
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
    total_count = query.count()
    # 최종 쿼리 결과를 가져옵니다.
    group_members = query.offset(offset).limit(records_per_page).all()
    
    for group_member in group_members:
        group_member.member = db.query(Member).filter_by(mb_id=group_member.mb_id).first()
        group_member.group_count = db.query(GroupMember).filter_by(mb_id=group_member.mb_id).count()

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
def board_form(
    request: Request,
    db: Session = Depends(get_db),
    mb_id: str = Path(...)
):
    """
    회원별 접근가능한 게시판 그룹 목록
    """   
    exists_member = db.query(Member).filter_by(mb_id = mb_id).first()
    if not exists_member:
        raise AlertException(f"{mb_id} 회원이 존재하지 않습니다.", 404)

    gm = aliased(GroupMember)
    gr = aliased(Group)
    query_groups = db.query(Group).filter_by(gr_use_access = 1).order_by(Group.gr_id)
    query_members = db.query(gm, gr).join(gr, gm.gr_id == gr.gr_id).filter(gm.mb_id == mb_id).order_by(desc(gm.gr_id))
    # 본인이 관리하는 그룹만 조회
    if not request.state.is_super_admin:
        query_groups = query_groups.filter_by(gr_admin = mb_id)
        query_members = query_members.filter(gr.gr_admin == mb_id)

    groups = query_groups.all()
    group_members = query_members.all()

    context = {
        "request": request,
        "member": exists_member,
        "groups": groups,
        "group_members": group_members,
    }
    return templates.TemplateResponse("boardgroupmember_form.html", context)


@router.post("/boardgroupmember_insert")
async def boardgroupmember_insert(
    request: Request,
    db: Session = Depends(get_db),
    token: str = Form(...),
    mb_id: str = Form(...),
    gr_id: str = Form(...),
):
    """
    접근가능한 그룹회원 추가
    """
    if not check_token(request, token):
        raise AlertException("토큰이 유효하지 않습니다", 403)

    exists_member = db.query(Member).filter_by(mb_id = mb_id).first()
    if not exists_member:
        raise AlertException(f"{mb_id} 회원이 존재하지 않습니다.", 404)

    exists_group = db.query(Group).filter_by(gr_id = gr_id).first()
    if not exists_group:
        raise AlertException(f"{gr_id} 그룹이 존재하지 않습니다.", 404)

    exists_group_member = db.query(GroupMember).filter_by(gr_id = gr_id, mb_id = mb_id).first()
    if exists_group_member:
        raise AlertException(f"{mb_id} 회원은 이미 {gr_id} 그룹에 등록되어 있습니다.", 409)

    group_member = GroupMember(
        gr_id = gr_id,
        mb_id = mb_id,
        gm_datetime = datetime.now(),
    )
    db.add(group_member)
    db.commit()
    
    return RedirectResponse(f"/admin/boardgroupmember_form/{mb_id}", status_code=303)


@router.post("/boardgroupmember_delete")
async def boardgroupmember_delete(
    request: Request,
    db: Session = Depends(get_db),
    token: str = Form(...),
    checks: List[int] = Form(None, alias="chk[]"),
    mb_id: str = Form(None),
    gr_id: str = Form(None),
):
    """
    접근가능한 그룹회원 삭제
    """
    if not check_token(request, token):
        raise AlertException("토큰이 유효하지 않습니다", 403)
    
    db.query(GroupMember).filter(GroupMember.gm_id.in_(checks)).delete()
    db.commit()

    if mb_id:
        return RedirectResponse(f"/admin/boardgroupmember_form/{mb_id}?{request.query_params}", status_code=303)
    else:
        return RedirectResponse(f"/admin/boardgroupmember_list/{gr_id}?{request.query_params}", status_code=303)

