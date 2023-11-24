from datetime import datetime
from typing import Optional, Union

from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Depends
from fastapi import Request
from fastapi.params import Form, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session
from sqlalchemy import func
from starlette.responses import RedirectResponse

from common.database import get_db, engine
from lib.common import MyTemplates, ADMIN_TEMPLATES_DIR, datetime_format, auth_check_menu, AlertException
from lib.plugin.service import PLUGIN_DIR, get_all_plugin_module_names
from plugin.popbill import module_name, models
from plugin.popbill.models import SmsForm
from plugin.popbill.models import SmsFormGroup, SmsConfig

admin_router = APIRouter(prefix="/sms_admin")

templates = MyTemplates(directory=[ADMIN_TEMPLATES_DIR, f"{PLUGIN_DIR}/{module_name}/templates"])
templates.env.globals["get_all_plugin_module_names"] = get_all_plugin_module_names
templates.env.globals["datetime"] = datetime
templates.env.filters["datetime_format"] = datetime_format
templates.env.globals['relativedelta'] = relativedelta
models.Base.metadata.create_all(bind=engine)


@admin_router.get("/config")
def show_sms_config(request: Request, db: Session = Depends(get_db)):
    MEMBER_MENU_KEY = "900100"

    error = auth_check_menu(request, MEMBER_MENU_KEY, "r")
    if error:
        raise AlertException(error)

    sms_config = db.query(SmsConfig).first()
    if not sms_config:
        sms_config = {}

    return templates.TemplateResponse("admin/sms_config.html", {
        "config": request.state.config,
        "sms_config": sms_config,
        "request": request})


@admin_router.get("/sms_write")
def show_sms_send_form(request: Request, db: Session = Depends(get_db), fg_no: Optional[str] = Form(default=0)):
    MEMBER_MENU_KEY = "900100"

    error = auth_check_menu(request, MEMBER_MENU_KEY, "r")
    if error:
        raise AlertException(error)

    sms_config = db.query(SmsConfig).filter(SmsConfig.cf_phone).first()
    cnt = db.query(SmsForm).filter(SmsForm.fg_no == 0).count()
    # 미분류 카운트
    no_group_count = cnt if cnt else 0
    next_year = datetime.now() + relativedelta(years=1)

    form_group = db.query(SmsFormGroup).order_by(SmsFormGroup.fg_name).all()

    return templates.TemplateResponse("admin/sms_write.html", {
        "next_year": next_year,
        "sms_config": sms_config,
        "config": request.state.config,
        "request": request,
        "fg_no": fg_no,
        "no_group_count": no_group_count,
        "form_group": form_group
    })


@admin_router.get("/form_group")
def show_emoticon_form(request: Request, db: Session = Depends(get_db)):
    MEMBER_MENU_KEY = "900500"

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
        fg_count_result = db.query(SmsForm).filter(SmsForm.fg_no == 0).count()
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

    error = auth_check_menu(request, MEMBER_MENU_KEY, "r")
    if error:
        raise AlertException(error)

    sfl = request.state.sfl
    if not ['all', "content", "name"]:
        sfl = "all"
    fg_no = fg_no or 0

    if not sfl:
        emoticon_group = db.query(models.SmsFormGroup).filter(SmsFormGroup.fg_no == fg_no).order_by(
            SmsFormGroup.fg_name.desc()).all()
    else:
        emoticon_group = (db.query(models.SmsFormGroup).filter(
            SmsFormGroup.fg_no == fg_no and SmsFormGroup.fg_name == request.state.stx)
                          .order_by(SmsFormGroup.fg_name.desc()).all())

    # 미분류 그룹
    none_group = db.query(SmsForm).filter(SmsForm.fg_no == 0).all()
    none_group_count = db.query(SmsForm).filter(SmsForm.fg_no == 0).count()

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

