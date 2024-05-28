import inspect
from typing import List
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.wrappers import Limit
from slowapi.errors import RateLimitExceeded


class LimiterNoWarning(Limiter):
    """
    Limiter 클래스의 __evaluate_limits 메서드에서
    로깅되는 경고 메시지를 출력하지 않도록 오버라이딩하여 사용하는 Limiter 클래스
    """
    def __init__(self, key_func):
        super().__init__(key_func=key_func)

    def _Limiter__evaluate_limits(
        self, request: Request, endpoint: str, limits: List[Limit]
    ) -> None:
        failed_limit = None
        limit_for_header = None
        for lim in limits:
            limit_scope = lim.scope or endpoint
            if lim.is_exempt:
                continue
            if lim.methods is not None and request.method.lower() not in lim.methods:
                continue
            if lim.per_method:
                limit_scope += ":%s" % request.method

            if "request" in inspect.signature(lim.key_func).parameters.keys():
                limit_key = lim.key_func(request)
            else:
                limit_key = lim.key_func()

            args = [limit_key, limit_scope]
            if all(args):
                if self._key_prefix:
                    args = [self._key_prefix] + args
                if not limit_for_header or lim.limit < limit_for_header[0]:
                    limit_for_header = (lim.limit, args)

                cost = lim.cost(request) if callable(lim.cost) else lim.cost
                if not self.limiter.hit(lim.limit, *args, cost=cost):
                    failed_limit = lim
                    limit_for_header = (lim.limit, args)
                    break
            else:
                self.logger.error(
                    "Skipping limit: %s. Empty value found in parameters.", lim.limit
                )
                continue
        # keep track of which limit was hit, to be picked up for the response header
        request.state.view_rate_limit = limit_for_header

        if failed_limit:
            raise RateLimitExceeded(failed_limit)


read_count_limiter = LimiterNoWarning(key_func=get_remote_address)


@read_count_limiter.limit("1 per day")
def limit_read_count(request: Request):
    """
    게시글 작성자 외에 게시글 조회시,
    하루에 1회만 게시글 읽기 카운트 증가를 허용하는 함수
    """
    pass