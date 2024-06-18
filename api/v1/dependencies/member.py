"""회원 관련 의존성을 정의합니다."""
from typing import Optional
from typing_extensions import Annotated

from fastapi import Body, Depends, HTTPException, Path, Request, status

from api.settings import api_settings
from api.v1.auth import oauth2_optional, oauth2_scheme
from api.v1.auth.jwt import JWT
from api.v1.models.auth import TokenPayload
from api.v1.models.member import CreateMember, UpdateMember
from api.v1.service.certificate import CertificateServiceAPI
from api.v1.service.member import MemberServiceAPI, ValidateMemberAPI
from core.models import Member
from lib.common import is_none_datetime
from lib.pbkdf2 import validate_password


async def get_current_member(
    token: Annotated[str, Depends(oauth2_scheme)],
    member_service: Annotated[MemberServiceAPI, Depends()]
) -> Member:
    """현재 로그인한 회원 정보를 조회합니다.

    Args:
        request (Request): Request 객체
        db (db_session): 데이터베이스 세션
        token (Annotated[str, Depends(oauth2_scheme)]): JWT

    Raises:
        HTTPException: 회원아이디가 없거나 회원 정보가 없을 경우 발생하는 예외

    Returns:
        Member: 현재 로그인한 회원 정보
    """
    payload: TokenPayload = JWT.decode_token(
        token,
        api_settings.ACCESS_TOKEN_SECRET_KEY
    )

    mb_id: str = payload.sub
    if mb_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    member = member_service.get_member(mb_id)

    return member


async def get_current_member_optional(
    token: Annotated[str, Depends(oauth2_optional)],
    member_service: Annotated[MemberServiceAPI, Depends()]
) -> Optional[Member]:
    """현재 로그인한 회원 정보를 선택적으로 조회합니다.

    Args:
        token (Annotated[str, Depends(oauth2_scheme_none)]): JWT
        member_service (MemberServiceAPI): 회원 서비스 인스턴스

    Returns:
        Optional[Member]: 현재 로그인한 회원 정보 또는 None
    """
    if token is None:
        return None
    return await get_current_member(token, member_service)


def validate_create_data(
    request: Request,
    cert_service: Annotated[CertificateServiceAPI, Depends()],
    validate: Annotated[ValidateMemberAPI, Depends()],
    data: CreateMember
):
    """회원 가입시 회원 정보의 유효성을 검사합니다."""
    validate.valid_id(data.mb_id)
    validate.valid_name(data.mb_name)
    validate.valid_nickname(data.mb_nick)
    validate.valid_email(data.mb_email)
    validate.valid_recommend(data.mb_recommend, data.mb_id)

    # 휴대폰 번호가 필수인 경우 유효성 검사
    config = request.state.config
    if cert_service.should_required_hp() and config.cf_use_hp:
        validate.valid_hp(data.mb_hp)

    # 본인인증 유효성 검사
    if cert_service.cert_use:
        # 본인인증 여부 체크
        if cert_service.cert_req and not data.cert_no:
            raise HTTPException(400, "회원가입을 위해 본인인증을 먼저 진행해주시기 바랍니다.")

        # 기존회원 가입여부 체크
        if data.cert_type and data.cert_dupinfo:
            cert_service.validate_exists_dupinfo(data.cert_dupinfo, '')

        # 본인인증 데이터 확인
        if data.cert_type and data.cert_no:
            cert_hash = cert_service.hasing_cert_hash(
                data.mb_name, data.cert_type, data.cert_no,
                data.cert_user_birthday, data.mb_hp)

            if not data.cert_hash == cert_hash:
                raise HTTPException(400, "본인확인 데이터가 일치하지 않습니다.")

        # 데이터 처리
        data.mb_certify = data.cert_type
        data.mb_adult = data.cert_adult
        data.mb_birth = data.cert_user_birthday
        data.mb_dupinfo = data.cert_dupinfo

    del data.cert_type
    del data.cert_no
    del data.cert_hash
    del data.cert_adult
    del data.cert_dupinfo
    del data.cert_user_name
    del data.cert_user_phone
    del data.cert_user_birthday

    return data


def validate_update_data(
    validate: Annotated[ValidateMemberAPI, Depends()],
    member: Annotated[Member, Depends(get_current_member)],
    data: UpdateMember,
):
    """회원 정보 수정시 회원 정보의 유효성을 검사합니다."""
    # 닉네임 변경 유효성 검사
    if data.mb_nick and member.mb_nick != data.mb_nick:
        validate.valid_nickname(data.mb_nick)
        validate.valid_nickname_change_date(member.mb_nick_date)
    else:
        del data.mb_nick
        del data.mb_nick_date

    # 이메일 변경 유효성 검사
    if member.mb_email != data.mb_email:
        validate.valid_email(data.mb_email)

    # 회원정보 공개 변경 유효성 검사
    if member.mb_open != data.mb_open:
        validate.valid_open_change_date(member.mb_open_date)
    else:
        del data.mb_open_date

    return data



def validate_certify_email_member(
    member_service: Annotated[MemberServiceAPI, Depends()],
    mb_id: Annotated[str, Path(..., title="회원 아이디", description="회원 아이디")],
    password: Annotated[str, Body(..., title="비밀번호", description="회원 비밀번호")],
):
    """
    인증 이메일 변경시 회원 정보의 유효성을 검사합니다.
    """
    member = member_service.fetch_member_by_id(mb_id)
    if not validate_password(password, member.mb_password):
        raise HTTPException(
            status_code=400,
            detail="비밀번호가 올바르지 않습니다.",
        )

    if not is_none_datetime(member.mb_email_certify):
        raise HTTPException(
            status_code=409,
            detail="이미 메일인증을 진행한 회원입니다.",
        )

    return member
