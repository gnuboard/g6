from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Request, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session
from database import get_db
import models
import datetime
from common import *
from dataclassform import MemberForm
from pbkdf2 import create_hash

router = APIRouter()
templates = Jinja2Templates(directory=ADMIN_TEMPLATES_DIR)
# 파이썬 함수 및 변수를 jinja2 에서 사용할 수 있도록 등록
templates.env.globals["getattr"] = getattr
templates.env.globals["today"] = SERVER_TIME.strftime("%Y%m%d")
templates.env.globals["get_selected"] = get_selected
templates.env.globals["get_member_level_select"] = get_member_level_select
templates.env.globals['subject_sort_link'] = subject_sort_link
templates.env.globals["get_admin_menus"] = get_admin_menus
templates.env.globals["generate_token"] = generate_token

MEMBER_MENU_KEY = "200100"


@router.get("/member_list")
async def member_list(
    request: Request,
    db: Session = Depends(get_db),
    search_params: dict = Depends(common_search_query_params),
):
    """
    회원관리 목록
    """
    request.session["menu_key"] = MEMBER_MENU_KEY

    result = select_query(
        request,
        models.Member,
        search_params,
        same_search_fields=["mb_level"],
        prefix_search_fields=[
            "mb_name",
            "mb_nick",
            "mb_tel",
            "mb_hp",
            "mb_datetime",
            "mb_recommend",
        ],
    )

    context = {
        "request": request,
        "members": result["rows"],
        "admin": request.state.login_member,  # 로그인해 있는 회원을 관리자로 간주함
        "total_count": result["total_count"],
        "paging": get_paging(
            request, search_params["current_page"], result["total_count"]
        ),
    }
    return templates.TemplateResponse("member_list.html", context)


@router.post("/member_list_update")
async def member_list_update(
        request: Request,
        db: Session = Depends(get_db),
        token: Optional[str] = Form(...),
        checks: Optional[List[int]] = Form(None, alias="chk[]"),
        mb_id: Optional[List[str]] = Form(None, alias="mb_id[]"),
        mb_open: Optional[List[int]] = Form(None, alias="mb_open[]"),
        mb_mailling: Optional[List[int]] = Form(None, alias="mb_mailling[]"),
        mb_sms: Optional[List[int]] = Form(None, alias="mb_sms[]"),
        mb_intercept_date: Optional[List[int]] = Form(None, alias="mb_intercept_date[]"),
        mb_level: Optional[List[str]] = Form(None, alias="mb_level[]"),
        act_button: Optional[str] = Form(...),
        ):
    
    if not compare_token(request, token, "member_list"):
        return templates.TemplateResponse("alert.html", {"request": request, "errors": ["토큰이 유효하지 않습니다."]})
        
    query_string = generate_query_string(request)

    if act_button == "선택삭제":
        for i in checks:
            # 관리자와 로그인된 본인은 삭제 불가
            if (request.state.config.cf_admin == mb_id[i]) or (request.state.login_member.mb_id == mb_id[i]):
                continue
                
            member = (db.query(models.Member).filter(models.Member.mb_id == mb_id[i]).first())
            if member:
                # // 이미 삭제된 회원은 제외
                # if(preg_match('#^[0-9]{8}.*삭제함#', $mb['mb_memo']))
                #     return
                # 이미 삭제된 회원은 제외
                if re.match(r"^[0-9]{8}.*삭제함", member.mb_memo):
                    continue

                # member 의 경우 레코드를 삭제하는게 아니라 mb_id 를 남기고 모두 제거
                member.mb_password = ""
                member.mb_level = 1
                member.mb_email = ""
                member.mb_homepage = ""
                member.mb_tel = ""
                member.mb_hp = ""
                member.mb_zip1 = ""
                member.mb_zip2 = ""
                member.mb_addr1 = ""
                member.mb_addr2 = ""
                member.mb_addr3 = ""
                member.mb_point = 0
                member.mb_profile = ""
                member.mb_birth = ""
                member.mb_sex = ""
                member.mb_signature = ""
                member.mb_memo = (f"{SERVER_TIME.strftime('%Y%m%d')} 삭제함\n{member.mb_memo}")
                member.mb_certify = ""
                member.mb_adult = 0
                member.mb_dupinfo = ""
                db.commit()
                # 나머지 테이블에서도 삭제
                # 포인트 테이블에서 삭제

                # 그룹접근가능 테이블에서 삭제

                # 쪽지 테이블에서 삭제

                # 스크랩 테이블에서 삭제

                # 관리권한 테이블에서 삭제

                # 그룹관리자인 경우 그룹관리자를 공백으로
                db.query(models.Group).filter(models.Group.gr_admin == mb_id[i]).update({models.Group.gr_admin: ""})
                db.commit()

                # 게시판관리자인 경우 게시판관리자를 공백으로
                db.query(models.Board).filter(models.Board.bo_admin == mb_id[i]).update({models.Board.bo_admin: ""})
                db.commit()

                # 소셜로그인에서 삭제 또는 해제

                # 아이콘 삭제

                # 프로필 이미지 삭제

            return RedirectResponse(f"/admin/member_list?{query_string}", status_code=303)

    # 선택수정
    # print(mb_open)
    for i in checks:
        member = db.query(models.Member).filter(models.Member.mb_id == mb_id[i]).first()
        if member:
            if (request.state.config.cf_admin == mb_id[i]) or (request.state.login_member.mb_id == mb_id[i]):
                # 관리자와 로그인된 본인은 차단일자를 설정했다면 수정불가
                if get_from_list(mb_intercept_date, i, 0):
                    continue
            
            # print(get_from_list(mb_open, i, 0))
            member.mb_open = get_from_list(mb_open, i, 0)
            member.mb_mailling = get_from_list(mb_mailling, i, 0)
            member.mb_sms = get_from_list(mb_sms, i, 0)
            member.mb_intercept_date = (datetime.now().strftime("%Y%m%d") if get_from_list(mb_intercept_date, i, 0) else "")
            member.mb_level = mb_level[i]
            db.commit()

    return RedirectResponse(f"/admin/member_list?{query_string}", status_code=303)


@router.get("/member_form")
def member_form_add(request: Request, db: Session = Depends(get_db)):
    """
    회원추가 폼
    """
    request.session["menu_key"] = MEMBER_MENU_KEY
    error = auth_check(request, request.session["menu_key"], "r")
    if error:
        return templates.TemplateResponse("alert.html", {"request": request, "errors": [error]})

    return templates.TemplateResponse("member_form.html", {"request": request, "member": None})


# 회원수정 폼
@router.get("/member_form/{mb_id}")
def member_form_edit(mb_id: str, request: Request, db: Session = Depends(get_db)):
    """
    회원수정 폼
    """
    request.session["menu_key"] = MEMBER_MENU_KEY
    error = auth_check(request, request.session["menu_key"], "r")
    if error:
        return templates.TemplateResponse("alert.html", {"request": request, "errors": [error]})

    exists_member = db.query(models.Member).filter_by(mb_id = mb_id).first()
    if not exists_member:
        return templates.TemplateResponse("alert.html", {"request": request, "errors": ["회원아이디가 존재하지 않습니다."]}) 

    return templates.TemplateResponse("member_form.html", {"request": request, "member": exists_member})


# DB등록 및 수정
@router.post("/member_form_update")
def member_form_update(
        request: Request,
        db: Session = Depends(get_db),
        token: str = Form(...),
        mb_id: str = Form(...),
        mb_password: str = Form(default=""),
        mb_certify_case: Optional[str] = Form(default=""),
        mb_intercept_date: Optional[str] = Form(default=""),
        mb_leave_date: Optional[str] = Form(default=""),
        form_data: MemberForm = Depends(),
        ):

    # token 값에 insert 가 포함되어 있다면 등록    
    if compare_token(request, token, "insert"):
        exists_member = (
            db.query(models.Member).filter(models.Member.mb_id == mb_id).first()
        )
        if exists_member:
            errors = [f"{mb_id} 회원아이디가 이미 존재합니다. (등록불가)"]
            return templates.TemplateResponse(
                "alert.html", {"request": request, "errors": errors}
            )

        new_member = models.Member(mb_id=mb_id, **form_data.__dict__)

        if mb_certify_case and form_data.mb_certify:
            new_member.mb_certify = mb_certify_case
            new_member.mb_adult = form_data.mb_adult
        else:
            new_member.mb_certify = ""
            new_member.mb_adult = 0

        if form_data.mb_password:
            new_member.mb_password = create_hash(form_data.mb_password)
        else:
            # 비밀번호가 없다면 현재시간으로 해시값을 만든후 다시 해시 (알수없게 만드는게 목적)
            new_member.mb_password = create_hash(create_hash(TIME_YMDHIS))

        db.add(new_member)
        db.commit()

    elif compare_token(request, token, "update"): # token 값에 update 가 포함되어 있다면 수정
        exists_member = (db.query(models.Member).filter(models.Member.mb_id == mb_id).first())
        if not exists_member:
            return templates.TemplateResponse("alert.html", {"request": request, "errors": [f"{mb_id} 회원아이디가 존재하지 않습니다. (수정불가)"]})
        
        if (request.state.config.cf_admin == mb_id) or (request.state.login_member.mb_id == mb_id):
            # 관리자와 로그인된 본인은 차단일자, 탈퇴일자를 설정했다면 수정불가
            if mb_intercept_date:
                return templates.TemplateResponse("alert.html", {"request": request, "errors": ["로그인된 관리자의 차단일자를 설정할 수 없습니다."]})
            if mb_leave_date:
                return templates.TemplateResponse("alert.html", {"request": request, "errors": ["로그인된 관리자의 탈퇴일자를 설정할 수 없습니다."]})

        # 폼 데이터 반영 후 commit
        for field, value in form_data.__dict__.items():
            setattr(exists_member, field, value)

        # 수정시 비밀번호를 입력했다면 (수정에서는 비밀번호를 입력하지 않아도 됨)
        if mb_password:
            exists_member.mb_password = create_hash(mb_password)
            
        if mb_certify_case and form_data.mb_certify:
            exists_member.mb_certify = mb_certify_case
            exists_member.mb_adult = form_data.mb_adult
            
        exists_member.mb_intercept_date = mb_intercept_date
        exists_member.mb_leave_date = mb_leave_date

        db.commit()

    else: # token 값에 insert, update 가 포함되어 있지 않다면 잘못된 접근
        return templates.TemplateResponse("alert.html", {"request": request, "errors": ["잘못된 접근입니다."]})

    return RedirectResponse(url=f"/admin/member_form/{mb_id}", status_code=302)
