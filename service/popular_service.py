"""인기 검색어 관련 기능을 제공하는 서비스 모듈입니다."""
from datetime import date, datetime, timedelta
from typing import List

from cachetools import LRUCache, cached
from cachetools.keys import hashkey
from fastapi import Request
from sqlalchemy import delete, desc, exists, func, select
from sqlalchemy.exc import SQLAlchemyError
from core.database import db_session
from core.models import Popular
from lib.common import get_client_ip
from service import BaseService


class PopularService(BaseService):
    """인기 검색어 관련 서비스를 제공하는 종속성 주입 클래스입니다."""

    def __init__(self, db: db_session):
        self.db = db

    @classmethod
    async def async_init(cls, db: db_session):
        instance = cls(db)
        return instance

    def raise_exception(self, status_code: int, detail: str = None):
        pass

    @cached(LRUCache(maxsize=128),
            key=lambda self, limit=10, day=3: hashkey("populars", limit, day))
    def fetch_populars(self, limit: int = 10, day: int = 3) -> List[Popular]:
        """
        현재 날짜와 day일 전 날짜 사이의 인기검색어를 조회한다.
        - LFU(Least Frequently Used)캐시를 사용하여 조회한다.

        Args:
            limit (int, optional): 조회 갯수. Defaults to 7.
            day (int, optional): 오늘부터 {day}일 전. Defaults to 3.

        Returns:
            List[Popular]: 인기검색어 리스트

        """
        today = datetime.now()
        before_day = today - timedelta(days=day)
        populars = self.db.execute(
            select(Popular.pp_word, func.count(Popular.pp_word).label('count'))
            .where(
                Popular.pp_word != '',
                Popular.pp_date >= before_day,
                Popular.pp_date <= today
            )
            .group_by(Popular.pp_word)
            .order_by(desc('count'), Popular.pp_word)
            .limit(limit)
        ).all()

        return populars

    def create_popular(self, request: Request, fields: str, word: str) -> None:
        """인기검색어를 생성합니다."""
        try:
            if not word or not fields:
                self.raise_exception(400, "검색어가 없습니다.")
                return None

            if "mb_id" in fields:  # 회원아이디로 검색은 제외
                self.raise_exception(400, "회원아이디로 검색은 제외합니다.")
                return None

            today_date = datetime.now()
            exists_popular = self.db.scalar(
                exists(Popular)
                .where(
                    Popular.pp_word == word,
                    Popular.pp_date == today_date.strftime("%Y-%m-%d")
                ).select()
            )

            if exists_popular:
                self.raise_exception(409, "이미 등록된 검색어입니다.")
                return None

            # 현재 날짜의 인기검색어가 없으면 새로 등록한다.
            popular = Popular(
                pp_word=word,
                pp_date=today_date,
                pp_ip=get_client_ip(request))
            self.db.add(popular)
            self.db.commit()
        except SQLAlchemyError:
            pass
        return None

    def delete_populars(self, base_date: date) -> int:
        """기준 날짜 이전의 인기검색어를 삭제합니다."""
        result = self.db.execute(
            delete(Popular).where(Popular.pp_date < base_date)
        )
        self.db.commit()
        return result.rowcount
