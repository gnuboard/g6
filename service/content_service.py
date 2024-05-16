"""컨텐츠 관련 기능을 제공하는 모듈입니다."""
from fastapi import Request
from sqlalchemy import func, select

from core.database import db_session
from core.exception import AlertException
from core.models import Content
from service import BaseService


class ContentService(BaseService):
    """
    컨텐츠 관련 서비스를 제공하는 종속성 주입 클래스입니다.
    """

    def __init__(self, request: Request, db: db_session):
        self.request = request
        self.db = db

    def raise_exception(self, status_code: int = 400, detail: str = None, url: str = None):
        raise AlertException(detail, status_code, url)

    def fetch_total_records(self) -> int:
        """
        컨텐츠 전체 레코드 수를 조회합니다.
        """
        return self.db.scalar(select(func.count(Content.co_id)))

    def fetch_content(self, co_id: str):
        """
        컨텐츠 1건을 데이터베이스에서 조회합니다.
        """
        return self.db.get(Content, co_id)

    def fetch_contents(self, offset: int, per_page: int):
        """
        컨텐츠 목록을 데이터베이스에서 조회합니다.
        """
        return self.db.scalars(
            select(Content).offset(offset).limit(per_page)
        ).all()

    def read_content(self, co_id: str):
        """
        컨텐츠를 불러옵니다.
        """
        content = self.fetch_content(co_id)
        if not content:
            self.raise_exception(404, f"{co_id} : 컨텐츠 아이디가 존재하지 않습니다.")
        return content

    def read_contents(self, offset: int, per_page: int):
        """
        컨텐츠 목록을 불러옵니다.
        """
        return self.fetch_contents(offset, per_page)
