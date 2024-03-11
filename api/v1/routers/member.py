import secrets
from datetime import datetime
from typing import Any
from typing_extensions import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from fastapi.templating import Jinja2Templates

from core.database import db_session, DBConnect
from core.models import Config, Member
from core.template import TemplateService
from lib.common import get_client_ip, mailer
from lib.point import insert_point

from api.v1.models import responses
from api.v1.dependencies.member import get_current_member, validate_create_member, validate_update_member
from api.v1.models.member import CreateMemberModel, ResponseMemberModel, UpdateMemberModel

router = APIRouter()


@router.get("/me",
            summary="현재 로그인한 회원 정보 조회",
            description="JWT을 통해 현재 로그인한 회원 정보를 조회합니다. \
                <br>- 탈퇴 또는 차단된 회원은 조회할 수 없습니다. \
                <br>- 이메일 인증이 완료되지 않은 회원은 조회할 수 없습니다.",
            response_description="로그인한 회원 정보를 반환합니다.")
async def read_members_me(
    current_member: Annotated[Member, Depends(get_current_member)]
):
    """현재 로그인한 회원 정보를 조회합니다.

    Args:
        current_member (Annotated[Member, Depends(get_current_member)]): 현재 로그인한 회원 정보

    Returns:
        Member: 현재 로그인한 회원 정보
    """
    return current_member


@router.post("",
             summary="회원 가입",
             response_model=ResponseMemberModel,
             responses={**responses})
async def create_member(
    request: Request,
    db: db_session,
    background_tasks: BackgroundTasks,
    data: Annotated[CreateMemberModel, Depends(validate_create_member)]
) -> Any:
    """
    회원 가입을 처리합니다.

    #### 회원가입과 함께 처리되는 작업
    - 회원가입 포인트 지급
    - 회원가입 메일 발송 (메일발송 설정 시)
    - 관리자에게 회원가입 메일 발송 (메일발송 설정 시)
    """

    config = request.state.config
    # TODO: 인증은 아직 구현하지 않으므로 삭제예정
    # if mb_certify_case and member.mb_certify:
    #     member.mb_certify = mb_certify_case
    #     member.mb_adult = member.mb_adult
    # else:
    #     member.mb_certify = ""
    #     member.mb_adult = 0
    # TODO: 회원 이미지 업로드 API는 별도로 구현 예정
    # # 이미지 검사 & 업로드
    # validate_and_update_member_image(request, mb_img, mb_icon, mb_id, None, None)

    # TODO: mb_sex 정규식으로 검사하므로 삭제예정
    # if member_form.mb_sex not in {"m", "f"}:
    #     member_form.mb_sex = ""

    # TODO: 레벨 입력방지 => 모델에서 선언되지 않으므로 삭제예정
    # del member_form.mb_level

    member = Member(**data.__dict__)
    # member.mb_datetime = datetime.now()   # TODO: Model 기본값 설정으로 변경, 삭제예정
    # member.mb_lost_certify = ""   # TODO: 필요없음, 삭제예정
    # # DB 스키마 호환성을 위해 null 대신 최저년도를 사용.
    # member.mb_nick_date = datetime(1, 1, 1, 0, 0, 0)  # TODO: 필요없음, 삭제예정
    # member.mb_open_date = datetime(1, 1, 1, 0, 0, 0)  # TODO: 필요없음, 삭제예정
    # member.mb_today_login = datetime.now()  # Model 기본값 설정으로 변경, 삭제예정

    # 추가 회원정보 설정
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


@router.put("/{mb_id}",
            summary="회원 정보 수정",
            response_model=ResponseMemberModel,
            responses={**responses})
async def update_member(
    db: db_session,
    current_member: Annotated[Member, Depends(get_current_member)],
    data: Annotated[UpdateMemberModel, Depends(validate_update_member)],
):
    """회원 정보를 수정합니다."""
    member_data = data.model_dump().items()
    for key, value in member_data:
        if hasattr(current_member, key) and value is not None:
            setattr(current_member, key, value)
    db.commit()

    return current_member


def send_register_mail(request: Request, member: Member) -> None:
    """background task > 회원가입 메일 발송 처리

    Args:
        request (Request): Request 객체
        member (Member): 신규가입한 회원 객체
    """
    # background에서 Session 공유 문제로 인해 DBConnect().sessionLocal() 사용
    with DBConnect().sessionLocal() as db:
        request.state.config = config = db.query(Config).first()
    context = {
        "request": request,
        "member": member,
    }
    try:
        templates = Jinja2Templates(
            directory=TemplateService.get_templates_dir())

        # 회원에게 인증메일 발송
        if config.cf_use_email_certify:
            subject = f"[{config.cf_title}] 회원가입 인증메일 발송"
            cntx = context + \
                {"certify_href": f"{request.base_url.__str__()}bbs/email_certify/{member.mb_id}?certify={member.mb_email_certify2}"}
            body = templates.TemplateResponse(
                "bbs/mail_form/register_certify_mail.html",
                cntx
            ).body.decode("utf-8")
            mailer(member.mb_email, subject, body)
        # 회원에게 회원가입 메일 발송
        elif config.cf_email_mb_member:
            subject = f"[{config.cf_title}] 회원가입을 축하드립니다."
            body = templates.TemplateResponse(
                "bbs/mail_form/register_send_member_mail.html",
                context
            ).body.decode("utf-8")
            mailer(member.mb_email, subject, body)

        # 최고관리자에게 회원가입 메일 발송
        if config.cf_email_mb_super_admin:
            subject = f"[{config.cf_title}] {member.mb_nick} 님께서 회원으로 가입하셨습니다."
            body = templates.TemplateResponse(
                "bbs/mail_form/register_send_admin_mail.html",
                context
            ).body.decode("utf-8")
            mailer(config.cf_admin_email, subject, body)
    except Exception as e:
        print(e)
