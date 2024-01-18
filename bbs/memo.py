from typing_extensions import Annotated

from fastapi import APIRouter, Depends, Form, Path, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select, update, func

from core.database import db_session
from core.exception import AlertException
from core.models import Member, Memo
from core.template import UserTemplates
from lib.common import *
from lib.dependencies import (
    get_login_member, validate_token, validate_captcha
)
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
    member: Annotated[Member, Depends(get_login_member)],
    kind: str = Query(default="recv"),
    current_page: int = Query(default=1, alias="page")
):
    """
    쪽지 목록
    """
    mb_column = Memo.me_recv_mb_id if kind == "recv" else Memo.me_send_mb_id
    query = (
        select()
        .where(mb_column == member.mb_id, Memo.me_type == kind)
        .order_by(Memo.me_id.desc())
    )

    # 페이징 처리
    records_per_page = request.state.config.cf_page_rows
    total_records = db.scalar(query.add_columns(func.count()).select_from(Memo).order_by(None))
    offset = (current_page - 1) * records_per_page
    memos = db.scalars(query.add_columns(Memo).offset(offset).limit(records_per_page)).all()

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
    login_member: Annotated[Member, Depends(get_login_member)],
    me_id: int = Path(...)
):
    """
    쪽지 상세
    """
    # 본인 쪽지 조회
    memo = db.get(Memo, me_id)
    if not memo:
        raise AlertException(status_code=404, detail="쪽지가 존재하지 않습니다.", url="/bbs/memo")
    
    kind = memo.me_type
    target_mb_id = memo.me_send_mb_id if kind == "recv" else memo.me_recv_mb_id
    memo_mb_id = memo.me_recv_mb_id if kind == "recv" else memo.me_send_mb_id
    memo_mb_column = Memo.me_recv_mb_id if kind == "recv" else Memo.me_send_mb_id

    if not memo_mb_id == login_member.mb_id:
        raise AlertException(status_code=403, detail="본인의 쪽지만 조회 가능합니다.", url="/bbs/memo")

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

        # 안읽은쪽지 갯수 갱신
        db.execute(
            update(Member)
            .values(mb_memo_cnt=get_memo_not_read(login_member.mb_id))
            .where(Member.mb_id == login_member.mb_id)
        )
        db.commit()

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
    member: Annotated[Member, Depends(get_login_member)],
    me_recv_mb_id: str = Form(...),
    me_memo: str = Form(...)
):
    """
    쪽지 전송
    """
    config = request.state.config

    # me_recv_mb_id 공백 제거
    mb_id_list = me_recv_mb_id.replace(" ", "").split(',')
    target_list = []
    error_list = []
    for mb_id in mb_id_list:
        # 쪽지를 전송할 회원 정보 조회
        target = db.scalar(select(Member).filter(Member.mb_id == mb_id))
        if target and target.mb_open and not (target.mb_leave_date or target.mb_intercept_date):
            target_list.append(target)
        else:
            error_list.append(mb_id)

    if error_list:
        raise AlertException(f"{','.join(error_list)} : 존재(또는 정보공개)하지 않는 회원이거나 탈퇴/차단된 회원입니다.\\n쪽지를 발송하지 않았습니다.", 404)

    # 총 사용 포인트 체크
    use_point = int(config.cf_memo_send_point)
    total_use_point = use_point * len(target_list)
    if total_use_point > 0:
        if member.mb_point < total_use_point:
            raise AlertException(f"보유하신 포인트({member.mb_point})가 부족합니다.\\n쪽지를 발송하지 않았습니다.", 403)

    # 전송대상의 목록을 순회하며 쪽지 전송
    for target in target_list:
        memo_dict = {
            "me_send_mb_id": member.mb_id,
            "me_recv_mb_id": target.mb_id,
            "me_memo": me_memo,
            "me_send_ip": request.client.host,
        }
        memo_send = Memo(me_type='send', **memo_dict)
        db.add(memo_send)
        db.commit()
        memo_recv = Memo(me_type='recv', me_send_id=memo_send.me_id, **memo_dict)
        db.add(memo_recv)
        db.commit()

        # 실시간 쪽지 알림
        target.mb_memo_call = member.mb_id
        target.mb_memo_cnt = get_memo_not_read(target.mb_id)
        db.commit()

        # 포인트 소진
        insert_point(request, member.mb_id, use_point * (-1), f"{target.mb_nick}({target.mb_id})님에게 쪽지 발송", "@memo", target.mb_id, "쪽지전송")

    return RedirectResponse(url=f"/bbs/memo?kind=send", status_code=302)


@router.get("/memo_delete/{me_id}", dependencies=[Depends(validate_token)])
async def memo_delete(
    request: Request,
    db: db_session,
    member: Annotated[Member, Depends(get_login_member)],
    me_id: int = Path(...),
    page: int = Query(default=1)
):
    """
    쪽지 삭제
    """
    memo = db.get(Memo, me_id)
    if not memo:
        raise AlertException(status_code=403, detail="쪽지가 존재하지 않습니다.", url="/bbs/memo")
    
    kind = memo.me_type
    memo_mb_id = memo.me_recv_mb_id if kind == "recv" else memo.me_send_mb_id
    if not memo_mb_id == member.mb_id:
        raise AlertException(status_code=403, detail="본인의 쪽지만 삭제 가능합니다.", url="/bbs/memo")
    
    # 실시간 알림 삭제(업데이트)
    if is_none_datetime(memo.me_read_datetime):
        target_member = db.scalar(
            select(Member).where(
                Member.mb_id == memo.me_recv_mb_id,
                Member.mb_memo_call == memo.me_send_mb_id
            )
        )
        if target_member:
            target_member.mb_memo_call = ''
            db.commit()

    db.delete(memo)
    db.commit()

    # 안읽은쪽지 갯수 갱신
    db.execute(
        update(Member)
        .values(mb_memo_cnt=get_memo_not_read(member.mb_id))
        .where(Member.mb_id == member.mb_id)
    )
    db.commit()

    return RedirectResponse(url=f"/bbs/memo?kind={kind}&page={page}", status_code=302)
