"""회원 관련 유효성 검사를 위한 의존성 함수를 정의합니다."""
from typing_extensions import Annotated

from fastapi import Depends, Form, Request, status
from fastapi.responses import RedirectResponse

from core.exception import AlertException
from core.formclass import RegisterMemberForm, UpdateMemberForm
from core.models import Member
from lib.dependency.auth import get_login_member
from lib.pbkdf2 import create_hash, validate_password
from service.certificate_service import CertificateService
from service.member_service import ValidateMember


def validate_policy_agree(request: Request):
    """약관 동의 여부 검사"""
    if (not request.session.get("ss_agree", None)
            or not request.session.get("ss_agree2", None)):
        raise AlertException("회원가입 약관에 동의해 주세요.", 400, url="/bbs/register")


def validate_register_data(
    request: Request,
    cert_service: Annotated[CertificateService, Depends()],
    validate: Annotated[ValidateMember, Depends()],
    data: Annotated[RegisterMemberForm, Depends()],
):
    """회원 가입시 회원 정보의 유효성을 검사합니다."""
    validate.valid_id(data.mb_id)
    validate.valid_nickname(data.mb_nick)
    validate.valid_email(data.mb_email)

    # 휴대폰 번호가 필수인 경우 유효성 검사
    config = request.state.config
    if cert_service.should_required_hp() and config.cf_use_hp:
        validate.valid_hp(data.mb_hp)

    # 본인인증 유효성 검사
    if cert_service.cert_use:
        ss_cert_no = request.session.get("ss_cert_no")
        ss_cert_type = request.session.get("ss_cert_type")
        ss_cert_dupinfo = request.session.get("ss_cert_dupinfo")
        ss_cert_hash = request.session.get("ss_cert_hash")
        ss_cert_adult = request.session.get("ss_cert_adult")
        ss_cert_birth = request.session.get("ss_cert_birth")

        # 본인인증 여부 체크
        if cert_service.cert_req and (not data.cert_no or data.cert_no != ss_cert_no):
            raise AlertException("회원가입을 위해서는 본인확인을 해주셔야 합니다.", 400)

        # 기존회원 가입여부 체크
        if ss_cert_type and ss_cert_dupinfo:
            cert_service.validate_exists_dupinfo(ss_cert_dupinfo, '')

        # 본인인증 데이터 확인
        if ss_cert_type and ss_cert_no:
            cert_hash = cert_service.hasing_cert_hash(data.mb_name, ss_cert_type,
                                                    ss_cert_birth, ss_cert_no, data.mb_hp)
            if not ss_cert_hash == cert_hash:
                raise AlertException("본인확인 데이터가 일치하지 않습니다.", 400)
        # 데이터 처리
        data.mb_certify = ss_cert_type
        data.mb_adult = ss_cert_adult
        data.mb_birth = ss_cert_birth
        data.mb_dupinfo = ss_cert_dupinfo

    del data.cert_no

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
