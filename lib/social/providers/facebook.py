from typing import Optional, Tuple

from core.formclass import SocialProfile
from lib.social.social import SocialProvider


class Facebook(SocialProvider):
    """소셜 로그인
    doc: https://developers.facebook.com/docs/permissions/
    https://developers.facebook.com/docs/graph-api/reference/user/#default-public-profile-fields
    클래스 메서드만 사용하며 인스턴스를 생성하지 않는다.
    """
    provider_name = "facebook"
    version = "v18.0"  # https://developers.facebook.com/docs/graph-api/changelog/versions

    @classmethod
    def register(cls, oauth_instance, client_id, client_secret):
        oauth_instance.register(
            name=cls.provider_name,
            access_token_url=f"https://graph.facebook.com/{cls.version}/oauth/access_token",
            access_token_params=None,
            authorize_url=f"https://www.facebook.com/{cls.version}/dialog/oauth",
            authorize_params=None,
            api_base_url=f"https://graph.facebook.com",
            client_kwargs={"scope": "email public_profile"},
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
        response = await oauth_instance.__getattr__(cls.provider_name).get(
            f"{cls.version}/me",
            token=auth_token
        )
        # raise http status code 200 아닐 때 발생
        response.raise_for_status()
        return response.json()

    @classmethod
    def convert_gnu_profile_data(cls, response) -> Tuple[str, SocialProfile]:
        """
        그누보드 MemberSocialProfiles 에서 사용하는 SocialProfile 형식으로 변환
        Args:
            response: 소셜 제공자에서 받은 프로필 정보
        """

        email = response.get("email", "")
        socialprofile = SocialProfile(
            mb_id=response.get("id", ""),
            provider=cls.provider_name,
            identifier=response.get("id", ""),
            profile_url=response.get("profile_image_url_https", ""),
            photourl=response.get("profile_image_url_https", ""),
            displayname=response.get("screen_name", ""),
            disciption=response.get("description", "")
        )

        return email, socialprofile

    @classmethod
    async def logout(cls, oauth_instance, auth_token):
        """
        소셜 서비스 토큰 revoke
        Args:
            oauth_instance (OAuth): OAuth 인증 객체
            auth_token (Dict): 소셜 서비스 토큰
        """
        # 페이스북은 토큰 무효화를 위한 엔드포인트를 제공하지 않음
        # 앱 접근 권한 삭제만 제공
        pass
