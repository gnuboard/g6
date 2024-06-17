"""API 환경설정 관련 파일"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class ApiSettings(BaseSettings):
    """
    API 서버의 설정을 관리하는 모델입니다.

    - 실제 환경변수의 값은 .env 파일에서 설정할 수 있습니다.
    - .env 파일이 없거나 값이 없는 경우, ApiSettings클래스의 기본값을 사용합니다.
    """
    # 읽어올 .env 파일의 설정을 선언합니다.
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',  # extra=forbid (default)
        frozen=True  # 값을 변경할 수 없도록 설정합니다.
    )

    API_VERSION: str = "v1"

    AUTH_ALGORITHM: str = "HS256"  # JWT 알고리즘
    AUTH_ISSUER: str = "g6_rest_api"  # JWT 발급자
    AUTH_AUDIENCE: str = "g6_rest_api"  # JWT 대상자

    ACCESS_TOKEN_EXPIRE_MINUTES: float = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: float = 60 * 24 * 14  # 14 days

    # JWT Secret Key
    # 보안을 위해 .env파일의 환경변수를 설정해야 합니다.
    ACCESS_TOKEN_SECRET_KEY: str = "access_token_secret_key"
    REFRESH_TOKEN_SECRET_KEY: str = "refresh_token_secret_key"


api_settings = ApiSettings()
