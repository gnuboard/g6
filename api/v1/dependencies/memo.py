"""쪽지 관련 의존성을 정의합니다."""
from typing_extensions import Annotated

from fastapi import Depends

from core.models import Member

from api.v1.dependencies.member import get_current_member
from api.v1.models.memo import SendMemoModel
from api.v1.lib.memo import MemoServiceAPI


def validate_send_memo(
    memo_service: Annotated[MemoServiceAPI, Depends()],
    current_member: Annotated[Member, Depends(get_current_member)],
    data: SendMemoModel
):
    """쪽지 전송 시 필요한 정보를 검증합니다."""
    data.send_members = memo_service.get_send_members(data.send_mb_ids)
    data.send_point = memo_service.calculate_send_point(current_member, len(data.send_members))

    return data
