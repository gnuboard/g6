"""현재 접속자 API Router"""
from typing_extensions import Annotated

from fastapi import APIRouter, Depends, Request

from core.models import Member
from lib.common import get_paging_info, hide_ip_address
from lib.member import is_super_admin
from api.v1.dependencies.member import get_current_member_optional
from api.v1.service.current_connect import CurrentConnectServiceAPI
from api.v1.models.current_connect import (
    CurrentConnectListRequest, CurrentConnectListResponse, CurrentConnectResponse
)
from api.v1.models.response import response_500


router = APIRouter()


@router.get("/members/current-connect",
            summary="현재 접속자 목록 조회",
            responses={**response_500})
async def read_member_points(
    request: Request,
    login_member: Annotated[Member, Depends(get_current_member_optional)],
    service: Annotated[CurrentConnectServiceAPI, Depends()],
    data: Annotated[CurrentConnectListRequest, Depends()]
) -> CurrentConnectListResponse:
    """현재 사이트에 접속 중인 회원들의 목록을 조회합니다."""
    only_member = data.only_member == "Y"
    total_records = service.fetch_total_records(only_member)
    paging_info = get_paging_info(data.page, data.per_page, total_records)
    connects = service.fetch_corrent_connects(only_member,
                                                  data.offset, data.per_page)
    # List[Tuple()] 형태의 데이터를 OnlineMemberListResponse로 변환
    logins = []
    for login, member in connects:
        logins.append(CurrentConnectResponse(
            lo_id=login.lo_id,
            lo_ip=(
                hide_ip_address(login.lo_ip)
                if not login_member or not is_super_admin(request, login_member.mb_id)
                else login.lo_ip
            ),
            mb_id=getattr(login, "mb_id", None),
            mb_nick=getattr(member, "mb_nick", None),
            mb_email=getattr(member, "mb_email", None),
            mb_homepage=getattr(member, "mb_homepage", None),
            lo_datetime=login.lo_datetime,
            lo_location=login.lo_location,
            lo_url=login.lo_url,
        ))

    return {
        "total_records": total_records,
        "total_pages": paging_info["total_pages"],
        "logins": logins,
    }
