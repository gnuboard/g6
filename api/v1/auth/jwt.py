from datetime import datetime, timedelta
from enum import Enum

from fastapi import HTTPException, status
from jose import ExpiredSignatureError, JWTError, jwt

from api.settings import SETTINGS
from api.v1.models.auth import TokenPayload


class TokenType(Enum):
    ACCESS = {
        "secret_key": SETTINGS.ACCESS_TOKEN_SECRET_KEY,
        "expires_minute": SETTINGS.ACCESS_TOKEN_EXPIRE_MINUTES
    }
    REFRESH = {
        "secret_key": SETTINGS.REFRESH_TOKEN_SECRET_KEY,
        "expires_minute": SETTINGS.REFRESH_TOKEN_EXPIRE_MINUTES
    }

class JWT:
    """JWT 관련 작업을 처리하는 클래스입니다."""

    JWT_TYPE = "Bearer"

    @staticmethod
    def create_token(data: dict, token_type: TokenType) -> str:
        """JWT를 생성합니다.

        Args:
            data (dict): JWT에 담을 데이터
            token_type (TokenType): JWT 종류 (ACCESS, REFRESH)
        Returns:
            str: JWT
        """
        secret_key = token_type.value["secret_key"]
        expires_minute = token_type.value["expires_minute"]
        to_encode = data.copy()
        expire = datetime.now() + timedelta(minutes=expires_minute)
        to_encode.update({"exp": expire})
        print(f"Settings.{token_type.name.lower()}_token_secret_key", secret_key)

        return jwt.encode(to_encode, secret_key, algorithm=SETTINGS.AUTH_ALGORITHM)

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

        try:
            payload = jwt.decode(token, secret_key, algorithms=[SETTINGS.AUTH_ALGORITHM])
            return TokenPayload(**payload)
        except ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
