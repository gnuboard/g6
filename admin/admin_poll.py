"""설문조사 관리 Template Router"""
from typing import List
from typing_extensions import Annotated

from fastapi import APIRouter, Depends, Form, Path, Request
from fastapi.responses import RedirectResponse

from sqlalchemy import delete

from core.database import db_session
from core.exception import AlertException
from core.formclass import PollForm
from core.models import Poll, PollEtc
from core.template import AdminTemplates
from lib.common import select_query, set_url_query_params
from lib.dependency.dependencies import common_search_query_params, validate_token
from lib.template_functions import get_member_level_select, get_paging
from service.poll_service import PollService

router = APIRouter()
templates = AdminTemplates()
templates.env.globals['get_member_level_select'] = get_member_level_select

POLL_MENU_KEY = "200900"


@router.get("/poll_list")
async def poll_list(
    request: Request,
    db: db_session,
    search_params: dict = Depends(common_search_query_params)
):
    """
    설문조사 목록
    """
    request.session["menu_key"] = POLL_MENU_KEY

    # 설문조사 목록 데이터 출력
    polls = select_query(
        request,
        db,
        Poll,
        search_params,
        default_sst="po_id",
        default_sod="desc",
    )
    for poll in polls['rows']:
        # 설문조사 항목별 투표수 합계
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
    service: Annotated[PollService, Depends()],
    checks: List[int] = Form(..., alias="chk[]")
):
    """
    설문조사 목록 삭제
    """
    # in 조건을 사용해서 일괄 삭제
    db.execute(delete(Poll).where(Poll.po_id.in_(checks)))
    db.execute(delete(PollEtc).where(PollEtc.po_id.in_(checks)))
    db.commit()

    # 기존캐시 삭제
    service.fetch_latest_poll.cache_clear()

    url = "/admin/poll_list"
    query_params = request.query_params
    return RedirectResponse(set_url_query_params(url, query_params), 303)


@router.get("/poll_form")
async def poll_form_add(request: Request):
    """
    설문조사 등록 폼
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
    설문조사 수정 폼
    """
    poll = db.get(Poll, po_id)
    context = {"request": request, "poll": poll}
    return templates.TemplateResponse("poll_form.html", context)


@router.post("/poll_form_update", dependencies=[Depends(validate_token)])
async def poll_form_update(
    request: Request,
    db: db_session,
    service: Annotated[PollService, Depends()],
    po_id: int = Form(None),
    form_data: PollForm = Depends()
):
    """
    설문조사 등록 및 수정 처리
    """

    # 설문조사 수정
    if po_id:
        poll = db.get(Poll, po_id)
        if not poll:
            raise AlertException("설문조사가 존재하지 않습니다.", 404)

        # 데이터 수정 후 commit
        for field, value in form_data.__dict__.items():
            if value is None:
                value = ""
            setattr(poll, field, value)
        db.commit()

    # 설문조사 등록
    else:
        poll = Poll(**form_data.__dict__)
        db.add(poll)
        db.commit()

    # 기존캐시 삭제
    service.fetch_latest_poll.cache_clear()

    url = f"/admin/poll_form/{poll.po_id}"
    query_params = request.query_params
    return RedirectResponse(set_url_query_params(url, query_params), 302)
