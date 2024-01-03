import re

from fastapi import APIRouter, Depends, Request, Form, Path

from core.database import db_session
from core.exception import AlertException
from core.template import UserTemplates
from lib.common import *
from lib.dependencies import validate_token

router = APIRouter()
templates = UserTemplates()
templates.env.globals["captcha_widget"] = captcha_widget


@router.get("/formmail/{mb_id}")
async def formmail(
    request: Request,
    db: db_session,
    mb_id: str = Path(None),
    name: str = None,
    email: str = None
):
    """
    폼메일 폼 작성
    """
    config = request.state.config
    login_member = request.state.login_member

    if not config.cf_email_use:
        raise AlertException(status_code=400, detail='환경설정에서 "메일발송 사용"에 체크하셔야 메일을 발송할 수 있습니다.\n\n관리자에게 문의하시기 바랍니다.')
    
    if config.cf_formmail_is_member and not login_member:
        raise AlertException(status_code=400, detail="회원만 이용 가능합니다.")

    if login_member and not login_member.mb_open and not request.state.is_super_admin and login_member.mb_id != mb_id:
        raise AlertException(status_code=400, detail='자신의 정보를 공개하지 않으면 다른분에게 메일을 보낼 수 없습니다.\n\n정보공개 설정은 회원정보수정에서 하실 수 있습니다.')

    if mb_id:
        exists_member = db.scalar(
            select(Member).where(Member.mb_id == mb_id)
        )
        if not exists_member:
            raise AlertException(status_code=400, detail="존재하지 않는 회원입니다.")

        if not exists_member.mb_open and not request.state.is_super_admin:
            raise AlertException(status_code=400, detail="정보공개를 하지 않았습니다.")

    sendmail_count = request.session.get('ss_sendmail_count', 0) + 1
    if sendmail_count > 3:
        raise AlertException(status_code=400, detail="한번 접속후 일정수의 메일만 발송할 수 있습니다.\n\n계속해서 메일을 보내시려면 다시 로그인 또는 접속하여 주십시오.")
    
    enc = StringEncrypt()
    decrypted_email = enc.decrypt(email)

    def get_email_address(email):
        matches = re.findall(r"[0-9a-z._-]+@[a-z0-9._-]{4,}", email, re.I)
        return matches[0] if matches else None

    email = get_email_address(decrypted_email)
    if not email:
        raise AlertException(status_code=400, detail="이메일이 올바르지 않습니다.")

    email = enc.encrypt(email)

    if not name:
        name = email

    context = {
        "request": request,
        "member": login_member,
        "to_name": name,
        "to_email": email,
    }

    return templates.TemplateResponse(f"bbs/formmail.html", context)


@router.post("/formmail_send", dependencies=[Depends(validate_token)])
async def formmail_send(
    request: Request,
    db: db_session,
    email: str = Form(..., alias="to"),
    name: str = Form(None, alias="fnick"),
    fmail: str = Form(..., alias="fmail"),
    subject: str = Form(..., alias="subject"),
    content: str = Form(..., alias="content"),
):
    """
    폼메일 발송
    """
    enc = StringEncrypt()
    decrypted_to_email = enc.decrypt(email)
    # to_emails = decrypted_to_email.split(',') if ',' in decrypted_to_email else [decrypted_to_email]
    # print(to_emails[0], subject, body)
    # mailer(to_emails, subject, body)
    mailer(decrypted_to_email, subject, content)
