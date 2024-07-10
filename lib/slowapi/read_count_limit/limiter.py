from fastapi import Request
from slowapi.util import get_remote_address

from lib.slowapi import LimiterNoWarning


read_count_limiter = LimiterNoWarning(key_func=get_remote_address)


@read_count_limiter.limit("1 per day")
def limit_read_count(request: Request):
    """
    게시글 작성자 외에 게시글 조회시,
    하루에 1회만 게시글 읽기 카운트 증가를 허용하는 함수
    """
    pass