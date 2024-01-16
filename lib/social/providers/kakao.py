from typing import Optional, Tuple

from core.formclass import SocialProfile
from lib.social.social import SocialProvider


class Kakao(SocialProvider):
    """
    doc: https://developers.kakao.com/docs/latest/ko/kakaologin/common
    소셜 서비스에 필요한 메서드를 정의
    클래스 메서드만 사용하며 인스턴스를 생성하지 않는다.
    """

    provider_name = "kakao"

    @classmethod
    def register(cls, oauth_instance, client_id, client_secret):
        """
        소셜 서비스 인증 객체를 등록
        Args:
            oauth_instance (OAuth): OAuth 인증 객체
        """
        oauth_instance.register(
            name="kakao",
            access_token_url="https://kauth.kakao.com/oauth/token",
            access_token_params=None,
            authorize_url="https://kauth.kakao.com/oauth/authorize",
            authorize_params=None,
            client_kwargs={"scope": "account_email, profile_image"},
            api_base_url="https://kapi.kakao.com/v2/user/me",
            # api_base_url="https://kapi.kakao.com/v2/user/me?property_keys=['kakao_account.profile', 'kakao_account.email']",
        )
        oauth_instance.__getattr__(cls.provider_name).client_id = client_id
        if client_secret:
            oauth_instance.__getattr__(cls.provider_name).client_secret = client_secret

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
        response = await oauth_instance.__getattr__(cls.provider_name).get('me', token=auth_token)
        # raise http status code 200 아닐 때 발생
        response.raise_for_status()
        result = response.json()
        if result.get("id", "") == "":
            raise ValueError(result)

        return result

    @classmethod
    def convert_gnu_profile_data(cls, response) -> Tuple[str, SocialProfile]:
        """
        그누보드 소셜 서비스 프로필 데이터를 가져옴
        Args:
            response (dict): 소셜 서비스 응답 데이터
        Returns:
            SocialProfile
        """
        kakao_account = response.get("kakao_account", {})
        email_verify = kakao_account.get("is_email_verified", "")
        email = ""
        if email_verify:
            email = kakao_account.get("email", "")

        socialprofile = SocialProfile(
            mb_id=response.get("id", ""),
            provider=cls.provider_name,
            identifier=str(response.get("id", "")),
            profile_url="",
            photourl=response.get("properties", {}).get("thumbnail_image_url", ""),
            displayname=response.get("profile", {}).get("nickname", ""),
            disciption=""
        )

        return email, socialprofile

    @classmethod
    async def logout(cls, oauth_instance, auth_token):
        """
        소셜 서비스 토큰 revoke
        Args:
            oauth_instance (OAuth): OAuth 인증 객체
            auth_token (Dict): 소셜 서비스 토큰
        Docs:
            https://developers.kakao.com/docs/latest/ko/kakaologin/rest-api
        """
        await oauth_instance.__getattr__(cls.provider_name).post('https://kapi.kakao.com/v1/user/logout', token=auth_token)
