"""포인트 Template Router"""
from typing_extensions import Annotated

from fastapi import APIRouter, Depends, Query, Request

from core.models import Member
from core.template import UserTemplates
from lib.common import get_paging_info
from lib.dependency.auth import get_login_member
from lib.template_functions import get_paging
from service.point_service import PointService

router = APIRouter()
templates = UserTemplates()


@router.get("/point")
async def point_list(
    request: Request,
    point_service: Annotated[PointService, Depends()],
    member: Annotated[Member, Depends(get_login_member)],
    current_page: Annotated[int, Query(alias="page")] = 1
):
    """
    포인트 목록
    """
    records_per_page = request.state.config.cf_page_rows

    total_records = point_service.fetch_total_records(member)
    paging_info = get_paging_info(current_page, records_per_page, total_records)
    points = point_service.fetch_points(member, paging_info["offset"], records_per_page)

    for point in points:
        point.num = total_records - paging_info["offset"] - (points.index(point))
        point.is_positive = point.po_point > 0

    context = {
        "request": request,
        "points": points,
        "sum_points": point_service.calculate_sum(points),
        "total_records": total_records,
        "page": current_page,
        "paging": get_paging(request, current_page, total_records),
    }
    return templates.TemplateResponse("/bbs/point_list.html", context)
