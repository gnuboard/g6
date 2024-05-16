"""회원 관련 API Router"""
from datetime import datetime
from typing_extensions import Annotated

from fastapi import (
    APIRouter, BackgroundTasks, Depends, File, Form, Path, Query,
    Request, status, UploadFile
)
from sqlalchemy import delete

from api.v1.service.point import PointServiceAPI
from bbs.social import SocialAuthService
from core.database import db_session
from core.models import Member
from lib.mail import send_password_reset_mail, send_register_mail

from api.v1.dependencies.member import (
    get_current_member, validate_create_data, validate_update_data
)
from api.v1.service.member import (
    MemberServiceAPI,
    MemberImageServiceAPI as ImageService
)
from api.v1.models import MemberRefreshToken
from api.v1.models.member import (
    CreateMember, SearchMemberId, SearchMemberPassword,
    ResetMemberPassword, MemberResponse, RegisterResponse,
    SearchMemberIdResponse, UpdateMember
)
from api.v1.models.response import (
    MessageResponse, response_401, response_403, response_404, response_409, response_422
)

router = APIRouter()


@router.post("/members",
             summary="회원 가입",
             status_code=status.HTTP_201_CREATED,
             responses={**response_403, **response_409, **response_422})
async def create_member(
    request: Request,
    background_tasks: BackgroundTasks,
    service: Annotated[MemberServiceAPI, Depends()],
    point_service: Annotated[PointServiceAPI, Depends()],
    data: Annotated[CreateMember, Depends(validate_create_data)]
) -> RegisterResponse:
    """
    회원 가입을 처리합니다.

    #### 회원가입과 함께 처리되는 작업
    - 회원가입 & 추천인 포인트 지급
    - 회원가입 메일 발송 (메일발송 설정 시)
    - 관리자에게 회원가입 메일 발송 (메일발송 설정 시)
    """
    config = request.state.config
    member = service.create_member(data)

    # 회원가입 포인트 지급
    register_point = getattr(config, "cf_register_point", 0)
    point_service.save_point(member.mb_id, register_point, "회원가입 축하",
                             "@member", member.mb_id, "회원가입")

    # 추천인 포인트 지급
    mb_recommend = data.mb_recommend
    if getattr(config, "cf_use_recommend", False) and mb_recommend:
        recommend_point = getattr(config, "cf_recommend_point", 0)
        point_service.save_point(mb_recommend, recommend_point, f"{member.mb_id}의 추천인",
                                 "@member", mb_recommend, f"{member.mb_id} 추천")

    # 회원가입메일 발송 처리(백그라운드)
    background_tasks.add_task(send_register_mail, request, member)

    message = "회원가입이 완료되었습니다."
    if member.mb_email_certify2:
        message += " 이메일 인증을 진행해주세요."

    return {
        "message": message,
        "mb_id": member.mb_id,
        "mb_name": member.mb_name,
        "mb_nick": member.mb_nick,
    }


@router.put("/members/{mb_id}/email-certification",
            summary="회원가입 메일인증 처리")
async def certificate_email(
    db: db_session,
    member_service: Annotated[MemberServiceAPI, Depends()],
    mb_id: Annotated[str, Path(title="회원 아이디", description="회원 아이디")],
    certify_key: str = Query(..., title="인증키", description="이메일 인증키")
) -> MessageResponse:
    """
    회원가입 시, 메일인증을 처리합니다.  
    '관리자 > 기본환경설정'에서 메일인증을 사용하지 않을 경우, 이 API는 사용되지 않습니다.
    """
    member = member_service.read_email_non_certify_member(mb_id, certify_key)
    member.mb_email_certify = datetime.now()
    member.mb_email_certify2 = ""
    db.commit()

    return {"message": "이메일 인증이 완료되었습니다."}


@router.get("/members/me",
            summary="현재 로그인 회원 정보 조회",
            responses={**response_401, **response_403, **response_404})
async def read_member_me(
    member: Annotated[Member, Depends(get_current_member)]
) -> MemberResponse:
    """
    JWT 토큰을 통해 인증된 회원 정보를 조회합니다.
    - 탈퇴 또는 차단된 회원은 조회할 수 없습니다.
    - 이메일 인증이 완료되지 않은 회원은 조회할 수 없습니다.
    """
    return member


@router.get("/members/{mb_id}",
            summary="회원 정보 조회",
            responses={**response_401, **response_403, **response_404})
async def read_member(
    service: Annotated[MemberServiceAPI, Depends()],
    current_member: Annotated[Member, Depends(get_current_member)],
    mb_id: Annotated[str, Path(title="회원 아이디", description="회원 아이디")],
) -> MemberResponse:
    """
    회원 정보를 조회합니다.
    - 자신&상대방의 정보가 공개 설정된 경우 조회 가능합니다.
    """
    return service.get_member_profile(mb_id, current_member)


@router.put("/member",
            summary="회원 정보 수정",
            responses={**response_401, **response_403,
                       **response_409, **response_422})
async def update_member(
    service: Annotated[MemberServiceAPI, Depends()],
    member: Annotated[Member, Depends(get_current_member)],
    data: Annotated[UpdateMember, Depends(validate_update_data)],
) -> MessageResponse:
    """JWT 토큰을 통해 인증된 회원 정보를 수정합니다."""
    service.update_member(member, data.model_dump())

    return {"message": "회원정보 수정이 완료되었습니다."}


@router.put("/member/image",
            summary="회원 아이콘&이미지 수정",
            responses={**response_401, **response_403, **response_422})
async def update_member_image(
    service: Annotated[ImageService, Depends()],
    member: Annotated[Member, Depends(get_current_member)],
    mb_img: Annotated[UploadFile, File(title="첨부파일1")] = None,
    mb_icon: Annotated[UploadFile, File(title="첨부파일2")] = None,
    del_mb_img: Annotated[int, Form(title="첨부파일1 삭제 여부")] = 0,
    del_mb_icon: Annotated[int, Form(title="첨부파일2 삭제 여부")] = 0,
) -> MessageResponse:
    """JWT 토큰을 통해 인증된 회원의 아이콘 & 이미지를 수정합니다."""
    service.update_image_file(member.mb_id, 'image', mb_img, del_mb_img)
    service.update_image_file(member.mb_id, 'icon', mb_icon, del_mb_icon)

    return {"message": "회원 이미지가 수정되었습니다."}


@router.delete("/member",
              summary="회원 탈퇴",
              responses={**response_401, **response_403})
async def leave_member(
    db: db_session,
    service: Annotated[MemberServiceAPI, Depends()],
    member: Annotated[Member, Depends(get_current_member)]
) -> MessageResponse:
    """
    JWT 토큰을 통해 인증된 회원을 탈퇴 처리합니다.
    - 실제로 데이터가 삭제되지 않고, 탈퇴 처리만 진행됩니다.
    """
    service.leave_member(member)

    # 소셜로그인 연동 해제
    SocialAuthService.unlink_social_login(member.mb_id)

    # 토큰 삭제
    db.execute(delete(MemberRefreshToken)
               .where(MemberRefreshToken.mb_id == member.mb_id))
    db.commit()

    return {"message": "회원탈퇴가 처리되었습니다."}


@router.post("/members/search/id",
             summary="회원 아이디 찾기",
             responses={**response_404, **response_422})
async def find_member_id(
    service: Annotated[MemberServiceAPI, Depends()],
    data: SearchMemberId
) -> SearchMemberIdResponse:
    """
    이름, 이메일을 통해 회원아이디를 찾습니다.
    - 아이디는 가운데 글자를 *로 가려서 반환합니다.
    - 소셜 로그인으로 가입한 회원은 아이디 찾기가 불가능합니다.
    """
    mb_id, register_date = service.find_id(data.mb_name, data.mb_email)

    return {
        "mb_id": mb_id,
        "register_date": register_date
    }


@router.post("/members/search/password",
             summary="비밀번호 재설정 메일 발송",
             responses={**response_404, **response_422})
async def find_member_password(
    request: Request,
    background_tasks: BackgroundTasks,
    member_service: Annotated[MemberServiceAPI, Depends()],
    data: SearchMemberPassword
) -> MessageResponse:
    """아이디, 이메일을 통해 비밀번호를 재설정할 수 있는 링크를 메일로 발송합니다."""
    member = member_service.find_member_from_password_info(data.mb_id, data.mb_email)
    # 비밀번호 재설정 메일 발송 처리(백그라운드)
    background_tasks.add_task(send_password_reset_mail, request, member)

    return {"message": "비밀번호 재설정 메일이 발송되었습니다."}


@router.patch("/members/{mb_id}/password/{token}",
              name="reset_password_api",
              summary="비밀번호 재설정",
              responses={**response_404, **response_422})
async def reset_password(
    member_service: Annotated[MemberServiceAPI, Depends()],
    mb_id: Annotated[str, Path(title="회원 아이디", description="회원 아이디")],
    token: Annotated[str, Path(title="토큰", description="비밀번호 재설정 토큰")],
    data: ResetMemberPassword
) -> MessageResponse:
    """비밀번호를 재설정합니다."""
    member_service.reset_password(mb_id, token, data.password)

    return {"message": "비밀번호가 재설정되었습니다."}
