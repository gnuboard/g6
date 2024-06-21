"""소셜 로그인 관련 유효성 검사를 위한 의존성 함수를 정의합니다."""
from fastapi import Query, Request
from typing_extensions import Annotated

from core.exception import AlertException, JSONException
from core.models import Config


def validate_use_social_login(request: Request):
    """
    소셜 로그인 사용 여부 확인
    """
    config: Config = request.state.config
    if not getattr(config, "cf_social_login_use", False):
        raise AlertException(detail="소셜 로그인이 비활성화 상태입니다.", status_code=400)


def get_provider_from_query(
    request: Request,
    provider: Annotated[str, Query()] = "",
):
    """
    Query String에서 세션에서 소셜 로그인 제공자 가져오기
    """
    return _validate_provider(request, provider, AlertException)


def get_provider_from_session(request: Request):
    """
    세션에서 소셜 로그인 제공자 가져오기
    """
    provider = request.session.get("ss_social_provider")
    return _validate_provider(request, provider, AlertException)


def get_provider_from_link(
    request: Request,
    provider: Annotated[str, Query()] = ""
):
    """
    회원정보수정 > 소셜 로그인 연결 > 제공자 가져오기
    """
    return _validate_provider(request, provider, JSONException)


def get_auth_token_from_session(request: Request):
    """
    세션에서 소셜 로그인 토큰 가져오기
    """
    auth_token = request.session.get("ss_social_access")
    if not auth_token:
        raise AlertException("유효하지 않은 인증 정보입니다.", 400, request.url_for('login'))

    return auth_token


def _validate_provider(
    request: Request,
    provider: str,
    exception_class: Exception,
) -> str:
    """
    소셜 로그인 제공자 유효성 검사
    """
    config = request.state.config
    social_service_list = getattr(config, 'cf_social_servicelist', "").split(",")

    if not provider or provider not in social_service_list:
        message = f"사용하지 않는 소셜 서비스 입니다. {provider}"
        status_code = 404
        if exception_class == JSONException:
            raise exception_class(message=message, status_code=status_code)
        raise exception_class(detail=message, status_code=status_code)

    return provider
