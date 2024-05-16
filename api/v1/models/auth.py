"""JWT 모델 정의 파일"""
from datetime import datetime

from pydantic import BaseModel


class TokenResponse(BaseModel):
    """JWT 모델"""
    access_token: str
    access_token_expire_at: datetime
    refresh_token: str
    refresh_token_expire_at: datetime
    token_type: str


class TokenPayload(BaseModel):
    """JWT Payload 모델"""
    iss: str = None
    sub: str = None
    aud: str = None
    exp: int = None
    nbf: int = None
    iat: int = None
    jti: str = None
