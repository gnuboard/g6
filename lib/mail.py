"""
메일 발송 라이브러리
TODO: common.py에 있는 메일 관련 함수들을 이곳으로 이동
"""
from fastapi import Request
from fastapi.templating import Jinja2Templates

from core.database import DBConnect
from core.models import Config, Member
from core.template import TemplateService
from lib.common import get_admin_email, get_admin_email_name, mailer


def send_register_mail(request: Request, member: Member) -> None:
    """background task > 회원가입 메일 발송 처리

    Args:
        request (Request): Request 객체
        member (Member): 신규가입한 회원 객체
    """
    # background에서 Session 공유 문제로 인해 DBConnect().sessionLocal() 사용
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
