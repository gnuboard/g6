from fastapi import Request

from core.database import db_session
from core.models import Board, Member
from lib.board_lib import BoardConfig, get_admin_type
from lib.common import dynamic_create_write_table


class BoardRouter:

    def __init__(
        self,
        request: Request,
        db: db_session,
        bo_table: str,
        board: Board,
        member: Member
    ):
        self.request = request
        self.config = request.state.config
        self.db = db
        self.bo_table = bo_table
        self.board = board
        self.board_config = BoardConfig(request, self.board)
        self.write_model = dynamic_create_write_table(bo_table)
        self.categories = self.board_config.get_category_list()
        self.member = member
        self.mb_id = getattr(member, "mb_id", None)
        self.member_level = getattr(member, "mb_level") if member else 1
        self.admin_type = get_admin_type(request, self.mb_id, board=self.board)