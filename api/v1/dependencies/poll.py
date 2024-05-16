"""설문조사 유효성 검사를 위한 의존성 함수를 정의합니다."""
from typing_extensions import Annotated

from fastapi import Depends, Path

from api.v1.dependencies.member import (
    get_current_member, get_current_member_optional
)
from api.v1.service.poll import PollServiceAPI, ValidatePollServiceAPI
from core.models import Member, Poll, PollEtc


async def get_poll(
    service: Annotated[PollServiceAPI, Depends()],
    po_id: Annotated[int, Path(title="설문조사 ID",
                               description="설문조사 ID")],
):
    """설문조사 정보 조회 의존성 함수"""
    return service.read_poll(po_id)


async def get_poll_etc(
    service: Annotated[PollServiceAPI, Depends()],
    pc_id: Annotated[int, Path(title="기타의견 ID",
                               description="설문조사 기타의견 ID")],
):
    """설문조사 기타의견 조회 의존성 함수"""
    return service.read_poll_etc(pc_id)


async def validate_poll_read(
    validate: Annotated[ValidatePollServiceAPI, Depends()],
    poll: Annotated[Poll, Depends(get_poll)],
    member: Annotated[Member, Depends(get_current_member_optional)],
):
    """설문조사 조회 유효성 검사 의존성 함수"""
    validate.is_used(poll)
    validate.check_level(poll, member)


async def validate_poll_update(
    validate: Annotated[ValidatePollServiceAPI, Depends()],
    poll: Annotated[Poll, Depends(get_poll)],
    member: Annotated[Member, Depends(get_current_member_optional)],
):
    """설문조사 수정 유효성 검사 의존성 함수"""
    validate.is_used(poll)
    validate.is_participated(poll, member)
    validate.check_level(poll, member)


async def validate_poll_etc_create(
    validate: Annotated[ValidatePollServiceAPI, Depends()],
    poll: Annotated[Poll, Depends(get_poll)],
    member: Annotated[Member, Depends(get_current_member_optional)],
):
    """설문조사 기타의견 등록 유효성 검사 의존성 함수"""

    validate.is_used(poll)
    validate.is_used_etc(poll)
    validate.check_level(poll, member)


async def validate_poll_etc_delete(
    validate: Annotated[ValidatePollServiceAPI, Depends()],
    poll: Annotated[Poll, Depends(get_poll)],
    poll_etc: Annotated[PollEtc, Depends(get_poll_etc)],
    member: Annotated[Member, Depends(get_current_member)]
):
    """설문조사 기타의견 삭제 유효성 검사 의존성 함수"""
    validate.is_used(poll)
    validate.is_used_etc(poll)
    validate.check_level(poll, member)
    validate.is_etc_owner(poll_etc, member)
