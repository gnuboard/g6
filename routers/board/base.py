from fastapi import Request

from core.database import db_session
from core.models import Board, Member
from lib.board_lib import BoardConfig, get_admin_type
from lib.common import dynamic_create_write_table


class BoardRouter(BoardConfig):

    def __init__(
        self,
        request: Request,
        db: db_session,
        bo_table: str,
        board: Board,
        member: Member
    ):
        super().__init__(request, board)
        self.db = db
        self.bo_table = bo_table
        self.write_model = dynamic_create_write_table(bo_table)
        self.categories = self.get_category_list()
        self.member = member
        self.mb_id = getattr(member, "mb_id", None)
        self.member_level = getattr(member, "mb_level") if member else 1
        self.admin_type = get_admin_type(request, self.mb_id, board=self.board)
        self.login_member = self.member
        self.login_member_id = self.mb_id
        self.login_member_admin_type = self.admin_type

    def set_wr_name(self, member: Member = None, default_name: str = None) -> str:
        """실명사용 여부를 확인 후 실명이면 이름을, 아니면 닉네임을 반환한다.

        Args:
            board (Board): 게시판 object
            member (Member): 회원 object 

        Returns:
            str: 이름 또는 닉네임
        """
        if member:
            if self.board.bo_use_name:
                return member.mb_name
            else:
                return member.mb_nick
        elif default_name:
            return default_name
        else:
            raise self.ClassException(detail="로그인 세션 만료, 비회원 글쓰기시 작성자 이름 미기재 등의 비정상적인 접근입니다.", status_code=400)
