"""
메일 발송 라이브러리
- background에서 Session 공유 문제로 인해 DBConnect().sessionLocal()을 사용함
"""
import smtplib
from datetime import datetime
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

from fastapi import Request
from fastapi.templating import Jinja2Templates

from core.database import DBConnect
from core.models import Config, Member, PollEtc, QaConfig, QaContent
from core.settings import settings
from core.template import TemplateService
from lib.common import cut_name, get_admin_email, get_admin_email_name

_SMTP_SERVER = settings.SMTP_SERVER
_SMTP_PORT = settings.SMTP_PORT
_SMTP_USERNAME = settings.SMTP_USERNAME
_SMTP_PASSWORD = settings.SMTP_PASSWORD


def mailer(from_email: str, to_email: str, subject: str, body: str,
           from_name: str = None, to_name: str = None) -> None:
    """메일 발송 함수

    Args:
        from_email (str): 보내는 사람 이메일
        email (str): 받는 사람 이메일 (,로 구분하여 여러명에게 보낼 수 있음)
        subject (str): 제목
        body (str): 내용
        from_name (str, optional): 보내는 사람 이름. Defaults to None.
        to_name (str, optional): 받는 사람 이름. Defaults to None.

    Raises:
        SMTPAuthenticationError: SMTP 인증정보가 잘못되었을 때
        SMTPServerDisconnected: SMTP 서버에 연결하지 못했거나 연결이 끊어졌을 때
        SMTPException: 메일을 보내는 중에 오류가 발생했을 때
        Exception: 기타 오류
    """
    try:
        # Daum, Naver 메일은 SMTP_SSL을 사용합니다.
        if _SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(_SMTP_SERVER, _SMTP_PORT, timeout=10)
        else: # port: 587
            server = smtplib.SMTP(_SMTP_SERVER, _SMTP_PORT, timeout=10)
            server.starttls()

        if _SMTP_USERNAME and _SMTP_PASSWORD:
            server.login(_SMTP_USERNAME, _SMTP_PASSWORD)

        msg = MIMEMultipart()
        msg['From'] = formataddr((str(Header(from_name, 'utf-8')), from_email))
        msg['To'] = formataddr((str(Header(to_name, 'utf-8')), to_email))
        msg['Subject'] = subject
        # Assuming body is HTML, if not change 'html' to 'plain'
        msg.attach(MIMEText(body, 'html'))

        server.sendmail(from_email, to_email, msg.as_string())

    except smtplib.SMTPAuthenticationError as e:
        print(f"SMTP 인증정보가 잘못되었습니다. {e}")
    except smtplib.SMTPServerDisconnected as e:
        print(f"SMTP 서버에 연결하지 못했거나 연결이 끊어졌습니다. {e}")
    except smtplib.SMTPException as e:
        print(f"메일을 보내는 중에 오류가 발생했습니다. {e}")
    except Exception as e:
        print(e)
    finally:
        try:
            server.quit()
        except Exception as e:
            pass


async def send_password_reset_mail(request: Request, member: Member) -> None:
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


async def send_register_mail(request: Request, member: Member) -> None:
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


async def send_poll_etc_mail(request: Request, poll_etc: PollEtc) -> None:
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


async def send_qa_mail(request: Request, qa: QaContent) -> None:
    """
    Q&A 등록 시 메일 발송 처리
    - Q&A 등록 시, 설정에 등록된 관리자 이메일 주소로 메일 발송
    - 답변글 등록 시, 메일/메일 수신여부 설정에 따라 사용자에게 메일 발송
    
    Args:
        request (Request): Request 객체
        poll_etc (PollEtc): 기타의견 객체

    TODO : 메일 발송 템플릿 적용이 필요하다.
    """
    with DBConnect().sessionLocal() as db:
        request.state.config = config = db.query(Config).first()
        qa_config = db.query(QaConfig).first()

    from_email = get_admin_email(request)
    from_name = get_admin_email_name(request)
    subject = f"[{config.cf_title}] {qa_config.qa_title} 질문 알림 메일"
    content = qa.qa_subject + "<br><br>" + qa.qa_content

    if qa.qa_parent:
        question = db.get(QaContent, qa.qa_parent)
        if question.qa_email_recv and question.qa_email:
            subject = f"{subject} 에 대한 답변이 등록되었습니다."
            mailer(from_email, question.qa_email, subject, content, from_name)
    else:
        if qa_config.qa_admin_email:
            mailer(from_email, qa_config.qa_admin_email, subject, content, from_name)
