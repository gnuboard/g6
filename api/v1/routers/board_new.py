"""새글(최신 게시글) API Router"""
from typing_extensions import Annotated, List
from fastapi import (
    APIRouter, Depends, HTTPException, Query,
    Body, Request, Path
)

from api.v1.models.pagination import PagenationRequest
from lib.board_lib import get_bo_table_list
from api.v1.dependencies.member import get_current_member
from api.v1.models.response import response_401, response_422
from api.v1.models.board import (
    BoardNewViewType, RequestBoardNewWrites, ResponseNormalModel,
    ResponseBoardNewListModel, ResponseTotalBoardNewListModel,
    ResponseWriteModel
)
from lib.common import get_paging_info
from service.board_new import BoardNewServiceAPI

router = APIRouter()


@router.get("",
            summary="최신 게시글 목록",
            responses={**response_401, **response_422})
async def api_board_new_list(
    service: Annotated[BoardNewServiceAPI, Depends()],
    pagination: Annotated[PagenationRequest, Depends()],
    gr_id: str = Query(None, title="게시판 그룹 id", description="게시판 그룹 id"),
    view: BoardNewViewType = Query(None, title="게시판 view", description="게시판 view"),
    mb_id: str = Query(None, title="회원 id", description="회원 id"),
) -> ResponseBoardNewListModel:
    """
    최신 게시글 목록
    """
    view_type = view.value if view else None
    query = service.get_query(gr_id, mb_id, view_type)
    current_page = pagination.page
    per_page = pagination.per_page
    offset = service.get_offset(current_page)
    board_news = service.get_board_news(query, offset, per_page)
    total_records = service.get_total_count(query)
    service.arrange_borad_news_data(board_news, total_records, offset)
    paging_info = get_paging_info(current_page, per_page, total_records)

    content = {
        "total_records": total_records,
        "total_pages": paging_info["total_pages"],
        "board_news": board_news,
        "current_page": current_page,
    }
    return content


@router.get("/writes",
            summary="최신글 조회",
            responses={**response_401, **response_422}
            )
async def api_latest_posts(
    service: Annotated[BoardNewServiceAPI, Depends()],
    data: RequestBoardNewWrites = Depends(),
) -> ResponseTotalBoardNewListModel:
    """
    모든 게시판의 최신글을 조회합니다.
    """
    bo_table_list = get_bo_table_list()
    latest_posts = service.get_latest_posts(bo_table_list, data.view_type.value, data.rows)
    return latest_posts


@router.get("/writes/{bo_table}",
            summary="최신글 게시판별 조회",
            responses={**response_401, **response_422}
            )
async def api_latest_posts_by_board(
    service: Annotated[BoardNewServiceAPI, Depends()],
    bo_table: Annotated[str, Path(..., title="게시판 코드", description="게시판 코드")],
    data: RequestBoardNewWrites = Depends(),
) -> List[ResponseWriteModel]:
    """
    최신글을 게시판별로 조회합니다.
    """
    latest_posts = service.get_latest_posts([bo_table], data.view_type.value, data.rows)
    return latest_posts[bo_table]


@router.post("/delete",
             summary="최신 게시글을 삭제",
             responses={**response_401, **response_422})
async def api_new_delete(
    request: Request,
    service: Annotated[BoardNewServiceAPI, Depends()],
    member: Annotated[str, Depends(get_current_member)],
    bn_ids: Annotated[List[int], Body(..., title="삭제할 최신글 id 리스트")],
) -> ResponseNormalModel:
    """
    최신 게시글을 삭제한다.

    ### Request Body
    - **bn_ids**: 삭제할 최신글 id 리스트 (예시: [1, 2, 3])
    """
    admin_id = getattr(request.state.config, "cf_admin")
    if member.mb_id != admin_id:
        raise HTTPException(403, "최고관리자만 접근 가능합니다.")

    service.delete_board_news(bn_ids)

    return {"result": "deleted"}
