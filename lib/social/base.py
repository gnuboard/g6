import abc
from typing import Optional, Tuple

from core.formclass import SocialProfile


class SocialProvider(metaclass=abc.ABCMeta):
    """
    소셜 서비스제공자의 oauth 인증에 필요한 메서드를 정의한 인터페이스
    - 클래스 메서드만 사용하며 인스턴스를 생성하지 않는다.
    """

    provider_name = ""

    @classmethod
    @abc.abstractmethod
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
    @abc.abstractmethod
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
    @abc.abstractmethod
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
    @abc.abstractmethod
    async def logout(cls, oauth_instance, auth_token):
        """
        소셜 서비스 토큰 revoke
        Args:
            oauth_instance (OAuth): OAuth 인증 객체
            auth_token (Dict): 소셜 서비스 토큰
        """
        raise NotImplementedError()
