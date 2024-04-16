"""쪽지 관련 유효성 검사를 위한 의존성 함수를 정의합니다."""
from fastapi import Depends, Path
from typing_extensions import Annotated

from core.models import Member, Memo
from lib.dependency.auth import get_login_member
from service.memo_service import MemoService


def get_memo(
    service: Annotated[MemoService, Depends()],
    member: Annotated[Member, Depends(get_login_member)],
    me_id: Annotated[int, Path()],
) -> Memo:
    """쪽지 조회"""
    return service.read_memo(me_id, member)
    