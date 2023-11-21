import math
from fastapi import APIRouter, Depends, Query, Request, Form, HTTPException, Path
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import asc, desc, and_, or_, func, extract
from sqlalchemy.orm import Session
from common.database import get_db, engine
import common.models as models 
from lib.common import *
from fastapi import FastAPI, HTTPException
import ssl
import os
import smtplib
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from sse_starlette.sse import EventSourceResponse
import time
import asyncio

from lib.plugin.service import get_admin_plugin_menus, get_all_plugin_module_names

router = APIRouter()
templates = Jinja2Templates(directory=[ADMIN_TEMPLATES_DIR, EDITOR_PATH])
templates.env.globals['getattr'] = getattr
templates.env.globals['get_selected'] = get_selected
templates.env.globals['option_selected'] = option_selected
templates.env.globals['get_skin_select'] = get_skin_select
templates.env.globals['get_group_select'] = get_group_select
templates.env.globals['get_editor_select'] = get_editor_select
templates.env.globals['get_member_level_select'] = get_member_level_select
templates.env.globals['subject_sort_link'] = subject_sort_link
templates.env.globals['get_admin_menus'] = get_admin_menus
templates.env.globals["get_admin_plugin_menus"] = get_admin_plugin_menus
templates.env.globals["get_all_plugin_module_names"] = get_all_plugin_module_names
templates.env.globals["domain_mail_host"] = domain_mail_host
templates.env.globals["editor_path"] = editor_path

MAIL_MENU_KEY = "200300"

@router.get("/mail_list")
async def mail_list(request: Request, db: Session = Depends(get_db), search_params: dict = Depends(common_search_query_params)):
    '''
    회원메일발송 목록
    '''
    request.session["menu_key"] = MAIL_MENU_KEY
    
    config = request.state.config
    # page = int(request.state.page or 1)

    # total_count = db.query(models.Mail.ma_id).count()
    # mails = db.query(models.Mail).order_by(desc(models.Mail.ma_id)).all()
    # for i, mail in enumerate(mails):
    #     mail.num = total_count - (page - 1) * int(config.cf_page_rows) - i
    result = select_query(
                request, 
                models.Mail, 
                search_params,
            )
    for i, mail in enumerate(result["rows"]):
        mail.num = result["total_count"] - (search_params["current_page"] - 1) * int(config.cf_page_rows) - i
        
    context = {
        "request": request,
        "config": config,
        "member": request.state.login_member,
        "total_count": result["total_count"],
        "mails": result["rows"],
        "paging": get_paging(request, search_params["current_page"], result["total_count"]),
    }
    return templates.TemplateResponse("mail_list.html", context)


# @router.get("/mail_form")                
# async def mail_form(request: Request, db: Session = Depends(get_db),):
#     '''
#     회원메일발송 등록
#     '''
#     request.session["menu_key"] = "200300"
    
#     context = {
#         "request": request,
#         "config": request.state.config,
#         "member": request.state.login_member,
#         "mail": None,
#     }
#     return templates.TemplateResponse("mail_form.html", context)


@router.get("/mail_form") # 등록
@router.get("/mail_form/{ma_id}") # 수정
async def mail_form(request: Request, db: Session = Depends(get_db),
                    ma_id: int = None):
    '''
    회원메일발송 등록 및 수정
    ma_id 가 없으면 등록, 있으면 수정
    '''
    request.session["menu_key"] = MAIL_MENU_KEY
    
    mail = db.query(models.Mail).filter(models.Mail.ma_id == ma_id).first()
    # if not mail:
    #     raise AlertException("메일 정보가 없습니다.")
    
    context = {
        "request": request,
        "config": request.state.config,
        "member": request.state.login_member,
        "mail": mail,
    }
    return templates.TemplateResponse("mail_form.html", context)


@router.post("/mail_update")
async def mail_form_update(request: Request, db: Session = Depends(get_db),
        token: str = Form(..., alias="token"),
        ma_id: int = Form(None, alias="ma_id"),
        ma_subject: str = Form(..., alias="ma_subject"),
        ma_content: str = Form(..., alias="ma_content"),
        ):
    '''
    회원메일발송 등록/수정
    '''
    if not check_token(request, token):
        raise AlertException("토큰이 유효하지 않습니다.")
    
    # 등록
    if not ma_id:
        mail = models.Mail()
        mail.ma_subject = ma_subject
        mail.ma_content = ma_content
        mail.ma_time = datetime.now()
        mail.ma_ip = request.client.host
        db.add(mail)
        db.commit()
        ma_id = mail.ma_id        
    else: # 수정
        mail = db.query(models.Mail).filter(models.Mail.ma_id == ma_id).first()
        if not mail:
            raise AlertException("메일 정보가 없습니다.")
        
        mail.ma_subject = ma_subject
        mail.ma_content = ma_content
        db.commit()
    
    return RedirectResponse(f"/admin/mail_form/{ma_id}", status_code=303)


@router.post("/mail_delete")
async def mail_delete(request: Request, db: Session = Depends(get_db),
        token: str = Form(..., alias="token"),
        checks: List[int] = Form(..., alias="chk[]"),
        ma_id: List[int] = Form(..., alias="ma_id[]"),
        ):
    '''
    회원메일발송 삭제
    '''
    if not check_token(request, token):
        raise AlertException("토큰이 유효하지 않습니다.")
    
    for i in checks:
        exists_mail = db.query(models.Mail).filter(models.Mail.ma_id == ma_id[i]).first()
        if exists_mail:
            db.delete(exists_mail)
            db.commit()
            
    return RedirectResponse("/admin/mail_list", status_code=303)


@router.get("/mail_test/{ma_id}")
async def mail_test(request: Request, db: Session = Depends(get_db),
        ma_id: int = Path(...),
        ):
    '''
    회원메일발송 테스트
    '''
    # if not check_token(request, token):
    #     raise AlertException("토큰이 유효하지 않습니다.")
    
    config = request.state.config
    if not config.cf_email_use:
        raise AlertException("환경설정에서 '메일발송 사용'에 체크하셔야 메일을 발송할 수 있습니다.")
    
    error = auth_check_menu(request, request.session.get("menu_key"), "w")
    if error:
        raise AlertException(error)    
    
    exists_mail = db.query(models.Mail).filter(models.Mail.ma_id == ma_id).first()
    if not exists_mail:
        raise AlertException("메일 정보가 없습니다.")
    
    login_member = request.state.login_member
    name = login_member.mb_name
    nick = login_member.mb_nick
    mb_id = login_member.mb_id
    email = login_member.mb_email
    ma_id = exists_mail.ma_id
    
    subject = exists_mail.ma_subject
    content = exists_mail.ma_content
    # $content = preg_replace("/{이름}/", $name, (string)$content);
    # $content = preg_replace("/{닉네임}/", $nick, (string)$content);
    # $content = preg_replace("/{회원아이디}/", $mb_id, (string)$content);
    # $content = preg_replace("/{이메일}/", $email, (string)$content);
    # 치환
    content = content.replace("{이름}", name)
    content = content.replace("{닉네임}", nick)
    content = content.replace("{회원아이디}", mb_id)
    content = content.replace("{이메일}", email)
    
    #$mb_md5 = md5($member['mb_id'] . $member['mb_email'] . $member['mb_datetime']);
    mb_md5 = hashlib.md5(f"{mb_id}{email}{login_member.mb_datetime}".encode()).hexdigest()
    #$content = $content . '<p>더 이상 정보 수신을 원치 않으시면 [<a href="' . G5_BBS_URL . '/email_stop.php?mb_id=' . $mb_id . '&amp;mb_md5=' . $mb_md5 . '" target="_blank">수신거부</a>] 해 주십시오.</p>';
    content = content + f'<p>더 이상 정보 수신을 원치 않으시면 [<a href="/bbs/email_stop/{mb_id}&mb_md5={mb_md5}" target="_blank">수신거부</a>] 해 주십시오.</p>' 
    
    # 메일 발송
    mailer(email, subject, content)
    
    # return RedirectResponse("/admin/mail_list", status_code=303)
    # alert($member['mb_nick'] . '(' . $member['mb_email'] . ')님께 테스트 메일을 발송하였습니다. 확인하여 주십시오.');
    raise AlertException(status_code=200, detail=f"{nick}({email})님께 테스트 메일을 발송하였습니다. 확인하여 주십시오.")


@router.get("/mail_select_form/{ma_id}")
async def mail_select_form(request: Request, db: Session = Depends(get_db),
        ma_id: int = Path(...),
        mb_id1: int = Query(None),
        mb_level_from: str = Query(None),
        mb_level_to: str = Query(None),
        mb_mailling: str = Query(None),
        mb_email: str = Query(None),        
        ):
    '''
    회원메일발송 선택
    '''
    request.session["menu_key"] = MAIL_MENU_KEY
    # if not check_token(request, token):
    #     raise AlertException("토큰이 유효하지 않습니다.")
    
    config = request.state.config
    if not config.cf_email_use:
        raise AlertException(status_code=403, detail="환경설정에서 '메일발송 사용'에 체크하셔야 메일을 발송할 수 있습니다.")
    
    error = auth_check_menu(request, request.session.get("menu_key"), "w")
    if error:
        raise AlertException(error)
    
    exists_mail = db.query(models.Mail).filter(models.Mail.ma_id == ma_id).first()
    if not exists_mail:
        raise AlertException("메일 정보가 없습니다.")
    
    cleaned_host = re.sub(r'^(www[^\.]*\.)', '', request.client.host)
    
    # $sql = " select gr_id, gr_subject from {$g5['group_table']} order by gr_subject ";
    # $result = sql_query($sql);
    # for ($i = 0; $row = sql_fetch_array($result); $i++) {
    groups = db.query(models.Group).order_by(models.Group.gr_subject).all()
    
    # if (!isset($mb_id1)) {
    #     $mb_id1 = 1;
    # }
    # if (!isset($mb_level_from)) {
    #     $mb_level_from = 1;
    # }
    # if (!isset($mb_level_to)) {
    #     $mb_level_to = 10;
    # }
    # if (!isset($mb_mailling)) {
    #     $mb_mailling = 1;
    # }
    if not mb_id1:
        mb_id1 = 1
    if not mb_level_from:
        mb_level_from = 1
    if not mb_level_to:
        mb_level_to = 10
    if not mb_mailling:
        mb_mailling = 1
    if not mb_email:
        mb_email = ""
    
    context = {
        "request": request,
        "config": config,
        "member": request.state.login_member,
        "mail": exists_mail,
        "cleaned_host": cleaned_host,
        "groups": groups,
        "mb_id1": mb_id1,
        "mb_level_from": mb_level_from,
        "mb_level_to": mb_level_to,
        "mb_mailling": mb_mailling,
        "mb_email": mb_email,
    }
    return templates.TemplateResponse("mail_select_form.html", context)


@router.post("/mail_select_list")
async def mail_select_list(request: Request, db: Session = Depends(get_db),
        # token: str = Form(..., alias="token"),
        ma_id: int = Form(..., alias="ma_id"),
        mb_id1: int = Form(None, alias="mb_id1"),
        mb_id1_from: str = Form(None, alias="mb_id1_from"),
        mb_id1_to: str = Form(None, alias="mb_id1_to"),
        mb_email: str = Form(None, alias="mb_email"),
        mb_mailling: str = Form(None, alias="mb_mailling"),
        mb_level_from: int = Form(None, alias="mb_level_from"),
        mb_level_to: int = Form(None, alias="mb_level_to"),
        gr_id: str = Form(None, alias="gr_id"),
        ):
    '''
    회원메일발송 선택
    '''
    query = db.query(models.Member)
    if mb_id1 != 1:
        query = query.filter(models.Member.mb_id.between(mb_id1_from, mb_id1_to))        
    if mb_email:
        query = query.filter(models.Member.mb_email.like(f"%{mb_email}%"))
    if mb_mailling:
        query = query.filter(models.Member.mb_mailling == mb_mailling)
        
    query = query.filter(models.Member.mb_level.between(mb_level_from, mb_level_to))
    
    if gr_id:
        group_member = []
        result = db.query(models.GroupMember.mb_id).filter(models.GroupMember.gr_id == gr_id).order_by(models.GroupMember.mb_id).all()
        
        for row in result:
            group_member.append(row.mb_id)
            
        if not group_member:
            raise AlertException("선택하신 게시판 그룹회원이 한명도 없습니다.")
        
        qroup_str = ",".join(group_member)
        query = query.filter(models.Member.mb_id.in_(group_member))
    
    # 탈퇴, 차단하지 않은 회원만 선택합니다.
    # 1년 1월 1일의 datetime 객체를 생성합니다.
    cutoff_date = datetime(1, 1, 1)
    # cutoff_date 이전의 mb_leave_date와 mb_intercept_date를 가진 멤버만 선택합니다.
    query = query.filter(
        (models.Member.mb_leave_date <= cutoff_date) | (models.Member.mb_leave_date.is_(None)),
        (models.Member.mb_intercept_date <= cutoff_date) | (models.Member.mb_intercept_date.is_(None))
    )
    members = query.all()
    
    # members 를 ma_last_option 필드에 저장함 (파이썬, PHP의 차이점으로 인해 POST로 넘기지 못하고 DB에 저장해야함)
    save_members = []
    for member in members:
        save_members.append(member.mb_name+"||"+member.mb_nick+"||"+member.mb_id+"||"+member.mb_email)
    save_members_str = "\n".join(save_members)
    
    db.query(models.Mail).filter(models.Mail.ma_id == ma_id).update({models.Mail.ma_last_option: save_members_str})
    db.commit()
        
    extend = {
        "request": request,
        "config": request.state.config,
        "login_member": request.state.login_member,
        "members": members,
        "ma_id": ma_id,
    }
    return templates.TemplateResponse("mail_select_list.html", extend)


@router.post("/mail_select_result", response_class=HTMLResponse)
async def mail_select_result(request: Request, db: Session = Depends(get_db),
        token: str = Form(..., alias="token"),
        ma_id: int = Form(..., alias="ma_id"),
        ):
    '''
    회원메일발송 결과보여주는 HTML 페이지
    '''
    error = auth_check_menu(request, request.session.get("menu_key"), "w")
    if error:
        raise AlertException(error)    
    
    if not check_token(request, token):
        raise AlertException("토큰이 유효하지 않습니다.")

    context = {
        "request": request,
        "ma_id": ma_id,
    }
    return templates.TemplateResponse("mail_select_result.html", context)


@router.get("/mail_select_send")
async def mail_select_send(request: Request, db: Session = Depends(get_db),
        ma_id: int = Query(...),
        ):
    '''
    회원메일발송 처리
    '''
    error = auth_check_menu(request, request.session.get("menu_key"), "w")
    if error:
        raise AlertException(error)    
    
    async def send_events(members: list, mail_subject: str, mail_content: str):
        count = 0
        sleepsec = 1  # 1초 간격으로 조정
        
        for member in members:
            mb_name, mb_nick, mb_id, mb_email = member.split("||")
            
            if not mb_email:
                continue
            
            # $mb_md5 = md5($mb_id . $to_email . $datetime);
            mb_md5 = hashlib.md5(f"{mb_id}{mb_email}{datetime.now()}".encode()).hexdigest()

            # $content = $ma['ma_content'];
            # $content = preg_replace("/{이름}/", $name, (string)$content);
            # $content = preg_replace("/{닉네임}/", $nick, (string)$content);
            # $content = preg_replace("/{회원아이디}/", $mb_id, (string)$content);
            # $content = preg_replace("/{이메일}/", $to_email, (string)$content);
            # $content = $content . "<hr size=0><p><span style='font-size:9pt; font-family:굴림'>▶ 더 이상 정보 수신을 원치 않으시면 [<a href='" . G5_BBS_URL . "/email_stop.php?mb_id={$mb_id}&amp;mb_md5={$mb_md5}' target='_blank'>수신거부</a>] 해 주십시오.</span></p>";
            subject = mail_subject
            content = mail_content
            content = content.replace("{이름}", mb_name)
            content = content.replace("{닉네임}", mb_nick)
            content = content.replace("{회원아이디}", mb_id)
            content = content.replace("{이메일}", mb_email)
            content = content + f"<hr size=0><p><span style='font-size:10pt; font-family:돋움'>▶ 더 이상 정보 수신을 원치 않으시면 [<a href='/bbs/email_stop/{mb_id}&mb_md5={mb_md5}' target='_blank'>수신거부</a>] 해 주십시오.</span></p>"           
            
            # 메일 발송
            mailer(mb_email, subject, content)
            count += 1
            
            # 10명마다 1초씩 쉬어줍니다.
            if count % 10 == 0:
                await asyncio.sleep(sleepsec)  # 비동기 sleep 사용
                
            # 발송 상태를 'yield'를 사용하여 전송합니다.
            # 전송시 필히 data: 로 시작하고 \n\n으로 끝나야 합니다.
            yield f"data: {count}. {mb_name}({mb_email})님께 메일을 보내고 있습니다.\n\n"
        
        # 멤버 리스트 메일발송 완료 후 함수 종료
        # 종료 메시지 전송
        yield "data: [끝]\n\n"
            
    exists_mail = db.query(models.Mail).filter(models.Mail.ma_id == ma_id).first()
    if not exists_mail.ma_subject or not exists_mail.ma_content:
        raise AlertException("메일 내용이 없습니다.")

    members = exists_mail.ma_last_option.split("\n")
        
    return EventSourceResponse(send_events(members, exists_mail.ma_subject, exists_mail.ma_content))


@router.get("/mail_preview/{ma_id}")
async def mail_preview(request: Request, db: Session = Depends(get_db),
        ma_id: int = Path(...),
        ):
    '''
    회원메일발송 미리보기
    '''
    request.session["menu_key"] = MAIL_MENU_KEY
    
    exists_mail = db.query(models.Mail).filter(models.Mail.ma_id == ma_id).first()
    if not exists_mail:
        raise AlertException("메일 정보가 없습니다.")
    
    login_member = request.state.login_member
    
    subject = exists_mail.ma_subject
    content = exists_mail.ma_content

    content = content.replace("{이름}", login_member.mb_name)
    content = content.replace("{닉네임}", login_member.mb_nick)
    content = content.replace("{회원아이디}", login_member.mb_id)
    content = content.replace("{이메일}", login_member.mb_email)
    
    content = content + f"<hr size=0><p><span style='font-size:10pt; font-family:돋움'>▶ 더 이상 정보 수신을 원치 않으시면 [<a href='/bbs/email_stop/{login_member.mb_id}&mb_md5=***' target='_blank'>수신거부</a>] 해 주십시오.</span></p>"

    context = {
        "request": request,
        "mail_subject": subject,
        "mail_content": content,
    }
    return templates.TemplateResponse("mail_preview.html", context)
