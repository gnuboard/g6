"""캡차 API Router"""
from typing_extensions import Annotated
from fastapi import APIRouter, Body, HTTPException, Request

from api.v1.models.response import (
    MessageResponse, response_400, response_404, response_422
)
from lib.captcha import get_current_captcha_cls

router = APIRouter(prefix="/captcha")


@router.post("/recaptcha/verify",
             summary="구글 reCAPTCHA 유효성 검사",
             responses={**response_400, **response_404, **response_422})
async def recaptcha_verify(
    request: Request,
    recaptcha_response: Annotated[str, Body()] = None,
) -> MessageResponse:
    """
    구글 reCAPTCHA 유효성 검사
    
    #### Request Body
    - recaptcha_response: 구글 reCAPTCHA 응답 토큰
    """
    config = request.state.config

    captcha_cls = get_current_captcha_cls(config)
    if not captcha_cls:
        raise HTTPException(status_code=404, detail="사용할 수 있는 캡차가 없습니다.")

    captcha = captcha_cls(config)
    if captcha and (not await captcha.verify(recaptcha_response)):
        raise HTTPException(status_code=400, detail="캡차가 올바르지 않습니다.")

    return {"message": "캡차가 올바릅니다."}
