import datetime
import re
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, Path, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import delete, func, select, update

from bbs.social import SocialAuthService
from core.database import db_session
from core.exception import AlertException
from core.formclass import MemberForm
from core.models import Member, Point, GroupMember, Memo, Scrap, Auth, Group, Board
from core.template import AdminTemplates
from lib.common import *
from lib.dependencies import common_search_query_params, validate_token
from lib.member_lib import get_member_icon, get_member_image
from lib.pbkdf2 import create_hash
from lib.template_functions import get_member_level_select, get_paging


router = APIRouter()
templates = AdminTemplates()
# 파이썬 함수 및 변수를 jinja2 에서 사용할 수 있도록 등록
templates.env.globals["today"] = datetime.now().strftime("%Y%m%d")
templates.env.globals["get_member_level_select"] = get_member_level_select
templates.env.globals["is_none_datetime"] = is_none_datetime

MEMBER_MENU_KEY = "200100"
MEMBER_ICON_DIR = "data/member"
MEMBER_IMAGE_DIR = "data/member_image"
# CF_MEMBER_IMG_WIDTH = 60
# CF_MEMBER_IMG_HEIGHT = 60


@router.get("/member_list")
async def member_list(
    request: Request,
    db: db_session,
    search_params: dict = Depends(common_search_query_params),
):
    """
    회원관리 목록
    """
    request.session["menu_key"] = MEMBER_MENU_KEY

    result = select_query(
        request,
        Member,
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
        default_sst="mb_datetime",
        default_sod="desc"
    )

    # 회원정보 추가 설정
    for member in result["rows"]:
        member.group_count = len(member.groups)
        if not is_none_datetime(member.mb_datetime):
            member.mb_datetime = member.mb_datetime.strftime("%y-%m-%d")
        else:
            member.mb_datetime = "없음"
        if not is_none_datetime(member.mb_today_login):
            member.mb_today_login = member.mb_today_login.strftime("%y-%m-%d")
        else:
            member.mb_today_login = "없음"

    # 탈퇴/차단 회원수
    leave_count = db.scalar(select(func.count(Member.mb_id)).where(Member.mb_leave_date != ""))
    intercept_count = db.scalar(select(func.count(Member.mb_id)).where(Member.mb_intercept_date != ""))

    context = {
        "request": request,
        "members": result["rows"],
        "admin": request.state.login_member,  # 로그인해 있는 회원을 관리자로 간주함
        "total_count": result["total_count"],
        "leave_count": leave_count,
        "intercept_count": intercept_count,
        "paging": get_paging(
            request, search_params["current_page"], result["total_count"]
        ),
    }
    return templates.TemplateResponse("member_list.html", context)


@router.post("/member_list_update", dependencies=[Depends(validate_token)])
async def member_list_update(
    request: Request,
    db: db_session,
    checks: List[int] = Form(None, alias="chk[]"),
    mb_id: List[str] = Form(None, alias="mb_id[]"),
    mb_open: List[int] = Form(None, alias="mb_open[]"),
    mb_mailling: List[int] = Form(None, alias="mb_mailling[]"),
    mb_sms: List[int] = Form(None, alias="mb_sms[]"),
    mb_intercept_date: List[int] = Form(None, alias="mb_intercept_date[]"),
    mb_level: List[str] = Form(None, alias="mb_level[]"),
):
    """회원관리 목록 일괄 수정"""
    for i in checks:
        member = db.scalar(select(Member).filter_by(mb_id=mb_id[i]))
        if member:
            if (request.state.config.cf_admin == mb_id[i]) or (request.state.login_member.mb_id == mb_id[i]):
                if get_from_list(mb_intercept_date, i, 0):
                    print("관리자와 로그인된 본인은 차단일자를 설정했다면 수정불가")
                    continue

            member.mb_open = get_from_list(mb_open, i, 0)
            member.mb_mailling = get_from_list(mb_mailling, i, 0)
            member.mb_sms = get_from_list(mb_sms, i, 0)
            member.mb_intercept_date = (datetime.now().strftime("%Y%m%d") if get_from_list(mb_intercept_date, i, 0) else "")
            member.mb_level = mb_level[i]
            db.commit()

    query_params = request.query_params
    url = "/admin/member_list"
    return RedirectResponse(set_url_query_params(url, query_params), 303)


@router.post("/member_list_delete", dependencies=[Depends(validate_token)])
async def member_list_delete(
    request: Request,
    db: db_session,
    checks: List[int] = Form(None, alias="chk[]"),
    mb_id: List[str] = Form(None, alias="mb_id[]"),
):
    """회원관리 목록 일괄 삭제"""
    for i in checks:
        # 관리자와 로그인된 본인은 삭제 불가
        if (request.state.config.cf_admin == mb_id[i]) or (request.state.login_member.mb_id == mb_id[i]):
            print("관리자와 로그인된 본인은 삭제 불가")
            continue

        member = db.scalar(select(Member).filter_by(mb_id=mb_id[i]))
        if member:
            # 이미 삭제된 회원은 제외
            # if re.match(r"^[0-9]{8}.*삭제함", member.mb_memo):
            #     continue
            delete_time = datetime.now().strftime("%Y%m%d")
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
            member.mb_memo = (f"{delete_time} 삭제함\n{member.mb_memo}")
            member.mb_certify = ""
            member.mb_adult = 0
            member.mb_dupinfo = ""

            # 나머지 테이블에서도 삭제
            # 포인트 테이블에서 삭제
            db.execute(delete(Point).where(Point.mb_id == member.mb_id))

            # 그룹접근가능 테이블에서 삭제
            db.execute(delete(GroupMember).where(GroupMember.mb_id == member.mb_id))
            
            # 쪽지 테이블에서 삭제
            db.execute(delete(Memo).where(Memo.me_send_mb_id == member.mb_id))

            # 스크랩 테이블에서 삭제
            db.execute(delete(Scrap).where(Scrap.mb_id == member.mb_id))

            # 관리권한 테이블에서 삭제
            db.execute(delete(Auth).where(Auth.mb_id == member.mb_id))

            # 그룹관리자인 경우 그룹관리자를 공백으로
            db.execute(update(Group).where(Group.gr_admin == member.mb_id).values(gr_admin=""))

            # # 게시판관리자인 경우 게시판관리자를 공백으로
            db.execute(update(Board).where(Board.bo_admin == member.mb_id).values(bo_admin=""))

            # 소셜로그인에서 삭제 또는 해제
            if SocialAuthService.check_exists_by_member_id(member.mb_id):
                SocialAuthService.unlink_social_login(member.mb_id)

            # 아이콘 삭제
            delete_image(f"{MEMBER_ICON_DIR}/{member.mb_id[:2]}", f"{member.mb_id}.gif", 1)

            # 프로필 이미지 삭제
            delete_image(f"{MEMBER_IMAGE_DIR}/{member.mb_id[:2]}", f"{member.mb_id}.gif", 1)

            db.commit()

    url = "/admin/member_list"
    query_params = request.query_params
    return RedirectResponse(set_url_query_params(url, query_params), 303)


@router.get("/member_form")
@router.get("/member_form/{mb_id}")
async def member_form(
    request: Request,
    db: db_session,
    mb_id: Optional[str] = None
):
    """
    회원추가, 수정 폼
    """
    request.session["menu_key"] = MEMBER_MENU_KEY

    exists_member = None
    if mb_id:
        exists_member = db.scalar(select(Member).filter_by(mb_id=mb_id))
        if not exists_member:
            raise AlertException("회원아이디가 존재하지 않습니다.")

        exists_member.mb_icon = get_member_icon(mb_id)
        exists_member.mb_img = get_member_image(mb_id)

    context = {
        "request": request, "member": exists_member}
    return templates.TemplateResponse("member_form.html", context)


# 회원수정 폼
# @router.get("/member_form/{mb_id}")
# def member_form_edit(mb_id: str, request: Request, db: db_session):
#     """
#     회원수정 폼
#     """
#     request.session["menu_key"] = MEMBER_MENU_KEY
#     error = auth_check_menu(request, request.session["menu_key"], "r")
#     if error:
#         return templates.TemplateResponse("alert.html", {"request": request, "errors": [error]})

#     exists_member = db.query(Member).filter_by(mb_id = mb_id).first()
#     if not exists_member:
#         return templates.TemplateResponse("alert.html", {"request": request, "errors": ["회원아이디가 존재하지 않습니다."]})

#     exists_member.mb_icon = get_member_icon(mb_id)
#     exists_member.mb_img = get_member_image(mb_id)

#     return templates.TemplateResponse("member_form.html", {"request": request, "member": exists_member})


# DB등록 및 수정
@router.post("/member_form_update", dependencies=[Depends(validate_token)])
async def member_form_update(
    request: Request,
    db: db_session,
    mb_id: str = Form(...),
    mb_password: str = Form(default=""),
    mb_certify_case: Optional[str] = Form(default=""),
    mb_intercept_date: Optional[str] = Form(default=""),
    mb_leave_date: Optional[str] = Form(default=""),
    mb_zip: Optional[str] = Form(default=""),
    form_data: MemberForm = Depends(),
    mb_icon: UploadFile = File(None),
    del_mb_icon: int = Form(None),
    mb_img: UploadFile = File(None),
    del_mb_img: int = Form(None),
):
    # 한국 우편번호 (postalcode)
    form_data.mb_zip1 = mb_zip[:3]
    form_data.mb_zip2 = mb_zip[3:]

    exists_member = db.scalar(select(Member).filter_by(mb_id=mb_id))
    if not exists_member:  # 등록 (회원아이디가 존재하지 않으면)

        new_member = Member(mb_id=mb_id, **form_data.__dict__)

        if mb_certify_case and form_data.mb_certify:
            new_member.mb_certify = mb_certify_case
            new_member.mb_adult = form_data.mb_adult
        else:
            new_member.mb_certify = ""
            new_member.mb_adult = 0

        if mb_password:
            new_member.mb_password = create_hash(mb_password)
        else:
            # 비밀번호가 없다면 현재시간으로 해시값을 만든후 다시 해시 (알수없게 만드는게 목적)
            time_ymdhis = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            new_member.mb_password = create_hash(create_hash(time_ymdhis))

        db.add(new_member)
        db.commit()

    else:  # 수정 (회원아이디가 존재하면)

        if (request.state.config.cf_admin == mb_id) or (request.state.login_member.mb_id == mb_id):
            # 관리자와 로그인된 본인은 차단일자, 탈퇴일자를 설정했다면 수정불가
            if mb_intercept_date:
                raise AlertException("로그인된 관리자의 차단일자를 설정할 수 없습니다.")
            if mb_leave_date:
                raise AlertException("로그인된 관리자의 탈퇴일자를 설정할 수 없습니다.")

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

    upload_member_icon(request, mb_id, mb_icon, del_mb_icon)
    upload_member_image(request, mb_id, mb_img, del_mb_img)

    url = f"/admin/member_form/{mb_id}"
    query_params = request.query_params
    return RedirectResponse(set_url_query_params(url, query_params), 302)


@router.get("/check_member_id/{mb_id}")
async def check_member_id(
    request: Request,
    db: db_session,
    mb_id: str = Path(...)
):
    """
    회원아이디 중복체크
    """
    exists_member = db.scalar(select(Member).filter_by(mb_id=mb_id))
    if exists_member:
        return {"result": "exists"}
    else:
        return {"result": "not_exists"}


@router.get("/check_member_email/{mb_email}/{mb_id}")
async def check_member_email(
    request: Request,
    db: db_session,
    mb_email: str = Path(...),
    mb_id: str = Path(...),
):
    """
    회원이메일 중복체크
    """
    exists_member = db.scalar(
        select(Member)
        .where(Member.mb_email == mb_email)
        .where(Member.mb_id != mb_id)
    )
    if exists_member:
        return {"result": "exists"}
    else:
        return {"result": "not_exists"}


@router.get("/check_member_nick/{mb_nick}/{mb_id}")
async def check_member_nick(
    request: Request,
    db: db_session,
    mb_nick: str = Path(),
    mb_id: str = Path(),
):
    """
    회원닉네임 중복체크
    """
    exists_member = db.scalar(
        select(Member)
        .where(Member.mb_nick == mb_nick)
        .where(Member.mb_id != mb_id)
    )
    if exists_member:
        return {"result": "exists"}
    else:
        return {"result": "not_exists"}


def upload_member_icon(request: Request, mb_id: str, mb_icon: UploadFile, del_mb_icon: int):
    """회원아이콘 업로드

    Args:
        mb_id (str): 회원아이디
        mb_icon (UploadFile): 업로드된 이미지
        del_mb_icon (int): 삭제여부

    Raises:
        AlertException: 이미지 파일이 아닌경우
    """
    config = request.state.config
    member_icon_dir = f"{MEMBER_ICON_DIR}/{mb_id[:2]}"

    # 이미지 삭제
    delete_image(member_icon_dir, f"{mb_id}.gif", del_mb_icon)

    if mb_icon.filename == "" or mb_icon.size == 0:
        return

    if mb_icon.filename[-3:].lower() != "gif":
        raise AlertException("아이콘은 gif 파일만 업로드 가능합니다.", 400)

    # 하위경로를 만들지 않아도 알아서 만들어줌 data/member/ka/kagla.gif
    make_directory(member_icon_dir)
    # 이미지 저장
    # save_image(member_icon_dir, f"{mb_id}.gif", mb_icon)
    # 이미지 저장
    img = Image.open(mb_icon.file)
    img.resize((config.cf_member_icon_width, config.cf_member_icon_height)).save(f"{member_icon_dir}/{mb_id}.gif")


def upload_member_image(request: Request, mb_id: str, uploaded_mb_img: UploadFile, del_mb_img: int):
    """회원이미지 업로드

    Args:
        mb_id (str): 회원아이디
        uploaded_mb_img (UploadFile): 업로드된 이미지
        del_mb_img (int): 삭제여부

    Raises:
        AlertException: 이미지 파일이 아닌경우
    """
    config = request.state.config
    image_filename = f"{mb_id}.gif"
    member_image_dir = f"{MEMBER_IMAGE_DIR}/{mb_id[:2]}"

    # 이미지 삭제
    delete_image(member_image_dir, image_filename, del_mb_img)

    if uploaded_mb_img.filename == "" or uploaded_mb_img.size == 0:
        return

    IMAGE_REGEX = r"\.(gif|jpe?g|png)$"
    print(uploaded_mb_img.filename)
    if not re.search(IMAGE_REGEX, uploaded_mb_img.filename, re.IGNORECASE):
        raise AlertException(status_code=400, detail="회원이미지 파일은 이미지 파일만 업로드 가능합니다.")

    make_directory(member_image_dir)

    dest_path = os.path.join(member_image_dir, image_filename)
    save_image(member_image_dir, image_filename, uploaded_mb_img)

    if os.path.exists(dest_path):
        with Image.open(dest_path) as img:
            if img.width > config.cf_member_img_width or img.height > config.cf_member_img_height:
                if img.format in ['JPEG', 'PNG']:
                    img.thumbnail((config.cf_member_img_width, config.cf_member_img_height))
                    os.unlink(dest_path)
                    img.save(dest_path)
                else:
                    os.unlink(dest_path)
