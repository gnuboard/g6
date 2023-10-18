from common import *
from database import get_db
from fastapi import APIRouter, Depends, Form, Path, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

import models

router = APIRouter()
templates = Jinja2Templates(directory=TEMPLATES_DIR)
# 파이썬 함수 및 변수를 jinja2 에서 사용할 수 있도록 등록
templates.env.globals["now"] = now
templates.env.globals['getattr'] = getattr
templates.env.globals["generate_one_time_token"] = generate_one_time_token
templates.env.globals["generate_query_string"] = generate_query_string


# TODO : Capcha
# TODO : 포인트 유효성검사&소진
# TODO : user_sideview 추가


@router.get("/list")
def memo_list(request: Request, db: Session = Depends(get_db),
                kind: str = Query(default="recv"),
                current_page: int = Query(default=1, alias="page")):
    """
    쪽지 목록
    """
    member = request.state.context['member']
    if not member:
        errors = ["로그인 후 이용 가능합니다."]
        return templates.TemplateResponse("alert.html", {"request": request, "errors": errors, "url": "/bbs/login/"})

    model = models.Memo
    join_model = models.Member
    target_column = model.me_send_mb_id if kind == "recv" else model.me_recv_mb_id
    mb_column = model.me_recv_mb_id if kind == "recv" else model.me_send_mb_id
    query = db.query(model, join_model.mb_id, join_model.mb_nick).outerjoin(join_model, join_model.mb_id==target_column).filter(
        mb_column == member.mb_id,
        model.me_type == kind
    ).order_by(model.me_id.desc())

    # 페이징 처리
    records_per_page = request.state.config.cf_page_rows
    total_records = query.count()
    offset = (current_page - 1) * records_per_page
    memos = query.offset(offset).limit(records_per_page).all()
    
    context = {
        "request": request,
        "kind": kind,
        "memos": memos,
        "total_records": total_records,
        "page": current_page,
        "paging": get_paging(request, current_page, total_records, f"/memo/list?kind={ kind }&page="),
    }
    
    return templates.TemplateResponse(f"memo/{request.state.device}/memo_list.html", context)


@router.get("/view/{me_id}")
def memo_view(request: Request, db: Session = Depends(get_db), me_id: int = Path(...)):
    """
    쪽지 상세
    """
    member = request.state.context['member']
    if not member:
        errors = ["로그인 후 이용 가능합니다."]
        return templates.TemplateResponse("alert.html", {"request": request, "errors": errors, "url": "/bbs/login/"})
    
    model = models.Memo
    
    # 본인 쪽지 조회
    memo = db.query(model).get(me_id)
    if not memo:
        errors = ["쪽지가 존재하지 않습니다."]
        return templates.TemplateResponse("alert.html", {"request": request, "errors": errors, "url": "/memo/list"})
    
    kind = memo.me_type
    target_mb_id = memo.me_send_mb_id if kind == "recv" else memo.me_recv_mb_id
    memo_mb_id = memo.me_recv_mb_id if kind == "recv" else memo.me_send_mb_id
    memo_mb_column = model.me_recv_mb_id if kind == "recv" else model.me_send_mb_id

    if not memo_mb_id == member.mb_id:
        errors = ["본인의 쪽지만 조회 가능합니다."]
        return templates.TemplateResponse("alert.html", {"request": request, "errors": errors, "url": "/memo/list"})

    # 상대방 정보 조회
    target = db.query(models.Member).filter(models.Member.mb_id==target_mb_id).first()

    # 이전,다음 쪽지 조회
    prev_memo = db.query(model).filter(
        model.me_id < me_id,
        model.me_type == kind,
        memo_mb_column == member.mb_id
    ).order_by(model.me_id.desc()).first()
    next_memo = db.query(model).filter(
        model.me_id > me_id,
        model.me_type == kind,
        memo_mb_column == member.mb_id
    ).order_by(model.me_id.asc()).first()

    # 받은 쪽지 읽음처리
    if kind == "recv" and memo.me_read_datetime is None:
        now = datetime.now()
        memo.me_read_datetime = now
        send_memo = db.query(model).filter(model.me_send_id==memo.me_id).first()
        if send_memo:
            send_memo.me_read_datetime = now
        
        db.commit()

    context = {
        "request": request,
        "kind": memo.me_type,
        "memo": memo,
        "target": target,
        "prev_memo": prev_memo,
        "next_memo": next_memo,
    }
    return templates.TemplateResponse(f"memo/{request.state.device}/memo_view.html", context)


@router.get("/form")
def memo_form(request: Request, db: Session = Depends(get_db),
    me_recv_mb_id : str = Query(default=None),
    me_id: int = Query(default=None)
):
    """
    쪽지 작성
    """
    member = request.state.context['member']
    if not member:
        errors = ["로그인 후 이용 가능합니다."]
        return templates.TemplateResponse("alert.html", {"request": request, "errors": errors, "url": "/bbs/login/"})

    target = None
    if me_recv_mb_id:
        # 쪽지를 전송할 회원 정보 조회
        target = db.query(models.Member).filter(models.Member.mb_id==me_recv_mb_id).first()
    
    memo = None
    if me_id:
        # 답장할 쪽지의 정보 조회
        model = models.Memo
        memo = db.query(model).get(me_id)

    context = {
        "request": request,
        "target": target,
        "memo": memo,
    }
    return templates.TemplateResponse(f"memo/{request.state.device}/memo_form.html", context)


# TODO : 개발 진행 중 => 전송아이디 구분 & 유효성검사
@router.post("/form")
def memo_update(request: Request, db: Session = Depends(get_db),
    token: str = Form(...),
    me_recv_mb_id : str = Form(...),
    me_memo: str = Form(...)
):
    """
    쪽지 전송
    """
    if not validate_one_time_token(token, 'create'):
        raise HTTPException(status_code=404, detail=f"{token} : 토큰이 존재하지 않습니다.")

    member = request.state.context['member']
    if not member:
        errors = ["로그인 후 이용 가능합니다."]
        return templates.TemplateResponse("alert.html", {"request": request, "errors": errors, "url": "/bbs/login/"})
    
    memo_dict = {
        "me_send_mb_id": member.mb_id,
        "me_recv_mb_id": me_recv_mb_id,
        "me_memo": me_memo,
        "me_send_ip": request.client.host,
    }
    memo_send = models.Memo(me_type='send', **memo_dict)
    db.add(memo_send)
    db.commit()
    memo_recv = models.Memo(me_type='recv', me_send_id=memo_send.me_id, **memo_dict)
    db.add(memo_recv)
    db.commit()
    
    return RedirectResponse(url=f"/memo/list?kind=send", status_code=302)


# TODO : 개발 진행 중
@router.get("/delete/{me_id}")
def memo_delete(request: Request, db: Session = Depends(get_db), me_id: int = Path(...), token:str = Query(...)):
    """
    쪽지 삭제
    """
    if not validate_one_time_token(token, 'delete'):
        raise HTTPException(status_code=404, detail=f"{token} : 토큰이 존재하지 않습니다.")
    
    member = request.state.context['member']
    if not member:
        errors = ["로그인 후 이용 가능합니다."]
        return templates.TemplateResponse("alert.html", {"request": request, "errors": errors, "url": "/bbs/login/"})
    
    model = models.Memo
    memo = db.query(model).get(me_id)
    if not memo:
        errors = ["쪽지가 존재하지 않습니다."]
        return templates.TemplateResponse("alert.html", {"request": request, "errors": errors, "url": "/memo/list"})
    
    kind = memo.me_type
    memo_mb_id = memo.me_recv_mb_id if kind == "recv" else memo.me_send_mb_id
    if not memo_mb_id == member.mb_id:
        errors = ["본인의 쪽지만 삭제 가능합니다."]
        return templates.TemplateResponse("alert.html", {"request": request, "errors": errors, "url": "/memo/list"})
    
    db.delete(memo)
    db.commit()
    
    return RedirectResponse(url=f"/memo/list", status_code=302)