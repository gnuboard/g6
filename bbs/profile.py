from typing_extensions import Annotated

from datetime import datetime
from fastapi import APIRouter, Depends
from starlette.requests import Request

from core.template import UserTemplates
from lib.common import *
from lib.member_lib import MemberServiceTemplate

router = APIRouter()
templates = UserTemplates()


@router.get('/profile/{mb_id}')
async def get_profile(
    request: Request,
    member_service: Annotated[MemberServiceTemplate, Depends()],
):
    member_profile = member_service.get_member_profile(request.state.login_member)
    member_profile.mb_profile = member_profile.mb_profile or "소개 내용이 없습니다."
    mb_datetime = member_profile.mb_datetime if not is_none_datetime(member_profile.mb_datetime) else datetime.now()
    member_after_regdate = (datetime.now() - mb_datetime).days + 1

    context = {
        "request": request,
        "member": member_profile,
        "reg_after_date": member_after_regdate
    }
    return templates.TemplateResponse("/member/member_profile.html", context)
