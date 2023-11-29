import re
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import MetaData, Table
from sqlalchemy.orm import Session

from lib.plugin.service import get_admin_plugin_menus, get_all_plugin_module_names
from common.database import SessionLocal, get_db, engine

# from common.models import create_dynamic_create_write_table
import common.models as models
from lib.common import *
from jinja2 import Environment, FileSystemLoader
import random
import os
from typing import List, Optional
import socket
from common.formclass import ConfigForm


# from pydanticmodel import ConfigForm

router = APIRouter()
templates = AdminTemplates(directory=ADMIN_TEMPLATES_DIR)
# 파이썬 함수 및 변수를 jinja2 에서 사용할 수 있도록 등록
templates.env.globals["getattr"] = getattr
templates.env.globals["get_member_id_select"] = get_member_id_select
templates.env.globals["get_skin_select"] = get_skin_select
templates.env.globals["get_editor_select"] = get_editor_select
templates.env.globals["get_selected"] = get_selected
templates.env.globals["get_member_level_select"] = get_member_level_select
templates.env.globals["option_array_checked"] = option_array_checked
templates.env.globals["get_admin_menus"] = get_admin_menus
templates.env.globals["get_admin_plugin_menus"] = get_admin_plugin_menus
templates.env.globals["get_all_plugin_module_names"] = get_all_plugin_module_names
templates.env.globals["get_client_ip"] = get_client_ip

CONFIG_MENU_KEY = "100100"

@router.get("/config_form")
def config_form(request: Request, db: Session = Depends(get_db)):
    """
    기본환경설정
    """
    request.session["menu_key"] = CONFIG_MENU_KEY
    if not request.state.is_super_admin:
        raise AlertException("최고관리자만 접근 가능합니다.")

    host_name = socket.gethostname()
    host_ip = socket.gethostbyname(host_name)

    return templates.TemplateResponse(
        "config_form.html",
        {
            "request": request,
            "config": request.state.config,
            "host_name": host_name,
            "host_ip": host_ip,
        },
    )


@router.post("/config_form_update")
def config_form_update(
        request: Request,
        token: str = Form(None),
        cf_social_servicelist: List[str] = Form(None, alias="cf_social_servicelist[]"),
        form_data: ConfigForm = Depends(),
        db: Session = Depends(get_db),
        ):
    
    """
    기본환경설정 저장
    """
    request.session["menu_key"] = CONFIG_MENU_KEY
    
    if not check_token(request, token):
        raise AlertException("잘못된 접근입니다.")

    if not request.state.is_super_admin:
        raise AlertException("최고관리자만 접근 가능합니다.")
    

    # print(request.state.context['member'])

    # # 에러 체크
    # member = request.state.login_member
    # # print(member.__dict__)
    # if member:
    #     if member.mb_level < 10:
    #         return templates.TemplateResponse(
    #             "alert.html", {"request": request, "errors": ["최고관리자만 접근 가능합니다."]}
    #         )

    #     if not member.mb_id:
    #         return templates.TemplateResponse(
    #             "alert.html", {"request": request, "errors": ["회원아이디가 존재하지 않습니다."]}
    #         )
    # else:
    #     return templates.TemplateResponse(
    #         "alert.html", {"request": request, "errors": ["로그인 후 이용해 주세요."]}
    #     )

    # 차단 IP 리스트에 현재 접속 IP 가 있으면 접속이 불가하게 되므로 저장하지 않는다.
    if form_data.cf_intercept_ip:
        pattern = form_data.cf_intercept_ip.split("\n")
        for i in range(len(pattern)):
            pattern[i] = pattern[i].strip()
            if not pattern[i]:
                continue
            pattern[i] = pattern[i].replace(".", "\.")
            pattern[i] = pattern[i].replace("+", "[0-9\.]+", pattern[i])
            pat = "/^{$pattern[$i]}$/"
            if re.match(pat, request.client.host):
                return templates.TemplateResponse("alert.html", {"request": request, "errors": ["현재 접속 IP : "+ request.client.host+ " 가 차단될수 있기 때문에, 다른 IP를 입력해 주세요."]})

    if (form_data.cf_cert_use and not form_data.cf_cert_ipin and not form_data.cf_cert_hp and not form_data.cf_cert_simple):
        return templates.TemplateResponse("alert.html", {"request": request, "errors": ["본인확인을 위해 아이핀, 휴대폰 본인확인, KG이니시스 간편인증 서비스 중 하나 이상 선택해 주십시오."]})

    if not form_data.cf_cert_use:
        form_data.cf_cert_ipin = ""
        form_data.cf_cert_hp = ""
        form_data.cf_cert_simple = ""

    # 배열로 넘어오는 자료를 문자열로 변환. 예) "naver,kakao,facebook,google,twitter,payco"
    cf_social_service = ','.join(cf_social_servicelist) if cf_social_servicelist else ""
    form_data.cf_social_servicelist = cf_social_service
    config = db.query(models.Config).first()

    # 폼 데이터 반영 후 commit
    for field, value in form_data.__dict__.items():
        setattr(config, field, value)
    db.commit()
    return RedirectResponse("/admin/config_form", status_code=303)
