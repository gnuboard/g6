"""환경설정 관련 API Router"""
from fastapi import APIRouter, Request

from api.v1.models.config import (
    HtmlBaseResponse, MemoResponse, PolicyResponse, RegisterResponse
)
from api.v1.models.response import response_500
from api.v1.models import Tags

router = APIRouter(
    prefix="/config",
    responses={**response_500}
)


@router.get("/html",
            summary="HTML 설정 조회")
async def read_config_html(request: Request) -> HtmlBaseResponse:
    """HTML을 구성하는데 필요한 설정 정보를 조회합니다."""
    return request.state.config


@router.get("/policy",
            summary="회원가입 약관 조회",
            tags=[Tags.MEMBER])
async def read_member_policy(request: Request) -> PolicyResponse:
    """
    회원가입 약관을 조회합니다.
    - 회원가입 약관
    - 개인정보 수집 및 허용 약관
    """
    return request.state.config


@router.get("/member",
            summary="회원가입 설정 조회",
            tags=[Tags.MEMBER])
async def read_config_member(request: Request) -> RegisterResponse:
    """회원가입에 필요한 기본환경설정 정보를 조회합니다."""
    return request.state.config


@router.get("/memo",
            summary="쪽지 발송 시, 설정 포인트 조회",
            tags=[Tags.MEMO])
async def read_config_memo(request: Request) -> MemoResponse:
    """쪽지 발송 시, 1건당 소모되는 포인트 설정 정보를 조회합니다."""
    return request.state.config
