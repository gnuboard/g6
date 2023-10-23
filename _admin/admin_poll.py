from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import text
from sqlalchemy.orm import Session as DBSession
from database import get_db
from common import *

from dataclassform import PollForm
from models import Poll, PollEtc 

router = APIRouter()
templates = Jinja2Templates(directory=ADMIN_TEMPLATES_DIR)
templates.env.globals['getattr'] = getattr
templates.env.globals['get_admin_menus'] = get_admin_menus
templates.env.globals['get_member_level_select'] = get_member_level_select
templates.env.globals['get_selected'] = get_selected
templates.env.globals["generate_one_time_token"] = generate_one_time_token

MENU_KEY = "200900"


@router.get("/poll_list")
def poll_list(request: Request, db: DBSession = Depends(get_db),
                 search_params: dict = Depends(common_search_query_params)):
    """
    투표 목록
    """
    request.session["menu_key"] = MENU_KEY

    # 투표 목록 데이터 출력
    polls = select_query(
        request,
        Poll,
        search_params,
        default_sst="po_id",
        default_sod="desc",
    )
    for poll in polls['rows']:
        for i in range(1, 10):
            poll.sum_po_cnt = getattr(poll, "sum_po_cnt", 0) + getattr(poll, f"po_cnt{i}", 0)

    total_count = polls['total_count']
    context = {
        "request": request,
        "polls": polls['rows'],
        "total_count": total_count,
        "paging": get_paging(request, search_params['current_page'], total_count),
    }
    return templates.TemplateResponse("poll_list.html", context)


@router.post("/poll_list_update")
def poll_list_update(request: Request,
                    token: str = Form(None),
                    db: DBSession = Depends(get_db),
                    checks: List[int] = Form(..., alias="chk[]")):
    """
    투표 목록 삭제
    """
    if not validate_one_time_token(token, 'delete'):
        return templates.TemplateResponse("alert.html", {"request": request, "errors": ["토큰이 유효하지 않습니다. 새로고침후 다시 시도해 주세요."]})

    # in 조건을 사용해서 일괄 삭제
    db.query(Poll).filter(Poll.po_id.in_(checks)).delete()
    db.query(PollEtc).filter(PollEtc.po_id.in_(checks)).delete()
    db.commit()
        
    query_string = generate_query_string(request)

    return RedirectResponse(f"/admin/poll_list?{query_string}", status_code=303)


@router.get("/poll_form")
def poll_form_add(request: Request, db: DBSession = Depends(get_db)):
    """
    투표 등록 폼
    """
    return templates.TemplateResponse(
        "poll_form.html", {"request": request, "poll": None}
    )


@router.get("/poll_form/{po_id}")
def poll_form_edit(po_id: int, request: Request, db: DBSession = Depends(get_db)):
    """
    투표 수정 폼
    """
    poll = db.query(Poll).get(po_id)
    return templates.TemplateResponse(
        "poll_form.html", {"request": request, "poll": poll}
    )


@router.post("/poll_form_update")
def poll_form_update(request: Request,
                        db: DBSession = Depends(get_db),
                        token: str = Form(...),
                        po_id: int = Form(None),
                        form_data: PollForm = Depends()
                        ):
    """
    투표등록 및 수정 처리
    """
    if validate_one_time_token(token, 'insert'): # 토큰에 등록돤 action이 insert라면 신규 등록
        # 투표 등록
        poll = Poll(**form_data.__dict__)
        db.add(poll)
        db.commit()

    elif validate_one_time_token(token, 'update'):  # 토큰에 등록된  action이 update라면 수정
        poll = db.query(Poll).get(po_id)
        if not poll:
            raise HTTPException(status_code=404, detail=f"{po_id} : 투표 아이디가 존재하지 않습니다.")

        # 데이터 수정 후 commit
        for field, value in form_data.__dict__.items():
            setattr(poll, field, value)
        db.commit()
    
    else: # 토큰 검사 실패
        raise HTTPException(status_code=404, detail=f"{token} : 토큰이 존재하지 않습니다.")

    return RedirectResponse(url=f"/admin/poll_form/{poll.po_id}", status_code=302)