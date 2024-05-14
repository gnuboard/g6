"""전체검색 Template Router"""
from typing_extensions import Annotated
from fastapi import APIRouter, Depends, Request, Query

from core.template import UserTemplates
from lib.template_filters import search_font
from service.popular_service import PopularService
from service.search import SearchService

router = APIRouter()
templates = UserTemplates()
templates.env.filters["search_font"] = search_font


@router.get("/search")
async def search(
    request: Request,
    search_service: Annotated[SearchService, Depends(SearchService.async_init)],
    popular_service: Annotated[PopularService, Depends()],
    sfl: str = Query("wr_subject||wr_content"),
    stx: str = Query(...),
    sop: str = Query("and"),
    onetable: str = Query(None),
):
    """
    게시판 검색
    """
    groups = search_service.get_groups()
    boards = search_service.get_boards()
    searched_result = search_service.search(boards, sfl, stx, sop)
    total_search_count = searched_result["total_search_count"]
    boards = searched_result["boards"]

    # 검색 단어를 인기검색어에 등록
    popular_service.create_popular(request, sfl, stx)

    context = {
        "request": request,
        "onetable": onetable,
        "total_search_count": total_search_count,
        "groups": groups,
        "boards": boards,
    }
    return templates.TemplateResponse("/bbs/search.html", context)
