"""소셜 로그인 함수 모음"""
import logging
from typing import Optional

from authlib.integrations.starlette_client import OAuth
from authlib.integrations.starlette_client.apps import StarletteOAuth2App
from starlette.requests import Request

from core.exception import AlertException
from core.models import Config
from lib.social import providers
from lib.social.base import SocialProvider

oauth = OAuth()


def get_provider_client_key(provider: str, config: Config) -> tuple:
    """
    소셜 로그인 제공자의 client_id, secret_key 가져오기

    Args:
        provider (str): 소셜 서비스 제공자
        config (Config): 기본환경설정 객체

    Returns:
        tuple: client_id, secret_key

    Examples:
        client_id, secret_key = get_provider_client_key('naver', config)
    """
    if provider == "naver":
        client_id = getattr(config, "cf_naver_clientid", '')
        secret_key = getattr(config, "cf_naver_secret", '')
    elif provider == 'kakao':
        client_id = getattr(config, "cf_kakao_rest_key", '')
        secret_key = getattr(config, "cf_kakao_client_secret", '')
    elif provider == 'google':
        client_id = getattr(config, "cf_google_clientid", '')
        secret_key = getattr(config, "cf_google_secret", '')
    elif provider == 'twitter':
        client_id = getattr(config, "cf_twitter_key", '')
        secret_key = getattr(config, "cf_twitter_secret", '')
    elif provider == 'facebook':
        client_id = getattr(config, "cf_facebook_appid", '')
        secret_key = getattr(config, "cf_facebook_secret", '')

    return client_id.strip(), secret_key.strip()


def register_social_provider(provider: str, client_id: str, secret_key: str):
    """
    소셜 서비스 인증 객체를 등록

    Args:
        provider (str): 소셜 서비스 제공자
        client_id (str): 클라이언트 ID
        secret_key (str): 시크릿 키

    Examples:
        register_social_provider('naver', 'client_id', 'secret_key')
    """
    provider_class = load_provider_class(provider)
    provider_class.register(oauth, client_id, secret_key)


async def get_social_login_token(
        request: Request, provider: str) -> Optional[dict]:
    """
    소셜 로그인 토큰 가져오기

    Args:
        request (Request): starlette request
        provider (str): 소셜 서비스 제공자

    Returns:
        Optional[dict]: 토큰 딕셔너리

    Raises:
        HTTPException: token csrf mismatch, token expired 등
    """
    try:
        oauth2_app: StarletteOAuth2App = getattr(oauth, provider)
        auth_token = await oauth2_app.authorize_access_token(request)
        if not auth_token:
            raise ValueError("Failed to obtain auth token")

        request.session['ss_social_access'] = auth_token

        return auth_token
    except Exception as e:
        logging.warning('social login token error', exc_info=e)

        # 토큰 불일치, 만료, 재사용 등 기존 인증 토큰 삭제
        session_keys_to_remove = ['ss_social_access', 'ss_social_provider']
        session_keys_to_remove += [key for key in request.session.keys()
                                   if key.startswith('_state')]

        for key in session_keys_to_remove:
            request.session.pop(key, None)


async def get_social_profile(request: Request,
                             provider_class: SocialProvider,
                             auth_token: dict) -> Optional[object]:
    """
    소셜 로그인 프로필 가져오기
    Args:
        request (Request): starlette request
        provider_class (str): 소셜 서비스 클래스
        auth_token (dict): 토큰 딕셔너리

    Returns:
        profile (Optional[object]): 프로필 딕셔너리

    Raises:
        AlertException (status_code=400) 알림 후 로그인페이지 이동
    """
    try:
        return await provider_class.fetch_profile_data(oauth_instance=oauth,
                                                       auth_token=auth_token)
    except Exception as e:
        logging.critical('social login profile get error', exc_info=e)

        raise AlertException(detail="유효하지 않은 요청입니다. 관리자에게 문의하십시오.",
                             status_code=400,
                             url=request.url_for('login')) from e


def load_provider_class(provider: str):
    """
    소셜 로그인 제공자 클래스 가져오기
    """
    try:
        provider_module = getattr(providers, f"{provider}")
        class_name = provider.capitalize()
        provider_class: SocialProvider = getattr(provider_module, class_name)
    except ImportError as e:
        raise AlertException(status_code=500,
                             detail="프로바이더 모듈을 찾을 수 없습니다.") from e
    except AttributeError as e:
        raise AlertException(status_code=500,
                             detail="프로바이더 클래스를 찾을 수 없습니다.") from e
    return provider_class
