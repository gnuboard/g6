"""회원탈퇴 Template Router"""
from typing_extensions import Annotated

from fastapi import APIRouter, Depends, Request

from bbs.social import SocialAuthService
from core.exception import AlertException
from core.models import Member
from core.template import UserTemplates
from lib.dependency.member import validate_leave_member
from lib.dependency.dependencies import validate_token
from lib.dependency.auth import get_login_member
from service.member_service import MemberService

router = APIRouter()
templates = UserTemplates()


@router.get("/member_leave")
async def member_leave_form(
    request: Request,
    member: Member = Depends(get_login_member)):
    """
    회원탈퇴 폼을 보여준다.
    """
    context = {
        "request": request,
        "member": member,
        "action_url": request.url_for("member_leave")
    }
    return templates.TemplateResponse("/member/member_confirm.html", context)


@router.post("/member_leave",
             dependencies=[Depends(validate_token),
                           Depends(validate_leave_member)])
async def member_leave(
    request: Request,
    member_service: Annotated[MemberService, Depends()],
    login_member: Annotated[Member, Depends(get_login_member)],
):
    """
    회원탈퇴 처리
    """
    member = member_service.read_member(login_member.mb_id)
    member_service.leave_member(member)

    # 소셜로그인 연동 해제
    SocialAuthService.unlink_social_login(login_member.mb_id)

    # 로그아웃
    request.session.clear()

    raise AlertException(f"{login_member.mb_nick} 님의 회원탈퇴가 처리되었습니다.", 200)
