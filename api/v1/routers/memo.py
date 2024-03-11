from typing import List
from typing_extensions import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from sqlalchemy import select, update

from core.database import db_session
from core.models import Member, Memo
from lib.common import get_client_ip, get_memo_not_read, is_none_datetime
from lib.point import insert_point

from api.v1.models import responses
from api.v1.dependencies.member import get_current_member
from api.v1.models.memo import CreateMemoModel, ResponseMemoModel
from api.v1.dependencies.memo import validate_create_memo

router = APIRouter()


@router.get("/{mb_id}/memos",
            summary="회원 메시지 목록 조회",
            response_model=List[ResponseMemoModel],
            responses={**responses})
async def read_member_memos(
    mb_id: Annotated[str, Path(title="회원 아이디")],
    current_member: Annotated[Member, Depends(get_current_member)],
    me_type: Annotated[str, Query(title="메시지 유형", description="recv: 받은 메시지, send: 보낸 메시지",
                                  pattern="^(recv|send)?$")] = "recv"
):
    """회원 메시지 목록을 조회합니다."""
    if mb_id != current_member.mb_id:
        raise HTTPException(status_code=403, detail="본인의 회원정보만 조회할 수 있습니다.")

    if me_type not in {"recv", "send"}:
        raise HTTPException(status_code=400, detail="메시지 유형이 올바르지 않습니다.")

    if me_type == "send":
        return current_member.send_memos.where(Memo.me_type == me_type).all()
    else:
        return current_member.recv_memos.where(Memo.me_type == me_type).all()


@router.get("/{mb_id}/memos/{me_id}",
            summary="회원 메시지 조회",
            response_model=ResponseMemoModel,
            responses={**responses})
async def read_member_memo(
    db: db_session,
    mb_id: Annotated[str, Path(title="회원 아이디")],
    me_id: Annotated[int, Path(title="메시지 아이디")],
    current_member: Annotated[Member, Depends(get_current_member)]
):
    """회원 메시지를 조회합니다."""
    # if mb_id != current_member.mb_id:
    #     raise HTTPException(status_code=403, detail="본인의 회원정보만 조회할 수 있습니다.")
    memo = db.get(Memo, me_id)
    if memo is None:
        raise HTTPException(status_code=404, detail="쪽지를 찾을 수 없습니다.")

    kind = memo.me_type
    memo.target_mb_id = memo.me_send_mb_id if kind == "recv" else memo.me_recv_mb_id
    memo_mb_id = memo.me_recv_mb_id if kind == "recv" else memo.me_send_mb_id

    if not memo_mb_id == current_member.mb_id:
        raise HTTPException(status_code=403, detail="본인의 쪽지만 조회 가능합니다.")

    return memo


@router.post("/{mb_id}/memos",
             summary="회원 메시지 전송",
             #  response_model=ResponseMemoModel,
             responses={**responses})
async def create_member_memo(
    request: Request,
    db: db_session,
    mb_id: Annotated[str, Path(title="회원 아이디")],
    current_member: Annotated[Member, Depends(get_current_member)],
    data: Annotated[CreateMemoModel, Depends(validate_create_memo)]
):
    """회원 메시지를 전송합니다."""
    config = request.state.config

    # me_recv_mb_id 공백 제거
    target_list = []
    error_list = []
    for mb_id in data._mb_ids:
        # 쪽지를 전송할 회원 정보 조회
        target = db.scalar(select(Member).filter(Member.mb_id == mb_id))
        if target and target.mb_open and not (target.mb_leave_date or target.mb_intercept_date):
            target_list.append(target)
        else:
            error_list.append(mb_id)

    if error_list:
        raise HTTPException(
            status_code=400,
            detail=f"{','.join(error_list)} : 존재(또는 정보공개)하지 않는 회원이거나 탈퇴/차단된 회원입니다.\\n쪽지를 발송하지 않았습니다.")

    # 총 사용 포인트 체크
    use_point = int(config.cf_memo_send_point)
    total_use_point = use_point * len(target_list)
    if total_use_point > 0:
        if current_member.mb_point < total_use_point:
            HTTPException(
                status_code=403,
                detail=f"보유하신 포인트({current_member.mb_point})가 부족합니다.\\n쪽지를 발송하지 않았습니다.")

    # 전송대상의 목록을 순회하며 쪽지 전송
    for target in target_list:
        memo_dict = {
            "me_send_mb_id": current_member.mb_id,
            "me_recv_mb_id": target.mb_id,
            "me_memo": data.me_memo,
            "me_send_ip": get_client_ip(request),
        }
        memo_send = Memo(me_type='send', **memo_dict)
        db.add(memo_send)
        db.commit()
        memo_recv = Memo(me_type='recv', me_send_id=memo_send.me_id, **memo_dict)
        db.add(memo_recv)
        db.commit()

        # 실시간 쪽지 알림
        target.mb_memo_call = current_member.mb_id
        target.mb_memo_cnt = get_memo_not_read(target.mb_id)
        db.commit()

        # 포인트 소진
        insert_point(request, current_member.mb_id, use_point * (-1), f"{target.mb_nick}({target.mb_id})님에게 쪽지 발송", "@memo", target.mb_id, "쪽지전송")

    return {"detail": "쪽지를 발송하였습니다."}


@router.delete("/{mb_id}/memos/{me_id}",
               summary="회원 메시지 삭제",
               responses={**responses})
async def delete_member_memo(
    db: db_session,
    mb_id: Annotated[str, Path(title="회원 아이디")],
    me_id: Annotated[int, Path(title="메시지 아이디")],
    current_member: Annotated[Member, Depends(get_current_member)]
):
    """회원 메시지를 삭제합니다."""
    # if mb_id != current_member.mb_id:
    #     raise HTTPException(status_code=403, detail="본인의 쪽지만 삭제할 수 있습니다.")

    memo = db.get(Memo, me_id)
    if memo is None:
        raise HTTPException(status_code=404, detail="쪽지를 찾을 수 없습니다.")
    
    kind = memo.me_type
    memo_mb_id = memo.me_recv_mb_id if kind == "recv" else memo.me_send_mb_id
    if not memo_mb_id == current_member.mb_id:
        raise HTTPException(status_code=403, detail="본인의 쪽지만 삭제 가능합니다.")
    
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
        .values(mb_memo_cnt=get_memo_not_read(current_member.mb_id))
        .where(Member.mb_id == current_member.mb_id)
    )

    db.delete(memo)
    db.commit()

    return {"detail": "쪽지를 삭제하였습니다."}
