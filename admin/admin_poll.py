from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from lib.common import *
from common.database import get_db
from common.formclass import PollForm
from lib.plugin.service import get_admin_plugin_menus, get_all_plugin_module_names
from common.models import Poll, PollEtc 

router = APIRouter()
templates = AdminTemplates()
templates.env.globals['getattr'] = getattr
templates.env.globals['get_admin_menus'] = get_admin_menus
templates.env.globals["get_admin_plugin_menus"] = get_admin_plugin_menus
templates.env.globals["get_all_plugin_module_names"] = get_all_plugin_module_names
templates.env.globals['get_member_level_select'] = get_member_level_select
templates.env.globals['get_selected'] = get_selected

MENU_KEY = "200900"


@router.get("/poll_list")
def poll_list(request: Request,
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


@router.post("/poll_list_delete")
def poll_list_delete(
    request: Request,
    db: Session = Depends(get_db),
    token: str = Form(None),
    checks: List[int] = Form(..., alias="chk[]")
):
    """
    투표 목록 삭제
    """
    if not check_token(request, token):
        raise AlertException("토큰이 유효하지 않습니다", 403)

    # in 조건을 사용해서 일괄 삭제
    db.query(Poll).filter(Poll.po_id.in_(checks)).delete()
    db.query(PollEtc).filter(PollEtc.po_id.in_(checks)).delete()
    db.commit()
        
    query_string = generate_query_string(request)

    return RedirectResponse(f"/admin/poll_list?{query_string}", status_code=303)


@router.get("/poll_form")
def poll_form_add(request: Request):
    """
    투표 등록 폼
    """
    return templates.TemplateResponse(
        "poll_form.html", {"request": request, "poll": None}
    )


@router.get("/poll_form/{po_id}")
def poll_form_edit(po_id: int, request: Request, db: Session = Depends(get_db)):
    """
    투표 수정 폼
    """
    poll = db.query(Poll).get(po_id)
    return templates.TemplateResponse(
        "poll_form.html", {"request": request, "poll": poll}
    )


@router.post("/poll_form_update")
def poll_form_update(request: Request,
                        db: Session = Depends(get_db),
                        token: str = Form(...),
                        po_id: int = Form(None),
                        form_data: PollForm = Depends()
                        ):
    """
    투표등록 및 수정 처리
    """
    if not check_token(request, token):
        raise AlertException("토큰이 유효하지 않습니다", 403)
    
    poll = db.query(Poll).filter_by(po_id=po_id).first()
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

    return RedirectResponse(url=f"/admin/poll_form/{poll.po_id}", status_code=302)