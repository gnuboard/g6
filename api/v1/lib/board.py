from typing_extensions import Dict
from fastapi import Request

from core.models import Board
from lib.board_lib import get_admin_type


def is_possible_level(
    request: Request,
    member_info: Dict,
    board: Board
):
    member_level = member_info["member_level"]
    mb_id = member_info["mb_id"]
    admin_type = get_admin_type(request, mb_id, board=board)
    if admin_type:
        return True
    return member_level >= board.bo_list_level