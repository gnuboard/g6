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


@router.post("/token")
async def login_for_access_token(
    db: db_session,
    member: Annotated[Member, Depends(authenticate_member)]
) -> Token:
    """로그인한 회원에게 Access Token을 발급합니다.

    Args:
        member (Annotated[Member, Depends(authenticate_member)]): 로그인한 회원

    Returns:
        Token: Access Token
    """
    # Access Token과 Refresh Token을 생성
    access_token = JWT.create_token(
        data={"sub": member.mb_id}, token_type=TokenType.ACCESS
    )
    refresh_token = JWT.create_token(
        data={"sub": member.mb_id}, token_type=TokenType.REFRESH
    )

    # 데이터베이스에 refresh_token 저장
    db.execute(
        insert(MemberRefreshToken)
        .values(
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


@router.post("/refresh")
async def refresh_access_token(
    db: db_session,
    mb_id: Annotated[str, Depends(authenticate_refresh_token)]
) -> Token:
    """Refresh Token을 사용하여 새로운 Access Token을 발급합니다.

    Args:
        refresh_token (str): 클라이언트로부터 받은 Refresh Token

    Returns:
        Token: 새로운 Access Token과 Refresh Token을 포함한 객체
    """
    # 새로운 Access Token과 Refresh Token을 생성
    new_access_token = JWT.create_access_token(data={"sub": mb_id})
    new_refresh_token = JWT.create_refresh_token(data={"sub": mb_id})

    # 데이터베이스의 refresh_token 갱신
    db.execute(
        update(MemberRefreshToken)
        .values(
            refresh_token=new_refresh_token,
            expires_at=datetime.now() + timedelta(
                minutes=SETTINGS.REFRESH_TOKEN_EXPIRE_MINUTES),
            updated_at=datetime.now()
        )
        .where(MemberRefreshToken.mb_id == mb_id)
    )
    db.commit()

    return Token(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type=JWT.JWT_TYPE
    )
