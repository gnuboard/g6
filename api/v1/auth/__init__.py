from fastapi.security import OAuth2PasswordBearer

from api.settings import SETTINGS

# oauth2_scheme는 OAuth 2.0 표준을 따르는 인증 방식을 사용하는 보안 요청을 처리합니다.
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"/api/{SETTINGS.REST_API_VERSION}/token")