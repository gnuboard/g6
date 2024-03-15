from datetime import datetime, timedelta
from typing_extensions import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import insert, update

from core.database import db_session
from core.models import Member

from api.settings import SETTINGS
from api.v1.models import MemberRefreshToken
from api.v1.auth.auth import authenticate_member, authenticate_refresh_token
from api.v1.auth.jwt import JWT, TokenType
from api.v1.models.auth import Token

router = APIRouter()


@router.post("/token",
             summary="Access/Refresh Token 발급",
             response_model=Token)
async def login_for_access_token(
    db: db_session,
    member: Annotated[Member, Depends(authenticate_member)]
) -> Token:
    """
    로그인한 회원에게 Access Token, Refresh Token을 발급합니다.
    - Refresh Token은 데이터베이스에 저장됩니다.
    """
    # Access Token과 Refresh Token을 생성
    data = {"sub": member.mb_id}
    access_token = JWT.create_token(token_type=TokenType.ACCESS, data=data)
    refresh_token = JWT.create_token(token_type=TokenType.REFRESH)

    # 데이터베이스에 refresh_token 저장
    db.execute(
        insert(MemberRefreshToken).values(
            mb_id=member.mb_id,
            refresh_token=refresh_token,
            expires_at=datetime.now() + timedelta(
                minutes=SETTINGS.REFRESH_TOKEN_EXPIRE_MINUTES)
        )
    )
    db.commit()

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type=JWT.JWT_TYPE
    )


@router.post("/token/refresh",
             summary="Access Token 재 발급",
             response_model=Token)
async def refresh_access_token(
    db: db_session,
    member_refresh_token: Annotated[MemberRefreshToken, Depends(
        authenticate_refresh_token)]
) -> Token:
    """
    Refresh Token을 사용하여 새로운 Access Token을 발급합니다.
    - Refresh Token도 함께 갱신합니다.
    """
    # 새로운 Access Token과 Refresh Token을 생성
    data = {"sub": member_refresh_token.mb_id}
    new_access_token = JWT.create_token(token_type=TokenType.ACCESS, data=data)
    new_refresh_token = JWT.create_token(token_type=TokenType.REFRESH)

    # 데이터베이스의 refresh_token 갱신
    member_refresh_token.updated_at = datetime.now()
    member_refresh_token.expires_at = datetime.now() + timedelta(
        minutes=SETTINGS.REFRESH_TOKEN_EXPIRE_MINUTES),
    member_refresh_token.refresh_token = new_refresh_token
    db.commit()

    return Token(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type=JWT.JWT_TYPE
    )
