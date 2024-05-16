from typing_extensions import Annotated
from fastapi import APIRouter, Form, Path, Request, Depends
from fastapi.responses import JSONResponse

from service.ajax import AJAXService

router = APIRouter()


@router.post("/good/{bo_table}/{wr_id}/{type}")
async def ajax_good(
    request: Request,
    service: Annotated[AJAXService, Depends(AJAXService.async_init)],
    token: str = Form(...),
    bo_table: str = Path(...),
    wr_id: int = Path(...),
    type: str = Path(...)
):
    """
    게시글 좋아요/싫어요 처리
    """
    member = request.state.login_member
    service.validate_member(member)
    service.validate_token(token)
    board = service.get_board(bo_table)
    service.validate_board_good_use(board, type)
    write = service.get_write(bo_table, wr_id)
    service.validate_write_owner(write, member, type)
    result = service.get_ajax_good_result(bo_table, member, write, type)
    return JSONResponse(result, 200)
