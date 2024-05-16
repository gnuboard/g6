"""API 인증 관련 의존성 함수를 정의합니다."""
from typing_extensions import Annotated

from jose import ExpiredSignatureError, JWTError
from fastapi import Depends, Form, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.sql import select

from core.database import db_session

from core.models import Member
from api.settings import api_settings
from api.v1.models import MemberRefreshToken
from api.v1.auth.jwt import JWT
from api.v1.service.member import MemberServiceAPI


def authenticate_member(
    service: Annotated[MemberServiceAPI, Depends()],
    form: Annotated[OAuth2PasswordRequestForm, Depends()]
) -> Member:
    """회원 인증을 수행합니다.

    Args:
        service (Annotated[MemberServiceAPI, Depends]): 회원 서비스
        form_data (Annotated[OAuth2PasswordRequestForm, Depends): 

    Raises:
        HTTPException: 회원 인증 실패시 발생하는 예외

    Returns:
        Member: 회원 객체
    """
    return service.authenticate_member(form.username, form.password)


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
        MemberRefreshToken: refresh Token 객체
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # 토큰 유효성 검사
        JWT.decode_token(refresh_token, api_settings.REFRESH_TOKEN_SECRET_KEY)

        member_refresh_token = db.scalar(
            select(MemberRefreshToken)
            .where(MemberRefreshToken.refresh_token == refresh_token)
        )
        if not member_refresh_token:
            raise credentials_exception

        return member_refresh_token

    except ExpiredSignatureError as e:
        credentials_exception.detail = "Refresh Token has expired"
        raise credentials_exception from e
    except JWTError as e:
        credentials_exception.detail = "Could not validate credentials"
        raise credentials_exception from e
