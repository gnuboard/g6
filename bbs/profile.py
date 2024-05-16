"""회원 프로필 수정 Template Router"""
from datetime import datetime
from typing_extensions import Annotated

from fastapi import APIRouter, Depends, Path
from starlette.requests import Request

from core.models import Member
from core.template import UserTemplates
from lib.dependency.auth import get_login_member
from lib.common import is_none_datetime
from service.member_service import MemberService

router = APIRouter()
templates = UserTemplates()


@router.get('/profile/{mb_id}')
async def get_profile(
    request: Request,
    login_member: Annotated[Member, Depends(get_login_member)],
    member_service: Annotated[MemberService, Depends()],
    mb_id: Annotated[str, Path(...)]
):
    """
    회원의 자기소개 폼을 조회합니다.
    """
    profile = member_service.get_member_profile(mb_id, login_member)
    register_date = profile.mb_datetime
    if is_none_datetime(register_date):
        register_date = datetime.now()
    days_since_regist = (datetime.now() - register_date).days + 1

    context = {
        "request": request,
        "member": profile,
        "days_since_regist": days_since_regist
    }
    return templates.TemplateResponse("/member/member_profile.html", context)
