from typing import List

from fastapi import Request
from sqlalchemy import select

from core.database import db_session
from core.models import Board, Group, Member
from lib.member import MemberDetails
from . import BoardService


class GroupService(BoardService):
    """
    그룹 게시판 서비스 클래스
    """

    def __init__(self, request: Request, db: db_session):
        self.request = request
        self.db = db
        self.device = request.state.device

    def get_groups(self) -> List[Group]:
        """게시판 그룹 목록 조회"""
        query = select(Group).order_by(Group.gr_order)
        groups = self.db.scalars(query).all()
        return groups

    def get_group(self, gr_id: str) -> Group:
        """게시판 그룹 정보 조회"""
        group = self.db.get(Group, gr_id)
        if not group:
            self.raise_exception(detail=f"{gr_id} : 존재하지 않는 게시판그룹입니다.", status_code=404)
        return group

    def check_device_only(self, group: Group, login_member: Member) -> None:
        """그룹의 접속기기 확인"""
        member = MemberDetails(self.request, login_member, group=group)
        if member.admin_type:
            return
        if group.gr_device not in [self.device, "both"]:
            self.raise_exception(
                status_code=403,
                detail=f"{group.gr_subject} 그룹은 {group.gr_device}에서만 접근할 수 있습니다."
            )

    def get_boards_in_group(self, group: Group, login_member: Member) -> List[Board]:
        """게시판 그룹에 속한 게시판 목록 조회"""
        member = MemberDetails(self.request, login_member, group=group)
        # 그룹별 게시판 목록 조회
        query = group.boards.where(
            Board.bo_list_level <= member.level,
            Board.bo_device.in_([self.device, "both"]),
        ).order_by(Board.bo_order)

        # 인증게시판 제외
        if not member.admin_type:
            query = query.where(Board.bo_use_cert=="")

        boards = self.db.scalars(query).all()
        return boards
