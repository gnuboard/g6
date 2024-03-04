from datetime import datetime
from typing import Union
from typing_extensions import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from sqlalchemy.sql import select

from core.database import db_session
from core.models import Member

from api.settings import SETTINGS
from api.v1.auth import oauth2_scheme
from api.v1.auth.jwt import JWT
from api.v1.models.auth import TokenPayload

router = APIRouter()


def get_member(db: Session, mb_id: str) -> Union[Member, None]:
    """회원 정보를 조회합니다."""
    return db.scalar(select(Member).where(Member.mb_id == mb_id))


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


def check_active_member(member: Member) -> bool:
    """활성화된 회원인지 확인합니다."""
    if member.mb_leave_date or member.mb_intercept_date:
        return False
    return True


def check_email_certified_member(
    request: Request,
    member: Member,
) -> bool:
    """이메일 인증이 완료된 회원인지 확인합니다."""
    config = request.state.config
    if config.cf_use_email_certify and member.mb_email_certify == datetime(1, 1, 1, 0, 0, 0):
        raise False
    return True


@router.get("/me",
            summary="현재 로그인한 회원 정보 조회",
            description="JWT을 통해 현재 로그인한 회원 정보를 조회합니다. \
                <br>- 탈퇴 또는 차단된 회원은 조회할 수 없습니다. \
                <br>- 이메일 인증이 완료되지 않은 회원은 조회할 수 없습니다.",
            response_description="로그인한 회원 정보를 반환합니다.")
async def read_members_me(
    current_member: Annotated[Member, Depends(get_current_member)]
):
    """현재 로그인한 회원 정보를 조회합니다.

    Args:
        current_member (Annotated[Member, Depends(get_current_member)]): 현재 로그인한 회원 정보

    Returns:
        Member: 현재 로그인한 회원 정보
    """
    return current_member


@router.post("/items/{item_id}")
async def update_item(
    item_id: int,
):
    results = {"item_id": item_id}
    return results