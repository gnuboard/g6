"""Naver 소셜 로그인 관련 모듈"""
import httpx
from authlib.integrations.starlette_client import OAuth
from authlib.integrations.starlette_client.apps import StarletteOAuth2App

from core.formclass import SocialProfile
from lib.social.base import SocialProvider


class Naver(SocialProvider):
    """네이버 소셜 로그인 클래스

    Docs:
        https://developers.naver.com/docs/login/api/
    """
    provider_name = "naver"

    API_URL = "https://openapi.naver.com"
    AUTH_URL = "https://nid.naver.com/oauth2.0"

    @classmethod
    def register(cls, oauth_instance: OAuth, client_id: str, client_secret: str):
        """OAuth 인스턴스에 Naver를 등록합니다.

        Args:
            oauth_instance (OAuth): OAuth 인증 객체
            client_id (str): Naver 클라이언트 ID
            client_secret (str): Naver 클라이언트 시크릿
        """
        oauth_instance.register(
            name=cls.provider_name,
            access_token_url=f"{cls.AUTH_URL}/token",
            access_token_params=None,
            authorize_url=f"{cls.AUTH_URL}/authorize",
            authorize_params=None,
            api_base_url=f"{cls.API_URL}/v1/nid/me",
            client_kwargs={"scope": "user:email"},
        )
        naver: StarletteOAuth2App = getattr(oauth_instance, cls.provider_name)
        naver.client_id = client_id
        naver.client_secret = client_secret

    @classmethod
    async def fetch_profile_data(cls, oauth_instance: OAuth, auth_token: dict) -> dict:
        """Naver 로그인 후 프로필 정보를 가져옵니다.

        Args:
            oauth_instance (OAuth): OAuth 인증 객체
            auth_token (dict): 소셜 서비스 토큰

        Returns:
            dict: Naver 프로필 정보

        Raises:
            HTTPStatusError: HTTP status code가 200이 아닐 때 발생
            ValueError: 응답 데이터가 없을 때 발생
        """
        naver: StarletteOAuth2App = getattr(oauth_instance, cls.provider_name)
        response: httpx.Response = await naver.get('me', token=auth_token)
        response.raise_for_status()  # 응답 상태 코드 확인 & 예외 발생

        result: dict = response.json()
        if result.get("resultcode", "") != "00":
            raise ValueError(result)
        return result

    @classmethod
    def extract_email(cls, response: dict) -> str:
        """Naver 응답에서 이메일을 추출합니다.

        Args:
            response (dict): Naver 프로필 응답 데이터

        Returns:
            str: 이메일 주소
        """
        response = response.get("response", {})
        return response.get("email", "")

    @classmethod
    def extract_social_profile(cls, response: dict) -> SocialProfile:
        """Naver 응답에서 프로필 정보를 추출합니다.

        Args:
            response (dict): Naver 프로필 응답 데이터

        Returns:
            SocialProfile: 소셜 프로필 객체
        """
        response = response.get("response", {})
        return SocialProfile(
            mb_id=response.get("id", ""),
            provider=cls.provider_name,
            identifier=response.get("id", ""),
            profile_url="",
            photourl=response.get("profile_image", ""),
            displayname=response.get("nickname", ""),
            description=""
        )

    @classmethod
    async def logout(cls, oauth_instance: OAuth, auth_token: dict) -> None:
        """Naver 로그인 인증 토큰을 취소합니다.

        Args:
            oauth_instance (OAuth): OAuth 인증 객체
            auth_token (Dict): 소셜 서비스 토큰
        
        Notes:
            네이버 정책상 로그아웃이 별도로 없음.

        Docs:
            https://developers.naver.com/docs/login/api/api.md
        """
        return None
