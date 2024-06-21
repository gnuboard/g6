"""Facebook 소셜 로그인 관련 모듈"""
import httpx
from authlib.integrations.starlette_client import OAuth
from authlib.integrations.starlette_client.apps import StarletteOAuth2App

from core.formclass import SocialProfile
from lib.social.base import SocialProvider


class Facebook(SocialProvider):
    """Facebook 소셜 로그인 클래스

    Docs:
        https://developers.facebook.com/docs/permissions/
        https://developers.facebook.com/docs/graph-api/reference/user/#default-public-profile-fields
    """
    provider_name = "facebook"
    version = "v20.0"  # https://developers.facebook.com/docs/graph-api/changelog/versions

    BASE_URL = "https://graph.facebook.com"
    AUTH_URL = "https://www.facebook.com"

    @classmethod
    def register(cls, oauth_instance: OAuth, client_id: str, client_secret: str):
        """OAuth 인스턴스에 Facebook을 등록합니다.

        Args:
            oauth_instance (OAuth): OAuth 인증 객체
            client_id (str): Facebook 클라이언트 ID
            client_secret (str): Facebook 클라이언트 시크릿
        """
        oauth_instance.register(
            name=cls.provider_name,
            access_token_url=f"{cls.BASE_URL}/{cls.version}/oauth/access_token",
            access_token_params=None,
            authorize_url=f"{cls.AUTH_URL}/{cls.version}/dialog/oauth",
            authorize_params=None,
            api_base_url=cls.BASE_URL,
            client_kwargs={"scope": "email public_profile"},
        )

        facebook: StarletteOAuth2App = getattr(oauth_instance, cls.provider_name)
        facebook.client_id = client_id
        facebook.client_secret = client_secret

    @classmethod
    async def fetch_profile_data(cls, oauth_instance: OAuth, auth_token: dict) -> dict:
        """Facebook 로그인 후 프로필 정보를 가져옵니다.

        Args:
            oauth_instance (OAuth): OAuth 인증 객체
            auth_token (dict): 소셜 서비스 토큰

        Returns:
            dict: Facebook 프로필 정보

        Raises:
            HTTPStatusError: HTTP status code가 200이 아닐 때 발생
        """
        facebook: StarletteOAuth2App = getattr(oauth_instance, cls.provider_name)
        response: httpx.Response = await facebook.get(
            url=f"{cls.version}/me?fields=id,name,email,picture,short_name",
            token=auth_token
        )
        response.raise_for_status()  # 응답 상태 코드 확인 & 예외 발생

        return response.json()

    @classmethod
    def extract_email(cls, response: dict) -> str:
        """Facebook 응답에서 이메일을 추출합니다.

        Args:
            response (dict): Facebook 프로필 응답 데이터

        Returns:
            str: 이메일 주소
        """
        return response.get("email", "")

    @classmethod
    def extract_social_profile(cls, response: dict) -> SocialProfile:
        """Facebook 응답에서 프로필 정보를 추출합니다.

        Args:
            response (dict): Facebook 프로필 응답 데이터

        Returns:
            SocialProfile: 소셜 프로필 객체
        """
        picture_data: dict = response.get("picture", {}).get("data", {})

        return SocialProfile(
            mb_id=response.get("id", ""),
            provider=cls.provider_name,
            identifier=response.get("id", ""),
            profile_url=picture_data.get("url", ""),
            photourl=picture_data.get("url", ""),
            displayname=response.get("short_name", ""),
            description=""
        )

    @classmethod
    async def logout(cls, oauth_instance: OAuth, auth_token: dict) -> None:
        """Facebook 로그인 인증 토큰을 취소합니다.

        Args:
            oauth_instance (OAuth): OAuth 인증 객체
            auth_token (dict): 소셜 서비스 토큰

        Notes:
            페이스북은 토큰 취소를 위한 엔드포인트를 제공하지 않음
        """
        return None
