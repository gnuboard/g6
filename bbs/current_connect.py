"""현재 접속자 Template Router"""
from typing_extensions import Annotated

from fastapi import APIRouter, Depends, Request

from core.template import UserTemplates
from lib.common import hide_ip_address
from service.current_connect_service import CurrentConnectService

router = APIRouter()
templates = UserTemplates()


@router.get("/current_connect")
async def current_connect(
    request: Request,
    service: Annotated[CurrentConnectService, Depends()],
):
    """현재 접속중인 사용자의 정보를 반환합니다."""
    logins = service.fetch_corrent_connects(per_page=100000)
    for login, member in logins:
        if not request.state.is_super_admin:
            login.lo_ip = hide_ip_address(login.lo_ip)

    context = {
        "request": request,
        "logins": logins,
    }
    return templates.TemplateResponse("/bbs/current_connect.html", context)
