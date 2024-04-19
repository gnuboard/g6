from fastapi import APIRouter, Request, Depends, Query
from fastapi.encoders import jsonable_encoder

from core.database import db_session
from core.models import Member
from api.v1.models.response import response_401, response_403, response_422
from api.v1.dependencies.board import get_current_member
from api.v1.models.board import ResponseBoardModel, ResponseWriteSearchModel, ResponseSearchModel
from service.search import SearchServiceAPI


router = APIRouter()

@router.get("/search",
            summary="게시판 검색",
            responses={**response_401, **response_403, **response_422}
            )
async def api_search(
    request: Request,
    db: db_session,
    member: Member = Depends(get_current_member),
    gr_id: str = Query(None),
    sfl: str = Query("wr_subject||wr_content", title="검색필드", description="검색필드"),
    stx: str = Query(..., title="검색어", description="검색어"),
    sop: str = Query("and", title="검색연산자", description="검색연산자", pattern="and|or"),
    onetable: str = Query(None, title="통합검색", description="통합검색"),
) -> ResponseSearchModel:
    """
    게시판 검색
    - 게시판 종류와, 개별 게시판에 있는 게시글을 검색합니다.
    """
    search_service = SearchServiceAPI(
        request, db, member, gr_id, onetable
    )
    boards = search_service.get_boards()
    searched_result = search_service.search(boards, sfl, stx, sop)
    total_search_count = searched_result["total_search_count"]
    boards = searched_result["boards"]

    return {
        "onetable": onetable,
        "total_search_count": total_search_count,
        "boards": boards,
    }