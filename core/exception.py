
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.templating import Jinja2Templates
from starlette.templating import _TemplateResponse

from core.template import TEMPLATES_DIR, theme_asset


class AlertException(HTTPException):
    """스크립트 경고창 출력을 위한 예외 클래스
    - HTTPExceptiond에서 페이지 이동을 위한 url 매개변수를 추가적으로 받는다.
    """

    def __init__(self, detail: str = None, status_code: int = 200, url: str = None):
        self.status_code = status_code
        self.detail = detail
        self.url = url


class AlertCloseException(HTTPException):
    """스크립트 경고창 출력 및 윈도우 창 닫기를 위한 예외 클래스"""

    def __init__(
        self,
        detail: Any = None,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        super().__init__(status_code=status_code, detail=detail, headers=headers)


def regist_core_exception_handler(app: FastAPI) -> None:
    """애플리케이션 인스턴스에 예외처리 핸들러를 등록합니다."""

    @app.exception_handler(AlertException)
    async def alert_exception_handler(
            request: Request, exc: AlertException):
        """AlertException 예외처리 handler 등록"""
        context = {
            "request": request,
            "errors": exc.detail,
            "url": exc.url
        }
        return template_response("alert.html", context, exc.status_code)

    @app.exception_handler(AlertCloseException)
    async def alert_close_exception_handler(
            request: Request, exc: AlertCloseException):
        """AlertCloseException 예외처리 handler 등록"""
        context = {
            "request": request,
            "errors": exc.detail
        }
        return template_response("alert_close.html", context, exc.status_code)


def template_response(
        template_html: str,
        context: Dict[str, Any],
        status_code: int = 200) -> _TemplateResponse:
    """템플릿 응답 객체를 반환합니다.

    Args:
        template_html (_type_): 템플릿 파일명
        context (_type_): context 객체
        status_code (int, optional): HTTP 상태코드. Defaults to 200.

    Returns:
        _TemplateResponse: 템플릿 응답 객체
    """
    # 새로운 템플릿 응답 객체를 생성합니다.
    # - UserTemplates, AdminTemplates 클래스는 기본 컨텍스트 설정 시 DB를 조회하는데,
    #   처음 설치 시에는 DB가 없으므로 새로운 템플릿 응답 객체를 생성합니다.
    template = Jinja2Templates(directory=TEMPLATES_DIR)
    template.env.globals["theme_asset"] = theme_asset
    return template.TemplateResponse(
        name=template_html,
        context=context,
        status_code=status_code
    )
