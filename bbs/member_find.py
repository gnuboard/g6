"""회원정보 찾기 Template Router"""
from typing_extensions import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Form, Path, Request

from core.database import db_session
from core.exception import AlertException
from core.template import UserTemplates
from lib.captcha import captcha_widget
from lib.dependency.dependencies import validate_captcha, validate_token
from lib.dependency.member import redirect_if_logged_in, validate_password_reset
from lib.mail import send_password_reset_mail
from service.certificate_service import CertificateService
from service.member_service import MemberService

router = APIRouter(dependencies=[Depends(redirect_if_logged_in)])
templates = UserTemplates()
templates.env.globals["captcha_widget"] = captcha_widget


@router.get("/id_lost")
async def find_member_id_form(
    request: Request,
    cert_service: Annotated[CertificateService, Depends()]
):
    """
    회원 ID 찾기 페이지
    """
    cert_context = {
        "cert_hp" : cert_service.cert_hp,
        "cert_simple" : cert_service.cert_simple,
        "cert_ipin" : cert_service.cert_ipin,
        "is_use_cert": cert_service.cert_use,
    }
    context = {
        "request": request,
        "certificate": cert_context,
        "is_view_cert": cert_service.cert_use and cert_service.cert_find
    }
    return templates.TemplateResponse("/member/id_find_form.html", context)


@router.post("/id_lost",
             dependencies=[Depends(validate_captcha),
                           Depends(validate_token)])
async def find_member_id(
    request: Request,
    member_service: Annotated[MemberService, Depends()],
    mb_name: str = Form(...),
    mb_email: str = Form(...)
):
    """
    회원 ID 찾기 처리 및 결과 페이지
    """
    member_id, register_date = member_service.find_id(mb_name, mb_email)

    context = {
        "request": request,
        "member_id": member_id,
        "register_date": register_date
    }
    return templates.TemplateResponse("/member/id_find_result.html", context)


@router.post("/id_lost/certificate",
             dependencies=[Depends(validate_token)])
async def find_member_id_certificate(
    request: Request,
    member_service: Annotated[MemberService, Depends()],
    dupinfo: str = Form(...)
):
    """
    회원 ID 찾기 처리 및 결과 페이지 (본인인증)
    """
    member_id, register_date = member_service.find_id_by_certify(dupinfo)

    context = {
        "request": request,
        "member_id": member_id,
        "register_date": register_date
    }
    return templates.TemplateResponse("/member/id_find_result.html", context)


@router.get("/password_lost")
async def find_member_password_form(
    request: Request,
    cert_service: Annotated[CertificateService, Depends()]
):
    """
    회원 비밀번호 찾기 페이지
    """
    cert_context = {
        "cert_hp" : cert_service.cert_hp,
        "cert_simple" : cert_service.cert_simple,
        "cert_ipin" : cert_service.cert_ipin,
        "is_use_cert": cert_service.cert_use,
    }
    context = {
        "request": request,
        "certificate": cert_context,
        "is_view_cert": cert_service.cert_use and cert_service.cert_find
    }
    return templates.TemplateResponse("/member/password_find_form.html", context)


@router.post("/password_lost",
             dependencies=[Depends(validate_captcha),
                           Depends(validate_token)])
async def find_member_password(
    request: Request,
    background_tasks: BackgroundTasks,
    member_service: Annotated[MemberService, Depends()],
    mb_id: str = Form(...),
    mb_email: str = Form(...),
):
    """
    회원정보를 찾은 후 비밀번호 재설정 링크 메일 발송
    """
    member = member_service.find_member_from_password_info(mb_id, mb_email)
    # 비밀번호 재설정 메일 발송 처리(백그라운드)
    background_tasks.add_task(send_password_reset_mail, request, member)

    context = {
        "request": request,
        "member": member
    }
    return templates.TemplateResponse("/member/password_find_result.html", context)


@router.post("/password_lost/certificate",
             dependencies=[Depends(validate_token)])
async def find_member_password_certificate(
    request: Request,
    db: db_session,
    member_service: Annotated[MemberService, Depends()],
    mb_id: str = Form(...),
    dupinfo: str = Form(...)
):
    """
    비밀번호 재설정 페이지 (본인인증)
    """
    member = member_service.fetch_member_by_dupinfo(dupinfo, mb_id=mb_id)
    if not member:
        raise AlertException("입력하신 아이디와 일치하는 회원정보가 없습니다.", 404)

    # 비밀번호 재설정 정보에 인증정보 저장
    member.mb_lost_certify = dupinfo
    db.commit()
    db.refresh(member)

    context = {
        "request": request,
        "member": member,
    }
    return templates.TemplateResponse("/member/password_reset_form.html", context)


@router.get("/password_reset/{mb_id}/{token}")
async def reset_password_form(
    request: Request,
    member_service: Annotated[MemberService, Depends()],
    mb_id: Annotated[str, Path()],
    token: Annotated[str, Path()],
):
    """
    비밀번호 재설정 페이지 (메일 링크 클릭시)
    """
    member = member_service.read_member_by_lost_certify(mb_id, token)
    context = {
        "request": request,
        "member": member
    }
    return templates.TemplateResponse("/member/password_reset_form.html", context)


@router.post("/password_reset/{mb_id}/{token}",
             dependencies=[Depends(validate_captcha),
                           Depends(validate_token)])
async def reset_password(
    member_service: Annotated[MemberService, Depends()],
    password_hash: Annotated[str, Depends(validate_password_reset)],
    mb_id: Annotated[str, Path()],
    token: Annotated[str, Path()],
):
    """
    비밀번호 재설정 처리
    """
    member_service.reset_password(mb_id, token, password_hash)

    raise AlertException("비밀번호가 변경되었습니다.", 303, "/bbs/login")
