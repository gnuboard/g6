"""API Q&A 관련 기능 구현 모듈"""
from fastapi import HTTPException

from service.qa_service import QaConfigService, QaFileService, QaService


class QaConfigServiceAPI(QaConfigService):
    """
    API 요청에 사용되는 QaConfigServiceAPI 구현 클래스.  
    - 이 클래스는 API와 관련된 특정 예외 처리를 오버라이드하여 구현합니다.
    """

    def raise_exception(self, status_code: int = 400, detail: str = None, url: str = None):
        raise HTTPException(status_code=status_code, detail=detail)


class QaFileServiceAPI(QaFileService):
    """
    API 요청에 사용되는 QaFileService 구현 클래스.  
    - 이 클래스는 API와 관련된 특정 예외 처리를 오버라이드하여 구현합니다.
    """
    def raise_exception(self, status_code: int = 400, detail: str = None, url: str = None):
        raise HTTPException(status_code=status_code, detail=detail)


class QaServiceAPI(QaService):
    """
    API 요청에 사용되는 QaService 구현 클래스.  
    - 이 클래스는 API와 관련된 특정 예외 처리를 오버라이드하여 구현합니다.
    """

    def raise_exception(self, status_code: int = 400, detail: str = None, url: str = None):
        raise HTTPException(status_code=status_code, detail=detail)
