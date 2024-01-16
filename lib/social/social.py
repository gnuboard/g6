import logging
from typing import Optional, Tuple

from authlib.integrations.starlette_client import OAuth
from starlette.requests import Request

from core.exception import AlertException
from core.formclass import SocialProfile
from core.models import Config
from lib.social import providers

oauth = OAuth()


def register_social_provider(config: Config):
    """
    소셜 서비스 인증 객체를 등록
    Args:
        config (Config): 기본환경설정 객체
    Examples:
        서버 재시작 후 인증 객체가 등록되지 않아
        각 소셜서비스를 사용할 수 없는 경우가 있음.
    """
    if not config.cf_social_login_use:
        return

    available_providers = config.cf_social_servicelist.split(',')
    for provider_name in available_providers:

        # 소셜프로바이더 등록 - 등록된 클래스 찾아 호출
        provider_module_name = getattr(providers, f"{provider_name}")
        provider_class: SocialProvider = getattr(provider_module_name, f"{provider_name.capitalize()}")

        if provider_name == "naver":
            if config.cf_naver_clientid.strip() and config.cf_naver_secret.strip():
                provider_class.register(oauth, config.cf_naver_clientid.strip(), config.cf_naver_secret.strip())

        elif provider_name == 'kakao':
            if not config.cf_kakao_rest_key:
                # 카카오 client_secret 은 선택사항
                provider_class.register(oauth, config.cf_kakao_rest_key.strip(), config.cf_kakao_client_secret.strip())

        elif provider_name == 'google':
            if not (config.cf_google_clientid.strip() and config.cf_google_secret.strip()):
                provider_class.register(oauth, config.cf_google_clientid.strip(), config.cf_google_secret.strip())

        elif provider_name == 'twitter':
            if not (config.cf_twitter_key.strip() and config.cf_twitter_secret.strip()):
                provider_class.register(oauth, config.cf_twitter_key.strip(), config.cf_twitter_secret.strip())

        elif provider_name == 'facebook':
            if not (config.cf_facebook_appid.strip() and config.cf_facebook_secret.strip()):
                provider_class.register(oauth, config.cf_facebook_appid.strip(), config.cf_facebook_secret.strip())


async def get_social_login_token(provider_name, request: Request):
    """
    소셜 로그인 토큰 가져오기
    토큰 발행 오류시 None 리턴
    Args:
        provider_name (str): 소셜 서비스 제공자
        request (Request): starlette request
    Returns:
        Optional[auth_token] (dict): 토큰 딕셔너리
    Raises:
        token csrf mismatch, token expired
    """
    try:
        auth_token = await oauth.__getattr__(provider_name).authorize_access_token(request)
        if not auth_token:  # None
            raise ValueError
        return auth_token
    except Exception as e:
        logging.warning('social login token error', exc_info=e)
        # 토큰 불일치, 만료, 재사용 등 기존 인증 토큰 삭제
        if 'ss_social_access' in request.session:
            del request.session['ss_social_access']
        if 'ss_social_provider' in request.session:
            del request.session['ss_social_provider']

        remove_keys = []
        for key in request.session.keys():
            if key.startswith('_state'):
                remove_keys.append(key)
        for key in remove_keys:
            del request.session[key]


async def get_social_profile(auth_token, provider_name, request):
    """
    소셜 로그인 프로필 가져오기
    Args:
        auth_token (dict): 토큰 딕셔너리
        provider_name (str): 소셜 서비스 제공자
        request (Request): starlette request
    Returns:
        profile (dict): 프로필 딕셔너리
    Raises:
        AlertException (status_code=400) 알림 후 로그인페이지 이동
    """
    try:
        provider_module_name = getattr(providers, f"{provider_name}")
        provider_class: SocialProvider = getattr(provider_module_name, f"{provider_name.capitalize()}")
        return await provider_class.fetch_profile_data(oauth_instance=oauth, auth_token=auth_token)

    except Exception as e:
        logging.critical('social login profile get error', exc_info=e)
        raise AlertException(status_code=400, detail="유효하지 않은 요청입니다. 관리자에게 문의하십시오.",
                             url=request.url_for('login').__str__())


class SocialProvider:
    """
    소셜 서비스제공자의 oauth 인증에 필요한 메서드를 정의한 인터페이스
    클래스 메서드만 사용하며 인스턴스를 생성하지 않는다.
    """

    provider_name = ""

    @classmethod
    def register(cls, oauth_instance, client_id, client_secret):
        """
        소셜 서비스 인증 객체를 등록
        Args:
            oauth_instance (OAuth): OAuth 인증 객체
            client_id (str): 소셜 서비스 클라이언트 아이디
            client_secret (str): 소셜 서비스 클라이언트 시크릿
        """
        raise NotImplementedError()

    @classmethod
    async def fetch_profile_data(cls, oauth_instance, auth_token) -> Optional[object]:
        """
        소셜 서비스 프로필 데이터 가져오기
        Args:
            oauth_instance (OAuth): OAuth 인증 객체
            auth_token (Dict): 소셜 서비스 토큰
        Returns:
            SocialProfile
        """
        raise NotImplementedError()

    @classmethod
    def convert_gnu_profile_data(cls, response) -> Tuple[str, SocialProfile]:
        """
        그누보드 소셜 서비스 프로필 데이터를 가져옴
        Args:
            response (dict): 소셜 서비스 응답 데이터
        Returns:
            Tuple(email, SocialProfile)
        """
        raise NotImplementedError()

    @classmethod
    async def logout(cls, oauth_instance, auth_token):
        """
        소셜 서비스 토큰 revoke
        Args:
            oauth_instance (OAuth): OAuth 인증 객체
            auth_token (Dict): 소셜 서비스 토큰
        """
        raise NotImplementedError()
