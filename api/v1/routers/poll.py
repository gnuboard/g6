"""설문조사 API Router."""
from typing_extensions import Annotated
from fastapi import APIRouter, BackgroundTasks, Depends, Path, Request

from api.v1.service.point import PointServiceAPI
from core.models import Member, Poll, PollEtc
from lib.mail import send_poll_etc_mail
from api.v1.dependencies.member import get_current_member_optional
from api.v1.dependencies.poll import (
    get_poll, get_poll_etc, validate_poll_etc_create, validate_poll_etc_delete,
    validate_poll_read, validate_poll_update
)
from api.v1.service.poll import PollServiceAPI
from api.v1.models.response import (
    MessageResponse, response_403, response_404, response_409, response_422,
    response_500
)
from api.v1.models.poll import (
    CreatePollEtc, LatestPollResponse, PollResponse
)

router = APIRouter()


@router.get("/polls/latest",
            summary="최신 설문조사 1건 조회",
            responses={**response_500})
async def read_poll_latest(
    service: Annotated[PollServiceAPI, Depends()],
) -> LatestPollResponse:
    """
    최신 설문조사 1건을 조회합니다.
    - LRU(Least Recently Used)캐시를 사용하여 조회합니다.
    """
    return service.fetch_latest_poll()


@router.get("/polls/{po_id}",
            dependencies=[Depends(validate_poll_read)],
            summary="설문조사 조회",
            responses={**response_403, **response_404})
async def read_poll(
    service: Annotated[PollServiceAPI, Depends()],
    poll: Annotated[Poll, Depends(get_poll)],
) -> PollResponse:
    """
    설문조사 정보를 조회합니다.
    """
    total_vote, items = service.calculate_poll_result(poll)
    other_polls = service.fetch_other_polls(poll.po_id)

    return {
        "poll": poll,
        "total_vote": total_vote,
        "items": items,
        "etcs": poll.etcs,
        "other_polls": other_polls
    }


@router.patch("/polls/{po_id}/{item}",
              dependencies=[Depends(validate_poll_update)],
              summary="설문조사 참여",
              responses={**response_403, **response_404, **response_409})
async def update_poll(
    service: Annotated[PollServiceAPI, Depends()],
    point_service: Annotated[PointServiceAPI, Depends()],
    member: Annotated[Member, Depends(get_current_member_optional)],
    poll: Annotated[Poll, Depends(get_poll)],
    item: Annotated[int, Path(title="설문항목 번호", description="설문항목 번호", ge=1, le=9)],
) -> MessageResponse:
    """
    설문조사 항목에 투표합니다.
    - 권한이 없거나 이미 참여한 경우는 투표할 수 없습니다.
    - 포인트 설정이 되어있는 경우, 투표 시 포인트가 지급됩니다.
    """
    poll = service.update_poll(poll.po_id, item, member)

    # 포인트 지급
    if member:
        content = f'{poll.po_id}. {poll.po_subject[:20]} 설문조사 참여'
        point_service.save_point(member.mb_id, poll.po_point, content,
                                 '@poll', poll.po_id, '투표')

    return {"message": "설문조사 참여가 완료되었습니다."}


@router.post("/polls/{po_id}/etc",
             dependencies=[Depends(validate_poll_etc_create)],
             summary="기타 의견 등록",
             responses={**response_403, **response_404, **response_422})
async def create_poll_etc(
    request: Request,
    background_tasks: BackgroundTasks,
    service: Annotated[PollServiceAPI, Depends()],
    member: Annotated[Member, Depends(get_current_member_optional)],
    poll: Annotated[Poll, Depends(get_poll)],
    data: CreatePollEtc,
) -> MessageResponse:
    """
    설문조사의 기타의견을 등록합니다.
    - 기타의견을 등록할 수 있는 설문조사인 경우에만 등록할 수 있습니다.
    - 작성자는 회원 또는 비회원으로 등록할 수 있습니다.
    - 기타의견 등록 시 최고관리자에게 메일이 발송됩니다. (메일발송 설정 시)

    ### Request Body
    - **pc_name**: 작성자
    - **pc_idea**: 기타의견
    """
    poll_etc = service.create_poll_etc(poll, member, **data.__dict__)

    # 기타의견 메일 발송
    background_tasks.add_task(send_poll_etc_mail, request, poll_etc)

    return {"message": "기타의견이 등록되었습니다."}


@router.delete("/polls/{po_id}/etc/{pc_id}",
               dependencies=[Depends(validate_poll_etc_delete)],
               summary="기타 의견 삭제",
               responses={**response_403, **response_404, **response_404})
async def delete_poll_etc(
    poll_service: Annotated[PollServiceAPI, Depends()],
    poll_etc: Annotated[PollEtc, Depends(get_poll_etc)],
) -> MessageResponse:
    """
    기타의견을 삭제합니다.
    """
    poll_service.delete_poll_etc(poll_etc)

    return {"message": "기타의견이 삭제되었습니다."}
