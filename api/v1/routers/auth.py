from typing_extensions import Annotated

from fastapi import APIRouter, Depends

from core.models import Member
from api.v1.auth.auth import authenticate_member
from api.v1.auth.jwt import JWT
from api.v1.models.auth import Token

router = APIRouter()


@router.post("/token")
async def login_for_access_token(
    member: Annotated[Member, Depends(authenticate_member)]
) -> Token:
    """로그인한 회원에게 Access Token을 발급합니다.

    Args:
        member (Annotated[Member, Depends(authenticate_member)]): 로그인한 회원

    Returns:
        Token: Access Token
    """
    access_token = JWT.create_access_token(data={"sub": member.mb_id})

    return Token(access_token=access_token, token_type="bearer")