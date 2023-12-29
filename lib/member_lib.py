from sqlalchemy import select
from sqlalchemy.orm import Session

import common.models as models
from lib.common import is_none_datetime


class MemberService(models.Member):
    @classmethod
    def create_by_id(cls, db: Session, mb_id: str) -> "MemberService":
        query = select(cls).where(cls.mb_id == mb_id)

        return db.scalar(query)

    def is_intercept_or_leave(self) -> bool:
        """차단 또는 탈퇴한 회원인지 확인합니다.

        Returns:
            bool: 차단 또는 탈퇴한 회원이면 True, 아니거나 회원정보가 없으면 False
        """
        if not self.mb_id:
            return False

        return self.mb_leave_date or self.mb_intercept_date
    
    def is_email_certify(self, use_email_certify: bool) -> bool:
        """이메일 인증을 받았는지 확인합니다.
        Args:
            use_email_certify (bool): 이메일 인증을 사용하는지 여부

        Returns:
            bool: 이메일 인증을 받았으면 True, 아니면 False
        """
        if not use_email_certify:
            return True

        if not self.mb_id:
            return False
        
        return not is_none_datetime(self.mb_email_certify)