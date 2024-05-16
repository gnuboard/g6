""".env 환경설정 값을 관리합니다."""
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_PATH = ".env"


class Settings(BaseSettings):
    """.env 파일 설정 모델"""
    # .env 파일을 읽어서 환경변수를 설정합니다.
    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
        env_file_encoding='utf-8',
        extra='ignore',  # extra=forbid (default)
    )

    ADMIN_THEME: str = "basic"  # 관리자 테마
    APP_IS_DEBUG: bool = False  # 디버그 모드

    COOKIE_DOMAIN: str = ""  # 쿠키 도메인

    # 데이터베이스 설정
    DB_TABLE_PREFIX: str = "g6_"
    DB_ENGINE: str = ""
    DB_USER: str = ""
    DB_PASSWORD: str = ""
    DB_HOST: str = ""
    DB_PORT: int = 3306
    DB_NAME: str = ""
    DB_CHARSET: str = "utf8mb4"

    IS_RESPONSIVE: bool = True  # 반응형 사용

    SESSION_COOKIE_NAME: str = "session"  # 세션 쿠키 이름
    SESSION_SECRET_KEY: str = ""  # 세션 비밀키

    # SMTP 설정
    SMTP_SERVER: str = "localhost"
    SMTP_PORT: int = 25
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""

    TIME_ZONE: str = "Asia/Seoul"  # 시간대

    # 에디터 업로드 설정
    UPLOAD_IMAGE_RESIZE: bool = False  # 에디터 이미지 리사이즈 사용
    UPLOAD_IMAGE_SIZE_LIMIT: int = 20  # 이미지 업로드 제한 용량 (MB)
    UPLOAD_IMAGE_RESIZE_WIDTH: int = 1200  # 이미지 리사이즈 너비 (px)
    UPLOAD_IMAGE_RESIZE_HEIGHT: int = 2800  # 이미지 리사이즈 높이 (px)
    UPLOAD_IMAGE_QUALITY: int = 80  # 이미지 품질 (0~100)

    USE_API: bool = True  # API 사용
    USE_TEMPLATE: bool = True  # 템플릿 사용


settings = Settings()
