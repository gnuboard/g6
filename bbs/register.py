from typing_extensions import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Form, File, Path, Query, UploadFile
from fastapi.responses import RedirectResponse, Response

from core.database import db_session
from core.exception import AlertException
from core.formclass import MemberForm
from core.models import Member
from core.template import UserTemplates
from lib.common import *
from lib.mail import send_register_mail
from lib.member_lib import (
    MemberService, validate_and_update_member_image
)
from lib.dependencies import validate_regist_agree, validate_token, validate_captcha
from lib.dependency.member import validate_register_member
from lib.point import insert_point
from lib.template_filters import default_if_none

router = APIRouter()
templates = UserTemplates()
templates.env.filters["default_if_none"] = default_if_none
templates.env.globals["captcha_widget"] = captcha_widget
templates.env.globals["check_profile_open"] = check_profile_open


@router.get("/register")
async def get_register(
    request: Request,
    response: Response
):
    """
    회원가입 약관 동의 페이지
    """
    # 캐시 제어 헤더 설정 (캐시된 페이지를 보여주지 않고 새로운 페이지를 보여줌)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    request.session["ss_agree"] = ""
    request.session["ss_agree2"] = ""

    context = {
        "request": request
    }
    return templates.TemplateResponse("/bbs/register.html", context)


@router.post("/register")
async def post_register(
    request: Request,
    agree: str = Form(None),
    agree2: str = Form(None)
):
    """
    회원가입 약관 동의 처리
    """
    if not agree:
        raise AlertException(status_code=400, detail="회원가입약관에 동의해 주세요.")
    if not agree2:
        raise AlertException(status_code=400, detail="개인정보 수집 및 이용에 동의해 주세요.")

    request.session["ss_agree"] = agree
    request.session["ss_agree2"] = agree2
    return RedirectResponse(url="/bbs/register_form", status_code=302)


@router.get("/register_form",
            dependencies=[Depends(validate_regist_agree)],
            name='register_form')
async def get_register_form(request: Request):
    """
    회원가입 폼 페이지
    """
    config = request.state.config
    member = Member()
    member.mb_level = config.cf_register_level

    form_context = {
        # https 의 경우 http 경로가 넘어와서 제대로 전송이 되지 않음
        # "action_url": f"{request.base_url.__str__()}bbs{router.url_path_for('register_form_save')}",
        "is_profile_open": check_profile_open(open_date=None, config=config),
        "next_profile_open_date": get_next_profile_openable_date(open_date=None, config=config),
    }
    context = {
        "is_register": True,
        "request": request,
        "member": member,
        "form": form_context,
        "config": config,
    }
    return templates.TemplateResponse("/member/register_form.html", context)


@router.post("/register_form",
             dependencies=[Depends(validate_token),
                           Depends(validate_captcha),
                           Depends(validate_regist_agree)],
             name='register_form_save')
async def post_register_form(
    request: Request,
    member_service: Annotated[MemberService, Depends()],
    member_form: Annotated[MemberForm, Depends(validate_register_member)],
    background_tasks: BackgroundTasks,
    mb_id: str = Form(None),
    mb_img: UploadFile = File(None),
    mb_icon: UploadFile = File(None),
):
    """
    회원가입 처리
    """
    config = request.state.config
    member = member_service.create_member(member_form)

    # 회원가입 포인트 지급
    insert_point(request, member.mb_id, config.cf_register_point,
                "회원가입 축하", "@member", member.mb_id, "회원가입")

    # 추천인 포인트 지급
    mb_recommend = member_form.mb_recommend
    if config.cf_use_recommend and mb_recommend:
        insert_point(request, mb_recommend, config.cf_recommend_point,
                    f"{member.mb_id}의 추천인", "@member", mb_recommend, f"{member.mb_id} 추천")

    # 회원가입메일 발송 처리(백그라운드)
    background_tasks.add_task(send_register_mail, request, member)

    # 이미지 검사 & 업로드
    validate_and_update_member_image(request, mb_img, mb_icon, mb_id, None, None)

    # 회원가입 이후 세션 처리
    if not config.cf_use_email_certify:
        request.session["ss_mb_id"] = member.mb_id
        request.session["ss_mb_key"] = session_member_key(request, member)
    request.session["ss_mb_reg"] = member.mb_id

    return RedirectResponse(url="/bbs/register_result", status_code=302)


@router.get("/register_result")
async def register_result(
    request: Request,
    db: db_session
):
    """
    회원가입 결과 페이지
    """
    register_mb_id = request.session.get("ss_mb_reg", "")
    if "ss_mb_reg" in request.session:
        request.session.pop("ss_mb_reg")

    # 회원가입이 아닐때.
    if not register_mb_id:
        return RedirectResponse(url="/bbs/register", status_code=302)

    member = db.scalar(select(Member).where(Member.mb_id == register_mb_id))
    if not member:
        # 가입실패
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
    member = member_service.get_email_non_certify_member(mb_id, certify)
    member.mb_email_certify = datetime.now()
    member.mb_email_certify2 = ""
    db.commit()

    raise AlertException(f"메일인증 처리를 완료 하였습니다.\
                         \\n\\n지금부터 {member.mb_id} 아이디로 로그인 가능합니다", 200, "/")