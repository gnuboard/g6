import secrets

from fastapi import Request

def create_session_token(request: Request):
    """
    토큰 생성 후 세션에 저장&반환

    Args:
        request (Request): FastAPI Request 객체

    Returns:
        str: 생성된 토큰
    """
    token = secrets.token_hex(16)  # 16바이트 토큰 생성
    request.session["ss_token"] = token  # 세션에 토큰 저장
    return token

def check_token(request: Request, token: str) -> bool:
    """세션과 인수로 넘어온 토큰확인 함수

    Args:
        request (Request): FastAPI Request 객체
        token (str): token 문자열

    Returns:
        bool: 토큰 일치 여부
    """
    if not token:
        return False

    token = token.strip()
    if token == request.session.get("ss_token"):
        # 세션 삭제
        request.session["ss_token"] = ""
        return True

    return False


