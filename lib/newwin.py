"""레이어팝업 관련 기능을 제공하는 파일입니다."""
from typing import List

from cachetools import cached, LFUCache
from fastapi import Request

from core.database import DBConnect
from core.models import NewWin
from service.newwin_service import NewWinService


@cached(LFUCache(maxsize=256))
def get_newwins(device: str) -> List[NewWin]:
    """
    레이어 팝업 목록 조회 함수
    - LFUCache 캐시를 사용하여 레이어 팝업 목록을 캐싱
    """
    with DBConnect().sessionLocal() as db:
        service = NewWinService(db)
        return service.fetch_newwins(device)


def get_newwins_except_cookie(request: Request):
    """쿠키에 저장된 팝업을 제외한 레이어 팝업 목록을 반환하는 함수"""
    newwins = get_newwins(request.state.device)

    # "hd_pops_" + nw_id 이름으로 선언된 쿠키가 있는지 확인하고 있다면 팝업을 제거
    return [newwin for newwin in newwins if not request.cookies.get("hd_pops_" + str(newwin.nw_id))]
