from fastapi import APIRouter, Request

from common.database import db_session
from common.models import Point
from lib.common import *

router = APIRouter()
templates = UserTemplates()
templates.env.filters["datetime_format"] = datetime_format


@router.get("/point")
async def point_list(
    request: Request,
    db: db_session,
    current_page: int = Query(default=1, alias="page")
):
    """
    포인트 목록
    """
    member = request.state.login_member
    if not member:
        raise AlertCloseException("로그인 후 이용 가능합니다.", 403)

    # 스크랩 목록 조회 쿼리
    query = (
        select()
        .where(Point.mb_id == member.mb_id)
        .order_by(desc(Point.po_id))
    )

    # 페이징 처리
    records_per_page = request.state.config.cf_page_rows
    total_records = db.scalar(query.add_columns(func.count(Point.po_id)))
    offset = (current_page - 1) * records_per_page
    points = db.scalars(
        query.add_columns(Point).offset(offset).limit(records_per_page)
    ).all()

    sum_positive = 0
    sum_negative = 0
    for point in points:
        # 포인트 정보
        point.num = total_records - offset - (points.index(point))
        point.is_positive = point.po_point > 0
        # 포인트 합계
        if point.is_positive:
            sum_positive += point.po_point
        else:
            sum_negative += point.po_point

    context = {
        "request": request,
        "points": points,
        "sum_positive": sum_positive,
        "sum_negative": sum_negative,
        "total_records": total_records,
        "page": current_page,
        "paging": get_paging(request, current_page, total_records),
    }
    return templates.TemplateResponse(f"{request.state.device}/bbs/point_list.html", context)
