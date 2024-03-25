from enum import Enum
from typing_extensions import Union
from fastapi import Request, HTTPException

from core.database import db_session
from core.models import Board, Member
from core.exception import AlertException
from lib.board_lib import BoardConfig, get_admin_type
from lib.template_filters import number_format
from lib.common import dynamic_create_write_table


class PointEnum(Enum):
    WRITE = {"attr": "bo_write_point", "func": "is_write_point", "action": "글 작성"}

class BoardBase(BoardConfig):
    """게시판 관련 router 함수에 사용될 기본 클래스"""

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
        self.ClassException = None  # 템플릿, API 클래스에서 인스턴스 생성시 set_exception_type 메소드를 통해 정의합니다.

    def set_exception_type(self, exception_type: Union[HTTPException, AlertException]):
        """
        예외처리 클래스를 설정합니다.
        - 템플릿, API 클래스에서 인스턴스 생성시 해당 메소드를 통해 정의합니다.
        """
        self.ClassException = exception_type

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

    def validate_possible_point(self, point_type: PointEnum):
        """포인트에 따른 접근 권한을 검사합니다."""
        if not self.config.cf_use_point:
            return

        point = getattr(self.board, point_type.value["attr"])
        validate_func = getattr(self, point_type.value["func"])
    
        if not validate_func():
            point = number_format(abs(point))
            message = f"{point_type.value['action']}에 필요한 포인트({point})가 부족합니다. "
            if not self.member:
                message += "로그인 후 다시 시도해주세요."
            raise self.ClassException(status_code=403, detail=message)
