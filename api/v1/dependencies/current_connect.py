"""현재 접속자 관련 의존성 함수를 정의합니다."""
from typing_extensions import Annotated
from fastapi import Depends, Request
from sqlalchemy.exc import ProgrammingError

from api.v1.dependencies.member import get_current_member_optional
from api.v1.service.current_connect import CurrentConnectServiceAPI
from core.models import Member
from lib.common import get_client_ip
from lib.member import is_super_admin


async def set_current_connect(
        request: Request,
        service: Annotated[CurrentConnectServiceAPI, Depends()],
        member: Annotated[Member, Depends(get_current_member_optional)]):
    """현재 접속자 정보 설정"""
    try:
        current_ip = get_client_ip(request)
        path = request.url.path
        mb_id = getattr(member, "mb_id", "")

        if not is_super_admin(request, mb_id):
            current_login = service.fetch_current_connect(current_ip)
            if current_login:
                service.update_current_connect(current_login, path, mb_id)
            else:
                service.create_current_connect(current_ip, path, mb_id)

        # 현재 로그인한 이력 삭제
        service.delete_current_connect()

    except ProgrammingError as e:
        print(e)
    