from typing_extensions import Annotated, List
from fastapi import APIRouter, Depends, Query, Body

from api.v1.models.response import response_401, response_422
from api.v1.models.board import (
    BoardNewViewType, ResponseNormalModel, ResponseBoardNewListModel
)
from service.board_new import BoardNewServiceAPI

router = APIRouter()


@router.get("",
            summary="최신 게시글 목록",
            responses={**response_401, **response_422}
            )
async def api_board_new_list(
    service: Annotated[BoardNewServiceAPI, Depends()],
    gr_id: str = Query(None, title="게시판 그룹 id", description="게시판 그룹 id"),
    view: BoardNewViewType = Query(None, title="게시판 view", description="게시판 view"),
    mb_id: str = Query(None, title="회원 id", description="회원 id"),
    current_page: int = Query(1, alias="page", title="현재 페이지", description="현재 페이지")
) -> ResponseBoardNewListModel:
    """
    최신 게시글 목록
    """
    view_type = view.value if view else None
    query = service.get_query(gr_id, mb_id, view_type)
    offset = service.get_offset(current_page)
    board_news = service.get_board_news(query, offset)
    total_count = service.get_total_count(query)
    service.arrange_borad_news_data(board_news, total_count, offset)

    content = {
        "total_count": total_count,
        "board_news": board_news,
        "current_page": current_page,
    }
    return content


@router.post("/delete",
            summary="최신 게시글을 삭제",
            responses={**response_401, **response_422}
            )
async def api_new_delete(
    service: Annotated[BoardNewServiceAPI, Depends()],
    bn_ids: Annotated[List[int], Body(..., title="삭제할 최신글 id 리스트")],
) -> ResponseNormalModel:
    """
    최신 게시글을 삭제한다.

    ### Request Body
    - **bn_ids**: 삭제할 최신글 id 리스트 (예시: [1, 2, 3])
    """
    service.delete_board_news(bn_ids)

    return {"result": "deleted"}
