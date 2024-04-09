"""회원 관련 유효성 검사를 위한 의존성 함수를 정의합니다."""
from typing_extensions import Annotated

from fastapi import Depends, Form, Request, status
from fastapi.responses import RedirectResponse

from core.exception import AlertException
from core.formclass import RegisterMemberForm, UpdateMemberForm
from core.models import Member
from lib.dependency.auth import get_login_member
from lib.pbkdf2 import create_hash, validate_password
from service.member_service import ValidateMember


def validate_policy_agree(request: Request):
    """약관 동의 여부 검사"""
    if (not request.session.get("ss_agree", None)
            or not request.session.get("ss_agree2", None)):
        raise AlertException("회원가입 약관에 동의해 주세요.", 400, url="/bbs/register")


def validate_register_data(
    validate: Annotated[ValidateMember, Depends()],
    data: Annotated[RegisterMemberForm, Depends()],
):
    """회원 가입시 회원 정보의 유효성을 검사합니다."""
    validate.valid_id(data.mb_id)
    validate.valid_nickname(data.mb_nick)
    validate.valid_email(data.mb_email)

    return data


def validate_update_data(
    validate: Annotated[ValidateMember, Depends()],
    member: Annotated[Member, Depends(get_login_member)],
    data: Annotated[UpdateMemberForm, Depends()],
):
    """회원 정보 수정시 회원 정보의 유효성을 검사합니다."""
    # 닉네임 변경 유효성 검사
    if member.mb_nick != data.mb_nick:
        validate.valid_nickname(data.mb_nick)
        validate.valid_nickname_change_date(member.mb_nick_date)
    else:
        del data.mb_nick_date

    # 이메일 변경 유효성 검사
    if member.mb_email != data.mb_email:
        validate.valid_email(data.mb_email)

    # 회원정보 공개 변경 유효성 검사
    if data.mb_open != member.mb_open:
        validate.valid_open_change_date(member.mb_open_date)
    else:
        del data.mb_open_date

    return data


def validate_leave_member(
    request: Request,
    member: Annotated[Member, Depends(get_login_member)],
    mb_password: str = Form(...),
):
    """회원 탈퇴시 회원 정보의 유효성을 검사합니다."""
    if request.state.is_super_admin:
        raise AlertException("최고관리자는 탈퇴할 수 없습니다.", 400)
    if not validate_password(mb_password, member.mb_password):
        raise AlertException("비밀번호가 일치하지 않습니다.", 400)


def redirect_if_logged_in(request: Request) -> None:
    """로그인 상태에서는 메인 페이지로 리다이렉트합니다."""
    member = request.state.login_member
    if member:
        return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    return None


def validate_password_reset(
    mb_password: str = Form(..., min_length=4, max_length=20),
    mb_password_confirm: str = Form(..., min_length=4, max_length=20)
) -> str:
    """비밀번호 재설정시 비밀번호가 일치하는지 검사합니다."""
    if mb_password != mb_password_confirm:
        raise AlertException("비밀번호가 일치하지 않습니다.", 400)

    return create_hash(mb_password)
