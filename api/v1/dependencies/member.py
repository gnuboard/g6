"""회원 관련 의존성을 정의합니다."""
from typing_extensions import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import exists

from core.database import db_session
from core.models import Member
from bbs.member_profile import validate_nickname, validate_userid, is_prohibit_email

from api.settings import SETTINGS
from api.v1.auth import oauth2_scheme
from api.v1.auth.jwt import JWT
from api.v1.lib.member import get_member, check_active_member, check_email_certified_member
from api.v1.models.auth import TokenPayload
from api.v1.models.member import CreateMemberModel


def validate_create_member(
    request: Request,
    db: db_session,
    member: CreateMemberModel
):
    """회원 가입시 회원 정보의 유효성을 검사합니다."""
    config = request.state.config
    # 아이디 유효성 검사
    exists_mb_id = db.scalar(
        exists(Member).where(Member.mb_id == member.mb_id).select()
    )
    if exists_mb_id:
        raise HTTPException(status_code=409, detail='이미 존재하는 아이디 입니다.')
    result = validate_userid(member.mb_id, config.cf_prohibit_id)
    if result["msg"]:
        raise HTTPException(status_code=403, detail=result["msg"])

    # 닉네임 유효성 검사
    result = validate_nickname(member.mb_nick, config.cf_prohibit_id)
    if result["msg"]:
        raise HTTPException(status_code=403, detail= result["msg"])
    
    # 이메일 유효성 검사
    exists_email = db.scalar(
        exists(Member.mb_email)
        .where(Member.mb_email == member.mb_email).select()
    )
    if exists_email:
        raise HTTPException(status_code=409, detail='이미 존재하는 이메일 입니다.')
    if is_prohibit_email(request, member.mb_email):
        raise HTTPException(status_code=403, detail=f"{member.mb_email} 메일은 사용할 수 없습니다.")

    return member


async def get_current_member(
    request: Request,
    db: db_session,
    token: Annotated[str, Depends(oauth2_scheme)]
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
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload: TokenPayload = JWT.decode_token(
        token,
        SETTINGS.ACCESS_TOKEN_SECRET_KEY
    )

    mb_id: str = payload.sub
    if mb_id is None:
        raise credentials_exception

    member = get_member(db, mb_id=mb_id)
    if member is None:
        raise credentials_exception
    if not check_active_member(member):
        credentials_exception.detail = "탈퇴 또는 차단된 회원입니다."
        raise credentials_exception
    if not check_email_certified_member(request, member):
        credentials_exception.detail = f"{member.mb_email} 메일로 메일인증을 받으셔야 로그인 가능합니다."
        raise credentials_exception

    return member