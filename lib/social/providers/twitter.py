"""Twitter 소셜 로그인 관련 모듈"""
import base64

import httpx
from authlib.integrations.starlette_client import OAuth
from authlib.integrations.starlette_client.apps import StarletteOAuth2App

from core.formclass import SocialProfile
from lib.social.base import SocialProvider


class Twitter(SocialProvider):
    """Twitter 소셜 로그인 클래스

    Docs:
        https://developer.twitter.com/en/docs/authentication/oauth-2-0/application-only
    """
    provider_name = "twitter"

    API_URL = "https://api.twitter.com"
    AUTH_URL = "https://twitter.com/i/oauth2/authorize"

    @classmethod
    def register(cls, oauth_instance: OAuth, client_id: str, client_secret: str):
        """OAuth 인스턴스에 Twitter을 등록합니다.

        Args:
            oauth_instance (OAuth): OAuth 인증 객체
            client_id (str): Twitter 클라이언트 ID
            client_secret (str): Twitter 클라이언트 시크릿
        """
        oauth_instance.register(
            name="twitter",
            access_token_url=f"{cls.API_URL}/2/oauth2/token",
            access_token_params=None,
            authorize_url=cls.AUTH_URL,
            authorize_params=None,
            api_base_url=f"{cls.API_URL}/2/",
            client_kwargs={"scope": ""},
        )
        twitter: StarletteOAuth2App = getattr(oauth_instance, cls.provider_name)
        twitter.client_id = client_id
        twitter.client_secret = client_secret

    @classmethod
    async def fetch_profile_data(cls, oauth_instance: OAuth, auth_token: dict) -> dict:
        """Twitter 로그인 후 프로필 정보를 가져옵니다.

        Args:
            oauth_instance (OAuth): OAuth 인증 객체
            auth_token (dict): 소셜 서비스 토큰

        Returns:
            dict: Twitter 프로필 정보

        Raises:
            HTTPStatusError: HTTP status code가 200이 아닐 때 발생
        """
        twitter: StarletteOAuth2App = getattr(oauth_instance, cls.provider_name)
        response: httpx.Response = await twitter.get(
            url=f'{cls.API_URL}/2/users/me',
            token=auth_token
        )
        response.raise_for_status()  # 응답 상태 코드 확인 & 예외 발생

        return response.json()

    @classmethod
    def extract_email(cls, response: dict) -> str:
        """Twitter 응답에서 이메일을 추출합니다.

        Args:
            response (dict): Twitter 프로필 응답 데이터

        Returns:
            str: 이메일 주소
        """
        return response.get("email", "")

    @classmethod
    def extract_social_profile(cls, response: dict) -> SocialProfile:
        """Twitter 응답에서 프로필 정보를 추출합니다.

        Args:
            response (dict): Twitter 프로필 응답 데이터

        Returns:
            SocialProfile: 소셜 프로필 객체
        """
        return SocialProfile(
            mb_id=response.get("id", ""),
            provider=cls.provider_name,
            identifier=response.get("id", ""),
            profile_url=response.get("profile_image_url_https", ""),
            photourl=response.get("profile_image_url_https", ""),
            displayname=response.get("screen_name", ""),
            description=response.get("description", "")
        )

    @classmethod
    async def logout(cls, oauth_instance: OAuth, auth_token: dict) -> None:
        """Twitter 로그인 인증 토큰을 취소합니다.

        Args:
            oauth_instance (OAuth): OAuth 인증 객체
            auth_token (dict): 소셜 서비스 토큰
        """
        twitter: StarletteOAuth2App = getattr(oauth_instance, cls.provider_name)
        access_token = auth_token.get('access_token', None)
        client_id = twitter.client_id
        client_secret = twitter.client_secret

        async with httpx.AsyncClient() as client:
            bearer_token = base64.b64encode(f"{client_id}:{client_secret}".encode())
            headers = {
                "Authorization": f"Basic {bearer_token.decode()}",
                "Content-Type": "application/x-www-form-urlencoded",
            }
            await client.post(
                f"{cls.API_URL}/oauth2/invalidate_token",
                params={'access_token': access_token},
                headers=headers
            )
