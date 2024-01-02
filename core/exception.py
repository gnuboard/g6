
from typing import Any, Dict, Optional

from fastapi import HTTPException

class AlertException(HTTPException):
    """스크립트 경고창 출력을 위한 예외 클래스
        - HTTPExceptiond에서 페이지 이동을 위한 url 매개변수를 추가적으로 받는다.

    Args:
        HTTPException (HTTPException): HTTP 예외 클래스
    """

    def __init__(self, detail: str = None, status_code: int = 200, url: str = None):
        self.status_code = status_code
        self.detail = detail
        self.url = url

class AlertCloseException(HTTPException):
    """스크립트 경고창 출력 및 윈도우 창 닫기를 위한 예외 클래스

    Args:
        HTTPException (HTTPException): HTTP 예외 클래스
    """

    def __init__(
        self,
        detail: Any = None,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        super().__init__(status_code=status_code, detail=detail, headers=headers)
