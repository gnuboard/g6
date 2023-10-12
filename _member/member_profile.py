from dataclasses import dataclass

from fastapi import APIRouter, Form, Depends, HTTPException
from sqlalchemy.orm import Session
from starlette.responses import RedirectResponse

from common import *
from database import get_db
from main import templates, app
from models import Config, Member

router = APIRouter()


@router.get("/member_confirm")
def check_member_form(request: Request):
    test_member = {"mb_id": ""}

    return templates.TemplateResponse("member/member_confirm.html", {
        "request": request,
        "member": test_member
    })


@dataclass
class FormData:
    mb_password: str = Form(...)


@router.post("/member_confirm", name='member_password')
def check_member(
        request: Request,
        form: FormData = Depends(),
        db: Session = Depends(get_db),
):
    errors = []
    mb_id = request.session.get("ss_mb_id", "")
    member = db.query(models.Member).filter(Member.mb_id == mb_id).first()
    if not member:
        return templates.TemplateResponse("alert.html", {"request": request, "errors": errors})
    else:
        if not verify_password(form.mb_password, member.mb_password):
            errors.append("아이디 또는 패스워드가 일치하지 않습니다.")

    if errors:
        return templates.TemplateResponse("member/member_confirm.html", {
            "request": request,
            "member": None,
            "errors": errors
        })

    return RedirectResponse(url=f"/bbs/member_profile/{member.mb_no}", status_code=302)


@router.get("/member_profile/{mb_no}", name='member_profile')
def member_profile(request: Request):
    member = None
    errors = request
    form_context = {
        "page": True,
        "action_url": router.url_path_for("member_profile", mb_no=request.path_params["mb_no"]),
        "name_readonly": "readonly",
        "hp_readonly": "readonly" if get_is_phone_certify(member) else "",
    }

    return templates.TemplateResponse("member/register_form.html", {
        "request": request,
        "member": member,
        "errors": errors,
        "form": form_context,
    })

@router.post("/member_profile/{mb_no}", name='member_profile_save')
def member_profile_save(request: Request):
    errors = []
    member = None
    form_context = {
        "page": True,
        "action_url": router.url_path_for("member_profile", mb_no=request.path_params["mb_no"]),
        "name_readonly": "readonly",
        "hp_readonly": "readonly" if get_is_phone_certify(member) else "",
    }

    return templates.TemplateResponse("member/register_form.html", {
        "request": request,
        "member": member,
        "errors": errors,
        "form": form_context,
    })

def get_is_phone_certify(member: Member) -> bool:
    """휴대폰 본인인증 사용여부 확인
    """
    config = get_config()
    return (config.cf_cert_use and config.cf_cert_req and
            (config.cf_cert_hp or config.cf_cert_simple) and
            member.mb_certify != "ipin")
