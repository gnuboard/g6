""" This module contains the authentication logic for the API."""
from typing_extensions import Annotated

from jose import ExpiredSignatureError, JWTError
from fastapi import Depends, Form, Request, HTTPException, status
from fastapi.security import OAuth2PasswordRequestFormStrict
from sqlalchemy.sql import exists

from core.database import db_session
from lib.pbkdf2 import validate_password

from api.settings import SETTINGS
from api.v1.models import MemberRefreshToken
from api.v1.auth.jwt import JWT
from api.v1.models.auth import TokenPayload
from api.v1.routers.member import (
    get_member,
    check_active_member, check_email_certified_member
)


def authenticate_member(
    request: Request,
    db: db_session,
    form_data: Annotated[OAuth2PasswordRequestFormStrict, Depends()]
):
    """회원 인증을 수행합니다.

    Args:
        request (Request): Request 객체
        db (db_session): 데이터베이스 세션
        form_data (Annotated[OAuth2PasswordRequestFormStrict, Depends): 

    Raises:
        HTTPException: 회원 인증 실패시 발생하는 예외

    Returns:
        Member: 회원 객체
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Bearer"},
    )

    member = get_member(db, form_data.username)

    if not member:
        raise credentials_exception
    if not validate_password(form_data.password, member.mb_password):
        raise credentials_exception
    if not check_active_member(member):
        credentials_exception.detail = "탈퇴 또는 차단된 회원입니다."
        raise credentials_exception
    if not check_email_certified_member(request, member):
        credentials_exception.detail = f"{member.mb_email} 메일로 메일인증을 받으셔야 로그인 가능합니다."
        raise credentials_exception

    return member


def authenticate_refresh_token(
    db: db_session,
    refresh_token: Annotated[str, Form(...)]
) -> str:
    """refresh Token을 검증합니다.

    Args:
        db (db_session): 데이터베이스 세션
        refresh_token (Annotated[str, Form(...)]): refresh Token

    Raises:
        credentials_exception: 데이터베이스에서 refresh Token을 찾을 수 없을 때 발생하는 예외
        credentials_exception: refresh Token이 만료되었을 때 발생하는 예외
        credentials_exception: refresh Token이 유효하지 않을 때 발생하는 예외

    Returns:
        str: 회원 아이디
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload: TokenPayload = JWT.decode_token(
            refresh_token, SETTINGS.REFRESH_TOKEN_SECRET_KEY)
        mb_id = payload.sub

        exists_refresh_token = db.scalar(
            exists(MemberRefreshToken.refresh_token)
            .where(MemberRefreshToken.mb_id == mb_id,
                   MemberRefreshToken.refresh_token == refresh_token)
            .select()
        )
        if not exists_refresh_token:
            raise credentials_exception

        return mb_id

    except ExpiredSignatureError:
        credentials_exception.detail = "Refresh Token has expired"
        raise credentials_exception
    except JWTError:
        credentials_exception.detail = "Could not validate credentials"
        raise credentials_exception
