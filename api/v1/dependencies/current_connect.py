"""현재 접속자 관련 의존성 함수를 정의합니다."""
from typing_extensions import Annotated
from fastapi import Depends, Request
from sqlalchemy.exc import ProgrammingError

from api.v1.auth import oauth2_optional
from core.database import db_session
from api.v1.dependencies.member import get_current_member_optional
from api.v1.service.current_connect import CurrentConnectServiceAPI
from api.v1.service.member import MemberServiceAPI
from lib.common import get_client_ip


async def set_current_connect(
        request: Request,
        db: db_session,
        service: Annotated[CurrentConnectServiceAPI, Depends()],
        member_service: Annotated[MemberServiceAPI, Depends()],
        ):
    """현재 접속자 정보 설정"""
    try:
        current_ip = get_client_ip(request)
        path = request.url.path

        token = await oauth2_optional(request)
        member = await get_current_member_optional(token, member_service)
        mb_id = getattr(member, "mb_id", "")
        cf_admin = getattr(request.state.config, "cf_admin", "admin")

        if cf_admin != mb_id:
            current_login = service.fetch_current_connect(current_ip)
            if current_login:
                service.update_current_connect(current_login, path, mb_id)
            else:
                service.create_current_connect(current_ip, path, mb_id)

        # 현재 로그인한 이력 삭제
        service.delete_current_connect()

        # 세션의 member 데이터를 데이터베이스와 동기화
        if member:
            db.refresh(member)

    except ProgrammingError as e:
        print(e)
