from fastapi import APIRouter, Depends, Form, Path, Request
from fastapi.responses import RedirectResponse

from core.database import db_session
from core.formclass import PollForm
from core.models import Poll, PollEtc
from core.template import AdminTemplates
from lib.common import *
from lib.dependencies import common_search_query_params, validate_token
from lib.template_functions import get_member_level_select, get_paging

router = APIRouter()
templates = AdminTemplates()
templates.env.globals['get_member_level_select'] = get_member_level_select

POLL_MENU_KEY = "200900"


@router.get("/poll_list")
async def poll_list(
    request: Request,
    search_params: dict = Depends(common_search_query_params)
):
    """
    투표 목록
    """
    request.session["menu_key"] = POLL_MENU_KEY

    # 투표 목록 데이터 출력
    polls = select_query(
        request,
        Poll,
        search_params,
        default_sst="po_id",
        default_sod="desc",
    )
    for poll in polls['rows']:
        # 투표 항목별 투표수 합계
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


@router.post("/poll_list_delete", dependencies=[Depends(validate_token)])
async def poll_list_delete(
    request: Request,
    db: db_session,
    checks: List[int] = Form(..., alias="chk[]")
):
    """
    투표 목록 삭제
    """
    # in 조건을 사용해서 일괄 삭제
    db.execute(delete(Poll).where(Poll.po_id.in_(checks)))
    db.execute(delete(PollEtc).where(PollEtc.po_id.in_(checks)))
    db.commit()

    url = "/admin/poll_list"
    query_params = request.query_params
    return RedirectResponse(set_url_query_params(url, query_params), 303)


@router.get("/poll_form")
async def poll_form_add(request: Request):
    """
    투표 등록 폼
    """
    context = {"request": request, "poll": None}
    return templates.TemplateResponse("poll_form.html", context)


@router.get("/poll_form/{po_id}")
async def poll_form_edit(
    request: Request,
    db: db_session,
    po_id: int = Path(...)
):
    """
    투표 수정 폼
    """
    poll = db.get(Poll, po_id)
    context = {"request": request, "poll": poll}
    return templates.TemplateResponse("poll_form.html", context)


@router.post("/poll_form_update", dependencies=[Depends(validate_token)])
async def poll_form_update(
    request: Request,
    db: db_session,
    po_id: int = Form(None),
    form_data: PollForm = Depends()
):
    """
    투표등록 및 수정 처리
    """
    poll = db.get(Poll, po_id)
    # 투표 수정
    if poll:
        # 데이터 수정 후 commit
        for field, value in form_data.__dict__.items():
            setattr(poll, field, value)
        db.commit()
    # 투표 등록
    else:
        poll = Poll(**form_data.__dict__)
        db.add(poll)
        db.commit()

        # 기존캐시 삭제
        lfu_cache.update({"poll": None})

    url = f"/admin/poll_form/{poll.po_id}"
    query_params = request.query_params
    return RedirectResponse(set_url_query_params(url, query_params), 302)
