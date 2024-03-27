from datetime import datetime
from typing import Any
from typing_extensions import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Path, Request
from sqlalchemy import delete

from bbs.social import SocialAuthService
from core.database import db_session
from core.models import Member
from lib.mail import send_register_mail, send_password_reset_mail
from lib.point import insert_point
from api.v1.models import MemberRefreshToken, responses
from api.v1.dependencies.member import (
    get_current_member, validate_create_data, validate_update_data
)
from api.v1.lib.member import MemberServiceAPI
from api.v1.models.member import (
    CreateMemberModel, ResponseMemberModel, UpdateMemberModel,
    FindMemberIdModel, FindMemberPasswordModel, ResetMemberPasswordModel
)

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
    current_member: Annotated[Member, Depends(get_current_member)],
    mb_id: Annotated[str, Path(...)]
):
    """회원 정보를 조회합니다."""
    return member_service.get_member_profile(mb_id, current_member)


@router.post("/member",
             summary="회원 가입",
             response_model=ResponseMemberModel,
             responses={**responses})
async def create_member(
    request: Request,
    member_service: Annotated[MemberServiceAPI, Depends()],
    background_tasks: BackgroundTasks,
    data: Annotated[CreateMemberModel, Depends(validate_create_data)]
) -> Any:
    """
    회원 가입을 처리합니다.

    #### 회원가입과 함께 처리되는 작업
    - 회원가입 & 추천인 포인트 지급
    - 회원가입 메일 발송 (메일발송 설정 시)
    - 관리자에게 회원가입 메일 발송 (메일발송 설정 시)
    """
    config = request.state.config
    member = member_service.create_member(data)

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
    member_service: Annotated[MemberServiceAPI, Depends()],
    current_member: Annotated[Member, Depends(get_current_member)],
    data: Annotated[UpdateMemberModel, Depends(validate_update_data)],
):
    """회원 정보를 수정합니다."""
    member_service.update_member(current_member, data.model_dump())

    return current_member


@router.put("/members/{mb_id}/email-certification/{key}",
            summary="회원가입 메일인증 처리")
async def certificate_email(
    db: db_session,
    member_service: Annotated[MemberServiceAPI, Depends()],
    mb_id: Annotated[str, Path(...)],
    key: str = Path(...)
):
    """
    회원가입 시, 메일인증을 처리합니다.  
    '기본환경설정'에서 메일인증을 사용하지 않을 경우 바로 인증처리됩니다.
    """
    member = member_service.get_email_non_certify_member(mb_id, key)
    member.mb_email_certify = datetime.now()
    member.mb_email_certify2 = ""
    db.commit()

    return HTTPException(status_code=200, detail="메일인증이 완료되었습니다.")


@router.patch("/member/leave",
              summary="회원 탈퇴",
              responses={**responses})
async def leave_member(
    db: db_session,
    member_service: Annotated[MemberServiceAPI, Depends()],
    current_member: Annotated[Member, Depends(get_current_member)]
):
    """현재 로그인한 회원을 탈퇴 처리합니다."""
    member_service.leave_member(current_member)

    # 소셜로그인 연동 해제
    SocialAuthService.unlink_social_login(current_member.mb_id)

    # 토큰 삭제
    db.execute(delete(MemberRefreshToken)
               .where(MemberRefreshToken.mb_id == current_member.mb_id))
    db.commit()

    return HTTPException(status_code=200, detail="회원탈퇴가 처리되었습니다.")


@router.post("/member/find/id",
            summary="회원아이디 찾기",
            responses={**responses})
async def find_member_id(
    member_service: Annotated[MemberServiceAPI, Depends()],
    data: FindMemberIdModel
):
    """회원아이디를 찾습니다."""
    member_id, register_date = member_service.find_id(data.mb_name, data.mb_email)

    return {
        "member_id": member_id,
        "register_date": register_date
    }


@router.post("/member/find/password",
            summary="비밀번호 재설정 메일 발송",
            responses={**responses})
async def find_member_password(
    request: Request,
    background_tasks: BackgroundTasks,
    member_service: Annotated[MemberServiceAPI, Depends()],
    data: FindMemberPasswordModel
):
    """비밀번호를 재설정할 수 있는 링크를 메일로 발송합니다."""
    # 회원정보 조회
    member = member_service.find_member_from_password_info(data.mb_id, data.mb_email)
    # 비밀번호 재설정 메일 발송 처리(백그라운드)
    background_tasks.add_task(send_password_reset_mail, request, member)
    
    return HTTPException(status_code=200, detail="비밀번호 찾기 메일이 발송되었습니다.")


@router.patch("/member/{mb_id}/password-reset/{token}",
               name="reset_password_api",
               summary="비밀번호 재설정",
               responses={**responses})
async def reset_password(
    member_service: Annotated[MemberServiceAPI, Depends()],
    mb_id: Annotated[str, Path(..., title="아이디")],
    token: Annotated[str, Path(..., title="토큰")],
    data: ResetMemberPasswordModel
):
    """비밀번호를 재설정합니다."""
    member_service.reset_password(mb_id, token, data.password)

    return HTTPException(status_code=200, detail="비밀번호가 재설정되었습니다.")