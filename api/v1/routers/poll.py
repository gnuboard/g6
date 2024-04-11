"""설문조사 API Router."""
from typing_extensions import Annotated
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.exc import SQLAlchemyError

from core.models import Member, Poll, PollEtc
from lib.mail import send_poll_etc_mail
from lib.point import insert_point
from lib.poll import get_latest_poll
from api.v1.dependencies.member import get_current_member_optional
from api.v1.dependencies.poll import (
    get_poll, get_poll_etc, validate_poll_etc_create, validate_poll_etc_delete,
    validate_poll_read, validate_poll_update
)
from api.v1.lib.poll import PollServiceAPI
from api.v1.models.response import responses
from api.v1.models.poll import CreatePollEtcModel, PatchPollModel

router = APIRouter()


@router.get("/polls/latest-one",
            summary="최신 설문조사 1건 조회",
            # response_model=None,
            responses={**responses})
async def read_poll_latest():
    """
    최신 설문조사 1건을 조회합니다.
    """
    try:
        return get_latest_poll()
    except SQLAlchemyError as e:
        return HTTPException(status_code=500, detail=str(e))


@router.get("/polls/{po_id}",
            dependencies=[Depends(validate_poll_read)],
            summary="설문조사 조회",
            # response_model=None,
            responses={**responses})
async def read_poll(
    poll_service: Annotated[PollServiceAPI, Depends()],
    poll: Annotated[Poll, Depends(get_poll)],
):
    """
    설문조사 정보를 조회합니다.
    """
    total_count, items = poll_service.calculate_poll_result(poll)
    other_polls = poll_service.fetch_other_polls(poll.po_id)
    etcs = poll.etcs

    return {
        "poll": poll,
        "total_count": total_count,
        "items": items,
        "other_polls": other_polls
    }


@router.patch("/polls/{po_id}/{item}",
              dependencies=[Depends(validate_poll_update)],
              summary="설문조사 참여",
              # response_model=None,
              responses={**responses})
async def update_poll(
    request: Request,
    poll_service: Annotated[PollServiceAPI, Depends()],
    member: Annotated[Member, Depends(get_current_member_optional)],
    poll: Annotated[Poll, Depends(get_poll)],
    data: Annotated[PatchPollModel, Depends()],
):
    """
    설문조사 항목에 투표합니다.
    """
    poll = poll_service.update_poll(data.po_id, data.item, member)

    # 포인트 지급
    if member:
        content = f'{poll.po_id}. {poll.po_subject[:20]} 설문조사 참여'
        insert_point(request, member.mb_id, poll.po_point,
                     content, '@poll', poll.po_id, '투표')

    return {"message": "설문조사에 참여가 완료되었습니다."}


@router.post("/polls/{po_id}/etc",
             dependencies=[Depends(validate_poll_etc_create)],
             summary="기타 의견 등록",
             # response_model=None,
             responses={**responses})
async def create_poll_etc(
    request: Request,
    poll_service: Annotated[PollServiceAPI, Depends()],
    member: Annotated[Member, Depends(get_current_member_optional)],
    poll: Annotated[Poll, Depends(get_poll)],
    data: CreatePollEtcModel,
):
    """
    기타의견 등록
    """
    poll_etc = poll_service.create_poll_etc(poll, member, **data.__dict__)

    # 기타의견 메일 발송
    send_poll_etc_mail(request, poll_etc)

    return {"message": "기타의견이 등록되었습니다."}


@router.delete("/polls/{po_id}/etc/{pc_id}",
               dependencies=[Depends(validate_poll_etc_delete)],
               summary="기타 의견 삭제",
               # response_model=None,
               responses={**responses})
async def delete_poll_etc(
    poll_service: Annotated[PollServiceAPI, Depends()],
    poll_etc: Annotated[PollEtc, Depends(get_poll_etc)],
):
    """
    기타의견을 삭제합니다.
    """
    poll_service.delete_poll_etc(poll_etc)

    return {"message": "기타의견이 삭제되었습니다."}
