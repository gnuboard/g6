"""회원 관련 유틸리티 함수를 제공합니다."""
from datetime import datetime
from typing import Union

from fastapi import Request
from sqlalchemy.orm import Session
from sqlalchemy.sql import select

from core.models import Member


def get_member(db: Session, mb_id: str) -> Union[Member, None]:
    """회원 정보를 조회합니다."""
    return db.scalar(select(Member).where(Member.mb_id == mb_id))

def check_active_member(member: Member) -> bool:
    """활성화된 회원인지 확인합니다."""
    if member.mb_leave_date or member.mb_intercept_date:
        return False
    return True

def check_email_certified_member(
    request: Request,
    member: Member,
) -> bool:
    """이메일 인증이 완료된 회원인지 확인합니다."""
    config = request.state.config
    if config.cf_use_email_certify and member.mb_email_certify == datetime(1, 1, 1, 0, 0, 0):
        raise False
    return True