"""회원정보 수정 Template Router"""
from typing_extensions import Annotated

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from sqlalchemy import select
from starlette.responses import RedirectResponse

from core.database import db_session
from core.exception import AlertException
from core.formclass import MemberForm
from core.models import Config, Member, MemberSocialProfiles
from core.template import UserTemplates
from lib.common import captcha_widget, check_profile_open, get_next_profile_openable_date
from lib.dependencies import get_login_member, validate_captcha, validate_token
from lib.dependency.member import validate_update_member
from lib.member_lib import MemberImageService, MemberService
from lib.pbkdf2 import validate_password
from lib.template_filters import default_if_none

router = APIRouter()
templates = UserTemplates()
templates.env.filters["default_if_none"] = default_if_none
templates.env.globals["captcha_widget"] = captcha_widget
templates.env.globals["check_profile_open"] = check_profile_open


@router.get("/member_confirm")
async def check_member_form(
    request: Request,
    db: db_session,
    member: Annotated[Member, Depends(get_login_member)]
):
    """
    회원프로필 수정 전 비밀번호 확인 폼
    """
    # 회원정보를 수정할 수 있는지 확인하는 세션변수
    request.session["ss_profile_change"] = False

    # 소셜로그인 사용중이면 소셜로그인 정보가 있는지 확인
    if request.state.config.cf_social_login_use:
        social_member = db.scalar(
            select(MemberSocialProfiles).filter_by(mb_id=member.mb_id)
        )
        if social_member:
            request.session["ss_profile_change"] = True
            return RedirectResponse(url="/bbs/member_profile", status_code=302)

    context = {
        "request": request,
        "member": member,
        "action_url": request.url_for("member_password")
    }
    return templates.TemplateResponse("/member/member_confirm.html", context)


@router.post("/member_confirm", name='member_password')
async def check_member(
    request: Request,
    member: Annotated[Member, Depends(get_login_member)],
    mb_password: str = Form(...)
):
    """
    회원프로필 수정 전 비밀번호 확인 처리
    """
    if not validate_password(mb_password, member.mb_password):
        raise AlertException("아이디 또는 패스워드가 일치하지 않습니다.", 404)

    request.session["ss_profile_change"] = True

    return RedirectResponse(url="/bbs/member_profile", status_code=302)


@router.get("/member_profile", name='member_profile')
async def member_profile(
    request: Request,
    db: db_session,
    member: Annotated[Member, Depends(get_login_member)],
):
    """
    회원프로필 수정 폼
    """
    config = request.state.config

    if not request.session.get("ss_profile_change", False):
        raise AlertException("잘못된 접근입니다", 403, url="/")

    member = db.scalar(select(Member).filter_by(mb_id=member.mb_id))
    if not member:
        raise AlertException("회원정보가 없습니다.", 404)

    form_context = {
        "action_url": request.url_for("member_profile_save").path,
        "name_readonly": "readonly",
        "hp_readonly": "readonly" if get_is_phone_certify(member, config) else "",
        "mb_icon_url": MemberImageService.get_icon_path(member.mb_id),
        "mb_img_url": MemberImageService.get_image_path(member.mb_id),
        "is_profile_open": check_profile_open(open_date=member.mb_open_date,
                                              config=request.state.config),
        "profile_open_date": get_next_profile_openable_date(
            open_date=member.mb_open_date,
            config=config
        ),
    }

    context = {
        "config": request.state.config,
        "request": request,
        "member": member,
        "form": form_context,
    }
    return templates.TemplateResponse("/member/register_form.html", context)


@router.post("/member_profile", name='member_profile_save',
             dependencies=[Depends(validate_token), Depends(validate_captcha)])
async def member_profile_save(
    request: Request,
    member_service: Annotated[MemberService, Depends()],
    file_service: Annotated[MemberImageService, Depends()],
    login_member: Annotated[Member, Depends(get_login_member)],
    member_form: Annotated[MemberForm, Depends(validate_update_member)],
    del_mb_img: int = Form(None),
    del_mb_icon: int = Form(None),
    mb_img: UploadFile = File(None),
    mb_icon: UploadFile = File(None),
):
    """
    회원정보 수정 처리
    """
    if not request.session.get("ss_profile_change", False):
        raise AlertException(
            "잘못된 접근입니다.", 403, url=request.url_for("member_password").path)

    member = member_service.read_member(login_member.mb_id)
    member_service.update_member(member, member_form.__dict__)

    # 이미지 검사 & 이미지 수정(삭제 포함)
    file_service.update_image_file(member.mb_id, 'image', mb_img, del_mb_img)
    file_service.update_image_file(member.mb_id, 'icon', mb_icon, del_mb_icon)

    if "ss_profile_change" in request.session:
        del request.session["ss_profile_change"]

    raise AlertException("회원정보가 수정되었습니다.", 302, "/")


def get_is_phone_certify(member: Member, config: Config) -> bool:
    """휴대폰 본인인증 사용여부 확인"""
    return (config.cf_cert_use
            and config.cf_cert_req
            and (config.cf_cert_hp or config.cf_cert_simple)
            and member.mb_certify != "ipin")
