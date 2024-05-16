"""API 스크랩 관련 기능 구현 모듈"""
from fastapi import HTTPException

from service.scrap_service import ScrapService, ValidateScrapService


class ScrapServiceAPI(ScrapService):
    """
    API 요청에 사용되는 ScrapService 구현 클래스.  
    - 이 클래스는 API와 관련된 특정 예외 처리를 오버라이드하여 구현합니다.
    """

    def raise_exception(self, status_code: int, detail: str = None, url: str = None):
        raise HTTPException(status_code=status_code, detail=detail)


class ValidateScrapServiceAPI(ValidateScrapService):
    """
    API 요청에 사용되는 ValidateScrapService 구현 클래스.  
    - 이 클래스는 API와 관련된 특정 예외 처리를 오버라이드하여 구현합니다.
    """

    def raise_exception(self, status_code: int, detail: str = None, url: str = None):
        raise HTTPException(status_code=status_code, detail=detail)
