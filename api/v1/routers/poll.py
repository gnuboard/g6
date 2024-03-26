"""투표 API Router."""
from typing_extensions import Annotated
from fastapi import APIRouter, Depends, HTTPException, Path, Request
from sqlalchemy.exc import SQLAlchemyError

from core.models import Member
from lib.mail import send_poll_etc_mail
from lib.point import insert_point
from lib.poll import get_latest_poll
from api.v1.dependencies.member import (
    get_current_member, get_current_member_optional
)
from api.v1.models import responses
from api.v1.models.poll import CreatePollEtcModel, PatchPollModel
from api.v1.lib.poll import PollServiceAPI

router = APIRouter()


@router.get("/polls/latest-one",
            summary="최신 투표 1건 조회",
            # response_model=None,
            responses={**responses})
async def read_poll_latest():
    """
    최신 투표 1건을 조회합니다.
    """
    try:
        return get_latest_poll()
    except SQLAlchemyError as e:
        return HTTPException(status_code=500, detail=str(e))


@router.get("/polls/{po_id}",
            summary="투표 조회",
            # response_model=None,
            responses={**responses})
async def read_poll(
    poll_service: Annotated[PollServiceAPI, Depends()],
    member: Annotated[Member, Depends(get_current_member)],
    po_id: Annotated[int, Path(..., title="투표 ID")]
):
    """
    투표 정보를 조회합니다.
    """
    poll = poll_service.fetch_poll(po_id, member)
    total_count, items = poll_service.get_poll_result(poll)
    other_polls = poll_service.fetch_other_polls(po_id)

    return {
        "poll": poll,
        "total_count": total_count,
        "items": items,
        "etcs": poll.etcs,
        "other_polls": other_polls
    }


@router.patch("/polls/{po_id}/{item}",
              summary="설문조사 참여",
              # response_model=None,
              responses={**responses})
async def create_poll(
    request: Request,
    poll_service: Annotated[PollServiceAPI, Depends()],
    member: Annotated[Member, Depends(get_current_member_optional)],
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
             summary="기타 의견 등록",
             # response_model=None,
             responses={**responses})
async def create_poll_etc(
    request: Request,
    member: Annotated[Member, Depends(get_current_member_optional)],
    poll_service: Annotated[PollServiceAPI, Depends()],
    po_id: Annotated[int, Path(...)],
    data: CreatePollEtcModel,
):
    """
    기타의견 등록
    """
    poll_etc = poll_service.create_poll_etc(po_id, member, **data.__dict__)

    send_poll_etc_mail(request, poll_etc)

    return {"message": "기타의견이 등록되었습니다."}


@router.delete("/polls/{po_id}/etc/{pc_id}",
               summary="기타 의견 삭제",
               # response_model=None,
               responses={**responses})
async def delete_poll_etc(
    poll_service: Annotated[PollServiceAPI, Depends()],
    member: Annotated[Member, Depends(get_current_member)],
    po_id: Annotated[int, Path(...)],
    pc_id: Annotated[int, Path(...)],
):
    """
    기타의견을 삭제합니다.
    """
    poll_service.delete_poll_etc(po_id, pc_id, member)

    return {"message": "기타의견이 삭제되었습니다."}
