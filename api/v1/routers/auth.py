"""인증 관련 API Router"""
from datetime import datetime, timedelta
from typing import Tuple
from typing_extensions import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import insert

from core.database import db_session
from core.models import Member

from api.v1.dependencies.auth import authenticate_member, authenticate_refresh_token
from api.v1.auth.jwt import JWT, TokenType
from api.v1.models import MemberRefreshToken
from api.v1.models.auth import TokenResponse
from api.v1.models.response import response_403, response_422

router = APIRouter()


@router.post("/token",
             summary="Access/Refresh Token 발급",
             responses={**response_403, **response_422})
async def login_for_access_token(
    db: db_session,
    member: Annotated[Member, Depends(authenticate_member)]
) -> TokenResponse:
    """
    Access Token & Refresh Token을 발급합니다.
    - Access Token은 API 요청에 사용되며, 일정 시간 후 만료됩니다.
    - Refresh Token은 Access Token 재발급에 필요하며 데이터베이스에 저장됩니다.
    """
    # Access Token, Refresh Token 생성
    access_token, access_token_expire_at = _create_token_and_expiration(
        TokenType.ACCESS, member.mb_id)
    refresh_token, refresh_token_expire_at = _create_token_and_expiration(
        TokenType.REFRESH)

    # 데이터베이스에 refresh_token 저장
    db.execute(
        insert(MemberRefreshToken).values(
            mb_id=member.mb_id,
            refresh_token=refresh_token,
            expires_at=refresh_token_expire_at
        )
    )
    db.commit()

    return TokenResponse(
        access_token=access_token,
        access_token_expire_at=access_token_expire_at,
        refresh_token=refresh_token,
        refresh_token_expire_at=refresh_token_expire_at,
        token_type=JWT.JWT_TYPE
    )


@router.post("/token/refresh",
             summary="Access Token 재 발급",
             responses={**response_422})
async def refresh_access_token(
    db: db_session,
    member_refresh_token: Annotated[MemberRefreshToken,
                                    Depends(authenticate_refresh_token)]
) -> TokenResponse:
    """
    Refresh Token을 사용하여 새로운 Access Token을 발급합니다.
    - Refresh Token도 함께 갱신되며 데이터베이스에 저장됩니다.
    """
    # 새로운 Access Token과 Refresh Token을 생성
    access_token, access_token_expire_at = _create_token_and_expiration(
        TokenType.ACCESS, member_refresh_token.mb_id)
    refresh_token, refresh_token_expire_at = _create_token_and_expiration(
        TokenType.REFRESH)

    # 데이터베이스의 refresh_token 갱신
    member_refresh_token.updated_at = datetime.now()
    member_refresh_token.expires_at = refresh_token_expire_at
    member_refresh_token.refresh_token = refresh_token
    db.commit()

    return TokenResponse(
        access_token=access_token,
        access_token_expire_at=access_token_expire_at,
        refresh_token=refresh_token,
        refresh_token_expire_at=refresh_token_expire_at,
        token_type=JWT.JWT_TYPE
    )


def _create_token_and_expiration(
        token_type: TokenType, member_id: str = None) -> Tuple[str, datetime]:
    """토큰과 해당 토큰의 만료 시간을 생성합니다."""
    data = {}
    if member_id:
        data = {"sub": member_id}

    token = JWT.create_token(token_type=token_type, data=data)
    expiration_time = datetime.now() + timedelta(minutes=token_type.expires_minute)
    return token, expiration_time
