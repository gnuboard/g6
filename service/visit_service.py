"""방문자 서비스를 제공하는 모듈입니다."""
from datetime import date, datetime, timedelta
import re
from typing import Union

from fastapi import Request
from sqlalchemy import exists, func, select
from user_agents import parse

from core.database import db_session
from core.models import Config, Visit, VisitSum
from lib.common import get_client_ip


class VisitService:
    """
    방문자 관련 서비스를 제공하는 종속성 주입 클래스입니다.
    """

    def __init__(self, request: Request, db: db_session) -> None:
        self.request = request
        self.db = db
        self.today = date.today()

    @staticmethod
    def parse_visit_data(visit_data: str = None) -> dict:
        """방문자 수 데이터를 파싱합니다."""
        visit = {"today": 0, "yesterday": 0, "max": 0, "total": 0}
        if not visit_data:
            return visit

        visit_list = re.findall(r'\d+', visit_data)
        visit["today"] = int(visit_list[0])
        visit["yesterday"] = int(visit_list[1])
        visit["max"] = int(visit_list[2])
        visit["total"] = int(visit_list[3])

        return visit

    def create_visit_record(self) -> Union[Visit, None]:
        """
        방문자 접속 이력 생성 함수
        - 새로운 접속 이력 생성
        - 방문자 합계 테이블 갱신
        - 기본설정 테이블에 방문자 수 기록
        """
        vi_ip = get_client_ip(self.request)
        if self.is_exists_visit(vi_ip, self.today):
            return None

        referer = self.request.headers.get("referer", "")
        user_agent = self.request.headers.get("User-Agent", "")
        browser, os, device = self._parse_user_agent(user_agent)
        visit = Visit(
            vi_ip=vi_ip,
            vi_date=self.today,
            vi_time=datetime.now().time(),
            vi_referer=referer,
            vi_agent=user_agent,
            vi_browser=browser,
            vi_os=os,
            vi_device=device,
        )
        self.db.add(visit)
        self.db.commit()
        self.db.refresh(visit)

        self._update_visit_sum()
        self._update_config()

        return visit

    def is_exists_visit(self, ip: str, visit_date: date) -> bool:
        """오늘의 접속이 이미 기록되어 있는지 확인합니다."""
        return self.db.scalar(
            exists().where(
                Visit.vi_date == visit_date,
                Visit.vi_ip == ip
            ).select()
        )

    def _parse_user_agent(self, user_agent: str):
        """User-Agent 문자열을 파싱하여 브라우저, OS, 디바이스 정보를 반환합니다."""
        ua = parse(user_agent)
        browser = getattr(ua.browser, 'family', 'unknown')
        os = getattr(ua.os, 'family', 'unknown')
        device = 'pc' if ua.is_pc else 'mobile' if ua.is_mobile else 'tablet' if ua.is_tablet else 'unknown'
        return browser, os, device

    def _update_config(self) -> None:
        """기본설정 테이블 > 방문자 수 갱신 함수"""
        today = self.db.scalar(
            select(VisitSum.vs_count).where(VisitSum.vs_date == self.today)
        ) or 0
        yesterday = self.db.scalar(
            select(VisitSum.vs_count)
            .where(VisitSum.vs_date == self.today - timedelta(days=1))
        ) or 0
        visit_max = self.db.scalar(func.max(VisitSum.vs_count)) or 0
        visit_total = self.db.scalar(func.sum(VisitSum.vs_count)) or 0

        config = self.db.scalars(select(Config)).first()
        config.cf_visit = f"오늘:{today},어제:{yesterday},최대:{visit_max},전체:{visit_total}"
        self.db.commit()

    def _update_visit_sum(self) -> None:
        """방문자 합계 테이블 갱신 함수"""
        visit_count_today = self.db.scalar(
            select(func.count(Visit.vi_id))
            .where(Visit.vi_date == self.today)
        )
        self.db.merge(VisitSum(vs_date=self.today, vs_count=visit_count_today))
        self.db.commit()
