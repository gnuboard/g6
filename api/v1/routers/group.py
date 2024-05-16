from typing_extensions import Annotated
from fastapi import APIRouter, Depends

from api.v1.models.response import response_401, response_422
from api.v1.models.board import ResponseGroupBoardsModel
from api.v1.service.board import GroupBoardListServiceAPI


router = APIRouter()


@router.get("/{gr_id}/boards",
            summary="게시판그룹 목록 조회",
            responses={**response_401, **response_422}
            )
async def api_group_board_list(
    service: Annotated[GroupBoardListServiceAPI, Depends(GroupBoardListServiceAPI.async_init)],
) -> ResponseGroupBoardsModel:
    """
    게시판그룹의 모든 게시판 목록을 보여줍니다.
    """
    group = service.group
    service.check_mobile_only()
    boards = service.get_boards_in_group()
    return {"group": group, "boards": boards}