import logging
import os
from datetime import datetime
from typing import Optional, Union

from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends
from fastapi import Request
from fastapi.params import Form, Query
from popbill import PopbillException
from sqlalchemy import func
from sqlalchemy import or_
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse

from common.database import get_db
from lib.common import MyTemplates, ADMIN_TEMPLATES_DIR, datetime_format, auth_check_menu, AlertException, get_paging, \
    default_if_none
from lib.plugin.service import PLUGIN_DIR, get_all_plugin_module_names
from plugin.popbill import module_name, models, POPBILL_LINK_ID, POPBILL_SECRET_KEY
from plugin.popbill.models import SmsForm, SmsBook, SmsBookGroup, SmsWrite, SmsHistory
from plugin.popbill.models import SmsFormGroup, SmsConfig
from plugin.popbill.router import messageService

admin_router = APIRouter(prefix="/sms_admin")

templates = MyTemplates(directory=[ADMIN_TEMPLATES_DIR, f"{PLUGIN_DIR}/{module_name}/templates"])
templates.env.globals["get_all_plugin_module_names"] = get_all_plugin_module_names
templates.env.globals["datetime"] = datetime
templates.env.filters["datetime_format"] = datetime_format
templates.env.globals['relativedelta'] = relativedelta
templates.env.filters["default_if_none"] = default_if_none


def number_format(number: int) -> str:
    """숫자를 천단위로 구분하여 반환하는 템플릿 필터

    Args:
        number (int): 숫자

    Returns:
        str: 천단위로 구분된 숫자
    """
    if isinstance(number, int):
        return "{:,}".format(number)
    else:
        return "Invalid input. Please provide an integer."


templates.env.globals['number_format'] = number_format


@admin_router.get("/config")
def show_sms_config(request: Request, db: Session = Depends(get_db)):
    MEMBER_MENU_KEY = "900100"
    request.session["menu_key"] = MEMBER_MENU_KEY
    error = auth_check_menu(request, MEMBER_MENU_KEY, "r")
    if error:
        raise AlertException(error)

    sms_config = db.query(SmsConfig).first()
    if not sms_config:
        sms_config = {}

    popbill_registered = POPBILL_LINK_ID and POPBILL_SECRET_KEY
    company_register_num = os.getenv("POPBILL_COMPANY_REGISTER_NUM")
    charge_url = ""
    remain_point = 0
    if popbill_registered:
        try:
            remain_point = messageService.getBalance(company_register_num)
            charge_url = messageService.getChargeURL(company_register_num, POPBILL_LINK_ID)

        except PopbillException as e:
            logging.warning(f"Exception Occur : {e.code}, {e.message}")

    return templates.TemplateResponse("admin/sms_config.html", {
        "config": request.state.config,
        "sms_config": sms_config,
        "popbill_id": POPBILL_LINK_ID,
        "remain_point": int(float(remain_point)),
        "charge_url": charge_url,
        "popbill_registered": popbill_registered,
        "request": request
    })


@admin_router.get("/sms_write")
def show_sms_send_form(request: Request, db: Session = Depends(get_db),
                       fg_no: Optional[str] = Form(default=0),
                       wr_no: Optional[int] = Form(default=0),
                       bk_no: Optional[int] = Query(default=None),
                       fo_no: Optional[int] = Query(default=None)

                       ):
    MEMBER_MENU_KEY = "900100"
    request.session["menu_key"] = MEMBER_MENU_KEY
    error = auth_check_menu(request, MEMBER_MENU_KEY, "r")
    if error:
        raise AlertException(error)

    sms_config = db.query(SmsConfig).filter(SmsConfig.cf_phone).first()
    cnt = db.query(SmsForm).filter(SmsForm.fg_no == 0).count()
    # 미분류 카운트
    no_group_count = cnt if cnt else 0
    next_year = datetime.now() + relativedelta(years=1)

    form_group = db.query(SmsFormGroup).order_by(SmsFormGroup.fg_name).all()

    sms_book = []
    if bk_no:  # smsbook (연락처) 기본키
        sms_book = db.query(SmsBook).filter(SmsBook.bk_no == bk_no).scalar()

    sms_form_content = ""
    if fo_no:  # sms_form 기본키
        sms_form = db.query(SmsForm).filter(SmsForm.fo_no == fo_no).scalar()
        if sms_form:
            sms_form_content = sms_form.fo_content.replace(r"\r\n", "\\n").replace(r"\n", "\\n")

    member_sms_history = []
    guest_sms_history = []
    sms_write = []
    member_sms_hitory_send_data = ''
    if wr_no:  # SMSWrite(발송내역) 번호
        # 메세지와 발송번호
        sms_write = db.query(SmsWrite).filter(SmsForm.fo_no == wr_no).scalar()

        member_sms_history = db.query(SmsHistory).filter(SmsHistory.wr_no == wr_no, SmsHistory.bk_no > 0).all()
        if len(member_sms_history) > 0:
            send_data = 'p,'
            for data in member_sms_history:
                send_data += f"{data.bk_no},"

            member_sms_hitory_send_data = send_data

        # 비회원 목록

        guest_sms_history = db.query(SmsHistory).filter(SmsHistory.wr_no == wr_no, SmsHistory.bk_no == 0).all()

    return templates.TemplateResponse("admin/sms_write.html", {
        "next_year": next_year,
        "sms_config": sms_config,
        "sms_write": sms_write,
        "sms_book": sms_book,
        "sms_form_content": sms_form_content,
        "member_sms_history": member_sms_history,
        "member_sms_history_count": len(member_sms_history),
        "member_sms_hitory_send_data": member_sms_hitory_send_data,
        "guest_sms_history": guest_sms_history,
        "guest_sms_history_count": len(guest_sms_history),
        "config": request.state.config,
        "request": request,
        "fg_no": fg_no,
        "no_group_count": no_group_count,
        "form_group": form_group
    })


@admin_router.get("/form_group")
def show_emoticon_form(request: Request, db: Session = Depends(get_db)):
    MEMBER_MENU_KEY = "900500"
    request.session["menu_key"] = MEMBER_MENU_KEY
    error = auth_check_menu(request, MEMBER_MENU_KEY, "r")
    if error:
        raise AlertException(error)

    emoticon_group = db.query(models.SmsFormGroup).order_by(SmsFormGroup.fg_name.desc()).all()
    none_group = db.query(SmsForm).filter(SmsForm.fg_no == 0).all()  # 미분류 그룹
    none_group_count = db.query(SmsForm).filter(SmsForm.fg_no == 0).count()

    return templates.TemplateResponse("admin/form_emoticon_group.html", {
        "config": request.state.config,
        "emoticon_group": emoticon_group,
        "none_group": none_group,
        "none_group_count": none_group_count,
        "request": request,
        "total_count": len(emoticon_group) + none_group_count
    })


@admin_router.post("/emoticon_group")
def add_emoticon_group(request: Request, db: Session = Depends(get_db), fg_name: str = Form(...)):
    error = auth_check_menu(request, request.session["menu_key"], "w")
    if error:
        raise AlertException(error)

    if not fg_name:
        raise AlertException("그룹명을 입력해주세요.")

    if db.query(SmsFormGroup).filter(SmsFormGroup.fg_name == fg_name).first():
        raise AlertException("이미 존재하는 그룹명입니다.")

    fg = SmsFormGroup()
    fg.fg_name = fg_name
    fg.fg_count = 0
    fg.fg_member = 0

    db.add(fg)
    db.commit()

    return RedirectResponse(url="/admin/sms_admin/form_group", status_code=302)


@admin_router.post("group_move")
def move_emoticon_group(request: Request, db: Session = Depends(get_db),
                        fg_no: Optional[int] = Form(default=0),
                        move_no: Optional[int] = Form(default=0)):
    sub_menu_key = "900500"
    error = auth_check_menu(request, sub_menu_key, "w")
    if error:
        raise AlertException(error)

    if fg_no:
        result = db.query(SmsFormGroup).filter(SmsFormGroup.fg_no == fg_no).first()
        if result:
            fg_count = result.fg_count
        else:
            fg_count = 0

        db.query(SmsFormGroup).filter(SmsFormGroup.fg_no == move_no).update(
            {SmsFormGroup.fg_count: SmsFormGroup.fg_count + fg_count}
        )

        db.query(SmsFormGroup).filter(SmsFormGroup.fg_no == fg_no).update({
            SmsFormGroup.fg_count: 0,
            SmsFormGroup.fg_no: fg_no
        })

    else:
        fg_count_result = db.query(func.count()).filter(SmsForm.fg_no == 0).scalar()
        db.query(SmsFormGroup).filter(SmsFormGroup.fg_no == move_no).update({
            "fg_count": SmsFormGroup.fg_count + fg_count_result
        })

    form_group = db.query(SmsFormGroup).filter(SmsFormGroup.fg_no == move_no).first()

    db.query(SmsForm).filter(SmsForm.fg_no == fg_no).update({
        SmsForm.fg_no: move_no,
        SmsForm.fg_member: form_group.fg_member
    })
    db.commit()

    return RedirectResponse(url="/admin/sms_admin/form_group", status_code=302)


@admin_router.get("/form_list")
def show_emoticon_form_list(request: Request, db: Session = Depends(get_db), fg_no: Optional[int] = Form(default=0)):
    MEMBER_MENU_KEY = "900600"
    request.session["menu_key"] = MEMBER_MENU_KEY

    error = auth_check_menu(request, MEMBER_MENU_KEY, "r")
    if error:
        raise AlertException(error)

    sfl = request.state.sfl
    if not ['all', "content", "name"]:
        sfl = "all"
    fg_no = fg_no or 0

    if not sfl:
        emoticon_group = (db.query(models.SmsFormGroup).filter(SmsFormGroup.fg_no == fg_no)
                          .order_by(SmsFormGroup.fg_name.desc()).all())
    else:
        emoticon_group = (db.query(models.SmsFormGroup).filter(
            SmsFormGroup.fg_no == fg_no and SmsFormGroup.fg_name == request.state.stx)
                          .order_by(SmsFormGroup.fg_name.desc()).all())

    # 미분류 그룹
    none_group = db.query(SmsForm).filter(SmsForm.fg_no == 0).scalar()
    none_group_count = db.query(func.count()).filter(SmsForm.fg_no == 0).scalar()

    context = {
        "config": request.state.config,
        "emoticon_group": emoticon_group,
        "none_group": none_group,
        "none_group_count": none_group_count,
        "request": request,
        "total_count": len(emoticon_group) + none_group_count
    }

    return templates.TemplateResponse("admin/form_emoticon_list.html", context)


@admin_router.post("/form_group_update")
def update_form_group(request: Request, db: Session = Depends(get_db),
                      fg_no: Optional[int] = Form(default=0),
                      fg_name: Optional[str] = Form(default=""),
                      fg_member: Optional[int] = Form(default=0)):
    sub_menu_key = "900600"
    error = auth_check_menu(request, sub_menu_key, "w")
    if error:
        raise AlertException(error)

    if not fg_name:
        raise AlertException("그룹명을 입력해주세요.")

    if db.query(SmsFormGroup).filter(SmsFormGroup.fg_name == fg_name).first():
        raise AlertException("이미 존재하는 그룹명입니다.")

    db.query(SmsFormGroup).filter(SmsFormGroup.fg_no == fg_no).update({
        SmsFormGroup.fg_name: fg_name,
        SmsFormGroup.fg_member: fg_member
    })

    db.commit()

    return RedirectResponse(url="/admin/sms_admin/form_group", status_code=302)


@admin_router.get("/ajax/sms_write_form")
async def get_form_data(
        fg_no: Optional[Union[int, str]] = Query(default='all', alias="fg_no"),
        st: Optional[str] = None,
        sv: Optional[str] = None,
        current_page: Optional[int] = Query(default=1, alias="page"),  # 페이지
        db: Session = Depends(get_db),
):
    page_size = 6

    if not current_page:
        current_page = 1

    filters = []

    if str(fg_no).isnumeric:
        filters.append(SmsForm.fg_no == fg_no)

    if st == 'all':
        filters.append(or_(SmsForm.fo_name.like(f'%{sv}%'), SmsForm.fo_content.like(f'%{sv}%')))
    elif st == 'name':
        filters.append(SmsForm.fo_name.like(f'%{sv}%'))
    elif st == 'content':
        filters.append(SmsForm.fo_content.like(f'%{sv}%'))

    total_count = db.query(func.count()).filter(*filters).scalar()
    total_page = int(total_count / page_size) + (1 if total_count % page_size != 0 else 0)
    page_start = page_size * (current_page - 1)

    # todo 미사용 코드
    # vnum = total_count - ((current_page - 1) * page_size)
    # 
    # form_group = db.query(SmsFormGroup).order_by(SmsFormGroup.fg_name).all()
    # 
    # no_count = db.query(func.count().label('cnt')).filter(SmsForm.fg_no == 0).scalar()
    # 
    # count = 1
    form_groups = (
        db.query(SmsForm)
        .filter(*filters)
        .order_by(SmsForm.fo_no.desc())
        .offset(page_start)
        .limit(page_size)
        .all()
    )

    list_text = ""

    if not total_count:
        list_text = "<li class=\"empty_list\">데이터가 없습니다.</li>"

    for form_group in form_groups:
        # todo 미사용 코드주석
        # tmp = db.query(SmsFormGroup.fg_name).filter(SmsFormGroup.fg_no == form_group.fg_no).scalar()
        # group_name = '미분류' if not tmp else tmp

        list_text += (
            "<li class=\"screen_list sms5_box\">"
            "<span class=\"box_ico\"></span>"
            f"<textarea readonly class=\"sms_textarea box_txt box_square\" onclick=\"emoticon_list.go({form_group.fo_no})\">{form_group.fo_content}</textarea>"
            f"<textarea id=\"fo_contents_{form_group.fo_no}\" style=\"display:none\">{form_group.fo_content}</textarea>"
            f"<strong class=\"emo_tit\">{form_group.fo_name[:20]}</strong>"
            "</li>"
        )

    arr_ajax_msg = {
        'error': '',
        'list_text': list_text,
        'page': current_page,
        'total_count': total_count,
        'total_page': total_page
    }

    return arr_ajax_msg


@admin_router.get("/ajax/sms_write_group_form")
def show_sms_write_group_form(
        request: Request,
        db: Session = Depends(get_db),
):
    MEMBER_MENU_KEY = "900300"
    request.session["menu_key"] = MEMBER_MENU_KEY
    error = auth_check_menu(request, MEMBER_MENU_KEY, "r")
    if error:
        raise AlertException(error)

    none_group = db.query(SmsBookGroup).filter(SmsBookGroup.bg_no == 1).scalar()
    if not none_group:
        none_group = SmsBookGroup()
        none_group.bg_receipt = 0
        none_group.bg_datetime = datetime.now()
        none_group.bg_member = 0
        none_group.bg_name = "미분류"

    groups = db.query(SmsBookGroup).order_by(SmsBookGroup.bg_name).filter(SmsBookGroup.bg_no > 1).all()
    db.commit()
    if not groups:
        groups = []

    return templates.TemplateResponse("admin/sms_write_group.html", context={
        "request": request,
        "none_group": none_group,
        "groups": groups,
    })


@admin_router.get("/num_book")
def show_sms_num_book_form(
        request: Request,
        bg_no: Optional[int] = Form(default=0),
        ap: Optional[int] = Form(default=0),
        no_hp: Optional[str] = Query(default="", alias="no_hp"),
        st: Optional[str] = None,
        sv: Optional[str] = None,
        db: Session = Depends(get_db),
):
    MEMBER_MENU_KEY = "900300"
    request.session["menu_key"] = MEMBER_MENU_KEY
    current_page = request.state.page if request.state.page else 1

    request.state.page = int(current_page)
    error = auth_check_menu(request, MEMBER_MENU_KEY, "r")
    if error:
        raise AlertException(error)

    filters = []
    # filters = []
    # 
    # if str(fg_no).isnumeric:
    #     filters.append(SmsForm.fg_no == fg_no)

    if bg_no:
        filters.append(SmsBook.bg_no == bg_no)

    if st == 'all':
        filters.append(or_(SmsBook.bk_name.like(f'%{sv}%'), SmsBook.bk_hp.like(f'%{sv}%')))
    elif st == 'name':
        filters.append(SmsBook.bk_name.like(f'%{sv}%'))
    elif st == 'hp':
        filters.append(SmsBook.bk_hp.like(f'%{sv}%'))

    no_hp_checked = ""
    set_cookie = None
    if no_hp == "yes":
        set_cookie = ('cookie_no_hp', 'yes', 60 * 60 * 24 * 365)
        no_hp_checked = "checked"
    else:
        set_cookie = ('cookie_no_hp', 'no', 0)
        no_hp_checked = ""

    if no_hp_checked == "checked":
        filters.append(SmsBook.bk_hp != '')

    total_count = db.query(SmsBook).filter(*filters).count()
    page_size = 10
    total_page = int(total_count / page_size) + (1 if total_count % page_size != 0 else 0)
    page_start = page_size * (request.state.page - 1)

    # 인덱스로 표시되는 가상인덱스 번호
    vnum = total_count - ((request.state.page - 1) * page_size)
    receipt_count = db.query(func.count()).filter(SmsBook.bk_receipt == 1, *filters).scalar()
    reject_count = total_count - receipt_count

    none_member_count = db.query(func.count()).filter(SmsBook.mb_id == '', *filters).scalar()

    member_count = total_count - none_member_count

    none_group = db.query(SmsBookGroup).filter(SmsBookGroup.bg_no == 1).scalar()
    groups = db.query(SmsBookGroup).order_by(SmsBookGroup.bg_name).filter(SmsBookGroup.bg_no > 1).all()

    person_phone_books = (db.query(SmsBook).order_by(SmsBook.bk_no.desc()).filter(*filters)
                          .offset(page_start).limit(page_size).all())

    person_phone_groups = []
    for data in person_phone_books:
        group_name = db.query(SmsBookGroup.bg_name).filter(SmsBookGroup.bg_no == data.bg_no).scalar()
        data.group_name = group_name
        person_phone_groups.append(data)

    sms_config = db.query(SmsConfig).first()
    context = {
        "request": request,
        "total_count": total_count,
        "receipt_count": receipt_count,
        "reject_count": reject_count,
        "none_member_count": none_member_count,
        "member_count": member_count,
        "none_group": none_group,
        "groups": groups,
        "bg_no": bg_no,
        "person_phone_groups": person_phone_groups,
        "paging": get_paging(request, request.state.page, total_count, page_rows=page_size),
        "sms_config": sms_config,
        "no_hp_checked": no_hp_checked,
        "vnum": vnum,
    }

    response = templates.TemplateResponse("admin/sms_num_book.html", context)
    if set_cookie:
        response.set_cookie(*set_cookie)
    return response
