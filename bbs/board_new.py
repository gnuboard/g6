from typing_extensions import Annotated
from fastapi import APIRouter, Depends, Form, Query
from fastapi.responses import RedirectResponse

from core.template import UserTemplates
from lib.common import set_url_query_params
from lib.dependencies import validate_token
from lib.template_functions import get_group_select, get_paging
from service.board_new import BoardNewService

router = APIRouter()
templates = UserTemplates()
templates.env.globals["get_group_select"] = get_group_select


@router.get("/new")
async def board_new_list(
    board_new_service: Annotated[BoardNewService, Depends()],
    gr_id: str = Query(None),
    view: str = Query(None),
    mb_id: str = Query(None),
    current_page: int = Query(1, alias="page")
):
    """
    최신 게시글 목록
    """
    query = board_new_service.get_query(gr_id, mb_id, view)
    offset = board_new_service.get_offset(current_page)
    board_news = board_new_service.get_board_news(query, offset)
    total_count = board_new_service.get_total_count(query)
    board_new_service.arrange_borad_news_data(board_news, total_count, offset)

    context = {
        "request": board_new_service.request,
        "total_count": total_count,
        "board_news": board_news,
        "current_page": current_page,
        "paging": get_paging(board_new_service.request, current_page, total_count, board_new_service.page_rows)
    }
    return templates.TemplateResponse("/new/basic/new_list.html", context)


@router.post("/new_delete", dependencies=[Depends(validate_token)])
async def new_delete(
    board_new_service: Annotated[BoardNewService, Depends()],
    bn_ids: list = Form(..., alias="chk_bn_id[]"),
):
    """
    게시글을 삭제한다.
    """
    board_new_service.delete_board_news(bn_ids)
    url = "/bbs/new"
    query_params = board_new_service.request.query_params
    return RedirectResponse(set_url_query_params(url, query_params), 303)