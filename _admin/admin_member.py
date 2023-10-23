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
templates.env.globals["get_admin_menus"] = get_admin_menus
templates.env.globals["generate_one_time_token"] = generate_one_time_token
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
    mb_certify: Optional[List[str]] = Form(None, alias="mb_certify[]"),
    mb_open: Optional[List[int]] = Form(None, alias="mb_open[]"),
    mb_mailling: Optional[List[int]] = Form(None, alias="mb_mailling[]"),
    mb_sms: Optional[List[int]] = Form(None, alias="mb_sms[]"),
    mb_adult: Optional[List[int]] = Form(None, alias="mb_adult[]"),
    mb_intercept_date: Optional[List[int]] = Form(None, alias="mb_intercept_date[]"),
    mb_level: Optional[List[str]] = Form(None, alias="mb_level[]"),
    act_button: Optional[str] = Form(...),
):
    # if not token or not validate_one_time_token(token, 'update'):
    #     return templates.TemplateResponse("alert.html", {"request": request, "errors": ["토큰값이 일치하지 않습니다."]})
    query_string = generate_query_string(request)

    if act_button == "선택삭제":
        for i in checks:
            member = (
                db.query(models.Member).filter(models.Member.mb_id == mb_id[i]).first()
            )
            if member:
                # // 이미 삭제된 회원은 제외
                # if(preg_match('#^[0-9]{8}.*삭제함#', $mb['mb_memo']))
                #     return
                # 이미 삭제된 회원은 제외
                if re.match(r"^[0-9]{8}.*삭제함", member.mb_memo):
                    continue

                # member 의 경우 레코드를 삭제하는게 아니라 mb_id 를 남기고 모두 제거
                # $sql = " update {$g5['member_table']} set mb_password = '', mb_level = 1, mb_email = '', mb_homepage = '', mb_tel = '', mb_hp = '', mb_zip1 = '', mb_zip2 = '', mb_addr1 = '', mb_addr2 = '', mb_addr3 = '', mb_point = 0, mb_profile = '', mb_birth = '', mb_sex = '', mb_signature = '', mb_memo = '".date('Ymd', G5_SERVER_TIME)." 삭제함\n".sql_real_escape_string($mb['mb_memo'])."', mb_certify = '', mb_adult = 0, mb_dupinfo = '' where mb_id = '{$mb_id}' ";
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
                member.mb_memo = (
                    f"{SERVER_TIME.strftime('%Y%m%d')} 삭제함\n{member.mb_memo}"
                )
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
                db.query(models.Group).filter(models.Group.gr_admin == mb_id[i]).update(
                    {models.Group.gr_admin: ""}
                )
                db.commit()

                # 게시판관리자인 경우 게시판관리자를 공백으로
                db.query(models.Board).filter(models.Board.bo_admin == mb_id[i]).update(
                    {models.Board.bo_admin: ""}
                )
                db.commit()

                # 소셜로그인에서 삭제 또는 해제

                # 아이콘 삭제

                # 프로필 이미지 삭제

            return RedirectResponse(
                f"/admin/member_list?{query_string}", status_code=303
            )

    # 선택수정
    # print(mb_open)
    for i in checks:
        member = db.query(models.Member).filter(models.Member.mb_id == mb_id[i]).first()
        if member:
            member.mb_certify = mb_certify[i]
            # print(get_from_list(mb_open, i, 0))
            member.mb_open = get_from_list(mb_open, i, 0)
            member.mb_mailling = get_from_list(mb_mailling, i, 0)
            member.mb_sms = get_from_list(mb_sms, i, 0)
            member.mb_adult = get_from_list(mb_adult, i, 0)
            member.mb_intercept_date = (
                datetime.now().strftime("%Y%m%d")
                if get_from_list(mb_intercept_date, i, 0)
                else ""
            )
            member.mb_level = mb_level[i]

            # board.bo_read_point = int(bo_read_point[i]) if bo_read_point[i] is not None and bo_read_point[i].isdigit() else 0
            # board.bo_write_point = int(bo_write_point[i]) if bo_write_point[i] is not None and bo_write_point[i].isdigit() else 0
            # board.bo_comment_point = int(bo_comment_point[i]) if bo_comment_point[i] is not None and bo_comment_point[i].isdigit() else 0
            # board.bo_download_point = int(bo_download_point[i]) if bo_download_point[i] is not None and bo_download_point[i].isdigit() else 0

            # # try:
            # #     board.bo_use_sns = 1 if i in bo_use_sns is not None else 0
            # # except (TypeError, IndexError):
            # #     board.bo_use_sns = 0
            # board.bo_use_sns = get_from_list(bo_use_sns, i, 0)
            # board.bo_use_search = get_from_list(bo_use_search, i, 0)

            # checkbox 에 값을 집어 넣는것 까지 하다가 어느 정도 결과가 나와서 퇴근함 kagla 230922 17:50
            # checkbox 에 value = 0, 1, 2, 3... n 으로 증가시켜야 함 (주의)

            # board.bo_order = int(bo_order[i]) if bo_order[i] is not None and bo_order[i].isdigit() else 0
            # board.bo_device = bo_device[i] if bo_device[i] is not None else ""
            db.commit()

    return RedirectResponse(f"/admin/member_list?{query_string}", status_code=303)


@router.get("/member_form")
def member_form_add(request: Request, db: Session = Depends(get_db)):
    """
    회원추가 폼
    """
    request.session["menu_key"] = MEMBER_MENU_KEY

    token = hash_password(hash_password(""))  # 토큰값을 아무도 알수 없게 만듬
    request.session["token"] = token

    return templates.TemplateResponse(
        "member_form.html", {"request": request, "member": None, "token": token}
    )


# 회원수정 폼
@router.get("/member_form/{mb_id}")
def member_form_edit(mb_id: str, request: Request, db: Session = Depends(get_db)):
    """
    회원수정 폼
    """
    request.session["menu_key"] = MEMBER_MENU_KEY

    sst = request.state.sst
    sod = request.state.sod
    sfl = request.state.sfl
    stx = request.state.stx
    page = request.state.page
    # print(request.state.sfl)

    request.session["menu_key"] = MEMBER_MENU_KEY

    member = db.query(models.Member).filter(models.Member.mb_id == mb_id).first()
    if not member:
        raise HTTPException(status_code=404, detail=f"{mb_id} is not found.")

    # 토큰값을 회원아이디로 만들어 세션에 저장하고 수정시 넘어오는 토큰값을 비교하여 수정 상태임을 확인
    token = hash_password(mb_id)
    request.session["token"] = token

    return templates.TemplateResponse(
        "member_form.html", {"request": request, "member": member, "token": token}
    )


# DB등록 및 수정
@router.post("/member_form_update")
def member_form_update(
    request: Request,
    db: Session = Depends(get_db),
    token: str = Form(...),
    mb_id: str = Form(...),
    mb_certify_case: Optional[str] = Form(default=""),
    form_data: MemberForm = Depends(),
):
    if compare_token(request, token, "insert"):
        existing_member = (
            db.query(models.Member).filter(models.Member.mb_id == mb_id).first()
        )
        if existing_member:
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
            # new_member.mb_password = hash_password(form_data.mb_password)
            new_member.mb_password = create_hash(form_data.mb_password)
        else:
            # 비밀번호가 없다면 현재시간으로 해시값을 만든후 다시 해시 (알수없게 만드는게 목적)
            # new_member.mb_password = hash_password(hash_password(TIME_YMDHIS))
            new_member.mb_password = create_hash(create_hash(TIME_YMDHIS))

        db.add(new_member)
        db.commit()

    elif compare_token(request, token, "update"):
        existing_member = (
            db.query(models.Member).filter(models.Member.mb_id == mb_id).first()
        )
        if not existing_member:
            errors = [f"{mb_id} 회원아이디가 존재하지 않습니다. (수정불가)"]
            return templates.TemplateResponse(
                "alert.html", {"request": request, "errors": errors}
            )

        # 폼 데이터 반영 후 commit
        for field, value in form_data.__dict__.items():
            # if field == 'mb_nick_date':
            #     continue                
                
            # 해당 필드의 유형을 가져옴
            # field_type = type(getattr(existing_member, field))

            # # 필드 유형이 date 또는 datetime인 경우
            # if field_type is date:
            #     setattr(existing_member, field, date(1, 1, 1))
            # elif field_type is datetime:
            #     setattr(existing_member, field, datetime(1, 1, 1, 0, 0, 0))
            # else:
            setattr(existing_member, field, value)

        # 비밀번호가 있다면 (수정했다면) : 수정에서는 비밀번호를 입력하지 않아도 됨 (선택사항)
        if form_data.mb_password:
            # existing_member.mb_password = hash_password(form_data.mb_password)
            existing_member.mb_password = create_hash(form_data.mb_password)

        db.commit()

    else:
        return templates.TemplateResponse(
            "alert.html", {"request": request, "errors": ["잘못된 접근입니다."]}
        )

    return RedirectResponse(url=f"/admin/member_form/{mb_id}", status_code=302)
