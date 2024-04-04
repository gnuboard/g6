from typing_extensions import Annotated
from fastapi import APIRouter, Form, Path, Request, Depends
from fastapi.responses import JSONResponse

from service.ajax_good import AjaxGoodService

router = APIRouter()


@router.post("/good/{bo_table}/{wr_id}/{type}")
async def ajax_good(
    request: Request,
    ajax_good_service: Annotated[AjaxGoodService, Depends()],
    token: str = Form(...),
    bo_table: str = Path(...),
    wr_id: int = Path(...),
    type: str = Path(...)
):
    """
    게시글 좋아요/싫어요 처리
    """
    member = request.state.login_member
    ajax_good_service.validate_member(member)
    ajax_good_service.validate_token(token)
    board = ajax_good_service.get_board(bo_table)
    ajax_good_service.validate_board_good_use(board, type)
    write = ajax_good_service.get_write(bo_table, wr_id)
    ajax_good_service.validate_write_owner(write, member, type)
    result = ajax_good_service.get_ajax_good_result(bo_table, member, write, type)
    return JSONResponse(result, 200)
