from fastapi import APIRouter, Depends, Request, Form

from core.template import AdminTemplates
from lib.common import *
from lib.dependencies import validate_token

router = APIRouter()
templates = AdminTemplates()
templates.env.globals["domain_mail_host"] = domain_mail_host

SENDMAIL_MENU_KEY = "100300"


@router.get("/sendmail_test")
async def visit_search(request: Request):
    """
    메일 테스트
    """
    request.session["menu_key"] = SENDMAIL_MENU_KEY

    context = {
        "request": request,
        "config": request.state.config,
        "member": request.state.login_member,
    }
    return templates.TemplateResponse("sendmail_test.html", context)


@router.post("/sendmail_test_result", dependencies=[Depends(validate_token)])
async def sendmail_test_result(
    request: Request,
    to_email: str = Form(..., alias="email"),
):
    """
    메일 테스트 실행
    """
    # ','를 기준으로 문자열을 분리하여 리스트로 변환하거나, 하나의 요소만 있는 리스트를 생성
    subject = "[메일검사] 제목"
    body = f'<span style="font-size:9pt;">[메일검사] 내용\
        <p>이 내용이 제대로 보인다면 보내는 메일 서버에는 이상이 없는것입니다.<p>\
        {datetime.now()}<p>이 메일 주소로는 회신되지 않습니다.</span>'

    mailer(to_email, subject, body)

    real_emails = to_email.split(',') if ',' in to_email else [to_email]

    context = {
        "request": request,
        "config": request.state.config,
        "member": request.state.login_member,
        "real_emails": real_emails,
    }
    return templates.TemplateResponse("sendmail_test_result.html", context)
