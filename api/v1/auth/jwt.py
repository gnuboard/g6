"""JWT 관련 작업을 처리하는 클래스입니다."""
from datetime import datetime, timedelta
from enum import Enum

from fastapi import HTTPException, status
from jwt import encode, decode, ExpiredSignatureError, InvalidTokenError

from api.settings import api_settings
from api.v1.models.auth import TokenPayload


class TokenType(Enum):
    """JWT 토큰의 종류별 설정을 관리하는 Enum 클래스입니다."""
    ACCESS = "access"
    REFRESH = "refresh"

    @property
    def secret_key(self):
        """JWT 암호화 키를 반환합니다."""
        if self == TokenType.REFRESH:
            return api_settings.REFRESH_TOKEN_SECRET_KEY
        return api_settings.ACCESS_TOKEN_SECRET_KEY

    @property
    def expires_minute(self):
        """JWT 만료 시간을 반환합니다."""
        if self == TokenType.REFRESH:
            return api_settings.REFRESH_TOKEN_EXPIRE_MINUTES
        return api_settings.ACCESS_TOKEN_EXPIRE_MINUTES


class JWT:
    """JWT 관련 작업을 처리하는 클래스입니다."""
    JWT_TYPE = "Bearer"

    @staticmethod
    def create_token(token_type: TokenType, data: dict = None) -> str:
        """JWT를 생성합니다.

        Args:
            data (dict): JWT에 담을 데이터
            token_type (TokenType): JWT 종류 (ACCESS, REFRESH)
        Returns:
            str: JWT
        """
        if data is None:
            data = {}

        secret_key = token_type.secret_key
        expires_minute = token_type.expires_minute

        to_encode = data.copy()
        iat = datetime.now()
        exp = datetime.now() + timedelta(minutes=expires_minute)
        to_encode.update({
            "iss": api_settings.AUTH_ISSUER,
            "aud": api_settings.AUTH_AUDIENCE,
            "nbf": int(iat.timestamp()),
            "iat": int(iat.timestamp()),
            "exp": int(exp.timestamp())})

        return encode(to_encode, secret_key, algorithm=api_settings.AUTH_ALGORITHM)

    @staticmethod
    def decode_token(token: str, secret_key: str) -> dict:
        """JWT를 디코딩합니다.

        Args:
            token (str): JWT
            secret_key (str): JWT 암호화 키

        Raises:
            HTTPException: JWT 만료시 발생하는 예외
            HTTPException: JWT 디코딩 실패시 발생하는 예외

        Returns:
            TokenPayload: JWT Payload
        """
        http_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="",
            headers={"WWW-Authenticate": JWT.JWT_TYPE},
        )

        try:
            payload = decode(
                token,
                secret_key,
                algorithms=[api_settings.AUTH_ALGORITHM],
                audience=api_settings.AUTH_AUDIENCE,
            )
            return TokenPayload(**payload)
        except ExpiredSignatureError as e:
            http_exception.detail = f"Token has expired. {e}"
            raise http_exception from e
        except InvalidTokenError as e:
            http_exception.detail = f"Could not validate credentials. {e}"
            raise http_exception from e
        except Exception as e:
            http_exception.detail = str(e)
            raise http_exception from e
