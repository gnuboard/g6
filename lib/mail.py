"""
메일 발송 라이브러리
TODO: common.py에 있는 메일 관련 함수들을 이곳으로 이동

- background에서 Session 공유 문제로 인해 DBConnect().sessionLocal()을 사용함
"""
from datetime import datetime
from fastapi import Request
from fastapi.templating import Jinja2Templates

from core.database import DBConnect
from core.models import Config, Member, PollEtc
from core.template import TemplateService
from lib.common import cut_name, get_admin_email, get_admin_email_name, mailer


def send_password_reset_mail(request: Request, member: Member) -> None:
    """background task > 비밀번호 재설정 링크 메일 발송

    Args:
        request (Request): Request 객체
        member (Member): 신규가입한 회원 객체
    """
    with DBConnect().sessionLocal() as db:
        request.state.config = config = db.query(Config).first()

    try:
        templates = Jinja2Templates(
            directory=TemplateService.get_templates_dir())

        subject = f"[{config.cf_title}] 요청하신 비밀번호 찾기 메일입니다."
        body = templates.TemplateResponse(
            "bbs/mail_form/find_pasword_mail.html",
            {
                "request": request,
                "member": member,
                "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        ).body.decode("utf-8")
        mailer(get_admin_email(request), member.mb_email,
               subject, body, get_admin_email_name(request))
    except Exception as e:
        print(e)


def send_register_mail(request: Request, member: Member) -> None:
    """background task > 회원가입 메일 발송 처리

    Args:
        request (Request): Request 객체
        member (Member): 신규가입한 회원 객체
    """
    with DBConnect().sessionLocal() as db:
        request.state.config = config = db.query(Config).first()

    try:
        templates = Jinja2Templates(
            directory=TemplateService.get_templates_dir())
        from_email = get_admin_email(request)
        from_name = get_admin_email_name(request)
        context = {"request": request, "member": member}

        # 회원에게 인증메일 발송
        if config.cf_use_email_certify:
            subject = f"[{config.cf_title}] 회원가입 인증메일 발송"
            cntx = context + \
                {"certify_href": f"{request.base_url.__str__()}bbs/email_certify/{member.mb_id}?certify={member.mb_email_certify2}"}
            body = templates.TemplateResponse(
                "bbs/mail_form/register_certify_mail.html",
                cntx
            ).body.decode("utf-8")
            mailer(from_email, member.mb_email, subject, body, from_name)
        # 회원에게 회원가입 메일 발송
        elif config.cf_email_mb_member:
            subject = f"[{config.cf_title}] 회원가입을 축하드립니다."
            body = templates.TemplateResponse(
                "bbs/mail_form/register_send_member_mail.html",
                context
            ).body.decode("utf-8")
            mailer(from_email, member.mb_email, subject, body, from_name)

        # 최고관리자에게 회원가입 메일 발송
        if config.cf_email_mb_super_admin:
            subject = f"[{config.cf_title}] {member.mb_nick} 님께서 회원으로 가입하셨습니다."
            body = templates.TemplateResponse(
                "bbs/mail_form/register_send_admin_mail.html",
                context
            ).body.decode("utf-8")
            mailer(from_email, config.cf_admin_email, subject, body, from_name)
    except Exception as e:
        print(e)


def send_poll_etc_mail(request: Request, poll_etc: PollEtc) -> None:
    """
    최고관리자에게 기타의견 메일 발송 처리
    - 기본환경설정 > 기타의견 메일발송 설정이 되어있을 경우에만 발송

    Args:
        request (Request): Request 객체
        poll_etc (PollEtc): 기타의견 객체
    """
    with DBConnect().sessionLocal() as db:
        request.state.config = config = db.query(Config).first()

    try:
        if config.cf_email_po_super_admin and config.cf_admin_email:
            templates = Jinja2Templates(
                directory=TemplateService.get_templates_dir())
            email = get_admin_email(request)
            from_name = get_admin_email_name(request)
            subject = f"[{config.cf_title}] 설문조사 - 기타의견 메일"
            body = templates.TemplateResponse(
                "bbs/mail_form/poll_etc_update_mail.html",
                {
                    "request": request,
                    "subject": subject,
                    "mb_name": cut_name(request, poll_etc.pc_name),
                    "mb_id": poll_etc.mb_id if poll_etc.mb_id else "비회원",
                    "content": poll_etc.pc_idea,
                }
            ).body.decode("utf-8")
            mailer(email, email, subject, body, from_name)
    except Exception as e:
        print(e)
