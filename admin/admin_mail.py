import asyncio

from fastapi import APIRouter, Depends, Query, Request, Form, Path
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import or_, select, update, delete, func, DateTime
from sse_starlette.sse import EventSourceResponse

from core.database import db_session
from core.exception import AlertException
from core.database import db_connect
from core.models import Group, Mail, Member
from core.template import AdminTemplates
from lib.common import *
from lib.dependencies import common_search_query_params, validate_token
from lib.template_functions import get_group_select, get_paging

router = APIRouter()
templates = AdminTemplates()
templates.env.globals["get_group_select"] = get_group_select

MAIL_MENU_KEY = "200300"


@router.get("/mail_list")
async def mail_list(
    request: Request,
    db: db_session,
    search_params: dict = Depends(common_search_query_params)
):
    """
    회원메일발송 목록
    """
    request.session["menu_key"] = MAIL_MENU_KEY

    config = request.state.config

    result = select_query(
        request,
        Mail,
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
# async def mail_form(request: Request, db: db_session,):
#     """
#     회원메일발송 등록
#     """
#     request.session["menu_key"] = "200300"

#     context = {
#         "request": request,
#         "config": request.state.config,
#         "member": request.state.login_member,
#         "mail": None,
#     }
#     return templates.TemplateResponse("mail_form.html", context)


@router.get("/mail_form")  # 등록
@router.get("/mail_form/{ma_id}")  # 수정
async def mail_form(
    request: Request,
    db: db_session,
    ma_id: int = None
):
    """
    회원메일발송 등록 및 수정
    - ma_id 가 없으면 등록, 있으면 수정
    """
    request.session["menu_key"] = MAIL_MENU_KEY

    mail = db.get(Mail, ma_id)
    # if not mail:
    #     raise AlertException("메일 정보가 없습니다.", 400)

    context = {
        "request": request,
        "config": request.state.config,
        "member": request.state.login_member,
        "mail": mail,
    }
    return templates.TemplateResponse("mail_form.html", context)


@router.post("/mail_update", dependencies=[Depends(validate_token)])
async def mail_form_update(
    request: Request,
    db: db_session,
    ma_id: int = Form(None),
    ma_subject: str = Form(...),
    ma_content: str = Form(...),
):
    """
    회원메일발송 등록/수정
    """
    # 등록
    if not ma_id:
        mail = Mail(
            ma_subject=ma_subject,
            ma_content=ma_content,
            ma_time=datetime.now(),
            ma_ip=request.client.host
        )
        db.add(mail)
        db.commit()
        ma_id = mail.ma_id
    else:  # 수정
        mail = db.get(Mail, ma_id)
        if not mail:
            raise AlertException("메일 정보가 없습니다.", 400)

        mail.ma_subject = ma_subject
        mail.ma_content = ma_content
        db.commit()

    return RedirectResponse(f"/admin/mail_form/{ma_id}", status_code=303)


@router.post("/mail_delete", dependencies=[Depends(validate_token)])
async def mail_delete(
    request: Request,
    db: db_session,
    checks: List[int] = Form(..., alias="chk[]"),
    ma_id: List[int] = Form(..., alias="ma_id[]"),
):
    """
    회원메일발송 삭제
    """
    for i in checks:
        db.execute(delete(Mail).where(Mail.ma_id == ma_id[i]))
    db.commit()

    return RedirectResponse("/admin/mail_list", status_code=303)


@router.get("/mail_test/{ma_id}")
async def mail_test(
    request: Request,
    db: db_session,
    ma_id: int = Path(...),
):
    """
    회원메일발송 테스트
    """
    config = request.state.config
    if not config.cf_email_use:
        raise AlertException("환경설정에서 '메일발송 사용'에 체크하셔야 메일을 발송할 수 있습니다.", 400)

    exists_mail = db.get(Mail, ma_id)
    if not exists_mail:
        raise AlertException("메일 정보가 없습니다.", 400)

    login_member = request.state.login_member
    name = login_member.mb_name
    nick = login_member.mb_nick
    mb_id = login_member.mb_id
    email = login_member.mb_email
    ma_id = exists_mail.ma_id

    subject = exists_mail.ma_subject
    content = exists_mail.ma_content
    # 치환
    content = content.replace("{이름}", name)
    content = content.replace("{닉네임}", nick)
    content = content.replace("{회원아이디}", mb_id)
    content = content.replace("{이메일}", email)

    mb_md5 = hashlib.md5(f"{mb_id}{email}{login_member.mb_datetime}".encode()).hexdigest()
    content = content + f'<p>더 이상 정보 수신을 원치 않으시면 [<a href="/bbs/email_stop/{mb_id}&mb_md5={mb_md5}" target="_blank">수신거부</a>] 해 주십시오.</p>' 

    # 메일 발송
    mailer(email, subject, content)

    raise AlertException(f"{nick}({email})님께 테스트 메일을 발송하였습니다. 확인하여 주십시오.")


@router.get("/mail_select_form/{ma_id}")
async def mail_select_form(
    request: Request,
    db: db_session,
    ma_id: int = Path(...),
    mb_id1: int = Query(1),
    mb_level_from: str = Query(1),
    mb_level_to: int = Query(10),
    mb_mailling: bool = Query(1),
    mb_email: str = Query(""),
):
    """
    회원메일발송 선택
    """
    request.session["menu_key"] = MAIL_MENU_KEY

    config = request.state.config
    if not config.cf_email_use:
        raise AlertException("환경설정에서 '메일발송 사용'에 체크하셔야 메일을 발송할 수 있습니다.", 403)

    exists_mail = db.get(Mail, ma_id)
    if not exists_mail:
        raise AlertException("메일 정보가 없습니다.")

    cleaned_host = re.sub(r'^(www[^\.]*\.)', '', request.client.host)

    groups = db.scalars(select(Group).order_by(Group.gr_subject)).all()

    # 전체/탈퇴 회원수
    member_count = db.scalar(select(func.count(Member.mb_id)))
    leave_count = db.scalar(
        select(func.count(Member.mb_id))
        .where(Member.mb_leave_date != "")
    )

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
        "member_count": member_count,
        "leave_count": leave_count,
    }
    return templates.TemplateResponse("mail_select_form.html", context)


@router.post("/mail_select_list", dependencies=[Depends(validate_token)])
async def mail_select_list(
    request: Request,
    db: db_session,
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
    """
    회원메일발송 선택
    """
    query = select(Member).where(Member.mb_level.between(mb_level_from, mb_level_to))

    if mb_id1 != 1:
        query = query.where(Member.mb_id.between(mb_id1_from, mb_id1_to))
    if mb_email:
        query = query.where(Member.mb_email.like(f"%{mb_email}%"))
    if mb_mailling:
        query = query.where(Member.mb_mailling == mb_mailling)

    if gr_id:
        group_members = db.get(Group, gr_id).members
        if not group_members:
            raise AlertException("선택하신 게시판 그룹회원이 한명도 없습니다.")
        group_member_ids = [member.mb_id for member in group_members]
        query = query.where(Member.mb_id.in_(group_member_ids))

    # 탈퇴, 차단하지 않은 회원만 선택합니다.
    # 1년 1월 1일의 datetime 객체를 생성합니다.
    cutoff_date = datetime(1, 1, 1)
    # cutoff_date 이전의 mb_leave_date와 mb_intercept_date를 가진 멤버만 선택합니다.
    current_db_engine = db_connect._db_engine
    if current_db_engine == 'sqlite':
        comparing_leave_date = Member.mb_leave_date <= cutoff_date
        comparing_intercept_date = Member.mb_intercept_date <= cutoff_date
    else:
        comparing_leave_date = func.cast(Member.mb_leave_date, DateTime) <= cutoff_date
        comparing_intercept_date = func.cast(Member.mb_intercept_date, DateTime) <= cutoff_date            
    query = query.where(
        or_(Member.mb_leave_date == "", comparing_leave_date),
        or_(Member.mb_intercept_date == "", comparing_intercept_date)
    )
    members = db.scalars(query).all()

    # members 를 ma_last_option 필드에 저장함 (파이썬, PHP의 차이점으로 인해 POST로 넘기지 못하고 DB에 저장해야함)
    save_members = []
    textarea_members = []
    for member in members:
        save_members.append(
            member.mb_name
            + "||" + member.mb_nick
            + "||" + member.mb_id
            + "||" + member.mb_email
        )
        textarea_members.append(
            member.mb_email
            + "||" + member.mb_id
            + "||" + member.mb_name
            + "||" + member.mb_nick
            + "||" + member.mb_datetime.strftime("%Y-%m-%d %H:%M:%S")
        )
    save_members_str = "\n".join(save_members)
    textarea_members_str = "\n".join(textarea_members)

    db.execute(
        update(Mail)
        .where(Mail.ma_id == ma_id)
        .values(ma_last_option=save_members_str)
    )
    db.commit()

    extend = {
        "request": request,
        "config": request.state.config,
        "login_member": request.state.login_member,
        "members": members,
        "ma_id": ma_id,
        "textarea_members_str": textarea_members_str,
    }
    return templates.TemplateResponse("mail_select_list.html", extend)


@router.post("/mail_select_result", dependencies=[Depends(validate_token)], response_class=HTMLResponse)
async def mail_select_result(
    request: Request,
    db: db_session,
    ma_id: int = Form(...),
):
    """
    회원메일발송 결과보여주는 HTML 페이지
    """
    context = {
        "request": request,
        "ma_id": ma_id,
    }
    return templates.TemplateResponse("mail_select_result.html", context)


@router.get("/mail_select_send")
async def mail_select_send(
    request: Request,
    db: db_session,
    ma_id: int = Query(...),
):
    """
    회원메일발송 처리
    """
    async def send_events(members: list, mail_subject: str, mail_content: str):
        count = 0
        sleepsec = 1  # 1초 간격으로 조정

        for member in members:
            mb_name, mb_nick, mb_id, mb_email = member.split("||")

            if not mb_email:
                continue
            
            mb_md5 = hashlib.md5(f"{mb_id}{mb_email}{datetime.now()}".encode()).hexdigest()

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

    exists_mail = db.get(Mail, ma_id)
    if not exists_mail.ma_subject or not exists_mail.ma_content:
        raise AlertException("메일 내용이 없습니다.", 400)

    members = exists_mail.ma_last_option.split("\n")

    return EventSourceResponse(send_events(members, exists_mail.ma_subject, exists_mail.ma_content))


@router.get("/mail_preview/{ma_id}")
async def mail_preview(
    request: Request,
    db: db_session,
    ma_id: int = Path(...),
):
    """
    회원메일발송 미리보기
    """
    request.session["menu_key"] = MAIL_MENU_KEY

    exists_mail = db.get(Mail, ma_id)
    if not exists_mail:
        raise AlertException("메일 정보가 없습니다.", 400)

    login_member = request.state.login_member

    subject = exists_mail.ma_subject
    content = exists_mail.ma_content

    content = content.replace("{이름}", login_member.mb_name)
    content = content.replace("{닉네임}", login_member.mb_nick)
    content = content.replace("{회원아이디}", login_member.mb_id)
    content = content.replace("{이메일}", login_member.mb_email)

    content = content + f"<hr size=0><p><span style='font-size:10pt; font-family:돋움'>\
    ▶ 더 이상 정보 수신을 원치 않으시면\
    [<a href='/bbs/email_stop/{login_member.mb_id}&mb_md5=***' target='_blank'>수신거부</a>]\
    해 주십시오.</span></p>"

    context = {
        "request": request,
        "mail_subject": subject,
        "mail_content": content,
    }
    return templates.TemplateResponse("mail_preview.html", context)
