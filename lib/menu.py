"""메뉴 관련 기능을 제공하는 모듈입니다."""
from cachetools import cached, LFUCache
from sqlalchemy import func, select

from core.models import Menu
from core.database import DBConnect


@cached(LFUCache(maxsize=128))
def get_menus():
    """사용자페이지 메뉴 조회 함수

    Returns:
        list: 자식메뉴가 포함된 메뉴 list
    """
    with DBConnect().sessionLocal() as db:
        menus = []
        # 부모메뉴 조회
        parent_menus = db.scalars(
            select(Menu)
            .where(func.char_length(Menu.me_code) == 2)
            .order_by(Menu.me_order)
        ).all()

        for menu in parent_menus:
            parent_code = menu.me_code

            # 자식 메뉴 조회
            child_menus = db.scalars(
                select(Menu).where(
                    func.char_length(Menu.me_code) == 4,
                    func.substr(Menu.me_code, 1, 2) == parent_code
                ).order_by(Menu.me_order)
            ).all()

            menu.sub = child_menus
            menus.append(menu)
        return menus
