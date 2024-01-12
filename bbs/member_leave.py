from fastapi import APIRouter, Depends, Form, Request
from sqlalchemy import update

from bbs.social import SocialAuthService
from core.database import db_session
from core.exception import AlertException
from core.template import UserTemplates
from lib.common import *
from lib.dependencies import get_login_member, validate_token
from lib.pbkdf2 import validate_password

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


@router.post("/member_leave", dependencies=[Depends(validate_token)])
async def member_leave(
    request: Request,
    db: db_session,
    mb_password: str = Form(...)
):
    """
    회원탈퇴 처리
    """
    login_member = request.state.login_member
    if not login_member:
        raise AlertException("회원만 접근하실 수 있습니다.", 403)
    if request.state.is_super_admin:
        raise AlertException("최고관리자는 탈퇴할 수 없습니다.", 400)
    if not validate_password(mb_password, login_member.mb_password):
        raise AlertException("패스워드가 일치하지 않습니다.", 404)

    # 회원탈퇴
    leave_date = datetime.now().strftime("%Y-%m-%d")
    leave_date_ymd = datetime.now().strftime("%Y%m%d")
    memo = f"{login_member.mb_memo}\n{leave_date}탈퇴함"
    db.execute(
        update(Member)
        .values(mb_leave_date=leave_date_ymd, mb_memo=memo)
        .where(Member.mb_id == login_member.mb_id)
    )
    db.commit()

    # 소셜로그인 연동 해제
    if SocialAuthService.check_exists_by_member_id(login_member.mb_id):
        SocialAuthService.unlink_social_login(login_member.mb_id)

    # 로그아웃
    request.session.clear()

    raise AlertException(f"{login_member.mb_nick} 님께서는 {leave_date} 에 회원에서 탈퇴 하셨습니다.", url="/")
