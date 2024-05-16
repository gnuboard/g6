"""포인트 API Router"""
from typing_extensions import Annotated

from fastapi import APIRouter, Depends

from core.models import Member
from lib.common import get_paging_info

from api.v1.dependencies.member import get_current_member
from api.v1.models.response import response_500
from api.v1.models.pagination import PagenationRequest
from api.v1.models.point import PointListResponse
from api.v1.service.point import PointServiceAPI

router = APIRouter()


@router.get("/points",
            summary="회원 포인트 내역 목록 조회",
            responses={**response_500})
async def read_member_points(
    service: Annotated[PointServiceAPI, Depends()],
    member: Annotated[Member, Depends(get_current_member)],
    data: Annotated[PagenationRequest, Depends()]
) -> PointListResponse:
    """JWT 토큰을 통해 인증된 회원의 포인트 내역을 조회합니다."""
    total_records = service.fetch_total_records(member)
    paging_info = get_paging_info(data.page, data.per_page, total_records)
    points = service.fetch_points(member, data.offset, data.per_page)

    return {
        "total_records": total_records,
        "total_pages": paging_info["total_pages"],
        "total_points": member.mb_point,
        "page_sum_points": service.calculate_sum(points),
        "points": points
    }
