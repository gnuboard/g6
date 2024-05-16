"""쪽지 관련 의존성을 정의합니다."""
from typing_extensions import Annotated

from fastapi import Depends, Path

from core.models import Member, Memo

from api.v1.dependencies.member import get_current_member
from api.v1.models.memo import SendMemo
from api.v1.service.memo import MemoServiceAPI


def get_memo(
    service: Annotated[MemoServiceAPI, Depends()],
    member: Annotated[Member, Depends(get_current_member)],
    me_id: Annotated[int, Path(title="쪽지 아이디", description="쪽지 아이디")]
) -> Memo:
    """쪽지 정보 조회 의존성 함수"""
    return service.read_memo(me_id, member)


def validate_send_memo(
    memo_service: Annotated[MemoServiceAPI, Depends()],
    member: Annotated[Member, Depends(get_current_member)],
    data: SendMemo
):
    """쪽지 전송 시 필요한 정보를 검증합니다."""
    data.members = memo_service.get_receive_members(data.mb_ids)
    data.point = memo_service.calculate_send_point(member, len(data.members))

    return data
