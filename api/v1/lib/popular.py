"""API 요청에 사용되는 인기 검색어 관련 기능 모듈"""
from fastapi import HTTPException

from service.popular_service import PopularService


class PopularServiceAPI(PopularService):
    """
    API 요청에 사용되는 PopularService 구현 클래스.  
    - 이 클래스는 API와 관련된 특정 예외 처리를 오버라이드하여 구현합니다.
    """
    def raise_exception(self,
                        status_code: int = 400,
                        detail: str = None,
                        url: str = None) -> None:
        raise HTTPException(status_code=status_code, detail=detail)
