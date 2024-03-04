from datetime import datetime, timedelta
from typing import Union

from fastapi import HTTPException, status
from jose import ExpiredSignatureError, JWTError, jwt

from api.settings import SETTINGS
from api.v1.models.auth import TokenPayload


class JWT:
    """JWT 관련 작업을 처리하는 클래스입니다."""

    JWT_TYPE = "Bearer"

    def _encode_jwt(
            self,
            data: dict,
            secret_key: str,
            expires_minute: Union[float, None]) -> str:
        """JWT를 생성합니다.

        Args:
            data (dict): JWT에 담을 데이터
            secret_key (str): JWT 암호화 키
            expires_minute (Union[float, None]): 만료 시간 (분)

        Returns:
            str: JWT
        """

        to_encode = data.copy()
        expire = datetime.now() + timedelta(minutes=expires_minute)
        to_encode.update({"exp": expire})

        return jwt.encode(to_encode, secret_key, algorithm=SETTINGS.AUTH_ALGORITHM)

    @staticmethod
    def create_access_token(data: dict) -> str:
        """Access Token을 생성합니다.

        Args:
            data (dict): Access Token에 담을 데이터

        Returns:
            str: Access Token
        """
        print("SETTINGS.ACCESS_TOKEN_SECRET_KEY", SETTINGS.ACCESS_TOKEN_SECRET_KEY)
        jwt = JWT()
        return jwt._encode_jwt(
            data,
            SETTINGS.ACCESS_TOKEN_SECRET_KEY,
            SETTINGS.ACCESS_TOKEN_EXPIRE_MINUTES)

    @staticmethod
    def create_refresh_token(data: dict) -> str:
        """Refresh Token을 생성합니다.

        Args:
            data (dict): Refresh Token에 담을 데이터

        Returns:
            str: Refresh Token
        """
        jwt = JWT()
        return jwt._encode_jwt(
            data,
            SETTINGS.REFRESH_TOKEN_SECRET_KEY,
            SETTINGS.REFRESH_TOKEN_EXPIRE_MINUTES)

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
