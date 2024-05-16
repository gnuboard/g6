"""전체검색 API Router"""
from typing_extensions import Annotated

from fastapi import APIRouter, Depends, Query

from api.v1.models.response import response_401, response_403, response_422
from api.v1.models.board import ResponseSearchModel
from service.search import SearchServiceAPI

router = APIRouter()


@router.get("/search",
            summary="게시판 검색",
            responses={**response_401, **response_403, **response_422}
            )
async def api_search(
    service: Annotated[SearchServiceAPI, Depends(SearchServiceAPI.async_init)],
    sfl: str = Query("wr_subject||wr_content", title="검색필드", description="검색필드"),
    stx: str = Query(..., title="검색어", description="검색어"),
    sop: str = Query("and", title="검색연산자", description="검색연산자", pattern="and|or"),
    onetable: str = Query(None, title="통합검색", description="통합검색"),
) -> ResponseSearchModel:
    """
    게시판 검색
    - 게시판 종류와, 개별 게시판에 있는 게시글을 검색합니다.
    """
    boards = service.get_boards()
    searched_result = service.search(boards, sfl, stx, sop)
    total_search_count = searched_result["total_search_count"]
    boards = searched_result["boards"]

    return {
        "onetable": onetable,
        "total_search_count": total_search_count,
        "boards": boards,
    }
