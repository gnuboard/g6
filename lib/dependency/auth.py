from fastapi import Request

from core.exception import AlertException
from core.models import Member


def get_login_member(request: Request):
    """로그인 여부 검사 & 반환"""
    member: Member = request.state.login_member
    if not member:
        path = request.url.path
        url = request.url_for("login_form").replace_query_params(url=path)
        raise AlertException(f"로그인 후 이용 가능합니다.", 403, url=url)

    return member


def get_login_member_optional(request: Request) -> Member:
    """로그인 여부 검사 & 반환"""
    member: Member = request.state.login_member
    return member
