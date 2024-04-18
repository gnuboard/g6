from typing_extensions import Annotated
from fastapi import APIRouter, Path, Depends
from fastapi.responses import JSONResponse

from core.models import Member
from api.v1.dependencies.board import get_current_member
from service.ajax import AJAXService


router = APIRouter()


@router.get("/good/{bo_table}/{wr_id}/{type}",
            summary="좋아요/싫어요",
            responses={**AJAXService.responses}
            )
async def ajax_good(
    ajax_service: Annotated[AJAXService, Depends()],
    member: Annotated[Member, Depends(get_current_member)],
    bo_table: str = Path(..., title="게시판 테이블명", description="게시판 테이블명"),
    wr_id: int = Path(..., title="글 아이디", description="글 아이디"),
    type: str = Path(..., title="좋아요/싫어요", description="좋아요/싫어요", pattern="good|nogood")
):
    """
    게시글 좋아요/싫어요 처리
    """
    ajax_service.validate_member(member)
    board = ajax_service.get_board(bo_table)
    ajax_service.validate_board_good_use(board, type)
    write = ajax_service.get_write(bo_table, wr_id)
    ajax_service.validate_write_owner(write, member, type)
    result = ajax_service.get_ajax_good_result(bo_table, member, write, type)
    return JSONResponse(result, 200)