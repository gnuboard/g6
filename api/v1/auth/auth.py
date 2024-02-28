""" This module contains the authentication logic for the API."""
from typing_extensions import Annotated

from fastapi import Depends, Request, HTTPException, status
from fastapi.security import OAuth2PasswordRequestFormStrict

from core.database import db_session
from lib.pbkdf2 import validate_password

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
