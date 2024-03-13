""" 
회원 인증 관련 함수를 정의합니다.
"""
from typing_extensions import Annotated

from jose import ExpiredSignatureError, JWTError
from fastapi import Depends, Form, Request, HTTPException, status
from fastapi.security import OAuth2PasswordRequestFormStrict
from sqlalchemy.sql import exists

from core.database import db_session

from api.settings import SETTINGS
from api.v1.models import MemberRefreshToken
from api.v1.auth.jwt import JWT
from api.v1.models.auth import TokenPayload
from api.v1.lib.member import MemberServiceAPI


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
    member_service = MemberServiceAPI(request, db, form_data.username)
    return member_service.authenticate_member(form_data.password)


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
