"""회원 관련 의존성을 정의합니다."""
from typing import Optional
from typing_extensions import Annotated

from fastapi import Depends, HTTPException, status

from core.models import Member

from api.settings import api_settings
from api.v1.auth import oauth2_optional, oauth2_scheme
from api.v1.auth.jwt import JWT
from api.v1.service.member import MemberServiceAPI, ValidateMemberAPI
from api.v1.models.auth import TokenPayload
from api.v1.models.member import CreateMember, UpdateMember


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
    validate: Annotated[ValidateMemberAPI, Depends()],
    data: CreateMember
):
    """회원 가입시 회원 정보의 유효성을 검사합니다."""
    validate.valid_id(data.mb_id)
    validate.valid_nickname(data.mb_nick)
    validate.valid_email(data.mb_email)

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
