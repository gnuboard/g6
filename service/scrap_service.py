"""스크랩 서비스를 제공하는 모듈입니다."""
from typing import List
from typing_extensions import Annotated

from fastapi import Depends, Request
from sqlalchemy import select

from core.database import db_session
from core.exception import AlertException
from core.models import Member, Scrap
from lib.common import dynamic_create_write_table
from service import BaseService
from service.member_service import MemberService


class ScrapService(BaseService):
    """
    회원 스크랩 관련 서비스를 제공하는 종속성 주입 클래스입니다.
    """

    def __init__(self,
                 request: Request,
                 db: db_session,
                 member_servce: Annotated[MemberService, Depends()]
                 ) -> None:
        self.request = request
        self.db = db
        self.member_servce = member_servce

    def raise_exception(self, status_code: int = 400, detail: str = None, url: str = None) -> None:
        raise AlertException(detail, status_code, url)

    def fetch_total_records(self, member: Member) -> int:
        """
        스크랩 목록의 총 개수를 데이터베이스에서 조회합니다.
        """
        # request.state.login_member로 받는 경우
        # 세션이 달라져서 현재 세션으로 재 연결해야함
        member = self.member_servce.fetch_member_by_id(member.mb_id)
        return member.scraps.count()

    def fetch_scraps(self, member: Member, offset: int = 0, records_per_page: int = 10):
        """
        스크랩 목록을 조회합니다.
        """
        return (member.scraps
                .order_by(Scrap.ms_id.desc())
                .offset(offset).limit(records_per_page)
                .all())

    def fetch_scrap(self, ms_id: int) -> Scrap:
        """
        스크랩 정보를 데이터베이스에서 조회합니다.
        """
        return self.db.get(Scrap, ms_id)

    def fetch_scrap_by_board(self, mb_id: str, bo_table: str, wr_id: int) -> Scrap:
        """
        게시글 정보로 스크랩 정보를 데이터베이스에서 조회합니다.
        """
        return self.db.scalar(
            select(Scrap).where(
                Scrap.mb_id == mb_id,
                Scrap.bo_table == bo_table,
                Scrap.wr_id == wr_id
            )
        )

    def create_scrap(self, member: Member, bo_table: str, wr_id: int) -> None:
        """
        스크랩을 추가합니다.
        """
        scrap = Scrap(mb_id=member.mb_id, bo_table=bo_table, wr_id=wr_id)
        self.db.add(scrap)
        self.db.commit()

    def read_scrap(self, ms_id: int) -> Scrap:
        """
        스크랩 정보를 조회합니다.
        """
        scrap = self.fetch_scrap(ms_id)
        if not scrap:
            self.raise_exception(404, "스크랩이 존재하지 않습니다.")
        return scrap

    def update_scrap_count(self, member: Member) -> None:
        """
        회원 테이블의 스크랩 수를 업데이트합니다.
        """
        member.mb_scrap_cnt = self.fetch_total_records(member)
        self.db.commit()

    def delete_scrap(self, scrap: Scrap) -> None:
        """
        스크랩을 삭제합니다.
        """
        self.db.delete(scrap)
        self.db.commit()

    def set_subjects(self, scraps: List[Scrap]) -> List[Scrap]:
        """
        스크랩 목록의 게시판/게시글 제목을 설정합니다.
        """
        for scrap in scraps:
            board = scrap.board
            write = None
            if board:
                write_model = dynamic_create_write_table(table_name=board.bo_table)
                write = self.db.scalar(
                    select(write_model).where(write_model.wr_id == scrap.wr_id)
                )

            scrap.wr_subject = getattr(write, "wr_subject", "[글 없음]")
            scrap.bo_subject = getattr(board, "bo_subject", "[게시판 없음]")

        return scraps


class ValidateScrapService(BaseService):
    """
    스크랩 서비스의 유효성을 검증하는 클래스입니다.
    """

    def __init__(self,
                 request: Request,
                 db: db_session,
                 scrap_service: Annotated[ScrapService, Depends()]) -> None:
        self.request = request
        self.db = db
        self.scrap_service = scrap_service

    def raise_exception(self, status_code: int, detail: str = None, url: str = None):
        raise AlertException(detail, status_code, url)

    def is_exists_scrap(self, member: Member, bo_table: str, wr_id: int) -> None:
        """
        스크랩이 이미 존재하는지 확인합니다.
        """
        exists_scrap = self.scrap_service.fetch_scrap_by_board(
            member.mb_id, bo_table, wr_id)
        if exists_scrap:
            self.raise_exception(
                status_code=409,
                detail="이미 스크랩하신 글 입니다.",
                url=self.request.url_for('scrap_list'))

    def is_owner_scrap(self, scrap: Scrap, member: Member) -> None:
        """
        스크랩의 소유자인지 확인합니다.
        """
        if scrap.mb_id != member.mb_id:
            self.raise_exception(
                status_code=403,
                detail="권한이 없습니다.",
                url=self.request.url_for('scrap_list'))
