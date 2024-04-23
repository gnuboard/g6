from typing_extensions import Union, List
from fastapi import Request
from sqlalchemy import select

from core.database import db_session
from core.models import Board, WriteBaseModel, Group
from core.exception import AlertException
from lib.board_lib import BoardConfig
from lib.member import MemberDetails
from lib.common import dynamic_create_write_table
from service import BaseService


class BoardService(BaseService, BoardConfig):
    """게시판 관련 기반 서비스 클래스"""

    def __init__(
        self,
        request: Request,
        db: db_session,
        bo_table: str,
    ):
        self.db = db
        board = self.get_board(bo_table)
        super().__init__(request, board)
        self.bo_table = bo_table
        self.write_model = dynamic_create_write_table(bo_table)
        self.categories = self.get_category_list()
        self.member = MemberDetails(request, request.state.login_member, board=self.board)

    def raise_exception(self, status_code: int, detail: str = None, url: str = None):
        raise AlertException(status_code=status_code, detail=detail, url=url)

    def set_wr_name(self, member: MemberDetails = None, default_name: str = None) -> str:
        """실명사용 여부를 확인 후 실명이면 이름을, 아니면 닉네임을 반환한다.

        Args:
            board (Board): 게시판 object
            member (MemberDetails): 회원정보 object 

        Returns:
            str: 이름 또는 닉네임
        """
        if member.mb_id:
            if self.board.bo_use_name:
                return member.mb_name
            else:
                return member.mb_nick
        elif default_name:
            return default_name
        else:
            self.raise_exception(detail="로그인 세션 만료, 비회원 글쓰기시 작성자 이름 미기재 등의 비정상적인 접근입니다.", status_code=400)

    def validate_admin_authority(self):
        """게시판 관리자 검증"""
        if not self.member.admin_type:
            self.raise_exception(detail="게시판 관리자 이상 접근이 가능합니다.", status_code=403)

    def get_board(self, bo_table: str) -> Board:
        """게시판 정보를 가져온다."""
        board = self.db.get(Board, bo_table)
        if not board:
            self.raise_exception(detail="존재하지 않는 게시판입니다.", status_code=404)
        return board

    def get_admin_board_list(self) -> List[Board]:
        """관리자가 속한 게시판 목록을 가져옵니다."""
        query = select(Board).join(Group).order_by(Board.gr_id, Board.bo_order, Board.bo_table)
        if self.member.admin_type == "group":
            query = query.where(Group.gr_admin == self.member.mb_id)
        elif self.member.admin_type == "board":
            query = query.where(Board.bo_admin == self.member.mb_id)
        return self.db.scalars(query).all()

    def get_write(self, wr_id: Union[int, str]) -> WriteBaseModel:
        """게시글(댓글)을 가져온다."""
        if not isinstance(wr_id, int) and not wr_id.isdigit():
            self.raise_exception(detail="올바르지 않은 게시글 번호입니다.", status_code=400)

        write = self.db.get(self.write_model, wr_id)
        if not write:
            self.raise_exception(detail="존재하지 않는 게시글(댓글)입니다.", status_code=404)

        return write