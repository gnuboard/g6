"""회원 관련 의존성을 정의합니다."""
from datetime import timedelta
from typing import Optional
from typing_extensions import Annotated

from fastapi import Depends, HTTPException, Request, status

from core.models import Member
from lib.common import check_profile_open
from lib.member_lib import (
    validate_email, validate_mb_id,
    validate_nickname, validate_nickname_change_date
)

from api.settings import SETTINGS
from api.v1.auth import oauth2_scheme, oauth2_optional
from api.v1.auth.jwt import JWT
from api.v1.lib.member import MemberServiceAPI
from api.v1.models.auth import TokenPayload
from api.v1.models.member import CreateMemberModel, UpdateMemberModel


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
        SETTINGS.ACCESS_TOKEN_SECRET_KEY
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
    data: CreateMemberModel
):
    """회원 가입시 회원 정보의 유효성을 검사합니다."""
    # 아이디 유효성 검사
    is_valid, message = validate_mb_id(request, data.mb_id)
    if not is_valid:
        raise HTTPException(status_code=400, detail=message)

    # 닉네임 유효성 검사
    is_valid, message = validate_nickname(request, data.mb_nick)
    if not is_valid:
        raise HTTPException(status_code=400, detail=message)

    # 이메일 유효성 검사
    is_valid, message = validate_email(request, data.mb_email)
    if not is_valid:
        raise HTTPException(status_code=400, detail=message)

    return data


def validate_update_data(
    request: Request,
    member: Annotated[Member, Depends(get_current_member)],
    data: UpdateMemberModel,
):
    """회원 정보 수정시 회원 정보의 유효성을 검사합니다."""
    config = request.state.config

    # 이메일 변경 유효성 검사
    if member.mb_email != data.mb_email:
        is_valid, message = validate_email(request, data.mb_email)
        if not is_valid:
            raise HTTPException(status_code=400, detail=message)

    # 닉네임 변경 유효성 검사
    if member.mb_nick != data.mb_nick:
        is_valid, message = validate_nickname(request, data.mb_nick)
        if not is_valid:
            raise HTTPException(status_code=403, detail=message)

        if member.mb_nick_date:
            is_valid, message = validate_nickname_change_date(
                member.mb_nick_date, config.cf_nick_modify)
            if not is_valid:
                raise HTTPException(status_code=403, detail=message)
    else:
        del data.mb_nick_date

    # 회원정보 공개 유효성 검사
    if member.mb_open != data.mb_open:
        if not check_profile_open(member.mb_open_date, config):
            open_day = getattr(config, "cf_open_modify", 0)
            available_date = member.mb_open_date + timedelta(days=open_day)
            raise HTTPException(status_code=403,
                                detail=f"회원정보 변경은 {available_date} 이후 가능합니다.")
    else:
        del data.mb_open_date

    return data
