from typing import Annotated, Optional
from fastapi import Request, Depends
from fastapi.security.utils import get_authorization_scheme_param
from sqlalchemy import select
from slowapi import Limiter
from slowapi.util import get_remote_address

from core.database import DBConnect
from core.models import Config, Member
from api.settings import api_settings
from api.v1.auth import oauth2_scheme
from api.v1.auth.jwt import JWT
from api.v1.service.member import MemberServiceAPI
from api.v1.models.auth import TokenPayload


def get_request_member(
    token: Annotated[str, Depends(oauth2_scheme)],
    member_service: Annotated[MemberServiceAPI, Depends()]
) -> Optional[Member]:
    """
    REST_API 요청 시 JWT 토큰을 통해 사용자 정보를 가져오는 함수

    Args:
        token (Annotated[str, Depends(oauth2_scheme)]): JWT 토큰
        member_service (Annotated[MemberServiceAPI, Depends()]): 사용자 정보 서비스

    Returns:
        Member: 사용자 정보 객체 또는 None
    """
    payload: TokenPayload = JWT.decode_token(
        token,
        api_settings.ACCESS_TOKEN_SECRET_KEY
    )

    mb_id: str = payload.sub
    if mb_id is None:
        return None

    member = member_service.get_member(mb_id)
    return member


def limiter_key_func(request: Request) -> Optional[str]:
    """
    Limiter 인스턴스 생성시 key_func 인자에 제공될 함수.
    None으로 반환되는 IP 주소(관리자 IP)는 요청 제한을 하지 않는다.

    Args:
        request (Request): FastAPI Request 객체
    
    Returns:
        Optional[str]: 요청 제한 IP 주소 또는 None
    """
    authorization = request.headers.get("Authorization")
    scheme, token = get_authorization_scheme_param(authorization)

    if not authorization or scheme.lower() != "bearer":
        return get_remote_address(request)

    with DBConnect().sessionLocal() as db:
        member_service = MemberServiceAPI(request, db)
        cf_admin = db.scalar(select(Config)).cf_admin

    member = get_request_member(token, member_service)
    if member.mb_id == cf_admin:
        return None

    return get_remote_address(request)


def get_cf_delay_sec_from_db():
    """
    데이터베이스에서 cf_delay_sec 값을 가져와서
    Limiter 인스턴스 생성시 사용할 제한 표현식을 반환하는 함수
    "n/t time" 형식으로 반환
      - t시간 (시간 단위는 time) 동안 n번의 요청을 허용
      - time: second, minute, hour, day, month, year
      - documentation: https://limits.readthedocs.io/en/stable/quickstart.html#rate-limit-string-notation
    """
    with DBConnect().sessionLocal() as db:
        cf_delay_sec = db.scalar(select(Config)).cf_delay_sec
    limiter_expr = f"1/{cf_delay_sec} second"
    return limiter_expr


# 요청 제한 limiter 인스턴스 생성
limiter = Limiter(key_func=limiter_key_func)


@limiter.limit(
    get_cf_delay_sec_from_db,
    error_message="너무 빠른 시간내에 게시글을 연속해서 올릴 수 없습니다.",
)
def validate_slowapi_create_post(request: Request):
    """
    slowapi의 Limiter를 통해 게시글 생성 API 요청 제한 시간을 검증하는 함수

    Args:
        request (Request): FastAPI Request 객체
    """
    pass