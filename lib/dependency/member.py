"""회원 관련 유효성 검사를 위한 의존성 함수를 정의합니다."""
import re
from datetime import datetime
from typing_extensions import Annotated

from fastapi import Depends, Form, Path, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from bbs.social import SocialAuthService
from core.database import db_session
from core.exception import AlertException
from core.formclass import MemberForm
from core.models import Member
from lib.dependencies import get_login_member
from lib.member_lib import (
    validate_email, validate_mb_id, validate_nickname, validate_nickname_change_date
)
from lib.pbkdf2 import create_hash, validate_password


def validate_register_member(
    request: Request,
    data: Annotated[MemberForm, Depends()],
    mb_id: str = Form(None),
    mb_password: str = Form(None),
    mb_password_re: str = Form(None),
    mb_certify_case: str = Form(default=""),
    mb_zip: str = Form(default=""),
):
    """회원 가입시 회원 정보의 유효성을 검사합니다."""
    # 회원 아이디 검사
    if len(mb_id) < 3 or len(mb_id) > 20:
        raise AlertException("회원아이디는 3~20자 이어야 합니다.", 400)
    if not re.match(r"^[a-zA-Z0-9_]+$", mb_id):
        raise AlertException("회원아이디는 영문자, 숫자, _ 만 사용할 수 있습니다.", 400)
    is_valid, message = validate_mb_id(request, mb_id)
    if not is_valid:
        raise AlertException(status_code=400, detail=message)

    # 비밀번호 검사
    if not (mb_password and mb_password_re):
        raise AlertException(status_code=400, detail="비밀번호를 입력해 주세요.")
    if mb_password != mb_password_re:
        raise AlertException(status_code=400, detail="비밀번호와 비밀번호 확인이 일치하지 않습니다.")

    # 이름 검사
    if not data.mb_name:
        raise AlertException(status_code=400, detail="이름을 입력해 주세요.")

    # 닉네임 유효성 검사
    is_valid, message = validate_nickname(request, data.mb_nick)
    if not is_valid:
        raise AlertException(status_code=400, detail=message)

    # 이메일 유효성 검사
    is_valid, message = validate_email(request, data.mb_email)
    if not is_valid:
        raise AlertException(status_code=400, detail=message)
    
    # 본인인증
    if mb_certify_case and data.mb_certify:
        data.mb_certify = mb_certify_case
        data.mb_adult = data.mb_adult
    else:
        data.mb_certify = ""
        data.mb_adult = 0

    if data.mb_sex not in {"m", "f"}:
        data.mb_sex = ""

    # 한국 우편번호 (postalcode)
    if mb_zip:
        data.mb_zip1 = mb_zip[:3]
        data.mb_zip2 = mb_zip[3:]

    # 레벨 입력방지
    del data.mb_level

    # 비밀번호 암호화
    data.mb_id = mb_id
    data.mb_password = create_hash(mb_password)

    return data


def validate_update_member(
    request: Request,
    member: Annotated[Member, Depends(get_login_member)],
    data: Annotated[MemberForm, Depends()],
    mb_password: str = Form(None),
    mb_password_re: str = Form(None),
    mb_certify_case: str = Form(default=""),
    mb_zip: str = Form(None),
):
    """회원 정보 수정시 회원 정보의 유효성을 검사합니다."""
    config = request.state.config
    # 한국 우편번호 (postalcode)
    if mb_zip:
        data.mb_zip1 = mb_zip[:3]
        data.mb_zip2 = mb_zip[3:]

    # 비밀번호 변경
    is_password_changed = False
    mb_password = mb_password.strip() if mb_password else ""
    mb_password_re = mb_password_re.strip() if mb_password_re else ""

    if mb_password and mb_password_re:
        # 비밀번호 변경 확인
        if not validate_password(password=mb_password, hash=member.mb_password):
            if mb_password != mb_password_re:
                raise AlertException("비밀번호가 일치하지 않습니다.", 400)
            is_password_changed = True

    # 이메일 변경
    if member.mb_email != data.mb_email:
        is_valid, message = validate_email(request, data.mb_email)
        if not is_valid:
            raise AlertException(message, 400)

    # 닉네임변경 검사
    if member.mb_nick != data.mb_nick:
        is_valid, message = validate_nickname(request, data.mb_nick)
        if not is_valid:
            raise AlertException(message, 400)

        if member.mb_nick_date:
            is_valid, message = validate_nickname_change_date(member.mb_nick_date, config.cf_nick_modify)
            if not is_valid:
                raise AlertException(message, 400)

        data.mb_nick_date = datetime.now()

    if not data.mb_sex in {"m", "f"}:
        data.mb_sex = ""

    data.mb_level = member.mb_level

    del data.mb_birth
    del data.mb_name

    if is_password_changed:
        data.mb_password = create_hash(mb_password)

    # 본인인증
    if mb_certify_case and data.mb_certify:
        data.mb_certify = mb_certify_case
    else:
        data.mb_certify = ""
        data.mb_adult = 0

    if data.mb_open != member.mb_open:
        data.mb_open_date = datetime.now()

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


def get_member_by_lost_certify(
    request: Request,
    db: db_session,
    mb_id: Annotated[str, Path()],
    token: Annotated[str, Path()],
) -> Member:
    """비밀번호 재설정을 위한 회원 정보를 조회합니다."""
    config = request.state.config
    member = db.scalar(
        select(Member).where(
            Member.mb_id == mb_id,
            Member.mb_lost_certify == token,
            Member.mb_id != config.cf_admin  # 최고관리자는 제외
        )
    )
    if not member:
        raise AlertException("유효하지 않은 요청입니다.", 403)

    if SocialAuthService.check_exists_by_member_id(member.mb_id):
        raise AlertException("소셜로그인으로 가입하신 회원은 비밀번호를 재설정할 수 없습니다.", 400)

    return member


def validate_password_reset(
    mb_password: str = Form(..., min_length=4, max_length=20),
    mb_password_confirm: str = Form(..., min_length=4, max_length=20)
) -> str:
    """비밀번호 재설정시 비밀번호가 일치하는지 검사합니다."""
    if mb_password != mb_password_confirm:
        raise AlertException("비밀번호가 일치하지 않습니다.", 400)

    return mb_password
