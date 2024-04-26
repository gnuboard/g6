from fastapi.security import OAuth2PasswordBearer

from api.settings import api_settings


# oauth2_scheme는 OAuth 2.0 표준을 따르는 인증 방식을 사용하는 보안 요청을 처리합니다.
TOKEN_URL = f"/api/{api_settings.API_VERSION}/token"

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=TOKEN_URL,
    description="""로그인을 통해 Access Token 발급 후, API 요청 시 Authorization 헤더를 추가합니다.  
> Authorization: Bearer {Access Token}"""
)
oauth2_optional = OAuth2PasswordBearer(
    tokenUrl=TOKEN_URL,
    auto_error=False,
    scheme_name="OAuth2PasswordBearer(Optional)",
    description="""Access Token발급 여부와 관계없이 API 요청이 가능합니다.  
> Access Token이 발급되었을 경우: Authorization: Bearer {Access Token}  
> Access Token이 발급되지 않았을 경우: 비회원으로 인식"""
)
