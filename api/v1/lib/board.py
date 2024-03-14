from typing_extensions import Dict
from fastapi import Request, HTTPException

from core.models import Board
from lib.board_lib import get_admin_type


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