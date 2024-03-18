import abc
from typing import List, Tuple

from fastapi import Request
from sqlalchemy import exists, update

from core.database import db_session
from core.models import Member, Scrap
from lib.common import dynamic_create_write_table
from lib.service import BaseService


class ScrapService(BaseService):
    """
    회원 스크랩 관련 서비스를 제공하는 종속성 주입 클래스입니다.
    """

    def __init__(self, request: Request, db: db_session) -> None:
        self.request = request
        self.db = db
        self.scrap = None

    def raise_exception(self, status_code: int = 400, detail: str = None, url: str = None) -> None:
        from core.exception import AlertException
        raise AlertException(detail, status_code, url)

    def create_scrap(self, mb_id: str, bo_table: str, wr_id: int) -> None:
        """
        스크랩을 추가합니다.
        """
        exists, message = self.check_scrap_exists(mb_id, bo_table, wr_id)
        if exists:
            self.raise_exception(
                302, message, self.request.url_for('scrap_list'))

        scrap = Scrap(mb_id=mb_id, bo_table=bo_table, wr_id=wr_id)
        self.db.add(scrap)
        self.db.commit()

    def check_scrap_exists(self, mb_id: str, bo_table: str, wr_id: int) -> Tuple[bool, str]:
        """
        스크랩 여부를 확인합니다.
        """
        exist_scrap = self.db.scalar(
            exists(Scrap).where(
                Scrap.mb_id == mb_id,
                Scrap.bo_table == bo_table,
                Scrap.wr_id == wr_id
            ).select()
        )
        if exist_scrap:
            return True, "이미 스크랩하신 글 입니다."
        return False, "스크랩이 존재하지 않습니다."

    def fetch_scrap(self, ms_id: int) -> Scrap:
        """
        쪽지 정보를 데이터베이스에서 조회합니다.
        """
        if self.scrap is None:
            scrap = self.db.get(Scrap, ms_id)
            if not scrap:
                self.raise_exception(404, "스크랩이 존재하지 않습니다.")
            self.scrap = scrap
        return self.scrap

    def fetch_scraps(self, member: Member, offset: int = 0, records_per_page: int = 10):
        """
        스크랩 목록을 조회합니다.
        """
        return (member.scraps
                .order_by(Scrap.ms_id.desc())
                .offset(offset).limit(records_per_page)
                .all())

    def fetch_total_records(self, member: Member) -> int:
        """
        스크랩 목록의 총 개수를 데이터베이스에서 조회합니다.
        """
        return member.scraps.count()

    def update_scrap_count(self, member: Member) -> None:
        """
        회원 테이블의 스크랩 수를 업데이트합니다.
        """
        count = self.fetch_total_records(member)
        self.db.execute(
            update(Member).values(mb_scrap_cnt=count)
            .where(Member.mb_id == member.mb_id)
        )
        self.db.commit()

    def delete_scrap(self, ms_id: int, mb_id: str) -> None:
        """
        스크랩을 삭제합니다.
        """
        scrap = self.fetch_scrap(ms_id)
        if scrap.mb_id != mb_id:
            self.raise_exception(403, "삭제 권한이 없습니다.")
        self.db.delete(scrap)
        self.db.commit()

    def set_subjects(self, scraps: List[Scrap]) -> List[Scrap]:
        """
        스크랩 목록의 게시판/게시글 제목을 설정합니다.
        """
        for scrap in scraps:
            write_model = dynamic_create_write_table(table_name=scrap.bo_table)
            write = self.db.get(write_model, scrap.wr_id)

            scrap.wr_subject = getattr(write, "wr_subject", "") or "[글 없음]"
            scrap.bo_subject = getattr(scrap.board, "bo_subject", "") or "[게시판 없음]"

        return scraps
