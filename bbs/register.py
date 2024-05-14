"""회원가입 Template Router"""
from datetime import datetime
from typing_extensions import Annotated

from fastapi import (
    APIRouter, BackgroundTasks, Depends, File, Form, Path, Query, Request,
    UploadFile
)
from fastapi.responses import RedirectResponse

from core.database import db_session
from core.exception import AlertException
from core.formclass import RegisterMemberForm
from core.models import Member
from core.template import UserTemplates
from lib.captcha import captcha_widget
from lib.common import session_member_key
from lib.dependency.dependencies import (
    validate_captcha, validate_token, no_cache_response
)
from lib.dependency.member import validate_policy_agree, validate_register_data
from lib.mail import send_register_mail
from service.member_service import MemberImageService, MemberService
from lib.template_filters import default_if_none
from service.point_service import PointService

router = APIRouter()
templates = UserTemplates()
templates.env.filters["default_if_none"] = default_if_none
templates.env.globals["captcha_widget"] = captcha_widget


@router.get("/register",
            dependencies=[Depends(no_cache_response)])
async def get_register(request: Request):
    """
    회원가입 약관 동의 페이지
    """
    request.session["ss_agree"] = ""
    request.session["ss_agree2"] = ""
    return templates.TemplateResponse("/bbs/register.html", {"request": request})


@router.post("/register")
async def post_register(
    request: Request,
    agree: str = Form(None),
    agree2: str = Form(None)
):
    """
    회원가입 약관 동의 처리
    """
    request.session["ss_agree"] = agree
    request.session["ss_agree2"] = agree2
    return RedirectResponse(url="/bbs/register_form", status_code=302)


@router.get("/register_form",
            dependencies=[Depends(validate_policy_agree)],
            name='register_form')
async def get_register_form(request: Request):
    """
    회원가입 폼 페이지
    """
    config = request.state.config
    member = Member(mb_level=config.cf_register_level)

    context = {
        "request": request,
        "config": config,
        "member": member,
        "form": {
            "is_profile_open": True,
        },
        "is_register": True,
    }
    return templates.TemplateResponse("/member/register_form.html", context)


@router.post("/register_form",
             dependencies=[Depends(validate_token),
                           Depends(validate_captcha),
                           Depends(validate_policy_agree)],
             name='register_form_save')
async def post_register_form(
    request: Request,
    member_service: Annotated[MemberService, Depends()],
    file_service: Annotated[MemberImageService, Depends()],
    point_service: Annotated[PointService, Depends()],
    form_data: Annotated[RegisterMemberForm, Depends(validate_register_data)],
    background_tasks: BackgroundTasks,
    mb_id: str = Form(None),
    mb_img: UploadFile = File(None),
    mb_icon: UploadFile = File(None),
):
    """
    회원가입 처리
    """
    config = request.state.config
    member = member_service.create_member(form_data)

    # 회원가입 포인트 지급
    register_point = getattr(config, "cf_register_point", 0)
    point_service.save_point(member.mb_id, register_point, "회원가입 축하",
                            "@member", member.mb_id, "회원가입")

    # 추천인 포인트 지급
    mb_recommend = form_data.mb_recommend
    if config.cf_use_recommend and mb_recommend:
        recommend_point = getattr(config, "cf_recommend_point", 0)
        point_service.save_point(mb_recommend, recommend_point, f"{member.mb_id}의 추천인",
                                 "@member", mb_recommend, f"{member.mb_id} 추천")

    # 회원가입메일 발송 처리(백그라운드)
    background_tasks.add_task(send_register_mail, request, member)

    # 이미지 검사 & 업로드
    file_service.update_image_file(mb_id, 'icon', mb_icon)
    file_service.update_image_file(mb_id, 'image', mb_img)

    # 회원가입 이후 세션 처리
    if not config.cf_use_email_certify:
        request.session["ss_mb_id"] = member.mb_id
        request.session["ss_mb_key"] = session_member_key(request, member)
    request.session["ss_mb_reg"] = member.mb_id

    return RedirectResponse(url="/bbs/register_result", status_code=302)


@router.get("/register_result")
async def register_result(
    request: Request,
    member_service: Annotated[MemberService, Depends()]
):
    """
    회원가입 결과 페이지
    """
    mb_id = request.session.pop("ss_mb_reg", "")
    member = member_service.fetch_member_by_id(mb_id)
    if not member:
        return RedirectResponse(url="/bbs/register", status_code=302)

    context = {
        "request": request,
        "member": member,
    }
    return templates.TemplateResponse("/bbs/register_result.html", context)


@router.get("/email_certify/{mb_id}")
async def email_certify(
    db: db_session,
    member_service: Annotated[MemberService, Depends()],
    mb_id: Annotated[str, Path(...)],
    certify: Annotated[str, Query(...)]
):
    """회원가입 메일인증 처리"""
    member = member_service.read_email_non_certify_member(mb_id, certify)
    member.mb_email_certify = datetime.now()
    member.mb_email_certify2 = ""
    db.commit()

    raise AlertException(f"메일인증 처리를 완료 하였습니다.\
                         \\n\\n지금부터 {member.mb_id} 아이디로 로그인 가능합니다", 200, "/")
