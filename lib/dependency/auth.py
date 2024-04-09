from fastapi import Request

from core.exception import AlertException
from core.models import Member


def get_login_member(request: Request):
    """현재 로그인 여부 검사 진행 후 로그인 멤버를 반환한다."""
    member: Member = request.state.login_member
    if not member:
        path = request.url.path
        url = request.url_for("login_form").replace_query_params(url=path)
        raise AlertException("로그인 후 이용 가능합니다.", 403, url=url)

    return member


def get_login_member_optional(request: Request) -> Member:
    """현재 로그인 멤버를 반환한다. 로그인이 되어 있지 않으면 None을 반환한다."""
    member: Member = request.state.login_member
    return member
