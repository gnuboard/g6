import secrets
from datetime import datetime
from typing import Any
from typing_extensions import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Path, Request

from core.database import db_session
from core.models import Member
from lib.common import get_client_ip
from lib.mail import send_register_mail
from lib.point import insert_point
from api.v1.models import responses
from api.v1.dependencies.member import (
    get_current_member, validate_create_data, validate_update_data
)
from api.v1.lib.member import MemberServiceAPI
from api.v1.models.member import CreateMemberModel, ResponseMemberModel, UpdateMemberModel

router = APIRouter()


@router.get("/member",
            summary="현재 로그인한 회원 정보 조회",
            description="JWT을 통해 현재 로그인한 회원 정보를 조회합니다. \
                <br>- 탈퇴 또는 차단된 회원은 조회할 수 없습니다. \
                <br>- 이메일 인증이 완료되지 않은 회원은 조회할 수 없습니다.",
            response_description="로그인한 회원 정보를 반환합니다.",
            response_model=ResponseMemberModel)
async def read_member_me(
    current_member: Annotated[Member, Depends(get_current_member)]
):
    """현재 로그인한 회원 정보를 조회합니다.

    Args:
        current_member (Member): 현재 로그인한 회원 정보

    Returns:
        Member: 현재 로그인한 회원 정보
    """
    return current_member


@router.get("/members/{mb_id}",
            summary="회원 정보 조회",
            response_model=ResponseMemberModel,
            responses={**responses})
async def read_member(
    member_service: Annotated[MemberServiceAPI, Depends()],
    current_member: Annotated[Member, Depends(get_current_member)]
):
    """회원 정보를 조회합니다."""
    return member_service.get_member_profile(current_member)


@router.post("/member",
             summary="회원 가입",
             response_model=ResponseMemberModel,
             responses={**responses})
async def create_member(
    request: Request,
    db: db_session,
    background_tasks: BackgroundTasks,
    data: Annotated[CreateMemberModel, Depends(validate_create_data)]
) -> Any:
    """
    회원 가입을 처리합니다.

    #### 회원가입과 함께 처리되는 작업
    - 회원가입 포인트 지급
    - 회원가입 메일 발송 (메일발송 설정 시)
    - 관리자에게 회원가입 메일 발송 (메일발송 설정 시)
    """
    config = request.state.config

    member = Member(**data.__dict__)
    member.mb_level = getattr(config, "cf_register_level", data.mb_level)
    member.mb_login_ip = get_client_ip(request)
    # 메일인증
    if getattr(config, "cf_use_email_certify", False):
        member.mb_email_certify2 = secrets.token_hex(16)  # 일회용 인증키
    else:
        member.mb_email_certify = datetime.now()  # 인증완료 처리

    db.add(member)
    db.commit()

    # 회원가입 포인트 지급
    insert_point(request, member.mb_id, config.cf_register_point,
                 "회원가입 축하", "@member", member.mb_id, "회원가입")

    # 추천인 포인트 지급
    mb_recommend = data.mb_recommend
    if getattr(config, "cf_use_recommend", False) and mb_recommend:
        insert_point(request, mb_recommend, getattr(config, "cf_use_recommend", 0),
                     f"{member.mb_id}의 추천인", "@member", mb_recommend, f"{member.mb_id} 추천")

    # 회원가입메일 발송 처리(백그라운드)
    background_tasks.add_task(send_register_mail, request, member)

    return member


@router.put("/member",
            summary="회원 정보 수정",
            response_model=ResponseMemberModel,
            responses={**responses})
async def update_member(
    db: db_session,
    current_member: Annotated[Member, Depends(get_current_member)],
    data: Annotated[UpdateMemberModel, Depends(validate_update_data)],
):
    """회원 정보를 수정합니다."""
    member_data = data.model_dump().items()
    for key, value in member_data:
        if hasattr(current_member, key) and value is not None:
            setattr(current_member, key, value)
    db.commit()

    return current_member


@router.put("/members/{mb_id}/email-certification/{key}",
            summary="회원가입 메일인증 처리")
async def certificate_email(
    db: db_session,
    member_service: Annotated[MemberServiceAPI, Depends()],
    key: str = Path(...)
):
    """
    회원가입 시, 메일인증을 처리합니다.  
    '기본환경설정'에서 메일인증을 사용하지 않을 경우 바로 인증처리됩니다.
    """
    member = member_service.get_email_non_certify_member(key)
    member.mb_email_certify = datetime.now()
    member.mb_email_certify2 = ""
    db.commit()

    return HTTPException(status_code=200, detail="메일인증이 완료되었습니다.")