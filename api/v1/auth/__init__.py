from fastapi.security import OAuth2PasswordBearer

# oauth2_scheme는 OAuth 2.0 표준을 따르는 인증 방식을 사용하는 보안 요청을 처리합니다.
# TODO : /api/v1/token 값을 설정할 수 있도록 .env의 값을 가져오도록 설정합니다.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/token")