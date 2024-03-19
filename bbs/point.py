from typing_extensions import Annotated

from fastapi import APIRouter, Depends, Query, Request

from core.template import UserTemplates
from lib.common import *
from lib.dependencies import get_login_member
from lib.point import PointService
from lib.template_functions import get_paging

router = APIRouter()
templates = UserTemplates()


@router.get("/point")
async def point_list(
    request: Request,
    member: Annotated[Member, Depends(get_login_member)],
    point_service: Annotated[PointService, Depends()],
    current_page: int = Query(default=1, alias="page")
):
    """
    포인트 목록
    """
    records_per_page = request.state.config.cf_page_rows

    total_records = point_service.fetch_total_records(member)
    paging_info = get_paging_info(current_page, records_per_page, total_records)
    points = point_service.fetch_points(member, paging_info["offset"], records_per_page)

    sum_positive = 0
    sum_negative = 0
    for point in points:
        # 포인트 정보
        point.num = total_records - paging_info["offset"] - (points.index(point))
        # 포인트 합계
        if point.po_point > 0:
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
    return templates.TemplateResponse("/bbs/point_list.html", context)
