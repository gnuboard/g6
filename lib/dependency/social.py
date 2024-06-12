"""소셜 로그인 관련 유효성 검사를 위한 의존성 함수를 정의합니다."""
from fastapi import Query, Request
from typing_extensions import Annotated

from core.exception import AlertException
from core.models import Config


def validate_use_social_login(
    request: Request,
):
    """
    소셜 로그인 사용 여부 확인
    """
    config: Config = request.state.config
    if not getattr(config, "cf_social_login_use", False):
        raise AlertException(detail="소셜 로그인이 비활성화 상태입니다.", status_code=400)


def get_provider_by_query(
    request: Request,
    provider: Annotated[str, Query()] = None,
):
    """
    소셜 로그인 제공자 유효성 검사
    """
    config: Config = request.state.config
    social_list = getattr(config, "cf_social_servicelist", '').split(',')

    if not provider or provider not in social_list:
        raise AlertException(detail="사용하지 않는 서비스 입니다.", status_code=400)
    return provider


def get_provider_by_session(
    request: Request,
):
    """
    세션에서 소셜 로그인 제공자 가져오기
    """
    provider = request.session.get("ss_social_provider")
    if not provider:
        raise AlertException(detail="유효하지 않은 요청입니다.", status_code=400)

    return provider


def get_auth_token_by_session(
    request: Request,
):
    """
    세션에서 소셜 로그인 토큰 가져오기
    """
    auth_token = request.session.get("ss_social_access")
    if not auth_token:
        raise AlertException(detail="유효하지 않은 인증 정보입니다.",
                             status_code=400,
                             url=request.url_for('login'))

    return auth_token
