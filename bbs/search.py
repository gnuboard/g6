from fastapi import APIRouter, Request, Query

from core.database import db_session
from core.template import UserTemplates
from lib.board_lib import *
from lib.common import *
from lib.template_filters import search_font
from response_handlers.search import SearchService


router = APIRouter()
templates = UserTemplates()
templates.env.filters["search_font"] = search_font


@router.get("/search")
async def search(
    request: Request,
    db: db_session,
    gr_id: str = Query(None),
    sfl: str = Query("wr_subject||wr_content"),
    stx: str = Query(...),
    sop: str = Query("and"),
    onetable: str = Query(None),
):
    """
    게시판 검색
    """
    member = request.state.login_member
    search_service = SearchService(
        request, db, member, gr_id, onetable
    )
    groups = search_service.get_groups()
    boards = search_service.get_boards()
    searched_result = search_service.search(boards, sfl, stx, sop)
    total_search_count = searched_result["total_search_count"]
    boards = searched_result["boards"]

    context = {
        "request": request,
        "onetable": onetable,
        "total_search_count": total_search_count,
        "groups": groups,
        "boards": boards,
    }
    return templates.TemplateResponse("/bbs/search.html", context)
