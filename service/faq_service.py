"""FAQ 관련 기능을 제공하는 모듈입니다."""
from typing import List

from fastapi import Request
from sqlalchemy import select

from core.database import db_session
from core.exception import AlertException
from core.models import Faq, FaqMaster
from service import BaseService


class FaqService(BaseService):
    """
    FAQ 관련 서비스를 제공하는 종속성 주입 클래스입니다.
    """

    def __init__(self, request: Request, db: db_session):
        self.request = request
        self.db = db

    def raise_exception(self, status_code: int = 400, detail: str = None, url: str = None):
        raise AlertException(detail, status_code, url)

    def fetch_faq_master(self, fm_id: int) -> FaqMaster:
        """
        FAQ 분류 1건을 데이터베이스에서 조회합니다.
        """
        return self.db.get(FaqMaster, fm_id)

    def fetch_faq_masters(self) -> List[FaqMaster]:
        """
        FAQ 분류 목록을 데이터베이스에서 조회합니다.
        """
        return self.db.scalars(
            select(FaqMaster).order_by(
                FaqMaster.fm_order.asc(),
                FaqMaster.fm_id.asc()
            )
        ).all()

    def fetch_faqs(self, faq_master: FaqMaster, stx: str = None) -> List[Faq]:
        """
        FAQ 목록을 불러옵니다.
        """
        query = faq_master.related_faqs.order_by(Faq.fa_order.asc())
        if stx:
            query = query.where(
                Faq.fa_subject.like(f"%{stx}%")
                | Faq.fa_content.like(f"%{stx}%")
            )
        return self.db.scalars(query).all()

    def read_faq_masters(self) -> List[FaqMaster]:
        """
        FAQ 분류 목록을 불러옵니다.
        """
        faq_masters = self.fetch_faq_masters()
        if not faq_masters:
            self.raise_exception(404, "FAQ가 등록되지 않았습니다.")
        return faq_masters

    def read_faq_master(self, fm_id: int) -> FaqMaster:
        """
        FAQ 분류를 불러옵니다.
        """
        faq_master = self.fetch_faq_master(fm_id)
        if not faq_master:
            self.raise_exception(404, f"{fm_id} : FAQ 분류 정보가 존재하지 않습니다.")
        return faq_master

    def read_faqs(self, faq_master: FaqMaster, stx: str = None) -> List[Faq]:
        """
        FAQ 목록을 불러옵니다.
        """
        faqs = self.fetch_faqs(faq_master, stx)
        return faqs
