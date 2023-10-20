import math
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, Query, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import asc, desc, and_, or_, func, extract
from sqlalchemy.orm import Session
from database import get_db, engine
import models 
from common import *
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import FastAPI, HTTPException
from concurrent.futures import ThreadPoolExecutor
import ssl
import smtplib


# load_dotenv()

# SMTP_SERVER = os.getenv("SMTP_SERVER")
# SMTP_PORT = os.getenv("SMTP_PORT")
# SMTP_USERNAME = os.getenv("SMTP_USERNAME")
# SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")


def send_email(recipient_email, subject, body):
    
    SMTP_SERVER="smtp.worksmobile.com"
    SMTP_PORT=465
    SMTP_USERNAME="admin@sir.kr"
    SMTP_PASSWORD="UiN7mTCYntcv"
    
    sender_email = SMTP_USERNAME

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = sender_email
    message["To"] = recipient_email

    # text = MIMEText(body, "plain")
    text = MIMEText(body, "html")
    message.attach(text)

    context = ssl.create_default_context()

    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as server:
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(sender_email, recipient_email, message.as_string())


router = APIRouter()
templates = Jinja2Templates(directory=ADMIN_TEMPLATES_DIR)
templates.env.globals['getattr'] = getattr
templates.env.globals['get_selected'] = get_selected
templates.env.globals['option_selected'] = option_selected
templates.env.globals['get_skin_select'] = get_skin_select
templates.env.globals['get_group_select'] = get_group_select
templates.env.globals['get_editor_select'] = get_editor_select
templates.env.globals['get_member_level_select'] = get_member_level_select
templates.env.globals['subject_sort_link'] = subject_sort_link
templates.env.globals['get_admin_menus'] = get_admin_menus
templates.env.globals["generate_one_time_token"] = generate_one_time_token
templates.env.globals["domain_mail_host"] = domain_mail_host


@router.get("/sendmail_test")
async def visit_search(request: Request, db: Session = Depends(get_db),
        ):
    '''
    메일 테스트
    '''
    request.session["menu_key"] = "100300"
    
    context = {
        "request": request,
        "config": request.state.config,
        "member": request.state.login_member,
    }
    return templates.TemplateResponse("sendmail_test.html", context)


@router.post("/sendmail_test_result")
async def sendmail_test_result(request: Request, db: Session = Depends(get_db),
        token: str = Form(..., alias="token"),
        to_email: str = Form(..., alias="email"),
        ):
    '''
    메일 테스트 실행
    '''
    if not validate_one_time_token(token, 'sendmail_test_result'):
        return templates.TemplateResponse("alert.html", {"request": request, "errors": ["토큰이 유효하지 않습니다. 새로고침후 다시 시도해 주세요."]})

    # ','를 기준으로 문자열을 분리하여 리스트로 변환하거나, 하나의 요소만 있는 리스트를 생성
    recipients = to_email.split(',') if ',' in to_email else [to_email]
    subject = "[메일검사] 제목"
    body = f'<span style="font-size:9pt;">[메일검사] 내용<p>이 내용이 제대로 보인다면 보내는 메일 서버에는 이상이 없는것입니다.<p>{datetime.now()}<p>이 메일 주소로는 회신되지 않습니다.</span>'

    if not recipients:
        raise HTTPException(status_code=400, detail="Recipient list is empty.")
    
    futures = {}
    with ThreadPoolExecutor() as executor:
        for recipient in recipients:
            # 각 이메일 발송 작업을 ThreadPoolExecutor로 실행
            futures[recipient] = executor.submit(send_email, recipient.strip(), subject, body)
        
    context = {
        "request": request,
        "config": request.state.config,
        "member": request.state.login_member,
        "real_emails": recipients,
    }
    return templates.TemplateResponse("sendmail_test_result.html", context)
