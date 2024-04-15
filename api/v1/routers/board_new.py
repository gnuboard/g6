from typing_extensions import Annotated
from fastapi import APIRouter, Depends, Query, Body

from api.v1.models.response import response_401, response_422
from api.v1.models.board import ResponseNormalModel, ResponseBoardNewListModel
from service.board_new import BoardNewServiceAPI


router = APIRouter()


@router.get("/new",
            summary="최신 게시글 목록",
            responses={**response_401, **response_422}
            )
async def api_board_new_list(
    board_new_service: Annotated[BoardNewServiceAPI, Depends()],
    gr_id: str = Query(None),
    view: str = Query(None),
    mb_id: str = Query(None),
    current_page: int = Query(1, alias="page")
) -> ResponseBoardNewListModel:
    """
    최신 게시글 목록

    ### Request Body
    - 삭제할 최신글 id 리스트 (예: [1, 2, 3]
    """
    query = board_new_service.get_query(gr_id, mb_id, view)
    offset = board_new_service.get_offset(current_page)
    board_news = board_new_service.get_board_news(query, offset)
    total_count = board_new_service.get_total_count(query)
    board_new_service.arrange_borad_news_data(board_news, total_count, offset)

    content = {
        "total_count": total_count,
        "board_news": board_news,
        "current_page": current_page,
    }
    return content


@router.post("/new_delete",
            summary="최신 게시글을 삭제",
            responses={**response_401, **response_422}
             )
async def api_new_delete(
    board_new_service: Annotated[BoardNewServiceAPI, Depends()],
    bn_ids: list = Body(...),
) -> ResponseNormalModel:
    """
    최신 게시글을 삭제한다.
    """
    board_new_service.delete_board_news(bn_ids)
    return {"result": "deleted"}