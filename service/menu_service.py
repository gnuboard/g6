"""메뉴 서비스를 제공하는 모듈입니다."""
from typing import List
from cachetools import LRUCache, cached
from cachetools.keys import hashkey

from fastapi import Request
from sqlalchemy import func, select

from core.database import db_session
from core.exception import AlertException
from core.models import Menu
from service import BaseService


class MenuService(BaseService):
    """
    메뉴 관련 서비스를 제공하는 종속성 주입 클래스입니다.
    """

    def __init__(self, request: Request, db: db_session) -> None:
        self.request = request
        self.db = db

    def raise_exception(self, status_code: int = 400, detail: str = None, url: str = None) -> None:
        raise AlertException(detail, status_code, url)

    @cached(LRUCache(maxsize=128), key=lambda _: hashkey("menus"))
    def fetch_menus(self) -> List[Menu]:
        """사용자페이지 메뉴 조회 함수"""
        menus = []
        # 부모메뉴 조회
        parent_menus = self.db.scalars(
            select(Menu)
            .where(func.char_length(Menu.me_code) == 2)
            .order_by(Menu.me_order)
        ).all()

        for menu in parent_menus:
            parent_code = menu.me_code
            # 자식 메뉴 조회
            child_menus = self.db.scalars(
                select(Menu).where(
                    func.char_length(Menu.me_code) == 4,
                    func.substr(Menu.me_code, 1, 2) == parent_code
                ).order_by(Menu.me_order)
            ).all()

            menu.sub = child_menus
            menus.append(menu)
        return menus
