from typing_extensions import Annotated

from fastapi import APIRouter, Depends, Path, Request

from core.database import db_session
from core.models import Member, Memo
from lib.point import insert_point

from api.v1.dependencies.member import get_current_member
from api.v1.models import responses
from api.v1.models.memo import (
    SendMemoModel, ViewMemoListModel,
    ResponseMemoModel, ResponseMemoListModel
)
from api.v1.dependencies.memo import validate_send_memo
from api.v1.lib.memo import MemoServiceAPI

router = APIRouter()


@router.get("/memos",
            summary="회원 메시지 목록 조회",
            response_model=ResponseMemoListModel,
            responses={**responses})
async def read_member_memos(
    current_member: Annotated[Member, Depends(get_current_member)],
    data: Annotated[ViewMemoListModel, Depends()]
):
    """회원 메시지 목록을 조회합니다."""
    
    query = current_member.send_memos if data.me_type == "send" else current_member.recv_memos
    query = query.where(Memo.me_type == data.me_type)
    # Pagination
    total_records = query.count()
    offset = (data.page - 1) * data.per_page
    memos = (query.order_by(Memo.me_id.desc())
                 .offset(offset)
                 .limit(data.per_page)
                 .all())

    return {
        "total_records": total_records,
        "page": data.page,
        "memos": memos
    }

@router.get("/memos/{me_id}",
            summary="회원 메시지 조회",
            response_model=ResponseMemoModel,
            responses={**responses})
async def read_member_memo(
    memo_service: Annotated[MemoServiceAPI, Depends()],
    current_member: Annotated[Member, Depends(get_current_member)],
    me_id: Annotated[int, Path(..., title="쪽지 ID")]
):
    """회원 메시지를 조회합니다."""
    return memo_service.read_memo(me_id, current_member)


@router.post("/memos",
             summary="회원 메시지 전송",
             #  response_model=ResponseMemoModel,
             responses={**responses})
async def send_memo(
    request: Request,
    db: db_session,
    memo_service: Annotated[MemoServiceAPI, Depends()],
    current_member: Annotated[Member, Depends(get_current_member)],
    data: Annotated[SendMemoModel, Depends(validate_send_memo)]
):
    """회원 쪽지를 전송합니다."""
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
               summary="회원 쪽지 삭제",
               responses={**responses})
async def delete_member_memo(
    db: db_session,
    memo_service: Annotated[MemoServiceAPI, Depends()],
    current_member: Annotated[Member, Depends(get_current_member)],
    me_id: Annotated[int, Path(..., title="쪽지 ID")]
):
    """
    회원 쪽지를 삭제합니다.

    #### 함께 처리되는 작업
    - 쪽지알림 삭제
    - 읽지 않은 쪽지 갯수 갱신
    """
    memo = memo_service.read_memo(me_id, current_member)
    db.delete(memo)
    db.commit()

    # 쪽지알림 삭제
    memo_service.update_memo_call(memo)

    # 읽지 않은 쪽지 갯수 갱신
    memo_service.update_not_read_memos(current_member.mb_id)

    return {"detail": "쪽지를 삭제하였습니다."}
