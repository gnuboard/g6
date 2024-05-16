from typing import Union
from typing_extensions import Annotated
from fastapi import Depends, Request

from core.exception import AlertException
from core.models import Member
from service.member_service import MemberService


def get_login_member(
    request: Request,
    service: Annotated[MemberService, Depends()]
) -> Member:
    """현재 로그인 여부 검사 진행 후 로그인 멤버를 반환한다."""
    mb_id = request.session.get("ss_mb_id", "")
    member: Member = service.fetch_member_by_id(mb_id)
    if not member or not mb_id:
        path = request.url.path
        url = request.url_for("login_form").replace_query_params(url=path)
        raise AlertException("로그인 후 이용 가능합니다.", 403, url=url)

    return member


def get_login_member_optional(
    request: Request,
    service: Annotated[MemberService, Depends()]
) -> Union[Member, None]:
    """현재 로그인 멤버를 반환한다. 로그인이 되어 있지 않으면 None을 반환한다."""
    mb_id = request.session.get("ss_mb_id", "")
    member: Member = service.fetch_member_by_id(mb_id)
    return member
