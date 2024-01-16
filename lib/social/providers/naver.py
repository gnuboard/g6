from typing import Optional, Tuple

from core.formclass import SocialProfile
from lib.social.social import SocialProvider


class Naver(SocialProvider):
    """네이버 소셜 로그인
    doc: https://developers.naver.com/docs/login/api/
    클래스 메서드만 사용하며 인스턴스를 생성하지 않는다.
    """
    provider_name = "naver"

    @classmethod
    def register(cls, oauth_instance, client_id, client_secret):
        oauth_instance.register(
            name="naver",
            access_token_url="https://nid.naver.com/oauth2.0/token",
            access_token_params=None,
            authorize_url="https://nid.naver.com/oauth2.0/authorize",
            authorize_params=None,
            api_base_url="https://openapi.naver.com/v1/nid/me",
            client_kwargs={"scope": "user:email"},
        )
        oauth_instance.__getattr__(cls.provider_name).client_id = client_id
        oauth_instance.__getattr__(cls.provider_name).client_secret = client_secret

    @classmethod
    async def fetch_profile_data(cls, oauth_instance, auth_token) -> Optional[object]:
        """
        소셜 로그인 후 프로필 정보를 가져온다.
        Args:
            oauth_instance (OAuth): OAuth 인증 객체
            auth_token (Dict): 소셜 서비스 토큰
        Returns:
            SocialProfile
        Raises:
            HTTPException: HTTP status code 200 아닐 때 발생
            ValueError: 소셜 로그인 실패 시 발생
        """
        response = await oauth_instance.__getattr__(cls.provider_name).get('me', token=auth_token)
        # raise http status code 200 아닐 때 발생
        response.raise_for_status()
        result = response.json()
        if result.get("message", "") != "success":
            raise ValueError(result)

        return result

    @classmethod
    def convert_gnu_profile_data(cls, response) -> Tuple[str, SocialProfile]:
        """그누보드 MemberSocialProfiles 에서 사용하는 SocialProfile 형식으로 변환
        Args:
            response: 소셜 제공자에서 받은 프로필 정보
        """
        response = response.get("response", {})
        email = response.get("email", "")
        socialprofile = SocialProfile(
            mb_id=response.get("id", ""),
            provider=cls.provider_name,
            identifier=response.get("id", ""),
            profile_url="",
            photourl=response.get("profile_image", ""),
            displayname=response.get("nickname", ""),
            disciption=""
        )

        return email, socialprofile

    @classmethod
    async def logout(cls, oauth_instance, auth_token):
        """소셜 서비스 토큰 revoke
        Args:
            oauth_instance (OAuth): OAuth 인증 객체
            auth_token (Dict): 소셜 서비스 토큰
        """
        # https://developers.naver.com/docs/login/api/api.md  
        # 네이버 정책상 로그아웃이 별도로 없다.
        # 문서 3.2 항목에 있는 delete는 로그인 연동해제.
        pass
