"""방문자 관련 기능을 제공하는 모듈입니다."""
from cachetools import TTLCache, cached

from service.visit_service import VisitService


@cached(TTLCache(maxsize=1, ttl=600))
def get_total_visit(config_visit: str) -> dict:
    """
    방문자 수 집계 조회
    - 10분 동안 캐시된 데이터를 반환합니다.
    """
    return VisitService.parse_visit_data(config_visit)
