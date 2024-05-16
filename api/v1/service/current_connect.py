"""API 현재 접속자 관련 기능 구현 모듈"""
from fastapi import HTTPException

from service.current_connect_service import CurrentConnectService


class CurrentConnectServiceAPI(CurrentConnectService):
    """
    API 요청에 사용되는 CurrentConnectService 구현 클래스.  
    - 이 클래스는 API와 관련된 특정 예외 처리를 오버라이드하여 구현합니다.
    """

    def raise_exception(self, status_code: int, detail: str = None):
        raise HTTPException(status_code=status_code, detail=detail)
