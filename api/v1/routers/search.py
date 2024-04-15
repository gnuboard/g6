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
    sfl: str = Query("wr_subject||wr_content"),
    stx: str = Query(...),
    sop: str = Query("and"),
    onetable: str = Query(None),
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

    # board 및 write에 대해 지정해준 API 속성만 필터링
    filtered_boards = []
    for board in boards:
        board_json = jsonable_encoder(board)
        board_json_writes = board_json["writes"]
        filtered_writes = []
        for write in board_json_writes:
            write_api = ResponseWriteSearchModel.model_validate(write)
            filtered_writes.append(write_api)
        board_api = dict(ResponseBoardModel.model_validate(board_json))
        board_api["writes"] = filtered_writes
        filtered_boards.append(board_api)

    return {
        "onetable": onetable,
        "total_search_count": total_search_count,
        "boards": filtered_boards,
    }