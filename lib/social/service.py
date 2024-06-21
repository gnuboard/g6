"""소셜 로그인 관련 기능을 제공하는 서비스 모듈입니다."""
import hashlib
import zlib
from typing import Optional

from sqlalchemy import delete, exists, select
from core.database import db_session
from core.exception import AlertException
from core.formclass import SocialProfile
from core.models import MemberSocialProfiles
from service import BaseService


class SocialAuthService(BaseService):
    """
    소셜 로그인 관련 서비스를 제공하는 종속성 주입 클래스입니다.
    """
    def __init__(self, db: db_session):
        self.db = db

    def raise_exception(self, status_code: int, detail: str = None, url: str = None):
        return AlertException(detail=detail, status_code=status_code, url=url)

    def get_profile_by_identifier(self, identifier: str, provider: str) -> Optional[str]:
        """ 소셜 서비스 identifier 로 회원 아이디를 가져옴

        Args:
            identifier (str) : 소셜서비스 사용자 식별 id
            provider (str) : 소셜 제공자

        Returns:
            g5 user_id
        """
        return self.db.scalar(
            select(MemberSocialProfiles)
            .where(
                MemberSocialProfiles.provider == provider,
                MemberSocialProfiles.identifier == identifier
            )
        )

    def check_exists_by_mb_id(self, provider: str, mb_id: str) -> bool:
        """소셜 서비스 아이디가 존재하는지 확인

        Args:
            provider (str) : 소셜 제공자
            mb_id (str) : 회원 아이디

        Returns:
            bool
        """
        result = self.db.scalar(
            exists(MemberSocialProfiles.mp_no)
            .where(
                MemberSocialProfiles.provider == provider,
                MemberSocialProfiles.mb_id == mb_id
            ).select()
        )
        return bool(result)

    def check_exists_by_member_id(self, member_id: str) -> bool:
        """회원아이디가 존재하는지 확인

        Args:
            member_id (str) : 회원 아이디

        Returns:
            True or False
        """
        result = self.db.scalar(
            exists(MemberSocialProfiles.mb_id)
            .where(MemberSocialProfiles.mb_id == member_id)
            .select()
        )
        return bool(result)

    def g6_convert_social_id(self, identifier: str, provider: str) -> str:
        """소셜 id 생성 함수
        - 그누보드5의 get_social_convert_id() 함수를 참고하여 작성
        - provider + uid로 부터 고유 해시값생성

        Args:
            identifier (str) : 소셜서비스 사용자 식별 id
            provider (str) : 소셜 제공자

        Returns:
            str : 소셜회원 mb_id
        """
        md5_hash = hashlib.md5(identifier.encode()).hexdigest()
        # Adler-32 hash on the hexadecimal MD5 hash
        adler32_hash = zlib.adler32(md5_hash.encode())

        return f"{provider}_{hex(adler32_hash)[2:]}"

    def link_social_login(self, mb_id: str, provider: str, profile: SocialProfile):
        """
        소셜계정 연결
        """
        member_social_profiles = MemberSocialProfiles(
            mb_id=mb_id,
            provider=provider,
            identifier=profile.identifier,
            displayname=profile.displayname,
            profileurl=profile.profile_url,
            photourl=profile.photourl
        )
        self.db.add(member_social_profiles)
        self.db.commit()

    def unlink_social_login(self, mb_id: str, provider: str = None) -> None:
        """
        소셜계정 연결해제
        """
        query = delete(MemberSocialProfiles).where(MemberSocialProfiles.mb_id == mb_id)
        if provider:
            query = query.where(MemberSocialProfiles.provider == provider)
        self.db.execute(query)
        self.db.commit()
