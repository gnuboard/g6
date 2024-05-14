"""회원 포인트 관리 Template Router"""
import uuid
from typing import List
from typing_extensions import Annotated

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from sqlalchemy import select, update, func

from core.database import db_session
from core.exception import AlertException
from core.models import Point, Member
from core.template import AdminTemplates
from lib.common import select_query, set_url_query_params
from lib.dependency.dependencies import common_search_query_params, validate_token
from lib.template_functions import get_paging
from service.member_service import MemberService
from service.point_service import PointService

router = APIRouter()
templates = AdminTemplates()

POINT_MENU_KEY = "200200"


@router.get("/point_list")
async def point_list(
    request: Request,
    db: db_session,
    search_params: dict = Depends(common_search_query_params)
):
    """
    포인트 목록
    """
    request.session["menu_key"] = POINT_MENU_KEY

    result = select_query(
        request,
        db,
        Point,
        search_params,
        same_search_fields=["mb_id"],
        default_sst="po_id",
        default_sod="desc",
    )

    # 회원아이디 검색시 회원정보 조회
    search_member = None
    if search_params['sfl'] == "mb_id" and search_params['stx']:
        search_member = db.scalar(
            select(Member)
            .where(Member.mb_id == search_params['stx'])
        )
    # 전체 포인트 합계
    sum_point = db.scalar(func.sum(Point.po_point)) or 0

    context = {
        "request": request,
        "config": request.state.config,
        "points": result['rows'],
        "total_count": result['total_count'],
        "search_member": search_member,
        "sum_point": int(sum_point),
        "paging": get_paging(request, search_params['current_page'], result['total_count']),
    }
    return templates.TemplateResponse("point_list.html", context)


@router.post("/point_update", dependencies=[Depends(validate_token)])
async def point_update(
    request: Request,
    db: db_session,
    service: Annotated[PointService, Depends()],
    mb_id: str = Form(default=""),
    po_content: str = Form(default=""),
    po_point: str = Form(default="0"),
    po_expire_term: int = Form(default=0),
):
    """
    포인트 지급/차감
    """
    try:
        po_point = int(po_point)
    except ValueError:
        raise AlertException(f"{po_point} : 포인트를 숫자(정수)로 입력하세요.", 400)

    exist_member = db.scalar(select(Member).filter_by(mb_id=mb_id))
    if not exist_member:
        raise AlertException(f"{mb_id} : 회원이 존재하지 않습니다.", 400)

    if (po_point < 0) and ((po_point * -1) > exist_member.mb_point):
        raise AlertException(f"{mb_id} : 포인트를 깍는 경우 현재 포인트보다 작으면 안됩니다.", 400)

    # 포인트 내역 저장
    rel_action = exist_member.mb_id + '-' + str(uuid.uuid4())
    service.save_point(mb_id, po_point,
                       po_content, "@passive",
                       mb_id, rel_action, po_expire_term)

    url = "/admin/point_list"
    query_params = request.query_params
    return RedirectResponse(set_url_query_params(url, query_params), 303)


@router.post("/point_list_delete", dependencies=[Depends(validate_token)])
async def point_list_delete(
    request: Request,
    db: db_session,
    member_service: Annotated[MemberService, Depends()],
    service: Annotated[PointService, Depends()],
    checks: List[int] = Form(None, alias="chk[]"),
    po_id: List[int] = Form(None, alias="po_id[]"),
):
    """
    포인트 내역 일괄 삭제
    """
    for i in checks:
        point = db.get(Point, po_id[i])
        if not point:
            continue

        if point.po_point < 0:
            abs_po_point = abs(point.po_point)

            if point.po_rel_table == "@expire":
                service.delete_expire_point(point.mb_id, abs_po_point)
            else:
                service.delete_use_point(point.mb_id, abs_po_point)
        elif point.po_use_point > 0:
            service.insert_use_point(point.mb_id, point.po_use_point, point.po_id)

        # 포인트 내역 삭제
        db.delete(point)
        db.commit()

        # po_mb_point에 반영
        db.execute(
            update(Point)
            .values(po_mb_point=Point.po_mb_point - point.po_point)
            .where(Point.mb_id == point.mb_id, Point.po_id > point.po_id)
        )
        db.commit()

        # 회원 포인트 갱신
        sum_point = service.get_total_point(point.mb_id)
        member_service.update_member_point(point.mb_id, sum_point)

    url = "/admin/point_list"
    query_params = request.query_params
    return RedirectResponse(set_url_query_params(url, query_params), 303)
