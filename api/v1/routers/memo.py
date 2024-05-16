"""쪽지 API Router"""
from typing_extensions import Annotated

from fastapi import APIRouter, Depends

from api.v1.service.point import PointServiceAPI
from core.models import Member, Memo
from lib.common import get_paging_info

from api.v1.dependencies.member import get_current_member
from api.v1.dependencies.memo import get_memo, validate_send_memo
from api.v1.service.memo import MemoServiceAPI
from api.v1.models.response import (
    MessageResponse, response_401, response_403, response_422, response_404
)
from api.v1.models.memo import MemoResponse, SendMemo, MemoList, MemoListResponse

router = APIRouter()


@router.get("/memos",
            summary="쪽지 목록 조회",
            responses={**response_401, **response_422})
async def read_memos(
    service: Annotated[MemoServiceAPI, Depends()],
    member: Annotated[Member, Depends(get_current_member)],
    data: Annotated[MemoList, Depends()]
) -> MemoListResponse:
    """현재 로그인 회원의 쪽지 목록을 조회합니다."""
    total_records = service.fetch_total_records(data.me_type, member.mb_id)
    paging_info = get_paging_info(data.page, data.per_page, total_records)
    memos = service.fetch_memos(data.me_type, member.mb_id,
                                     data.offset, data.per_page)

    return {
        "total_records": total_records,
        "total_pages": paging_info["total_pages"],
        "memos": memos
    }

@router.get("/memos/{me_id}",
            summary="쪽지 조회",
            responses={**response_401, **response_403, **response_404, **response_422})
async def read_member_memo(
    service: Annotated[MemoServiceAPI, Depends()],
    member: Annotated[Member, Depends(get_current_member)],
    memo: Annotated[Memo, Depends(get_memo)],
) -> MemoResponse:
    """
    쪽지를 1건 조회합니다.
    - 본인의 쪽지만 조회할 수 있습니다.
    """
    prev_memo, next_memo = service.fetch_prev_next_qa(memo.me_id, member)

    return {
        "memo": memo,
        "prev_memo": prev_memo,
        "next_memo": next_memo,
    }


@router.patch("/memos/{me_id}/read",
              summary="쪽지 읽음 처리",
              responses={**response_401, **response_403, **response_404, **response_422})
async def update_read_member_memo(
    service: Annotated[MemoServiceAPI, Depends()],
    member: Annotated[Member, Depends(get_current_member)],
    memo: Annotated[Memo, Depends(get_memo)],
) -> MessageResponse:
    """
    쪽지를 읽음 처리합니다.
    - 본인의 쪽지만 읽음 처리할 수 있습니다.
    """
    service.update_read_datetime(memo)
    service.update_not_read_memos(member)

    return {"message": "쪽지를 읽음 처리하였습니다."}


@router.post("/memos",
             summary="쪽지 전송",
             responses={**response_403, **response_404, **response_422})
async def send_memo(
    service: Annotated[MemoServiceAPI, Depends()],
    point_service: Annotated[PointServiceAPI, Depends()],
    member: Annotated[Member, Depends(get_current_member)],
    data: Annotated[SendMemo, Depends(validate_send_memo)]
) -> MessageResponse:
    """
    쪽지를 전송합니다.
    - 쪽지 전송 시 포인트가 소진됩니다.

    ### Request Body
    - **me_recv_mb_id**: 쪽지를 받을 회원 아이디 (,로 구분하여 여러명에게 전송 가능)
    - **me_memo**: 쪽지 내용
    """
    # 발송 대상 회원에게 쪽지 발송
    for target in data.members:
        service.send_memo(member, target, data.me_memo)
        service.update_memo_call(member, target)
        # 포인트 소진
        point_service.save_point(
            member.mb_id, data.point * (-1),
            f"{target.mb_nick}({target.mb_id})님에게 쪽지 발송", "@memo",
            target.mb_id, "쪽지전송")

    return {"message": "쪽지를 발송하였습니다."}


@router.delete("/memos/{me_id}",
               summary="쪽지 삭제",
               responses={**response_403, **response_404})
async def delete_member_memo(
    memo_service: Annotated[MemoServiceAPI, Depends()],
    member: Annotated[Member, Depends(get_current_member)],
    memo: Annotated[Memo, Depends(get_memo)],
) -> MessageResponse:
    """
    쪽지를 삭제합니다.

    ### 함께 처리되는 작업
    - 쪽지알림 삭제
    - 읽지 않은 쪽지 갯수 갱신
    """
    memo_service.delete_memo_call(memo)
    memo_service.delete_memo(memo)
    memo_service.update_not_read_memos(member)

    return {"message": "쪽지를 삭제하였습니다."}
