"""API 환경설정 관련 파일"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class ApiSettings(BaseSettings):
    """API 설정 모델"""
    # .env 파일을 읽어서 환경변수를 설정합니다.
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',  # extra=forbid (default)
        frozen=True  # 값을 변경할 수 없도록 설정합니다.
    )

    API_VERSION: str = "v1"

    AUTH_ALGORITHM: str = "HS256"  # JWT 알고리즘
    AUTH_ISSUER: str = "g6_rest_api"  # JWT 발급자

    ACCESS_TOKEN_EXPIRE_MINUTES: float = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: float = 60 * 24 * 14  # 14 days

    # JWT Secret Key
    # 보안을 위해 .env파일의 환경변수를 설정해야 합니다.
    ACCESS_TOKEN_SECRET_KEY: str = "access_token_secret_key"
    REFRESH_TOKEN_SECRET_KEY: str = "refresh_token_secret_key"


api_settings = ApiSettings()
