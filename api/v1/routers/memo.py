from typing_extensions import Annotated

from fastapi import APIRouter, Depends, Path, Request

from core.database import db_session
from core.models import Member
from lib.common import get_paging_info
from lib.point import insert_point

from api.v1.dependencies.member import get_current_member
from api.v1.models import responses, responses_403
from api.v1.models.memo import (
    SendMemoModel, ViewMemoListModel,
    ResponseMemoModel, ResponseMemoListModel
)
from api.v1.dependencies.memo import validate_send_memo
from api.v1.lib.memo import MemoServiceAPI

router = APIRouter()


@router.get("/memos",
            summary="쪽지 목록 조회",
            responses={**responses_403},
            response_model=ResponseMemoListModel)
async def read_member_memos(
    memo_service: Annotated[MemoServiceAPI, Depends()],
    current_member: Annotated[Member, Depends(get_current_member)],
    data: Annotated[ViewMemoListModel, Depends()]
):
    """쪽지 목록을 조회합니다."""
    total_records = memo_service.fetch_total_records(data.me_type, current_member)
    paging_info = get_paging_info(data.page, data.per_page, total_records)
    memos = memo_service.fetch_memos(data.me_type, current_member, paging_info["offset"], data.per_page)

    return {
        "total_records": total_records,
        "total_pages": paging_info["total_pages"],
        "memos": memos
    }

@router.get("/memos/{me_id}",
            summary="쪽지 조회",
            response_model=ResponseMemoModel,
            responses={**responses})
async def read_member_memo(
    memo_service: Annotated[MemoServiceAPI, Depends()],
    current_member: Annotated[Member, Depends(get_current_member)],
    me_id: Annotated[int, Path(..., title="쪽지 ID")]
):
    """쪽지를 조회합니다."""
    return memo_service.read_memo(me_id, current_member)


@router.patch("/memos/{me_id}/read",
              summary="쪽지 읽음 처리",)
async def read_member_memo(
    memo_service: Annotated[MemoServiceAPI, Depends()],
    current_member: Annotated[Member, Depends(get_current_member)],
    me_id: Annotated[int, Path(..., title="쪽지 ID")]
):
    """쪽지를 읽음 처리합니다."""
    memo_service.update_read_datetime(me_id)
    memo_service.update_not_read_memos(current_member.mb_id)

    return {"detail": "쪽지를 읽음 처리하였습니다."}


@router.post("/memos",
             summary="쪽지 전송",
             #  response_model=ResponseMemoModel,
             responses={**responses})
async def send_memo(
    request: Request,
    db: db_session,
    memo_service: Annotated[MemoServiceAPI, Depends()],
    current_member: Annotated[Member, Depends(get_current_member)],
    data: Annotated[SendMemoModel, Depends(validate_send_memo)]
):
    """쪽지를 전송합니다."""
    # 쪽지 전송 처리
    for target in data._send_members:
        memo_service.send_memo(current_member, target, data.me_memo)

        # 실시간 쪽지 알림
        target.mb_memo_call = current_member.mb_id
        target.mb_memo_cnt = memo_service.fetch_non_read_memo(target.mb_id)
        db.commit()

        # 포인트 소진
        insert_point(request, current_member.mb_id, data._send_point * (-1), f"{target.mb_nick}({target.mb_id})님에게 쪽지 발송", "@memo", target.mb_id, "쪽지전송")

    return {"detail": "쪽지를 발송하였습니다."}


@router.delete("/memos/{me_id}",
               summary="쪽지 삭제",
               responses={**responses})
async def delete_member_memo(
    db: db_session,
    memo_service: Annotated[MemoServiceAPI, Depends()],
    current_member: Annotated[Member, Depends(get_current_member)],
    me_id: Annotated[int, Path(..., title="쪽지 ID")]
):
    """
    쪽지를 삭제합니다.

    #### 함께 처리되는 작업
    - 쪽지알림 삭제
    - 읽지 않은 쪽지 갯수 갱신
    """
    memo = memo_service.read_memo(me_id, current_member)
    db.delete(memo)
    db.commit()

    memo_service.update_memo_call(memo)
    memo_service.update_not_read_memos(current_member.mb_id)

    return {"detail": "쪽지를 삭제하였습니다."}
