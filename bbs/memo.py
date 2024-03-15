from typing_extensions import Annotated

from fastapi import APIRouter, Depends, Form, Path, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select, func

from core.database import db_session
from core.models import Member, Memo
from core.template import UserTemplates
from lib.common import *
from lib.dependencies import (
    get_login_member, validate_token, validate_captcha
)
from lib.memo import MemoService
from lib.point import insert_point
from lib.template_filters import default_if_none
from lib.template_functions import get_paging

router = APIRouter()
templates = UserTemplates()
templates.env.globals["captcha_widget"] = captcha_widget
templates.env.filters["default_if_none"] = default_if_none
templates.env.globals["is_none_datetime"] = is_none_datetime


@router.get("/memo")
async def memo_list(
    request: Request,
    db: db_session,
    memo_service: Annotated[MemoService, Depends()],
    member: Annotated[Member, Depends(get_login_member)],
    kind: str = Query(default="recv"),
    current_page: int = Query(default=1, alias="page")
):
    """
    쪽지 목록
    """
    records_per_page = request.state.config.cf_page_rows

    total_records = memo_service.fetch_total_records(kind, member)
    paging_info = get_paging_info(current_page, records_per_page, total_records)
    memos = memo_service.fetch_memos(kind, member, paging_info["offset"], records_per_page)

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
    db: db_session,
    memo_service: Annotated[MemoService, Depends()],
    login_member: Annotated[Member, Depends(get_login_member)],
    me_id: int = Path(...)
):
    """
    쪽지 상세
    """
    memo = memo_service.read_memo(me_id, login_member)
    
    kind = memo.me_type
    target_mb_id = memo.me_send_mb_id if kind == "recv" else memo.me_recv_mb_id
    memo_mb_column = Memo.me_recv_mb_id if kind == "recv" else Memo.me_send_mb_id

    # 상대방 정보 조회
    target = db.scalar(select(Member).where(Member.mb_id == target_mb_id))

    # 이전,다음 쪽지 조회
    prev_memo = db.scalars(
        select(Memo).where(
            Memo.me_id < me_id,
            Memo.me_type == kind,
            memo_mb_column == login_member.mb_id
        ).order_by(Memo.me_id.desc())
    ).first()
    next_memo = db.scalars(
        select(Memo).where(
            Memo.me_id > me_id,
            Memo.me_type == kind,
            memo_mb_column == login_member.mb_id
        ).order_by(Memo.me_id.asc())
    ).first()

    # 받은 쪽지 읽음처리
    if kind == "recv" and is_none_datetime(memo.me_read_datetime):
        now = datetime.now()
        memo.me_read_datetime = now
        send_memo = db.scalar(select(Memo).where(Memo.me_id==memo.me_send_id))
        if send_memo:
            send_memo.me_read_datetime = now
        db.commit()

        # 읽지 않은 쪽지 갯수 갱신
        memo_service.update_not_read_memos(login_member.mb_id)

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
    db: db_session,
    me_recv_mb_id: str = Query(default=None),
    me_id: int = Query(default=None)
):
    """
    쪽지 작성
    """
    # 쪽지를 전송할 회원 정보 조회
    target = None
    if me_recv_mb_id:
        target = db.scalar(select(Member).filter(Member.mb_id==me_recv_mb_id))
    
    # 답장할 쪽지의 정보 조회
    memo = db.get(Memo, me_id) if me_id else None

    context = {
        "request": request,
        "target": target,
        "memo": memo,
    }
    return templates.TemplateResponse("/memo/memo_form.html", context)


@router.post("/memo_form_update", dependencies=[Depends(validate_token), Depends(validate_captcha)])
async def memo_form_update(
    request: Request,
    db: db_session,
    memo_service: Annotated[MemoService, Depends()],
    login_member: Annotated[Member, Depends(get_login_member)],
    me_recv_mb_id: str = Form(...),
    me_memo: str = Form(...)
):
    """
    쪽지 전송
    """
    # me_recv_mb_id 공백 제거
    mb_id_list = me_recv_mb_id.replace(" ", "").split(',')
    send_members = memo_service.get_send_members(mb_id_list)
    send_point = memo_service.get_send_point(login_member, len(send_members))

    # 쪽지 전송 처리
    for target in send_members:
        memo_service.send_memo(login_member, target, me_memo)

        # 실시간 쪽지 알림
        target.mb_memo_call = login_member.mb_id
        target.mb_memo_cnt = memo_service.fetch_non_read_memo(target.mb_id)
        db.commit()

        # 포인트 소진
        insert_point(request, login_member.mb_id, send_point * (-1), f"{target.mb_nick}({target.mb_id})님에게 쪽지 발송", "@memo", target.mb_id, "쪽지전송")

    return RedirectResponse(url=f"/bbs/memo?kind=send", status_code=302)


@router.get("/memo_delete/{me_id}", dependencies=[Depends(validate_token)])
async def memo_delete(
    db: db_session,
    memo_service: Annotated[MemoService, Depends()],
    login_member: Annotated[Member, Depends(get_login_member)],
    me_id: Annotated[int, Path()],
    page: Annotated[int, Query()] = 1
):
    """
    쪽지 삭제
    """
    memo = memo_service.read_memo(me_id, login_member)
    db.delete(memo)
    db.commit()

    # 쪽지알림 삭제
    memo_service.update_memo_call(memo)

    # 읽지 않은 쪽지 갯수 갱신
    memo_service.update_not_read_memos(login_member.mb_id)

    return RedirectResponse(url=f"/bbs/memo?kind={memo.me_type}&page={page}", status_code=302)
