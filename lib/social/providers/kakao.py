"""Kakao 소셜 로그인 관련 모듈"""
import httpx
from authlib.integrations.starlette_client import OAuth
from authlib.integrations.starlette_client.apps import StarletteOAuth2App

from core.formclass import SocialProfile
from lib.social.base import SocialProvider


class Kakao(SocialProvider):
    """Kakao 소셜 로그인

    Docs:
        https://developers.kakao.com/docs/latest/ko/kakaologin/common
    """
    provider_name = "kakao"

    API_URL = "https://kapi.kakao.com"
    AUTH_URL = "https://kauth.kakao.com/oauth"

    @classmethod
    def register(cls, oauth_instance: OAuth, client_id: str, client_secret: str):
        """OAuth 인스턴스에 Kakao를 등록합니다.

        Args:
            oauth_instance (OAuth): OAuth 인증 객체
            client_id (str): Kakao 클라이언트 ID
            client_secret (str): Kakao 클라이언트 시크릿
        """
        # api_url_params = "?property_keys=['kakao_account.profile', 'kakao_account.email']"
        api_url_params = ""
        oauth_instance.register(
            name="kakao",
            access_token_url=f"{cls.AUTH_URL}/token",
            access_token_params=None,
            authorize_url=f"{cls.AUTH_URL}/authorize",
            authorize_params=None,
            client_kwargs={
                "scope": "account_email, profile_image",
                "token_endpoint_auth_method": "client_secret_post"
            },
            api_base_url=f"{cls.API_URL}/v2/user/me{api_url_params}",
        )
        kakao: StarletteOAuth2App = getattr(oauth_instance, cls.provider_name)
        kakao.client_id = client_id
        if client_secret:
            kakao.client_secret = client_secret

    @classmethod
    async def fetch_profile_data(cls, oauth_instance: OAuth, auth_token: dict) -> dict:
        """Kakao 로그인 후 프로필 정보를 가져옵니다.

        Args:
            oauth_instance (OAuth): OAuth 인증 객체
            auth_token (dict): 소셜 서비스 토큰

        Returns:
            dict: Kakao 프로필 정보

        Raises:
            HTTPStatusError: HTTP status code가 200이 아닐 때 발생
            ValueError: 응답 데이터가 없을 때 발생
        """
        kakao: StarletteOAuth2App = getattr(oauth_instance, cls.provider_name)
        response: httpx.Response = await kakao.get('me', token=auth_token)
        response.raise_for_status()  # 응답 상태 코드 확인 & 예외 발생

        result: dict = response.json()
        if result.get("id", "") == "":
            raise ValueError(result)
        return result

    @classmethod
    def extract_email(cls, response: dict) -> str:
        """Kakao 응답에서 이메일을 추출합니다.

        Args:
            response (dict): Kakao 프로필 응답 데이터

        Returns:
            str: 이메일 주소
        """
        kakao_account = response.get("kakao_account", {})
        email_verify = kakao_account.get("is_email_verified", "")

        return kakao_account.get("email", "") if email_verify else ""

    @classmethod
    def extract_social_profile(cls, response: dict) -> SocialProfile:
        """Kakao 응답에서 프로필 정보를 추출합니다.

        Args:
            response (dict): Kakao 프로필 응답 데이터

        Returns:
            SocialProfile: 소셜 프로필 객체
        """
        return SocialProfile(
            mb_id=response.get("id", ""),
            provider=cls.provider_name,
            identifier=str(response.get("id", "")),
            profile_url="",
            photourl=response.get("profile", {}).get("thumbnail_image_url", ""),
            displayname=response.get("profile", {}).get("nickname", ""),
            description=""
        )

    @classmethod
    async def logout(cls, oauth_instance: OAuth, auth_token: dict) -> None:
        """Kakao 로그인 인증 토큰을 취소합니다.

        Args:
            oauth_instance (OAuth): OAuth 인증 객체
            auth_token (dict): 소셜 서비스 토큰

        Docs:
            https://developers.kakao.com/docs/latest/ko/kakaologin/rest-api#logout
        """
        kakao: StarletteOAuth2App = getattr(oauth_instance, cls.provider_name)
        await kakao.post(f'{cls.API_URL}/v1/user/logout', token=auth_token)
