"""API 요청에 사용되는 설문조사 관련 기능 모듈"""
from fastapi import HTTPException

from service.poll_service import PollService, ValidatePollService


class PollServiceAPI(PollService):
    """
    API 요청에 사용되는 PollService 구현 클래스.  
    - 이 클래스는 API와 관련된 특정 예외 처리를 오버라이드하여 구현합니다.
    """
    def raise_exception(self,
                        status_code: int = 400,
                        detail: str = None,
                        url: str = None) -> None:
        raise HTTPException(status_code=status_code, detail=detail)


class ValidatePollServiceAPI(ValidatePollService):
    """
    API 요청에 사용되는 ValidatePollService 구현 클래스.  
    - 이 클래스는 API와 관련된 특정 예외 처리를 오버라이드하여 구현합니다.
    """
    def raise_exception(self,
                        status_code: int = 400,
                        detail: str = None,
                        url: str = None) -> None:
        raise HTTPException(status_code=status_code, detail=detail)
