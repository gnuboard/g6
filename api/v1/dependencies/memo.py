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
    send_members = memo_service.get_send_members(data._send_mb_ids)
    data._send_members = send_members

    send_point = memo_service.get_send_point(current_member, len(send_members))
    data._send_point = send_point

    return data
