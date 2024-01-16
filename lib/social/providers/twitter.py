import base64
from typing import Optional, Tuple

import httpx

from core.formclass import SocialProfile
from lib.social.social import SocialProvider


class Twitter(SocialProvider):
    """소셜 로그인
    doc: https://developer.twitter.com/en/docs/authentication/oauth-2-0/application-only
    클래스 메서드만 사용하며 인스턴스를 생성하지 않는다.
    """
    provider_name = "twitter"

    @classmethod
    def register(cls, oauth_instance, client_id, client_secret):
        oauth_instance.register(
            name="twitter",
            access_token_url="https://api.twitter.com/2/oauth2/token",
            access_token_params=None,
            authorize_url="https://twitter.com/i/oauth2/authorize",
            authorize_params=None,
            api_base_url="https://api.twitter.com/2/",
            client_kwargs={"scope": ""},
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
            'https://api.twitter.com/2/users/me',
            token=auth_token
        )
        # raise http status code 200 아닐 때 발생
        response.raise_for_status()
        result = response.json()
        return result

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
        access_token = auth_token.get('access_token', None)
        client_id = oauth_instance.__getattr__(cls.provider_name).client_id
        client_secret = oauth_instance.__getattr__(cls.provider_name).client_secret

        async with httpx.AsyncClient() as client:
            bearer_token = base64.b64encode(f"{client_id}:{client_secret}".encode())
            headers = {
                "Authorization": f"Basic {bearer_token.decode()}",
                "Content-Type": "application/x-www-form-urlencoded",
            }
            await client.post(
                'https://api.twitter.com/oauth2/invalidate_token',
                params={'access_token': access_token},
                headers=headers
            )
