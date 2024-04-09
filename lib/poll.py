"""설문조사 관련 기능을 제공하는 모듈입니다."""
from cachetools import cached, LFUCache

from core.database import DBConnect
from lib.service.poll_service import PollService


@cached(LFUCache(maxsize=1))
def get_latest_poll():
    """
    최근 설문조사 정보 1건을 가져오는 함수
    """
    with DBConnect().sessionLocal() as db:
        return PollService.fetch_latest_poll(db)
