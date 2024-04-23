"""현재 접속자 관련 기능을 제공하는 서비스 모듈입니다."""
from datetime import datetime, timedelta
from typing import Any

from fastapi import Request
from sqlalchemy import Row, Select, Sequence, func, select

from core.database import db_session
from core.exception import AlertException
from core.models import Login, Member
from service import BaseService


class CurrentConnectService(BaseService):
    """
    
    현재 접속자 관련 서비스를 제공하는 종속성 주입 클래스입니다.
    """

    def __init__(self, request: Request, db: db_session) -> None:
        self.request = request
        self.db = db
        self.admin = getattr(request.state.config, "cf_admin", "admin")
        login_minute = getattr(request.state.config, "cf_login_minutes", 10)
        self.base_date = datetime.now() - timedelta(minutes=login_minute)

    def raise_exception(self, status_code: int, detail: str = None, url: str = None):
        return AlertException(status_code=status_code, detail=detail, url=url)

    def fetch_total_records(self, only_member: bool = False) -> int:
        """현재 접속중인 회원의 총 수를 반환합니다."""
        query = self._base_query(only_member)

        return self.db.scalar(query.add_columns(func.count(Login.mb_id)))

    def fetch_corrent_connects(self, only_member: bool = False,
                             offset: int = 0, per_page: int = 10) -> Sequence[Row[Any]]:
        """현재 접속중인 회원 목록을 반환합니다."""
        query = self._base_query(only_member)

        return self.db.execute(
            query.add_columns(Login, Member)
            .outerjoin(Member, Login.mb_id == Member.mb_id)
            .order_by(Login.lo_datetime.desc())
            .offset(offset).limit(per_page)
        ).all()

    def _base_query(self, only_member: bool = False) -> Select:
        """기본 쿼리를 반환합니다."""
        query = select().where(
            Login.mb_id != self.admin,
            Login.lo_ip != "",
            Login.lo_datetime > self.base_date
        )

        if only_member:
            query = query.where(Login.mb_id != "")

        return query
