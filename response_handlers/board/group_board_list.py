from fastapi import Request, HTTPException
from sqlalchemy import select

from core.database import db_session
from core.models import Board, Group, Member
from lib.board_lib import get_admin_type
from .base_handler import BoardService


class GroupBoardListService(BoardService):
    """
    그룹의 게시판 목록을 얻기 위한 클래스
    """

    def __init__(
        self,
        request: Request,
        db: db_session,
        gr_id: str,
        member: Member,
    ):
        self.request = request
        self.db = db
        self.gr_id = gr_id
        self.group = self.get_group()
        self.member = member
        self.mb_id = getattr(member, "mb_id", None)
        self.member_level = getattr(member, "mb_level") if member else 1
        self.admin_type = get_admin_type(request, self.mb_id, group=self.group)
        self.login_member = self.member
        self.login_member_id = self.mb_id
        self.login_member_admin_type = self.admin_type
        self.login_member_level = self.member_level

    def get_group(self):
        """게시판 그룹 정보 조회"""
        group = self.db.get(Group, self.gr_id)
        if not group:
            self.raise_exception(detail=f"{self.gr_id} : 존재하지 않는 게시판그룹입니다.", status_code=404)
        return group

    def check_mobile_only(self):
        """모바일 전용 게시판인지 확인"""
        # FIXME: 모바일/PC 분기처리
        if self.admin_type:
            return
        if self.request.state.device == "mobile":
            self.raise_exception(detail=f"{self.group.gr_subject} 그룹은 모바일에서만 접근할 수 있습니다.", status_code=403)

    def get_boards_in_group(self):
        """게시판 그룹에 속한 게시판 목록 조회"""
        # 그룹별 게시판 목록 조회
        query = (
            select(Board)
            .where(
                Board.gr_id == self.gr_id,
                Board.bo_list_level <= self.member_level,
                Board.bo_device != 'mobile'
            )
            .order_by(Board.bo_order)
        )
        # 인증게시판 제외
        if not self.admin_type:
            query = query.filter_by(bo_use_cert="")

        boards = self.db.scalars(query).all()
        return boards


class GroupBoardListServiceAPI(GroupBoardListService):
    """
    그룹의 게시판 목록을 얻기 위한 API 클래스
      - 이 클래스는 API와 관련된 특정 예외 처리를 오버라이드하여 구현합니다.
    """

    def raise_exception(self, status_code: int, detail: str = None):
        raise HTTPException(status_code=status_code, detail=detail)