"""쪽지 Template Router"""
from typing_extensions import Annotated

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import RedirectResponse

from core.models import Member, Memo
from core.template import UserTemplates
from lib.captcha import captcha_widget
from lib.common import get_paging_info, is_none_datetime
from lib.dependency.auth import get_login_member
from lib.dependency.dependencies import validate_captcha, validate_token
from lib.dependency.memo import get_memo
from lib.html_sanitizer import content_sanitizer as sanitizer
from lib.template_filters import default_if_none
from lib.template_functions import get_paging
from service.member_service import MemberService
from service.memo_service import MemoService
from service.point_service import PointService

router = APIRouter()
templates = UserTemplates()
templates.env.globals["captcha_widget"] = captcha_widget
templates.env.filters["default_if_none"] = default_if_none
templates.env.globals["is_none_datetime"] = is_none_datetime


@router.get("/memo")
async def memo_list(
    request: Request,
    memo_service: Annotated[MemoService, Depends()],
    member: Annotated[Member, Depends(get_login_member)],
    kind: str = Query(default="recv"),
    current_page: int = Query(default=1, alias="page")
):
    """
    쪽지 목록 조회 페이지
    """
    per_page = getattr(request.state.config, "cf_page_rows", 10)

    total_records = memo_service.fetch_total_records(kind, member.mb_id)
    paging_info = get_paging_info(current_page, per_page, total_records)
    memos = memo_service.fetch_memos(kind, member.mb_id,
                                     paging_info["offset"], per_page)

    for memo in memos:
        memo.target_member = memo.send_member if kind == "recv" else memo.recv_member

    context = {
        "request": request,
        "kind": kind,
        "memos": memos,
        "total_records": total_records,
        "page": current_page,
        "paging": get_paging(request, current_page, total_records),
    }
    return templates.TemplateResponse("/memo/memo_list.html", context)


@router.get("/memo_view/{me_id}")
async def memo_view(
    request: Request,
    member_service: Annotated[MemberService, Depends()],
    memo_service: Annotated[MemoService, Depends()],
    member: Annotated[Member, Depends(get_login_member)],
    memo: Annotated[Memo, Depends(get_memo)],
):
    """
    쪽지 조회 페이지
    """
    # 상대방 정보 조회
    target_mb_id = memo.me_send_mb_id if memo.me_type == "recv" else memo.me_recv_mb_id
    target = member_service.fetch_member_by_id(target_mb_id)

    # 이전,다음 쪽지 조회
    prev_memo, next_memo = memo_service.fetch_prev_next_qa(memo.me_id, member)

    # 받은 쪽지 읽음처리
    memo_service.update_read_datetime(memo)
    memo_service.update_not_read_memos(member)

    context = {
        "request": request,
        "kind": memo.me_type,
        "memo": memo,
        "target": target,
        "prev_memo": prev_memo,
        "next_memo": next_memo,
    }
    return templates.TemplateResponse("/memo/memo_view.html", context)


@router.get("/memo_form", dependencies=[Depends(get_login_member)])
async def memo_form(
    request: Request,
    member_service: Annotated[MemberService, Depends()],
    memo_service: Annotated[MemoService, Depends()],
    me_id: int = Query(default=None)
):
    """
    쪽지 작성 페이지
    """
    # 답장할 쪽지 & 회원 정보 조회
    target = None
    memo = memo_service.fetch_memo(me_id)
    if memo:
        target = member_service.read_member(memo.me_send_mb_id)

    context = {
        "request": request,
        "target": target,
        "memo": memo,
    }
    return templates.TemplateResponse("/memo/memo_form.html", context)


@router.post("/memo_form_update",
             dependencies=[Depends(validate_token),
                           Depends(validate_captcha)])
async def memo_form_update(
    memo_service: Annotated[MemoService, Depends()],
    point_service: Annotated[PointService, Depends()],
    member: Annotated[Member, Depends(get_login_member)],
    me_recv_mb_id: str = Form(...),
    me_memo: str = Form(...)
):
    """
    쪽지 전송
    """
    # me_recv_mb_id 공백 제거
    mb_id_list = me_recv_mb_id.replace(" ", "").split(',')
    send_members = memo_service.get_receive_members(mb_id_list)
    send_point = memo_service.calculate_send_point(member, len(send_members))

    # 쪽지 전송 처리
    for target in send_members:
        memo_service.send_memo(member, target, sanitizer.get_cleaned_data(me_memo))

        # 실시간 쪽지 알림
        memo_service.update_memo_call(member, target)

        # 포인트 소진
        point_service.save_point(
            member.mb_id, send_point * (-1),
            f"{target.mb_nick}({target.mb_id})님에게 쪽지 발송", "@memo",
            target.mb_id, "쪽지전송")

    return RedirectResponse(url="/bbs/memo?kind=send", status_code=302)


@router.get("/memo_delete/{me_id}",
            dependencies=[Depends(validate_token)])
async def memo_delete(
    service: Annotated[MemoService, Depends()],
    member: Annotated[Member, Depends(get_login_member)],
    memo: Annotated[Memo, Depends(get_memo)],
    page: Annotated[int, Query()] = 1
):
    """
    쪽지 삭제
    """
    service.delete_memo_call(memo)
    service.delete_memo(memo)
    service.update_not_read_memos(member)

    return RedirectResponse(url=f"/bbs/memo?kind={memo.me_type}&page={page}", status_code=302)
