"""설문조사 유효성 검사를 위한 의존성 함수를 정의합니다."""
from typing_extensions import Annotated

from fastapi import Depends, Form, Path, Request

from core.models import Member, Poll
from lib.dependency.dependencies import validate_captcha
from lib.dependency.auth import get_login_member_optional
from service.poll_service import PollService, ValidatePollService


async def get_poll(
    service: Annotated[PollService, Depends()],
    po_id: Annotated[int, Path(..., title="설문조사 ID")],
):
    """투표 정보 조회 의존성 함수"""
    return service.read_poll(po_id)


async def get_poll_etc(
    service: Annotated[PollService, Depends()],
    pc_id: Annotated[int, Path(..., title="설문조사 기타의견 ID")],
):
    """투표 기타의견 조회 의존성 함수"""
    return service.read_poll_etc(pc_id)


async def validate_poll_read(
    validate: Annotated[ValidatePollService, Depends()],
    member: Annotated[Member, Depends(get_login_member_optional)],
    poll: Annotated[Poll, Depends(get_poll)],
):
    """투표 조회 유효성 검사 의존성 함수"""
    validate.is_used(poll)
    validate.check_level(poll, member)


async def validate_poll_update(
    validate: Annotated[ValidatePollService, Depends()],
    member: Annotated[Member, Depends(get_login_member_optional)],
    poll: Annotated[Poll, Depends(get_poll)],
):
    """투표 수정 유효성 검사 의존성 함수"""
    validate.is_used(poll)
    validate.is_participated(poll, member)
    validate.check_level(poll, member)


async def validate_poll_etc_create(
    request: Request,
    validate: Annotated[ValidatePollService, Depends()],
    member: Annotated[Member, Depends(get_login_member_optional)],
    poll: Annotated[Poll, Depends(get_poll)],
    recaptcha_response: str = Form("", alias="g-recaptcha-response")
):
    """투표 기타의견 등록 유효성 검사 의존성 함수"""

    validate.is_used(poll)
    validate.is_used_etc(poll)
    validate.check_level(poll, member)

    if not member:
        await validate_captcha(request, recaptcha_response)


async def validate_poll_etc_delete(
    validate: Annotated[ValidatePollService, Depends()],
    member: Annotated[Member, Depends(get_login_member_optional)],
    poll: Annotated[Poll, Depends(get_poll)],
    poll_etc: Annotated[Poll, Depends(get_poll_etc)]
):
    """투표 기타의견 삭제 유효성 검사 의존성 함수"""
    validate.is_used(poll)
    validate.is_used_etc(poll)
    validate.check_level(poll, member)
    validate.is_etc_owner(poll_etc, member)
