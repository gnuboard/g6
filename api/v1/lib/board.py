from typing_extensions import Dict, Annotated
from fastapi import Request, HTTPException, Path, Depends

from core.models import Board, Member
from core.database import db_session
from lib.board_lib import get_admin_type
from lib.member import MemberDetails
from service.board import GroupBoardListService
from api.v1.dependencies.member import get_current_member_optional


class GroupBoardListServiceAPI(GroupBoardListService):
    """
    그룹의 게시판 목록을 얻기 위한 API 클래스
      - 이 클래스는 API와 관련된 특정 예외 처리를 오버라이드하여 구현합니다.
    """

    def __init__(
        self,
        request: Request,
        db: db_session,
        gr_id: Annotated[str, Path(...)],
        member: Annotated[Member, Depends(get_current_member_optional)],
    ):
        super().__init__(request, db, gr_id)
        self.member = MemberDetails(request, member, group=self.group)

    def raise_exception(self, status_code: int, detail: str = None):
        raise HTTPException(status_code=status_code, detail=detail)


def is_possible_level(
    request: Request,
    member_info: Dict,
    board: Board,
    level_type: str,
):
    member_level = member_info["member_level"]
    mb_id = member_info["mb_id"]
    admin_type = get_admin_type(request, mb_id, board=board)
    board_level = getattr(board, level_type)
    if board_level is None:
        raise HTTPException(status_code=404, detail=f"level_type: {level_type} > 존재하지 않는 속성입니다.")
    if admin_type:
        return True
    return member_level >= board_level


def is_possible_point(
    member_info: Dict,
    action_point: int,
):
    member = member_info["member"]
    if not action_point:
        return True
    
    if not member:
        return False

    return member.mb_point + action_point >= 0    