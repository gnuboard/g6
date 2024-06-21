"""Google 소셜 로그인 관련 모듈"""
import httpx
from authlib.integrations.starlette_client import OAuth
from authlib.integrations.starlette_client.apps import StarletteOAuth2App

from core.formclass import SocialProfile
from lib.social.base import SocialProvider


class Google(SocialProvider):
    """Google 소셜 로그인 클래스
    
    Docs:
        https://developers.google.com/identity/sign-in/web/sign-in
    """
    provider_name = "google"

    API_URL = "https://www.googleapis.com"
    AUTH_URL = "https://accounts.google.com/o/oauth2"
    META_DATA_URL = "https://accounts.google.com/.well-known/openid-configuration"

    @classmethod
    def register(cls, oauth_instance: OAuth, client_id: str, client_secret: str):
        """OAuth 인스턴스에 Google을 등록합니다.

        Args:
            oauth_instance (OAuth): OAuth 인증 객체
            client_id (str): Google 클라이언트 ID
            client_secret (str): Google 클라이언트 시크릿
        """
        oauth_instance.register(
            name=cls.provider_name,
            access_token_url=f"{cls.AUTH_URL}/token",
            access_token_params=None,
            authorize_url=f"{cls.AUTH_URL}/auth",
            authorize_params=None,
            api_base_url=cls.API_URL,
            server_metadata_url=cls.META_DATA_URL,
            client_kwargs={
                'response_type': 'code',
                'token_endpoint_auth_method': 'client_secret_post',
                "scope": "email profile"
            },
        )
        google: StarletteOAuth2App = getattr(oauth_instance, cls.provider_name)
        google.client_id = client_id
        google.client_secret = client_secret

    @classmethod
    async def fetch_profile_data(cls, oauth_instance: OAuth, auth_token: dict) -> dict:
        """Google 로그인 후 프로필 정보를 가져옵니다.

        Args:
            oauth_instance (OAuth): OAuth 인증 객체
            auth_token (dict): 소셜 서비스 토큰

        Returns:
            dict: Google 프로필 정보

        Raises:
            HTTPStatusError: HTTP status code가 200이 아닐 때 발생
            ValueError: 응답 데이터가 없을 때 발생
        """
        google: StarletteOAuth2App = getattr(oauth_instance, cls.provider_name)
        response: httpx.Response = await google.get(
            url=f'{cls.API_URL}/oauth2/v3/userinfo',
            token=auth_token
        )

        response.raise_for_status()  # 응답 상태 코드 확인 & 예외 발생
        result: dict = response.json()

        if all(result.get(key) is None for key in ["sub", "id", "email"]):
            raise ValueError(result)

        return result

    @classmethod
    def extract_email(cls, response: dict) -> str:
        """Google 응답에서 이메일을 추출합니다.

        Args:
            response (dict): Google 프로필 응답 데이터

        Returns:
            str: 이메일 주소
        """
        return response.get("email", "")

    @classmethod
    def extract_social_profile(cls, response: dict) -> SocialProfile:
        """Google 응답에서 프로필 정보를 추출합니다.

        Args:
            response (dict): Google 프로필 응답 데이터

        Returns:
            SocialProfile: 소셜 프로필 객체
        """
        identifier = response.get("sub") or response.get("id", "")

        return SocialProfile(
            mb_id=response.get("sub", ""),
            provider=cls.provider_name,
            identifier=identifier,
            profile_url=response.get("picture", ""),
            photourl=response.get("picture", ""),
            displayname=response.get("nickname", ""),
            description=""
        )

    @classmethod
    async def logout(cls, oauth_instance: OAuth, auth_token: dict) -> None:
        """Google 로그인 인증 토큰을 취소합니다.

        Args:
            oauth_instance (OAuth): OAuth 인증 객체
            auth_token (dict): 소셜 서비스 토큰
        """
        access_token = auth_token.get('access_token', None)
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{cls.AUTH_URL}/revoke",
                params={'token': access_token},
                headers={'content-type': 'application/x-www-form-urlencoded'})
