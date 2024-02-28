from pydantic import BaseModel


class Token(BaseModel):
    """JWT access 또는 refresh 토큰 모델"""
    access_token: str
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
