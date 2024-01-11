# Jinja2 Templates 사용자 정의 필터
# ============================================================================
import re
from datetime import datetime
from typing import Union

from fastapi import Request
from starlette.datastructures import URL


def datetime_format(date: datetime, format="%Y-%m-%d %H:%M:%S"):
    """날짜를 지정된 포맷으로 변환"""
    if not date:
        return ""

    return date.strftime(format)


def default_if_none(value, arg):
    """If value is None"""
    if value is None:
        return arg
    return value


def number_format(number: int) -> str:
    """숫자를 천단위로 구분하여 반환

    Args:
        number (int): 숫자

    Returns:
        str: 천단위로 구분된 숫자
    """
    if isinstance(number, int):
        return "{:,}".format(number)

    return "0"


def search_font(content: str, stx: str) -> str:
    """검색어를 지정된 폰트의 색상, 배경색상으로 대체

    Args:
        content (str): 검색 대상 문자열
        stx (str): 검색어

    Returns:
        str: 검색어가 지정된 폰트의 색상, 배경색상으로 대체된 문자열
    """
    # 문자 앞에 \를 붙입니다.
    src = ['/', '|']
    dst = ['\\/', '\\|']

    if not stx or not stx.strip() and stx != '0':
        return content

    # 검색어 전체를 공란으로 나눈다
    search_keywords = stx.split()

    # "(검색1|검색2)"와 같은 패턴을 만듭니다.
    pattern = ''
    bar = ''
    for keyword in search_keywords:
        if keyword.strip() == '':
            continue
        tmp_str = re.escape(keyword)
        tmp_str = tmp_str.replace(src[0], dst[0]).replace(src[1], dst[1])
        pattern += f'{bar}{tmp_str}(?![^<]*>)'
        bar = "|"

    # 지정된 검색 폰트의 색상, 배경색상으로 대체
    replace = "<b class=\"sch_word\">\\1</b>"

    return re.sub(f'({pattern})', replace, content, flags=re.IGNORECASE)


def set_query_params(url: Union[URL, str], request: Request, **params: dict) -> URL:
    """url에 query string을 추가

    Args:
        url (str): URL
        request (Request): FastAPI Request 객체
        **params (dict): 추가할 query string

    Returns:
        str: query string이 추가된 URL
    """
    # 현재 query string
    query_params = request.query_params
    if query_params or params:
        if isinstance(url, str):
            url = URL(url)
        # 현재 query string을 유지하면서 추가할 query string을 추가
        url = url.replace_query_params(**query_params, **params)

    return url
