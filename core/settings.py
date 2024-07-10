""".env 환경설정 값을 관리합니다."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from lib.print_log import PrintLog


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

    # CORS 설정
    CORS_ALLOW_ORIGINS: str = "*"
    CORS_ALLOW_CREDENTIALS: bool = False
    CORS_ALLOW_METHODS: str = "*"
    CORS_ALLOW_HEADERS:str = "*"

settings = Settings()


class CORSConfig:
    """CORS 설정"""

    def parse_comma_separated_list(self, value):
        """쉼표로 구분된 문자열을 리스트로 변환합니다."""
        if value == "*":
            return ["*"]
        return [item.strip() for item in value.split(",") if item.strip()]

    @property
    def allow_origins(self):
        """CORS 허용 도메인"""
        return self.parse_comma_separated_list(settings.CORS_ALLOW_ORIGINS)

    @property
    def allow_credentials(self):
        """CORS 허용 쿠키 전송 여부"""
        allow_credentials = settings.CORS_ALLOW_CREDENTIALS
        if not isinstance(allow_credentials, bool):
            allow_credentials = settings.CORS_ALLOW_CREDENTIALS.lower() == "true"
        if allow_credentials and self.allow_origins == ["*"]:
            PrintLog.warn("allow_origins를 모두 허용하는 것과 allow_credentials를 True로 함께 설정할 수 없습니다.")
            PrintLog.warn("보안을 위해 allow_credentials를 False로 설정합니다.")
            allow_credentials = False
        return allow_credentials

    @property
    def allow_methods(self):
        """CORS 허용 메서드"""
        return self.parse_comma_separated_list(settings.CORS_ALLOW_METHODS)

    @property
    def allow_headers(self):
        """CORS 허용 헤더"""
        return self.parse_comma_separated_list(settings.CORS_ALLOW_HEADERS)


cors_config = CORSConfig()