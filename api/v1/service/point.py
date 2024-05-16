from typing_extensions import Annotated
from fastapi import Depends, HTTPException, Request

from api.v1.service.member import MemberServiceAPI
from core.database import db_session
from service.point_service import PointService


class PointServiceAPI(PointService):
    """
    API 요청에 사용되는 PointService 구현 클래스.  
    - 이 클래스는 API와 관련된 특정 예외 처리를 오버라이드하여 구현합니다.
    """
    def __init__(
            self,
            request: Request,
            db: db_session,
            member_service: Annotated[MemberServiceAPI, Depends()]
        ):
        super().__init__(request, db, member_service)

    def raise_exception(self, status_code: int, detail: str = None):
        raise HTTPException(status_code=status_code, detail=detail)
