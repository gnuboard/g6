"""좋아요/싫어요 API Router"""
from typing_extensions import Annotated
from fastapi import APIRouter, Path, Depends
from fastapi.responses import JSONResponse

from api.v1.dependencies.board import get_board, get_write
from api.v1.dependencies.member import get_current_member
from api.v1.models.ajax import GoodType, ResponseGoodModel
from core.models import Board, Member, WriteBaseModel
from service.ajax import AJAXService

router = APIRouter()


@router.post("/boards/{bo_table}/writes/{wr_id}/{good_type}",
            summary="좋아요/싫어요",
            responses={**AJAXService.responses}
            )
async def board_good(
    service: Annotated[AJAXService, Depends()],
    member: Annotated[Member, Depends(get_current_member)],
    board: Annotated[Board, Depends(get_board)],
    write: Annotated[WriteBaseModel, Depends(get_write)],
    good_type: GoodType = Path(title="좋아요/싫어요", description="좋아요/싫어요")
) -> ResponseGoodModel:
    """
    게시글 좋아요/싫어요 처리
    """
    good_type = good_type.value
    service.validate_board_good_use(board, good_type)
    service.validate_write_owner(write, member, good_type)
    result = service.get_ajax_good_result(board.bo_table, member,
                                          write, good_type)

    return JSONResponse(result, 200)
