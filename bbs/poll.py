"""설문조사 Template Router."""
from typing_extensions import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Form, Request
from fastapi.responses import RedirectResponse

from core.models import Member, Poll, PollEtc
from core.template import UserTemplates
from lib.captcha import captcha_widget
from lib.dependency.dependencies import validate_token
from lib.dependency.auth import get_login_member_optional
from lib.dependency.poll import (
    get_poll, get_poll_etc, validate_poll_etc_create,
    validate_poll_etc_delete, validate_poll_read, validate_poll_update
)
from lib.mail import send_poll_etc_mail
from lib.member import get_member_level
from service.point_service import PointService
from service.poll_service import PollService

router = APIRouter()
templates = UserTemplates()
templates.env.globals["get_member_level"] = get_member_level
templates.env.globals["captcha_widget"] = captcha_widget


@router.post("/poll_update/{po_id}",
             dependencies=[Depends(validate_token),
                           Depends(validate_poll_update)])
async def poll_update(
    service: Annotated[PollService, Depends()],
    point_service: Annotated[PointService, Depends()],
    member: Annotated[Member, Depends(get_login_member_optional)],
    poll: Annotated[Poll, Depends(get_poll)],
    gb_poll: int = Form(...)
):
    """
    설문조사 참여
    """
    poll = service.update_poll(poll, gb_poll, member)

    # 포인트 지급
    if member:
        content = f'{poll.po_id}. {poll.po_subject[:20]} 설문조사 참여'
        point_service.save_point(member.mb_id, poll.po_point, content,
                                 '@poll', poll.po_id, '투표')

    return RedirectResponse(url=f"/bbs/poll_result/{poll.po_id}", status_code=302)


@router.get("/poll_result/{po_id}",
            dependencies=[Depends(validate_poll_read)])
async def poll_result(
    request: Request,
    service: Annotated[PollService, Depends()],
    poll: Annotated[Poll, Depends(get_poll)],
):
    """
    설문조사 결과 페이지
    """
    total_count, items = service.calculate_poll_result(poll)
    other_polls = service.fetch_other_polls(poll.po_id)

    context = {
        "request": request,
        "poll": poll,
        "total_count": total_count,
        "items": items,
        "other_list": other_polls
    }
    return templates.TemplateResponse("/bbs/poll_result.html", context)


@router.post("/poll/{po_id}/etc_update",
             dependencies=[Depends(validate_token),
                           Depends(validate_poll_etc_create)])
async def poll_etc_update(
    request: Request,
    background_tasks: BackgroundTasks,
    service: Annotated[PollService, Depends()],
    member: Annotated[Member, Depends(get_login_member_optional)],
    poll: Annotated[Poll, Depends(get_poll)],
    pc_name: str = Form(...),
    pc_idea: str = Form(...),
):
    """
    설문조사 기타의견 등록
    """
    poll_etc = service.create_poll_etc(poll, member,
                                       pc_name=pc_name, pc_idea=pc_idea)
    # 관리자에게 메일 발송(백그라운드)
    background_tasks.add_task(send_poll_etc_mail, request, poll_etc)

    return RedirectResponse(url=f"/bbs/poll_result/{poll.po_id}", status_code=302)


@router.get("/poll/{po_id}/etc_delete/{pc_id}",
            dependencies=[Depends(validate_token),
                          Depends(validate_poll_etc_delete)])
async def poll_etc_delete(
    service: Annotated[PollService, Depends()],
    poll_etc: Annotated[PollEtc, Depends(get_poll_etc)]
):
    """
    기타의견 삭제
    """
    service.delete_poll_etc(poll_etc)

    return RedirectResponse(url=f"/bbs/poll_result/{poll_etc.po_id}", status_code=302)
