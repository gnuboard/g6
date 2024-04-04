from typing_extensions import Annotated
from fastapi import APIRouter, Path, Depends
from fastapi.responses import JSONResponse

from core.models import Member
from api.v1.dependencies.board import get_current_member
from api.v1.models import responses
from service.ajax import AjaxGoodService


router = APIRouter()


@router.get("/good/{bo_table}/{wr_id}/{type}",
            summary="좋아요/싫어요",
            responses={**responses}
            )
async def ajax_good(
    ajax_good_service: Annotated[AjaxGoodService, Depends()],
    member: Annotated[Member, Depends(get_current_member)],
    bo_table: str = Path(...),
    wr_id: int = Path(...),
    type: str = Path(...)
):
    """
    게시글 좋아요/싫어요 처리
    """
    ajax_good_service.validate_member(member)
    board = ajax_good_service.get_board(bo_table)
    ajax_good_service.validate_board_good_use(board, type)
    write = ajax_good_service.get_write(bo_table, wr_id)
    ajax_good_service.validate_write_owner(write, member, type)
    result = ajax_good_service.get_ajax_good_result(bo_table, member, write, type)
    return JSONResponse(result, 200)