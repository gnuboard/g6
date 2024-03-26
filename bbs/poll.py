"""투표 Template Router."""
from typing_extensions import Annotated

from fastapi import APIRouter, Depends, Form, Path, Request
from fastapi.responses import RedirectResponse

from core.models import Member
from core.template import UserTemplates
from lib.common import captcha_widget
from lib.dependencies import get_login_member, validate_token, validate_captcha
from lib.mail import send_poll_etc_mail
from lib.member_lib import get_member_level
from lib.point import insert_point
from lib.poll import PollService

router = APIRouter()
templates = UserTemplates()
templates.env.globals["get_member_level"] = get_member_level
templates.env.globals["captcha_widget"] = captcha_widget


@router.post("/poll_update/{po_id}",
             dependencies=[Depends(validate_token)])
async def poll_update(
    request: Request,
    poll_service: Annotated[PollService, Depends()],
    po_id: int = Path(...),
    gb_poll: int = Form(...)
):
    """
    투표하기
    """
    member = request.state.login_member
    poll = poll_service.update_poll(po_id, gb_poll, member)

    # 포인트 지급
    if member:
        content = f'{poll.po_id}. {poll.po_subject[:20]} 설문조사 참여'
        insert_point(request, member.mb_id, poll.po_point,
                     content, '@poll', poll.po_id, '투표')

    return RedirectResponse(url=f"/bbs/poll_result/{po_id}", status_code=302)


@router.get("/poll_result/{po_id}")
async def poll_result(
    request: Request,
    poll_service: Annotated[PollService, Depends()],
    login_member: Annotated[Member, Depends(get_login_member)],
    po_id: int = Path(...)
):
    """
    설문조사 결과
    """
    poll = poll_service.fetch_poll(po_id, login_member)
    total_count, items = poll_service.get_poll_result(poll)
    other_polls = poll_service.fetch_other_polls(po_id)

    context = {
        "request": request,
        "poll_result": poll,
        "total_count": total_count,
        "items": items,
        "etcs": poll.etcs,
        "other_list": other_polls
    }
    return templates.TemplateResponse("/bbs/poll_result.html", context)


@router.post("/poll_etc_update/{po_id}",
             dependencies=[Depends(validate_token)])
async def poll_etc_update(
    request: Request,
    poll_service: Annotated[PollService, Depends()],
    member: Annotated[Member, Depends(get_login_member)],
    po_id: int = Path(...),
    pc_name: str = Form(...),
    pc_idea: str = Form(...),
    recaptcha_response: str = Form("", alias="g-recaptcha-response"),
):
    """
    기타의견 등록
    """
    if not member:
        await validate_captcha(request, recaptcha_response)

    poll_etc = poll_service.create_poll_etc(
        po_id, member, pc_name=pc_name, pc_idea=pc_idea)

    send_poll_etc_mail(request, poll_etc)

    return RedirectResponse(url=f"/bbs/poll_result/{po_id}", status_code=302)


@router.get("/poll/{po_id}/etc_delete/{pc_id}",
            dependencies=[Depends(validate_token)])
async def poll_etc_delete(
    member: Annotated[Member, Depends(get_login_member)],
    poll_service: Annotated[PollService, Depends()],
    po_id: int = Path(...),
    pc_id: int = Path(...)
):
    """
    기타의견 삭제
    """
    poll_service.delete_poll_etc(po_id, pc_id, member)

    return RedirectResponse(url=f"/bbs/poll_result/{po_id}", status_code=302)
