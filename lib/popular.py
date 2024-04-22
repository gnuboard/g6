"""인기 검색어 관련 기능을 제공하는 모듈입니다."""
from cachetools import TTLCache, cached

from core.database import DBConnect
from service.popular_service import PopularService


@cached(TTLCache(maxsize=10, ttl=300))
def get_populars(limit: int = 10, day: int = 3):
    """
    인기검색어 조회
    - LFU(Least Frequently Used)캐시를 사용하여 조회한다.

    Args:
        limit (int, optional): 조회 갯수. Defaults to 7.
        day (int, optional): 오늘부터 {day}일 전. Defaults to 3.

    Returns:
        List[Popular]: 인기검색어 리스트
    """
    with DBConnect().sessionLocal() as db:
        service = PopularService(db)
        return service.fetch_populars(limit, day)
